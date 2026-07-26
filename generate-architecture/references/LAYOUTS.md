# Directory Layout Templates

Reference for Sections 7 and 8 of `architecture.md`. Canonical Clean Architecture directory layouts per project type, with language-specific annotations.

## How to Use

Each project type below has a **canonical layout** (language-agnostic) and **language annotations** (file extensions, package conventions, framework specifics). The coordinator selects the canonical layout for the chosen project type, then applies language annotations.

---

## 1. Backend

### Canonical Layout

```text
src/
├── domain/                    # Entities, value objects, repository interfaces
│   ├── entities/
│   ├── value-objects/
│   ├── repositories/          # Interface declarations (ports)
│   └── services/              # Domain services (pure domain logic)
│
├── application/               # Use cases, DTOs
│   ├── use-cases/
│   ├── dtos/
│   └── services/              # Application services
│
├── infrastructure/            # Adapters: DB, HTTP clients, external services
│   ├── persistence/
│   ├── http-clients/
│   ├── messaging/
│   ├── config/
│   └── di/                    # Composition root / dependency wiring
│
├── presentation/              # HTTP/CLI/gRPC entry points
│   ├── controllers/
│   ├── routes/
│   └── middlewares/
│
├── shared/                    # Cross-cutting: errors, types, utils
│   ├── errors/
│   ├── types/
│   └── utils/
│
├── config/
├── migrations/
├── tests/
└── main.ts                    # Entry point: composition root
```

### Language Annotations

| Language | Entry point | Source dir | Key conventions |
|----------|------------|-----------|-----------------|
| TypeScript | `src/main.ts` | `src/` | Interfaces in `domain/repositories/*.ts`; path alias `@/` |
| Python | `src/main.py` | `src/` or `app/` | `__init__.py` in every dir; `abc.ABC` for interfaces |
| Go | `cmd/api/main.go` | `internal/` | Interfaces at use-site; `internal/` for private |
| Rust | `src/main.rs` | `src/` | Traits for interfaces; `Arc<dyn Trait>` for DI |
| Java | `src/main/java/.../Application.java` | `src/main/java/` | Package-per-layer; Spring `@Configuration` |
| Kotlin | `src/main/kotlin/.../Application.kt` | `src/main/kotlin/` | `interface` in domain; `data class` for entities |
| C# | `src/Program.cs` | `src/<Project>/` | `IOrderRepository` interface; ASP.NET Core |
| C++ | `src/main.cpp` | `src/` | Abstract base classes for interfaces; PIMPL idiom |

### Framework Notes

| Framework | Additional directories |
|-----------|----------------------|
| Express/Fastify | `src/presentation/middlewares/` |
| Spring Boot | `src/main/resources/` for config |
| ASP.NET Core | `appsettings.json` at root |
| Django | `myproject/settings.py`, `myproject/urls.py` |

---

## 2. Frontend

### Canonical Layout

```text
src/
├── app/                       # App entrypoints and composition
│   ├── providers/             # Context providers, DI
│   └── store/                 # State management
│
├── features/                  # Feature-first organization
│   ├── auth/
│   │   ├── domain/            # Business rules, state types
│   │   ├── application/       # Use cases, selectors
│   │   ├── infrastructure/    # API clients, persistence
│   │   ├── presentation/      # Components, hooks, pages
│   │   └── index.ts
│   │
│   └── user/
│       ├── domain/
│       ├── application/
│       ├── infrastructure/
│       ├── presentation/
│       └── index.ts
│
├── shared/                    # Cross-feature reusable modules
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   ├── ui/                    # Design system components
│   ├── utils/
│   ├── types/
│   └── constants/
│
├── config/
├── styles/
├── tests/
└── main.ts                    # Entry point
```

### Language Annotations

| Language | Entry point | Key conventions |
|----------|------------|-----------------|
| TypeScript | `src/main.tsx` | `.tsx` for components, `.ts` for logic |
| JavaScript | `src/main.jsx` | `.jsx` for components, `.js` for logic |

### Framework Notes

| Framework | Adaptations |
|-----------|------------|
| React | Hooks in `presentation/hooks/`; Context providers in `app/providers/` |
| Vue | `.vue` SFCs in `presentation/`; Composables in `application/` |
| Angular | Modules in `app/`; Services in `application/`; Components in `presentation/` |
| Svelte | `.svelte` files in `presentation/`; Stores in `app/store/` |
| Next.js | `app/` directory (App Router); `pages/` for Pages Router |

---

## 3. Full-Stack

### Canonical Layout

```text
src/
├── backend/                   # Backend service (see Backend layout)
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   ├── presentation/
│   ├── main.ts
│   └── tests/
│
├── frontend/                  # Frontend app (see Frontend layout)
│   ├── src/
│   │   ├── app/
│   │   ├── features/
│   │   ├── shared/
│   │   └── main.tsx
│   └── tests/
│
├── shared/                    # Shared types, configs, scripts
│   ├── types/
│   ├── config/
│   ├── docker/
│   ├── scripts/
│   └── docs/
│
├── docker-compose.yml
├── package.json               # Monorepo root (workspace)
├── README.md
└── turbo.json                 # Or nx.json for Nx monorepo
```

