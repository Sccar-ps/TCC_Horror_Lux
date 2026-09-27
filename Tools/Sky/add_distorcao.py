# LUX - Distorcao temporal (item 1): em alguns loops, o sol cruza o ceu N vezes em poucos segundos e volta a mesma noite.
# Ligada por padrao desde 27/09 (DISTORCAO_PADRAO; modo "padrao" grava so isso). O ator de condicao do Passo 4 restringe.
#   py "<projeto>/Tools/Sky/add_distorcao.py" sondar|instalar|verificar|desfazer|padrao
# Pecas: BP_LuxCeu (ator com PPDistorcao + Custom Events), LS_LuxDistorcao (Level Sequence da lua/ceu/PP),
# LUX_Ceu e LUX_Distorcao_Seq no Mapa_B, e um ramo no gatilho do LOOP_Manager (tambem gerado pelo setup_loop.py).
# Nao mexe no PedirTroca, na BP_BaseDoor, no PPV. Nunca recarrega pacote do disco. Log: Saved/Sky/distorcao_log.txt
import importlib, json, math, os, sys, traceback, unreal

# ------------------------------------------------------------------ constantes
N = 4                 # ciclos de sol (2..6)
T = 2.4               # segundos por ciclo (>= 2.2)
DIA_EV = 2.25         # pico do sol = lua * 2^DIA_EV
PICO_PITCH = -40.0
CEU_GANHO = 0.5
ARCO_YAW = 80.0
FPS = 30
APAGAR_ASSETS = False
GRAFO_VERSAO = 1      # sobe quando o grafo do BP_LuxCeu mudar (ele e refeito inteiro)
DISTORCAO_PADRAO = True  # Class Default de bDistorcaoAtiva (27/09: ligada; o ator de condicao do Passo 4 restringe a C/D)

CICLO = int(round(T * FPS))          # 72
S = [45 + CICLO * k for k in range(N)]
E = 45 + CICLO * N                   # 333
F = E + 60                           # 393
END = F + 15                         # 408 (fim exclusivo)
TE = E / float(FPS)                  # 11.1 s
DAWN, NOON = (1.0, 0.70, 0.45), (1.0, 0.97, 0.92)

EAL, BEL, BGE = unreal.EditorAssetLibrary, unreal.BlueprintEditorLibrary, unreal.BlueprintGraphEditor
DIR = "/Game/Masion/LUX/Ceu"
CEU = DIR + "/BP_LuxCeu"
CEU_C = CEU + ".BP_LuxCeu_C"
LS = DIR + "/LS_LuxDistorcao"
MGR = "/Game/Masion/LUX/Loop/BP_LuxLoopManager"
MGR_C = MGR + ".BP_LuxLoopManager_C"
KSL, KML, GS, ARR = ("/Script/Engine.KismetSystemLibrary:", "/Script/Engine.KismetMathLibrary:",
                     "/Script/Engine.GameplayStatics:", "/Script/Engine.KismetArrayLibrary:")
STR, TXT = "/Script/Engine.KismetStringLibrary:", "/Script/Engine.KismetTextLibrary:"
PLAYER = "/Script/MovieScene.MovieSceneSequencePlayer:"
LSA = "/Script/LevelSequence.LevelSequenceActor:"
TAG_SEQ, TAG_CEU = "LuxDistorcao", "LuxCeu"
AQUI = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(os.path.dirname(AQUI))
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(SAVED, "Sky", "distorcao_log.txt")

sys.path.insert(0, os.path.join(PROJ, "Tools", "Loop"))
import add_door_slam as ads
importlib.reload(ads)
G, ok_pin = ads.G, ads.ok_pin


def w(*a):
    line = " ".join(str(x) for x in a)
    unreal.log("[LUX ceu] " + line)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


class Aborta(Exception):
    pass


# ------------------------------------------------------------------ mundo
def eas():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def atores():
    return eas().get_all_level_actors()


def sujos():
    U = unreal.EditorLoadingAndSavingUtils
    return sorted(p.get_name() for p in list(U.get_dirty_map_packages()) + list(U.get_dirty_content_packages()))


def unico(cls, nome):
    lst = [a for a in atores() if isinstance(a, cls)]
    if len(lst) != 1:
        raise Aborta("esperava 1 %s, achei %d: %s" % (nome, len(lst), [a.get_actor_label() for a in lst]))
    return lst[0]


def lua():
    lst = [a for a in atores() if isinstance(a, unreal.DirectionalLight)
           and a.get_components_by_class(unreal.DirectionalLightComponent)[0].get_editor_property("atmosphere_sun_light")]
    if len(lst) != 1:
        raise Aborta("esperava 1 DirectionalLight com Atmosphere Sun Light, achei %d" % len(lst))
    return lst[0]


def por_tag(tag):
    return [a for a in atores() if tag in [str(t) for t in a.tags]]


def ppv():
    lst = [a for a in atores() if isinstance(a, unreal.PostProcessVolume) and a.get_actor_label() == "PPV_Atmosfera"]
    if len(lst) != 1:
        raise Aborta("PPV_Atmosfera nao encontrado")
    return lst[0]


def linear(c):
    return unreal.MathLibrary.conv_color_to_linear_color(c)


def snapshot():
    L = lua()
    lc = L.get_components_by_class(unreal.DirectionalLightComponent)[0]
    r = L.get_actor_rotation()
    sky = unico(unreal.SkyAtmosphere, "SkyAtmosphere").get_components_by_class(unreal.SkyAtmosphereComponent)[0]
    k = sky.get_editor_property("sky_luminance_factor")
    c = lc.get_editor_property("light_color")
    p = ppv()
    ps = p.get_editor_property("settings")
    pps = {}
    for f in ("auto_exposure_method", "auto_exposure_bias", "auto_exposure_min_brightness", "auto_exposure_max_brightness",
              "auto_exposure_speed_up", "auto_exposure_speed_down", "lumen_scene_lighting_update_speed",
              "lumen_final_gather_lighting_update_speed"):
        pps[f] = str(ps.get_editor_property(f))
        pps["override_" + f] = str(ps.get_editor_property("override_" + f))
    mgrs = [a for a in atores() if a.get_class().get_name().startswith("BP_LuxLoopManager")]
    m = {}
    if len(mgrs) == 1:
        for kk in ("LoopFinal", "PortaQuarto", "PortaSaida", "PortaLoop", "Chegada", "CamSala", "CamQuarto", "SomBatida"):
            v = mgrs[0].get_editor_property(kk)
            m[kk] = v.get_actor_label() if isinstance(v, unreal.Actor) else (v.get_path_name() if hasattr(v, "get_path_name") else v)
        m["LoopsBatida"] = list(mgrs[0].get_editor_property("LoopsBatida"))
    portas = {}
    for a in atores():
        if a.get_class().get_name().startswith("BP_LuxLoopDoor"):
            v = a.get_editor_property("Manager")
            portas[a.get_actor_label()] = v.get_actor_label() if v else None
    return {
        "lua": {"pitch": round(r.pitch, 4), "yaw": round(r.yaw, 4), "roll": round(r.roll, 4),
                "loc": [round(x, 3) for x in (L.get_actor_location().x, L.get_actor_location().y, L.get_actor_location().z)],
                "intensity": lc.get_editor_property("intensity"), "color": [c.r, c.g, c.b, c.a],
                "use_temperature": lc.get_editor_property("use_temperature"), "temperature": lc.get_editor_property("temperature"),
                "mobility": str(lc.get_editor_property("mobility")), "sun_light": lc.get_editor_property("atmosphere_sun_light"),
                "cast_shadows": lc.get_editor_property("cast_shadows")},
        "ceu": {"sky_luminance_factor": [k.r, k.g, k.b, k.a]},
        "ppv": pps, "manager": m, "portas": portas, "sujos": sujos()}


