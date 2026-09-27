# Refaz so o EventGraph da BP_LuxLoopDoor pelo gerador do setup_loop.py (com a rede de seguranca do Manager).
# Nao mexe nos atores do mapa nem no BP_LuxLoopManager. Salva so a BP_LuxLoopDoor.
#   py "<projeto>/Tools/Loop/fix_loop_door.py"
import importlib, os, sys, unreal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import add_door_slam, setup_loop as sl  # com a guarda __main__, importar nao roda o setup
importlib.reload(add_door_slam)  # o Python do editor guarda o modulo da execucao anterior
sl = importlib.reload(sl)

unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(sl.EAL.load_asset(sl.LDOOR))
sl.build_loop_door(sl.EAL.load_asset(sl.MGR))
print("BP_LuxLoopDoor:", sl.errors(sl.EAL.load_asset(sl.LDOOR), ("EventGraph",)) or "compilou sem erros/avisos")
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in eas.get_all_level_actors():
    if a.get_class().get_name().startswith("BP_LuxLoopDoor"):
        m = a.get_editor_property("Manager")
        print("%s.Manager = %s" % (a.get_actor_label(), m.get_actor_label() if m else None))
U = unreal.EditorLoadingAndSavingUtils
print("sujos", [p.get_name() for p in list(U.get_dirty_map_packages()) + list(U.get_dirty_content_packages())])
