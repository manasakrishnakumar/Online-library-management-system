"""Replaces references [1]-[25] with IEEE / Springer sources (metadata read from Crossref) and rewrites the sentences that cite them."""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))


def rd(n):
    return open(os.path.join(HERE, n), encoding="utf-8").read()


def wr(n, s):
    open(os.path.join(HERE, n), "w", encoding="utf-8").write(s)


NEW = [
    'V. Velepucha and P. Flores, "A Survey on Microservices Architecture: Principles, Patterns and Migration Challenges," IEEE Access, vol. 11, pp. 88339-88358, 2023, doi: 10.1109/ACCESS.2023.3305687.',
    'U. Chouhan, V. Tiwari and H. Kumar, "Comparing Microservices and Monolithic Applications in a DevOps Context," in Proc. 2023 3rd Asian Conf. Innovation in Technology (ASIANCON), 2023, pp. 1-7, doi: 10.1109/ASIANCON58793.2023.10270721.',
    'H. F. Oliveira Rocha, Practical Event-Driven Microservices Architecture. Berkeley, CA, USA: Apress (Springer Nature), 2022, doi: 10.1007/978-1-4842-7468-2.',
    'F. Gutierrez, Spring Boot Fundamentals. Berkeley, CA, USA: Apress (Springer Nature), 2021, doi: 10.1007/978-1-4842-7066-0.',
    'C. Rajasekharaiah, Cloud-Based Microservices. Berkeley, CA, USA: Apress (Springer Nature), 2021, doi: 10.1007/978-1-4842-6564-2.',
    "N. Dragoni, S. Giallorenzo, A. L. Lafuente, M. Mazzara, F. Montesi, R. Mustafin and L. Safina, \"Microservices: Yesterday, Today, and Tomorrow,\" in Present and Ulterior Software Engineering, Springer, 2017, pp. 195-216.",
    'H. Farsi, D. Allaki, A. En-nouaary and M. Dahchour, "Following Domain Driven Design principles for Microservices decomposition: is it enough?" in Proc. 2021 IEEE/ACS 18th Int. Conf. Computer Systems and Applications (AICCSA), 2021, pp. 1-8, doi: 10.1109/AICCSA53542.2021.9686947.',
    'K. M. Koyya and B. Muthukumar, "A Survey of Saga Frameworks for Distributed Transactions in Event-driven Microservices," in Proc. 2022 3rd Int. Conf. Smart Technologies in Computing, Electrical and Electronics (ICSTCEE), 2022, pp. 1-6, doi: 10.1109/ICSTCEE56972.2022.10099533.',
    'A. Navarro, "Local, Global, and Saga Transactions for SOA Services and Microservices (*Services)," IEEE Access, vol. 13, pp. 80206-80246, 2025, doi: 10.1109/ACCESS.2025.3566230.',
    'H. Hanada and K. Ishibashi, "Empirical Study on Request Timeout and Retry for Microservices Communication," in Proc. 2024 IEEE 29th Pacific Rim Int. Symp. Dependable Computing (PRDC), 2024, pp. 199-200, doi: 10.1109/PRDC63035.2024.00037.',
    'H. F. Oliveira Rocha, "Achieving Resilience and Event Processing Reliability in Event-Driven Microservices," in Practical Event-Driven Microservices Architecture. Berkeley, CA, USA: Apress (Springer Nature), 2021, pp. 275-321, doi: 10.1007/978-1-4842-7468-2_7.',
    'R. Laigner and Y. Zhou, "Benchmarking Data Management Systems for Microservices," in Proc. 2024 IEEE 40th Int. Conf. Data Engineering (ICDE), 2024, pp. 5671-5672, doi: 10.1109/ICDE60146.2024.00467.',
    'N. Ahmad, "Evaluating the Effect of Team Ownership of Microservices: Strategies for Balancing Decoupling, Coordination, and System Cohesion," Lecture Notes in Computer Science, Springer Nature Switzerland, 2024, pp. 58-64, doi: 10.1007/978-3-031-71246-3_7.',
    'D. A. Tamburri, R. Kazman and H. Fahimi, "On the Relationship Between Organizational Structure Patterns and Architecture in Agile Teams," IEEE Trans. Software Engineering, vol. 49, no. 1, pp. 325-347, 2023, doi: 10.1109/TSE.2022.3150415.',
    'F. Eyvazov, T. E. Ali, F. I. Ali and A. D. Zoltan, "Beyond Containers: Orchestrating Microservices with Minikube, Kubernetes, Docker, and Compose for Seamless Deployment and Scalability," in Proc. 2024 11th Int. Conf. Reliability, Infocom Technologies and Optimization (ICRITO), 2024, pp. 1-6, doi: 10.1109/ICRITO61523.2024.10522382.',
    'B. Varanasi and M. Bartkov, Spring REST, 2nd ed. Berkeley, CA, USA: Apress (Springer Nature), 2022, doi: 10.1007/978-1-4842-7477-4.',
    'M. Nardone and C. Scarioni, "JSON Web Token (JWT) Authentication," in Pro Spring Security. Berkeley, CA, USA: Apress (Springer Nature), 2023, pp. 239-279, doi: 10.1007/979-8-8688-0035-1_9.',
    'J. Rios, S. Jha and L. Shwartz, "Localizing and Explaining Faults in Microservices Using Distributed Tracing," in Proc. 2022 IEEE 15th Int. Conf. Cloud Computing (CLOUD), 2022, pp. 489-499, doi: 10.1109/CLOUD55607.2022.00072.',
    'Z. Zajac, "Goodbooks-10k: a new dataset for book recommendations," GitHub repository zygmuntz/goodbooks-10k, 2017 (data source, not a publication).',
    'B. Enochson, Architecting Microservices with Spring Boot and Spring Cloud. Berkeley, CA, USA: Apress (Springer Nature), 2026, doi: 10.1007/979-8-8688-2940-6.',
    'M. D. Argakoesoemah and M. Z. C. Candra, "Development of Cascading Circuit Breaker System Using Event-Driven Approach in Microservices," in Proc. 2024 IEEE Int. Conf. Data and Software Engineering (ICoDSE), 2024, pp. 102-107, doi: 10.1109/ICODSE63307.2024.10829897.',
    'R. Bux and G. S. Shenoy, "Performance Analysis of RESTFUL Web Services and RABBITMQ for Microservices based Systems on Cloud Environment," in Proc. 2024 3rd Int. Conf. Innovation in Technology (INOCON), 2024, pp. 1-6, doi: 10.1109/INOCON60754.2024.10511747.',
    'R. Pergl and N. Jíša, "Semantic Analysis of API Blueprint and OpenAPI Specification," Lecture Notes in Networks and Systems, Springer Nature Switzerland, 2024, pp. 172-181, doi: 10.1007/978-3-031-60227-6_15.',
    'M. M. Raikar, P. Patil, S. Guggari, P. Shavi, S. Mudavi, N. Patil and V. Rangannavar, "Leveraging Docker Containers for Deployment of Web Applications in Microservices Architecture," in Proc. 2024 1st Int. Conf. Women in Computing (InCoWoCo), 2024, pp. 1-6, doi: 10.1109/INCOWOCO64194.2024.10863683.',
    'M. Aich and D. Sengupta, "Monitoring Microservices with Prometheus and Grafana," in Cloud-Native Modernization Unleashed. Berkeley, CA, USA: Apress (Springer Nature), 2026, pp. 163-175, doi: 10.1007/979-8-8688-2379-4_8.',
]
assert len(NEW) == 25

