import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def edit(path, pairs):
    p = os.path.join(ROOT, path)
    s = open(p, encoding="utf-8").read()
    for old, new in pairs:
        assert old in s, (path, old[:70])
        s = s.replace(old, new, 1)
    open(p, "w", encoding="utf-8").write(s)


edit("README.md", [
    ("(12 Deployments and Services, a Secret for the JWT key, a ConfigMap for the database script; every JVM has its heap capped with `JAVA_TOOL_OPTIONS`)",
     "(14 Deployments and Services including Prometheus and Grafana, a Secret for the JWT key, 5 ConfigMaps; every JVM has its heap capped with `JAVA_TOOL_OPTIONS`, and **init containers** make each Java service wait for the config server, registry, PostgreSQL and RabbitMQ, so the pods start in order)"),
    ("kubectl get pods -n library              # all 14 pods ready after about 5 minutes", "kubectl get pods -n library              # all 16 pods ready (book and member run 2 replicas)"),
    ("| GET | `/api/books/search?q=` | Search by title or author |", "| GET | `/api/books/page?q=&page=0&size=24` | Server-side search and paging (size capped at 100) |\n| GET | `/api/books/stats` | Catalogue totals (titles, copies, copies available) |\n| GET | `/api/books/search?q=` | Search by title or author |"),
    ("| POST | `/api/auth/login` | Body `{\"username\":\"..\",\"password\":\"..\"}` |", "| POST | `/api/auth/login` | Body `{\"username\":\"..\",\"password\":\"..\"}` |\n| POST | `/api/auth/refresh` | Exchange a valid token for a fresh one (the web UI does this automatically) |\n| POST | `/api/auth/change-password` | Body `{\"oldPassword\":\"..\",\"newPassword\":\"..\"}`, at least 8 characters; kept in memory until the gateway restarts |"),
    ("- **23 unit tests** (gateway 9, book 5, lending 7, fine 2)", "- **31 unit tests** (gateway 14, book 8, lending 7, fine 2)"),
    ("- `report/experiments.py`: seven fault-injection experiments", "- `report/experiments.py`: seven fault-injection experiments with 13 pass/fail checks (also run by the second GitHub Actions workflow `.github/workflows/experiments.yml`)"),
    ("docker-compose.yml  Dockerfile  maven-settings.xml  infra/postgres/init.sql  monitoring/  k8s/  .github/workflows/ci.yml", "docker-compose.yml  Dockerfile  maven-settings.xml  infra/postgres/init.sql  monitoring/  k8s/  .github/workflows/ (ci.yml, experiments.yml)"),
    ("Data lives in the Docker volume `pgdata`.", "If port 8080 is already used on your machine, start with `GATEWAY_PORT=18080` (PowerShell: `$env:GATEWAY_PORT=18080`) and call the API on that port; the web UI is unaffected. Data lives in the Docker volume `pgdata`."),
    ("[docs/SYLLABUS_COVERAGE.md](docs/SYLLABUS_COVERAGE.md) maps every syllabus unit", "[docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) is a ten-minute demo script; [docs/SYLLABUS_COVERAGE.md](docs/SYLLABUS_COVERAGE.md) maps every syllabus unit"),
])
edit("docs/DESIGN.md", [
    ("(26 operations)", "(28 operations)"),
    ("One multi-stage Dockerfile, `docker-compose.yml` (14 containers), `k8s/library.yaml`, GitHub Actions workflow.", "One multi-stage Dockerfile, `docker-compose.yml` (14 containers), `k8s/library.yaml` (init containers for the start order, Prometheus and Grafana included), two GitHub Actions workflows (build and tests; fault-injection experiments)."),
])
edit("docs/SYLLABUS_COVERAGE.md", [
    ("(26 operations)", "(28 operations)"),
    ("`.github/workflows/ci.yml`; `docker-compose.yml`", "`.github/workflows/ci.yml` and `experiments.yml`; `docker-compose.yml`"),
])
print("docs updated")
