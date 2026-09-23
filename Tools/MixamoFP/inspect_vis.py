# Somente leitura: encerra o PIE (se ativo) e lista nos/variaveis do ABP_CowboyFP_Visible.
import os, unreal
EAL = unreal.EditorAssetLibrary
BEL = unreal.BlueprintEditorLibrary
VIS = "/Game/Characters/MixamoFP/Blueprints/ABP_CowboyFP_Visible"
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_inspect_vis.txt")
out = []
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if les.is_in_play_in_editor():
    les.editor_request_end_play()
    out.append("PIE encerrado")
vis = EAL.load_asset(VIS)
out.append("vars: %s" % [str(n) for n in BEL.list_member_variable_names(vis)])
for graph in ("EventGraph", "AnimGraph"):
    prefix = VIS + ".ABP_CowboyFP_Visible:" + graph + "."
    for obj in unreal.ObjectIterator(unreal.EdGraphNode):
        p = obj.get_path_name()
        if p.startswith(prefix) and "." not in p[len(prefix):]:
            links = []
            try:
                for pin in obj.list_all_pins():
                    c = pin.list_connected_pins()
                    if c:
                        links.append("%s->%s" % (pin.get_pin_name(), ",".join(x.get_owning_node().get_name() for x in c)))
            except Exception as e:
                links.append("?%s" % e)
            out.append("%s | %s | %s | %s" % (graph, obj.get_name(), str(obj.get_node_title()).replace("\n", " "), " ".join(links)))
open(LOG, "w", encoding="utf-8").write("\n".join(out))
