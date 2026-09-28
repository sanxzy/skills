#!/usr/bin/env python3
"""Read-only structural and approximate timing checks for video-script artifacts.

This does not fact-check narration or establish a recorded runtime.
Uses only the Python standard library.
"""

import argparse
import json
import math
from pathlib import Path
import re
import sys


STAMP = r"(\d{2}):([0-5]\d):([0-5]\d),(\d{3})"
SPAN = re.compile(rf"^{STAMP} --> {STAMP}$")
WORD = re.compile(r"[^\W_]+(?:['’\-][^\W_]+)*", re.UNICODE)
URL = re.compile(r"https?://|www\.", re.I)
INTERNAL_LABEL = re.compile(
    r"^(?:hook|introduction|intro|chapter\s+\d+|conclusion|"
    r"research\s+notes?|sources?|word\s+count|duration)\s*:", re.I
)
SENTENCE_BOUNDARY = re.compile(r"(?<!\.)[.!?](?!\.)[ \t]+(?=\S)")
BRACKETED = re.compile(r"\[([^\[\]]+)\]")
SPOKEN_ABBREVIATION = re.compile(r"[^\W\d_]+(?:\.[^\W\d_]+)*\.", re.UNICODE)


def has_invalid_brackets(narration):
    without_abbreviations = BRACKETED.sub(
        lambda match: "" if SPOKEN_ABBREVIATION.fullmatch(match.group(1)) else "[]", narration
    )
    return "[" in without_abbreviations or "]" in without_abbreviations


def has_multiple_sentences(narration):
    return bool(SENTENCE_BOUNDARY.search(narration))


def seconds(parts):
    hours, minutes, sec, millis = map(int, parts)
    return hours * 3600 + minutes * 60 + sec + millis / 1000


def count_words(narration):
    # Music is unspoken. Digits/acronyms are not expanded automatically.
    return len(WORD.findall(narration.replace("♪", " ")))


