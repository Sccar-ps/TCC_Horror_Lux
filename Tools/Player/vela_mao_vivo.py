# LUX: COM O PIE ABERTO, grava os ossos da mao (relativos ao hand_r) e a vela como estao no jogo, para comparar com o
# calculo fora da Unreal.   py "<projeto>/Tools/Player/vela_mao_vivo.py"   -> Saved/LuxSnapshots/mao_dump/vivo.json
import json, os, traceback
import unreal

OUT = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "LuxSnapshots", "mao_dump", "vivo.json")
OSSOS = ["hand_r"] + ["%s_%s_r" % (f, k) for f in ("index", "middle", "ring", "pinky") for k in ("metacarpal", "01", "02", "03")] + \
        ["thumb_01_r", "thumb_02_r", "thumb_03_r"]


def tr(t):
    q = t.rotation
    return [[t.translation.x, t.translation.y, t.translation.z], [q.x, q.y, q.z, q.w]]


def main():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
    mesh = [c for c in pawn.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == "FirstPersonMesh"][0]
    out = {"ossos": {}, "comps": {}}
    for b in OSSOS:
        out["ossos"][b] = tr(mesh.get_socket_transform(b, unreal.RelativeTransformSpace.RTS_COMPONENT))
    out["socket"] = tr(mesh.get_socket_transform("hand_r_Vela", unreal.RelativeTransformSpace.RTS_COMPONENT))
    for c in pawn.get_components_by_class(unreal.PrimitiveComponent):
        n = c.get_name()
        if n in ("FirstPersonMesh", "Vela") or "Vela" in n or "Chama" in n:
            d = {"pai": str(c.get_attach_parent().get_name()) if c.get_attach_parent() else None,
                 "socket": str(c.get_attach_socket_name()), "rel": tr(c.get_relative_transform()),
                 "escala": [c.relative_scale3d.x, c.relative_scale3d.y, c.relative_scale3d.z],
                 "mundo": tr(c.get_world_transform())}
            for k in ("first_person_primitive_type", "visible", "hidden_in_game"):
                try:
                    d[k] = str(c.get_editor_property(k))
                except Exception as ex:
                    d[k] = "? %s" % ex
            out["comps"][n] = d
    out["mesh_mundo"] = tr(mesh.get_world_transform())
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    unreal.log("[LUX vivo] gravado " + OUT)


try:
    main()
except Exception:
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"erro": traceback.format_exc()}))
