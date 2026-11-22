"""Regenerates k8s/library.yaml.  python k8s/generate_manifests.py
Images are expected as library/<name>:1.0.0 (see build-images.ps1).
Every Java service waits for the services it needs in an init container, so the pods start in order and do not restart.
Prometheus and Grafana are deployed from the same files as in Docker Compose (monitoring/)."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def read(*parts):
    return open(os.path.join(ROOT, *parts), encoding="utf-8").read()


INIT_SQL = read("infra", "postgres", "init.sql")

PORTS = {"config-server": 8888, "discovery-server": 8761, "api-gateway": 8080, "book-service": 8081, "member-service": 8082,
         "lending-service": 8083, "fine-service": 8084, "notification-service": 8085}
DB = {"book-service": ("bookdb", "bookuser", "book123"), "member-service": ("memberdb", "memberuser", "member123"),
      "lending-service": ("lendingdb", "lendinguser", "lending123"), "fine-service": ("finedb", "fineuser", "fine123"),
      "notification-service": ("notificationdb", "notificationuser", "notification123")}
RABBIT = ("lending-service", "fine-service", "notification-service")


def deployment(name, port, image, env=None, replicas=1, node=None, volumes="", mounts="", probe=True, waits=()):
    env_txt = ""
    if env:
        env_txt = "        env:\n" + "".join(f"        - {{name: {k}, value: \"{v}\"}}\n" if not isinstance(v, dict) else
                                            f"        - name: {k}\n          valueFrom:\n            secretKeyRef: {{name: {v['secret']}, key: {v['key']}}}\n"
                                            for k, v in env.items())
    probe_txt = f"        readinessProbe:\n          tcpSocket: {{port: {port}}}\n          initialDelaySeconds: 30\n          periodSeconds: 10\n" if probe else ""
    init_txt = ""
    if waits:
        script = "; ".join(f"until nc -z {h} {p}; do echo waiting for {h}; sleep 2; done" for h, p in waits)
        init_txt = f"      initContainers:\n      - name: wait-for-dependencies\n        image: busybox:1.36\n        imagePullPolicy: IfNotPresent\n        command: [\"sh\", \"-c\", \"{script}\"]\n"
    svc_type = "  type: NodePort\n" if node else ""
    node_txt = f"    nodePort: {node}\n" if node else ""
    svc_port = 80 if name == "frontend" else port
    return f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {name}
  namespace: library
spec:
  replicas: {replicas}
  selector:
    matchLabels: {{app: {name}}}
  template:
    metadata:
      labels: {{app: {name}}}
    spec:
{init_txt}      containers:
      - name: {name}
        image: {image}
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: {port}
{env_txt}{mounts}{probe_txt}{volumes}---
apiVersion: v1
kind: Service
metadata:
  name: {name}
  namespace: library
spec:
{svc_type}  selector:
    app: {name}
  ports:
  - port: {svc_port}
    targetPort: {port}
{node_txt}---
"""


def configmap(name, key, text):
    return f"apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: {name}\n  namespace: library\ndata:\n  {key}: |\n" + "".join("    " + line + "\n" for line in text.splitlines()) + "---\n"


out = "apiVersion: v1\nkind: Namespace\nmetadata:\n  name: library\n---\n"
out += """apiVersion: v1
kind: Secret
metadata:
  name: library-secrets
  namespace: library
type: Opaque
stringData:
  jwt-secret: library-demo-secret-library-demo-secret-2026   # demo value: replace before real use
---
"""
out += configmap("postgres-init", "init.sql", INIT_SQL)
out += configmap("prometheus-config", "prometheus.yml", read("monitoring", "prometheus.yml"))
out += configmap("grafana-datasources", "datasources.yml", read("monitoring", "grafana", "provisioning", "datasources", "datasources.yml"))
out += configmap("grafana-dashboard-provider", "dashboards.yml", read("monitoring", "grafana", "provisioning", "dashboards", "dashboards.yml"))
out += configmap("grafana-dashboards", "library.json", read("monitoring", "grafana", "dashboards", "library.json"))

