# Etapa D1 (UE): monta o componente BPC_DirectionalSpeed (Blueprint, API BlueprintGraphEditor do UE 5.8) e o adiciona
# ao BP_Player_Cowboy. O BP_Player (FPMovement) nao muda.
#
# Ideia: o BP_Player continua escrevendo CharacterMovement.MaxWalkSpeed (andar 150 / sprint 360 / agachado 80).
# A cada tick o componente detecta quando o valor foi trocado pelo BP_Player (difere do ultimo valor escrito por ele),
# guarda como BaseSpeed e aplica um fator conforme a direcao do input em relacao a frente do personagem:
#   frente = ForwardSprintFactor (sprint) / ForwardWalkFactor (andar), lados = SideFactor, tras = BackwardFactor,
#   interpolado por |cos| do angulo. Agachado fica sem fator (AffectCrouch = false).
import os, unreal
EAL = unreal.EditorAssetLibrary
BEL = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor
PATH = "/Game/Characters/MixamoFP/Blueprints/BPC_DirectionalSpeed"
COWBOY = "/Game/Characters/MixamoFP/Blueprints/BP_Player_Cowboy"
PLAYER_C = "/Game/FPMovement/Player/Blueprints/BP_Player.BP_Player_C"
KML = "/Script/Engine.KismetMathLibrary:"
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(saved, "MixamoFP_dirspeed_build.txt")
CAT = "Velocidade por direcao"
DEFAULTS = (("ForwardSprintFactor", 1.1112), ("ForwardWalkFactor", 1.0), ("SideFactor", 1.0), ("BackwardFactor", 0.8),
            ("AffectCrouch", False), ("Factor", 1.0))
out = []


def w(m):
    out.append(str(m))


def pos(n, x, y):
    try:
        BEL.set_node_pos(n, unreal.IntPoint(int(x), int(y)))
    except Exception:
        n.set_node_pos(unreal.IntPoint(int(x), int(y)))


def fn(ge, name, x, y, owner=KML):
    n = ge.add_call_function_node(owner + name)
    if n is None:
        raise RuntimeError("funcao nao encontrada: " + owner + name)
    pos(n, x, y)
    return n


def vget(ge, name, x, y, cls=""):
    n = ge.add_get_member_variable_node(name, cls) if cls else ge.add_get_member_variable_node(name)
    if n is None:
        raise RuntimeError("get falhou: %s %s" % (name, cls))
    pos(n, x, y)
    return n


def vset(ge, name, x, y, cls=""):
    n = ge.add_set_member_variable_node(name, cls) if cls else ge.add_set_member_variable_node(name)
    if n is None:
        raise RuntimeError("set falhou: %s %s" % (name, cls))
    pos(n, x, y)
    return n


def link(a, a_pin, b, b_pin):
    pa, pb = a.find_output_pin(a_pin), b.find_input_pin(b_pin)
    ok = bool(pa and pa.is_valid() and pb and pb.is_valid() and pa.try_create_connection(pb))
    if not ok:
        w("  FALHA link %s.%s -> %s.%s (pinos out=%s in=%s)" % (a.get_name(), a_pin, b.get_name(), b_pin,
          [str(p.get_pin_name()) for p in a.list_output_pins()], [str(p.get_pin_name()) for p in b.list_input_pins()]))
    return ok


def val(n, pin, v):
    p = n.find_input_pin(pin)
    ok = bool(p and p.is_valid() and p.set_pin_value(v))
    if not ok:
        w("  FALHA valor %s.%s = %s" % (n.get_name(), pin, v))


