# Clean Architecture Principles

Reference for Section 2 of `architecture.md`. Adapted from Robert C. Martin's Clean Architecture, with pragmatic additions for real-world projects.

## The Core Idea

Clean Architecture is a set of principles for separating software into layers with a strict dependency direction. The outer layers are implementation details; the inner layers are business rules. Dependencies always point inward.

## The Four Layers

### 1. Entities (Domain Layer)
- **Purpose**: Enterprise/business rules. The most stable layer.
- **Contains**: Entities, value objects, domain events, repository interfaces, domain services.
- **Depends on**: Nothing. No frameworks, no databases, no HTTP.
- **Testability**: 100% testable without infrastructure. Pure logic.
- **Identity**: Entities have identity (ID). Value objects are defined by their attributes.
- **Invariants**: Entities enforce business invariants (e.g., "an order cannot be shipped after it's cancelled").

### 2. Use Cases (Application Layer)
- **Purpose**: Application-specific business rules. Orchestrates entities to perform work.
- **Contains**: Use case classes/functions, DTOs, input/output ports, application services.
- **Depends on**: Entities layer only. Imports from domain, never from infrastructure.
- **Role**: One use case per business operation (CreateOrder, CancelSubscription). Each use case is a single transaction boundary.
- **Testability**: Testable by mocking repository interfaces.

### 3. Interface Adapters
- **Purpose**: Convert data between use cases and external systems.
- **Contains**: Controllers, presenters, gateways, repositories (implementations).
- **Depends on**: Use Cases and Entities. Implements interfaces defined in those layers.
- **HTTP**: Controllers parse HTTP requests, call use cases, format HTTP responses.
- **Persistence**: Repository implementations translate between domain entities and database models.
- **Mappers**: Use mappers at every boundary — never let database rows leak into domain code.

### 4. Frameworks & Drivers
- **Purpose**: Glue code connecting the application to the outside world.
- **Contains**: Web frameworks, database drivers, message queues, configuration, DI containers.
- **Depends on**: All inner layers. This is where `main()` lives.
- **Thin layer**: Should contain minimal logic. Wiring and bootstrapping only.

## The Dependency Rule

**Source code dependencies must only point inward.** Nothing in an inner circle can know about something in an outer circle.

```
Frameworks → Interface Adapters → Use Cases → Entities
```

Concrete rules:
- Domain imports from nothing.
- Application imports from domain only.
- Adapters import from domain and application.
- Frameworks import from everything.

## Key Principles (Pragmatic)

### 1. Business logic must not depend on infrastructure
The test of clean architecture: can you run your business logic without a database, a web server, or a message queue? If yes, you have clean architecture.

### 2. One use case per operation
Each use case does one thing. LoginUser, not UserService. CreateOrder, not OrderManager. This prevents God objects.

### 3. Repository interfaces live in domain
The domain declares what it needs: "I need a way to find users by email." The infrastructure provides the implementation. This is dependency inversion.

### 4. Use DTOs at every boundary
Never pass domain entities directly through HTTP or database layers. Translate. This prevents layer coupling.

### 5. Separate read and write models
CQRS (Command Query Responsibility Segregation) is a natural fit. Queries can bypass use cases and go directly to optimized read models. Commands always go through use cases.

### 6. Start simple, add layers when needed
A 5-endpoint CRUD API doesn't need four layers. Start with a well-organized service. Extract use cases when business logic becomes complex enough to justify the ceremony.

### 7. Thin controllers, fat domain
Routes/handlers/controllers should be thin — parse input, call use case, return response. All business logic lives in domain + application.

### 8. Composition root in one place
Dependency wiring happens in a single location (main.rs, main.go, main.ts, startup.py). No hidden DI, no globals, no init functions that create side effects.

## When to Use Clean Architecture

**Use when:**
- Project will live more than 1 year
- You expect to swap technologies (database, framework, providers)
- Business logic is complex (calculations, rules, state machines)
- More than 3 developers will work simultaneously

**Skip when:**
- CRUD with no business logic
- Prototypes and MVPs
- Small APIs (< 20 endpoints)
- Solo developer on a simple project

## Common Anti-Patterns

| Anti-Pattern | Problem | Fix |
|---|---|---|
| Anemic domain model | Entities are just data bags. Business logic scattered in services. | Put behavior in entities. `order.cancel()` not `orderService.cancelOrder(order)`. |
| Leaky abstraction | Database models appear in controllers. ORM types leak across layers. | Map at every boundary. Domain entities ≠ database models ≠ API DTOs. |
| Inverted dependency | Domain imports infrastructure (e.g., entity imports ORM decorator). | Invert: declare interface in domain, implement in infrastructure. |
| Service layer obesity | Every operation goes through a bloated `FooService` with 30 methods. | Split into individual use cases: RegisterUserUseCase, ResetPasswordUseCase. |
| Over-engineering | 15 layers for a todo list. | Start simple. Add layers when complexity justifies them. |
