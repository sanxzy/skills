# Language Conventions

Manifest detection strategy and idiomatic conventions per supported language. Used by the coordinator to detect the project language and generate language-appropriate directory layouts.

## Detection Order

Check manifests in this order. First match determines the language. If multiple manifests exist (polyglot project), the first match wins unless the user selects a multi-language project type.

| Language | Manifest(s) | Priority |
|----------|------------|----------|
| TypeScript | `package.json` with `typescript` in `devDependencies` or `dependencies`; `tsconfig.json` | 1 |
| JavaScript | `package.json` without `typescript` dep | 2 |
| Python | `pyproject.toml`, `setup.py`, `setup.cfg`, `requirements.txt` | 3 |
| Go | `go.mod` | 4 |
| Rust | `Cargo.toml` | 5 |
| Java | `pom.xml`, `build.gradle`, `build.gradle.kts` (without `kotlin` plugin) | 6 |
| Kotlin | `build.gradle.kts` with `kotlin` plugin; `build.gradle` with `kotlin` | 7 |
| Swift | `Package.swift`, `Podfile` | 8 |
| C++ | `CMakeLists.txt` | 9 |
| C# | `*.csproj`, `*.sln` | 10 |
| Dart | `pubspec.yaml` | 11 |

## Per-Language Idiosyncrasies

### TypeScript / JavaScript
- **Package manager**: npm, yarn, pnpm, bun
- **Module system**: ESM (`import`/`export`) is the 2026 default
- **Path aliases**: `@/` prefix via `tsconfig.json` `paths`
- **Source dir**: `src/` (conventional)
- **Test dir**: `tests/` or `__tests__/` co-located
- **Config files**: `tsconfig.json`, `eslint.config.js`, `prettier.config.js`
- **Build output**: `dist/` or `build/`
- **Key Clean Architecture convention**: Repository interfaces in `domain/repositories/` as `.ts` files using TypeScript interfaces

### Python
- **Package manager**: pip, poetry, uv
- **Module marker**: `__init__.py` in every package directory
- **Config**: `pyproject.toml`
- **Source dir**: `src/` or package name directly (e.g., `app/`)
- **Test dir**: `tests/` mirroring source structure
- **Key convention**: Use `abc.ABC`/`@abstractmethod` for repository interfaces in domain layer

### Go
- **Module**: defined by `go.mod`
- **Entry points**: `cmd/<name>/main.go`
- **Private code**: `internal/` (enforced by Go compiler)
- **Public code**: `pkg/` (importable by external packages)
- **Config dir**: `configs/` or `internal/config/`
- **Migration dir**: `migrations/`
- **Key convention**: Interfaces at use-site. Repository interface defined in domain package, implementation in `internal/repository/`

### Rust
- **Workspace**: `Cargo.toml` with `[workspace]` for multi-crate projects
- **Source dir**: `src/` (enforced by Cargo)
- **Entry point**: `src/main.rs`
- **Library**: `src/lib.rs`
- **Module files**: `src/<module>.rs` or `src/<module>/mod.rs`
- **Test dir**: `tests/` for integration tests; `#[cfg(test)]` modules for unit tests
- **Key convention**: Traits for repository interfaces. `Arc<dyn Trait>` for dependency injection

### Java
- **Build tool**: Maven (`pom.xml`) or Gradle (`build.gradle`)
- **Source dir**: `src/main/java/`
- **Test dir**: `src/test/java/`
- **Package structure**: `com/company/project/`
- **Key convention**: Interfaces in domain package, implementations in infrastructure package. Spring Boot convention uses `domain/`, `application/`, `infrastructure/`, `presentation/` package names

### Kotlin
- **Build tool**: Gradle with Kotlin DSL (`build.gradle.kts`)
- **Source dir**: `src/main/kotlin/`
- **Test dir**: `src/test/kotlin/`
- **Package structure**: Same as Java conventions
- **Multiplatform**: `src/commonMain/`, `src/androidMain/`, `src/iosMain/`
- **Key convention**: Interfaces in domain, `data class` for entities, `object` for use cases

### Swift
- **Package manager**: Swift Package Manager (`Package.swift`)
- **Source dir**: `Sources/`
- **Test dir**: `Tests/`
- **Xcode project**: `.xcodeproj` or `.xcworkspace`
- **Protocol convention**: Protocols (Swift interfaces) in domain, struct-based entities, value types preferred

### C++
- **Build system**: CMake (`CMakeLists.txt`)
- **Source dir**: `src/` or `lib/`
- **Header dir**: `include/`
- **Test dir**: `test/` or `tests/`
- **Key convention**: Abstract base classes for repository interfaces. PIMPL idiom for hiding implementation details. Header-only interfaces + .cpp implementations

### C# (.NET)
- **Build**: `.csproj` files
- **Solution**: `.sln` files
- **Source dir**: `src/<ProjectName>/`
- **Test dir**: `tests/<ProjectName>.Tests/`
- **Key convention**: Interfaces in `Domain` project, implementations in `Infrastructure` project. ASP.NET Core convention uses project-per-layer

### Dart
- **Package manager**: pub (`pubspec.yaml`)
- **Source dir**: `lib/`
- **Test dir**: `test/`
- **Flutter**: `lib/` for shared Dart code, `android/`, `ios/`, `web/` for platform-specific
- **Key convention**: Abstract classes for repository interfaces in domain. Immutable classes with `@freezed` or `copyWith` patterns

## Framework → Language Mapping

When the user selects a framework, the language is auto-derived:

| Framework | Language |
|-----------|----------|
| Flutter | Dart |
| React Native | TypeScript |
| SwiftUI | Swift |
| Kotlin / Jetpack Compose | Kotlin |
| Kotlin Multiplatform | Kotlin |
| Angular | TypeScript |
| Next.js | TypeScript |
| Vue / Nuxt | TypeScript |

## Toolchain → Language Mapping

| Toolchain | Language |
|-----------|----------|
| Arduino | C++ |
| ESP-IDF | C |
| Zephyr | C |
| bare-metal C | C |
| Embedded Linux | C or C++ |
