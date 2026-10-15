"""Coloca o Boston Dynamics Spot em cena no MuJoCo e salva uma foto (PNG).

Usa o modelo do Spot do MuJoCo Menagerie (scene.xml: robô + chão + luz), baixado
automaticamente na primeira execução. O robô fica na pose em pé "home" do Menagerie;
a física não é executada.

Uso:
    python spot_photo.py                       # salva spot_mujoco.png ao lado do script
    python spot_photo.py --gui                 # abre o visualizador interativo após a foto
    python spot_photo.py --out foto.png --width 1920 --height 1080
"""

import argparse
import math
import os
import subprocess
from pathlib import Path

import mujoco
import numpy as np
from PIL import Image

parser = argparse.ArgumentParser(description="Foto do Spot no MuJoCo")
parser.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "spot_mujoco.png"))
parser.add_argument("--width", type=int, default=1280)
parser.add_argument("--height", type=int, default=720)
parser.add_argument("--gui", action="store_true", help="Abre o visualizador interativo depois de salvar a foto")
args = parser.parse_args()

MENAGERIE_URL = "https://github.com/google-deepmind/mujoco_menagerie.git"
CACHE_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "mujoco_menagerie"


def download_spot() -> Path:
    """Baixa só a pasta boston_dynamics_spot do Menagerie (clone esparso)."""
    spot_dir = CACHE_DIR / "boston_dynamics_spot"
    if not (spot_dir / "scene.xml").exists():
        print(f"[spot_photo] Baixando o Spot do Menagerie em {CACHE_DIR}...", flush=True)
        subprocess.run(
            ["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse", MENAGERIE_URL, str(CACHE_DIR)], check=True
        )
        subprocess.run(["git", "-C", str(CACHE_DIR), "sparse-checkout", "set", "boston_dynamics_spot"], check=True)
    return spot_dir


spot_dir = download_spot()
model = mujoco.MjModel.from_xml_path(str(spot_dir / "scene.xml"))
data = mujoco.MjData(model)

# Pose em pé "home" definida no spot.xml do Menagerie
mujoco.mj_resetDataKeyframe(model, data, model.key("home").id)
mujoco.mj_forward(model, data)
print(f"[spot_photo] Spot carregado: {model.nbody} corpos, {model.nv} DOFs", flush=True)

# O framebuffer fora da tela tem 640x480 por padrão; aumenta para o tamanho da foto
model.vis.global_.offwidth = max(model.vis.global_.offwidth, args.width)
model.vis.global_.offheight = max(model.vis.global_.offheight, args.height)

# Câmera em diagonal, olhando para o centro do robô (mesmo enquadramento das fotos do Isaac Sim e do Newton)
target = np.array([0.0, 0.0, 0.3])
cam_pos = np.array([1.6, -1.6, 0.9])
d = target - cam_pos
camera = mujoco.MjvCamera()
camera.type = mujoco.mjtCamera.mjCAMERA_FREE
camera.lookat[:] = target
camera.distance = float(np.linalg.norm(d))
camera.azimuth = math.degrees(math.atan2(d[1], d[0]))
camera.elevation = math.degrees(math.atan2(d[2], math.hypot(d[0], d[1])))

with mujoco.Renderer(model, height=args.height, width=args.width) as renderer:
    renderer.update_scene(data, camera=camera)
    image = renderer.render()

Image.fromarray(image).save(args.out)
print(f"[spot_photo] Foto salva em {args.out}", flush=True)

if args.gui:
    import mujoco.viewer

    with mujoco.viewer.launch_passive(model, data) as viewer:
        viewer.cam.lookat[:] = camera.lookat
        viewer.cam.distance = camera.distance
        viewer.cam.azimuth = camera.azimuth
        viewer.cam.elevation = camera.elevation
        while viewer.is_running():
            viewer.sync()
