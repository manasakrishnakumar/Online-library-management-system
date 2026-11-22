"""The demo script, shared by the one-page Word document, docs/DEMO_SCRIPT.md and Appendix C of the report."""

# (step, what to do, what it shows / what to say)
STEPS = [
    ("1", "Start the system: docker compose up -d (set GATEWAY_PORT=18080 first if port 8080 is busy). Open http://localhost:3000.",
     "Everything, including the 10,000-book catalogue and the demo loans, is ready about two minutes after the command."),
    ("2", "Sign in as librarian / librarian123.",
     "JWT login at the gateway; the menu depends on the role."),
    ("3", "Dashboard.",
     "Counts come from four services: titles and copies (book), members, loans (lending), fines (fine)."),
    ("4", "Books: search \"tolkien\", then switch Grid to Table.",
     "Search and paging run on the server (GET /api/books/page); the browser never downloads all 10,000 books."),
    ("5", "Lending: Issue a book (type \"hobbit\"), choose a member, Issue. Then press History on the new loan.",
     "The saga trail: LOAN REQUESTED, BOOK ISSUED. Stock was reserved in the book service with an idempotency key."),
    ("6", "Press Make overdue on that loan, then Return. Open Fines, then Notifications.",
     "A late return makes fine-service create a fine by itself (2 rupees per day) and notification-service write the message: asynchronous events over RabbitMQ."),
    ("7", "Open Zipkin (http://localhost:9411), Run Query, open the POST /api/loans/issue trace.",
     "One request across gateway, lending, member and book, with the time spent in each."),
    ("8", "Open Grafana (http://localhost:3001).",
     "Business counters (loans issued, fines, notifications), p95 latency, circuit-breaker state, JVM heap."),
    ("9", "Break RabbitMQ: docker compose stop rabbitmq. Issue a book (still succeeds). Look at the Grafana panel Outbox events waiting. Then docker compose start rabbitmq.",
     "Transactional outbox: the event waits in the database and is delivered after the broker returns; the notification appears; nothing is lost."),
    ("10", "Break the book service: docker compose stop book-service. Issue a book: the UI says Accepted, the loan is Pending. Then docker compose start book-service and refresh Lending.",
     "Saga: the request is accepted for later completion; the recovery job finishes it with the same idempotency key, so exactly one copy is taken."),
    ("11", "Sign out, sign in as asha.rao@example.com / member123.",
     "Member view: read-only catalogue, only own loans, fines and notifications. The gateway answers 403 for anything else."),
    ("12", "Optional: kubectl get pods -n library (after minikube start and kubectl apply -f k8s/library.yaml).",
     "The same system on Kubernetes: init containers give the start order; Prometheus and Grafana run in the cluster too."),
]

TIPS = [
    "Reset all data: docker compose down -v, then docker compose up -d.",
    "If a service is slow after a restart, wait about a minute: Eureka and the load balancer need time to learn the new address.",
    "Stop everything when finished: docker compose stop (Docker Desktop restarts old containers by itself after a restart).",
    "Ten minutes is enough for steps 1 to 11; step 12 needs a few more.",
]
