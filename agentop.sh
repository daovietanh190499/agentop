#!/bin/bash

# Usage function
usage() {
  echo "Usage: $0 {create|list|delete|exec} [options]"
  echo
  echo "Commands:"
  echo "  create    Create and install a Helm release."
  echo "  list      List all Helm releases."
  echo "  update    Upgrade an existing Helm release."
  echo "  delete    Uninstall a Helm release."
  echo "  exec      Execute a command in a running pod."
  echo
  echo "Options for create or update:"
  echo "  --release-name <name>   Helm release name (default: my-release)"
  echo "  --version <value>       Helm chart version (default: v0.2.0)"
  echo "  --image <repository>    Docker image repository (default: busybox)"
  echo "  --image-tag <tag>       Docker image tag (default: latest)"
  echo "  --command <cmd>         Command to run inside pod (default: sleep infinity)"
  echo "  --port <port>           POD's port to expose (default: 8000)"
  echo "  --volumes <volumes>     Persistent volume claims to mount (default: '')"
  echo "  --cpu-requests <value>  CPU requests (default: 1m)"
  echo "  --cpu-limits <value>    CPU limits (default: 1m)"
  echo "  --memory-requests <value> RAM requests (default: 1Gi)"
  echo "  --memory-limits <value>  RAM limits (default: 1Gi)"
  echo "  --physical-gpu <value>  Number of physical GPUs (default: 1)"
  echo "  --gpu-memory <value>     Memory request per GPU (default: 8000)"
  echo "  --kubeconfig <value>     Kubernetes config file (default: auto retrieve from $HOME/.kube/config)"
  echo
  echo "Options for delete:"
  echo "  --release-name <name>   Helm release name (required)"
  echo "  --kubeconfig <value>    Kubernetes config file (default: auto retrieve from $HOME/.kube/config)"
  echo
  echo "Options for exec:"
  echo "  --release-name <name>   Helm release name (required)"
  echo "  --kubeconfig <value>    Kubernetes config file (default: auto retrieve from $HOME/.kube/config)"
  echo "  --command <cmd>         Command to execute in the pod (required)"
  echo "  --namespace <namespace>  Namespace of the release (default: default)"
  echo
}

# Function to create and install a Helm release
create() {
  local RELEASE_NAME="my-release"
  local VERSION="v0.1.0"
  local IMAGE="busybox"
  local IMAGE_TAG="latest"
  local COMMAND="sleep infinity"
  local PORT="8000"
  local CPU_REQUESTS="1m"
  local CPU_LIMITS="1m"
  local MEMORY_REQUESTS="1Gi"
  local MEMORY_LIMITS="1Gi"
  local SERVER_PATH=""
  local SCRIPT=""
  local TTL="forever"
  local KUBECONFIG=""
  local KUBECONFIG_ARG=""

  # Parse arguments
  while [[ "$#" -gt 0 ]]; do
    case $1 in
      --release-name) RELEASE_NAME="$2"; shift ;;
      --version) VERSION="$2"; shift ;;
      --image) IMAGE="$2"; shift ;;
      --image-tag) IMAGE_TAG="$2"; shift ;;
      --command) COMMAND="$2"; shift ;;
      --port) PORT="$2"; shift ;;
      --cpu-requests) CPU_REQUESTS="$2"; shift ;;
      --cpu-limits) CPU_LIMITS="$2"; shift ;;
      --memory-requests) MEMORY_REQUESTS="$2"; shift ;;
      --memory-limits) MEMORY_LIMITS="$2"; shift ;;
      --server-path) SERVER_PATH="$2"; shift ;;
      --script) SCRIPT="$2"; shift ;;
      --ttl) TTL="$2"; shift ;;
      --kubeconfig) KUBECONFIG="$2"; shift ;;
      *) echo "Unknown option: $1"; usage; exit 1 ;;
    esac
    shift
  done

  local ttl_enable="false"

  if [ "$TTL" = "forever" ]; then
    ttl_enable="false"
  else
    ttl_enable="true"
  fi

  echo "TTL Cronjob enable: $ttl_enable"
  echo "TTL Cronjob schedule: +$TTL"

  [[ -n "$KUBECONFIG" ]] && KUBECONFIG_ARG="--kubeconfig=$KUBECONFIG"

  # Helm install command
  helm upgrade --install "$RELEASE_NAME" agenttop-tool-$VERSION/agentop-tool-$VERSION.tgz \
    --namespace "default" \
    --create-namespace \
    $KUBECONFIG_ARG \
    --set image.repository="$IMAGE" \
    --set image.tag="$IMAGE_TAG" \
    --set image.pullPolicy="Always" \
    --set container.command="$COMMAND" \
    --set service.type="NodePort" \
    --set service.port="$PORT" \
    --set ingress.enabled="true" \
    --set ingress.className="nginx" \
    --set ingress.annotations."kubernetes\.io/ingress\.class"="nginx" \
    --set ingress.annotations."cert-manager\.io/cluster-issuer"="letsencrypt-prod" \
    --set ingress.annotations."nginx\.ingress\.kubernetes\.io/proxy-body-size"='"0"' \
    --set ingress.annotations."nginx\.ingress\.kubernetes\.io/proxy-read-timeout"='"600"' \
    --set ingress.annotations."nginx\.ingress\.kubernetes\.io/proxy-send-timeout"='"600"' \
    --set ingress.hosts[0].host="$RELEASE_NAME.iai-ailab01" \
    --set ingress.hosts[0].paths[0].path="/" \
    --set ingress.hosts[0].paths[0].pathType="Prefix" \
    --set ingress.tls[0].secretName="$RELEASE_NAME" \
    --set ingress.tls[0].hosts[0]="$RELEASE_NAME.iai-ailab01" \
    --set ttl.create="$ttl_enable" \
    --set ttl.schedule="+$TTL" \
    --set resources.requests.cpu="$CPU_REQUESTS" \
    --set resources.requests.memory="$MEMORY_REQUESTS" \
    --set resources.limits.cpu="$CPU_LIMITS" \
    --set resources.limits.memory="$MEMORY_LIMITS" \
    --set server.path="$SERVER_PATH" \
    --set server."main\.py"="$SCRIPT"
}

