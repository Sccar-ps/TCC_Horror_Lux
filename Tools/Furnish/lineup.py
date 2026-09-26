# Temporario: enfileira as malhas candidatas (yaw 0) no sul da sala para calibrar a frente de cada uma.
# py ".../Tools/Furnish/lineup.py"          -> cria (tag LUX_TEMP)
# py ".../Tools/Furnish/lineup.py" clear    -> remove
import sys, unreal

TAG = "LUX_TEMP"
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
w = ues.get_editor_world()

for a in unreal.GameplayStatics.get_all_actors_with_tag(w, TAG):
    eas.destroy_actor(a)
if len(sys.argv) > 1 and sys.argv[1] == "clear":
    raise SystemExit

MS = "/Game/Scene_Saloon/Assets/MS/3D/"
OW = "/Game/OldWest/VOL6/Meshes/"
ITEMS = [
    MS + "Res_Fur_Chair_Wood_Old_03/SM_Res_Fur_Chair_Wood_Old_03",
    MS + "Res_Fur_Chair_Wood_Worn_02/SM_Res_Fur_Chair_Wood_Worn_02",
    MS + "Res_Fur_Stool_Wood_Armless_01/SM_Res_Fur_Stool_Wood_Armless_01",
    MS + "Ind_Old_Furniture_Shelf_Wood_Worn_01/SM_Ind_Old_Furniture_Shelf_Wood_Worn_01",
    MS + "Res_Sto_Chest_Wood_Worn_08/SM_Res_Sto_Chest_Wood_Worn_08",
    OW + "SM_Piano_NN_01a",
    OW + "SM_Shelf_NN_12a",
    OW + "SM_Job_Board_NN_01b",
    MS + "Urb_Dec_PictureFrame_Wood_Worn_01/SM_Urb_Dec_PictureFrame_Wood_Worn_01",
    OW + "SM_Wall_Deer_Mount_NN_01a",
    OW + "SM_Candles_NN_01a",
    MS + "His_Sal_Bar_Wood_Pack_01/SM_His_Sal_Bar_Wood_Pack_01_B",
]
x = -2960.0
row_y = -1650.0
with unreal.ScopedEditorTransaction("LUX: lineup temporario"):
    for p in ITEMS:
        sm = unreal.load_asset(p)
        bb = sm.get_bounding_box()
        wx = bb.max.x - bb.min.x
        if x + wx > -2080.0:
            x = -2960.0
            row_y += 400.0
        cx = x + wx / 2 - (bb.max.x + bb.min.x) / 2
        z = -bb.min.z + (120.0 if "PictureFrame" in p or "Deer" in p else 0.0)
        a = eas.spawn_actor_from_object(sm, unreal.Vector(cx, row_y, z), unreal.Rotator(0, 0, 0))
        a.tags = [unreal.Name(TAG)]
        a.set_actor_label("TEMP_" + p.split("/")[-1])
        x += wx + 25.0
unreal.log("lineup ok, x final %.0f" % x)
