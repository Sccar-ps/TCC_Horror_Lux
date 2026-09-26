# Somente leitura: levantamento para o sistema de loop (portas, espaco livre, pawn, grafo da porta, API de grafos).
# Uso (console do editor, com o Mapa_B aberto):  py "C:/Users/bruno/Documents/Unreal Projects/TCC_Horror_Lux/Tools/Loop/probe_loop.py"
# Saida: Saved/Loop/probe.txt. Cria e apaga um Blueprint temporario em /Game/Masion/LUX/Loop/_Probe (teste da API).
import os, math, traceback, unreal

saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUTDIR = os.path.join(saved, "Loop")
os.makedirs(OUTDIR, exist_ok=True)
LOG = os.path.join(OUTDIR, "probe.txt")
out = []
EAL = unreal.EditorAssetLibrary
BEL = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor
DOOR = "/Game/FPMovement/Blueprints/Doors/BP_BaseDoor"
PROBE = "/Game/Masion/LUX/Loop/_Probe/BP_ProbeDoor"


def w(*a):
    out.append(" ".join(str(x) for x in a))


def v(x):
    return "(%.1f, %.1f, %.1f)" % (x.x, x.y, x.z)


def r(x):
    return "(p%.1f y%.1f r%.1f)" % (x.pitch, x.yaw, x.roll)


def section(t):
    w("")
    w("=" * 10, t)


def dump_graph(bp, gname):
    try:
        ge = BGE.get_graph_editor_by_name(bp, gname)
        nodes = list(ge.list_all_nodes())
    except Exception as e:
        w("  (grafo %s: %s)" % (gname, e))
        return
    w("--- grafo %s: %d nos" % (gname, len(nodes)))
    for n in nodes:
        title = str(n.get_node_title()).replace("\n", " / ")
        pins = []
        for p in n.list_all_pins():
            nm = str(p.get_pin_name())
            links = p.list_connected_pins()
            val = p.get_pin_value()
            s = nm
            try:
                s += ":" + str(p.get_pin_type_display_string())
            except Exception:
                pass
            if links:
                s += "->[" + ",".join("%s.%s" % (l.get_owning_node().get_name(), l.get_pin_name()) for l in links) + "]"
            elif val:
                s += "=" + val[:60]
            pins.append(s)
        w("  %-36s %-44s %s" % (n.get_name(), title[:44], " | ".join(pins)))


