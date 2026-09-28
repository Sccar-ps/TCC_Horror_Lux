# LUX: teste (sem salvar) de criar socket no SKM_Metahuman_Arms pelo Python. Desfaz no fim.
import os, traceback, unreal

EAL = unreal.EditorAssetLibrary
OUT = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "LuxSnapshots", "vela_socket_probe.txt")
L = []
try:
    sk = EAL.load_asset("/Game/FPMovement/Demo/Character/Arms/MetaHuman/SKM_Metahuman_Arms")
    s = unreal.new_object(unreal.SkeletalMeshSocket, sk)
    L.append("api socket: %s" % [x for x in dir(s) if not x.startswith("_")])
    for k, v in (("bone_name", "hand_r"), ("relative_location", unreal.Vector(1, 2, 3)), ("relative_rotation", unreal.Rotator(0, 0, 0)),
                 ("relative_scale", unreal.Vector(1, 1, 1)), ("socket_name", "LUX_teste")):
        try:
            s.set_editor_property(k, v)
            L.append("set %s ok -> %s" % (k, s.get_editor_property(k)))
        except Exception as ex:
            L.append("set %s FALHOU: %s" % (k, ex))
    n0 = sk.num_sockets()
    sk.add_socket(s, False)
    L.append("add_socket: %d -> %d; nome=%s osso=%s" % (n0, sk.num_sockets(), s.get_editor_property("socket_name"), s.get_editor_property("bone_name")))
    try:
        sk.rename_socket(s.get_editor_property("socket_name"), "LUX_teste")
        L.append("rename ok -> %s" % s.get_editor_property("socket_name"))
    except Exception as ex:
        L.append("rename FALHOU: %s" % ex)
    L.append("find LUX_teste: %s" % bool(sk.find_socket("LUX_teste")))
    try:
        sk.remove_socket(s.get_editor_property("socket_name"))
        L.append("removido: %d" % sk.num_sockets())
    except Exception as ex:
        L.append("remove FALHOU: %s" % ex)
except Exception:
    L.append(traceback.format_exc())
open(OUT, "w", encoding="utf-8").write("\n".join(L))
unreal.log("[LUX vela] socket probe ok")
