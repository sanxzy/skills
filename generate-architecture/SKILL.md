---
name: generate-architecture
version: 0.1.0
description: |
  Generate _xzy-ai/architecture.md — a principle-driven architectural reference that defines Clean Architecture layering, dependency direction, module responsibilities, directory structure, and an adoption checklist. Advisory-only: prescribes patterns and boundaries, NOT specific filenames or implementation details. Stays valid as the codebase evolves. Supports 11 languages and 10 project types. Use when: "generate architecture rules", "create architecture.md", "set up Clean Architecture", "define project structure", or after initial project scaffolding.
---

# Generate Architecture Skill

Generate `_xzy-ai/architecture.md` — a stable, principle-driven architectural reference document. The document defines architectural patterns, layer responsibilities, and boundaries that govern how code should be organized. It should remain valid over time as the codebase evolves.

**Advisory-only output.** This skill produces a principles-based reference — NOT an implementation plan. It must NOT prescribe specific filenames, function signatures, or concrete source files. The document describes **what each layer is for and how they relate**, leaving exact filenames and implementation details to the team. Prescribing specific files (e.g., `generate-package-json.ts`, `scaffold-project.ts`) makes the document outdated the moment the codebase changes.

This is a simple step-by-step coordinator workflow. No agents, no scripts — the coordinator handles everything from language detection to document generation.

## Modules

- [references/CLEAN-ARCHITECTURE-PRINCIPLES.md](./references/CLEAN-ARCHITECTURE-PRINCIPLES.md) — Clean Architecture principles, layers, anti-patterns, and when-to-use guidance.
- [references/FP-PARADIGM.md](./references/FP-PARADIGM.md) — Functional Programming paradigm patterns, immutability, pure functions, ADTs, Result/Either, dependency injection via function parameters.
- [references/OOP-PARADIGM.md](./references/OOP-PARADIGM.md) — Object-Oriented Programming paradigm patterns, SOLID, constructor injection, rich domain model, value objects.
- [references/LAYOUTS.md](./references/LAYOUTS.md) — Canonical directory layouts per project type with language annotations and file extension reference.
- [references/LANGUAGE-CONVENTIONS.md](./references/LANGUAGE-CONVENTIONS.md) — Manifest detection strategy, language-specific conventions, framework→language mappings, toolchain→language mappings.

---

## Coordinator Instructions

You are the coordinator for the `generate-architecture` workflow. Your job is to collect inputs, generate a 10-section `architecture.md`, validate it, and write it to disk.

### Document Structure

The output document has 10 fixed sections:

| # | Section | Content |
|---|---------|---------|
| 1 | Overview & Purpose | What this document is, who it's for, how to use it. |
| 2 | Clean Architecture Principles | Core principles, the four layers, the dependency rule, anti-patterns. |
| 3 | Architectural Paradigm | FP or OOP — the chosen paradigm's patterns and conventions. |
| 4 | Layering & Boundaries | What each layer contains, what it must not contain, layer communication rules. |
| 5 | Dependency Direction | The dependency rule in practice. What can import what. How to enforce. |
| 6 | Module Responsibilities | Layer responsibilities and patterns. What each layer owns conceptually. |
| 7 | Project Directory Structure | Principle-driven layer organization showing Clean Architecture structure. Folders with purpose annotations, NOT specific implementation filenames. |
| 8 | Reference Layout | Annotated reference layout showing idiomatic conventions for this language/framework. |
| 9 | Code Organization Rules | Naming conventions, file organization, import rules, cross-boundary rules. |
| 10 | Adoption Checklist | Principle-based alignment checks. How to verify and enforce architectural boundaries. |

Each section should be short and scannable — 3 bullet points of essential guidance, plus supporting prose.

---

### Step 1: Detect Language

Identify the project's programming language. If the user is in a greenfield/new project with no source code, this step will find no manifests.

1. Check for manifest files in the working directory using the detection table in [LANGUAGE-CONVENTIONS.md](./references/LANGUAGE-CONVENTIONS.md).
2. If exactly one language is detected → use it.
3. If multiple manifests exist → determine if this is a polyglot project. If the project type hasn't been selected yet, note the detected languages and defer the decision to Step 3.
4. If no manifests found (greenfield) → ask the user:
   ```
   No project manifests detected. Which language are you using?
   Options: TypeScript, JavaScript, Python, Go, Rust, Java, Kotlin, Swift, C++, C#, Dart
   ```
   Present as a single-select question.

