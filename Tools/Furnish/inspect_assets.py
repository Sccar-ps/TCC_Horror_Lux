# Somente leitura: pivots/bounds de meshes candidatas e parametros de materiais.
# Rodar: py ".../Tools/Furnish/inspect_assets.py"   Saida: Saved/Furnish/inspect.txt
import os, unreal

saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(saved, "Furnish", "inspect.txt")
L = []
MS = "/Game/Scene_Saloon/Assets/MS/3D/"
OW = "/Game/OldWest/VOL6/Meshes/"
SK = "/Game/SICKA_MouldingSet/Meshes/"
MESHES = [
    MS + "His_Sal_Furniture_Lamp_Wood_Old_02/SM_His_Sal_Furniture_Lamp_Wood_Old_02_A",
    MS + "His_Sal_Furniture_Lamp_Wood_Old_02/SM_His_Sal_Furniture_Lamp_Wood_Old_02_B",
    MS + "His_Wil_Furniture_Table_Wood_Worn_01/SM_His_Wil_Furniture_Table_Wood_Worn_01",
    MS + "Res_Fur_Chair_Wood_Old_03/SM_Res_Fur_Chair_Wood_Old_03",
    MS + "Res_Fur_Chair_Wood_Worn_02/SM_Res_Fur_Chair_Wood_Worn_02",
    MS + "Res_Fur_Stool_Wood_Armless_01/SM_Res_Fur_Stool_Wood_Armless_01",
    MS + "Res_Fur_Stool_Metal_Worn_01/SM_Res_Fur_Stool_Metal_Worn_01",
    MS + "Ind_Old_Furniture_Shelf_Wood_Worn_01/SM_Ind_Old_Furniture_Shelf_Wood_Worn_01",
    MS + "Res_Rur_Furniture_Shelf_Wood_Old_01/SM_Res_Rur_Furniture_Shelf_Wood_Old_01",
    MS + "Res_Sto_Chest_Wood_Worn_08/SM_Res_Sto_Chest_Wood_Worn_08",
    MS + "Urb_Dec_PictureFrame_Wood_Worn_01/SM_Urb_Dec_PictureFrame_Wood_Worn_01",
    MS + "Res_Book_Hardback_Paper_Brown_01/SM_Res_Book_Hardback_Paper_Brown_01",
    MS + "Res_Sto_Flask_Ceramic_Worn_01/SM_Res_Sto_Flask_Ceramic_Worn_01",
    MS + "His_Sal_Bar_Wood_Pack_01/SM_His_Sal_Bar_Wood_Pack_01_A",
    MS + "His_Sal_Bar_Wood_Pack_01/SM_His_Sal_Bar_Wood_Pack_01_B",
    MS + "Res_Rur_Storage_Bucket_Metal_Worn_03/SM_Res_Rur_Storage_Bucket_Metal_Worn_03",
    MS + "Mis_Ant_Bone_Ornate_01/SM_Mis_Ant_Bone_Ornate_01",
    MS + "His_Med_Tableware_Plate_Metal_Old_01/SM_His_Med_Tableware_Plate_Metal_Old_01",
    "/Game/Scene_Saloon/Assets/Custom/His_Sal_Cloth_01/SM_His_Sal_Cloth_Various_DetailLevels_Cloth_Medium",
    "/Game/Scene_Saloon/Assets/Custom/His_Sal_Bottle_Glass_01/SM_His_Sal_Bottle_Glass_01",
    "/Game/Scene_Saloon/Assets/Custom/His_Sal_Glass_01/SM_His_Sal_Glass_01",
    "/Game/Scene_Saloon/Assets/Custom/His_Sal_Curtain_01/SM_His_Sal_Curtain_01",
    OW + "SM_Piano_NN_01a", OW + "SM_Piano_NN_01b", OW + "SM_Shelf_NN_12a", OW + "SM_Job_Board_NN_01b",
    OW + "SM_Wall_Deer_Mount_NN_01a", OW + "SM_Wall_Deer_Mount_NN_01b",
    OW + "SM_Candles_NN_01a", OW + "SM_Candles_NN_01b", OW + "SM_Candles_NN_01c",
    OW + "SM_Toolbox_NN_01a", OW + "SM_Toolbox_NN_01b", OW + "SM_Lighting_Outdoor_NN_05a",
    SK + "SM_FramePattern_UV_1", SK + "SM_FramePattern_UV_2", SK + "SM_FramePattern_UV_3", SK + "SM_FramePattern_UV_4",
    SK + "SM_FullColumn_UV_5", SK + "SM_LowWall_Module_Straight_UV", SK + "SM_BoxDecor_UV_1",
    "/Game/FPMovement/Assets/Meshes/Note/SM_Paper",
    "/Game/Fab/Double_Bed_-__Modern_contemporary/Bed/StaticMeshes/Bed",
    "/Game/Fab/Vintage_Sofa__23MB_/vintage_sofa_23mb/StaticMeshes/vintage_sofa_23mb",
    "/Game/Fab/TV_Table/meubletv1/StaticMeshes/meubletv1",
]
MATS = [
    "/Game/Scene_Saloon/Assets/MS/Surfaces/Wall_Fabric_Panel_Old_01/T_Wall_Fabric_Panel_Old_01_Mat",
    "/Game/Scene_Saloon/Assets/MS/Surfaces/Fabric_Antique_Plain_01/T_Fabric_Antique_Plain_01_Mat",
    "/Game/Scene_Saloon/Materials/MaterialInstances/MI_MS_LayerSurface_Wall_01",
    "/Game/Scene_Saloon/Materials/MaterialInstances/MI_MS_LayerSurface_Wall_02",
    "/Game/Scene_Saloon/Materials/MaterialInstances/MI_MS_LayerSurface_Floors_01",
    "/Game/SICKA_MouldingSet/Materials/MI_PlasterBasic",
    "/Game/SICKA_MouldingSet/Materials/MI_PlasterCream",
    "/Game/Scene_Saloon/Materials/MasterMaterials/M_Emissive",
    "/Game/Scene_Saloon/Materials/MaterialInstances/MI_His_Sal_Painting_Canon_01",
    "/Game/Scene_Saloon/Materials/MaterialInstances/MI_His_Sal_Painting_Saloon_01",
    "/Game/Scene_Saloon/Assets/MS/Decals/Decal_Debris_Dirt_02/MI_Decal_Debris_Dirt_02_A",
    "/Game/Scene_Saloon/Assets/MS/Decals/Decal_Leak_Dirt_02/MI_Decal_Leak_Dirt_02",
    "/Game/Fab/TV_Table/meubletv1/Materials/Tv_Screen",
    "/Game/Fab/TV_Table/meubletv1/Materials/Wood_Dark",
]


