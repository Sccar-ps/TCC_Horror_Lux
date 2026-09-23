# Somente leitura: amostras dos BlendSpaces 1D dos bracos 1P do FPMovement (dependem da velocidade).
import os, unreal
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_inspect_arms_bs.txt")
out = []
for p in ("/Game/FPMovement/Demo/Character/Animations/Unarmed/Blendspaces/BS_UnarmedMovement_V2",
          "/Game/FPMovement/Demo/Character/Animations/Flashlight/Blendspaces/BS_FlashlightMovement"):
    try:
        bs = unreal.load_asset(p)
        prm = bs.get_editor_property("blend_parameters")[0]
        out.append("%s  eixo=%s %s..%s grid=%s" % (p.rsplit("/", 1)[-1], prm.get_editor_property("display_name"),
                                                  prm.get_editor_property("min"), prm.get_editor_property("max"), prm.get_editor_property("grid_num")))
        for s in bs.get_editor_property("sample_data"):
            a = s.get_editor_property("animation")
            out.append("   x=%.1f  %s  rate=%.2f  len=%.3f" % (s.get_editor_property("sample_value").x, a and a.get_name(),
                                                               s.get_editor_property("rate_scale"), a.get_play_length() if a else 0))
    except Exception as e:
        out.append("%s: %s" % (p, e))
open(LOG, "w", encoding="utf-8").write("\n".join(out))