def grava(nome, dado):
    p = os.path.join(SAVED, "Sky", nome)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(dado, fh, indent=2, ensure_ascii=False, default=str)


def preflight(sondar=False):
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not world or world.get_name() != "Mapa_B":
        raise Aborta("abra o Mapa_B")
    if not sondar and unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():
        raise Aborta("feche o PIE")
    lib = unreal.LevelSequenceEditorBlueprintLibrary
    if lib.get_current_level_sequence():
        lib.close_level_sequence()
        if lib.get_current_level_sequence():
            raise Aborta("feche o Sequencer")
    if not sondar and sujos():
        raise Aborta("ha pacotes nao salvos antes de comecar: %s (feche sem salvar e rode de novo)" % sujos())
    lua()
    unico(unreal.SkyAtmosphere, "SkyAtmosphere")
    ppv()
    if len([a for a in atores() if a.get_class().get_name().startswith("BP_LuxLoopManager")]) != 1:
        raise Aborta("esperava 1 BP_LuxLoopManager no mapa")
    import setup_loop
    importlib.reload(setup_loop)
    if not (hasattr(setup_loop, "inserir_ramo_distorcao") and getattr(setup_loop, "DISTORCAO_HOOK", False)):
        raise Aborta("aplique o patch do setup_loop.py primeiro (DISTORCAO_HOOK / inserir_ramo_distorcao)")
    s = snapshot()
    if s["lua"]["intensity"] > 0.5 or not (-45 <= s["lua"]["pitch"] <= -10):
        raise Aborta("a lua nao parece a noite salva (intensidade %s, pitch %s)" % (s["lua"]["intensity"], s["lua"]["pitch"]))
    base = os.path.join(AQUI, "baseline_noite.json")
    if os.path.exists(base):
        b = json.load(open(base, encoding="utf-8"))
        if b.get("lua") != s["lua"] or b.get("ceu") != s["ceu"]:
            w("AVISO: lua/ceu diferentes do baseline_noite.json (a noite mudou desde a 1a instalacao?)")
    return s


# ------------------------------------------------------------------ grafo do manager (tambem usado pelo setup_loop.py)
def _links(n, pin, out=True):
    p = ok_pin(n.find_output_pin(pin) if out else n.find_input_pin(pin))
    return [q.get_owning_node() for q in p.list_connected_pins()] if p else []


def _cls(n):
    return n.get_class().get_name()


def _le_var(n, nome, prof=4):
    """True se o no (ou algo a montante ate 'prof' niveis) le a variavel 'nome'."""
    if prof < 0:
        return False
    if _cls(n) == "K2Node_VariableGet" and ok_pin(n.find_output_pin(nome)):
        return True
    for p in n.list_input_pins():
        for q in p.list_connected_pins():
            if _le_var(q.get_owning_node(), nome, prof - 1):
                return True
    return False


def achar_set_armado(ge):
    for n in ge.list_all_nodes():
        if _cls(n) != "K2Node_VariableSet" or not ok_pin(n.find_input_pin("bArmado")):
            continue
        alvo = _links(n, "then")
        if alvo and _cls(alvo[0]) in ("K2Node_IfThenElse", "K2Node_ExecutionSequence"):
            return n
    raise Aborta("nao achei o 'bArmado = false' do gatilho")


def achar_ramo_batida(ge, s_arm):
    alvo = _links(s_arm, "then")[0]
    if _cls(alvo) == "K2Node_ExecutionSequence":
        alvo = _links(alvo, "then_1")[0]
    cond = _links(alvo, "Condition", out=False)
    if _cls(alvo) != "K2Node_IfThenElse" or not cond or not (_le_var(cond[0], "LoopsBatida") and _le_var(cond[0], "LoopAtual")):
        raise Aborta("o alvo do 'bArmado = false' nao e o Branch da batida (LoopsBatida/LoopAtual)")
    return alvo


def ramo_instalado(ge, s_arm):
    alvo = _links(s_arm, "then")
    if not alvo or _cls(alvo[0]) != "K2Node_ExecutionSequence":
        return False
    for n in _links(alvo[0], "then_0"):
        if "GetActorOfClass" in str(n.get_node_title()).replace(" ", ""):
            return True
    return False


def nova_sequence(ge, x, y):
    nome = next((str(a) for a in ge.list_available_nodes([])
                 if str(a).split("|")[-1].lower() in ("sequence", "sequência", "sequencia")
                 and str(a).split("|")[-2].lower().replace(" ", "") in ("flowcontrol", "controledefluxo")), None)
    if not nome:
        raise Aborta("nao achei o no Sequence na lista de nos")
    n = ge.create_node_from_name(nome, unreal.Vector2D(x, y), [])
    if not n or _cls(n) != "K2Node_ExecutionSequence":
        raise Aborta("Sequence nao criado (%s)" % nome)
    return n


def inserir_ramo(ge, s_arm, x=950, y=2600):
    """Set bArmado.then -> Sequence; then_0 -> GetActorOfClass(BP_LuxCeu) -> IsValid -> LoopPedido = LoopAtual ->
    PedirDistorcao; then_1 -> o que vinha depois (Branch da batida), inalterado."""
    g = G(ge)
    depois = _links(s_arm, "then")
    if not depois:
        raise Aborta("'bArmado = false' sem saida")
    depois = depois[0]
    seq = g.pos(nova_sequence(ge, x, y), x, y)
    find = g.call(GS + "GetActorOfClass", x + 260, y - 260, ActorClass="/Script/Engine.BlueprintGeneratedClass'%s'" % CEU_C)
    tipo = str(find.find_output_pin("ReturnValue").get_pin_type_display_string())
    if "Lux Ceu" not in tipo and "LuxCeu" not in tipo:
        raise Aborta("GetActorOfClass nao tipou como BP_LuxCeu (%s)" % tipo)
    ok = g.call(KSL + "IsValid", x + 520, y - 120)
    g.link(find, "ReturnValue", ok, "Object")
    br = g.branch(x + 560, y - 260)
    g.link(ok, "ReturnValue", br, "Condition")
    s_lp = g.set("LoopPedido", x + 820, y - 360, cls=CEU_C)
    g.link(find, "ReturnValue", s_lp, "self")
    g.link(g.get("LoopAtual", x + 620, y - 460), "LoopAtual", s_lp, "LoopPedido")
    ped = g.call(CEU_C + ":PedirDistorcao", x + 1100, y - 360)
    g.link(find, "ReturnValue", ped, "self")
    ok_pin(s_arm.find_output_pin("then")).break_pin_links()
    g.link(s_arm, "then", seq, g.exec_in(seq))
    g.link(seq, "then_0", find, g.exec_in(find))
    g.link(find, "then", br, "execute")
    g.chain((br, "then"), s_lp, ped)
    g.link(seq, "then_1", depois, g.exec_in(depois))
    g.note("LUX_DISTORCAO (Tools/Sky/add_distorcao.py): pede a distorcao temporal ao BP_LuxCeu do nivel com o LoopAtual. "
           "Ele decide (desligada por padrao; so nos loops de LoopsDistorcao; uma vez por loop). then_1 = batida, inalterada",
           x - 40, y - 600, 1500, 800)
    return seq


# ------------------------------------------------------------------ BP_LuxCeu
EVENTOS = ("Registrar", "ResolverSeq", "TocarDoInicio", "Abreviar", "PedirDistorcao", "TocarPendente", "ForcarDistorcao",
           "EncerrarDistorcao", "LigarDistorcao", "DesligarDistorcao", "ResetarCeu")


