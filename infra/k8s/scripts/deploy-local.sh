#!/usr/bin/env bash
# Build the images, load them into the local kind cluster and install the chart.
#
# Memory-safe by design (laptops with ~14 GiB RAM shared with a browser and IDE):
#   * refuses to start below MIN_FREE_MB available memory,
#   * builds ONE image at a time and re-checks memory before each build,
#   * never runs builds in parallel.
#
# Usage: infra/k8s/scripts/deploy-local.sh [component ...]
#        (default: all components; e.g. "ai-agent" to rebuild only that one)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
CLUSTER="${CLUSTER:-claims-review}"
NAMESPACE="${NAMESPACE:-claims-review}"
TAG="${TAG:-dev}"
MIN_FREE_MB="${MIN_FREE_MB:-4000}"
ALL_COMPONENTS=(ml-service ai-agent claims-api frontend)
COMPONENTS=("${@:-${ALL_COMPONENTS[@]}}")

check_memory() {
  local available
  available="$(free -m | awk 'NR==2 {print $7}')"
  if [[ -n "${available}" && "${available}" -lt "${MIN_FREE_MB}" ]]; then
    echo "Only ${available} MiB available (< ${MIN_FREE_MB}). Close something and retry." >&2
    echo "Top memory users:" >&2
    ps -eo comm,rss --sort=-rss | head -6 >&2
    exit 1
  fi
}

build_one() {
  local component="$1" context dockerfile
  if [[ "${component}" == "frontend" ]]; then
    context="${ROOT}/frontend"; dockerfile="${ROOT}/frontend/Dockerfile"
  else
    context="${ROOT}"; dockerfile="${ROOT}/services/${component}/Dockerfile"
  fi
  check_memory
  echo "==> building ${component}:${TAG}"
  docker build --file "${dockerfile}" --tag "${component}:${TAG}" "${context}"
  echo "==> loading ${component}:${TAG} into kind/${CLUSTER}"
  kind load docker-image "${component}:${TAG}" --name "${CLUSTER}"
}

command -v kind >/dev/null || { echo "kind is required: https://kind.sigs.k8s.io" >&2; exit 1; }
kind get clusters | grep -qx "${CLUSTER}" || {
  check_memory
  kind create cluster --config "${ROOT}/infra/k8s/kind/cluster.yaml"
}

for component in "${COMPONENTS[@]}"; do
  build_one "${component}"
done

echo "==> installing the chart"
helm upgrade --install claims-review "${ROOT}/infra/helm/claims-review" \
  --namespace "${NAMESPACE}" --create-namespace \
  --values "${ROOT}/infra/helm/claims-review/values-dev.yaml" \
  --set global.imageTag="${TAG}" \
  --wait --timeout 10m

kubectl -n "${NAMESPACE}" get pods
cat <<MSG

Ready. In two terminals:
  kubectl -n ${NAMESPACE} port-forward svc/claims-review-frontend 3000:3000
  kubectl -n ${NAMESPACE} port-forward svc/claims-review-claims-api 8000:8000
Tear down: kind delete cluster --name ${CLUSTER}
MSG
