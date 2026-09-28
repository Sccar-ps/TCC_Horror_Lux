# LUX: exporta os dados da mao para conferir a pega FORA da Unreal (malha real da pele + ossos). Rodar SEM PIE.
#   py "<projeto>/Tools/Player/vela_mao_dump.py"
# Saida: Saved/LuxSnapshots/mao_dump/ (pose.json + malha do braco em glTF). So le assets; nada e salvo no projeto.
import json, os, traceback
import unreal

EAL, APE, AL = unreal.EditorAssetLibrary, unreal.AnimPoseExtensions, unreal.AnimationLibrary
SKM = "/Game/FPMovement/Demo/Character/Arms/MetaHuman/SKM_Metahuman_Arms"
ANIMS = "/Game/FPMovement/Demo/Character/Animations/Flashlight/"
LISTA = ("AS_Flashlight_Idle", "AS_Flashlight_Walk", "AS_Flashlight_Eqiup", "AS_Flashlight_Unequip", "AS_Flashlight_Jump",
         "AS_Flashlight_InAir", "AS_Flashlight_Land", "AS_Flashlight_Inspection", "AS_Flashlight_FlickerReaction")
PEGA = "/Game/Masion/LUX/Player/Anim/AS_LuxVela_Pega"
OUT = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "LuxSnapshots", "mao_dump")


def tr(t):
    q = t.rotation
    return [[t.translation.x, t.translation.y, t.translation.z], [q.x, q.y, q.z, q.w]]


def pose_de(seq, f, espacos=("LOCAL", "WORLD")):
    p = APE.get_anim_pose_at_frame(seq, f, unreal.AnimPoseEvaluationOptions())
    nomes = [str(b) for b in APE.get_bone_names(p)]
    out = {}
    for esp in espacos:
        e = getattr(unreal.AnimPoseSpaces, esp)
        out[esp] = {b: tr(APE.get_bone_pose(p, b, e)) for b in nomes}
    return p, nomes, out


def main():
    os.makedirs(OUT, exist_ok=True)
    log = []
    idle = EAL.load_asset(ANIMS + "AS_Flashlight_Idle")
    p, nomes, idle0 = pose_de(idle, 0)
    ref = {}
    for esp in ("LOCAL", "WORLD"):
        e = getattr(unreal.AnimPoseSpaces, esp)
        ref[esp] = {b: tr(APE.get_ref_bone_pose(p, b, e)) for b in nomes}
    dados = {"nomes": nomes, "ref": ref, "idle0": idle0, "anims": {}}
    for an in LISTA:
        seq = EAL.load_asset(ANIMS + an)
        n = AL.get_num_frames(seq)
        quadros = sorted(set(list(range(0, n + 1, max(1, n // 16))) + [n]))
        dados["anims"][an] = {"n": n, "len": AL.get_sequence_length(seq),
                              "quadros": {str(f): pose_de(seq, f, ("LOCAL",))[2]["LOCAL"] for f in quadros}}
        log.append("%s: %d quadros" % (an, n))
    if EAL.does_asset_exist(PEGA):
        dados["pega"] = pose_de(EAL.load_asset(PEGA), 0, ("LOCAL",))[2]["LOCAL"]
    sk = EAL.load_asset(SKM)
    s = sk.find_socket("hand_r_Vela")
    if s:
        dados["socket"] = {"osso": str(s.get_editor_property("bone_name")), "loc": [s.relative_location.x, s.relative_location.y, s.relative_location.z],
                           "rot": [s.relative_rotation.roll, s.relative_rotation.pitch, s.relative_rotation.yaw]}
    with open(os.path.join(OUT, "pose.json"), "w", encoding="utf-8") as fh:
        json.dump(dados, fh)
    log.append("pose.json: %d ossos" % len(nomes))
    # malha: glTF (vertices + pesos + hierarquia)
    arq = os.path.join(OUT, "arms.gltf")
    ok = None
    try:
        op = unreal.GLTFExportOptions()
        for k, v in (("bake_material_inputs", "DISABLED"), ("texture_image_format", "NONE")):
            try:
                enum = type(op.get_editor_property(k))
                op.set_editor_property(k, getattr(enum, v))
            except Exception as ex:
                log.append("  opcao %s: %s" % (k, ex))
        r = unreal.GLTFExporter.export_to_gltf(sk, arq, op, set())
        ok = r
        log.append("glTF: %s" % (r,))
    except Exception:
        log.append("glTF falhou: " + traceback.format_exc())
    if not os.path.exists(arq):
        # plano B: FBX em ASCII
        t = unreal.AssetExportTask()
        t.object, t.filename, t.automated, t.prompt, t.replace_identical = sk, os.path.join(OUT, "arms.fbx"), True, False, True
        o = unreal.FbxExportOption()
        o.set_editor_property("ascii", True)
        t.options = o
        log.append("FBX ascii: %s" % unreal.Exporter.run_asset_export_task(t))
    log.append("arquivos: %s" % os.listdir(OUT))
    with open(os.path.join(OUT, "log.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(log))
    unreal.log("[LUX dump] " + " | ".join(log))


try:
    main()
except Exception:
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "log.txt"), "w", encoding="utf-8") as fh:
        fh.write("ERRO " + traceback.format_exc())
