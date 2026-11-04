# Syllabus Coverage – IS373TA Microservices Architecture

| Unit | Syllabus topic | Where it is in this project |
|---|---|---|
| I | What are microservices; reducing coordination costs | Five independently deployable business services plus a separate frontend, each with its own module, build and image |
| I | Team topologies / operating model | [DESIGN.md §1](DESIGN.md): stream-aligned teams per service, platform team for gateway/discovery/config |
| I | SEED(S) process: actors, JTBD, sequence diagrams, actions & queries, API spec | [DESIGN.md §2–§5](DESIGN.md) |
| I | Microservices vs APIs | REST APIs exposed via gateway; services own behaviour and data behind them |
| II | Service boundaries, DDD, event storming, sizing | [DESIGN.md §6–§7](DESIGN.md): bounded contexts Catalogue, Membership, Lending, Fines |
| II | Microservices embed their data; independent deployability | Database-per-service (H2 each), no shared tables, only IDs cross boundaries |
| II | Event-driven choreography (events between services) | RabbitMQ topic exchange `library.events`: lending publishes, fine-service and notification-service consume independently |
| II | Event sourcing and CQRS | `LoanEvent` append-only log in lending-service (write side records events) and `GET /api/loans/{id}/events` as read model |
| III | DevOps principles, IaC pipeline | `.github/workflows/ci.yml` (build, test, image build); `docker-compose.yml` and `k8s/library.yaml` as declarative infrastructure |
| III | Infrastructure components | Config server, service registry (Eureka), API gateway, circuit breakers |
| IV | Developer workspace, containerised environment, Docker | Multi-stage `Dockerfile`, `docker compose up --build` |
| IV | Kubernetes | `k8s/library.yaml` (Namespace, Deployments (2 replicas for book and member services), Services, readiness probes, NodePort) |
| IV | Designing endpoints, implementing data and code | Controllers/repositories in each service; Spring Data JPA |
| IV | Second microservice, umbrella project | Parent Maven POM `pom.xml` aggregates all modules; lending → book/member via OpenFeign |
| V | Releasing: staging, shipping containers, deploying | Images tagged `library/<svc>:1.0.0`, deployed to the `library` namespace |
| V | Managing change | Versioned images, centralised config changes without code changes, loose coupling via IDs |
| V | Measuring progress / complexity | Actuator `/actuator/health` and `/actuator/circuitbreakers` on each service |

## Course outcomes

- **CO1** – SEED(S) process, boundaries and event sourcing: DESIGN.md, `LoanEvent`.
- **CO2** – Design and implement endpoints, pipelines with Docker/Kubernetes: services, Dockerfile, compose, k8s, CI.
- **CO3** – Team structure impact: DESIGN.md §1.
- **CO4** – Scalability and maintainability: replicas in Kubernetes, database-per-service, circuit breaker, central config.

## Common viva topics, quick answers

- **Why an API gateway?** One entry point; clients do not need to know service locations; cross-cutting concerns such as CORS live there.
- **Why service discovery?** Instances change address; Eureka lets `lb://book-service` resolve at call time.
- **Why a circuit breaker?** If book-service is down, lending fails fast with 503 rather than exhausting threads.
- **How is data consistency handled?** Each service owns its data; lending records the loan and an event after the remote stock update. Full distributed transactions (sagas) are noted as future work.