### Language Notes
- **Frontend + Backend same language** (e.g., TypeScript/TypeScript): Single `package.json` with workspace config (Turborepo, Nx).
- **Frontend + Backend different languages** (e.g., TypeScript frontend + Go backend): Separate manifests. `docker-compose.yml` for orchestration.

### Monorepo Tooling

| Tool | Config file |
|------|------------|
| Turborepo | `turbo.json` |
| Nx | `nx.json` |
| pnpm Workspaces | `pnpm-workspace.yaml` |
| Yarn Workspaces | `package.json` workspaces |

---

## 4. CLI

### Canonical Layout

```text
src/
├── domain/                    # Entities, value objects, domain rules
│   ├── entities/
│   ├── value-objects/
│   └── services/
│
├── application/               # Use cases
│   ├── commands/
│   └── services/
│
├── infrastructure/            # Adapters: file system, API clients
│   ├── cli/
│   ├── file-system/
│   └── http-clients/
│
├── presentation/              # CLI command definitions
│   ├── commands/
│   ├── parsers/
│   └── formatters/
│
├── shared/
├── tests/
└── main.ts                    # CLI entry point
```

### Framework Notes

| Framework | Entry point | Key conventions |
|-----------|------------|-----------------|
| Node.js (Commander) | `src/cli/index.ts` | Command modules in `presentation/commands/` |
| Python (Click/Typer) | `src/cli/main.py` | `@click.command` decorators |
| Go (Cobra) | `cmd/cli/main.go` | `cmd/` directory for entry points |
| Rust (Clap) | `src/main.rs` | `structopt` / `clap` derive macros |
| C# (.NET CLI) | `src/Program.cs` | `System.CommandLine` |

---

## 5. Library

### Canonical Layout

```text
src/
├── domain/                    # Public types, interfaces
│   ├── entities/
│   ├── value-objects/
│   └── repositories/          # Interface declarations
│
├── application/               # Public API use cases
│   ├── use-cases/
│   └── dtos/
│
├── infrastructure/            # Default implementations (optional)
│   └── implementations/
│
├── shared/                    # Internal utilities, errors
│   ├── errors/
│   └── utils/
│
├── tests/
└── index.ts                   # Library entry point (barrel file)
```

### Key Differences from Backend
- No `presentation/` layer — the library is consumed by other code
- `domain/` contains the public API surface
- `infrastructure/` is optional (consumers provide their own implementations)
- Entry point is a barrel file (`index.ts`, `__init__.py`, `lib.rs`)

---

## 6. Mobile Cross-Platform

### Canonical Layout

```text
lib/
├── app/                       # App entrypoints and composition
│   ├── providers/
│   └── navigation/
│
├── features/                  # Feature modules (shared across platforms)
│   ├── auth/
│   │   ├── domain/
│   │   ├── application/
│   │   ├── infrastructure/
│   │   ├── presentation/
│   │   └── index.ts
│   │
│   └── user/
│       ├── domain/
│       ├── application/
│       ├── infrastructure/
│       ├── presentation/
│       └── index.ts
│
├── shared/                    # Shared code
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   ├── ui/
│   ├── utils/
│   ├── types/
│   └── constants/
│
├── platform/                  # Platform-specific code
│   ├── android/
│   ├── ios/
│   └── web/
│
├── tests/
└── main.dart                  # Entry point
```

### Framework Notes

| Framework | Layout Adaptations |
|-----------|-------------------|
| Flutter | `lib/` source dir; `android/`, `ios/`, `web/` at root; `.dart` files |
| React Native | `src/` source dir; `android/`, `ios/` at root; `.tsx` files |
| Kotlin Multiplatform | `src/commonMain/`, `src/androidMain/`, `src/iosMain/` |

---

## 7. Android

### Canonical Layout (Jetpack Compose / Kotlin)

```text
app/
├── src/
│   ├── main/
│   │   ├── kotlin/
│   │   │   ├── di/              # Hilt/Dagger modules
│   │   │   ├── ui/              # Composables
│   │   │   ├── data/            # Data sources, repositories
│   │   │   ├── domain/          # Use cases, entities
│   │   │   ├── navigation/
│   │   │   └── MainActivity.kt
│   │   ├── res/
│   │   └── AndroidManifest.xml
│   └── test/
├── build.gradle.kts
└── proguard-rules.pro
```

### Clean Architecture Adaptation
- **Domain**: `domain/` package — entities, use cases, repository interfaces
- **Data**: `data/` package — repository implementations, data sources, DTOs
- **Presentation**: `ui/` package — ViewModels, Composables
- **DI**: `di/` package — Hilt modules wiring implementations

---

## 8. iOS

