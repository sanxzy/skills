# Functional Programming Paradigm

Reference for Section 3 of `architecture.md` when user selects FP.

## Core Principles

### 1. Immutability by Default
All data structures are immutable. Instead of mutating an object, create a new one with the desired changes. This eliminates entire classes of bugs related to shared mutable state and makes reasoning about code dramatically simpler.

```
# Python with dataclasses (frozen=True)
@dataclass(frozen=True)
class Order:
    id: str
    status: OrderStatus
    items: tuple[OrderItem, ...]

    def with_status(self, new_status: OrderStatus) -> 'Order':
        return Order(id=self.id, status=new_status, items=self.items)
```

### 2. Pure Functions for Business Logic
Business rules are expressed as pure functions: same input → same output, no side effects. A pure function can be tested, composed, and reasoned about in isolation.

```
// TypeScript
type CancelOrder = (order: Order) => Either<OrderError, Order>;
```

### 3. Explicit Effects
Side effects (IO, database calls, HTTP requests) are explicit in the type signatures and isolated at the boundaries. Never hide side effects inside business logic functions.

```
// Rust — Result type makes failure explicit
fn create_order(repo: &dyn OrderRepository, input: CreateOrderInput) -> Result<Order, OrderError>;
```

### 4. Function Composition over Inheritance
Build complex behavior by composing small, focused functions rather than through class hierarchies. Prefer `pipe`/`compose` patterns.

### 5. Algebraic Data Types for Domain Modeling
Model domain concepts using sum types (discriminated unions) and product types (records/structs). ADTs make invalid states unrepresentable.

```
// Haskell-like pattern in TypeScript
type OrderStatus = 
  | { kind: "pending" }
  | { kind: "confirmed"; confirmedAt: Date }
  | { kind: "shipped"; trackingNumber: string }
  | { kind: "cancelled"; reason: string };
```

## Layers in Functional Clean Architecture

### Entities (Domain) — FP Style
- **What**: Algebraic Data Types (ADTs), pure transformation functions, domain predicates.
- **Pattern**: Entities are immutable data types + pure functions that enforce invariants.
- **No classes needed**: Use records/structs/dataclasses + standalone functions.
- **Example**: An `Order` is a product type. `canBeCancelled(order: Order): boolean` is a pure function. `cancel(order: Order): Result<Order, Error>` returns a new Order.

### Use Cases (Application) — FP Style
- **What**: Functions that orchestrate domain logic and interact with ports (interfaces).
- **Pattern**: Higher-order functions. Dependencies injected as function parameters.
- **Structure**: Each use case is a standalone function: `(deps) => (input) => Result<output, error>`.
- **Example**: `makeCreateOrder(repo: OrderRepository) => (input: CreateOrderInput) => Promise<Result<Order, OrderError>>`
- **No classes**: Use factory functions or closures instead of class constructors.

### Interface Adapters — FP Style
- **What**: Functions that translate between domain types and external types.
- **Pattern**: Pure transformation functions at boundary.
- **HTTP**: `httpToDTO(req) → call use case → dtoToHttp(result)`
- **Persistence**: `domainToRow(entity) → save → rowToDomain(row)`
- **Repositories are interfaces**: Function types or traits/protocols that the domain declares.

### Frameworks & Drivers — FP Style
- **What**: Composition root. Wire concrete implementations into use case functions.
- **Pattern**: Manual function wiring in one place. No DI framework needed for small/medium projects.
- **Approach**: Create repositories, pass them to use case factories, pass use cases to route handlers.

## FP-Specific Patterns

### Result / Either Pattern
Return `Result<T, E>` or `Either<E, T>` instead of throwing exceptions. Makes error paths explicit and forces callers to handle them.

```
// Rust
fn create_order(...) -> Result<Order, OrderError>;

// Python (returns)
def create_order(...) -> Result[Order, OrderError]: ...

// TypeScript (fp-ts / effect-ts)
type CreateOrder = (...args) => Either<OrderError, Order>;
```

### Dependency Injection via Function Parameters
Pass dependencies as parameters rather than using a DI container.

```
// TypeScript — factory pattern
const makeCreateOrder = (
  repo: OrderRepository,
  eventBus: EventPublisher
) => (input: CreateOrderInput): Promise<Either<OrderError, Order>> => {
  // use repo and eventBus here
};
```

### Reader / Environment Pattern
For more complex dependency chains, the Reader monad (or equivalent) threads dependencies without explicit parameter passing.

```
// Haskell / Scala / Effect-TS
type CreateOrder = Reader<{ repo: OrderRepository; eventBus: EventPublisher }, 
                           Either<OrderError, Order>>;
```

### Tagless Final
A more advanced FP pattern where capabilities are abstracted as typeclasses/traits. Useful for effect management at scale.

## What FP Architecture Avoids
- **Mutable classes with hidden state**
- **Inheritance-based reuse** — use composition
- **Implicit side effects** — all effects are explicit
- **Mocking frameworks** — pure functions need no mocks; repository interfaces are test doubles
- **Complex ORMs** — prefer query functions over magic ORM behavior
- **Traditional MVC** — Models are pure data types, Controllers are functions, Views are render functions
