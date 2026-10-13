# LUX - A/B CONTROLADO de legibilidade (05/10/2026). `python -B ue_cli.py file pie_l1_ab.py [passos|vao]` (editor grafico aberto, fora do PIE). Resultados em Saved/LuxSnapshots/l1_fluido.
# A/B CONTROLADO de legibilidade da figura dos Passos no Loop 1 (troca real de loop; nenhum evento disparado; nada e salvo).
# Para cada variante de luz (A = LuzPassos como a equipe a deixou no mapa; B = LuzPassos na posicao do v3, SO NO PIE) e cada posicao da figura (centro das 3 janelas)
# tira 2 quadros IDENTICOS (mesma camera, mesma luz), um com a Presenca 0 e outro com 1, mirando o jogador (S1) na figura.
#   ue_cli.py file pie_estatica.py
import ctypes
import ctypes.wintypes as wt
import json
import math
import os
import sys
import time
import traceback
import unreal

SCR = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "LuxSnapshots", "l1_fluido").replace("\\", "/")
os.makedirs(SCR, exist_ok=True)
MODO = sys.argv[1] if len(sys.argv) > 1 else "passos"      # passos | vao
OUT = SCR + "/pie_l1_ab_%s.json" % MODO
SHOTDIR = SCR + "/shots"
os.makedirs(SHOTDIR, exist_ok=True)
LVL = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
U32 = ctypes.windll.user32
_HW = []
CFG = {
    "passos": dict(fig="LUX_Vulto_L1_Passos", luz="LUX_L1_LuzPassos", jogador=(-3054.0, -627.0), yaw=1.9, luz_v3=dict(pos=(-3300.0, -660.0, 230.0), raio=None),
                   pos={"j1": (-3175.0, -737.0), "j2": (-3067.0, -734.0), "j3": (-2960.0, -730.0)}),   # centro das 3 janelas acesas (t ~ 0,9 / 2,2 / 3,5 s)
    "vao": dict(fig="LUX_Vulto_L1_Porta", luz="LUX_L1_LuzFundo", jogador=(-3275.0, -100.0), yaw=90.0, luz_v3=dict(pos=(-3250.0, -1080.0, 110.0), raio=450.0),
                pos={"v0": (-3250.0, -700.0), "v1": (-3275.0, -665.0)}),                                  # as duas posicoes do vulto do vao (a 2a depois do tranco)
}[MODO]
JOGADOR, POSICOES = CFG["jogador"], CFG["pos"]
CASOS = [(var, pos, cpd) for var in ("A", "B") for pos in POSICOES for cpd in (0.0, 1.0)]

if hasattr(unreal, "_lux_pie_h") and unreal._lux_pie_h is not None:
    try:
        unreal.unregister_slate_post_tick_callback(unreal._lux_pie_h)
    except Exception:
        pass
    unreal._lux_pie_h = None
S = dict(fase="pie", t_wall0=time.time(), erros=[], fim=False, shots=[], foco=[], i=-1)
unreal._lux_pie = S


def foco():
    if not _HW:
        pid = os.getpid()

        @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
        def cb(h, _l):
            p = wt.DWORD()
            U32.GetWindowThreadProcessId(h, ctypes.byref(p))
            if p.value == pid and U32.IsWindowVisible(h) and U32.GetWindowTextLengthW(h) > 0:
                buf = ctypes.create_unicode_buffer(256)
                U32.GetWindowTextW(h, buf, 256)
                if "Unreal Editor" in buf.value:
                    _HW.append(h)
            return True
        U32.EnumWindows(cb, 0)
    if not _HW:
        return False
    h = _HW[0]
    if U32.GetForegroundWindow() != h:
        U32.keybd_event(0x12, 0, 0, 0)
        U32.keybd_event(0x12, 0, 2, 0)
        U32.ShowWindow(h, 9)
        U32.SetForegroundWindow(h)
    return U32.GetForegroundWindow() == h


def fim(motivo):
    S["fim"] = True
    S["motivo"] = motivo
    try:
        if unreal._lux_pie_h is not None:
            unreal.unregister_slate_post_tick_callback(unreal._lux_pie_h)
            unreal._lux_pie_h = None
    except Exception as ex:
        S["erros"].append("unregister: %s" % ex)
    try:
        if LVL.is_in_play_in_editor():
            LVL.editor_request_end_play()
    except Exception as ex:
        S["erros"].append("end_play: %s" % ex)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(S, fh, default=str)


def mundo():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()