# ---- content_c: REFS + note
s = rd("content_c.py")
a = s.index("REFS = [\n") + len("REFS = [\n")
lines = s[a:].split("\n")
# the first 25 entries are one per line
old = lines[:25]
assert old[0].lstrip().startswith('"I. Nadareishvili') and old[24].lstrip().startswith('"Prometheus Authors')
new_lines = ["    " + repr(r) if "'" in r and '"' not in r else "    " + '"' + r.replace('"', '\\"') + '",' for r in NEW]
new_lines = [l if l.endswith(",") else l + "," for l in new_lines]
s = s[:a] + "\n".join(new_lines) + "\n" + "\n".join(lines[25:])
s = re.sub(r'REF_NOTE = ".*?"\n', 'REF_NOTE = "Note: every entry except [19] (the source repository of the dataset, which is not a publication) is an IEEE or Springer publication (Springer includes the Apress and Springer Nature books and chapters). The title, authors, venue, year and DOI of entries [1] to [39] were checked against Crossref records."\n', s, count=1, flags=re.S)
wr("content_c.py", s)

# ---- content_a: text and table
s = rd("content_a.py")


def swap(old_start, new_text):
    global s
    i = s.index(old_start)
    j = s.index('"),\n', i)
    s = s[:i] + new_text + s[j:]


