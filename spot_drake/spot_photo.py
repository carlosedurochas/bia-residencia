"""Coloca o Boston Dynamics Spot em cena no Drake e salva uma foto (PNG).

Roda no WSL2 (Ubuntu). O Drake não tem um modelo próprio do Spot, então usamos o MJCF do
MuJoCo Menagerie (baixado automaticamente na primeira execução), importado pelo parser de MJCF
do Drake. A foto sai de um sensor RGB-D (RgbdSensor) renderizado com VTK. O robô fica na pose
em pé "home" do Menagerie; a física não é executada.

Uso (dentro do WSL, com o ambiente ~/envs/drake ativo):
    python spot_photo.py                       # salva spot_drake.png ao lado do script
    python spot_photo.py --out foto.png --width 1920 --height 1080
"""

import argparse
import math
import os
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image
from pydrake.geometry import (
    ClippingRange,
    ColorRenderCamera,
    DepthRange,
    DepthRenderCamera,
    HalfSpace,
    LightParameter,
    MakeRenderEngineVtk,
    RenderCameraCore,
    RenderEngineVtkParams,
)
from pydrake.math import RigidTransform, RotationMatrix
from pydrake.multibody.parsing import Parser
from pydrake.multibody.plant import AddMultibodyPlantSceneGraph
from pydrake.systems.framework import DiagramBuilder
from pydrake.systems.sensors import CameraInfo, RgbdSensor

parser = argparse.ArgumentParser(description="Foto do Spot no Drake")
parser.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "spot_drake.png"))
parser.add_argument("--width", type=int, default=1280)
parser.add_argument("--height", type=int, default=720)
args = parser.parse_args()

MENAGERIE_URL = "https://github.com/google-deepmind/mujoco_menagerie.git"
CACHE_DIR = Path.home() / ".cache" / "mujoco_menagerie"

# Keyframe "home" do spot.xml do Menagerie: altura da base e ângulo de cada tipo de junta
BASE_HEIGHT = 0.46
HOME_JOINT_ANGLES = {"hx": 0.0, "hy": 1.04, "kn": -1.8}
LEGS = ("fl", "fr", "hl", "hr")

# Câmera em diagonal, olhando para o centro do robô (mesmo enquadramento das fotos dos outros simuladores)
CAM_POS = np.array([1.6, -1.6, 0.9])
TARGET = np.array([0.0, 0.0, 0.3])
FOV_Y = math.radians(45)


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


def camera_pose(eye: np.ndarray, target: np.ndarray) -> RigidTransform:
    """Pose da câmera no mundo. No Drake a câmera olha para +z, com +x à direita e +y para baixo."""
    z = (target - eye) / np.linalg.norm(target - eye)
    x = np.cross(z, [0.0, 0.0, 1.0])
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    return RigidTransform(RotationMatrix(np.column_stack([x, y, z])), eye)


spot_dir = download_spot()

builder = DiagramBuilder()
plant, scene_graph = AddMultibodyPlantSceneGraph(builder, time_step=0.0)
(spot,) = Parser(plant).AddModels(str(spot_dir / "spot.xml"))
plant.RegisterVisualGeometry(
    plant.world_body(), RigidTransform(), HalfSpace(), "ground", np.array([0.55, 0.6, 0.65, 1.0])
)
plant.Finalize()

renderer = "vtk"
# A luz padrão do VTK sai da câmera e deixa o chão quase preto; adiciona uma luz direcional vinda de cima
vtk_params = RenderEngineVtkParams()
vtk_params.lights = [
    LightParameter(type="directional", frame="world", direction=[0.3, 0.4, -1.0], intensity=1.0),
    LightParameter(type="directional", frame="camera", direction=[0.0, 0.0, 1.0], intensity=0.5),
]
scene_graph.AddRenderer(renderer, MakeRenderEngineVtk(vtk_params))
core = RenderCameraCore(
    renderer, CameraInfo(args.width, args.height, FOV_Y), ClippingRange(0.01, 100.0), RigidTransform()
)
sensor = builder.AddSystem(
    RgbdSensor(
        parent_id=scene_graph.world_frame_id(),
        X_PB=camera_pose(CAM_POS, TARGET),
        color_camera=ColorRenderCamera(core, show_window=False),
        depth_camera=DepthRenderCamera(core, DepthRange(0.01, 100.0)),
    )
)
builder.Connect(scene_graph.get_query_output_port(), sensor.query_object_input_port())
diagram = builder.Build()

context = diagram.CreateDefaultContext()
plant_context = plant.GetMyMutableContextFromRoot(context)
plant.SetFreeBodyPose(plant_context, plant.GetBodyByName("body", spot), RigidTransform([0.0, 0.0, BASE_HEIGHT]))
for leg in LEGS:
    for joint, angle in HOME_JOINT_ANGLES.items():
        plant.GetJointByName(f"{leg}_{joint}", spot).set_angle(plant_context, angle)
print(f"[spot_photo] Spot carregado: {plant.num_bodies() - 1} corpos, {plant.num_velocities()} DOFs", flush=True)

image = sensor.color_image_output_port().Eval(sensor.GetMyContextFromRoot(context))
Image.fromarray(np.array(image.data)[:, :, :3]).save(args.out)
print(f"[spot_photo] Foto salva em {args.out}", flush=True)