# Function to list Helm releases
list() {
  local KUBECONFIG=""
  local KUBECONFIG_ARG
  # Parse arguments
  while [[ "$#" -gt 0 ]]; do
    case $1 in
      --kubeconfig) KUBECONFIG="$2"; shift ;;
      *) echo "Unknown option: $1"; usage; exit 1 ;;
    esac
    shift
  done
  [[ -n "$KUBECONFIG" ]] && KUBECONFIG_ARG="--kubeconfig=$KUBECONFIG"
  bash agentop-list.sh $KUBECONFIG_ARG
}

# Function to delete a Helm release
delete() {
  local RELEASE_NAME="my-release"
  local KUBECONFIG=""
  local KUBECONFIG_ARG=""

  # Parse arguments
  while [[ "$#" -gt 0 ]]; do
    case $1 in
      --release-name) RELEASE_NAME="$2"; shift ;;
      --kubeconfig) KUBECONFIG="$2"; shift ;;
      *) echo "Unknown option: $1"; usage; exit 1 ;;
    esac
    shift
  done

  if [ -z "$RELEASE_NAME" ]; then
    echo "Error: --release-name is required for delete."
    exit 1
  fi

  [[ -n "$KUBECONFIG" ]] && KUBECONFIG_ARG="--kubeconfig=$KUBECONFIG"

  # Helm uninstall command
  helm uninstall "$RELEASE_NAME" $KUBECONFIG_ARG
}

# Function to execute a command in a running pod
exec_cmd() {
  local RELEASE_NAME=""
  local COMMAND=""
  local NAMESPACE="default"
  local KUBECONFIG=""
  local KUBECONFIG_ARG=""

  # Parse arguments
B
  while [[ "$#" -gt 0 ]]; do
    case $1 in
      --release-name) RELEASE_NAME="$2"; shift ;;
      --command) COMMAND="$2"; shift ;;
      --namespace) NAMESPACE="$2"; shift ;;
      --kubeconfig) KUBECONFIG="$2"; shift ;;
      *) echo "Unknown option: $1"; usage; exit 1 ;;
    esac
    shift
  done

  if [ -z "$RELEASE_NAME" ]; then
    echo "Error: --release-name is required for exec."
    exit 1
  fi

  if [ -z "$COMMAND" ]; then
    echo "Error: --command is required for exec."
    exit 1
  fi

  if [[ "$RELEASE_NAME" == *agentop-tool* ]]; then
        RELEASE_NAME="$RELEASE_NAME"
  else
        RELEASE_NAME="${RELEASE_NAME}-agentop-tool"
  fi

  [[ -n "$KUBECONFIG" ]] && KUBECONFIG_ARG="--kubeconfig=$KUBECONFIG"

  # Execute command in the pod
  kubectl exec -it -n "$NAMESPACE" deploy/"$RELEASE_NAME" $KUBECONFIG_ARG -- $COMMAND
}

rollout-restart() {
  local KUBECONFIG=""
  local KUBECONFIG_ARG=""
  local RELEASE_NAME="default"
  local NAMESPACE="default"
  # Parse arguments
  while [[ "$#" -gt 0 ]]; do
    case $1 in
      --release-name) RELEASE_NAME="$2"; shift ;;
      --namespace) NAMESPACE="$2"; shift ;;
      --kubeconfig) KUBECONFIG="$2"; shift ;;
      *) echo "Unknown option: $1"; usage; exit 1 ;;
    esac
    shift
  done

  if [[ "$RELEASE_NAME" == *agentop-tool* ]]; then
        RELEASE_NAME="$RELEASE_NAME"
  else
        RELEASE_NAME="${RELEASE_NAME}-agentop-tool"
  fi

  [[ -n "$KUBECONFIG" ]] && KUBECONFIG_ARG="--kubeconfig=$KUBECONFIG"
  kubectl rollout restart -n "$NAMESPACE" deploy/"$RELEASE_NAME" $KUBECONFIG_ARG
}

# Main logic
if [[ "$#" -lt 1 ]]; then
  usage
  exit 1
fi

case $1 in
  create) shift; create "$@" ;;
  list) list ;;
  delete) shift; delete "$@" ;;
  exec) shift; exec_cmd "$@" ;;
  restart) shift; rollout-restart "$@" ;;
  *) echo "Unknown command: $1"; usage; exit 1 ;;
esac
