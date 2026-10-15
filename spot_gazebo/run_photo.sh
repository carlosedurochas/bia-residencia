#!/usr/bin/env bash
# Tira a foto do Spot no Gazebo Harmonic (WSL2).
#   bash run_photo.sh            salva spot_gazebo.png ao lado deste script
#   bash run_photo.sh --gui      abre também a interface do Gazebo (feche a janela para terminar)
set -e
cd "$(dirname "$0")"

export MAMBA_ROOT_PREFIX=~/micromamba
eval "$(~/.local/bin/micromamba shell hook -s bash)"
micromamba activate gazebo

FRAMES=/tmp/spot_gazebo_frames
TOPIC=/world/spot_photo/model/photographer/link/link/sensor/photo_camera/image
rm -rf "$FRAMES"

if [ "$1" = "--gui" ]; then
  gz sim -r spot_photo.sdf > /tmp/spot_gazebo.log 2>&1 &
else
  gz sim -s -r spot_photo.sdf > /tmp/spot_gazebo.log 2>&1 &
fi
GZ_PID=$!

# O Gazebo só renderiza uma câmera quando há alguém inscrito no tópico de imagem dela;
# o <save> do SDF sozinho não basta. Esperamos 3 imagens (a primeira pode sair antes da cena carregar).
if ! timeout 300 gz topic -e -t "$TOPIC" -n 3 > /dev/null 2>&1; then
  echo "[spot_photo] A câmera não publicou imagens em 300 s. Veja /tmp/spot_gazebo.log" >&2
  kill $GZ_PID 2>/dev/null
  exit 1
fi

if [ "$1" = "--gui" ]; then
  echo "[spot_photo] Feche a janela do Gazebo para salvar a foto."
  wait $GZ_PID
else
  kill $GZ_PID
  wait $GZ_PID 2>/dev/null || true
fi

# A imagem mais recente pode ter ficado pela metade (o Gazebo grava enquanto o tópico já publicou);
# copia a mais recente que abre sem erro
python - "$FRAMES" spot_gazebo.png <<'EOF'
import sys
from pathlib import Path
from PIL import Image

frames = sorted(Path(sys.argv[1]).glob("*.png"), key=lambda p: int(p.stem.rsplit("_", 1)[-1]), reverse=True)
for frame in frames:
    try:
        Image.open(frame).convert("RGB").save(sys.argv[2])
        print(f"[spot_photo] Foto salva em {Path(sys.argv[2]).resolve()} (quadro {frame.name})")
        break
    except OSError:
        continue
else:
    sys.exit("[spot_photo] Nenhuma imagem válida foi gravada.")
EOF
