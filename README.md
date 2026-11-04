# Online Library Management System (Microservices)

Course project for **IS373TA – Microservices Architecture** (VII Sem, ISE). Built with Spring Boot 3, Spring Cloud, Docker and Kubernetes.

## Architecture

```
 Browser --> Frontend (nginx) :3000 --/api--> API Gateway :8080 --> Eureka lookup :8761
                                                    |                Config Server :8888
        +-----------+-----------+-----------+------+
      Book        Member      Lending ---> Fine      Notification
      :8081       :8082       :8083  REST   :8084      :8085
      (H2)        (H2)        (H2)          (H2)       (H2)
                               |  \           ^           ^
                               |   +--- loan.returned ----+  (RabbitMQ topic exchange
                               +------- loan.issued ------->    "library.events")
                                   Fine --- fine.assessed --->
```

Two communication styles are used on purpose:

- **Synchronous REST (OpenFeign + circuit breaker):** Lending asks Book and Member (is the member active? is a copy available?).
- **Asynchronous events (RabbitMQ):** Lending publishes `loan.issued` / `loan.returned`; Fine reacts to late returns and assesses fines by itself, then publishes `fine.assessed`; Notification consumes all events and records member messages.

| Service | Port | Responsibility | Own database |
|---|---|---|---|
| frontend | 3000 | Web UI (nginx), proxies `/api` to the gateway | – |
| config-server | 8888 | Centralised configuration (loan period, fine rate, Eureka URL) | – |
| discovery-server | 8761 | Eureka service registry | – |
| api-gateway | 8080 | Single entry point, routing, CORS | – |
| book-service | 8081 | Catalogue (40 sample books), search, copy availability | H2 `bookdb` |
| member-service | 8082 | Members (15 sample members) | H2 `memberdb` |
| lending-service | 8083 | Issue/return, due dates, event log, publishes events | H2 `lendingdb` |
| fine-service | 8084 | Fines from late-return events, manual calculation, payment | H2 `finedb` |
| notification-service | 8085 | Consumes events, stores member notifications | H2 `notificationdb` |
| rabbitmq | 5672 / 15672 | Message broker (management UI: guest/guest) | – |

Services never touch each other's database; they only use REST or events and keep foreign IDs (plus small snapshots such as book title) only.

## Sample data

On first start the system loads a dataset so every screen has content:

- `book-service/src/main/resources/books.csv`: 40 real textbook and fiction titles across 14 categories.
- `member-service/src/main/resources/members.csv`: 15 members.
- lending-service creates 8 demo loans: 2 returned on time, 2 returned late (fines are generated automatically through RabbitMQ), 2 overdue, 2 on time.

Data is in memory (H2), so it resets on every restart.

## Run it

Needs only Docker.

```bash
docker compose up --build
```

Open <http://localhost:3000> for the UI, <http://localhost:8761> for the Eureka dashboard and <http://localhost:15672> for RabbitMQ (guest/guest). The API is also reachable directly at <http://localhost:8080>. First start takes a few minutes (Maven build inside Docker).

Without Docker you need JDK 17, Maven and a local RabbitMQ: `mvn clean package`, then start config-server, discovery-server, then the rest with `java -jar <module>/target/<module>-1.0.0.jar`, and serve `frontend/public` with any static server (the UI expects `/api` on the same origin).

### Kubernetes (local, e.g. Docker Desktop / minikube)

```powershell
./build-images.ps1
kubectl apply -f k8s/library.yaml
```

The web UI is exposed on NodePort 30080 (<http://localhost:30080>).

## REST API (all through the gateway at :8080)

| Method | Path | Description |
|---|---|---|
| GET/POST | `/api/books` | List / add book |
| GET | `/api/books/search?q=` | Search by title or author |
| GET/PUT/DELETE | `/api/books/{id}` | Read / update / delete |
| GET/POST | `/api/members` | List / register member |
| GET/PUT/DELETE | `/api/members/{id}` | Read / update / delete |
| POST | `/api/loans/issue` | Body `{"bookId":1,"memberId":1}` |
| POST | `/api/loans/{id}/return` | Return a book |
| GET | `/api/loans`, `/api/loans/{id}`, `/api/loans/member/{memberId}` | Query loans |
| GET | `/api/loans/{id}/events` | Event history of a loan |
| POST | `/api/fines/calculate/{loanId}` | Compute fine (days late × rate) |
| GET | `/api/fines`, `/api/fines/member/{memberId}` | List fines (late returns create them automatically) |
| GET | `/api/notifications`, `/api/notifications/member/{memberId}` | Notifications created from events |
| POST | `/api/loans/{id}/simulate-overdue?days=20` | Demo helper: pushes a loan into the past |
| PUT | `/api/fines/{id}/pay` | Mark fine paid |

To demo a fine in the UI: Lending page, press **Make overdue** on an issued loan, then **Return** it. fine-service gets the `loan.returned` event, creates the fine and notification-service writes the message (see Fines and Notifications pages).

Resilience demo: `docker compose stop book-service`, then issue a book. The circuit breaker answers `503` instead of hanging; `docker compose start book-service` recovers it.

## Syllabus coverage

See [docs/SYLLABUS_COVERAGE.md](docs/SYLLABUS_COVERAGE.md) for the unit-by-unit mapping, and [docs/DESIGN.md](docs/DESIGN.md) for the SEED(S) design artefacts (actors, jobs, sequence diagram, event storming, service sizing).

## Project layout

```
config-server/  discovery-server/  api-gateway/  frontend/
book-service/   member-service/    lending-service/   fine-service/   notification-service/
k8s/library.yaml   docker-compose.yml   Dockerfile   .github/workflows/ci.yml   docs/
```