def tipos():
    t = {k: BEL.get_basic_type_by_name(k) for k in ("bool", "int", "real", "string")}
    t["int[]"] = BEL.get_array_type(t["int"])
    t["string[]"] = BEL.get_array_type(t["string"])
    t["lsa"] = BEL.get_object_reference_type(unreal.LevelSequenceActor.static_class())
    return t


VARS = (  # nome, tipo, editavel, padrao
    ("bDistorcaoAtiva", "bool", True, DISTORCAO_PADRAO), ("LoopsDistorcao", "int[]", True, [3, 5]), ("LoopPedido", "int", True, 0),
    ("RegistroCeu", "string[]", True, []),
    ("LoopsTocados", "int[]", False, []), ("SequenciaDistorcao", "lsa", False, None), ("DuracaoS", "real", False, END / float(FPS)),
    ("TempoRetornoS", "real", False, TE), ("TInicio", "real", False, 0.0), ("LoopPendente", "int", False, 0),
    ("bOrigemPedido", "bool", False, False), ("UltimoEvento", "string", False, ""), ("VersaoGrafoCeu", "int", False, 0))


def ensure_ceu(prio):
    criado = not EAL.does_asset_exist(CEU)
    if not EAL.does_directory_exist(DIR):
        EAL.make_directory(DIR)
    bp = BEL.create_blueprint_asset_with_parent(CEU, unreal.Actor) if criado else EAL.load_asset(CEU)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    if criado:
        add_pp(bp, prio)
        w("BP_LuxCeu criado com PPDistorcao")
    t = tipos()
    existentes = [str(n) for n in BEL.list_member_variable_names(bp)]
    novas = []
    for nome, tp, ed, _ in VARS:
        if nome not in existentes:
            BEL.add_member_variable(bp, nome, t[tp])
            novas.append(nome)
        BEL.set_blueprint_variable_instance_editable(bp, nome, ed)
        BEL.set_blueprint_variable_category(bp, nome, unreal.Text("LUX Ceu" if ed else "LUX Ceu|Estado"))
    BEL.compile_blueprint(bp)
    cdo = unreal.get_default_object(bp.generated_class())
    for nome, _, _, pad in VARS:
        if nome in novas and pad is not None and pad != []:
            cdo.set_editor_property(nome, pad)
    if novas:
        w("  variaveis novas:", novas)
    if cdo.get_editor_property("VersaoGrafoCeu") != GRAFO_VERSAO:
        build_ceu_graph(bp)
        BEL.compile_blueprint(bp)
        unreal.get_default_object(bp.generated_class()).set_editor_property("VersaoGrafoCeu", GRAFO_VERSAO)
        w("  EventGraph do BP_LuxCeu montado (versao %d)" % GRAFO_VERSAO)
    else:
        w("  EventGraph do BP_LuxCeu ja na versao %d: mantido" % GRAFO_VERSAO)
    BEL.compile_blueprint(bp)
    return bp


def add_pp(bp, prio):
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    handles = sds.k2_gather_subobject_data_for_blueprint(bp)
    h, fail = sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=handles[0], new_class=unreal.PostProcessComponent,
                                                                 blueprint_context=bp))
    sds.rename_subobject(h, unreal.Text("PPDistorcao"))
    pp = lib.get_object_for_blueprint(lib.get_data(h), bp)
    configura_pp(pp, prio)


def configura_pp(pp, prio):
    pp.set_editor_property("enabled", True)
    pp.set_editor_property("unbound", True)
    pp.set_editor_property("blend_weight", 0.0)   # inerte com peso 0 (SceneView.cpp: Weight <= 0 -> return)
    pp.set_editor_property("priority", prio)
    s = unreal.PostProcessSettings()
    for k, v in (("auto_exposure_speed_up", 0.02), ("auto_exposure_speed_down", 0.02),
                 ("lumen_scene_lighting_update_speed", 4.0), ("lumen_final_gather_lighting_update_speed", 4.0)):
        s.set_editor_property("override_" + k, True)
        s.set_editor_property(k, v)
    pp.set_editor_property("settings", s)


def pp_do_template(bp):
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        o = lib.get_object_for_blueprint(lib.get_data(h), bp)
        if isinstance(o, unreal.PostProcessComponent):
            return o
    return None


