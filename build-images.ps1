# Builds all images tagged library/<name>:1.0.0 (used by k8s/library.yaml)
foreach ($m in "config-server","discovery-server","api-gateway","book-service","member-service","lending-service","fine-service","notification-service") {
  docker build --build-arg MODULE=$m -t "library/${m}:1.0.0" .
}
docker build -t library/frontend:1.0.0 ./frontend
