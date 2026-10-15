"""Controlador do Spot no Webots: só mantém o robô em pé."""

from controller import Robot

# Mesmos nomes e pose em pé do controlador de exemplo spot_moving_demo.c
MOTOR_NAMES = [
    f"{leg} {joint} motor"
    for leg in ("front left", "front right", "rear left", "rear right")
    for joint in ("shoulder abduction", "shoulder rotation", "elbow")
]
STAND_POSE = [-0.1, 0.0, 0.0, 0.1, 0.0, 0.0, -0.1, 0.0, 0.0, 0.1, 0.0, 0.0]

robot = Robot()
time_step = int(robot.getBasicTimeStep())

for name, position in zip(MOTOR_NAMES, STAND_POSE):
    robot.getDevice(name).setPosition(position)

while robot.step(time_step) != -1:
    pass
