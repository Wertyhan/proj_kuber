#!/usr/bin/env bash
set -e

K8S_DIR="k8s"
LOG_DIR="logs"
LOG_FILE="$LOG_DIR/report.txt"

mkdir -p "$LOG_DIR"
echo "=== K8s Deployment Log: $(date) ===" > "$LOG_FILE"

FASTAPI_DEPLOYMENT="$K8S_DIR/fastapi-deployment.yaml"
DB_DEPLOYMENT="$K8S_DIR/db-deployment.yaml"
HOSTPATH_POD="$K8S_DIR/hostpath-pod.yaml"
SECRET="$K8S_DIR/secret.yml"
EMPTYDIR_POD="$K8S_DIR/emptydir-pod.yaml"  

log() {
  echo "$1" | tee -a "$LOG_FILE"
}

check_file_exists() {
  if [[ ! -f "$1" ]]; then
    log "File not found: $1"
    exit 1
  fi
}

apply_services() {
  for f in "$SECRET" "$DB_DEPLOYMENT" "$FASTAPI_DEPLOYMENT" "$HOSTPATH_POD"; do
    check_file_exists "$f"
    log "Applying $f..."
    kubectl apply -f "$f" 2>&1 | tee -a "$LOG_FILE"
  done
}

delete_services() {
  for f in "$FASTAPI_DEPLOYMENT" "$DB_DEPLOYMENT" "$HOSTPATH_POD" "$SECRET"; do
    if [[ -f "$f" ]]; then
      log "Deleting $f..."
      kubectl delete -f "$f" --ignore-not-found 2>&1 | tee -a "$LOG_FILE"
    fi
  done
}

wait_for_pods() {
  log "Waiting for pods to be ready..."
  kubectl wait --for=condition=ready pod --all --timeout=90s 2>&1 | tee -a "$LOG_FILE" || log "⚠️ Some pods are not ready in time."
}

show_status() {
  log "Current status of pods and services:"
  kubectl get pods,svc -o wide 2>&1 | tee -a "$LOG_FILE"
}

if [[ "$1" == "--delete" ]]; then
  delete_services
  exit 0
fi

if [[ "$1" == "--run" ]]; then
  delete_services
  apply_services
  wait_for_pods
  show_status
  exit 0
fi

log "Usage: $0 [--run | --delete]"
exit 1
