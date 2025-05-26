#!/bin/bash

# Default: no custom kubeconfig, use system default
KUBECONFIG_ARG=""

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --kubeconfig)
            shift
            if [[ -n "$1" ]]; then
                KUBECONFIG_ARG="--kubeconfig=$1"
                shift
            else
                echo "❌ Missing path for --kubeconfig"
                exit 1
            fi
            ;;
        *)
            echo "❌ Invalid argument: $1"
            echo "✅ Usage: $0 [--kubeconfig <path>]"
            exit 1
            ;;
    esac
done

NOW=$(date -u +%s)

# Print header
printf "%-20s %-20s %-5s %-20s %-40s %-10s %-20s %-12s\n" \
  "NAME" "IMAGE" "READY" "LAST DEPLOYED" "URL" "SCHEDULE" "EXPIRED DATETIME" "REMAIN (m)"
printf "%-20s %-20s %-5s %-20s %-40s %-10s %-20s %-12s\n" \
  "--------------------" "--------------------" "-----" "--------------------" "----------------------------------------" "----------" "--------------------" "------------"

# Get release names
release_names=$(helm list $KUBECONFIG_ARG -o json | jq -r '.[]?.name')

for release in $release_names; do
  status_json=$(helm $KUBECONFIG_ARG status "$release" -o json 2>/dev/null)
  if [ -z "$status_json" ]; then
    continue
  fi

  # Extract values
  last_deployed_raw=$(echo "$status_json" | jq -r '.info.last_deployed')
  url=$(echo "$status_json" | jq -r '.config.ingress.hosts[0].host // "None"')
  schedule=$(echo "$status_json" | jq -r '.config.ttl.schedule // "None"')
  image=$(echo "$status_json" | jq -r '.config.image.repository // "None"')

  # Convert timestamp to supported format: YYYY-MM-DD HH:MM:SS
  last_deployed_fmt=$(echo "$last_deployed_raw" | sed -E 's/T/ /; s/\..*Z//')
  deployed_epoch=$(date -d "$last_deployed_fmt" +%s 2>/dev/null)
  if [ -z "$deployed_epoch" ]; then
    continue
  fi

  # Convert schedule to total minutes
  schedule_minutes=0
  if [[ "$schedule" =~ \+([0-9]+)h ]]; then
    schedule_minutes=$((schedule_minutes + ${BASH_REMATCH[1]} * 60))
  fi
  if [[ "$schedule" =~ \+([0-9]+)m ]]; then
    schedule_minutes=$((schedule_minutes + ${BASH_REMATCH[1]}))
  fi

  expired_epoch=$((deployed_epoch + schedule_minutes * 60))
  expired_datetime=$(date -u -d "@$expired_epoch" '+%Y-%m-%d %H:%M:%S')
  remaining_minutes=$(( (expired_epoch - NOW) / 60 ))

  if [[ "$release" == *agentop-tool* ]]; then
      deploy_name="$release"
  else
      deploy_name="${release}-agentop-tool"
  fi

  deploy_json=$(kubectl $KUBECONFIG_ARG get deploy "$deploy_name" -o json 2>/dev/null)
  if [[ -z "$deploy_json" ]]; then
      ready="N/A"
  else
      ready_replicas=$(echo "$deploy_json" | jq -r '.status.readyReplicas // 0')
      total_replicas=$(echo "$deploy_json" | jq -r '.status.replicas // 0')
      ready="${ready_replicas}/${total_replicas}"
  fi

  # Print row
  printf "%-20s %-20s %-5s %-20s %-40s %-10s %-20s %-12d\n" \
    "$release" "$image" "$ready" "$last_deployed_fmt" "$url" "$schedule" "$expired_datetime" "$remaining_minutes"
done
