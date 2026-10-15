#!/usr/bin/env bash
# Tira a foto do Spot no ManiSkill3 (WSL2). Argumentos extras são repassados ao script.
set -e
# No WSL não há driver Vulkan da NVIDIA; usa o lavapipe (Vulkan na CPU) do Mesa
export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json
source ~/envs/maniskill/bin/activate
python "$(dirname "$0")/spot_photo.py" "$@" 2> >(grep -v "Failed to find .* ICD file\|^  warn(" >&2)
