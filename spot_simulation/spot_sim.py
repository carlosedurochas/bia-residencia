"""Simulação simples do Boston Dynamics Spot no Isaac Sim 5.0.

Carrega o asset Isaac/Robots/BostonDynamics/spot/spot.usd sobre um plano de chão
e o faz caminhar usando a política de locomoção (RL) que acompanha o Isaac Sim.

Uso:
    python spot_sim.py                 # sequência automática de comandos
    python spot_sim.py --keyboard      # controle pelo teclado
    python spot_sim.py --no-policy     # só carrega o robô (sem controlador; ele cai)
    python spot_sim.py --headless --duration 10
"""

import argparse

parser = argparse.ArgumentParser(description="Simulação do Spot no Isaac Sim")
parser.add_argument("--headless", action="store_true", help="Executa sem interface gráfica")
parser.add_argument("--keyboard", action="store_true", help="Controla o Spot pelo teclado")
parser.add_argument("--no-policy", action="store_true", help="Apenas carrega o USD, sem política de caminhada")
parser.add_argument("--duration", type=float, default=0.0, help="Encerra após N segundos simulados (0 = infinito)")
args = parser.parse_args()

# O SimulationApp precisa ser criado antes de qualquer import do omni/isaacsim
from isaacsim import SimulationApp

simulation_app = SimulationApp({"headless": args.headless})

import carb
import numpy as np
import omni.appwindow
from isaacsim.core.api import World
from isaacsim.storage.native import get_assets_root_path

PHYSICS_DT = 1.0 / 500.0  # a política foi treinada a 500 Hz (decimação 10 -> 50 Hz)
RENDERING_DT = 10.0 / 500.0
SPOT_USD = "/Isaac/Robots/BostonDynamics/spot/spot.usd"
PRIM_PATH = "/World/Spot"

assets_root_path = get_assets_root_path()
if assets_root_path is None:
    carb.log_error("Não foi possível localizar a pasta de assets do Isaac Sim (verifique a conexão).")
    simulation_app.close()
    raise SystemExit(1)

world = World(stage_units_in_meters=1.0, physics_dt=PHYSICS_DT, rendering_dt=RENDERING_DT)
world.scene.add_default_ground_plane(
    z_position=0, name="default_ground_plane", prim_path="/World/defaultGroundPlane",
    static_friction=0.2, dynamic_friction=0.2, restitution=0.01,
)

# Comando da base: [v_x (m/s), v_y (m/s), w_z (rad/s)]
base_command = np.zeros(3)

if args.no_policy:
    from isaacsim.core.prims import SingleArticulation
    from isaacsim.core.utils.stage import add_reference_to_stage

    add_reference_to_stage(usd_path=assets_root_path + SPOT_USD, prim_path=PRIM_PATH)
    spot = world.scene.add(SingleArticulation(prim_path=PRIM_PATH, name="spot", position=np.array([0, 0, 0.8])))
else:
    from isaacsim.robot.policy.examples.robots import SpotFlatTerrainPolicy

    spot = SpotFlatTerrainPolicy(
        prim_path=PRIM_PATH,
        name="spot",
        usd_path=assets_root_path + SPOT_USD,
        position=np.array([0, 0, 0.8]),
    )

# --- Comandos ---------------------------------------------------------------

# Sequência automática: (duração em s, [v_x, v_y, w_z])
SCRIPTED_COMMANDS = [
    (2.0, [0.0, 0.0, 0.0]),   # parado (estabiliza)
    (4.0, [1.0, 0.0, 0.0]),   # anda para frente
    (3.0, [0.0, 0.0, 1.0]),   # gira para a esquerda
    (4.0, [1.0, 0.0, 0.0]),   # anda para frente
    (3.0, [0.0, 0.5, 0.0]),   # anda de lado
    (3.0, [0.0, 0.0, -1.0]),  # gira para a direita
]
SCRIPT_CYCLE = sum(d for d, _ in SCRIPTED_COMMANDS)


def scripted_command(t: float) -> np.ndarray:
    t = t % SCRIPT_CYCLE
    for duration, cmd in SCRIPTED_COMMANDS:
        if t < duration:
            return np.array(cmd)
        t -= duration
    return np.zeros(3)


# Teclado: setas / numpad -> frente/trás, lateral, giro
KEY_TO_COMMAND = {
    "UP": [1.0, 0.0, 0.0], "NUMPAD_8": [1.0, 0.0, 0.0],
    "DOWN": [-1.0, 0.0, 0.0], "NUMPAD_2": [-1.0, 0.0, 0.0],
    "RIGHT": [0.0, -1.0, 0.0], "NUMPAD_6": [0.0, -1.0, 0.0],
    "LEFT": [0.0, 1.0, 0.0], "NUMPAD_4": [0.0, 1.0, 0.0],
    "N": [0.0, 0.0, 1.0], "NUMPAD_7": [0.0, 0.0, 1.0],
    "M": [0.0, 0.0, -1.0], "NUMPAD_9": [0.0, 0.0, -1.0],
}


def on_keyboard_event(event, *_args) -> bool:
    global base_command
    # event.input pode ser um KeyboardInput (enum) ou uma str (eventos de caractere)
    name = getattr(event.input, "name", event.input)
    if name in KEY_TO_COMMAND:
        if event.type == carb.input.KeyboardEventType.KEY_PRESS:
            base_command = base_command + np.array(KEY_TO_COMMAND[name])
        elif event.type == carb.input.KeyboardEventType.KEY_RELEASE:
            base_command = base_command - np.array(KEY_TO_COMMAND[name])
    return True


if args.keyboard and not args.headless:
    appwindow = omni.appwindow.get_default_app_window()
    input_iface = carb.input.acquire_input_interface()
    keyboard_sub = input_iface.subscribe_to_keyboard_events(appwindow.get_keyboard(), on_keyboard_event)
    print("[spot_sim] Teclado: setas = andar/lateral, N/M = girar")

# --- Loop de simulação -----------------------------------------------------

first_step = True
sim_time = 0.0


def on_physics_step(step_size: float) -> None:
    global first_step, sim_time, base_command
    if first_step:
        spot.initialize()
        first_step = False
        return
    sim_time += step_size
    if not args.keyboard:
        base_command = scripted_command(sim_time)
    spot.forward(step_size, base_command)


world.reset()
if args.no_policy:
    spot.initialize()
else:
    world.add_physics_callback("spot_policy_step", callback_fn=on_physics_step)

reset_needed = False
while simulation_app.is_running():
    world.step(render=True)
    if world.is_stopped() and not reset_needed:
        reset_needed = True
    if world.is_playing() and reset_needed:
        world.reset()
        first_step, sim_time, reset_needed = True, 0.0, False
    if args.duration and world.current_time >= args.duration:
        pos, _ = spot.robot.get_world_pose() if not args.no_policy else spot.get_world_pose()
        print(f"[spot_sim] Fim após {world.current_time:.1f}s. Posição final do Spot: {np.round(pos, 3)}", flush=True)
        break

simulation_app.close()