swap('Lewis and Fowler [5] describe', 'Velepucha and Flores [1] survey the principles, patterns and migration challenges of the microservices style, and Dragoni et al. [6] trace how the style grew out of service-oriented architecture and discuss its benefits and open problems. Rajasekharaiah [5] gives a practical introduction to cloud-based microservices, and Chouhan et al. [2] compare microservices with monolithic applications in a DevOps context, the comparison behind the split of this project into independently deployable services. Gutierrez [4] and Enochson [20] cover Spring Boot and Spring Cloud, the technology used here, and Oliveira Rocha [3] covers event-driven microservices, in which services interact through messages. Spring support for the REST style of the service interfaces is covered in [16].')
swap('Evans [7] introduced', 'Domain-driven design divides a system into bounded contexts: parts of the domain inside which every term has one meaning. Farsi et al. [7] ask whether following these principles is enough to decompose a system into microservices. The syllabus adds event storming and a sizing formula as practical tools. In this project the contexts Catalogue, Membership, Lending, Fines and Notifications were therefore found by event storming and also checked against the rule that a service should have one reason to change.')
swap('Garcia-Molina and Salem [9]', 'A saga is a sequence of local transactions, each with a compensating action that undoes it. Koyya and Muthukumar [8] survey saga frameworks for distributed transactions in event-driven microservices, and Navarro [9] compares local, global and saga transactions for SOA services and microservices. Oliveira Rocha [3] discusses how to manage eventual consistency in event-driven microservices, and [11] the reliability of event processing, including repeated delivery of the same message. In the transactional outbox, an event is stored in the same transaction as the state change and published afterwards; idempotent receivers make repeated delivery safe. Laigner and Zhou [12] present a benchmark of data management systems for microservices, and Bux and Shenoy [22] analyse RESTful web services and RabbitMQ for microservice systems on the cloud, the two communication styles combined in this project. These sources are the background of the saga, the outbox, the idempotency keys and the duplicate-safe notification consumer in Chapter 5.')
swap('Nygard [10] describes', 'Hanada and Ishibashi [10] study request timeouts and retries in microservice communication, the two settings that stop one slow dependency from holding up its callers (the Feign timeouts used here), and Argakoesoemah and Candra [21] develop a cascading circuit breaker system for microservices. The Resilience4j library used here implements the circuit breaker. One practical lesson, confirmed by the measurements in Chapter 6, is that a circuit breaker must be told which failures to count: a business rejection such as \\"no copies available\\" is not a sign that the book service is unhealthy.')
swap('The JSON Web Token standard [17]', 'Nardone and Scarioni [17] describe JSON Web Token authentication for Spring applications: a compact signed token carries claims. A gateway that verifies the token and applies role rules protects every service behind it with one piece of code. This is the approach taken here; it is also the reason the gateway must be the only entry point, a point revisited in the limitations.')
swap('Sigelman et al. [18]', 'Rios et al. [18] use distributed tracing to localise and explain faults in microservices: a request carries an identifier through all services, and each service records timed spans. Zipkin, used here, follows the same model. Metrics are collected by Prometheus and shown in Grafana, which Aich and Sengupta [25] describe for microservices; the three pillars (logs, metrics, traces) are tied together by putting the trace identifier into every log line.')
swap('Conway [14] observed', 'Tamburri et al. [14] study the relationship between organisational structure patterns and architecture in agile teams, and Ahmad [13] evaluates the effect of team ownership of microservices, balancing decoupling, coordination and system cohesion. The syllabus uses team topologies (stream-aligned teams and a platform team) as the basis of the operating model, discussed in Section 4.3. For deployment, Eyvazov et al. [15] orchestrate microservices with Minikube, Kubernetes, Docker and Compose, the toolset used here, and Raikar et al. [24] describe Docker containers for deploying web applications in a microservices architecture. The API documents of the services follow the OpenAPI specification, whose semantics Pergl and Jíša [23] analyse.')

