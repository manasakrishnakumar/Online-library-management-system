"""Chapters 6 and 7, references and appendices."""
import csv
import statistics

from data import (COLD, DS, HW, OPS, cyc, cyc0, exp, f, fine_ms, fine_ms0, images, issue0, issue_ms, lat, lat0, loc, memory, note_ms, note_ms0, out_after,
                  out_before, return0, return_ms, startup, thr, thr0, ROOT)

peak = max(thr, key=lambda r: r["rps"])
peak0 = max(thr0, key=lambda r: r["rps"])
ep = [k for k in lat if k.startswith("GET /api") and "10,000" not in k]
med_delta = [lat[k]["p50"] - lat0[k]["p50"] for k in ep]
d, g = lat["direct GET /api/members/1 (:8082)"], lat["gateway GET /api/members/1"]
E1, E2, E3, E4, E5, E6, E7 = (exp[k] for k in ("E1_outbox", "E2_saga_outage", "E3_rejection", "E4_idempotency", "E5_duplicates", "E6_trace", "E7_rejections"))
slow_b = [x for x in out_before["during_outage"] if x["ms"] > 1000]
slow_a = [x for x in out_after["during_outage"] if x["ms"] > 1000]
fast_a = [x["ms"] for x in out_after["during_outage"] if x["ms"] < 1000 and x["status"] == 202]
mean = statistics.mean

