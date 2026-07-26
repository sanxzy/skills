# Object-Oriented Programming Paradigm

Reference for Section 3 of `architecture.md` when user selects OOP.

## Core Principles (SOLID)

### 1. Single Responsibility Principle (SRP)
A class should have one reason to change. Each class owns exactly one responsibility.

### 2. Open/Closed Principle (OCP)
Classes should be open for extension but closed for modification. Achieved through interfaces and composition.

### 3. Liskov Substitution Principle (LSP)
Subtypes must be substitutable for their base types. A `PostgresUserRepository` must honor the `UserRepository` contract without surprising behavior.

### 4. Interface Segregation Principle (ISP)
Many client-specific interfaces are better than one general-purpose interface. Don't force clients to depend on methods they don't use.

### 5. Dependency Inversion Principle (DIP)
Depend on abstractions, not concretions. High-level modules (business logic) should not depend on low-level modules (databases, frameworks). Both should depend on interfaces.

## Layers in OOP Clean Architecture

### Entities (Domain) — OOP Style
- **What**: Classes with encapsulated behavior. Entities carry both data and methods.
- **Pattern**: Rich domain model. Business rules are methods on entities, not external services.
- **Invariants**: Enforced in constructors and mutator methods. An entity should never be in an invalid state.
- **Identity**: Entities have identity (ID). Value objects are immutable and compared by value.
- **Example**: `Order` class has `cancel()`, `addItem()`, `canBeShipped()` methods. The class enforces: an order cannot be cancelled after shipping.

### Use Cases (Application) — OOP Style
- **What**: Classes that implement a single use case each.
- **Pattern**: Use case class with a single `execute()` method. Dependencies injected via constructor.
- **Naming**: `CreateOrderUseCase`, `CancelSubscriptionUseCase`. Each class does one thing.
- **Constructor injection**: Pass repository interfaces (and other dependencies) through the constructor.
- **Example**:
```java
public class CreateOrderUseCase {
    private final OrderRepository orderRepository;
    private final ProductRepository productRepository;

    public CreateOrderUseCase(OrderRepository orderRepo, ProductRepository productRepo) {
        this.orderRepository = orderRepo;
        this.productRepository = productRepo;
    }

    public Order execute(CreateOrderInput input) {
        // business logic here
    }
}
```

### Interface Adapters — OOP Style
- **What**: Classes that implement interfaces defined in domain/application.
- **Pattern**: Repository implementations, controllers, presenters.
- **Controllers**: Thin classes. Parse HTTP, call use case, return response. No business logic.
- **Repositories**: Implements domain repository interface. Translates between domain entities and database models.
- **Gateways**: Adapters for external services (email, payment, notifications).

### Frameworks & Drivers — OOP Style
- **What**: DI container, application bootstrap, framework configuration.
- **Pattern**: Composition root. Wire concrete implementations into use case constructors.
- **DI container** (optional): If project is large, use a DI framework. For small/medium projects, manual wiring is simpler and more debuggable.
- **Examples**: Spring `@Configuration` (Java), `tsyringe` (TypeScript), `inject` (Python), manual constructor wiring.

## OOP-Specific Patterns

### Dependency Injection via Constructor
Constructor injection is the preferred method. It makes dependencies explicit, enables easy test substitution, and makes classes self-documenting.

```java
public class ResetPasswordUseCase {
    private final UserRepository users;
    private final PasswordHasher hasher;
    private final EmailService email;

    public ResetPasswordUseCase(UserRepository users, PasswordHasher hasher, EmailService email) {
        this.users = users;
        this.hasher = hasher;
        this.email = email;
    }
}
```

### Contract-First Design
Define interfaces before implementations. The domain layer declares what it needs. Infrastructure provides how.

```csharp
// Domain — interface
public interface IOrderRepository
{
    Task<Order> GetById(OrderId id);
    Task Save(Order order);
}

// Infrastructure — implementation
public class PostgresOrderRepository : IOrderRepository { ... }
```

### Composition over Inheritance
Prefer composing objects over deep inheritance hierarchies. Use interfaces to define behavior contracts; use composition to build complex behavior from simple components.

### Encapsulation
Keep state private. Expose behavior through methods. Never expose mutable state directly. The entity controls access to its own data.

### Value Objects
Small, immutable objects that represent concepts (Email, Money, Address). Defined by their attributes, not identity. Equality is structural.

```java
public class Email {
    private final String value;

    public Email(String value) {
        if (!value.contains("@")) throw new InvalidEmailException(value);
        this.value = value;
    }
    // value object — no setter, no ID
}
```

## What OOP Architecture Avoids
- **Anemic domain model** — entities with only getters/setters, no behavior
- **God objects** — classes that do everything
- **Deep inheritance trees** — prefer interfaces + composition
- **Service layer accumulation** — avoid generic `FooService` with 30 methods; use single-responsibility use cases
- **Framework invasion of domain** — no ORM annotations on domain entities
- **Circular dependencies** — if A needs B and B needs A, extract a shared interface
