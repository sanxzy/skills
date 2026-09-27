#!/usr/bin/env python3
"""Build copy-ready Eleven v3 text and a timecode map from a full anchored draft.

Standard library only. This tool checks structure and approximate timing, not facts,
spoken performance, or the meaning of rewritten words.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys

STAMP = r"\d{2,}:[0-5]\d\.\d{3}"
RANGE = rf"({STAMP})–({STAMP})"
ANCHOR = re.compile(rf"^\[{RANGE}\]$")
TAG = re.compile(r"\[[^\]\n]+\]")
BRACKETED_ABBREVIATION = re.compile(r"\[[^\W\d_]+(?:\.[^\W\d_]+)*\.\]", re.UNICODE)
WORD = re.compile(r"[^\W_]+(?:['’\-][^\W_]+)*", re.UNICODE)
MUSIC = re.compile(r"[♪\s]+")
SRT_SPAN = re.compile(r"^(\d{2}):([0-5]\d):([0-5]\d),(\d{3}) --> (\d{2}):([0-5]\d):([0-5]\d),(\d{3})$")
BEAT = "<!-- beat -->"


@dataclass
class Block:
    anchor: str
    start: float
    end: float
    original: str
    directed: str = ""
    break_after: bool = False

    @property
    def music(self):
        return bool(MUSIC.fullmatch(self.original))


def to_seconds(stamp):
    minute, rest = stamp.split(":")
    second, millis = rest.split(".")
    return int(minute) * 60 + int(second) + int(millis) / 1000


def check_time(start, end, previous_end, where):
    if end <= start:
        raise ValueError(f"{where}: end must be later than start")
    if start < previous_end - 0.0001:
        raise ValueError(f"{where}: timecodes overlap or move backward")


def read_source(path):
    if path.suffix.lower() != ".srt":
        raise ValueError("source must be a narration .srt file")
    blocks = []
    content = path.read_text(encoding="utf-8-sig").strip()
    if not content:
        raise ValueError("source SRT is empty")
    for index, cue in enumerate(re.split(r"\n\s*\n", content), 1):
        lines = cue.splitlines()
        if len(lines) not in (3, 4) or lines[0] != str(index):
            raise ValueError(f"source cue {index}: expected sequential number, SRT range, and one or two spoken lines")
        match = SRT_SPAN.fullmatch(lines[1])
        if not match:
            raise ValueError(f"source cue {index}: expected HH:MM:SS,mmm --> HH:MM:SS,mmm")
        h, m, s, ms, eh, em, es, ems = map(int, match.groups())
        start, end = h * 3600 + m * 60 + s + ms / 1000, eh * 3600 + em * 60 + es + ems / 1000
        check_time(start, end, blocks[-1].end if blocks else 0, f"source cue {index}")
        text_lines = lines[2:]
        if any(not line or line != line.strip() for line in text_lines):
            raise ValueError(f"source cue {index}: every text line must be nonempty and trimmed")
        narration = " ".join(text_lines)
        anchor = f"[{h * 60 + m:02}:{s:02}.{ms:03}–{eh * 60 + em:02}:{es:02}.{ems:03}]"
        blocks.append(Block(anchor, start, end, narration))
    return blocks


def read_draft(path, source_blocks):
    blocks = []
    body = []
    current = None
    previous_end = 0

    def finish_block():
        if current is None:
            return
        text = "\n".join(body).strip()
        if not text:
            raise ValueError(f"draft block {len(blocks) + 1} {current.anchor}: empty text")
        if "```" in text or "<break" in text.lower() or BEAT in text:
            raise ValueError(f"draft block {len(blocks) + 1}: fenced text, SSML breaks and inline beat markers are not TTS input")
        if BRACKETED_ABBREVIATION.search(text):
            raise ValueError(f"draft block {len(blocks) + 1}: write spoken abbreviations without brackets (Mr., not [Mr.]); brackets are v3 audio tags")
        current.directed = text
        if current.music:
            if text != current.original:
                raise ValueError(f"draft block {len(blocks) + 1}: keep video-track music/SFX marker unchanged; it is omitted from TTS")
        elif "♪" in text:
            raise ValueError(f"draft block {len(blocks) + 1}: video-track music/SFX markers cannot appear in spoken text")
        elif not WORD.search(TAG.sub("", text)):
            raise ValueError(f"draft block {len(blocks) + 1}: no spoken words")
        blocks.append(current)
        body.clear()

    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        match = ANCHOR.fullmatch(line)
        if match:
            finish_block()
            start, end = match.groups()
            begin, finish = to_seconds(start), to_seconds(end)
            check_time(begin, finish, previous_end, f"draft line {line_number}")
            previous_end = finish
            if len(blocks) >= len(source_blocks):
                raise ValueError(f"draft line {line_number}: more blocks than source timeline")
            current = Block(line, begin, finish, source_blocks[len(blocks)].original)
        elif line.strip() == BEAT:
            finish_block()
            if not blocks or blocks[-1].break_after:
                raise ValueError(f"draft line {line_number}: beat marker needs a preceding block")
            blocks[-1].break_after = True
            current = None
        elif current is None:
            if line.strip():
                raise ValueError(f"draft line {line_number}: expected an anchored block, not {line!r}")
        else:
            body.append(line)
    finish_block()
    if not blocks:
        raise ValueError("working draft is empty")
    if blocks[-1].break_after:
        raise ValueError("draft ends with a beat marker")
    if len(blocks) != len(source_blocks):
        raise ValueError(f"draft has {len(blocks)} blocks; source has {len(source_blocks)} (do not omit or add blocks)")
    for i, (draft, source) in enumerate(zip(blocks, source_blocks), 1):
        if draft.anchor != source.anchor:
            raise ValueError(f"draft block {i}: anchor {draft.anchor} does not match source {source.anchor}")
        draft.original = source.original
        if source.music and draft.directed != source.original:
            raise ValueError(f"draft block {i}: video-track music/SFX marker must be unchanged")
    return blocks


def spoken(text):
    return TAG.sub("", text).strip()


def changed_words(a, b):
    return [word.casefold() for word in WORD.findall(a)] != [word.casefold() for word in WORD.findall(spoken(b))]


@dataclass
class Passage:
    block_index: int
    number: int
    total: int
    text: str
    final_in_block: bool


def passages_from(blocks):
    passages = []
    for index, block in enumerate(blocks):
        if block.music:
            passages.append(None)  # video-track marker, not spoken text
            continue
        pieces = []
        pending_tags = []
        for part in re.split(r"\n\s*\n", block.directed):
            part = part.strip()
            if not part:
                continue
            # Never strand a tag-only line (including a pause) at a segment end.
            if not WORD.search(TAG.sub("", part)):
                pending_tags.append(part)
                continue
            pieces.append("\n\n".join(pending_tags + [part]))
            pending_tags = []
        if pending_tags:
            pieces[-1] += "\n\n" + "\n\n".join(pending_tags)
        for number, text in enumerate(pieces, 1):
            passages.append(Passage(index, number, len(pieces), text, number == len(pieces)))
    return passages


def group(blocks, target, maximum):
    passages = passages_from(blocks)
    segments = []
    current = []
    size = 0

    def flush():
        nonlocal current, size
        if current:
            segments.append(current)
            current, size = [], 0

    for item in passages:
        if item is None:
            flush()
            continue
        block = blocks[item.block_index]
        length = len(item.text)
        if length > maximum:
            raise ValueError(f"block {item.block_index + 1} {block.anchor}, passage {item.number} is {length} characters, over the {maximum}-character cap; manually add an intonation-unit paragraph break without dropping words")
        additional = length + (2 if current else 0)
        if current and (size + additional > target or size + additional > maximum):
            flush()
            additional = length
        current.append(item)
        size += additional
        gap = blocks[item.block_index + 1].start - block.end if item.final_in_block and item.block_index + 1 < len(blocks) else 0
        if item.final_in_block and (block.break_after or (size >= min(250, target) and gap >= 2)):
            flush()
    flush()
    if not segments:
        raise ValueError("source has no spoken narration blocks")
    return segments


def render(blocks, segments, source_path):
    voice_lines = []
    map_lines = [
        "# Voice segment map", "",
        f"Source timeline (same directory): `{source_path.name}`", "",
        "Timecodes are editorial targets, not measured TTS timings. A source block may span several segments; these are not sub-block timestamps.",
        "Paste only the text inside a segment's fence into Eleven v3. Word-rate flags are approximations; review recorded audio later.", "",
    ]
    warnings = []
    changed = []
    for i, block in enumerate(blocks, 1):
        if block.music:
            continue
        words = len(WORD.findall(spoken(block.directed)))
        rate = words * 60 / (block.end - block.start)
        if words >= 8 and rate > 185:
            warnings.append(f"Block {i} {block.anchor}: about {rate:.0f} words/minute in its editorial interval; may overrun.")
        if changed_words(block.original, block.directed):
            changed.append((i, block))
    for number, items in enumerate(segments, 1):
        content = "\n\n".join(item.text for item in items)
        voice_lines.extend([f"## Segment {number:03d}", "", "```text", content, "```", ""])
        first, last = blocks[items[0].block_index], blocks[items[-1].block_index]
        map_lines.extend([f"## Segment {number:03d}", "", f"Source span: {first.anchor} to {last.anchor}; TTS characters: {len(content)}.", "", "Source passages:"])
        for item in items:
            block = blocks[item.block_index]
            map_lines.append(f"- Block {item.block_index + 1}, passage {item.number}/{item.total}: {block.anchor}")
        map_lines.append("")
    music = [(i, block) for i, block in enumerate(blocks, 1) if block.music]
    map_lines.extend(["## Editorial checks", "", "### Possible timing overruns", ""])
    map_lines.extend(f"- {w}" for w in warnings)
    if not warnings:
        map_lines.append("- None flagged by the approximate word-rate check; recorded timing still needs review.")
    map_lines.extend(["", "### Spoken-word differences to review", ""])
    for i, block in changed:
        map_lines.extend([f"- Block {i} {block.anchor}:", f"  - Source: {block.original}", f"  - Directed spoken text: {spoken(block.directed).replace(chr(10), ' ')}"])
    if not changed:
        map_lines.append("- None detected (case, punctuation, spacing, and audio tags are ignored by this comparison).")
    map_lines.extend(["", "### Video-track music/SFX placement (not TTS)", ""])
    map_lines.extend(f"- Block {i} {block.anchor}: `♪ ♪` is for video-track placement only; omitted from Eleven v3 input." for i, block in music)
    if not music:
        map_lines.append("- None.")
    map_lines.extend(["", "Review every flagged wording change for preserved meaning; this helper cannot fact-check or verify pronunciation."])
    return "\n".join(voice_lines).rstrip() + "\n", "\n".join(map_lines).rstrip() + "\n", warnings, changed


def build(source, draft, target=500, maximum=900, force=False):
    if not 0 < target <= maximum <= 4500:
        raise ValueError("require 0 < target-chars <= max-chars <= 4500 (leave headroom below 5,000)")
    if source.resolve() == draft.resolve():
        raise ValueError("source and working draft must be different files")
    if source.name.endswith((".source.md", ".sources.md", ".voice.md", ".voice.map.md")) or source.suffix.lower() != ".srt":
        raise ValueError("source must be a narration .srt file")
    voice = source.with_name(source.stem + ".voice.md")
    mapping = source.with_name(source.stem + ".voice.map.md")
    if not force and (voice.exists() or mapping.exists()):
        raise ValueError("output already exists; review both files first, then pass --force to regenerate together")
    if draft.resolve() in (voice.resolve(), mapping.resolve()):
        raise ValueError("working draft cannot be an output path")
    blocks = read_source(source)
    directed = read_draft(draft, blocks)
    segments = group(directed, target, maximum)
    voice_text, map_text, warnings, changes = render(directed, segments, source)
    voice.write_text(voice_text, encoding="utf-8")
    mapping.write_text(map_text, encoding="utf-8")
    return voice, mapping, len(segments), warnings, changes


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="video-script .srt narration")
    parser.add_argument("draft", type=Path, help="complete anchored voice-direction working draft")
    parser.add_argument("--target-chars", type=int, default=500)
    parser.add_argument("--max-chars", type=int, default=900)
    parser.add_argument("--force", action="store_true", help="replace both existing output files after review")
    args = parser.parse_args(argv)
    try:
        voice, mapping, count, warnings, changes = build(args.source, args.draft, args.target_chars, args.max_chars, args.force)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Created {voice} ({count} segment(s)) and {mapping}")
    print(f"Review {len(warnings)} timing warning(s) and {len(changes)} spoken-word difference(s) in the map.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