def prepara(w, tg):
    var, pos, cpd = CASOS[S["i"]]
    luz = S["a"][CFG["luz"]]
    pl = luz.point_light_component
    if var == "B":      # luz na posicao do v3, SO NO PIE (descartado ao fechar)
        luz.set_actor_location(unreal.Vector(*CFG["luz_v3"]["pos"]), False, True)
        pl.set_attenuation_radius(CFG["luz_v3"]["raio"] or S["raio_equipe"])
    else:
        luz.set_actor_location(unreal.Vector(*S["luz_equipe"]), False, True)
        pl.set_attenuation_radius(S["raio_equipe"])
    fx, fy = POSICOES[pos]
    S["a"][CFG["fig"]].set_actor_location_and_rotation(unreal.Vector(fx, fy, 0.0), unreal.Rotator(0, 0, CFG["yaw"]), False, True)
    fig = S["fig"]
    fig.set_hidden_in_game(False, False)
    fig.set_custom_primitive_data_float(0, cpd)
    pw = unreal.GameplayStatics.get_player_pawn(w, 0).get_actor_location()
    dx, dy, dz = fx - pw.x, fy - pw.y, 110.0 - (pw.z + 68.0)
    unreal.GameplayStatics.get_player_controller(w, 0).set_control_rotation(unreal.Rotator(0, math.degrees(math.atan2(dz, math.hypot(dx, dy))), math.degrees(math.atan2(dy, dx))))
    S["fase"] = "casos"
    S["t_f"] = tg


def tick(dt):
    try:
        agora = time.time()
        if agora - S.get("t_foco", 0.0) > 1.0:
            S["t_foco"] = agora
            S["foco"].append(bool(foco()))
        w = mundo()
        if S["fase"] == "pie":
            if agora - S["t_wall0"] > 150:
                return fim("timeout esperando o PIE")
            if not w or not unreal.GameplayStatics.get_player_pawn(w, 0):
                return
            S["t_pie0"] = unreal.GameplayStatics.get_time_seconds(w)
            S["fase"] = "aquecer"
            return
        tg = unreal.GameplayStatics.get_time_seconds(w)
        if S["fase"] == "aquecer":
            if tg - S["t_pie0"] < 6.0:
                return
            todos = unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor)
            quer = (CFG["fig"], "LOOP_Manager", CFG["luz"])
            S["a"] = {a.get_actor_label(): a for a in todos if a.get_actor_label() in quer}
            if len(S["a"]) < 3:
                return fim("atores ausentes: %s" % sorted(S["a"]))
            lp = S["a"][CFG["luz"]].get_actor_location()
            S["luz_equipe"] = [lp.x, lp.y, lp.z]
            S["raio_equipe"] = S["a"][CFG["luz"]].point_light_component.get_editor_property("attenuation_radius")
            pawn = unreal.GameplayStatics.get_player_pawn(w, 0)
            pawn.set_actor_location(unreal.Vector(-2294.0, -1827.0, pawn.get_actor_location().z), False, True)
            unreal.GameplayStatics.get_player_controller(w, 0).set_control_rotation(unreal.Rotator(0, 0, -90))
            S["fase"] = "interagir"
            S["t_f"] = tg
            return
        if S["fase"] == "interagir":
            if tg - S["t_f"] < 1.0:
                return
            unreal.GameplayStatics.get_player_pawn(w, 0).call_method("Interact")
            S["fase"] = "esperar_troca"
            S["t_f"] = tg
            return
        if S["fase"] == "esperar_troca":
            if tg - S["t_f"] > 20.0:
                return fim("a troca de loop nao aconteceu")
            if S["a"]["LOOP_Manager"].get_editor_property("LoopAtual") >= 1:
                S["fase"] = "assentar_troca"
                S["t_f"] = tg
            return
        if S["fase"] == "assentar_troca":
            if tg - S["t_f"] < 5.0:
                return
            pawn = unreal.GameplayStatics.get_player_pawn(w, 0)
            pawn.set_actor_location(unreal.Vector(JOGADOR[0], JOGADOR[1], pawn.get_actor_location().z), False, True)
            S["fig"] = S["a"][CFG["fig"]].get_components_by_class(unreal.SkeletalMeshComponent)[0]
            S["fase"] = "casos"
            S["t_f"] = tg
            S["i"] = -1
            return
        if S["fase"] == "casos":
            if tg - S["t_f"] < 0.9:
                return
            if 0 <= S["i"] < len(CASOS):
                var, pos, cpd = CASOS[S["i"]]
                nome = "%s/est_%s_%s_%s_P%d.png" % (SHOTDIR, MODO, var, pos, int(cpd))
                unreal.SystemLibrary.execute_console_command(w, 'HighResShot 1280x720 filename="%s"' % nome)
                S["shots"].append(dict(var=var, pos=pos, cpd=cpd, arq=nome))
                S["fase"] = "esperar_shot"
                S["t_f"] = tg
                return
            S["i"] += 1
            return prepara(w, tg)
        if S["fase"] == "esperar_shot":
            if tg - S["t_f"] < 0.4:
                return
            S["i"] += 1
            if S["i"] >= len(CASOS):
                return fim("ok")
            return prepara(w, tg)
    except Exception:
        S["erros"].append(traceback.format_exc())
        fim("excecao")


unreal._lux_pie_h = unreal.register_slate_post_tick_callback(tick)
LVL.editor_request_begin_play()
print("PIE A/B pedido; resultado em", OUT)
