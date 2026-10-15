"""Coloca o Boston Dynamics Spot em cena no ManiSkill3 (SAPIEN) e salva uma foto (PNG).

Roda no WSL2 (Ubuntu). O ManiSkill não tem um modelo do Spot, então o script registra um agente
"spot_menagerie" a partir do MJCF do MuJoCo Menagerie (baixado automaticamente na primeira execução),
do mesmo jeito que o ManiSkill define os robôs dele (ex.: UR10e, Humanoid). O robô fica na pose em pé
"home" do Menagerie; a física não é executada.

Uso (dentro do WSL, com o ambiente ~/envs/maniskill ativo):
    python spot_photo.py                       # salva spot_maniskill.png ao lado do script
    python spot_photo.py --out foto.png --width 1920 --height 1080
"""

import argparse
import os
import subprocess
from pathlib import Path

import numpy as np
import sapien
from PIL import Image

from mani_skill.agents.base_agent import BaseAgent, Keyframe
from mani_skill.agents.controllers import PDJointPosControllerConfig
from mani_skill.agents.registration import register_agent
from mani_skill.envs.sapien_env import BaseEnv
from mani_skill.sensors.camera import CameraConfig
from mani_skill.utils import sapien_utils
from mani_skill.utils.building.ground import build_ground

parser = argparse.ArgumentParser(description="Foto do Spot no ManiSkill3")
parser.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "spot_maniskill.png"))
parser.add_argument("--width", type=int, default=1280)
parser.add_argument("--height", type=int, default=720)
args = parser.parse_args()

MENAGERIE_URL = "https://github.com/google-deepmind/mujoco_menagerie.git"
CACHE_DIR = Path.home() / ".cache" / "mujoco_menagerie"


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


SPOT_DIR = download_spot()


@register_agent()
class SpotMenagerie(BaseAgent):
    uid = "spot_menagerie"
    mjcf_path = str(SPOT_DIR / "spot.xml")
    fix_root_link = False  # base flutuante, como um robô com pernas

    # Keyframe "home" do spot.xml do Menagerie: base a 0,46 m e (hx, hy, kn) de cada perna.
    # O qpos fica vazio aqui porque a ordem das juntas no SAPIEN só é conhecida depois de carregar o robô.
    keyframes = dict(home=Keyframe(pose=sapien.Pose(p=[0.0, 0.0, 0.46]), qpos=np.zeros(12)))
    home_joint_angles = {"hx": 0.0, "hy": 1.04, "kn": -1.8}

    @property
    def _controller_configs(self):
        # Controle de posição por junta (não é usado na foto, mas todo agente do ManiSkill precisa de um)
        return dict(
            pd_joint_pos=PDJointPosControllerConfig(
                [j.name for j in self.robot.active_joints],
                lower=None,
                upper=None,
                stiffness=500,
                damping=20,
                normalize_action=False,
            )
        )


class SpotPhotoEnv(BaseEnv):
    """Ambiente mínimo: chão, o Spot e uma câmera para a foto."""

    def __init__(self, *env_args, **kwargs):
        super().__init__(*env_args, robot_uids=SpotMenagerie.uid, **kwargs)

    @property
    def _default_human_render_camera_configs(self):
        # Câmera em diagonal, olhando para o centro do robô (mesmo enquadramento das fotos dos outros simuladores)
        return CameraConfig(
            "photo",
            pose=sapien_utils.look_at(eye=[1.6, -1.6, 0.9], target=[0.0, 0.0, 0.3]),
            width=args.width,
            height=args.height,
            fov=np.deg2rad(45),
            near=0.01,
            far=100,
        )

    def _load_scene(self, options: dict):
        build_ground(self.scene)

    def _initialize_episode(self, env_idx, options: dict):
        home = self.agent.keyframes["home"]
        robot = self.agent.robot
        robot.set_pose(home.pose)
        # O SAPIEN ordena as juntas por largura (todos os hx, depois hy, depois kn), não na ordem do XML;
        # por isso a pose é montada pelo sufixo do nome de cada junta (fl_hx, fl_hy, fl_kn, ...)
        angles = self.agent.home_joint_angles
        robot.set_qpos(np.array([angles[j.name.split("_")[-1]] for j in robot.active_joints]))
        # O carregador de MJCF cria uma raiz extra (dummy_root) e mantém o pos="0 0 .75" do <body> do Spot,
        # que no MuJoCo é substituído pela freejoint. Desce a raiz para que o corpo fique na altura do keyframe.
        body = next(link for link in robot.get_links() if link.name == "body")
        offset = float(body.pose.p[0, 2] - robot.pose.p[0, 2])
        robot.set_pose(sapien.Pose(p=[0.0, 0.0, float(home.pose.p[2]) - offset]))


# No WSL não há driver Vulkan da NVIDIA: a renderização usa o lavapipe (Vulkan na CPU), daí render_backend="cpu"
env = SpotPhotoEnv(render_mode="rgb_array", sim_backend="cpu", render_backend="cpu")
env.reset(seed=0)
robot = env.agent.robot
print(f"[spot_photo] Spot carregado: {len(robot.get_links())} corpos, {len(robot.active_joints)} juntas ativas", flush=True)

image = env.render()[0].cpu().numpy()
Image.fromarray(image).save(args.out)
print(f"[spot_photo] Foto salva em {args.out}", flush=True)
env.close()
