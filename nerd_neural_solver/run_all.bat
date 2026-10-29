@echo off
REM Refaz toda a comparacao solver analitico x solver neural (NeRD): metricas, gravacoes e videos.
REM Requer o repositorio em C:\nerd e o ambiente conda C:\nerd-env (ver README.md). Leva cerca de 15 min.
setlocal
set PY=C:\nerd-env\python.exe
set RUN=%PY% "%~dp0nerd_run.py"
set MODELS=../../pretrained_models
set RESULTS=%~dp0results
if not exist "%RESULTS%" mkdir "%RESULTS%"

echo === 1/4 Metricas de movimento passivo (2048 trajetorias de 100 passos)
for %%P in (Cartpole:Cartpole PendulumWithContact:Pendulum Ant:Ant Anymal:Anymal) do (
  for /f "tokens=1,2 delims=:" %%A in ("%%P") do (
    echo --- %%A
    %RUN% eval/eval_passive/eval_passive_motion.py --env-name %%A --model-path %MODELS%/NeRD_models/%%B/model/nn/model.pt --env-mode neural --num-envs 2048 --num-rollouts 2048 --rollout-horizon 100 --seed 500 > "%RESULTS%\passive_%%A.log" 2>&1
    findstr /c:"error mean" "%RESULTS%\passive_%%A.log"
  )
)

echo === 2/4 Politica de caminhada do ANYmal nos dois solvers (512 episodios)
for %%M in (ground-truth neural) do (
  echo --- %%M
  %RUN% eval/eval_rl/run_rl.py --rl-cfg ./cfg/Anymal/anymal_forward.yaml --playback %MODELS%/RL_policies/Anymal/forward_walk/0/nn/AnymalPPO.pth --num-envs 512 --num-games 512 --env-mode %%M > "%RESULTS%\rl_anymal_forward_%%M.log" 2>&1
  findstr /c:"av reward" "%RESULTS%\rl_anymal_forward_%%M.log"
)

echo === 3/4 Gravacoes (abre uma janela OpenGL para cada uma)
REM O NeRD chama o ffmpeg, que perguntaria antes de sobrescrever: apaga os GIFs antigos
del /q C:\nerd\eval\eval_passive\gifs\*.gif C:\nerd\eval\eval_rl\gifs\*.gif 2>nul
for %%M in (ground-truth neural) do (
  %RUN% eval/eval_passive/eval_passive_motion.py --env-name Cartpole --model-path %MODELS%/NeRD_models/Cartpole/model/nn/model.pt --env-mode %%M --num-envs 1 --num-rollouts 3 --rollout-horizon 200 --seed 500 --render --export-video --export-video-path cartpole_%%M.gif > nul 2>&1
  %RUN% eval/eval_passive/eval_passive_motion.py --env-name PendulumWithContact --model-path %MODELS%/NeRD_models/Pendulum/model/nn/model.pt --env-mode %%M --num-envs 1 --num-rollouts 3 --rollout-horizon 200 --seed 500 --render --export-video --export-video-path pendulum_%%M.gif > nul 2>&1
  %RUN% eval/eval_rl/run_rl.py --rl-cfg ./cfg/Anymal/anymal_forward.yaml --playback %MODELS%/RL_policies/Anymal/forward_walk/0/nn/AnymalPPO.pth --num-envs 1 --num-games 1 --max-episode-length 400 --env-mode %%M --render --export-video --export-video-path anymal_walk_%%M.gif > nul 2>&1
)

echo === 4/4 Videos lado a lado
%PY% "%~dp0make_videos.py"
endlocal