CH6 = [
    ("h2", "CHAPTER 6:  RESULTS AND ANALYSIS"),
    ("p", "This chapter reports what the finished system does. Section 6.1 shows the functional behaviour and security with live screenshots, Section 6.2 the performance measurements, Section 6.3 the fault-injection experiments, Section 6.4 the observability evidence, Section 6.5 the deployment on Kubernetes, and Sections 6.6 to 6.8 summarise the contributions and analyse the results. Everything was measured on one machine: " + f"{HW['cpu']}, {HW['threads']} threads, {HW['ram']} memory, {HW['os']}, running all fourteen containers and the test client together. The numbers are therefore indications of behaviour, not capacity figures for production."),
    ("h3", "6.1  Results: Functional Verification and Screenshots"),
    ("h5", "6.1.1  Security, isolation and demonstration data"),
    ("p", "{tab:live} lists the checks made against the running system on 4 and 5 November 2026 and their outcomes. All behaved as designed."),
    ("table", ["Check", "Expected", "Observed"], [
        ["GET /api/books without a token", "401", "401"],
        ["GET /api/books with a forged token", "401", "401, message: Invalid or expired token"],
        ["Login with a wrong password", "401", "401"],
        ["Librarian calls PUT /api/books/1/borrow", "403 (internal endpoint)", "403"],
        ["Member reads GET /api/books/1", "200", "200"],
        ["Member reads own loans, /api/loans/member/1", "200", "200"],
        ["Member reads another member's loans, /api/loans/member/2", "403", "403"],
        ["Member calls /api/members, /api/loans or POST /api/books", "403", "403, 403, 403"],
        ["Databases created", "five, one per service", "bookdb, memberdb, lendingdb, finedb, notificationdb, each with its own owner"],
        ["Rows in bookdb.book (as bookuser)", f"{DS['n']:,}", f"{DS['n']:,}"],
        ["lendinguser reads bookdb.book", "refused", "ERROR: permission denied for table book"],
        ["Demonstration loans after a clean start", "8 (4 issued, 4 returned)", "8 (4 ISSUED, 4 RETURNED)"],
        ["Outbox rows after a clean start", "12, all delivered", "12 of 12 sent"],
        ["Fines created by the two late returns", "32 and 8 rupees", "Karthik Reddy 16 days, 32.00; Divya Shetty 4 days, 8.00"],
        ["Prometheus targets", "6 up", "6 of 6 up"],
        ["Services visible in Zipkin", "6", "api-gateway, book, member, lending, fine, notification"],
    ], "Live checks of security, isolation and demonstration data", "live"),
    ("h5", "6.1.2  Application pages"),
    ("p", "{fig:login} shows the login page. After login, the librarian sees the dashboard ({fig:dash}): 10,000 titles, 29,996 of 30,000 copies available because four copies are on loan, 15 members, two overdue loans and 40 rupees of unpaid fines. The Books page ({fig:books}) shows the Goodbooks-10k catalogue as a grid of generated book covers, with a Table view, search and pagination; the librarian additionally sees Add, Edit and Delete. All application screenshots in this section were taken from the system running on the Kubernetes cluster of Section 6.5."),
    ("fig", "shots/login.jpg", "Login page of the web application", 4.6, "login"),
    ("fig", "shots/dashboard.jpg", "Librarian dashboard with counts taken from four services", 5.4, "dash"),
    ("fig", "shots/books.jpg", "Books page in grid view: the Goodbooks-10k catalogue with availability per title (librarian view)", 5.4, "books"),
    ("p", "The Lending page ({fig:lending}) lists every loan with its status. Issue, Return, Fine, History and, for the demonstration, Make overdue are available. The History button opens the event log of a loan ({fig:history}); the loan shown went through LOAN REQUESTED, BOOK ISSUED and BOOK RETURNED, which is the saga trail described in Chapter 4."),
    ("fig", "shots/lending.jpg", "Lending page with overdue, issued and returned loans", 5.4, "lending"),
    ("fig", "shots/history.jpg", "History of loan 6: the event log of the saga", 5.4, "history"),
    ("p", "The Fines page ({fig:fines}) shows the two fines that the fine service created by itself after reading loan.returned events, and the Notifications page ({fig:notes}) shows the messages created by the notification service for the issues, returns and fines. The Members page ({fig:members}) and the System page ({fig:system}), which checks every service through the gateway, complete the librarian's view."),
    ("fig", "shots/fines.jpg", "Fines created automatically from late returns", 5.4, "fines"),
    ("fig", "shots/notifications.jpg", "Notifications created from events by notification-service", 5.4, "notes"),
    ("fig", "shots/members.jpg", "Members page", 5.4, "members"),
    ("fig", "shots/system.jpg", "System status: every service checked through the gateway", 5.4, "system"),
    ("p", "A member who signs in sees a different application. The catalogue is read-only ({fig:mbooks}), and the pages My loans ({fig:mloans}) and My notifications ({fig:mnotes}) show only the records of that member; the same restriction is enforced by the gateway, not only by the interface, as {tab:live} shows."),
    ("fig", "shots/member_books.jpg", "Member view: the catalogue without add, edit or delete", 5.4, "mbooks"),
    ("fig", "shots/member_loans.jpg", "Member view: own loans only", 5.4, "mloans"),
    ("fig", "shots/member_notes.jpg", "Member view: own notifications only", 5.4, "mnotes"),
    ("h5", "6.1.3  Infrastructure consoles"),
    ("p", "{fig:eureka} shows the Eureka registry with the registered services, {fig:swagger} the Swagger UI generated by springdoc for the lending service, and {fig:rabbit} the two durable queues of the topic exchange, which are empty because every event has been consumed."),
    ("fig", "shots/eureka.jpg", "Eureka registry showing the registered services", 5.2, "eureka"),
    ("fig", "shots/swagger.jpg", "Swagger UI of the lending service generated from the code", 5.2, "swagger"),
    ("fig", "shots/rabbitmq.jpg", "RabbitMQ queues fine.loan-returned and notification.all-events", 5.2, "rabbit"),
    ("h3", "6.2  Benchmarking and Analysis"),
    ("h5", "6.2.1  Method"),
    ("p", "A Python client on the same machine signs in as the librarian and sends requests through the gateway. For each endpoint 10 warm-up requests are discarded and then 200 requests are timed one after the other (30 for the 10,000-row catalogue download). Throughput is measured with 1 to 32 client threads for six seconds each against a single-record read. Thirty complete business cycles (issue, make overdue, return, then wait until the fine and the notification are visible) measure the event path. The same scripts were run on the first version of the system (in-memory H2 databases, no login, no tracing) and on the final version (PostgreSQL, JWT, tracing at 100 percent), so the cost of the additions can be read directly."),
    ("h5", "6.2.2  Latency"),
    ("table", ["Endpoint through the gateway", "Samples", "Mean (ms)", "p50 (ms)", "p95 (ms)", "p99 (ms)", "Max (ms)"], [
        [k.replace("GET ", ""), str(v["n"]), f(v["mean"]), f(v["p50"]), f(v["p95"]), f(v["p99"]), f(v["max"])] for k, v in lat.items() if k.startswith("GET /api") or k.startswith("gateway")
    ] + [["direct to member-service (:8082), /api/members/1", str(d["n"]), f(d["mean"]), f(d["p50"]), f(d["p95"]), f(d["p99"]), f(d["max"])]], "Latency of read requests in the final system", "lat"),
    ("p", f"Single-record reads and small lists take about {f(min(lat[k]['p50'] for k in ep))} to {f(max(lat[k]['p50'] for k in ep))} ms at the median and stay below {f(max(lat[k]['p95'] for k in ep))} ms at the 95th percentile, so the design goal of 100 ms is met with a wide margin. The search for \"potter\" is slower because the book service scans 10,000 rows with a case-insensitive match. Downloading the full catalogue ({lat['GET /api/books (10,000 rows)']['p50']:.0f} ms median) returns about 1.6 MB; the front end does this once per visit and filters in the browser, a choice that would not scale to a much larger catalogue."),
    ("fig", "assets/perf_latency.png", "Median and 95th-percentile latency through the gateway", 4.8, "lat"),
    ("p", f"The gateway adds about {f(g['p50'] - d['p50'])} ms at the median ({f(d['p50'])} ms direct, {f(g['p50'])} ms through the gateway), which includes the token check and the routing."),
    ("h5", "6.2.3  Cost of PostgreSQL, login and tracing"),
    ("p", f"{{fig:cmp}} compares the median latency of the first version with the final version. The additions raised the median by {f(min(med_delta))} to {f(max(med_delta))} ms ({f(mean(med_delta))} ms on average over the six endpoints), a small price for persistent data, authentication and a trace for every request."),
    ("fig", "assets/perf_compare.png", "Median latency before and after PostgreSQL, JWT and tracing", 4.8, "cmp"),
    ("h5", "6.2.4  Throughput"),
    ("table", ["Client threads", "Requests in 6 s", "Errors", "Requests per second (final)", "Requests per second (first version)"], [
        [str(r["workers"]), str(r["requests"]), str(r["errors"]), f(r["rps"], 0), f(b["rps"], 0)] for r, b in zip(thr, thr0)
    ], "Throughput of GET /api/books/1 through the gateway", "thr"),
    ("p", f"Throughput grows with the number of threads up to about eight and then flattens at {f(peak['rps'], 0)} requests per second ({f(peak0['rps'], 0)} for the first version), because the test client, the gateway and all services share the same {HW['threads']} threads. No request failed at any level. The goal of 300 requests per second is met."),
    ("fig", "assets/perf_throughput.png", "Throughput against the number of client threads", 4.6, "thrfig"),
    ("h5", "6.2.5  The event path: from a return to a fine and a notification"),
    ("table", ["Measure", "Final system (outbox, 300 ms relay)", "First version (event after commit)"], [
        ["Fine visible after the return call, mean / min / max (ms)", f"{f(mean(fine_ms))} / {f(min(fine_ms))} / {f(max(fine_ms))}", f"{f(mean(fine_ms0))} / {f(min(fine_ms0))} / {f(max(fine_ms0))}"],
        ["Notification visible, mean / min / max (ms)", f"{f(mean(note_ms))} / {f(min(note_ms))} / {f(max(note_ms))}", f"{f(mean(note_ms0))} / {f(min(note_ms0))} / {f(max(note_ms0))}"],
        ["Issue call, mean (ms)", f(mean(issue_ms)), f(mean(issue0))],
        ["Return call, mean (ms)", f(mean(return_ms)), f(mean(return0))],
        ["Cycles completed with fine and notification", f"{sum(1 for x in cyc if x['fine_visible_ms'] and x['notification_visible_ms'])} of {len(cyc)}", "30 of 30"],
    ], "Event path of 30 business cycles", "evt"),
    ("p", f"All thirty cycles produced both the fine and the notification. The path is asynchronous, yet on average the fine is visible {f(mean(fine_ms))} ms and the notification {f(mean(note_ms))} ms after the return call. The final system is slower on this path than the first version ({f(mean(fine_ms0))} and {f(mean(note_ms0))} ms) because the relay polls the outbox every 300 milliseconds instead of publishing immediately; this is the price of never losing an event. An issue now takes {f(mean(issue_ms))} ms instead of {f(mean(issue0))} ms because the saga performs two local transactions and the remote calls carry trace headers."),
    ("fig", "assets/perf_events.png", "Delay between the return call and the visible fine and notification", 4.8, "evtfig"),
    ("h5", "6.2.6  Start-up time, memory and image size"),
    ("table", ["Module", "Start-up when all start together (s)"], [[k, f(v)] for k, v in sorted(startup.items(), key=lambda kv: kv[1])], "Spring Boot start-up time on a clean start", "start"),
    ("fig", "assets/sys_startup.png", "Start-up time of the Java services", 4.6, "startfig"),
    ("p", f"The slowest service is ready after {f(max(startup.values()))} seconds. A separate cold-start test (docker compose down -v, then docker compose up -d with the images already built) measured when the system became usable: the gateway accepted logins after {f(COLD['gateway_login_ok_s'], 0)} s, and the catalogue of {DS['n']:,} books, the eight demonstration loans and the two fines were all present after {f(COLD['fines_2_s'], 0)} s, which meets the goal of two minutes."),
    ("table", ["Container", "Idle memory (MiB)", "Image size"], [
        [k, f(v, 0), images.get(k, "-")] for k, v in sorted(memory.items(), key=lambda kv: -kv[1])
    ], "Memory of the containers after start-up (docker stats) and image size", "mem"),
    ("fig", "assets/sys_memory.png", "Idle memory of the containers", 4.6, "memfig"),
    ("p", f"The Java services use between {f(min(memory[k] for k in ('book-service', 'member-service', 'api-gateway', 'notification-service')), 0)} and {f(memory['lending-service'], 0)} MiB each; the fourteen containers together use {f(sum(memory.values()), 0)} MiB. This is the cost of running every service in its own Java virtual machine, one of the trade-offs of the style discussed in Section 6.7."),
    ("h3", "6.3  Fault Tolerance and Consistency"),
    ("p", "Seven experiments, run by report/experiments.py on a freshly started system, inject a fault and check an invariant. {tab:exp} summarises them; each passed."),
    ("table", ["ID", "Fault injected", "Expected", "Observed", "Result"], [
        ["E1", "RabbitMQ stopped, 5 loans issued, RabbitMQ started again", "Loans accepted; events kept; all delivered later", f"statuses {sorted(set(E1['http_status']))}; {E1['outbox_pending_during_outage']} events waited in the outbox; outbox empty {f(E1['seconds_until_outbox_empty_after_broker_restart'])} s after the restart; {E1['notifications_created']} notifications created", "pass"],
        ["E2", "book-service stopped while a loan is issued", "Loan accepted as pending; completed after recovery; stock reduced once", f"HTTP {E2['http_status_during_outage']}, status {E2['loan_status_when_accepted']} after {f(E2['seconds_to_accept'])} s; ISSUED {f(E2['seconds_until_issued_after_book_service_restart'])} s after the restart; copies {E2['copies_before']} to {E2['copies_after']}; events {', '.join(E2['events'])}", "pass"],
        ["E3", "Second request for the only copy of a book", "Rejected; no side effect", f"first {E3['first_status']}, second {E3['second_status']} ({E3['second_message']}); loan {E3['loan_state']}; copies stay {E3['copies_after_second']}; events {', '.join(E3['events'])}", "pass"],
        ["E4", "Same idempotency key sent 3 times to the book service", "Stock changes once", f"copies {E4['copies_before']} to {E4['copies_after']} (decrease of {E4['decrement']})", "pass"],
        ["E5", "3 outbox rows marked unsent and relayed again", "No duplicate notifications", f"notifications {E5['notifications_before']} before, {E5['notifications_after']} after", "pass"],
        ["E6", "One POST /api/loans/issue", "One trace across the services", f"trace with {E6['spans']} spans in {len(E6['services'])} services ({', '.join(E6['services'])}), {f(E6['duration_ms'])} ms", "pass"],
        ["E7", "12 business rejections in a row, then a valid request", "Breaker stays closed; valid request succeeds", f"{E7['rejected_count']} rejections (status {E7['rejected_statuses'][0]}), then {E7['next_valid_request_status']}", "pass"],
    ], "Fault-injection experiments", "exp"),
    ("fig", "assets/exp_times.png", "Times measured in experiments E1 and E2", 4.6, "exptimes"),
    ("p", f"E1 shows the outbox at work: while the broker was down the five issue calls still returned 201, the five events were safe in the lending database, and every one of them reached the consumers within {f(E1['seconds_until_outbox_empty_after_broker_restart'], 0)} seconds of the broker's return (this includes the time the broker itself needed to start again). E2 shows the saga: the call returned after {f(E2['seconds_to_accept'], 1)} seconds, which is the Feign connect timeout, with status 202; when the book service came back the recovery job completed the loan, and because of the idempotency key exactly one copy was taken. E3 and E7 show that a refused request leaves no trace except the FAILED loan record, and that refusals do not disturb the circuit breaker."),
    ("h5", "6.3.1  Behaviour with the book service stopped, before and after the fixes"),
    ("p", f"{{fig:outage}} compares the first version with the final version while the book service was stopped and requests were sent twice per second. In the first version the first calls took {', '.join(f(x['ms'] / 1000, 1) for x in slow_b[:3])} seconds each before the circuit breaker opened, every request was answered 503, and after the restart the first success came {f(out_before['first_success_s'] - out_before['restart_at_s'], 0)} seconds later. In the final version the slow calls take about {f(mean([x['ms'] for x in slow_a[:3]]) / 1000, 1)} seconds (the shorter timeout), the breaker then answers in about {f(mean(fast_a), 0)} ms with status 202 (accepted, pending), and the loans created during the outage are completed by the recovery job after the restart. The first synchronous success (201) in this test came {f(out_after['first_success_s'] - out_after['restart_at_s'], 0)} seconds after the restart; this is dominated by the start-up of the book service and by the time the registry and the load balancer need to learn the new address, not by the saga."),
    ("fig", "assets/perf_outage.png", "Response time of issue requests while the book service is stopped (first version and final version)", 5.6, "outage"),
    ("h3", "6.4  Observability Evidence"),
    ("p", f"{{fig:trace}} shows the trace of experiment E6 in Zipkin: the call enters at the gateway, passes to the lending service, which calls the member service and then the book service, {E6['spans']} spans and {f(E6['duration_ms'])} ms in total. The time of the lending span that is not covered by its two child calls was spent inside the lending service itself, outside the two remote calls (database work and the saga logic)."),
    ("fig", "shots/zipkin_trace.jpg", "Zipkin: one POST /api/loans/issue across four services", 5.4, "trace"),
    ("p", "{fig:prom} shows that Prometheus scrapes all six Spring Boot applications every five seconds, and {fig:grafana} the provisioned Grafana dashboard. The six counters at the top are business metrics registered by the services; the screenshot was taken after the experiments of Section 6.3, so the counters include the experiment traffic (18 loans issued, 5 returned, 2 fines, 25 notifications, none pending and no event waiting in the outbox). The time series show the request rate and the 95th-percentile response time per service, the 5xx rate of the gateway (the short spike belongs to the outage experiments), the state of the three circuit breakers and the heap of every service."),
    ("fig", "shots/prom_targets.jpg", "Prometheus targets: six of six up", 5.2, "prom"),
    ("fig", "shots/grafana.jpg", "Grafana dashboard Online Library: service overview", 5.4, "grafana"),
    ("h3", "6.5  Deployment on Kubernetes"),
    ("p", "The manifests of Section 4.4.6 were applied to a single-node minikube cluster on the same laptop (minikube 1.39.0 with the Docker driver, 6 processors, 9,000 MB of memory, Kubernetes v1.37.0 on containerd 2.3.4), after the Compose stack had been stopped. The nine images built for this project were loaded into the cluster with minikube image load; PostgreSQL, RabbitMQ and Zipkin were pulled by the cluster. kubectl apply created 27 objects: one namespace, one secret, one config map, twelve deployments and twelve services."),
    ("p", "All 14 pods (the book and member services run two replicas each) were running and ready about five minutes after the apply command; {tab:pods} lists them as they were when the last one became ready. Seven of the fourteen pods restarted once or twice while starting. The manifests contain no start-order control, so the first start-up attempt of a service happened before the config server accepted connections (the log shows Connection refused for http://config-server:8888), the container exited and Kubernetes started it again. This is the self-healing the platform is designed to provide; init containers or start-up probes would avoid the restarts."),
    ("table", ["Pod (deployment)", "Ready", "Restarts"], [
        ["api-gateway", "1/1", "0"], ["book-service (2 replicas)", "1/1 and 1/1", "2 and 1"], ["config-server", "1/1", "0"], ["discovery-server", "1/1", "0"],
        ["fine-service", "1/1", "1"], ["frontend", "1/1", "0"], ["lending-service", "1/1", "1"], ["member-service (2 replicas)", "1/1 and 1/1", "1 and 1"],
        ["notification-service", "1/1", "1"], ["postgres", "1/1", "0"], ["rabbitmq", "1/1", "0"], ["zipkin", "1/1", "0"],
    ], "Pods of the library namespace when all were ready", "pods"),
    ("p", "Through a port-forward to the front-end service the same functional checks as in Section 6.1 were repeated against the cluster. The login returned a token, the catalogue contained 10,000 books (loaded into the PostgreSQL pod by the book service), the lending service had created the eight demonstration loans and the fine service the two fines, a request without a token returned 401, and a new loan for a member was issued with status ISSUED and returned again. The application screenshots of Section 6.1.2 were taken from this cluster; the infrastructure consoles of Sections 6.1.3 and 6.4 are from the Compose stack, which also runs Prometheus and Grafana."),
    ("p", "The first deployment attempt failed for resource reasons and is worth recording. After a restart, minikube came up with only about 5.4 GB of memory while the old Compose containers also restarted by themselves, so fourteen Java pods and a second complete stack competed for processor and memory; the Kubernetes API server timed out and no pod was ready after 51 minutes. After stopping the Compose stack, recreating the cluster with 9,000 MB and capping the heap of every JVM with JAVA_TOOL_OPTIONS (256 MB for the services, 192 MB for the config and registry servers) in the manifests, all pods were ready within about five minutes (defect D12). The cluster has one node, so scheduling across nodes, load balancing between nodes and autoscaling were not exercised, and no performance figures were taken on Kubernetes."),
    ("h3", "6.6  Contributions"),
    ("bullets", [
        f"A complete, runnable microservices system with {len(OPS)} documented operations, eight Java modules, a web front end and fourteen containers, started with one command.",
        f"A real catalogue of {DS['n']:,} books loaded into PostgreSQL, with one database and one login per service, verified by a refused cross-database read.",
        "JWT login with librarian and member roles enforced at the gateway, with internal endpoints blocked, covered by nine unit tests and live checks.",
        "A saga with compensation, idempotency keys and a recovery job, a transactional outbox and duplicate-safe consumers, verified by seven fault-injection experiments.",
        "Traces, metrics and a provisioned dashboard, including business counters.",
        "A measured comparison of the first and the final version, and a list of fourteen defects with their causes and fixes.",
    ]),
    ("h3", "6.7  Overall Analysis"),
    ("p", f"The system meets all the quality goals set in Chapter 3 on the test machine. Reads are fast (median about {f(mean([lat[k]['p50'] for k in ep]))} ms), throughput reaches {f(peak['rps'], 0)} requests per second, and, more importantly for the topic of the course, the system behaves sensibly when parts of it fail: a broker outage delays notifications but loses none, a book-service outage turns issuing into an accepted, pending request that completes by itself, and a refused request changes nothing."),
    ("p", f"The measurements also show the costs of the style. Fourteen containers use {f(sum(memory.values()) / 1024, 1)} GiB of memory when idle, start-up takes up to {f(max(startup.values()), 0)} seconds per Java service, and the event path is about {f(mean(fine_ms) - mean(fine_ms0), 0)} ms slower than a direct publish because of the outbox polling. The fourteen defects of Section 5.4.4 are also typical of the style: three of the most instructive ones (default timeouts, a circuit breaker that counts business errors, and a stock change that is not atomic with the loan) are only visible when the system is exercised with failures, which is why the experiments were part of the work and not an afterthought."),
    ("h3", "6.8  Summary"),
    ("p", "The running system, its screenshots and its measurements confirm that every objective of Chapter 1 was met. The next chapter states the conclusions, the limitations that remain and the directions for further work."),
]

