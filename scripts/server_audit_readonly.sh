#!/usr/bin/env bash

set -u

run_if_available() {
  command_name="$1"
  shift
  printf '\n[%s]\n' "$command_name"
  if command -v "$command_name" >/dev/null 2>&1; then
    "$command_name" "$@" 2>&1 || true
  else
    printf 'NOT_FOUND\n'
  fi
}

printf '[audit_metadata]\n'
date --iso-8601=seconds 2>&1 || true
printf 'read_only=true\n'
printf 'repository_commit='
git rev-parse HEAD 2>&1 || true
printf 'repository_branch='
git branch --show-current 2>&1 || true

run_if_available hostnamectl
run_if_available uname -a
printf '\n[os_release]\n'
if [ -r /etc/os-release ]; then
  sed -n '1,80p' /etc/os-release
else
  printf 'NOT_READABLE\n'
fi
run_if_available nvidia-smi
run_if_available free -h
run_if_available lscpu
run_if_available lsblk -f
run_if_available df -hT
run_if_available df -i
run_if_available python3 --version
run_if_available git --version
run_if_available docker version
run_if_available podman version
run_if_available ip -brief address

printf '\n[audit_end]\n'
printf 'No state-changing command was requested by this script.\n'
