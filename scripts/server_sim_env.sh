#!/usr/bin/env bash

# Source this file before Isaac Sim work on the GPU server.
#
# Isaac Sim 6.0.1 requires Python 3.12, so it uses the h2r-sim prefix instead of
# the Python 3.10 environments that ROS2 Humble depends on. Do not source this
# together with scripts/server_ros2_env.sh; the two runtimes communicate over
# ROS2 messages, versioned files or an explicit RPC contract, not a shared
# interpreter.
#
# OMNI_KIT_ACCEPT_EULA records the user's acceptance of the NVIDIA Omniverse
# License Agreement, given on 2026-08-29. Without it every Kit bootstrap stops
# on an interactive prompt and fails under a non-interactive shell.
#
# Measured server values live in docs/server_environment.md.

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  echo "Usage: source $0" >&2
  exit 2
fi

HAND2ROBOT_PROJECT_ROOT="${HAND2ROBOT_PROJECT_ROOT:-/root/autodl-tmp/embodied}"
export HAND2ROBOT_PROJECT_ROOT

conda_profile="${CONDA_PROFILE:-/root/miniconda3/etc/profile.d/conda.sh}"
if [ ! -r "$conda_profile" ]; then
  echo "ERROR: conda profile not readable at $conda_profile" >&2
  return 1
fi
# shellcheck disable=SC1090
source "$conda_profile"

project_env="$HAND2ROBOT_PROJECT_ROOT/config/env.sh"
if [ -r "$project_env" ]; then
  # shellcheck disable=SC1090
  source "$project_env"
fi

export OMNI_KIT_ACCEPT_EULA=YES
export OMNI_KIT_CACHE_DIR="$HAND2ROBOT_PROJECT_ROOT/cache/isaac/kit"
export ISAAC_SIM_CACHE_ROOT="$HAND2ROBOT_PROJECT_ROOT/cache/isaac"

sim_prefix="$HAND2ROBOT_PROJECT_ROOT/envs/conda/h2r-sim"
if [ ! -x "$sim_prefix/bin/python" ]; then
  echo "ERROR: Isaac Sim environment missing at $sim_prefix" >&2
  return 1
fi
conda activate "$sim_prefix"
