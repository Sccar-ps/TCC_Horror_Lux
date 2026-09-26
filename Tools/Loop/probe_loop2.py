# Somente leitura (exceto um Blueprint temporario nao salvo em /Game/Masion/LUX/Loop/_Probe): nos para o grafo do loop,
# distorcao da porta aberta e 3 fotos (chegada no quarto, porta do quarto vista do corredor, porta da sala).
# Saida: Saved/Loop/probe2.txt e Saved/Loop/shot_*.png
import os, glob, math, traceback, unreal

saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUTDIR = os.path.join(saved, "Loop")
LOG = os.path.join(OUTDIR, "probe2.txt")
SRC = os.path.join(saved, "Screenshots", "WindowsEditor")
out = []
EAL = unreal.EditorAssetLibrary
BEL = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor
DOOR = "/Game/FPMovement/Blueprints/Doors/BP_BaseDoor"
PROBE = "/Game/Masion/LUX/Loop/_Probe/BP_ProbeDoor2"


def w(*a):
    out.append(" ".join(str(x) for x in a))


def v(x):
    return "(%.1f, %.1f, %.1f)" % (x.x, x.y, x.z)


def flush():
    open(LOG, "w", encoding="utf-8").write("\n".join(out))


def pins(n):
    return ["%s:%s" % (p.get_pin_name(), p.get_pin_type_display_string()) for p in n.list_all_pins()]


try:
    ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    door_cls = EAL.load_asset(DOOR).generated_class()
    by = {a.get_actor_label(): a for a in eas.get_all_level_actors()}

    # ---- 1) nos disponiveis num filho da BP_BaseDoor
    pbp = EAL.load_asset(PROBE) if EAL.does_asset_exist(PROBE) else BEL.create_blueprint_asset_with_parent(PROBE, door_cls)
    ge = BGE.get_graph_editor_by_name(pbp, "EventGraph")
    names = [str(x) for x in ge.list_available_nodes([])]
    w("nos:", len(names))
    for k in ("Interact", "Parent"):
        hits = [n for n in names if k.lower() in n.lower() and not any(s in n for s in ("Clothing", "VR", "Viewport", "Interchange", "TypedElement", "ToolMenu", "Widget|", "PCG"))]
        w("[%s] %d: %s" % (k, len(hits), hits))
    try:
        ev = BEL.add_event_override(pbp, "Interact", unreal.IntPoint(0, 0))
        w("add_event_override(Interact) ->", ev.get_name() if ev else None, pins(ev) if ev else "")
        if ev:
            ctx = [ev.find_then_pin()]
            hits = [n for n in ge.list_available_nodes(ctx) if "parent" in n.lower()]
            w("com contexto then do evento, 'parent':", hits)
    except Exception as e:
        w("add_event_override ERRO", str(e)[:200])
    # variavel do tipo BP_BaseDoor como contexto -> como chamar Interact numa porta
    BEL.add_member_variable(pbp, "PortaTeste", BEL.get_object_reference_type(door_cls))
    BEL.compile_blueprint(pbp)
    g = ge.add_get_member_variable_node("PortaTeste")
    w("get PortaTeste:", pins(g))
    ctxn = [n for n in ge.list_available_nodes([g.find_output_pin("PortaTeste")]) if "nteract" in n]
    w("com contexto PortaTeste, 'nteract':", ctxn)
    for fp in ("/Game/FPMovement/Player/Blueprints/Interface/BP_Interact.BP_Interact_C:Interact",
               "/Game/FPMovement/Blueprints/Doors/BP_BaseDoor.BP_BaseDoor_C:Interact"):
        try:
            n = ge.add_call_function_node(fp)
            ok = n and n.find_input_pin("self").try_create_connection(g.find_output_pin("PortaTeste"))
            w("add_call_function_node(%s) -> %s %s liga self=%s" % (fp, n.get_class().get_name() if n else None, pins(n) if n else "", ok))
        except Exception as e:
            w("add_call_function_node(%s) ERRO %s" % (fp, str(e)[:150]))
    for nm in ("Utilities|FlowControl|ForLoop", "Utilities|Array|ForEachLoop", "Utilities|FlowControl|ForEachLoop",
               "Utilities|Casting|CastToAudioComponent", "Utilities|FlowControl|Sequence", "AddEvent|Collision|EventActorBeginOverlap"):
        w("existe %s: %s" % (nm, nm in names))
    for k in ("ForLoop", "ForEach", "CastToAudioComponent", "Sequence", "IsValid", "StartCameraFade", "SetGameCameraCut",
              "SetIgnoreMoveInput", "GetAllActorsWithTag", "StringToName", "EventBeginPlay"):
        w("[%s] %s" % (k, [n for n in names if k.lower() in n.lower()][:12]))
    BEL.compile_blueprint(pbp)
    w("probe NAO salvo (fica so na memoria)")

    # ---- 2) distorcao da folha aberta (porta do quarto)
    d7 = by.get("BP_BaseDoor7")
    leaf = [c for c in d7.get_components_by_class(unreal.StaticMeshComponent) if c.get_name() == "Door"][0]
    bo, be, _ = unreal.SystemLibrary.get_component_bounds(leaf)
    w("porta7 fechada: centro %s ext %s | escala mundo da folha %s" % (v(bo), v(be), v(leaf.get_world_scale())))
    leaf.set_editor_property("relative_rotation", unreal.Rotator(roll=0.0, pitch=0.0, yaw=100.0))
    bo, be, _ = unreal.SystemLibrary.get_component_bounds(leaf)
    w("porta7 a 100 graus: centro %s ext %s" % (v(bo), v(be)))
    leaf.set_editor_property("relative_rotation", unreal.Rotator(roll=0.0, pitch=0.0, yaw=0.0))
    ow = by.get("SM_Door_Double_NN_01b")
    if ow:
        smc = ow.static_mesh_component
        w("SM_Door_Double_NN_01b: colisao %s, perfil %s, loc %s, rot %s, escala %s, bounds %s" % (
            smc.get_collision_enabled(), smc.get_collision_profile_name(), v(ow.get_actor_location()),
            ow.get_actor_rotation(), v(ow.get_actor_scale3d()), [v(x) for x in ow.get_actor_bounds(False)]))