### Canonical Layout (SwiftUI)

```text
Sources/
├── App/
│   ├── App.swift              # Entry point
│   └── DI/                    # Dependency injection
│
├── Domain/
│   ├── Entities/
│   ├── UseCases/
│   ├── Repositories/          # Protocol interfaces
│   └── Services/
│
├── Data/
│   ├── Repositories/          # Concrete implementations
│   ├── DataSources/           # API, database
│   ├── DTOs/
│   └── Mappers/
│
├── Presentation/
│   ├── Views/
│   ├── ViewModels/
│   └── Navigation/
│
├── Shared/
│   ├── Errors/
│   ├── Types/
│   └── Utils/
│
├── Resources/
└── Tests/
```

### Clean Architecture Adaptation
- **Domain**: Protocol-based repository interfaces. Pure Swift, no UIKit/SwiftUI imports.
- **Data**: Concrete repository implementations. Network and persistence adapters.
- **Presentation**: SwiftUI Views + ViewModels. Thin views, logic in ViewModels.
- **DI**: Resolver or manual wiring in `DI/` module.

---

## 9. Embedded System

### Canonical Layout (C/C++)

```text
src/
├── domain/                    # Pure logic, no hardware dependencies
│   ├── entities/
│   ├── value-objects/
│   └── services/
│
├── application/               # Use cases
│   ├── use-cases/
│   └── dtos/
│
├── ports/                     # Hardware abstraction interfaces
│   ├── gpio/
│   ├── i2c/
│   ├── spi/
│   └── uart/
│
├── adapters/                  # Hardware-specific implementations
│   ├── arduino/
│   ├── esp_idf/
│   ├── zephyr/
│   └── bare_metal/
│
├── drivers/                   # Low-level hardware drivers
├── config/                    # Build configs, linker scripts
├── tests/
└── main.cpp                   # Entry point
```

### Toolchain Notes

| Toolchain | Key conventions |
|-----------|----------------|
| Arduino | `platformio.ini`; `.ino` sketches in `adapters/arduino/` |
| ESP-IDF | `CMakeLists.txt`; FreeRTOS tasks in `application/` |
| Zephyr | `prj.conf`; Device Tree overlays in `config/` |
| bare-metal C | `Makefile` or `CMakeLists.txt`; no RTOS |
| Embedded Linux | C/C++ with pthreads; systemd service files |

### Key Differences
- **No dynamic allocation** in domain layer (stack-only)
- **No exceptions** in C++ — use `Result<T, E>` or error codes
- **Hardware abstraction layer** (ports/adapters) is critical
- **No heap** in many embedded environments — design accordingly
- **Static linking** — avoid runtime dependencies

---

## 10. IoT

### Canonical Layout

```text
src/
├── domain/                    # Business logic for device behavior
│   ├── entities/
│   ├── value-objects/
│   └── services/
│
├── application/               # Use cases (device operations)
│   ├── use-cases/
│   └── dtos/
│
├── ports/                     # Hardware and protocol interfaces
│   ├── sensors/
│   ├── actuators/
│   ├── connectivity/
│   └── storage/
│
├── adapters/                  # Hardware/protocol implementations
│   ├── mqtt/
│   ├── http/
│   ├── coap/
│   ├── sensors/
│   └── storage/
│
├── config/                    # Device config, OTA manifests
├── firmware/                  # Low-level firmware (if separate)
├── tests/
└── main.cpp                   # Device entry point
```

### Key Differences from Embedded System
- **Connectivity layer**: MQTT, CoAP, HTTP clients for cloud communication
- **OTA updates**: Config for over-the-air update manifests
- **Sensor/actuator abstraction**: Ports for each sensor type
- **Edge processing**: May include local data processing before cloud upload
- **Power management**: Use cases for sleep/wake cycles

---

## Cross-Language File Extensions

| Language | Source | Interface | Test | Config |
|----------|--------|-----------|------|--------|
| TypeScript | `.ts` | `.ts` (interface) | `.test.ts` | `.json` |
| JavaScript | `.js` | `.js` | `.test.js` | `.json` |
| Python | `.py` | `.py` (ABC) | `test_*.py` | `.toml` |
| Go | `.go` | `.go` (interface) | `_test.go` | `.yaml` |
| Rust | `.rs` | `.rs` (trait) | `test_*.rs` | `.toml` |
| Java | `.java` | `.java` (interface) | `*Test.java` | `.xml`/`.properties` |
| Kotlin | `.kt` | `.kt` (interface) | `*Test.kt` | `.toml` |
| Swift | `.swift` | `.swift` (protocol) | `*Tests.swift` | `.plist` |
| C++ | `.cpp`/`.hpp` | `.hpp` (abstract class) | `*_test.cpp` | `.json` |
| C# | `.cs` | `.cs` (interface) | `*Tests.cs` | `.json` |
| Dart | `.dart` | `.dart` (abstract class) | `*_test.dart` | `.yaml` |
