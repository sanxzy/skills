# syllabus.md Format

`syllabus.md` lives at the teaching workspace root. It is the agreed contract between the user and the teacher: what will be taught, in what order, and to what depth. Nothing is taught before the user confirms it.

## Structure

```md
# Syllabus: {Topic}

## Context
- **Audience**: {who the material is for}
- **Proficiency level**: {where the learner is starting from}
- **Depth**: {quick refresher | deep dive | hands-on skill}
- **Language**: {teaching language}

## Lessons

### 1. {Lesson title}
- **Goal**: {what the learner can do after this lesson, one line}
- **Depth**: {intro | core | mastery}
- **Prerequisites**: {lessons or prior knowledge required; "none" if first}
- **Scenes**: {ordered bullet list of the step-by-step scenes — one evolving visual}
  1. {scene 1: what is shown}
  2. {scene 2: what changes}
- **Success check**: {how the learner demonstrates understanding}

### 2. {Next lesson}
…
```

## Rules

- **One section = one visual lesson.** Each section maps to one `lessons/NNNN-<name>.html` file using the scene template. Do not split one section across lessons or cram several sections into one lesson.
- **First, interview; then draft.** Before writing the syllabus, make sure the context is clear: audience, proficiency level, learning goals, desired depth (quick refresher vs deep dive), learning preferences, and language. Reuse what is already recorded in `mission.md`, `transcript-histories.md`, and `notes.md`; only ask what is missing.
- **Present and confirm before teaching.** Show the proposed syllabus to the user and ask whether it is correct and sufficiently complete. If the user says it is incomplete or incorrect, ask what is missing or should change, revise, and repeat until the user confirms. Only then start the first lesson.
- **Keep each lesson small.** Lessons are short by design (working memory); prefer many small lessons over a few long ones.
- **Tie every lesson to the mission.** Each goal should trace back to why the user wants this.
- **Subagents allowed.** When the topic is broad, use subagents to research and propose sections before consolidating the syllabus — but the final syllabus is one coherent document, not a pile of drafts.
- **Revise when reality shifts.** Missions and goals change; when they do, update the syllabus in place and record the change in `transcript-histories.md`.