rows = {
    "[1]": ["[1]", "Velepucha and Flores, survey on microservices architecture (IEEE Access 2023)", "Principles, patterns, migration challenges", "Overall process, vocabulary"],
    "[2]": ["[2]", "Chouhan et al., microservices and monoliths in a DevOps context (IEEE ASIANCON 2023)", "Comparison with monoliths", "Why independent deployment"],
    "[3]": ["[3]", "Oliveira Rocha, Practical Event-Driven Microservices Architecture (Springer/Apress 2022)", "Events, eventual consistency", "Event-driven interaction between services"],
    "[4]": ["[4]", "Gutierrez, Spring Boot Fundamentals (Springer/Apress 2021)", "Spring Boot", "Framework of every service"],
    "[5]": ["[5]", "Rajasekharaiah, Cloud-Based Microservices (Springer/Apress 2021)", "Introduction to microservices", "Terminology and characteristics"],
    "[6]": ["[6]", "Dragoni et al., Microservices: Yesterday, Today, and Tomorrow (Springer 2017)", "History and open problems", "Motivation, limitations"],
    "[7]": ["[7]", "Farsi et al., domain-driven design for decomposition (IEEE AICCSA 2021)", "Bounded contexts", "Service boundaries"],
    "[8]": ["[8]", "Koyya and Muthukumar, survey of saga frameworks (IEEE ICSTCEE 2022)", "Saga frameworks", "Saga design"],
    "[9]": ["[9]", "Navarro, local, global and saga transactions (IEEE Access 2025)", "Transactions in microservices", "Compensation concept"],
    "[10]": ["[10]", "Hanada and Ishibashi, request timeout and retry (IEEE PRDC 2024)", "Timeouts and retries", "Feign timeouts"],
    "[11]": ["[11]", "Oliveira Rocha, resilience and event processing reliability (Springer/Apress 2021)", "Reliable event processing", "Outbox, idempotent consumers"],
    "[12]": ["[12]", "Laigner and Zhou, benchmarking data management for microservices (IEEE ICDE 2024)", "Data management", "Database per service"],
    "[13][14]": ["[13][14]", "Ahmad, team ownership (Springer LNCS 2024); Tamburri et al. (IEEE TSE 2023)", "Teams and architecture", "Operating model"],
    "[15]": ["[15]", "Eyvazov et al., Minikube, Kubernetes, Docker, Compose (IEEE ICRITO 2024)", "Container orchestration", "Kubernetes manifests"],
    "[17]": ["[17]", "Nardone and Scarioni, JWT authentication (Springer/Apress 2023)", "JSON Web Token", "Login and role claims"],
    "[18]": ["[18]", "Rios et al., tracing to localise faults (IEEE CLOUD 2022)", "Distributed tracing", "Zipkin traces"],
}
for key, row in rows.items():
    m = re.search(r'        \["%s", ".*?\],\n' % re.escape(key), s)
    assert m, key
    s = s[:m.start()] + "        " + repr(row).replace("'", '"') + ",\n" + s[m.end():]
wr("content_a.py", s)

# ---- content_b
s = rd("content_b.py")
old = 'The tools below are described in their reference documentation [20] to [25].'
assert old in s
s = s.replace(old, "The tools are described in [20] to [25] (Spring [4][20], circuit breaker [21], RabbitMQ [22], OpenAPI [23], Docker [24], Prometheus and Grafana [25]).")
assert 'Prescribed reference [4]; fast to start with' in s
s = s.replace('Prescribed reference [4]; fast to start with', 'Described in [4] and [20]; fast to start with')
wr("content_b.py", s)
print("refs patched")
