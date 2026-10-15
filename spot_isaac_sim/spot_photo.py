"""Coloca o Boston Dynamics Spot em cena no Isaac Sim 5.0 e salva uma foto (PNG).

O robô fica parado na pose padrão do USD (a física não é executada).

Uso:
    python spot_photo.py                       # salva spot_isaac_sim.png ao lado do script
    python spot_photo.py --gui                 # abre a janela do simulador após a foto
    python spot_photo.py --out foto.png --width 1920 --height 1080
"""

import argparse
import os

parser = argparse.ArgumentParser(description="Foto do Spot no Isaac Sim")
parser.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "spot_isaac_sim.png"))
parser.add_argument("--width", type=int, default=1280)
parser.add_argument("--height", type=int, default=720)
parser.add_argument("--gui", action="store_true", help="Mantém a janela aberta depois de salvar a foto")
args = parser.parse_args()

# O SimulationApp precisa ser criado antes de qualquer import do omni/isaacsim
from isaacsim import SimulationApp

simulation_app = SimulationApp({"headless": not args.gui, "width": args.width, "height": args.height})

import numpy as np
import omni.replicator.core as rep
import omni.usd
from isaacsim.core.prims import SingleXFormPrim
from isaacsim.core.utils.stage import add_reference_to_stage, create_new_stage
from isaacsim.storage.native import get_assets_root_path
from PIL import Image
from pxr import Gf, Usd, UsdGeom, UsdLux

SPOT_USD = "/Isaac/Robots/BostonDynamics/spot/spot.usd"
GRID_USD = "/Isaac/Environments/Grid/default_environment.usd"
PRIM_PATH = "/World/Spot"

assets_root_path = get_assets_root_path()
if assets_root_path is None:
    print("[spot_photo] Não foi possível localizar os assets do Isaac Sim (verifique a conexão).", flush=True)
    simulation_app.close()
    raise SystemExit(1)

create_new_stage()
stage = omni.usd.get_context().get_stage()
UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)

# Chão em grade + iluminação
add_reference_to_stage(usd_path=assets_root_path + GRID_USD, prim_path="/World/Ground")
UsdLux.DomeLight.Define(stage, "/World/DomeLight").CreateIntensityAttr(1000.0)
sun = UsdLux.DistantLight.Define(stage, "/World/Sun")
sun.CreateIntensityAttr(2500.0)
UsdGeom.Xformable(sun).AddRotateXYZOp().Set(Gf.Vec3f(-45.0, 0.0, 30.0))

# Spot
add_reference_to_stage(usd_path=assets_root_path + SPOT_USD, prim_path=PRIM_PATH)
for _ in range(10):  # deixa o USD terminar de carregar
    simulation_app.update()

# Apoia o robô no chão: desloca para que o ponto mais baixo fique em z = 0
spot_prim = stage.GetPrimAtPath(PRIM_PATH)
bbox = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_]).ComputeWorldBound(spot_prim).ComputeAlignedRange()
SingleXFormPrim(PRIM_PATH).set_world_pose(position=np.array([0.0, 0.0, -bbox.GetMin()[2]]))
center = (bbox.GetMin() + bbox.GetMax()) / 2.0
target = (center[0], center[1], (bbox.GetMax()[2] - bbox.GetMin()[2]) / 2.0)
print(f"[spot_photo] Spot carregado. Dimensões (m): {np.round(list(bbox.GetSize()), 3)}", flush=True)

# Câmera em diagonal, olhando para o centro do robô
camera = rep.create.camera(position=(target[0] + 1.6, target[1] - 1.6, target[2] + 0.9), look_at=target)
render_product = rep.create.render_product(camera, (args.width, args.height))
rgb = rep.AnnotatorRegistry.get_annotator("rgb")
rgb.attach(render_product)

rep.orchestrator.set_capture_on_play(False)
for _ in range(30):  # alguns frames para o renderizador convergir (texturas e sombras)
    rep.orchestrator.step(rt_subframes=4)

image = np.asarray(rgb.get_data())[:, :, :3]
Image.fromarray(image).save(args.out)
print(f"[spot_photo] Foto salva em {args.out}", flush=True)

rgb.detach()
render_product.destroy()

if args.gui:
    while simulation_app.is_running():
        simulation_app.update()

simulation_app.close()