def v(x):
    return "(%.1f,%.1f,%.1f)" % (x.x, x.y, x.z)


for p in MESHES:
    sm = unreal.load_asset(p)
    if not sm:
        L.append("MISSING " + p)
        continue
    bb = sm.get_bounding_box()
    mats = []
    try:
        for i, m in enumerate(sm.static_materials):
            mi = m.material_interface
            mats.append("%s=%s" % (m.material_slot_name, mi.get_path_name().split(".")[-1] if mi else None))
    except Exception as e:
        mats.append("err %s" % e)
    socks = []
    try:
        socks = [s.socket_name for s in sm.get_editor_property("sockets")]
    except Exception:
        pass
    L.append("%s min%s max%s mats[%s] socks%s" % (p.split("/")[-1], v(bb.min), v(bb.max), ", ".join(mats), socks))

mel = unreal.MaterialEditingLibrary
for p in MATS:
    m = unreal.load_asset(p)
    if not m:
        L.append("MISSING " + p)
        continue
    base = m
    try:
        base = m.get_base_material()
    except Exception:
        pass
    L.append("MAT %s (%s) base=%s domain=%s" % (p.split("/")[-1], m.get_class().get_name(), base.get_name(),
                                                 base.get_editor_property("material_domain")))
    for kind, fn, gv in (("S", mel.get_scalar_parameter_names, "get_material_default_scalar_parameter_value"),
                         ("V", mel.get_vector_parameter_names, "get_material_default_vector_parameter_value"),
                         ("T", mel.get_texture_parameter_names, "get_material_default_texture_parameter_value")):
        try:
            names = fn(base)
            vals = []
            for n in names:
                try:
                    if isinstance(m, unreal.MaterialInstance):
                        val = getattr(mel, gv.replace("material_default", "material_instance"))(m, n)
                    else:
                        val = getattr(mel, gv)(m, n)
                    if isinstance(val, unreal.Object):
                        val = val.get_name()
                    elif isinstance(val, float):
                        val = round(val, 3)
                except Exception:
                    val = "?"
                vals.append("%s=%s" % (n, val))
            L.append("   %s: %s" % (kind, "; ".join(vals)))
        except Exception as e:
            L.append("   %s err %s" % (kind, e))

for p in ["/Game/Scene_Saloon/Assets/Blueprints/BP_His_Sal_Configuration_Table_01",
          "/Game/Scene_Saloon/Assets/Blueprints/BP_His_Sal_Configuration_Table_02",
          "/Game/Scene_Saloon/Assets/Blueprints/BP_His_Sal_Bar_01"]:
    bp = unreal.load_asset(p)
    L.append("BP %s -> %s" % (p, bp))

for p in ["/Game/Backrooms_Ambience/Cues/5_LOOP_Backrooms_Memories__by_juanjo_sound__Cue",
          "/Game/Backrooms_Ambience/Cues/4_LOOP_Backrooms_Stalker__by_juanjo_sound__Cue",
          "/Game/Backrooms_Ambience/Cues/1_LOOP_Backrooms_Tea_Party__by_juanjo_sound__Cue",
          "/Game/FPMovement/Assets/Audio/Environment/SW_Wind_calm"]:
    s = unreal.load_asset(p)
    if s:
        L.append("SND %s dur=%s looping=%s" % (p.split("/")[-1], s.get_editor_property("duration"),
                                                 getattr(s, "looping", s.get_editor_property("looping") if isinstance(s, unreal.SoundWave) else "?")))
open(OUT, "w", encoding="utf-8").write("\n".join(L))
unreal.log("inspect OK")
