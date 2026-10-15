"""Coloca o Boston Dynamics Spot em cena no Genesis e salva uma foto (PNG).

Roda no WSL2 (Ubuntu). O Genesis não tem um modelo próprio do Spot, então usamos o MJCF do
MuJoCo Menagerie (baixado automaticamente na primeira execução). O robô fica na pose em pé
"home" do Menagerie; a física não é executada.

Uso (dentro do WSL, com o ambiente ~/envs/genesis ativo):
    python spot_photo.py                       # salva spot_genesis.png ao lado do script
    python spot_photo.py --gui                 # abre o visualizador do Genesis após a foto
    python spot_photo.py --out foto.png --width 1920 --height 1080
"""

import argparse
import os
import subprocess
from pathlib import Path

import genesis as gs
from PIL import Image

parser = argparse.ArgumentParser(description="Foto do Spot no Genesis")
parser.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "spot_genesis.png"))
parser.add_argument("--width", type=int, default=1280)
parser.add_argument("--height", type=int, default=720)
parser.add_argument("--gui", action="store_true", help="Abre o visualizador do Genesis depois de salvar a foto")
args = parser.parse_args()

MENAGERIE_URL = "https://github.com/google-deepmind/mujoco_menagerie.git"
CACHE_DIR = Path.home() / ".cache" / "mujoco_menagerie"

# Keyframe "home" do spot.xml do Menagerie: base (x, y, z), quaternion (w, x, y, z) e (hx, hy, kn) de cada perna
HOME_QPOS = [0, 0, 0.46, 1, 0, 0, 0] + [0, 1.04, -1.8] * 4


def download_spot() -> Path:
    """Baixa só a pasta boston_dynamics_spot do Menagerie (clone esparso)."""
    spot_dir = CACHE_DIR / "boston_dynamics_spot"
    if not (spot_dir / "spot.xml").exists():
        print(f"[spot_photo] Baixando o Spot do Menagerie em {CACHE_DIR}...", flush=True)
        subprocess.run(
            ["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse", MENAGERIE_URL, str(CACHE_DIR)], check=True
        )
        subprocess.run(["git", "-C", str(CACHE_DIR), "sparse-checkout", "set", "boston_dynamics_spot"], check=True)
    return spot_dir


spot_dir = download_spot()

gs.init(backend=gs.gpu, logging_level="warning")

scene = gs.Scene(show_viewer=args.gui, renderer=gs.renderers.Rasterizer())
scene.add_entity(gs.morphs.Plane())
spot = scene.add_entity(gs.morphs.MJCF(file=str(spot_dir / "spot.xml")))

# Câmera em diagonal, olhando para o centro do robô (mesmo enquadramento das fotos dos outros simuladores)
camera = scene.add_camera(res=(args.width, args.height), pos=(1.6, -1.6, 0.9), lookat=(0.0, 0.0, 0.3), fov=45)

scene.build()
spot.set_qpos(HOME_QPOS)
print(f"[spot_photo] Spot carregado: {spot.n_links} corpos, {spot.n_dofs} DOFs", flush=True)

rgb, *_ = camera.render(rgb=True)
Image.fromarray(rgb).save(args.out)
print(f"[spot_photo] Foto salva em {args.out}", flush=True)

if args.gui:
    while scene.viewer.is_alive():
        scene.visualizer.update()
