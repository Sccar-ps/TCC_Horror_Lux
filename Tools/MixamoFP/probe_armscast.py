# Somente leitura: o BP_Player conversa com o ABP dos bracos (cast para ABP_Player_C / variaveis dele)?
# Se sim, trocar o ABP dos bracos por uma copia quebraria lanterna/interacao; se nao, a copia e segura.
import os, unreal
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_probe_armscast.txt")
out = []
unreal.load_asset("/Game/FPMovement/Player/Blueprints/BP_Player")
unreal.load_asset("/Game/FPMovement/Demo/Character/ABP_Player")
prefix = "/Game/FPMovement/Player/Blueprints/BP_Player.BP_Player:"
for o in unreal.ObjectIterator(unreal.K2Node):
    p = o.get_path_name()
    if not p.startswith(prefix):
        continue
    txt = ""
    try:
        txt = str(o.get_node_title()).replace("\n", " ")
    except Exception:
        pass
    hit = "ABP_Player" in txt or "Anim Instance" in txt or "AnimInstance" in txt
    try:
        for pin in o.list_all_pins():
            t = str(pin.get_pin_type_display_string()) if hasattr(pin, "get_pin_type_display_string") else ""
            if "ABP_Player" in t:
                hit = True
    except Exception:
        pass
    if hit:
        out.append("%s | %s" % (p[len(prefix):], txt[:120]))
# classes de BP que referenciam o ABP_Player
reg = unreal.AssetRegistryHelpers.get_asset_registry()
refs = reg.get_referencers("/Game/FPMovement/Demo/Character/ABP_Player", unreal.AssetRegistryDependencyOptions())
out.append("referenciadores do ABP_Player: %s" % [str(r) for r in refs])
open(LOG, "w", encoding="utf-8").write("\n".join(out) or "nenhum uso encontrado")