**Completion**: Language identified (detected or user-specified).

---

### Step 2: Select Paradigm

Ask the user which architectural paradigm to use.

```
Which architectural paradigm should architecture.md prescribe?

- Functional Programming (FP) — recommended. Immutability by default.
  Pure functions, ADTs for domain modeling, explicit effects, function composition.
- Object-Oriented Programming (OOP) — SOLID principles.
  Constructor injection, rich domain model, interfaces as contracts, encapsulation.
```

Present as a single-select question. Recommend FP.

**Completion**: Paradigm selected.

---

### Step 3: Select Project Type

Ask the user which project type best describes their application.

```
What type of project is this?

- Backend — API server, service
- Frontend — browser application, SPA
- Full-Stack — backend + frontend in one repository
- CLI — command-line tool
- Library — reusable package/SDK
- Mobile Cross-Platform — Flutter, React Native, Kotlin Multiplatform
- Android — native Android app
- iOS — native iOS app
- Embedded System — microcontroller, firmware
- IoT — connected device with sensors/actuators
```

Present as a single-select question.

**Completion**: Project type selected.

---

### Step 3a: Full-Stack Language (if Full-Stack selected)

If the project type is Full-Stack:

1. If the backend language was detected and a frontend was also detected (polyglot), use those.
2. If only one language was detected, or greenfield, ask for the frontend language:
   ```
   Your backend language is <detected/specified>. What is your frontend language?
   Options: TypeScript, JavaScript
   ```
3. The generated document will include both backend and frontend layouts in Sections 7 and 8.

**Completion**: Both languages identified.

---

### Step 4: Framework Selection (if Mobile, Android, iOS, or Frontend)

If the project type is mobile cross-platform, Android, or iOS, ask for the specific framework. For frontend, optionally ask.

**Mobile Cross-Platform:**
```
Which mobile framework are you using?

- Flutter — Dart, Material Design
- React Native — TypeScript, cross-platform
- Kotlin Multiplatform — shared Kotlin + native UI
```

**Android:**
```
Which UI framework?

- Jetpack Compose — modern declarative UI
- XML Views — traditional View-based
```

**iOS:**
```
Which UI framework?

- SwiftUI — modern declarative UI
- UIKit — traditional framework
```

**Frontend (optional — only ask if it adds value):**
```
Which frontend framework?

- React / Next.js
- Vue / Nuxt
- Angular
- Svelte / SvelteKit
```

**Framework → Language Auto-Derivation**: When the user selects a framework that dictates the language, skip the language question and auto-derive. See mappings in [LANGUAGE-CONVENTIONS.md](./references/LANGUAGE-CONVENTIONS.md).

**Completion**: Framework selected (if applicable). Language confirmed or auto-derived.

---

### Step 5: Toolchain Selection (if Embedded or IoT)

If the project type is embedded system or IoT, ask for the toolchain:

```
Which toolchain or environment?

- Arduino — C++, PlatformIO
- ESP-IDF — C, FreeRTOS
- Zephyr — C, RTOS
- Bare-Metal C — no RTOS
- Embedded Linux — C/C++ with Linux userspace
```

Auto-derive language from toolchain selection. See mappings in [LANGUAGE-CONVENTIONS.md](./references/LANGUAGE-CONVENTIONS.md). Skip the language question when toolchain is known.

**Completion**: Toolchain selected. Language auto-derived.

---

### Step 6: Check for Existing Document

1. Check if `_xzy-ai/architecture.md` exists.
2. If it does **not** exist → proceed to Step 7.
3. If it exists, ask:
   ```
   _xzy-ai/architecture.md already exists. Overwrite it?

   - Yes — replace with the new architecture.md
   - No — keep the existing file (skill exits)
   ```
4. If user says No → exit gracefully:
   ```
   Existing _xzy-ai/architecture.md preserved. No changes made.
   To force regeneration, delete the file or rename it first.
   ```

**Completion**: Document path confirmed or exit.

---

### Step 7: Generate the Document

