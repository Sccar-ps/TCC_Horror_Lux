# Captura 4 vistas fixas na altura do olho (viewport do editor, game view) para comparar antes/depois.
# Uso: py ".../Tools/Lighting/shots.py" <rotulo>      -> Saved/Atmos/<rotulo>_<comodo>.png
# Espera a exposicao automatica assentar (WAIT s) antes de cada HighResShot. Nao altera o mapa.
import os, sys, glob, unreal

WAIT = 5.0  # s por vista (a adaptacao do olho precisa assentar)
SHOTS = [  # nome, (x, y, z), pitch, yaw   -- z 165 = olho sobre o piso (z 0)
    ("corredor", (-3275, -650, 165), -3.0, 90.0),
    ("sala", (-2150, -420, 165), -8.0, -119.0),
    ("escritorio", (-3160, -780, 165), -5.0, -134.0),
    ("quarto", (-2560, 950, 165), -5.0, 141.0),
]
label = sys.argv[1] if len(sys.argv) > 1 else "shot"
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
SRC = os.path.join(saved, "Screenshots", "WindowsEditor")
DST = os.path.join(saved, "Atmos")
os.makedirs(DST, exist_ok=True)

ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
world = ues.get_editor_world()
cam0 = ues.get_level_viewport_camera_info()[-2:]  # (loc, rot), com ou sem o bool de retorno
les.editor_set_game_view(True)
st = {"i": 0, "t": 0.0, "step": "move", "before": set()}


def pngs():
    return set(glob.glob(os.path.join(SRC, "*.png")))


def tick(dt):
    st["t"] += dt
    if st["i"] >= len(SHOTS):
        unreal.unregister_slate_post_tick_callback(handle)
        ues.set_level_viewport_camera_info(cam0[0], cam0[1])
        les.editor_set_game_view(False)
        unreal.log("LUX shots prontos em " + DST)
        return
    name, (x, y, z), pitch, yaw = SHOTS[st["i"]]
    if st["step"] == "move":
        ues.set_level_viewport_camera_info(unreal.Vector(x, y, z), unreal.Rotator(roll=0.0, pitch=pitch, yaw=yaw))
        st.update(step="wait", t=0.0)
    elif st["step"] == "wait" and st["t"] >= WAIT:
        st["before"] = pngs()
        unreal.SystemLibrary.execute_console_command(world, "HighResShot 1")
        st.update(step="save", t=0.0)
    elif st["step"] == "save" and st["t"] >= 1.5:
        new = sorted(pngs() - st["before"], key=os.path.getmtime)
        if new:
            out = os.path.join(DST, "%s_%s.png" % (label, name))
            if os.path.exists(out):
                os.remove(out)
            os.replace(new[-1], out)
        st.update(step="move", t=0.0, i=st["i"] + 1)


handle = unreal.register_slate_post_tick_callback(tick)
