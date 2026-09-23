# Somente leitura: lista pacotes com alteracoes nao salvas (para nao salvar nada do usuario por engano).
import os, unreal
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
out = []
try:
    out.append("content: %s" % [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()])
    out.append("maps: %s" % [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()])
except Exception as e:
    out.append("erro %s" % e)
open(os.path.join(saved, "MixamoFP_dirty.txt"), "w", encoding="utf-8").write("\n".join(out))