except Exception:
    w("ERRO " + traceback.format_exc())
flush()

# ---- 3) fotos (camera do viewport em game view)
SHOTS = [("chegada", (-3275, 955, 165), -5.0, -90.0),
         ("corredor_para_quarto", (-3275, 450, 165), -2.0, 90.0),
         ("sala_para_porta", (-2294, -1780, 165), -5.0, -90.0)]
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
world = ues.get_editor_world()
cam0 = ues.get_level_viewport_camera_info()[-2:]
les.editor_set_game_view(True)
st = {"i": 0, "t": 0.0, "step": "move", "before": set()}


def pngs():
    return set(glob.glob(os.path.join(SRC, "*.png")))


def tick(dt):
    st["t"] += dt
    if st["i"] >= len(SHOTS):
        unreal.unregister_slate_post_tick_callback(handle)
        ues.set_level_viewport_camera_info(cam0[0], cam0[1])
        les.editor_set_game_view(False)
        w("fotos prontas")
        flush()
        return
    name, (x, y, z), pitch, yaw = SHOTS[st["i"]]
    if st["step"] == "move":
        ues.set_level_viewport_camera_info(unreal.Vector(x, y, z), unreal.Rotator(roll=0.0, pitch=pitch, yaw=yaw))
        st.update(step="wait", t=0.0)
    elif st["step"] == "wait" and st["t"] >= 4.0:
        st["before"] = pngs()
        unreal.SystemLibrary.execute_console_command(world, "HighResShot 1")
        st.update(step="save", t=0.0)
    elif st["step"] == "save" and st["t"] >= 1.5:
        new = sorted(pngs() - st["before"], key=os.path.getmtime)
        if new:
            dst = os.path.join(OUTDIR, "shot_%s.png" % name)
            if os.path.exists(dst):
                os.remove(dst)
            os.replace(new[-1], dst)
        st.update(step="move", t=0.0, i=st["i"] + 1)


handle = unreal.register_slate_post_tick_callback(tick)