def build_ceu_graph(bp):
    ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
    ge.remove_nodes(list(ge.list_all_nodes()))  # o grafo inteiro e deste script (so Custom Events)
    for c in list(ge.list_comment_nodes()):
        ge.remove_comment_node(c)
    g = G(ge)
    ev = {}
    for i, nome in enumerate(EVENTOS):
        ev[nome] = g.pos(ge.add_custom_event_node(nome), 0, i * 900)
    BEL.compile_blueprint(bp)  # os eventos viram funcoes chamaveis
    me = CEU_C + ":"

    def call_ev(nome, x, y):
        return g.call(me + nome, x, y)

    def log(x, y, texto):
        s = g.set("UltimoEvento", x, y, texto)
        r = call_ev("Registrar", x + 240, y)
        g.chain(s, r)
        return s, r

    def player(x, y):
        """pino de saida com o LevelSequencePlayer da SequenciaDistorcao (no puro)"""
        gp = g.call(LSA + "GetSequencePlayer", x, y)
        g.link(g.get("SequenciaDistorcao", x - 200, y), "SequenciaDistorcao", gp, "self")
        return gp

    def valido(obj_node, obj_pin, x, y):
        ok = g.call(KSL + "IsValid", x, y + 120)
        g.link(obj_node, obj_pin, ok, "Object")
        br = g.branch(x, y)
        g.link(ok, "ReturnValue", br, "Condition")
        return br

    def branch_var(var, x, y):
        br = g.branch(x, y)
        g.link(g.get(var, x - 200, y + 120), var, br, "Condition")
        return br

    # Registrar: UltimoEvento -> linha com tempos -> RegistroCeu + log
    y = 0
    partes = []
    utc = g.call(KML + "UtcNow", 200, y + 200)
    asdt = g.call(TXT + "AsDateTime_DateTime", 400, y + 200)
    g.link(utc, "ReturnValue", asdt, "In")
    t2s = g.call(TXT + "Conv_TextToString", 640, y + 200)
    g.link(asdt, "ReturnValue", t2s, "InText")
    partes.append((None, "UTC="))
    partes.append((t2s, "ReturnValue"))
    for rotulo, fn, pin, x in (("|jogo=", GS + "GetTimeSeconds", "ReturnValue", 200), ("|real=", GS + "GetRealTimeSeconds", "ReturnValue", 200)):
        n = g.call(fn, x, y + 300 + len(partes) * 40)
        c = g.call(STR + "Conv_DoubleToString", x + 220, y + 300 + len(partes) * 40)
        g.link(n, pin, c, "InDouble")
        partes += [(None, rotulo), (c, "ReturnValue")]
    ci = g.call(STR + "Conv_IntToString", 420, y + 500)
    g.link(g.get("LoopPedido", 200, y + 500), "LoopPedido", ci, "InInt")
    partes += [(None, "|loop="), (ci, "ReturnValue"), (None, "|ev=")]
    ue = g.get("UltimoEvento", 200, y + 580)
    partes.append((ue, "UltimoEvento"))
    cb = g.call(STR + "Conv_BoolToString", 420, y + 660)
    g.link(g.get("bDistorcaoAtiva", 200, y + 660), "bDistorcaoAtiva", cb, "InBool")
    partes += [(None, "|on="), (cb, "ReturnValue"), (None, "|dur=")]
    cd = g.call(STR + "Conv_DoubleToString", 420, y + 740)
    g.link(g.get("DuracaoS", 200, y + 740), "DuracaoS", cd, "InDouble")
    partes.append((cd, "ReturnValue"))
    acc_node, acc_pin = None, None
    x = 900
    for node, pin in partes:
        a = g.call(STR + "Concat_StrStr", x, y + 300)
        x += 40
        if acc_node is None:
            g.val(a, "A", "")
        else:
            g.link(acc_node, acc_pin, a, "A")
        if node is None:
            g.val(a, "B", pin)
        else:
            g.link(node, pin, a, "B")
        acc_node, acc_pin = a, "ReturnValue"
    add = g.call(ARR + "Array_Add", 1700, y)
    g.link(g.get("RegistroCeu", 1500, y + 120), "RegistroCeu", add, "TargetArray")
    g.link(acc_node, acc_pin, add, "NewItem")
    pr = g.call(KSL + "PrintString", 2000, y, bPrintToScreen="false", bPrintToLog="true")
    g.link(acc_node, acc_pin, pr, "InString")
    g.chain(ev["Registrar"], add, pr)

    # ResolverSeq
    y = 900
    br = valido(g.get("SequenciaDistorcao", 200, y + 200), "SequenciaDistorcao", 300, y)
    ga = g.call(GS + "GetAllActorsOfClassWithTag", 600, y + 100, ActorClass="/Script/CoreUObject.Class'/Script/LevelSequence.LevelSequenceActor'",
                Tag=TAG_SEQ)
    ln = g.call(ARR + "Array_Length", 800, y + 300)
    g.link(ga, "OutActors", ln, "TargetArray")
    gt = g.call(KML + "Greater_IntInt", 1000, y + 300)
    g.link(ln, "ReturnValue", gt, "A")
    g.val(gt, "B", 0)
    br2 = g.branch(1100, y + 100)
    g.link(gt, "ReturnValue", br2, "Condition")
    get0 = g.call(ARR + "Array_Get", 1200, y + 300)
    g.link(ga, "OutActors", get0, "TargetArray")
    g.val(get0, "Index", 0)
    s_seq = g.set("SequenciaDistorcao", 1400, y + 100)
    g.link(get0, "Item", s_seq, "SequenciaDistorcao")
    g.chain(ev["ResolverSeq"], br)
    g.chain((br, "else"), ga, br2)
    g.chain((br2, "then"), s_seq)

    # TocarDoInicio
    y = 1800
    r0 = call_ev("ResolverSeq", 250, y)
    b_seq = valido(g.get("SequenciaDistorcao", 400, y + 200), "SequenciaDistorcao", 500, y)
    l_ss = log(700, y + 300, "ERRO_SEM_SEQ")
    gp = player(800, y + 200)
    b_p = valido(gp, "ReturnValue", 1000, y)
    l_sp = log(1200, y + 300, "ERRO_SEM_PLAYER")
    isp = g.call(PLAYER + "IsPlaying", 1200, y + 200)
    g.link(gp, "ReturnValue", isp, "self")
    b_play = g.branch(1400, y)
    g.link(isp, "ReturnValue", b_play, "Condition")
    # tocando
    b_orig = branch_var("bOrigemPedido", 1650, y - 300)
    s_pend = g.set("LoopPendente", 1900, y - 400)
    g.link(g.get("LoopPedido", 1700, y - 500), "LoopPedido", s_pend, "LoopPendente")
    now1 = g.call(GS + "GetTimeSeconds", 1900, y - 200)
    dt = g.call(KML + "Subtract_DoubleDouble", 2100, y - 200)
    g.link(now1, "ReturnValue", dt, "A")
    g.link(g.get("TInicio", 1900, y - 120), "TInicio", dt, "B")
    soma = g.call(KML + "Add_DoubleDouble", 2100, y - 80)
    g.link(g.get("DuracaoS", 1900, y - 40), "DuracaoS", soma, "A")
    g.val(soma, "B", 0.5)
    resto = g.call(KML + "Subtract_DoubleDouble", 2300, y - 120)
    g.link(soma, "ReturnValue", resto, "A")
    g.link(dt, "ReturnValue", resto, "B")
    mx = g.call(KML + "FMax", 2500, y - 120)
    g.link(resto, "ReturnValue", mx, "A")
    g.val(mx, "B", 0.2)
    tm = g.call(KSL + "K2_SetTimer", 2200, y - 400, FunctionName="TocarPendente", bLooping="false")
    g.link(mx, "ReturnValue", tm, "Time")
    l_adi = log(2500, y - 400, "ADIADO")
    l_ign = log(1900, y - 700, "IGN_TOCANDO")
    # livre: toca do inicio
    au = g.call(ARR + "Array_AddUnique", 1700, y + 300)
    g.link(g.get("LoopsTocados", 1500, y + 400), "LoopsTocados", au, "TargetArray")
    g.link(g.get("LoopPedido", 1500, y + 480), "LoopPedido", au, "NewItem")
    spp = g.call(PLAYER + "SetPlaybackPosition", 2000, y + 300, PlaybackParams="(Time=0.000000,PositionType=Time,UpdateMethod=Jump)")
    g.link(gp, "ReturnValue", spp, "self")
    pl = g.call(PLAYER + "Play", 2250, y + 300)
    g.link(gp, "ReturnValue", pl, "self")
    s_ti = g.set("TInicio", 2500, y + 300)
    g.link(g.call(GS + "GetTimeSeconds", 2300, y + 450), "ReturnValue", s_ti, "TInicio")
    l_ini = log(2750, y + 300, "INICIO")
    g.chain(ev["TocarDoInicio"], r0, b_seq)
    g.chain((b_seq, "else"), l_ss[0])
    g.chain((b_seq, "then"), b_p)
    g.chain((b_p, "else"), l_sp[0])
    g.chain((b_p, "then"), b_play)
    g.chain((b_play, "then"), b_orig)
    g.chain((b_orig, "then"), s_pend, tm, l_adi[0])
    g.chain((b_orig, "else"), l_ign[0])
    g.chain((b_play, "else"), au, spp, pl, s_ti, l_ini[0])

    # Abreviar: pula para o frame E (lua volta com exposicao ainda congelada)
    y = 2700
    r1 = call_ev("ResolverSeq", 250, y)
    a_seq = valido(g.get("SequenciaDistorcao", 400, y + 200), "SequenciaDistorcao", 500, y)
    gp2 = player(800, y + 200)
    a_p = valido(gp2, "ReturnValue", 1000, y)
    isp2 = g.call(PLAYER + "IsPlaying", 1200, y + 200)
    g.link(gp2, "ReturnValue", isp2, "self")
    a_play = g.branch(1400, y)
    g.link(isp2, "ReturnValue", a_play, "Condition")
    now2 = g.call(GS + "GetTimeSeconds", 1400, y + 300)
    dt2 = g.call(KML + "Subtract_DoubleDouble", 1600, y + 300)
    g.link(now2, "ReturnValue", dt2, "A")
    g.link(g.get("TInicio", 1400, y + 380), "TInicio", dt2, "B")
    lt = g.call(KML + "Less_DoubleDouble", 1800, y + 300)
    g.link(dt2, "ReturnValue", lt, "A")
    g.link(g.get("TempoRetornoS", 1600, y + 420), "TempoRetornoS", lt, "B")
    a_cedo = g.branch(1900, y)
    g.link(lt, "ReturnValue", a_cedo, "Condition")
    spp2 = g.call(PLAYER + "SetPlaybackPosition", 2150, y, PlaybackParams="(Time=%.6f,PositionType=Time,UpdateMethod=Jump)" % TE)
    g.link(gp2, "ReturnValue", spp2, "self")
    now3 = g.call(GS + "GetTimeSeconds", 2300, y + 250)
    sub3 = g.call(KML + "Subtract_DoubleDouble", 2500, y + 250)
    g.link(now3, "ReturnValue", sub3, "A")
    g.link(g.get("TempoRetornoS", 2300, y + 330), "TempoRetornoS", sub3, "B")
    s_ti2 = g.set("TInicio", 2700, y)
    g.link(sub3, "ReturnValue", s_ti2, "TInicio")
    g.chain(ev["Abreviar"], r1, a_seq)
    g.chain((a_seq, "then"), a_p)
    g.chain((a_p, "then"), a_play)
    g.chain((a_play, "then"), a_cedo)
    g.chain((a_cedo, "then"), spp2, s_ti2)

    # PedirDistorcao
    y = 3600
    s_or = g.set("bOrigemPedido", 250, y, "true")
    p_on = branch_var("bDistorcaoAtiva", 500, y)
    l_off = log(700, y + 300, "IGN_DESLIGADA")
    c1 = g.call(ARR + "Array_Contains", 700, y + 150)
    g.link(g.get("LoopsDistorcao", 500, y + 200), "LoopsDistorcao", c1, "TargetArray")
    g.link(g.get("LoopPedido", 500, y + 280), "LoopPedido", c1, "ItemToFind")
    p_lista = g.branch(900, y)
    g.link(c1, "ReturnValue", p_lista, "Condition")
    l_fora = log(1100, y + 300, "IGN_FORA_LISTA")
    c2 = g.call(ARR + "Array_Contains", 1100, y + 150)
    g.link(g.get("LoopsTocados", 900, y + 200), "LoopsTocados", c2, "TargetArray")
    g.link(g.get("LoopPedido", 900, y + 280), "LoopPedido", c2, "ItemToFind")
    p_ja = g.branch(1300, y)
    g.link(c2, "ReturnValue", p_ja, "Condition")
    l_ja = log(1500, y - 200, "IGN_JA_TOCADO")
    t1 = call_ev("TocarDoInicio", 1550, y + 100)
    g.chain(ev["PedirDistorcao"], s_or, p_on)
    g.chain((p_on, "else"), l_off[0])
    g.chain((p_on, "then"), p_lista)
    g.chain((p_lista, "else"), l_fora[0])
    g.chain((p_lista, "then"), p_ja)
    g.chain((p_ja, "then"), l_ja[0])
    g.chain((p_ja, "else"), t1)

    # TocarPendente
    y = 4500
    q_on = branch_var("bDistorcaoAtiva", 300, y)
    gt2 = g.call(KML + "Greater_IntInt", 500, y + 200)
    g.link(g.get("LoopPendente", 300, y + 250), "LoopPendente", gt2, "A")
    g.val(gt2, "B", 0)
    q_pend = g.branch(600, y)
    g.link(gt2, "ReturnValue", q_pend, "Condition")
    s_lp = g.set("LoopPedido", 850, y)
    g.link(g.get("LoopPendente", 650, y + 150), "LoopPendente", s_lp, "LoopPedido")
    z1 = g.set("LoopPendente", 1100, y, 0)
    s_or2 = g.set("bOrigemPedido", 1350, y, "true")
    t2 = call_ev("TocarDoInicio", 1600, y)
    z2 = g.set("LoopPendente", 900, y + 350, 0)
    g.chain(ev["TocarPendente"], q_on)
    g.chain((q_on, "then"), q_pend)
    g.chain((q_pend, "then"), s_lp, z1, s_or2, t2)
    g.chain((q_on, "else"), z2)
    g.chain((q_pend, "else"), z2)

    # ForcarDistorcao
    y = 5400
    l_f = log(250, y, "FORCADO")
    s_or3 = g.set("bOrigemPedido", 750, y, "false")
    t3 = call_ev("TocarDoInicio", 1000, y)
    g.chain(ev["ForcarDistorcao"], l_f[0])
    g.chain(l_f[1], s_or3, t3)

    # EncerrarDistorcao
    y = 6300
    ab1 = call_ev("Abreviar", 250, y)
    l_e = log(500, y, "ENCERRADO")
    g.chain(ev["EncerrarDistorcao"], ab1, l_e[0])

    # LigarDistorcao
    y = 7200
    s_on = g.set("bDistorcaoAtiva", 250, y, "true")
    l_l = log(500, y, "LIGADA")
    g.chain(ev["LigarDistorcao"], s_on, l_l[0])

    # DesligarDistorcao
    y = 8100
    s_off = g.set("bDistorcaoAtiva", 250, y, "false")
    ct = g.call(KSL + "K2_ClearTimer", 500, y, FunctionName="TocarPendente")
    z3 = g.set("LoopPendente", 750, y, 0)
    ab2 = call_ev("Abreviar", 1000, y)
    l_d = log(1250, y, "DESLIGADA")
    g.chain(ev["DesligarDistorcao"], s_off, ct, z3, ab2, l_d[0])

    # ResetarCeu
    y = 9000
    ct2 = g.call(KSL + "K2_ClearTimer", 250, y, FunctionName="TocarPendente")
    z4 = g.set("LoopPendente", 500, y, 0)
    ab3 = call_ev("Abreviar", 750, y)
    clr = g.call(ARR + "Array_Clear", 1000, y)
    g.link(g.get("LoopsTocados", 800, y + 150), "LoopsTocados", clr, "TargetArray")
    l_r = log(1250, y, "RESET")
    g.chain(ev["ResetarCeu"], ct2, z4, ab3, clr, l_r[0])

    g.note("LUX_CEU (Tools/Sky/add_distorcao.py, versao %d). Distorcao temporal: desligada por padrao (bDistorcaoAtiva). "
           "Sem BeginPlay, Tick ou nos latentes. Console: ke * LigarDistorcao / ForcarDistorcao / EncerrarDistorcao / "
           "DesligarDistorcao / ResetarCeu" % GRAFO_VERSAO, -60, -400, 1800, 300)