out += deployment("postgres", 5432, "postgres:16-alpine", {"POSTGRES_PASSWORD": "postgres"},
                  mounts="        volumeMounts:\n        - {name: init, mountPath: /docker-entrypoint-initdb.d}\n        - {name: data, mountPath: /var/lib/postgresql/data}\n",
                  volumes="      volumes:\n      - name: init\n        configMap: {name: postgres-init}\n      - name: data\n        emptyDir: {}\n")
out += deployment("rabbitmq", 5672, "rabbitmq:3.13-alpine")
out += deployment("zipkin", 9411, "openzipkin/zipkin:3")
out += deployment("prometheus", 9090, "prom/prometheus:v2.53.0",
                  mounts="        volumeMounts:\n        - {name: config, mountPath: /etc/prometheus/prometheus.yml, subPath: prometheus.yml}\n",
                  volumes="      volumes:\n      - name: config\n        configMap: {name: prometheus-config}\n")
out += deployment("grafana", 3000, "grafana/grafana:11.1.0",
                  {"GF_SECURITY_ADMIN_PASSWORD": "admin", "GF_AUTH_ANONYMOUS_ENABLED": "true", "GF_AUTH_ANONYMOUS_ORG_ROLE": "Viewer",
                   "GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH": "/var/lib/grafana/dashboards/library.json"},
                  node=30081,
                  mounts=("        volumeMounts:\n        - {name: datasources, mountPath: /etc/grafana/provisioning/datasources}\n"
                          "        - {name: provider, mountPath: /etc/grafana/provisioning/dashboards}\n        - {name: dashboards, mountPath: /var/lib/grafana/dashboards}\n"),
                  volumes=("      volumes:\n      - name: datasources\n        configMap: {name: grafana-datasources}\n      - name: provider\n        configMap: {name: grafana-dashboard-provider}\n"
                           "      - name: dashboards\n        configMap: {name: grafana-dashboards}\n"))

for name, port in PORTS.items():
    env, waits = None, []
    if name == "discovery-server":
        waits = [("config-server", 8888)]
    if name not in ("config-server", "discovery-server"):
        env = {"CONFIG_URL": "http://config-server:8888", "EUREKA_URL": "http://discovery-server:8761/eureka", "ZIPKIN_URL": "http://zipkin:9411/api/v2/spans", "JAVA_TOOL_OPTIONS": "-Xmx256m -XX:MaxMetaspaceSize=160m"}
        waits = [("config-server", 8888), ("discovery-server", 8761)]
        if name in RABBIT:
            env["SPRING_RABBITMQ_HOST"] = "rabbitmq"
            waits.append(("rabbitmq", 5672))
        if name in DB:
            d, u, p = DB[name]
            env.update({"SPRING_DATASOURCE_URL": f"jdbc:postgresql://postgres:5432/{d}", "SPRING_DATASOURCE_USERNAME": u, "SPRING_DATASOURCE_PASSWORD": p})
            waits.append(("postgres", 5432))
        if name == "api-gateway":
            env["JWT_SECRET"] = {"secret": "library-secrets", "key": "jwt-secret"}
    if name in ("config-server", "discovery-server"):
        env = {"JAVA_TOOL_OPTIONS": "-Xmx192m -XX:MaxMetaspaceSize=128m"}   # cap the heap so the whole system fits in about 9 GB
    out += deployment(name, port, f"library/{name}:1.0.0", env, replicas=2 if name in ("book-service", "member-service") else 1, waits=waits)
out += deployment("frontend", 80, "library/frontend:1.0.0", node=30080)
open(os.path.join(HERE, "library.yaml"), "w", encoding="utf-8").write(out.rstrip("-\n") + "\n")
print("wrote k8s/library.yaml with", out.count("kind: Deployment"), "deployments")
