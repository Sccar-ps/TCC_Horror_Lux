# Somente leitura (Blueprint temporario em _Probe, apagado pelo setup_loop): como criar soma de int e comparacoes.
import os, unreal
EAL, BEL, BGE = unreal.EditorAssetLibrary, unreal.BlueprintEditorLibrary, unreal.BlueprintGraphEditor
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())


def main():
    out = []
    path = "/Game/Masion/LUX/Loop/_Probe/BP_Probe4"
    bp = EAL.load_asset(path) if EAL.does_asset_exist(path) else BEL.create_blueprint_asset_with_parent(path, unreal.Actor.static_class())
    ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
    for f in ("Add_IntInt", "GreaterEqual_IntInt", "EqualEqual_ObjectObject", "BooleanAND", "Not_PreBool", "Add_DoubleDouble",
              "Less_IntInt", "Subtract_IntInt"):
        for fp in ("/Script/Engine.KismetMathLibrary:" + f, "/Script/Engine.KismetMathLibrary." + f):
            n = ge.add_call_function_node(fp)
            out.append("%-60s -> %s | %s" % (fp, str(n.get_node_title()).replace("\n", " ") if n else None,
                                               ["%s:%s" % (p.get_pin_name(), p.get_pin_type_display_string()) for p in n.list_all_pins()] if n else ""))
    names = [str(x) for x in ge.list_available_nodes([])]
    out.append("Operators: %s" % [x for x in names if "|Operators|" in x][:60])
    out.append("Integer +: %s" % [x for x in names if x.startswith("Math|Integer")][:80])
    open(os.path.join(saved, "Loop", "probe4.txt"), "w", encoding="utf-8").write("\n".join(out))


main()
