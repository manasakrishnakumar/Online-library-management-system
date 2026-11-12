# Online Library Management System (Microservices)

Course project for **IS373TA - Microservices Architecture** (VII Sem, ISE). Built with Spring Boot 3, Spring Cloud, PostgreSQL, RabbitMQ, Docker and Kubernetes manifests.
The full project report (Word, same layout as the college template) is in [report/Online_Library_Management_System_Report.docx](report/Online_Library_Management_System_Report.docx), with a PDF copy next to it.

## Architecture

```
 Browser --> Frontend (nginx) :3000 --/api--> API Gateway :8080  (JWT login, role rules, routing)
                                                  |   Eureka :8761   Config Server :8888
        +-----------+-----------+-----------+-----+
      Book        Member      Lending ---> Fine      Notification        PostgreSQL: one database
      :8081       :8082       :8083  REST   :8084      :8085            and one login per service
      bookdb      memberdb    lendingdb     finedb     notificationdb
                               |  \            ^           ^
                               |   +-- loan.returned ------+     RabbitMQ topic exchange "library.events"
                               +------ loan.issued -------->      (events leave through a transactional outbox)

 Zipkin :9411 (traces)    Prometheus :9090 -> Grafana :3001 (metrics, provisioned dashboard)
```

Two communication styles are used on purpose:

- **Synchronous REST (OpenFeign + circuit breaker):** the lending saga asks Member (is the member active?) and Book (reserve a copy, with an idempotency key).
- **Asynchronous events (RabbitMQ):** Lending publishes `loan.issued` / `loan.returned` through an outbox; Fine reacts to late returns and assesses fines by itself, then publishes `fine.assessed`; Notification consumes all events and ignores duplicates.

| Service | Port | Responsibility | Own database |
|---|---|---|---|
| frontend | 3000 | Web UI (nginx): login, dashboard, book-cover grid, librarian and member views | - |
| api-gateway | 8080 | Routing, `POST /api/auth/login`, JWT check, role rules | - |
| config-server | 8888 | Shared configuration (loan period, fine rate, tracing, metrics) | - |
| discovery-server | 8761 | Eureka service registry | - |
| book-service | 8081 | Catalogue (10,000 books), search, copies, idempotent stock changes | PostgreSQL `bookdb` |
| member-service | 8082 | Members (15 sample members) | PostgreSQL `memberdb` |
| lending-service | 8083 | Issue/return saga, event log, outbox relay, recovery job | PostgreSQL `lendingdb` |
| fine-service | 8084 | Fines from late-return events, manual calculation, payment | PostgreSQL `finedb` |
| notification-service | 8085 | Notification messages from events | PostgreSQL `notificationdb` |
| postgres, rabbitmq, zipkin, prometheus, grafana | 5432 (internal), 5672/15672, 9411, 9090, 3001 | Infrastructure | - |

Services never touch each other's database (each login can only open its own); they use REST or events and keep foreign IDs plus small snapshots (book title, member name).

## Run it

Needs only Docker.

```bash
docker compose up --build
```

First start takes a few minutes (Maven build inside Docker). After the images exist, the whole system including the data is ready about 110 seconds after `docker compose up` (measured). Then open:

| URL | What |
|---|---|
| http://localhost:3000 | The application (sign in below) |
| http://localhost:8761 | Eureka dashboard |
| http://localhost:9411 | Zipkin: find a trace after using the app |
| http://localhost:3001 | Grafana dashboard "Online Library: service overview" (anonymous viewer; admin/admin to edit) |
| http://localhost:9090/targets | Prometheus targets |
| http://localhost:15672 | RabbitMQ console (guest/guest) |
| http://localhost:8083/swagger-ui.html | Swagger UI per service (ports 8081 to 8085, loopback only) |

**Demo accounts** (defined in `api-gateway/src/main/resources/application.yml`, for local use only):

| Username | Password | Role |
|---|---|---|
| `librarian` | `librarian123` | LIBRARIAN: everything |
| `asha.rao@example.com` | `member123` | MEMBER (member id 1): browse catalogue, own loans, fines, notifications |
| `ravi.kumar@example.com`, `priya.nair@example.com` | `member123` | MEMBER (ids 2 and 3) |

Data lives in the Docker volume `pgdata`. Reset everything with `docker compose down -v`.

Without Docker you need JDK 17, Maven, PostgreSQL (or the in-memory H2 default), RabbitMQ and Zipkin: `mvn clean package`, start config-server, discovery-server, then the rest with `java -jar <module>/target/<module>-1.0.0.jar`, and serve `frontend/public` with a server that proxies `/api` to the gateway.

### Kubernetes (minikube, verified)

Stop the Compose stack first (both together need more memory than a laptop usually gives Docker), then:

```powershell
minikube start --driver=docker --memory=9000 --cpus=6
./build-images.ps1                       # builds library/<name>:1.0.0 (or retag the Compose images)
foreach ($m in "config-server","discovery-server","api-gateway","book-service","member-service","lending-service","fine-service","notification-service","frontend") { minikube image load "library/${m}:1.0.0" }
kubectl apply -f k8s/library.yaml
kubectl get pods -n library              # all 14 pods ready after about 5 minutes
kubectl port-forward -n library svc/frontend 3000:80    # then open http://localhost:3000
```

