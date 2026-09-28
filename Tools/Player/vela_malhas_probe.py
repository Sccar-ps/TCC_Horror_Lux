# LUX: formato das malhas de vela do OldWest (so leitura): bounds e perfil por fatia (procura castical com cabo).
#   py "<projeto>/Tools/Player/vela_malhas_probe.py"  -> Saved/LuxSnapshots/vela_malhas_probe.txt
import os, traceback, unreal

EAL = unreal.EditorAssetLibrary
OUT = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "LuxSnapshots", "vela_malhas_probe.txt")
L = []
try:
    for n in ("SM_Candles_01a", "SM_Candles_01b", "SM_Candles_01c", "SM_Candles_NN_01a", "SM_Candles_NN_01b", "SM_Candles_NN_01c"):
        sm = EAL.load_asset("/Game/OldWest/VOL6/Meshes/" + n)
        if not sm:
            L.append("%s: nao carregou" % n)
            continue
        b = sm.get_bounding_box()
        L.append("%s bounds (%.1f %.1f %.1f)-(%.1f %.1f %.1f) secoes %d mats %s" % (
            n, b.min.x, b.min.y, b.min.z, b.max.x, b.max.y, b.max.z, sm.get_num_sections(0),
            [(str(s.material_slot_name), s.material_interface.get_path_name() if s.material_interface else None) for s in sm.static_materials]))
        vs = []
        for s in range(sm.get_num_sections(0)):
            vs += list(unreal.ProceduralMeshLibrary.get_section_from_static_mesh(sm, 0, s)[0])
        h = b.max.z - b.min.z
        for i in range(10):
            z0, z1 = b.min.z + h * i / 10, b.min.z + h * (i + 1) / 10
            fatia = [v for v in vs if z0 <= v.z <= z1]
            if fatia:
                L.append("   z %.1f-%.1f: x %.1f..%.1f  y %.1f..%.1f  (%d vert)" % (z0, z1, min(v.x for v in fatia), max(v.x for v in fatia),
                                                                               min(v.y for v in fatia), max(v.y for v in fatia), len(fatia)))
except Exception:
    L.append(traceback.format_exc())
open(OUT, "w", encoding="utf-8").write("\n".join(L))
unreal.log("[LUX vela] malhas probe ok")
