#!/usr/bin/env bash
set -euo pipefail
umask 077

for name in BACKUP_EXPORT_TOKEN BACKUP_API_URL RUNNER_TEMP; do
  if [[ -z "${!name:-}" ]]; then
    echo "Missing backup configuration: $name" >&2
    exit 1
  fi
done

max_bytes="${MAX_BACKUP_BYTES:-26214400}"
if ! [[ "$max_bytes" =~ ^[0-9]+$ ]] || (( max_bytes < 1 )); then
  echo "MAX_BACKUP_BYTES must be a positive integer" >&2
  exit 1
fi

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
encrypted="$RUNNER_TEMP/sauditritons-$stamp.dump.age"
backup_ready=0
trap 'if [[ "$backup_ready" != 1 ]]; then rm -f "$encrypted"; fi' EXIT

# The backend creates, validates, and encrypts the dump inside Railway's
# private network. The GitHub runner only receives the encrypted bytes.
curl --fail --silent --show-error \
  --connect-timeout 10 --max-time 180 --max-filesize "$max_bytes" \
  --request POST \
  --header "Authorization: Bearer $BACKUP_EXPORT_TOKEN" \
  --output "$encrypted" \
  "$BACKUP_API_URL"

actual_bytes="$(wc -c < "$encrypted" | tr -d ' ')"
if (( actual_bytes > max_bytes )); then
  echo "Encrypted backup exceeds the artifact size cap" >&2
  exit 1
fi
if [[ "$(head -c 21 "$encrypted")" != "age-encryption.org/v1" ]]; then
  echo "Backend did not return an age-encrypted backup" >&2
  exit 1
fi

if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  printf 'artifact_path=%s\n' "$encrypted" >> "$GITHUB_OUTPUT"
fi
backup_ready=1
echo "Validated encrypted backup: $actual_bytes bytes"