`k8s/library.yaml` is generated by `k8s/generate_manifests.py` (12 Deployments and Services, a Secret for the JWT key, a ConfigMap for the database script; every JVM has its heap capped with `JAVA_TOOL_OPTIONS`). Verified on a single-node minikube cluster on 12 November 2026: all 14 pods ready, login, 10,000 books, demo loans and fines, 401 without a token, issuing a loan. Some pods restart once or twice while starting because the manifests have no start-order control (the services come up before the config server); Kubernetes restarts them and they settle. With less than about 9 GB for minikube the pods starve. Prometheus and Grafana are Compose-only; multi-node behaviour and autoscaling were not tested.

## Security

- `POST /api/auth/login` returns an HS256 JWT (60 minutes) carrying the role and, for members, the member id. Passwords are BCrypt-hashed in memory at start-up.
- The gateway verifies the token on every other `/api` call: no token or a bad token gives 401, a role that may not do the operation gives 403.
- Members may only read the catalogue and their own loans, fines and notifications. The stock endpoints `PUT /api/books/{id}/borrow|return` are internal: blocked for everybody at the gateway; only the lending saga calls them (directly, through Eureka).
- The business-service ports are published on `127.0.0.1` for Swagger and demos; in a real deployment they must only be reachable from the gateway.

## Consistency: saga and outbox

Issuing a book is an orchestrated saga in lending-service: save the loan as `PENDING`, reserve a copy in book-service (idempotency key `loan-{id}-borrow`), then mark it `ISSUED` and write an outbox row in one transaction. A 4xx answer fails the loan (`FAILED`); an unknown outcome leaves it `PENDING` (HTTP 202) and a recovery job replays the same keyed step; a failing last step releases the copy (compensation). The outbox relay publishes events to RabbitMQ at least once, and consumers ignore duplicates. Details and experiments: report Chapters 4 and 6.

## REST API (through the gateway at :8080, with `Authorization: Bearer <token>`)

| Method | Path | Description |
|---|---|---|
| POST | `/api/auth/login` | Body `{"username":"..","password":".."}` |
| GET/POST | `/api/books` | List / add book (add: librarian) |
| GET | `/api/books/search?q=` | Search by title or author |
| GET/PUT/DELETE | `/api/books/{id}` | Read / update / delete |
| GET/POST | `/api/members` | List / register member (librarian) |
| GET/PUT/DELETE | `/api/members/{id}` | Read / update / delete |
| POST | `/api/loans/issue` | Body `{"bookId":1,"memberId":1}`; 201 issued, 202 pending, 409 rejected |
| POST | `/api/loans/{id}/return` | Return a book |
| GET | `/api/loans`, `/api/loans/{id}`, `/api/loans/member/{memberId}` | Query loans |
| GET | `/api/loans/{id}/events` | Event history of a loan |
| POST | `/api/loans/{id}/simulate-overdue?days=20` | Demo helper: pushes a loan into the past |
| POST | `/api/fines/calculate/{loanId}` | Compute fine (days late x rate) |
| GET | `/api/fines`, `/api/fines/member/{memberId}` | List fines (late returns create them automatically) |
| PUT | `/api/fines/{id}/pay` | Mark fine paid |
| GET | `/api/notifications`, `/api/notifications/member/{memberId}` | Notifications created from events |

To demo a fine: Lending page, **Make overdue** on an issued loan, then **Return**. fine-service gets `loan.returned`, creates the fine, and notification-service writes the message.

## Sample data

On first start the system loads real data:

- `book-service/src/main/resources/books.csv`: **10,000 real books** from the public **Goodbooks-10k** dataset (https://github.com/zygmuntz/goodbooks-10k, also on Kaggle): titles, authors, ISBNs. The dataset has no genre, so the category column holds the publication era; copies per title (1 to 5) are generated. Please check the dataset repository's licence and credit it when you present the project.
- `member-service/src/main/resources/members.csv`: 15 members.
- lending-service creates 8 demonstration loans through the real saga (2 returned on time, 2 returned late so fines appear, 2 overdue, 2 on time).

## Tests, experiments and measurements

- **23 unit tests** (gateway 9, book 5, lending 7, fine 2): `mvn test`, or Docker only:
  `docker run --rm -v "%cd%:/src" -w /src maven:3.9-eclipse-temurin-17 mvn -B -s maven-settings.xml test`
- `report/experiments.py`: seven fault-injection experiments (broker down, book-service down, rejection, idempotency, duplicate delivery, trace, circuit breaker) against the running stack.
- `report/measure.py`: latency, throughput, event delay, outage behaviour. Results are in `report/results/`; `report/make_figs.py` draws the charts; `report/build_report.py` builds the Word report from them (it needs Microsoft Word only for `to_pdf.ps1`, which reads the real page numbers).
- OpenAPI documents of all services: [docs/openapi](docs/openapi).

## Documents

[docs/SYLLABUS_COVERAGE.md](docs/SYLLABUS_COVERAGE.md) maps every syllabus unit to the project; [docs/DESIGN.md](docs/DESIGN.md) has the SEED(S) design artefacts; the Word report ties everything together with measured figures.

## Project layout

```
config-server/  discovery-server/  api-gateway/  frontend/
book-service/   member-service/    lending-service/   fine-service/   notification-service/
docker-compose.yml  Dockerfile  maven-settings.xml  infra/postgres/init.sql  monitoring/  k8s/  .github/workflows/ci.yml
docs/  report/ (report builder, measurements, figures, screenshots, Word report)
```
