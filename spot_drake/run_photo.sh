#!/usr/bin/env bash
# Tira a foto do Spot no Drake (WSL2). Argumentos extras são repassados ao script.
set -e
source ~/envs/drake/bin/activate
python "$(dirname "$0")/spot_photo.py" "$@"
