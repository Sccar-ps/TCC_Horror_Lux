# Somente leitura: acha o buraco da fechadura das portas do loop.
# 1) grade de line traces (colisao complexa) perpendicular a folha, em volta da macaneta -> mapa de profundidade
# 2) foto de uma camera temporaria (FOV 40, reta para a porta) com uma luz temporaria -> Saved/Loop/fechadura_<porta>.png
# Tudo que e criado e apagado no fim. Saida: Saved/Loop/fechadura.txt
import glob, os, traceback, unreal

saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(saved, "Loop")
LOG = os.path.join(OUT, "fechadura.txt")
SHOTS = os.path.join(saved, "Screenshots")
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
out = []
CAM_BACK, CAM_DZ, FOV, RES = 40.0, -8.0, 40.0, (1280, 720)


def w(m):
    out.append(str(m))
    open(LOG, "w", encoding="utf-8").write("\n".join(out))


def handle(door):
    h = [c for c in door.get_components_by_class(unreal.StaticMeshComponent) if c.get_name() == "DoorHandle"][0]
    return unreal.SystemLibrary.get_component_bounds(h)[0]


def grid(world, door, H):
    leaf = [c for c in door.get_components_by_class(unreal.StaticMeshComponent) if c.get_name() == "Door"][0]
    face = unreal.SystemLibrary.get_component_bounds(leaf)[0].y + unreal.SystemLibrary.get_component_bounds(leaf)[1].y
    w("%s: macaneta (centro bounds) %s | face da folha (lado +Y) y=%.2f" % (door.get_actor_label(), H, face))
    w("grade: colunas dx=-12..+12 (x do mundo), linhas dz=+6..-26; '.'=face, 'H'=macaneta, 'o'=mais fundo que a face, "
      "'+'=mais alto que a face (espelho da fechadura?), ' '=sem hit")
    for dz in range(6, -27, -1):
        row = ""
        for dx in range(-12, 13):
            s = unreal.Vector(H.x + dx, H.y + 40, H.z + dz)
            e = unreal.Vector(H.x + dx, H.y - 3, H.z + dz)
            hit = unreal.SystemLibrary.line_trace_single(world, s, e, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [],
                                                         unreal.DrawDebugTrace.NONE, True)
            t = hit.to_tuple() if hit is not None else (False,)
            if not t[0]:
                row += " "
                continue
            comp = next((x for x in t if isinstance(x, unreal.PrimitiveComponent)), None)
            y = t[5].y                           # ImpactPoint (mesmo indice usado no furnish.py)
            name = comp.get_name() if comp else ""
            if name.startswith("DoorHandle"):
                row += "H"
            elif y < face - 0.4:
                row += "o"
            elif y > face + 0.4:
                row += "+"
            else:
                row += "."
        w("%+4d |%s|" % (dz, row))


def main():
    world = ues.get_editor_world()
    by = {a.get_actor_label(): a for a in eas.get_all_level_actors()}
    temps = []
    try:
        for label in ("BP_BaseDoor7", "LOOP_PortaSala"):
            door = by[label]
            H = handle(door)
            grid(world, door, H)
        # foto: so da porta do quarto (mesma malha nas duas)
        H = handle(by["BP_BaseDoor7"])
        loc = unreal.Vector(H.x, H.y + CAM_BACK, H.z + CAM_DZ)
        cam = eas.spawn_actor_from_class(unreal.CameraActor, loc, unreal.Rotator(roll=0.0, pitch=0.0, yaw=-90.0))
        cc = cam.get_editor_property("camera_component")
        cc.set_editor_property("field_of_view", FOV)
        cc.set_editor_property("constrain_aspect_ratio", False)
        light = eas.spawn_actor_from_class(unreal.PointLight, unreal.Vector(H.x + 10, H.y + 25, H.z + 10), unreal.Rotator())
        lc = light.get_component_by_class(unreal.PointLightComponent)
        lc.set_editor_property("intensity", 2.0)
        lc.set_editor_property("attenuation_radius", 80.0)
        lc.set_editor_property("cast_shadows", False)
        temps += [cam, light]
        w("foto: camera em %s, yaw -90, FOV %.0f, %dx%d; centro da imagem = macaneta + (0, 0, %.0f); face a %.1f cm" % (
            loc, FOV, RES[0], RES[1], CAM_DZ, CAM_BACK - 6.5))
        before = set(glob.glob(os.path.join(SHOTS, "**", "*.png"), recursive=True))
        unreal.AutomationLibrary.take_high_res_screenshot(RES[0], RES[1], "fechadura_quarto.png", cam)
        st = {"t": 0.0}

        def tick(dt):
            st["t"] += dt
            new = set(glob.glob(os.path.join(SHOTS, "**", "*.png"), recursive=True)) - before
            if new or st["t"] > 8.0:
                unreal.unregister_slate_post_tick_callback(st["h"])
                for p in new:
                    dst = os.path.join(OUT, os.path.basename(p))
                    if os.path.exists(dst):
                        os.remove(dst)
                    os.replace(p, dst)
                    w("foto salva: " + dst)
                for a in temps:
                    eas.destroy_actor(a)
                w("temporarios apagados" + ("" if new else " (foto nao saiu em 8 s)"))

        st["h"] = unreal.register_slate_post_tick_callback(tick)
    except Exception:
        w("ERRO " + traceback.format_exc())
        for a in temps:
            eas.destroy_actor(a)


main()
