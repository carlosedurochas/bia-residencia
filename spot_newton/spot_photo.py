"""Coloca o Boston Dynamics Spot em cena no Newton e salva uma foto (PNG).

O Newton não tem um modelo próprio do Spot, então usamos o MJCF do MuJoCo Menagerie
(baixado automaticamente na primeira execução). O robô fica na pose em pé "home"
do Menagerie; a física não é executada.

Uso:
    python spot_photo.py                       # salva spot_newton.png ao lado do script
    python spot_photo.py --gui                 # abre a janela do visualizador após a foto
    python spot_photo.py --out foto.png --width 1920 --height 1080
"""

import argparse
import math
import os

import numpy as np
import warp as wp
from PIL import Image

import newton
# API interna: a pública (newton.utils.download_asset) só baixa do newton-assets, que não tem o Spot
from newton._src.utils.download_assets import download_git_folder
from newton.viewer import ViewerGL

parser = argparse.ArgumentParser(description="Foto do Spot no Newton")
parser.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "spot_newton.png"))
parser.add_argument("--width", type=int, default=1280)
parser.add_argument("--height", type=int, default=720)
parser.add_argument("--gui", action="store_true", help="Mantém a janela aberta depois de salvar a foto")
args = parser.parse_args()

MENAGERIE_URL = "https://github.com/google-deepmind/mujoco_menagerie.git"

# Pose "home" do spot.xml do Menagerie: altura da base e (hx, hy, kn) de cada perna
BASE_HEIGHT = 0.46
LEG_POSE = [0.0, 1.04, -1.8]

spot_dir = download_git_folder(MENAGERIE_URL, "boston_dynamics_spot")

builder = newton.ModelBuilder(up_axis=newton.Axis.Z)
builder.add_mjcf(str(spot_dir / "spot.xml"), enable_self_collisions=False)
builder.add_ground_plane()

# Base flutuante: posição (x, y, z) + quaternion (x, y, z, w); depois as 12 juntas das pernas
builder.joint_q[:7] = [0.0, 0.0, BASE_HEIGHT, 0.0, 0.0, 0.0, 1.0]
builder.joint_q[7:19] = LEG_POSE * 4

model = builder.finalize()
state = model.state()
newton.eval_fk(model, model.joint_q, model.joint_qd, state)
print(f"[spot_photo] Spot carregado: {model.body_count} corpos, {model.joint_dof_count} DOFs", flush=True)

viewer = ViewerGL(width=args.width, height=args.height, headless=not args.gui)
viewer.set_model(model)

# Câmera em diagonal, olhando para o centro do robô (mesmo enquadramento da foto do Isaac Sim)
target = np.array([0.0, 0.0, 0.3])
cam_pos = np.array([1.6, -1.6, 0.9])
d = target - cam_pos
yaw = math.degrees(math.atan2(d[1], d[0]))
pitch = math.degrees(math.atan2(d[2], math.hypot(d[0], d[1])))
viewer.set_camera(wp.vec3(*cam_pos), pitch=pitch, yaw=yaw)

for _ in range(3):  # alguns frames para o renderizador estabilizar
    viewer.begin_frame(0.0)
    viewer.log_state(state)
    viewer.end_frame()

image = viewer.get_frame().numpy()
Image.fromarray(image).save(args.out)
print(f"[spot_photo] Foto salva em {args.out}", flush=True)

if args.gui:
    while viewer.is_running():
        viewer.begin_frame(0.0)
        viewer.log_state(state)
        viewer.end_frame()

viewer.close()