def erros_bp(bp, graficos):
    out = []
    for gname in graficos:
        ge = BGE.get_graph_editor_by_name(bp, gname)
        for kind, lst in (("ERRO", ge.list_nodes_with_errors()), ("aviso", ge.list_nodes_with_warnings())):
            out += ["%s em %s: %s" % (kind, gname, str(n.get_node_title()).replace("\n", " ")) for n in lst]
    return out


# ------------------------------------------------------------------ atores
def ensure_atores(bp, seq_asset):
    mgr = [a for a in atores() if a.get_class().get_name().startswith("BP_LuxLoopManager")][0]
    base = mgr.get_actor_location()
    ceus = [a for a in atores() if a.get_class().get_name().startswith("BP_LuxCeu")]
    if len(ceus) > 1:
        raise Aborta("mais de um BP_LuxCeu no mapa")
    if not ceus:
        c = eas().spawn_actor_from_class(bp.generated_class(), base + unreal.Vector(0, -150, 150), unreal.Rotator())
        w("LUX_Ceu colocado")
    else:
        c = ceus[0]
    c.set_actor_label("LUX_Ceu")
    c.set_folder_path("LUX/Ceu")
    c.set_editor_property("tags", [unreal.Name(TAG_CEU)])
    seqs = por_tag(TAG_SEQ)
    if len(seqs) > 1:
        raise Aborta("mais de um ator com a tag %s" % TAG_SEQ)
    if not seqs:
        s = eas().spawn_actor_from_class(unreal.LevelSequenceActor, base + unreal.Vector(0, -150, 250), unreal.Rotator())
        w("LUX_Distorcao_Seq colocado")
    else:
        s = seqs[0]
    s.set_actor_label("LUX_Distorcao_Seq")
    s.set_folder_path("LUX/Ceu")
    s.set_editor_property("tags", [unreal.Name(TAG_SEQ)])
    try:
        s.set_editor_property("level_sequence_asset", seq_asset)
    except Exception:
        s.set_sequence(seq_asset)
    ps = s.get_editor_property("playback_settings")
    for k, v in (("auto_play", False), ("pause_at_end", False), ("play_rate", 1.0), ("disable_camera_cuts", True),
                 ("hide_player", False), ("hide_hud", False), ("disable_movement_input", False), ("disable_look_at_input", False),
                 ("finish_completion_state_override", unreal.MovieSceneCompletionModeOverride.FORCE_KEEP_STATE)):
        ps.set_editor_property(k, v)
    lc = ps.get_editor_property("loop_count")
    lc.set_editor_property("value", 0)
    ps.set_editor_property("loop_count", lc)
    s.set_editor_property("playback_settings", ps)
    return c, s