def validate(script, sources=None, target_minutes=None, tolerance_seconds=None,
             min_wpm=95.0, max_wpm=185.0, max_unspoken_fraction=0.20,
             allow_spoken_labels=False):
    errors, warnings, blocks = [], [], []
    script = Path(script)
    source_path = Path(sources) if sources else script.with_suffix(".source.md")
    try:
        content = script.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        return {"ok": False, "errors": [f"Cannot read script: {exc}"],
                "warnings": [], "metrics": {}}
    if script.suffix.lower() != ".srt":
        errors.append("New video scripts must be .srt files.")
    if not content.strip():
        errors.append("SRT script is empty.")
    cues = re.split(r"\n\s*\n", content.strip()) if content.strip() else []
    previous_end = 0.0
    for index, cue in enumerate(cues, 1):
        lines = cue.splitlines()
        if len(lines) not in (3, 4):
            errors.append(f"Cue {index}: expected number, time range, and one or two text lines.")
            continue
        if lines[0] != str(index):
            errors.append(f"Cue {index}: cue number must be {index}.")
        match = SPAN.fullmatch(lines[1])
        if not match:
            errors.append(f"Cue {index}: expected HH:MM:SS,mmm --> HH:MM:SS,mmm.")
            continue
        start, end = seconds(match.groups()[:4]), seconds(match.groups()[4:8])
        text_lines = lines[2:]
        narration = " ".join(text_lines)
        if any(not line or line != line.strip() for line in text_lines):
            errors.append(f"Cue {index}: every text line must be nonempty without leading/trailing whitespace.")
        if end <= start:
            errors.append(f"Cue {index}: end must be after start.")
        if start < previous_end - 0.0001:
            errors.append(f"Cue {index}: overlaps or moves backward.")
        previous_end = max(previous_end, end)
        if URL.search(narration):
            errors.append(f"Cue {index}: URL belongs in the source file.")
        if any(marker in narration for marker in ("```", ":::writing", "cite", "")):
            errors.append(f"Cue {index}: wrapper or citation markup in narration.")
        if has_invalid_brackets(narration):
            errors.append(f"Cue {index}: brackets are allowed only for spoken title abbreviations such as [Mr.] or [Dr.]; no citations, tags, or metadata.")
        if INTERNAL_LABEL.search(narration) and not allow_spoken_labels:
            errors.append(f"Cue {index}: possible internal label; allow only if intentionally spoken with --allow-spoken-labels.")
        if has_multiple_sentences(narration):
            errors.append(f"Cue {index}: more than one sentence; split into separate timed cues.")
        if re.match(r"^(?:#{1,6}\s|---$)", narration):
            errors.append(f"Cue {index}: internal label/metadata in narration.")
        words = count_words(narration)
        music = narration == "♪ ♪"
        if "♪" in narration and not music:
            errors.append(f"Cue {index}: ♪ ♪ must be the only text in its video-track cue.")
        if not words and not music:
            errors.append(f"Cue {index}: no spoken narration or allowed ♪ ♪ marker.")
        duration = end - start
        if words and duration > 0:
            readability = []
            if max(map(len, text_lines)) > 40:
                readability.append(f"line reaches {max(map(len, text_lines))} characters (target ≤40)")
            if len(narration) > 80:
                readability.append(f"{len(narration)} displayed characters (review above ~80)")
            if len(narration) / duration > 15:
                readability.append(f"{len(narration) / duration:.1f} displayed CPS (relaxed target ≤15)")
            if readability:
                warnings.append(f"Cue {index}: subtitle readability: {'; '.join(readability)}.")
        if words > 35:
            errors.append(f"Cue {index}: {words} word tokens; maximum is 35 per spoken cue.")
        if words and duration > 15:
            errors.append(f"Cue {index}: {duration:.1f} seconds; maximum is 15 per spoken cue.")
        rate = 60 * words / duration if duration > 0 else 0.0
        if words >= 8 and duration > 0:
            if rate > max_wpm:
                errors.append(f"Cue {index}: {rate:.1f} estimated WPM exceeds {max_wpm:g}.")
            if rate < min_wpm:
                warnings.append(f"Cue {index}: {rate:.1f} estimated WPM; inspect for padding or visual action.")
        elif words and duration > 0:
            warnings.append(f"Cue {index}: short fragment; review timing manually.")
        blocks.append({"start": start, "end": end, "words": words,
                       "duration": max(0.0, duration), "wpm": rate})
    timeline = max((b["end"] for b in blocks), default=0.0)
    active = sum(b["duration"] for b in blocks if b["words"])
    word_count = sum(b["words"] for b in blocks)
    unspoken = max(0.0, timeline - active)
    fraction = unspoken / timeline if timeline else 0.0
    overall_rate = 60 * word_count / active if active else 0.0
    if target_minutes is None:
        if timeline < 480:
            errors.append("Default duration requires at least eight minutes.")
    else:
        target = target_minutes * 60
        tolerance = tolerance_seconds if tolerance_seconds is not None else target * 0.05
        if abs(timeline - target) > tolerance + 0.0001:
            errors.append(f"Timeline differs from requested duration by more than {tolerance:g} seconds.")
    if not word_count:
        errors.append("Script contains no spoken words.")
    elif active and not min_wpm <= overall_rate <= max_wpm:
        errors.append(f"Overall active narration rate {overall_rate:.1f} WPM is outside {min_wpm:g}–{max_wpm:g}.")
    if fraction > max_unspoken_fraction + 0.0001:
        errors.append(f"Unspoken time is {fraction:.1%}; inspect the visual plan before allowing this much time.")
    try:
        source_text = source_path.read_text(encoding="utf-8")
        if not source_text.strip() or not re.search(r"https?://\S+", source_text):
            errors.append("Sources file must be nonempty and contain supporting URLs.")
    except (OSError, UnicodeError) as exc:
        errors.append(f"Cannot read paired sources file: {exc}")
    return {
        "ok": not errors, "script": str(script), "sources": str(source_path),
        "errors": errors, "warnings": warnings,
        "metrics": {"cues": len(blocks), "words": word_count,
                    "timeline_seconds": round(timeline, 3),
                    "active_narration_seconds": round(active, 3),
                    "unspoken_seconds": round(unspoken, 3),
                    "unspoken_fraction": round(fraction, 4),
                    "estimated_active_wpm": round(overall_rate, 1)},
        "limitations": "Word-token estimates only; facts, source support, shot availability, and recorded timing require human/agent review."
    }


def positive(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be a positive finite number")
    return number


def nonnegative(value):
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise argparse.ArgumentTypeError("must be a nonnegative finite number")
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("script", type=Path, help="standard .srt script (one or two text lines per numbered cue)")
    parser.add_argument("--sources", type=Path)
    parser.add_argument("--target-minutes", type=positive)
    parser.add_argument("--tolerance-seconds", type=nonnegative)
    parser.add_argument("--min-wpm", type=positive, default=95.0)
    parser.add_argument("--max-wpm", type=positive, default=185.0)
    parser.add_argument("--max-unspoken-fraction", type=nonnegative, default=0.20)
    parser.add_argument("--allow-spoken-labels", action="store_true",
                        help="allow label-like wording explicitly intended as spoken narration")
    parser.add_argument("--json", action="store_true", help="emit machine-readable results")
    args = parser.parse_args(argv)
    if args.min_wpm > args.max_wpm:
        parser.error("--min-wpm must not exceed --max-wpm")
    if args.max_unspoken_fraction > 1:
        parser.error("--max-unspoken-fraction must be at most 1")
    if args.tolerance_seconds is not None and args.target_minutes is None:
        parser.error("--tolerance-seconds requires --target-minutes")
    report = validate(args.script, args.sources, args.target_minutes,
                      args.tolerance_seconds, args.min_wpm, args.max_wpm,
                      args.max_unspoken_fraction, args.allow_spoken_labels)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("PASS" if report["ok"] else "FAIL")
        for name, value in report["metrics"].items():
            print(f"{name}: {value}")
        for issue in report["errors"]:
            print(f"ERROR: {issue}")
        for issue in report["warnings"]:
            print(f"WARNING: {issue}")
        print(report.get("limitations", "No factual verification performed."))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