CH7 = [
    ("h2", "CHAPTER 7:  CONCLUSION"),
    ("h3", "7.1  Conclusion"),
    ("p", "The project built an Online Library Management System as a set of independent services with their own PostgreSQL databases, a gateway with JWT login and role rules, event-driven communication through RabbitMQ and a monitoring stack of Zipkin, Prometheus and Grafana. The catalogue contains 10,000 real books. The central design problem, keeping the stock of a book and the loan record consistent without a distributed transaction, was solved with a saga, a transactional outbox, idempotency keys and duplicate-safe consumers, and each guarantee was checked by an experiment that injects the corresponding failure."),
    ("p", "The syllabus topics have a concrete place in the system: SEED(S) and event storming in the design, bounded contexts and database per service in the boundaries, event sourcing in the loan history, a small CQRS-style separation in the event log and its read endpoint, Docker and Kubernetes in the deployment, and the management of change in versioned images and centrally configured settings. The most useful lessons were practical: defaults such as a ten-second connect timeout and a circuit breaker that counts every exception are unsafe for a system that is expected to survive failures, and they were found only by stopping services and measuring."),
    ("h3", "7.2  Limitations"),
    ("bullets", [
        "Everything ran on one laptop. The Compose stack was used for all measurements; the Kubernetes manifests were applied only to a single-node minikube cluster (Section 6.5), which gave a functional check but no performance, multi-node or autoscaling results, and Prometheus and Grafana are part of the Compose stack only.",
        "The performance figures come from one machine on which the client and all services compete for the same processor threads; they describe behaviour, not production capacity. Thirty cycles and 200 samples per endpoint are small samples.",
        "Users are defined in the gateway configuration with demonstration passwords, the JWT secret has a demonstration default, and the database passwords are in the Compose file. There is no token revocation or refresh, and the token is kept in the browser's session storage.",
        "The business services publish their ports on the loopback interface of the host for demonstration and Swagger. In a real deployment they must be reachable only from the gateway; today the gateway is the only place where roles are enforced.",
        "The outbox relay polls every 300 milliseconds and does not use publisher confirms. With several lending instances an event could be sent twice; the consumers tolerate this, but the design has not been tested with more than one lending instance.",
        "A PENDING loan stays pending as long as the book service is unavailable; there is no limit on the number of recovery attempts and no notification to the librarian.",
        "PostgreSQL runs as one instance without replication or backups, and in the Kubernetes manifest on a volume that is lost when the pod is removed.",
        "The dataset has no genres (the category is the publication era), the number of copies per title is generated, and the front end loads and filters the whole catalogue in the browser.",
        "The checks of the user interface were made by hand; there are no automated browser tests, and the experiments are scripts, not part of a continuous-integration run.",
    ]),
    ("h3", "7.3  Future Scope"),
    ("bullets", [
        "Replace the demonstration login by an identity provider (OpenID Connect, for example Keycloak), validate tokens in every service as a second line of defence, and keep the services off the host network.",
        "Add server-side search and pagination with an index (a CQRS read model, for example in OpenSearch) so that the catalogue can grow far beyond 10,000 titles.",
        "Run the manifests on a multi-node cluster, add start-up ordering (init containers or start-up probes) and a horizontal pod autoscaler for the book service, install Prometheus and Grafana there, and repeat the measurements with several replicas.",
        "Run the experiments in continuous integration with Testcontainers, and add automated browser tests.",
        "Replace the polling relay by change-data-capture (Debezium) or use publisher confirms, and use a dedicated workflow engine for sagas as the number of steps grows.",
        "Add reservations, renewals and e-mail or SMS delivery as further services that consume the existing events without any change to the lending service.",
    ]),
    ("h3", "7.4  Summary"),
    ("p", "The work delivered a working, secured, observable and measured microservices system and a documented record of the problems met on the way. The limitations are stated openly so that the results can be judged for what they are: a thorough single-machine study of the main patterns of the course."),
]