# ------------------------------------------------------------------ Level Sequence
L, C, A = (unreal.MovieSceneKeyInterpolation.LINEAR, unreal.MovieSceneKeyInterpolation.CONSTANT,
           unreal.MovieSceneKeyInterpolation.AUTO)


def curvas(snap):
    M = snap["lua"]["intensity"]
    p0, y0 = snap["lua"]["pitch"], snap["lua"]["yaw"]
    cc = snap["lua"]["color"]
    c0 = linear(unreal.Color(r=int(cc[0]), g=int(cc[1]), b=int(cc[2]), a=int(cc[3])))
    c0 = (c0.r, c0.g, c0.b)
    k0 = snap["ceu"]["sky_luminance_factor"]
    D = M * 2 ** DIA_EV
    inten = [(0, M, L), (15, M, L), (39, 0.0, C)]
    pitch = [(0, p0, C)]
    yaw = [(0, y0, C)]
    cor = [(0, c0, C)]
    ceu = [(0, k0[:3], C)]
    for s in S:
        inten += [(s, 0.0, L), (s + 27, D, L), (s + 39, D, L), (s + 66, 0.0, C)]
        pitch += [(s, 2.0, A), (s + 33, PICO_PITCH, A), (s + 66, 2.0, C)]
        yaw += [(s, y0 - ARCO_YAW, L), (s + 66, y0 + ARCO_YAW, C)]
        cor += [(s, DAWN, L), (s + 27, NOON, L), (s + 39, NOON, L), (s + 66, DAWN, C)]
        ceu += [(s, k0[:3], L), (s + 27, [v * CEU_GANHO for v in k0[:3]], L), (s + 39, [v * CEU_GANHO for v in k0[:3]], L), (s + 66, k0[:3], C)]
    inten += [(E, 0.0, L), (E + 24, M, C)]
    pitch += [(E, p0, C)]
    yaw += [(E, y0, C)]
    cor += [(E, c0, C)]
    ceu += [(E, k0[:3], C)]
    peso = [(0, 0.0, L), (15, 1.0, C), (E + 45, 1.0, L), (F, 0.0, C)]
    return {"M": M, "D": D, "c0": c0, "k0": k0, "inten": inten, "pitch": pitch, "yaw": yaw, "cor": cor, "ceu": ceu, "peso": peso}


def lint(cv, snap):
    erros = []
    if T < 2.2 or not (2 <= N <= 6):
        erros.append("T/N fora do limite")
    ev_pico = DIA_EV + math.log2(math.sin(math.radians(abs(PICO_PITCH))) / math.sin(math.radians(abs(snap["lua"]["pitch"]))))
    if ev_pico > 4:
        erros.append("pico %.2f EV > 4" % ev_pico)
    ks = cv["inten"]
    for (f1, v1, i1), (f2, v2, _) in zip(ks, ks[1:]):
        if i1 == C and abs(v1 - v2) > 1e-9:
            erros.append("Intensity: chave C em %d seguida de valor diferente em %d" % (f1, f2))
        if i1 != C and abs(v1 - v2) > 1e-9 and f2 - f1 < 24:
            erros.append("Intensity: rampa curta %d->%d" % (f1, f2))
    inicios = [f1 for (f1, v1, i1), (f2, v2, _) in zip(ks, ks[1:]) if i1 != C and abs(v1 - v2) > 1e-9]
    for a, b in zip(inicios, inicios[1:]):
        if b - a < 24:
            erros.append("inicios de rampa muito proximos: %d e %d" % (a, b))

    def valor(chaves, f):
        v = chaves[0][1]
        for fk, vk, ik in chaves:
            if fk <= f:
                v = vk
        return v

    for nome in ("pitch", "yaw", "cor"):
        chaves = cv[nome]
        for (f1, v1, i1), (f2, v2, _) in zip(chaves, chaves[1:]):
            if i1 == C and v1 != v2 and valor(ks, f2) > 1e-9:
                erros.append("%s: salto em %d com Intensity > 0" % (nome, f2))
    for nome, col in (("DAWN", DAWN), ("NOON", NOON), ("C0", cv["c0"])):
        if col[0] / sum(col) > 0.5:
            erros.append("%s vermelho demais" % nome)
    if abs(valor(ks, 0) - cv["M"]) > 1e-9 or abs(valor(ks, F) - cv["M"]) > 1e-9:
        erros.append("frame 0 ou F diferente da noite salva")
    return erros, ev_pico


def canais(sec):
    out = {}
    for ch in sec.get_all_channels():
        try:
            nome = str(ch.get_editor_property("channel_name"))
        except Exception:
            nome = str(ch.get_name())
        out[nome] = ch
    return out


def chave(ch, f, v, interp):
    ch.add_key(unreal.FrameNumber(int(f)), float(v), 0.0, unreal.MovieSceneTimeUnit.DISPLAY_RATE, interp)


def secao(track):
    sec = track.add_section()
    sec.set_range(0, END)
    sec.set_completion_mode(unreal.MovieSceneCompletionMode.KEEP_STATE)
    return sec


def acha(chs, *sufixos):
    for suf in sufixos:
        for nome, ch in chs.items():
            if nome == suf or nome.endswith("." + suf) or nome.endswith(suf):
                return ch
    raise Aborta("canal %s nao encontrado em %s" % (sufixos, list(chs)))