Synthesize all collected inputs and reference materials into a complete `architecture.md`.

**Inputs at this point**: language(s), paradigm, project type, framework/toolchain (if applicable).

**Generation process**:

1. **Read references** based on selections:
   - Always: `CLEAN-ARCHITECTURE-PRINCIPLES.md`
   - FP selected: `FP-PARADIGM.md`
   - OOP selected: `OOP-PARADIGM.md`
   - Always: `LAYOUTS.md` — locate the canonical layout for the selected project type
   - Always: `LANGUAGE-CONVENTIONS.md` — locate language-specific file extensions and conventions

2. **Assemble each section** (CRITICAL: see Capstone Rule below):

    > **CAPSTONE RULE — Advisory-Only Output**
    > The entire document must be a principle-driven reference. It must NOT prescribe specific implementation filenames, function names, class names, or file paths. The document should remain valid as the codebase evolves. If a section would list a specific filename like `generate-package-json.ts` or `ProjectName.ts`, replace it with a description of the pattern instead (e.g., "domain value objects" or "config generation functions").

    **Section 1: Overview & Purpose**
    - One paragraph: what this document is, its role in the project, who should read it.
    - One paragraph: how to use it — read before writing code, reference during code reviews.
    - One paragraph: relationship to other docs (design.md, specs).
    - Add: this document is advisory — it describes architectural principles and patterns, not a file-by-file implementation plan.

    **Section 2: Clean Architecture Principles**
    - Summarize the four layers from `CLEAN-ARCHITECTURE-PRINCIPLES.md`.
    - State the dependency rule.
    - List 3 most relevant anti-patterns for this project type.

    **Section 3: Architectural Paradigm**
    - If FP: core principles, Result/Either pattern, dependency injection via function parameters, ADTs.
    - If OOP: SOLID principles, constructor injection, rich domain model, value objects.
    - Source from `FP-PARADIGM.md` or `OOP-PARADIGM.md`.

    **Section 4: Layering & Boundaries**
    - For this project type, describe what each layer owns conceptually and what must NOT go in each layer.
    - **Forbidden:** Do NOT list specific filenames or subdirectories. Describe layer responsibilities at the pattern level (e.g., "the domain layer owns immutable value objects and domain predicates"). Do NOT enumerate files like `ProjectName.ts` or `substituteTemplate.ts`.
    - How layers communicate (interfaces, DTOs, ports).

    **Section 5: Dependency Direction**
    - The import/dependency rules with **pattern-level** examples (not file paths). Show the direction rule: `domain ← application ← adapters ← frameworks`.
    - `domain` imports from nothing.
    - `application` imports from `domain` only.
    - `adapters` imports from `domain` and `application`.
    - `frameworks` imports from everything.
    - What happens when rules are violated.
    - **Forbidden:** Do NOT show concrete import paths like `import { ProjectName } from "../../domain/value-objects/ProjectName"`. Instead, describe the pattern: "application layer imports from domain only — never from adapters or frameworks."

    **Section 6: Module Responsibilities**
    - Describe what each layer owns conceptually — its domain of responsibility. Do NOT list files.
    - Structure as prose paragraphs, not bullet lists of filenames. Example format: "The domain layer owns the immutable domain model — entity types, value objects with built-in validation, pure domain predicates, and port interfaces declared as function types or protocol interfaces."
    - What must NOT go in each layer (e.g., "Domain must NOT contain IO, framework types, or CLI parsing").
    - Cross-layer communication rules (what can call what).
    - **Forbidden:** No `<code>` delimited filenames anywhere. No bullet lists like `- value-objects/ — Immutable value objects: ProjectName (with validation)`. Instead: "The domain layer contains immutable value objects with inline validation and pure domain services for config generation."

    **Section 7: Project Directory Structure**
    - Show the Clean Architecture directory tree. **Directories and barrel files only.** ❌ `ProjectName.ts` ✅ `value-objects/` with a purpose annotation.
    - Annotate each directory with its purpose (what kind of code lives there).
    - Apply language-specific file extensions from `LANGUAGE-CONVENTIONS.md`.
    - **Only structural marker files are allowed:** `index.ts` / `__init__.py` / `mod.rs` / `lib.rs`.
    - **Forbidden: ALL individual source filenames.** Even domain type filenames like `types.ts`, `errors.ts`, `result.ts`. The tree must be directories with `# purpose` annotations. After writing the tree, verify: every line in the tree code block must be either a directory (ends with `/`) or a structural marker file (`index.ts`, `__init__.py`, `mod.rs`).

    **Section 8: Reference Layout**
    - Same format as Section 7 — directories with purpose annotations, no individual implementation files.
    - Use the canonical layout from `LAYOUTS.md`.
    - Add framework-specific sub-directories with annotations.
    - **Forbidden: individual source filenames.**

    **Section 9: Code Organization Rules**
    - Naming conventions: describe patterns (e.g., "use cases use verb-noun camelCase", "domain types use PascalCase"), NOT specific names.
    - File organization: one function/type per file, co-location rules.
    - Import rules: no relative imports crossing layer boundaries. Use path aliases where applicable.
    - Cross-boundary rules: always map across boundaries. Domain entities ≠ database models ≠ API DTOs.
    - Tooling recommendations: architecture tests, import linters.
      - TypeScript/JS: `dependency-cruiser`, `eslint-plugin-import`, `eslint-plugin-boundaries`
      - Python: `import-linter`
      - Java/Kotlin: `ArchUnit`
      - Rust: `cargo-modules` (check), architecture test in `tests/architecture_test.rs`
      - Go: go-module boundaries enforced by `internal/` package
      - .NET: `NetArchTest`, `ArchUnitNET`
    - **Forbidden:** Do NOT list specific function names (no `substituteTemplate`, `scaffoldProject`, `resolveState`). Describe the pattern instead: "Use case functions follow verb-noun naming and return `Result<T, E>`."

    **Section 10: Adoption Checklist**
    - Principle-based alignment checks — verify the architecture is being followed, not that specific files exist.
    - Focus on boundary enforcement and pattern adherence.
    - Examples:
      - [ ] Verify source code follows the directory structure (layers are respected)
      - [ ] Confirm dependency direction — domain imports nothing, application imports domain only
      - [ ] Add lint rules enforcing architectural boundaries (dependency-cruiser, import-linter, ArchUnit)
      - [ ] Review existing code for layer violations (IO leaking into domain, domain importing frameworks)
      - [ ] Set up architecture tests that verify dependency direction
      - [ ] Ensure composition root is in one place (single entry point wires all dependencies)
      - [ ] Verify no ORM/framework types leak into domain layer
      - [ ] Confirm entities enforce invariants (not anemic data bags)
    - **Forbidden:** Do NOT list implementation steps like "Implement `generatePackageJson` in `src/application/generate-package-json.ts`" or "Set up template files with `<% VAR %>` placeholders". These become stale. Focus on what the architecture enforces, not what to build.