try:
    ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    world = ues.get_editor_world()
    section("MUNDO")
    w("world:", world.get_path_name())
    door_bp = EAL.load_asset(DOOR)
    door_cls = door_bp.generated_class()
    varnames = [str(n) for n in BEL.list_member_variable_names(door_bp)]
    w("BP_BaseDoor vars:", varnames)
    for vn in varnames:
        try:
            w("  var %-24s tipo=%s" % (vn, BEL.get_member_variable_type(door_bp, vn)))
        except Exception as e:
            w("  var %-24s (tipo?) %s" % (vn, str(e)[:80]))
    actors = list(eas.get_all_level_actors())
    w("atores no nivel:", len(actors))

    section("PORTAS")
    doors = [a for a in actors if unreal.MathLibrary.class_is_child_of(a.get_class(), door_cls)]
    for a in doors:
        w("")
        w("PORTA", a.get_actor_label(), a.get_class().get_name(), "loc", v(a.get_actor_location()), "rot",
          r(a.get_actor_rotation()), "scale", v(a.get_actor_scale3d()), "tags", [str(t) for t in a.tags])
        o, e = a.get_actor_bounds(False)
        w("  bounds ator: centro", v(o), "extent", v(e))
        for vn in varnames:
            try:
                w("  %s = %s" % (vn, a.get_editor_property(vn)))
            except Exception as ex:
                w("  %s : %s" % (vn, str(ex)[:90]))
        for c in a.get_components_by_class(unreal.SceneComponent):
            line = "  comp %-18s %-24s rel %s %s %s | mundo %s" % (
                c.get_name(), c.get_class().get_name(), v(c.get_editor_property("relative_location")),
                r(c.get_editor_property("relative_rotation")), v(c.get_editor_property("relative_scale3d")),
                v(c.get_world_location()))
            if isinstance(c, unreal.StaticMeshComponent):
                sm = c.get_editor_property("static_mesh")
                bo, be, _ = unreal.SystemLibrary.get_component_bounds(c)
                line += " | mesh %s | bounds centro %s ext %s | colisao %s" % (
                    sm.get_path_name() if sm else None, v(bo), v(be), c.get_collision_profile_name())
                if c.get_name().startswith("Door") and not c.get_name().startswith("DoorHandle"):
                    piv = c.get_world_location()
                    off = bo - piv
                    try:
                        deg = float(a.get_editor_property("OpenDegrees"))
                    except Exception:
                        deg = 90.0
                    for sgn in (1, -1):
                        t = math.radians(sgn * deg)
                        nx = off.x * math.cos(t) - off.y * math.sin(t)
                        ny = off.x * math.sin(t) + off.y * math.cos(t)
                        line += " | yaw %+.0f -> centro da folha vai p/ %s" % (sgn * deg, v(unreal.Vector(piv.x + nx, piv.y + ny, bo.z)))
            w(line)
        # vizinhanca (2D, 300 cm)
        p = a.get_actor_location()
        near = []
        for b in actors:
            if b == a:
                continue
            try:
                bo, be = b.get_actor_bounds(False)
            except Exception:
                continue
            if be.x > 800 or be.y > 800:
                continue
            dx = max(abs(bo.x - p.x) - be.x, 0)
            dy = max(abs(bo.y - p.y) - be.y, 0)
            if math.hypot(dx, dy) < 300:
                near.append((math.hypot(dx, dy), b.get_actor_label(), b.get_class().get_name(), v(bo), v(be),
                             str(b.get_folder_path())))
        for d, lab, cls, bo, be, fold in sorted(near):
            w("    perto %5.0f cm  %-34s %-22s centro %s ext %s pasta %s" % (d, lab, cls, bo, be, fold))

    section("PLAYERSTART / GAMEMODE / PAWN")
    for a in actors:
        if isinstance(a, unreal.PlayerStart):
            w("PlayerStart", a.get_actor_label(), v(a.get_actor_location()), r(a.get_actor_rotation()))
    ws = world.get_world_settings()
    try:
        w("WorldSettings.default_game_mode:", ws.get_editor_property("default_game_mode"))
    except Exception as e:
        w("default_game_mode:", e)
    gm = EAL.load_asset("/Game/FPMovement/Player/Blueprints/BP_PlayerMode")
    gm_cdo = unreal.get_default_object(gm.generated_class())
    pawn_cls = gm_cdo.get_editor_property("default_pawn_class")
    w("BP_PlayerMode.default_pawn_class:", pawn_cls.get_path_name() if pawn_cls else None)
    w("BP_PlayerMode.player_controller_class:", gm_cdo.get_editor_property("player_controller_class").get_path_name())
    if pawn_cls:
        pcdo = unreal.get_default_object(pawn_cls)
        cap = pcdo.get_editor_property("capsule_component")
        w("capsula: half %.1f raio %.1f" % (cap.get_editor_property("capsule_half_height"), cap.get_editor_property("capsule_radius")))
        pbp = BEL.get_blueprint_for_class(pawn_cls) if hasattr(BEL, "get_blueprint_for_class") else None
        chain = []
        c = pawn_cls
        while c:
            chain.append(c.get_path_name())
            try:
                bpx = BEL.get_blueprint_for_class(c)
                c = BEL.get_blueprint_parent_class(bpx) if bpx else None
            except Exception:
                c = None
        w("hierarquia do pawn:", chain)

    section("CHAMADAS DE INTERACT NOS BLUEPRINTS DO PLAYER")
    for path in ("/Game/FPMovement/Player/Blueprints/BP_Player", "/Game/Characters/MixamoFP/Blueprints/BP_Player_Cowboy"):
        bp = EAL.load_asset(path)
        if not bp:
            continue
        for g in BEL.list_graph_names(bp) if hasattr(BEL, "list_graph_names") else []:
            try:
                ge = BGE.get_graph_editor_by_name(bp, g)
                for n in ge.list_all_nodes():
                    t = str(n.get_node_title())
                    if "nteract" in t:
                        pins = ["%s:%s" % (p.get_pin_name(), p.get_pin_type_display_string()) for p in n.list_all_pins()]
                        w("  %s | %s | %s | %s | %s" % (path.rsplit("/", 1)[-1], g, n.get_class().get_name(), t.replace("\n", " / "), pins))
            except Exception as e:
                w("  grafo %s: %s" % (g, str(e)[:80]))

    section("GRAFOS DA BP_BaseDoor")
    gnames = [str(g) for g in BEL.list_graph_names(door_bp)]
    w("grafos:", gnames)
    for g in gnames:
        dump_graph(door_bp, g)
    section("INTERFACE BP_Interact")
    itf = EAL.load_asset("/Game/FPMovement/Player/Blueprints/Interface/BP_Interact")
    for g in [str(x) for x in BEL.list_graph_names(itf)]:
        dump_graph(itf, g)

    section("API DE GRAFOS (Blueprint temporario filho da BP_BaseDoor)")
    if EAL.does_asset_exist(PROBE):
        EAL.delete_asset(PROBE)
    pbp = BEL.create_blueprint_asset_with_parent(PROBE, door_cls)
    w("probe criado:", pbp.get_path_name() if pbp else None)
    ge = BGE.get_graph_editor_by_name(pbp, "EventGraph")
    names = [str(x) for x in ge.list_available_nodes([])]
    w("nos disponiveis:", len(names))
    keys = ("Interact", "Parent", "Camera Fade", "Teleport", "Camera Cut", "|Delay", "For Loop", "For Each Loop",
            "With Tag", "Ignore Move", "Ignore Look", "ActorBeginOverlap", "Actor Begin Overlap", "Play Sound 2D",
            "Actor Hidden In Game", "Enable Collision", "Append", "String To Name", "To String (Integer)",
            "Component By Class", "Set Control Rotation", "Get Control Rotation", "Player Camera Manager",
            "Get Player Character", "Get Player Controller", "Begin Play", "Branch", "Custom Event", "Is Valid",
            "Break Rotator", "Make Rotator", "Cast To AudioComponent", "Fade Out", "Play (", "Is Closed", "Get Actor Location",
            "Get Actor Rotation", "Equal (Object)", "AND Boolean", "Less (Integer)", "Increment Int", "Add (")
    for k in keys:
        hits = [n for n in names if k.lower() in n.lower()]
        w("  [%s] %d: %s" % (k, len(hits), hits[:14]))
    for fp in ("/Script/Engine.KismetSystemLibrary:Delay", "/Script/Engine.KismetSystemLibrary.Delay"):
        try:
            n = ge.add_call_function_node(fp)
            w("add_call_function_node(%s) -> %s" % (fp, n.get_name() if n else None))
            if n:
                w("   pinos:", ["%s:%s" % (p.get_pin_name(), p.get_pin_type_display_string()) for p in n.list_all_pins()])
        except Exception as e:
            w("add_call_function_node(%s) ERRO %s" % (fp, str(e)[:120]))
    for fn in ("create_node_from_name", "add_component_bound_event_node", "add_dispatcher_event_node", "add_custom_event_node",
               "add_call_function_node", "add_get_member_variable_node", "add_macro_node", "find_event_node"):
        w("DOC %s: %s" % (fn, (getattr(BGE, fn).__doc__ or "").replace("\n", " ")[:900]))
    for fn in ("add_event_override", "add_function_override", "add_event_dispatcher", "add_event_dispatcher_parameter",
               "add_member_variable", "get_object_reference_type", "set_blueprint_variable_instance_editable"):
        w("DOC BEL.%s: %s" % (fn, (getattr(BEL, fn).__doc__ or "").replace("\n", " ")[:700]))
    unreal.EditorAssetLibrary.delete_asset(PROBE)
    EAL.delete_directory("/Game/Masion/LUX/Loop/_Probe")
    w("probe apagado")
except Exception:
    w("ERRO " + traceback.format_exc())
open(LOG, "w", encoding="utf-8").write("\n".join(out))
unreal.log("LUX probe_loop -> " + LOG)