def monta_ls(snap, ceu_ator):
    if EAL.does_asset_exist(LS):
        seq = EAL.load_asset(LS)
    else:
        seq = unreal.AssetToolsHelpers.get_asset_tools().create_asset("LS_LuxDistorcao", DIR, unreal.LevelSequence,
                                                                        unreal.LevelSequenceFactoryNew())
        w("LS_LuxDistorcao criado")
    seq.set_display_rate(unreal.FrameRate(FPS, 1))
    seq.set_playback_start(0)
    seq.set_playback_end(END)
    for _ in range(10):  # add_possessable sempre cria GUID novo: tira tudo (filhos primeiro) e recria
        bs = list(seq.get_bindings())
        if not bs:
            break
        for b in [b for b in bs if b.get_parent().is_valid()] + [b for b in bs if not b.get_parent().is_valid()]:
            try:
                b.remove()
            except Exception:
                pass
    if list(seq.get_bindings()):
        raise Aborta("nao consegui limpar os bindings antigos do LS")
    cv = curvas(snap)
    erros, ev_pico = lint(cv, snap)
    if erros:
        raise Aborta("lint: " + "; ".join(erros))
    w("lint ok: pico %.2f EV, D=%.4f lux, %d chaves de Intensity" % (ev_pico, cv["D"], len(cv["inten"])))
    L_ = lua()
    lc = L_.get_components_by_class(unreal.DirectionalLightComponent)[0]
    sky = unico(unreal.SkyAtmosphere, "SkyAtmosphere")
    skc = sky.get_components_by_class(unreal.SkyAtmosphereComponent)[0]
    pp = ceu_ator.get_components_by_class(unreal.PostProcessComponent)[0]
    b1 = seq.add_possessable(L_)
    b2 = seq.add_possessable(lc)
    b3 = seq.add_possessable(sky)
    b4 = seq.add_possessable(skc)
    b5 = seq.add_possessable(ceu_ator)
    b6 = seq.add_possessable(pp)
    for filho, pai in ((b2, b1), (b4, b3), (b6, b5)):
        filho.set_parent(pai)
    # 1: transform da lua
    tr = b1.add_track(unreal.MovieScene3DTransformTrack)
    chs = canais(secao(tr))
    loc = snap["lua"]["loc"]
    sc = L_.get_actor_scale3d()
    for nome, v in (("Location.X", loc[0]), ("Location.Y", loc[1]), ("Location.Z", loc[2]), ("Rotation.X", snap["lua"]["roll"]),
                    ("Scale.X", sc.x), ("Scale.Y", sc.y), ("Scale.Z", sc.z)):
        ch = acha(chs, nome)
        ch.set_default(float(v))
        chave(ch, 0, v, C)
    for nome, ks in (("Rotation.Y", cv["pitch"]), ("Rotation.Z", cv["yaw"])):
        ch = acha(chs, nome)
        ch.set_default(float(ks[0][1]))
        for f, v, i in ks:
            chave(ch, f, v, i)
    # 2: intensidade e cor
    tI = b2.add_track(unreal.MovieSceneFloatTrack)
    tI.set_property_name_and_path("Intensity", "Intensity")
    chI = list(canais(secao(tI)).values())[0]
    chI.set_default(float(cv["M"]))
    for f, v, i in cv["inten"]:
        chave(chI, f, v, i)
    tC = b2.add_track(unreal.MovieSceneColorTrack)
    tC.set_property_name_and_path("LightColor", "LightColor")
    chC = canais(secao(tC))
    for j, comp in enumerate(("R", "G", "B")):
        ch = acha(chC, comp)
        ch.set_default(float(cv["c0"][j]))
        for f, v, i in cv["cor"]:
            chave(ch, f, v[j], i)
    chave(acha(chC, "A"), 0, 1.0, C)
    # 4: ceu
    tK = b4.add_track(unreal.MovieSceneColorTrack)
    tK.set_property_name_and_path("SkyLuminanceFactor", "SkyLuminanceFactor")
    chK = canais(secao(tK))
    for j, comp in enumerate(("R", "G", "B")):
        ch = acha(chK, comp)
        ch.set_default(float(cv["k0"][j]))
        for f, v, i in cv["ceu"]:
            chave(ch, f, v[j], i)
    chave(acha(chK, "A"), 0, cv["k0"][3], C)
    # 6: peso do PPDistorcao
    tW = b6.add_track(unreal.MovieSceneFloatTrack)
    tW.set_property_name_and_path("BlendWeight", "BlendWeight")
    chW = list(canais(secao(tW)).values())[0]
    chW.set_default(0.0)
    for f, v, i in cv["peso"]:
        chave(chW, f, v, i)
    return seq, cv


# ------------------------------------------------------------------ verificar
def ler_ls(seq):
    info = {"fps": str(seq.get_display_rate()), "start": seq.get_playback_start(), "end": seq.get_playback_end(), "bindings": []}
    for b in seq.get_bindings():
        pai = b.get_parent()
        info["bindings"].append({"nome": str(b.get_display_name()), "classe": str(b.get_possessed_object_class().get_name()) if b.get_possessed_object_class() else None,
                                 "pai": str(pai.get_display_name()) if pai.is_valid() else None,
                                 "tracks": {str(t.get_display_name()): [
                                     {"range": (s.get_start_frame(), s.get_end_frame()), "completion": str(s.get_completion_mode()),
                                      "chaves": {n: len(c.get_keys()) for n, c in canais(s).items() if c.get_keys()}}
                                     for s in t.get_sections()] for t in b.get_tracks()}})
    return info


def verificar(snap=None):
    falhas = []
    bp = EAL.load_asset(CEU) if EAL.does_asset_exist(CEU) else None
    seq = EAL.load_asset(LS) if EAL.does_asset_exist(LS) else None
    if not bp or not seq:
        return ["assets ausentes"]
    e = erros_bp(bp, ("EventGraph",))
    if e:
        falhas.append("BP_LuxCeu: %s" % e)
    cdo = unreal.get_default_object(bp.generated_class())
    if cdo.get_editor_property("bDistorcaoAtiva") != DISTORCAO_PADRAO or list(cdo.get_editor_property("LoopsDistorcao")) != [3, 5]:
        falhas.append("padroes do BP_LuxCeu diferentes de (%s, [3, 5])" % DISTORCAO_PADRAO)
    pp = pp_do_template(bp)
    if not pp or pp.get_editor_property("blend_weight") != 0.0 or not pp.get_editor_property("unbound"):
        falhas.append("PPDistorcao fora do esperado")
    ceus = [a for a in atores() if a.get_class().get_name().startswith("BP_LuxCeu")]
    if len(ceus) != 1:
        falhas.append("esperava 1 BP_LuxCeu no mapa (%d)" % len(ceus))
    elif "DEFAULT" not in str(ceus[0].is_editor_property_overridden("bDistorcaoAtiva")) or ceus[0].get_editor_property("bDistorcaoAtiva") != DISTORCAO_PADRAO:
        falhas.append("a instancia LUX_Ceu tem override de bDistorcaoAtiva (deve seguir o Class Default)")
    info = ler_ls(seq)
    if len(info["bindings"]) != 6:
        falhas.append("LS com %d bindings" % len(info["bindings"]))
    if info["end"] != END or info["start"] != 0:
        falhas.append("playback %s..%s" % (info["start"], info["end"]))
    for b in info["bindings"]:
        for t, secs in b["tracks"].items():
            for s in secs:
                if "KEEP_STATE" not in s["completion"] or tuple(s["range"]) != (0, END):
                    falhas.append("secao %s/%s: %s %s" % (b["nome"], t, s["completion"], s["range"]))
    seqs = por_tag(TAG_SEQ)
    if len(seqs) != 1:
        falhas.append("esperava 1 ator %s" % TAG_SEQ)
    else:
        ps = seqs[0].get_editor_property("playback_settings")
        if ps.get_editor_property("auto_play") or str(ps.get_editor_property("finish_completion_state_override")).find("KEEP") < 0:
            falhas.append("playback_settings do LUX_Distorcao_Seq")
    mbp = EAL.load_asset(MGR)
    ge = BGE.get_graph_editor_by_name(mbp, "EventGraph")
    try:
        s_arm = achar_set_armado(ge)
        if not ramo_instalado(ge, s_arm):
            falhas.append("ramo LUX_DISTORCAO ausente no gatilho")
        achar_ramo_batida(ge, s_arm)
    except Aborta as ex:
        falhas.append(str(ex))
    import setup_loop
    importlib.reload(setup_loop)
    if not getattr(setup_loop, "DISTORCAO_HOOK", False):
        falhas.append("setup_loop sem DISTORCAO_HOOK")
    for porta, m in snapshot()["portas"].items():
        if not m:
            falhas.append("%s.Manager vazio" % porta)
    if sujos():
        falhas.append("pacotes sujos: %s" % sujos())
    w("LS lido:", json.dumps(info, ensure_ascii=False, default=str))
    return falhas


