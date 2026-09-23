# Somente leitura: encerra o PIE e resume o estado final (malha, texturas, componentes, defaults dos ABPs).
import os, unreal
EAL = unreal.EditorAssetLibrary
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_final.txt")
out = []


def w(m):
    out.append(str(m))


def safe(f, d="?"):
    try:
        return f()
    except Exception as e:
        return "%s(%s)" % (d, str(e)[:80])


les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if les.is_in_play_in_editor():
    les.editor_request_end_play()
    w("PIE encerrado")
skm = EAL.load_asset("/Game/Cowboy_character/Mesh/SM_SkeletalMesh_cowboy_character")
sms = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
nlod = safe(lambda: sms.get_lod_count(skm))
w("Cowboy LODs=%s verts LOD0=%s" % (nlod, safe(lambda: sms.get_num_verts(skm, 0))))
seen = set()
for m in skm.get_editor_property("materials"):
    mi = m.get_editor_property("material_interface")
    if not mi:
        continue
    texs = safe(lambda: unreal.MaterialEditingLibrary.get_used_textures(mi), [])
    for t in texs if isinstance(texs, list) else []:
        if t.get_path_name() in seen:
            continue
        seen.add(t.get_path_name())
        w("  tex %-40s %sx%s grupo=%s neverstream=%s maxsize=%s vt=%s" % (
            t.get_name(), safe(lambda: t.blueprint_get_size_x()), safe(lambda: t.blueprint_get_size_y()),
            safe(lambda: t.get_editor_property("lod_group")), safe(lambda: t.get_editor_property("never_stream")),
            safe(lambda: t.get_editor_property("max_texture_size")), safe(lambda: t.get_editor_property("virtual_texture_streaming"))))
w("texturas unicas: %d" % len(seen))
bp = EAL.load_asset("/Game/Characters/MixamoFP/Blueprints/BP_Player_Cowboy")
cdo = unreal.get_default_object(bp.generated_class())
mesh = cdo.get_editor_property("mesh")
w("Mesh(sombra): anim=%s mainpass=%s depth=%s shadow=%s tick=%s forcedLOD=%s" % (
    safe(lambda: mesh.get_editor_property("anim_class").get_name()), mesh.get_editor_property("render_in_main_pass"),
    mesh.get_editor_property("render_in_depth_pass"), mesh.get_editor_property("cast_shadow"),
    mesh.get_editor_property("visibility_based_anim_tick_option"), safe(lambda: mesh.get_editor_property("forced_lod_model"))))
for k in ("StandingHalfHeight", "CrouchedHalfHeight", "BackOffsetStand", "BackOffsetCrouch"):
    w("  ABP_CowboyFP.%s=%s" % (k, unreal.get_default_object(EAL.load_asset("/Game/Characters/MixamoFP/Blueprints/ABP_CowboyFP").generated_class()).get_editor_property(k)))
vcdo = unreal.get_default_object(EAL.load_asset("/Game/Characters/MixamoFP/Blueprints/ABP_CowboyFP_Visible").generated_class())
for k in ("NeckMinBehind", "MaxBodyShift", "LookDownShift", "LeanStartPitch", "LeanFullPitch", "LeanMax"):
    w("  ABP_CowboyFP_Visible.%s=%s" % (k, vcdo.get_editor_property(k)))
gm = EAL.load_asset("/Game/FPMovement/Player/Blueprints/BP_PlayerMode")
w("GameMode default pawn=%s" % safe(lambda: unreal.get_default_object(gm.generated_class()).get_editor_property("default_pawn_class").get_name()))
open(LOG, "w", encoding="utf-8").write("\n".join(out))