try:
    bp = EAL.load_asset(PATH) if EAL.does_asset_exist(PATH) else BEL.create_blueprint_asset_with_parent(PATH, unreal.ActorComponent)
    player_cls = unreal.load_class(None, PLAYER_C)
    real, boolean = BEL.get_basic_type_by_name("real"), BEL.get_basic_type_by_name("bool")
    types = {"ForwardSprintFactor": real, "ForwardWalkFactor": real, "SideFactor": real, "BackwardFactor": real,
             "AffectCrouch": boolean, "Player": BEL.get_object_reference_type(player_cls),
             "CMC": BEL.get_object_reference_type(unreal.CharacterMovementComponent.static_class()),
             "BaseSpeed": real, "WrittenSpeed": real, "Factor": real}
    have = set(str(n) for n in BEL.list_member_variable_names(bp))
    for name, t in types.items():
        if name not in have:
            BEL.add_member_variable(bp, name, t)
    for name in ("ForwardSprintFactor", "ForwardWalkFactor", "SideFactor", "BackwardFactor", "AffectCrouch"):
        try:
            BEL.set_blueprint_variable_instance_editable(bp, name, True)
            BEL.set_blueprint_variable_category(bp, name, CAT)
        except Exception as e:
            w("  aviso var %s: %s" % (name, e))
    BEL.compile_blueprint(bp)

    ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
    old = list(ge.list_all_nodes())                       # recomeca do zero (inclui os eventos "fantasma" do template)
    if old:
        ge.remove_nodes(old)
    for c in list(ge.list_comment_nodes()):
        ge.remove_comment_node(c)
    names = set(ge.list_available_nodes([]))

    # ------------------------------------------------------------------ BeginPlay: guarda Player, CMC e a velocidade base
    X0, Y0 = -1400, -700
    e_bp = BEL.add_event_override(bp, "ReceiveBeginPlay", unreal.IntPoint(X0, Y0))
    n_owner = fn(ge, "GetOwner", X0 + 60, Y0 + 180, owner="/Script/Engine.ActorComponent:")
    norm = lambda s: s.lower().replace("_", "").replace(" ", "")
    cands = sorted(s for s in names if "casting|castto" in s.lower() and "player" in s.lower())
    cast_name = next((s for s in cands if norm(s) == "utilities|casting|casttobpplayer"), None)
    w("  cast: %s (candidatos %s)" % (cast_name, cands[:12]))
    n_cast = ge.create_node_from_name(cast_name, unreal.Vector2D(X0 + 320, Y0), [])
    if n_cast is None:
        raise RuntimeError("no de cast nao criado")
    s_pl = vset(ge, "Player", X0 + 700, Y0)
    g_cm = vget(ge, "CharacterMovement", X0 + 760, Y0 + 200, "/Script/Engine.Character")
    s_cmc = vset(ge, "CMC", X0 + 1060, Y0)
    g_mw0 = vget(ge, "MaxWalkSpeed", X0 + 1100, Y0 + 200, "/Script/Engine.CharacterMovementComponent")
    s_b0 = vset(ge, "BaseSpeed", X0 + 1420, Y0)
    s_w0 = vset(ge, "WrittenSpeed", X0 + 1700, Y0)
    n_self = ge.create_node_from_name("Variables|Getareferencetoself", unreal.Vector2D(X0 + 1760, Y0 + 260), [])
    n_pre = fn(ge, "AddTickPrerequisiteComponent", X0 + 1980, Y0, owner="/Script/Engine.ActorComponent:")
    link(e_bp, "then", n_cast, "execute")
    link(n_owner, "ReturnValue", n_cast, "Object")
    link(n_cast, "then", s_pl, "execute")
    cast_out = [str(p.get_pin_name()) for p in n_cast.list_output_pins() if "BP" in str(p.get_pin_name())]
    link(n_cast, cast_out[0] if cast_out else "AsBP Player", s_pl, "Player")
    link(s_pl, "Output_Get", g_cm, "self")
    link(s_pl, "then", s_cmc, "execute")
    link(g_cm, "CharacterMovement", s_cmc, "CMC")
    link(s_cmc, "Output_Get", g_mw0, "self")
    link(s_cmc, "then", s_b0, "execute")
    link(g_mw0, "MaxWalkSpeed", s_b0, "BaseSpeed")
    link(s_b0, "then", s_w0, "execute")
    link(s_b0, "Output_Get", s_w0, "WrittenSpeed")
    link(s_w0, "then", n_pre, "execute")                  # o CMC passa a tickar DEPOIS deste componente
    link(s_cmc, "Output_Get", n_pre, "self")
    link(n_self, "self", n_pre, "PrerequisiteComponent")
    begin_nodes = [e_bp, n_owner, n_cast, s_pl, g_cm, s_cmc, g_mw0, s_b0, s_w0, n_self, n_pre]

    # ------------------------------------------------------------------ Tick: detecta troca feita pelo BP_Player
    X1, Y1 = -1400, 0
    e_tk = BEL.add_event_override(bp, "ReceiveTick", unreal.IntPoint(X1, Y1))
    g_cmc = vget(ge, "CMC", X1 + 20, Y1 + 200)
    n_valid = fn(ge, "IsValid", X1 + 220, Y1 + 200, owner="/Script/Engine.KismetSystemLibrary:")
    b1 = ge.add_branch_node(); pos(b1, X1 + 460, Y1)
    g_mw1 = vget(ge, "MaxWalkSpeed", X1 + 300, Y1 + 340, "/Script/Engine.CharacterMovementComponent")
    g_wr1 = vget(ge, "WrittenSpeed", X1 + 360, Y1 + 440)
    n_eq = fn(ge, "NearlyEqual_FloatFloat", X1 + 640, Y1 + 340)
    b2 = ge.add_branch_node(); pos(b2, X1 + 900, Y1)
    s_b1 = vset(ge, "BaseSpeed", X1 + 1160, Y1 + 160)
    s_fac = vset(ge, "Factor", X1 + 1480, Y1)
    g_bs2 = vget(ge, "BaseSpeed", X1 + 1500, Y1 + 200)
    n_mul = fn(ge, "Multiply_DoubleDouble", X1 + 1740, Y1 + 160)
    s_w1 = vset(ge, "WrittenSpeed", X1 + 1980, Y1)
    s_mw = vset(ge, "MaxWalkSpeed", X1 + 2280, Y1, "/Script/Engine.CharacterMovementComponent")
    link(e_tk, "then", b1, "execute")
    link(g_cmc, "CMC", n_valid, "Object")
    link(n_valid, "ReturnValue", b1, "Condition")
    link(g_cmc, "CMC", g_mw1, "self")
    link(g_mw1, "MaxWalkSpeed", n_eq, "A")
    link(g_wr1, "WrittenSpeed", n_eq, "B")
    val(n_eq, "ErrorTolerance", "0.01")
    link(b1, "then", b2, "execute")
    link(n_eq, "ReturnValue", b2, "Condition")
    link(b2, "then", s_fac, "execute")                    # igual ao ultimo valor escrito: base nao mudou
    link(b2, "else", s_b1, "execute")                     # o BP_Player trocou (sprint/andar/agachar): nova base
    link(g_mw1, "MaxWalkSpeed", s_b1, "BaseSpeed")
    link(s_b1, "then", s_fac, "execute")
    link(s_fac, "then", s_w1, "execute")
    link(g_bs2, "BaseSpeed", n_mul, "A")
    link(s_fac, "Output_Get", n_mul, "B")
    link(n_mul, "ReturnValue", s_w1, "WrittenSpeed")
    link(s_w1, "then", s_mw, "execute")
    link(g_cmc, "CMC", s_mw, "self")
    link(s_w1, "Output_Get", s_mw, "MaxWalkSpeed")
    tick_nodes = [e_tk, g_cmc, n_valid, b1, g_mw1, g_wr1, n_eq, b2, s_b1, s_fac, g_bs2, n_mul, s_w1, s_mw]

    # ------------------------------------------------------------------ Fator pela direcao do input (tudo puro)
    X2, Y2 = -1400, 700
    n_acc = fn(ge, "GetCurrentAcceleration", X2, Y2, owner="/Script/Engine.CharacterMovementComponent:")
    link(g_cmc, "CMC", n_acc, "self")
    n_len = fn(ge, "VSizeXYSquared", X2 + 300, Y2 - 60)
    link(n_acc, "ReturnValue", n_len, "A")
    n_has = fn(ge, "Greater_DoubleDouble", X2 + 540, Y2 - 60)
    link(n_len, "ReturnValue", n_has, "A"); val(n_has, "B", "1.0")
    n_dir = fn(ge, "Normal2D", X2 + 300, Y2 + 80)
    link(n_acc, "ReturnValue", n_dir, "A")
    g_pl = vget(ge, "Player", X2, Y2 + 260)
    n_fwd = fn(ge, "GetActorForwardVector", X2 + 240, Y2 + 240, owner="/Script/Engine.Actor:")
    link(g_pl, "Player", n_fwd, "self")
    n_dot = fn(ge, "Dot_VectorVector", X2 + 560, Y2 + 120)
    link(n_dir, "ReturnValue", n_dot, "A"); link(n_fwd, "ReturnValue", n_dot, "B")
    g_pw = vget(ge, "MaxWalkSpeed", X2 + 240, Y2 + 380, PLAYER_C)
    link(g_pl, "Player", g_pw, "self")
    n_thr = fn(ge, "Add_DoubleDouble", X2 + 520, Y2 + 380)
    link(g_pw, "MaxWalkSpeed", n_thr, "A"); val(n_thr, "B", "1.0")
    g_bs3 = vget(ge, "BaseSpeed", X2 + 520, Y2 + 520)
    n_spr = fn(ge, "Greater_DoubleDouble", X2 + 760, Y2 + 420)
    link(g_bs3, "BaseSpeed", n_spr, "A"); link(n_thr, "ReturnValue", n_spr, "B")
    g_fs = vget(ge, "ForwardSprintFactor", X2 + 760, Y2 + 560)
    g_fw = vget(ge, "ForwardWalkFactor", X2 + 760, Y2 + 640)
    n_ff = fn(ge, "SelectFloat", X2 + 1040, Y2 + 480)
    link(g_fs, "ForwardSprintFactor", n_ff, "A"); link(g_fw, "ForwardWalkFactor", n_ff, "B"); link(n_spr, "ReturnValue", n_ff, "bPickA")
    n_ge = fn(ge, "GreaterEqual_DoubleDouble", X2 + 820, Y2 + 180)
    link(n_dot, "ReturnValue", n_ge, "A"); val(n_ge, "B", "0.0")
    g_bk = vget(ge, "BackwardFactor", X2 + 1040, Y2 + 640)
    n_end = fn(ge, "SelectFloat", X2 + 1300, Y2 + 360)
    link(n_ff, "ReturnValue", n_end, "A"); link(g_bk, "BackwardFactor", n_end, "B"); link(n_ge, "ReturnValue", n_end, "bPickA")
    n_abs = fn(ge, "Abs", X2 + 820, Y2 + 60)
    link(n_dot, "ReturnValue", n_abs, "A")
    g_sd = vget(ge, "SideFactor", X2 + 1300, Y2 + 240)
    n_lerp = fn(ge, "Lerp", X2 + 1560, Y2 + 200)
    link(g_sd, "SideFactor", n_lerp, "A"); link(n_end, "ReturnValue", n_lerp, "B"); link(n_abs, "ReturnValue", n_lerp, "Alpha")
    g_cr = vget(ge, "IsCrouching?", X2 + 1300, Y2 + 760, PLAYER_C)
    link(g_pl, "Player", g_cr, "self")
    g_af = vget(ge, "AffectCrouch", X2 + 1300, Y2 + 860)
    n_not = fn(ge, "Not_PreBool", X2 + 1560, Y2 + 860)
    link(g_af, "AffectCrouch", n_not, "A")
    n_and = fn(ge, "BooleanAND", X2 + 1780, Y2 + 760)
    link(g_cr, "IsCrouching?", n_and, "A"); link(n_not, "ReturnValue", n_and, "B")
    n_f2 = fn(ge, "SelectFloat", X2 + 2020, Y2 + 300)
    val(n_f2, "A", "1.0"); link(n_lerp, "ReturnValue", n_f2, "B"); link(n_and, "ReturnValue", n_f2, "bPickA")
    g_fc = vget(ge, "Factor", X2 + 2020, Y2 + 480)
    n_sel = fn(ge, "SelectFloat", X2 + 2280, Y2 + 120)
    link(n_f2, "ReturnValue", n_sel, "A"); link(g_fc, "Factor", n_sel, "B"); link(n_has, "ReturnValue", n_sel, "bPickA")
    link(n_sel, "ReturnValue", s_fac, "Factor")
    math_nodes = [n_acc, n_len, n_has, n_dir, g_pl, n_fwd, n_dot, g_pw, n_thr, g_bs3, n_spr, g_fs, g_fw, n_ff, n_ge, g_bk,
                  n_end, n_abs, g_sd, n_lerp, g_cr, g_af, n_not, n_and, n_f2, g_fc, n_sel]

    for text, nodes in (("1) BeginPlay: guarda Player (BP_Player), CMC e a velocidade atual; o CMC passa a tickar depois deste componente",
                         begin_nodes),
                        ("2) Tick: se MaxWalkSpeed difere do ultimo valor escrito aqui, foi o BP_Player (sprint/andar/agachar) -> nova BaseSpeed. "
                         "Depois escreve BaseSpeed * Factor no CharacterMovement", tick_nodes),
                        ("3) Factor: cos = dot(direcao do input, frente). Frente = ForwardSprintFactor (sprint) ou ForwardWalkFactor; "
                         "tras = BackwardFactor; lados = SideFactor; interpola por |cos|. Agachado = 1 (AffectCrouch). Sem input mantem o anterior",
                         math_nodes)):
        try:
            ge.add_comment_to_nodes(text, nodes, 60)
        except Exception as e:
            w("  aviso comentario: %s" % e)

    BEL.compile_blueprint(bp)
    cdo = unreal.get_default_object(bp.generated_class())
    for k, v in DEFAULTS:
        cdo.set_editor_property(k, v)
    w("status=%s | erros=%s | avisos=%s" % (bp.get_editor_property("status"),
                                            [n.get_name() for n in ge.list_nodes_with_errors()],
                                            [n.get_name() for n in ge.list_nodes_with_warnings()]))
    w("defaults: %s" % [(k, cdo.get_editor_property(k)) for k, _ in DEFAULTS])
    w("eventos: %s" % [(str(e.get_editor_property("name")), e.get_editor_property("is_implemented")) for e in BEL.list_events(bp)])
    EAL.save_loaded_asset(bp, False)

    # ------------------------------------------------------------------ adiciona ao BP_Player_Cowboy
    cow = EAL.load_asset(COWBOY)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    handles = sds.k2_gather_subobject_data_for_blueprint(cow)
    exists = False
    for h in handles:
        o = lib.get_object(lib.get_data(h))
        if o and o.get_class() == bp.generated_class():
            exists = True
    if not exists:
        prm = unreal.AddNewSubobjectParams(parent_handle=handles[0], new_class=bp.generated_class(), blueprint_context=cow)
        res = sds.add_new_subobject(prm)
        h = res[0] if isinstance(res, tuple) else res
        w("add_new_subobject: %s" % (res,))
        try:
            sds.rename_subobject(h, unreal.Text("DirectionalSpeed"))
        except Exception as e:
            w("  aviso rename: %s" % e)
    BEL.compile_blueprint(cow)
    EAL.save_loaded_asset(cow, False)
    comps = []
    for h in sds.k2_gather_subobject_data_for_blueprint(cow):
        o = lib.get_object(lib.get_data(h))
        if o:
            comps.append("%s(%s)" % (o.get_name(), o.get_class().get_name()))
    w("BP_Player_Cowboy componentes: %s" % comps)

    # ------------------------------------------------------------------ relatorio do grafo
    for n in ge.list_all_nodes():
        links = []
        for p in n.list_all_pins():
            c = p.list_connected_pins()
            if c:
                links.append("%s->[%s]" % (p.get_pin_name(), ",".join("%s.%s" % (l.get_owning_node().get_name(), l.get_pin_name()) for l in c)))
        w("  %-34s %-40s %s" % (n.get_name(), str(n.get_node_title()).replace("\n", " ")[:40], " ".join(links)))
except Exception:
    import traceback
    w("ERRO " + traceback.format_exc())
open(LOG, "w", encoding="utf-8").write("\n".join(out))