**Document format**: Write as markdown with a YAML frontmatter header:

```yaml
---
generated_by: generate-architecture v0.1.0
generated_at: <ISO8601 timestamp>
paradigm: <fp | oop>
project_type: <backend | frontend | full-stack | cli | library | mobile-cross-platform | android | ios | embedded | iot>
language: <language or "frontend: <lang>, backend: <lang>">
framework: <framework or null>
toolchain: <toolchain or null>
---
```

**Self-check before proceeding:** Re-read the generated document and verify:
1. No implementation filenames appear in Sections 4, 5, 6, 7, 8, 9, or 10.
2. The directory tree in Section 7 contains only directories (ending with `/`) and structural markers (`index.ts`, `__init__.py`, `mod.rs`). No `.ts`, `.py`, `.rs` files that are not structural markers.
3. Section 10's checklist items are pattern-based, not implementation-based.
4. Section 6 describes layer responsibilities in prose, not as bullet lists of concrete filenames.
If any violation is found, fix it before writing the document to disk.

**Completion**: Full 10-section document generated in memory and self-checked.

---

### Step 8: Write Document

1. Ensure `_xzy-ai/` directory exists. Create if missing.
2. Write the generated document to `_xzy-ai/architecture.md`.
3. Use atomic write: write to `.tmp` path first, then rename.

**Completion**: `_xzy-ai/architecture.md` written to disk.

---

### Step 9: Validate

Run validation checks against the written document:

| # | Check | Pass Condition | Fail Action |
|---|-------|---------------|-------------|
| 1 | All 10 sections present | Each section heading exists | Report missing sections |
| 2 | Paradigm matches selection | Section 3 content reflects the chosen paradigm | Report mismatch |
| 3 | Language-specific extensions | File extensions in Sections 7/8 match the selected language | Report mismatches |
| 4 | No contradictions | Dependency direction in Section 5 matches the directory layout in Section 7 | Report contradictions |
| 5 | YAML frontmatter valid | Frontmatter is parseable YAML with all required fields | Fix automatically |
| 6 | Non-empty sections | Each section has substantive content (no "TODO", "TBD") | Report empty sections |
| 7 | Directory paths valid | All paths use valid characters, no absolute paths | Report invalid paths |
| 8 | No implementation filenames | No specific source filenames anywhere in Sections 4-10 (e.g., `generate-package-json.ts`, `resolve-config.ts`, `types.ts`, `ProjectName.ts`, `scaffoldProject.ts`). Directory trees in Sections 7/8 contain only directories and structural markers (`index.ts`, `__init__.py`, `mod.rs`). | Report and remove offending filenames |

If validation warnings exist, report them to the user but do not block completion. If critical failures exist (sections missing, paradigm mismatch), regenerate the affected sections before proceeding.

**Completion**: All validation checks pass or warnings reported.

---

### Step 10: Report Completion

Present a summary to the user:

```
Architecture reference generated successfully.

File: _xzy-ai/architecture.md

Configuration:
  - Paradigm: <fp | oop>
  - Project type: <type>
  - Language: <lang>
  - Framework: <framework | none>
  - Toolchain: <toolchain | none>

Document sections:
  - Overview & Purpose
  - Clean Architecture Principles
  - Architectural Paradigm (<FP | OOP>)
  - Layering & Boundaries
  - Dependency Direction
  - Module Responsibilities
  - Project Directory Structure
  - Reference Layout
  - Code Organization Rules
  - Adoption Checklist

Next steps:
  - Review the generated architecture.md
  - Share with your team for alignment
  - Run the adoption checklist to align your codebase
  - Use generate-engineering-specs for feature-level architecture decisions
```

---

## Interaction Summary

Maximum questions the skill may ask the user:

| Question | When asked | Skipped if |
|----------|-----------|------------|
| Language? | Greenfield only | Manifest detected |
| FP or OOP? | Always | — |
| Project type? | Always | — |
| Frontend language? | Full-stack only | Both detected |
| Framework? | Mobile / Android / iOS | Not applicable |
| Toolchain? | Embedded / IoT | Not applicable |
| Overwrite? | Existing architecture.md | No existing file |

Maximum questions: 7 (greenfield + full-stack + mobile + embedded + overwrite). Minimum: 3 (brownfield + backend + no existing file).

---

## Important Rules

- **Never skip steps** — always run all 10 steps in order.
- **Detection first, questions second** — always try to detect before asking.
- **Auto-derive when possible** — framework → language, toolchain → language.
- **Ask one question at a time** — present questions sequentially, not all at once.
- **Reference-first generation** — always read the relevant reference files before generating content.
- **Short reference format** — each section should be scannable. Target ~3 bullet points of essential guidance per section.
- **Language-specific details** — layouts and code examples must use the correct file extensions and idiomatic patterns.
- **Atomic write** — write the final document to `.tmp` first, then rename.
- **Advisory-only output** — the document prescribes architectural principles, patterns, and boundaries. It must NOT prescribe specific implementation filenames (no `generate-package-json.ts`, `scaffold-project.ts`, `types.ts`, `rules.ts`). The document should remain valid as the codebase evolves. Sections 6 and 7 describe layer responsibilities and directory organization — not which files to create.
- **Directories, not files** — the directory trees in Sections 7 and 8 show folders and their purpose annotations. Only structural marker files (`index.ts`, `__init__.py`, `mod.rs`) are acceptable. Individual source filenames are forbidden because they become stale the moment the codebase changes.
- **Principle-based checklist** — Section 10's adoption checklist verifies architectural adherence (boundaries, dependency direction, invariant enforcement), not implementation tasks (which specific files to create).