REFS = [
    "I. Nadareishvili, \"Microservices: Up and Running: A Step-by-Step Guide to Building a Microservices Architecture,\" Shroff Publishers, 2020, ISBN 9789385889608 (as listed in the syllabus).",
    "S. Newman, \"Building Microservices: Designing Fine-Grained Systems,\" 2nd ed., O'Reilly Media, 2021.",
    "H. Percival and B. Gregory, \"Architecture Patterns with Python,\" 1st ed., Shroff Publishers, 2020.",
    "J. Carnell, \"Spring Microservices in Action,\" 1st ed., Manning Publications, 2017.",
    "J. Lewis and M. Fowler, \"Microservices,\" martinfowler.com, Mar. 2014.",
    "N. Dragoni, S. Giallorenzo, A. L. Lafuente, M. Mazzara, F. Montesi, R. Mustafin and L. Safina, \"Microservices: Yesterday, Today, and Tomorrow,\" in Present and Ulterior Software Engineering, Springer, 2017, pp. 195-216.",
    "E. Evans, \"Domain-Driven Design: Tackling Complexity in the Heart of Software,\" Addison-Wesley, 2003.",
    "C. Richardson, \"Microservices Patterns,\" Manning Publications, 2018.",
    "H. Garcia-Molina and K. Salem, \"Sagas,\" ACM SIGMOD Record, vol. 16, no. 3, pp. 249-259, 1987.",
    "M. T. Nygard, \"Release It! Design and Deploy Production-Ready Software,\" 2nd ed., Pragmatic Bookshelf, 2018.",
    "G. Hohpe and B. Woolf, \"Enterprise Integration Patterns,\" Addison-Wesley, 2003.",
    "M. Kleppmann, \"Designing Data-Intensive Applications,\" O'Reilly Media, 2017.",
    "M. Skelton and M. Pais, \"Team Topologies,\" IT Revolution Press, 2019.",
    "M. E. Conway, \"How do committees invent?\" Datamation, vol. 14, no. 4, pp. 28-31, 1968.",
    "B. Burns, B. Grant, D. Oppenheimer, E. Brewer and J. Wilkes, \"Borg, Omega, and Kubernetes,\" ACM Queue, vol. 14, no. 1, 2016.",
    "R. T. Fielding, \"Architectural Styles and the Design of Network-based Software Architectures,\" Ph.D. dissertation, University of California, Irvine, 2000.",
    "M. Jones, J. Bradley and N. Sakimura, \"JSON Web Token (JWT),\" RFC 7519, IETF, May 2015.",
    "B. H. Sigelman et al., \"Dapper, a Large-Scale Distributed Systems Tracing Infrastructure,\" Google Technical Report, 2010.",
    "Z. Zajac, \"Goodbooks-10k: a new dataset for book recommendations,\" GitHub repository zygmuntz/goodbooks-10k, 2017.",
    "VMware, \"Spring Boot and Spring Cloud reference documentation,\" spring.io, accessed Nov. 2026.",
    "Resilience4j, \"Resilience4j documentation: CircuitBreaker,\" resilience4j.readme.io, accessed Nov. 2026.",
    "Broadcom (VMware), \"RabbitMQ documentation: AMQP 0-9-1 model and topic exchanges,\" rabbitmq.com, accessed Nov. 2026.",
    "OpenAPI Initiative, \"OpenAPI Specification v3.0,\" spec.openapis.org, accessed Nov. 2026.",
    "Docker Inc., \"Docker and Docker Compose documentation,\" docs.docker.com, accessed Nov. 2026.",
    "Prometheus Authors, Grafana Labs and OpenZipkin, \"Prometheus, Grafana and Zipkin documentation,\" accessed Nov. 2026.",
]
REF_NOTE = "Note: the entries were written from the authors' knowledge of the works. Volume, page and edition details should be checked against the publisher's page before the report is submitted."


def appendix_rows():
    rows = [l.split("|") for l in open(ROOT + "/book-service/src/main/resources/books.csv", encoding="utf-8").read().split("\n")[1:] if l.strip()]
    return rows


APPENDIX_A_FIRST = appendix_rows()[:15]
APPENDIX_A_LAST = appendix_rows()[-8:]