# ------------------------------------------------------------------ modos
def instalar():
    antes = preflight()
    grava("snap_antes.json", antes)
    prio = ppv().get_editor_property("priority") + 10
    mbp = EAL.load_asset(MGR)
    base_erros = erros_bp(mbp, ("EventGraph",))
    bp = ensure_ceu(prio)
    e = erros_bp(bp, ("EventGraph",))
    if e:
        raise Aborta("BP_LuxCeu nao compilou limpo: %s" % e)
    ceu_ator, seq_ator = ensure_atores(bp, None)
    seq, cv = monta_ls(antes, ceu_ator)
    ensure_atores(bp, seq)
    ge = BGE.get_graph_editor_by_name(mbp, "EventGraph")
    s_arm = achar_set_armado(ge)
    ramo = achar_ramo_batida(ge, s_arm)
    base = os.path.join(AQUI, "baseline_ramo.json")
    if not os.path.exists(base):
        json.dump({"branch_batida": ramo.get_name()}, open(base, "w", encoding="utf-8"))
    if ramo_instalado(ge, s_arm):
        w("manager: ramo LUX_DISTORCAO ja instalado")
    else:
        unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(mbp)
        inserir_ramo(ge, s_arm)
        BEL.compile_blueprint(mbp)
        w("manager: ramo LUX_DISTORCAO inserido")
    novos = [x for x in erros_bp(mbp, ("EventGraph",)) if x not in base_erros]
    if novos:
        raise Aborta("manager com erros/avisos novos: %s" % novos)
    depois = snapshot()
    grava("snap_depois.json", depois)
    for k in ("lua", "ceu", "ppv", "portas"):
        if antes[k] != depois[k]:
            raise Aborta("retrato mudou em %s: antes %s depois %s" % (k, antes[k], depois[k]))
    for k, v in antes["manager"].items():
        if depois["manager"].get(k) != v:
            raise Aborta("manager.%s mudou: %s -> %s" % (k, v, depois["manager"].get(k)))
    esperado = {CEU, LS, MGR, "/Game/Masion/Mapa_B"}
    extra = set(depois["sujos"]) - esperado
    if extra:
        raise Aborta("pacotes sujos inesperados: %s" % sorted(extra))
    w("retratos antes = depois; sujos:", depois["sujos"])
    for a in (bp, seq, mbp):
        w("salvo", a.get_path_name(), EAL.save_loaded_asset(a, False))
    U = unreal.EditorLoadingAndSavingUtils
    mapa = [p for p in U.get_dirty_map_packages() if p.get_name() == "/Game/Masion/Mapa_B"]
    if mapa:
        w("salvo Mapa_B", U.save_packages(mapa, True))
    if sujos():
        raise Aborta("ainda ha pacotes sujos depois de salvar: %s" % sujos())
    bn = os.path.join(AQUI, "baseline_noite.json")
    if not os.path.exists(bn):
        json.dump({"lua": depois["lua"], "ceu": depois["ceu"]}, open(bn, "w", encoding="utf-8"), indent=2)
    f = verificar()
    w("verificar:", f or "OK")


def sondar():
    s = preflight(sondar=True)
    grava("snap_sondar.json", s)
    w("retrato:", json.dumps(s, ensure_ascii=False, default=str))
    w("BP_LuxCeu existe:", EAL.does_asset_exist(CEU), "| LS existe:", EAL.does_asset_exist(LS),
      "| atores:", [a.get_actor_label() for a in por_tag(TAG_CEU) + por_tag(TAG_SEQ)])
    mbp = EAL.load_asset(MGR)
    ge = BGE.get_graph_editor_by_name(mbp, "EventGraph")
    s_arm = achar_set_armado(ge)
    w("ramo instalado:", ramo_instalado(ge, s_arm), "| branch da batida:", achar_ramo_batida(ge, s_arm).get_name())
    w("r.Shadow.Virtual.ResolutionLodBiasDirectionalMoving =",
      unreal.SystemLibrary.get_console_variable_float_value("r.Shadow.Virtual.ResolutionLodBiasDirectionalMoving"))
    cv = curvas(s)
    erros, ev = lint(cv, s)
    w("lint (sem gravar): %s, pico %.2f EV, D=%.4f" % (erros or "ok", ev, cv["D"]))


def padrao():
    """So grava o Class Default de bDistorcaoAtiva = DISTORCAO_PADRAO no BP_LuxCeu e salva so ele."""
    if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():
        raise Aborta("feche o PIE")
    bp = EAL.load_asset(CEU)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    cdo = unreal.get_default_object(bp.generated_class())
    w("bDistorcaoAtiva (Class Default):", cdo.get_editor_property("bDistorcaoAtiva"), "->", DISTORCAO_PADRAO)
    cdo.set_editor_property("bDistorcaoAtiva", DISTORCAO_PADRAO)
    BEL.compile_blueprint(bp)
    e = erros_bp(bp, ("EventGraph",))
    if e:
        raise Aborta("BP_LuxCeu nao compilou limpo: %s" % e)
    w("salvo BP_LuxCeu:", EAL.save_loaded_asset(bp, False))
    c = [a for a in atores() if a.get_class().get_name().startswith("BP_LuxCeu")]
    if c:
        w("LUX_Ceu: override na instancia =", c[0].is_editor_property_overridden("bDistorcaoAtiva"),
          "| valor =", c[0].get_editor_property("bDistorcaoAtiva"))


def desfazer():
    preflight()
    mbp = EAL.load_asset(MGR)
    ge = BGE.get_graph_editor_by_name(mbp, "EventGraph")
    s_arm = achar_set_armado(ge)
    if ramo_instalado(ge, s_arm):
        seq = _links(s_arm, "then")[0]
        ramo = _links(seq, "then_1")[0]
        apagar, fila = [], [seq]
        while fila:
            n = fila.pop()
            if n in apagar or n == ramo:
                continue
            apagar.append(n)
            for p in n.list_all_pins():
                for q in p.list_connected_pins():
                    o = q.get_owning_node()
                    if o not in (s_arm, ramo) and o not in apagar and not _le_var(o, "bArmado", 0):
                        fila.append(o)
        ge.remove_nodes(apagar)
        G(ge).link(s_arm, "then", ramo, G(ge).exec_in(ramo))
        BEL.compile_blueprint(mbp)
        w("manager: ramo removido (%d nos)" % len(apagar))
    for a in por_tag(TAG_CEU) + por_tag(TAG_SEQ):
        eas().destroy_actor(a)
        w("ator removido")
    EAL.save_loaded_asset(mbp, False)
    U = unreal.EditorLoadingAndSavingUtils
    U.save_packages([p for p in U.get_dirty_map_packages() if p.get_name() == "/Game/Masion/Mapa_B"], True)
    if APAGAR_ASSETS:
        for p in (LS, CEU):
            EAL.delete_asset(p)
    w("desfeito. Ponha DISTORCAO_HOOK = False no setup_loop.py se nao quiser o ramo num rebuild.")


def main():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    open(LOG, "w", encoding="utf-8").close()
    modo = next((a for a in sys.argv[1:] if a in ("sondar", "instalar", "verificar", "desfazer", "padrao")), "sondar")
    w("modo:", modo)
    try:
        {"sondar": sondar, "instalar": instalar, "desfazer": desfazer, "padrao": padrao,
         "verificar": lambda: w("verificar:", verificar() or "OK")}[modo]()
    except Aborta as ex:
        w("ABORTADO:", ex, "| nada foi salvo nesta etapa; sujos:", sujos())
    except Exception:
        w("ERRO " + traceback.format_exc(), "| sujos:", sujos())


if __name__ == "__main__":
    main()
