# Loop estilo P.T. no Mapa_B (UE 5.8, so Blueprint).
#   py "C:/Users/bruno/Documents/Unreal Projects/TCC_Horror_Lux/Tools/Loop/setup_loop.py"          -> (re)monta no mapa
#   py "C:/Users/bruno/Documents/Unreal Projects/TCC_Horror_Lux/Tools/Loop/setup_loop.py" rebuild  -> refaz o grafo do manager
# Sem "rebuild", o BP_LuxLoopManager existente e mantido (edicoes feitas a mao nele ficam); o EventGraph da BP_LuxLoopDoor
# e os atores LUX_LOOP do mapa sao sempre refeitos.
# "rebuild" refaz o EventGraph do BP_LuxLoopManager (edicoes a mao nele se perdem) e acrescenta variaveis que faltarem.
# Nunca remove grafos de funcao: isso, com o Blueprint aberto, derrubou o editor em 26/09.
# Log: Saved/Loop/setup_log.txt. O mapa NAO e salvo (Ctrl+S); desfazer: Ctrl+Z ("LUX: loop").
import gc, os, sys, traceback, unreal

EAL = unreal.EditorAssetLibrary
BEL = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor
DIR = "/Game/Masion/LUX/Loop"
MGR = DIR + "/BP_LuxLoopManager"
LDOOR = DIR + "/BP_LuxLoopDoor"
DOOR = "/Game/FPMovement/Blueprints/Doors/BP_BaseDoor"
DOOR_C = DOOR + ".BP_BaseDoor_C"
MGR_C = MGR + ".BP_LuxLoopManager_C"
MAC = "/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:"
GS, KSL, KML, STR = ("/Script/Engine.GameplayStatics:", "/Script/Engine.KismetSystemLibrary:",
                     "/Script/Engine.KismetMathLibrary:", "/Script/Engine.KismetStringLibrary:")
ACT, CTRL, PCM, AUD = ("/Script/Engine.Actor:", "/Script/Engine.Controller:", "/Script/Engine.PlayerCameraManager:",
                       "/Script/Engine.AudioComponent:")
TAG = "LUX_LOOP"
FOLDER = "LUX/Loop"
# Mapa_B (medido pelo probe_loop.py): porta da sala = BP_BaseDoor5, porta do quarto = BP_BaseDoor7 (abre para o corredor).
SALA, QUARTO = "BP_BaseDoor5", "BP_BaseDoor7"
CHEGADA = (-3275.0, 955.0, 98.0, -90.0)    # dentro do quarto, 85 cm da porta, olhando para o corredor (centro da capsula)
GATILHO = (-3275.0, 620.0, 110.0)          # corredor, ~2,5 m da porta do quarto
GATILHO_EXT = (126.0, 25.0, 110.0)         # largura inteira do corredor (253 cm)
START = (-3275.0, 760.0, 100.0, -90.0)     # PlayerStart: corredor, de costas para o quarto
APROX = (0.0, 35.0, 4.0)   # camera de close: 35 cm a frente da macaneta (lado de quem abre) e 4 cm acima
FOV_CLOSE = 45.0
DEFAULTS = {"LoopFinal": 5, "TempoAproximar": 0.5, "TempoEscurecer": 0.08, "TempoApagado": 0.04, "TempoClarear": 0.2,
            "TempoAfastar": 0.9}
PCTRL = "/Script/Engine.PlayerController:"

saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
os.makedirs(os.path.join(saved, "Loop"), exist_ok=True)
LOG = os.path.join(saved, "Loop", "setup_log.txt")
out = []


def w(*a):
    line = " ".join(str(x) for x in a)
    out.append(line)
    unreal.log("[LUX loop] " + line)
    with open(LOG, "a", encoding="utf-8") as fh:  # grava na hora: se o editor cair, o log mostra o ultimo passo
        fh.write(line + "\n")


# ------------------------------------------------------------------ grafo
def ok_pin(p):
    """find_*_pin devolve um struct invalido (e truthy) quando o pino nao existe."""
    return p if p is not None and p.is_valid() else None


class G:
    """Atalhos sobre BlueprintGraphEditor. Falha alto se um pino nao ligar."""

    def __init__(self, ge):
        self.ge = ge

    def pos(self, n, x, y):
        n.set_node_pos(unreal.IntPoint(int(x), int(y)))
        return n

    def call(self, path, x, y, **vals):
        n = self.ge.add_call_function_node(path)
        if not n:
            raise RuntimeError("no nao criado: " + path)
        for k, v in vals.items():
            self.val(n, k, v)
        return self.pos(n, x, y)

    def macro(self, name, x, y):
        return self.pos(self.ge.add_macro_node(MAC + name), x, y)

    def branch(self, x, y):
        return self.pos(self.ge.add_branch_node(), x, y)

    def get(self, var, x, y, cls=""):
        return self.pos(self.ge.add_get_member_variable_node(var, cls), x, y)

    def set(self, var, x, y, value=None, cls=""):
        n = self.pos(self.ge.add_set_member_variable_node(var, cls), x, y)
        if value is not None:
            self.val(n, var, value)
        return n

    def val(self, n, pin, v):
        p = ok_pin(n.find_input_pin(pin))
        ok = p and p.set_pin_value(str(v))
        if p and not ok and str(v).startswith("/Script/"):  # pino de classe: tenta o formato de referencia completo
            ok = p.set_pin_value("/Script/CoreUObject.Class'%s'" % v)
        if not ok:
            raise RuntimeError("valor %s=%s nao aceito em %s" % (pin, v, n.get_node_title()))

    def link(self, a, ap, b, bp):
        pa = ok_pin(a.find_output_pin(ap))
        pb = ok_pin(b.find_input_pin(bp))
        if not (pa and pb and pa.try_create_connection(pb)):
            names = lambda n: ["%s:%s" % (p.get_pin_name(), p.get_pin_type_display_string()) for p in n.list_all_pins()]
            raise RuntimeError("ligacao falhou: %s.%s -> %s.%s (achou %s/%s, pode=%s)\n  %s\n  %s" % (
                str(a.get_node_title()).replace("\n", " "), ap, str(b.get_node_title()).replace("\n", " "), bp,
                bool(pa), bool(pb), pa.can_create_connection(pb) if (pa and pb) else "-", names(a), names(b)))

    def chain(self, *steps):
        """steps: nos, ou (no, pino_saida) para sair por outro pino exec. Liga saida -> 'execute'/'Exec' do proximo."""
        for a, b in zip(steps, steps[1:]):
            an, ap = a if isinstance(a, tuple) else (a, "then")
            bn = b[0] if isinstance(b, tuple) else b
            bp = next(str(p.get_pin_name()) for p in bn.list_input_pins() if str(p.get_pin_type_display_string()) == "Exec")
            self.link(an, ap, bn, bp)

    def note(self, text, x, y, wd, ht):
        self.ge.add_comment_node(text, unreal.Vector2D(x, y), unreal.Vector2D(wd, ht))


def errors(bp, graphs):
    msgs = []
    for g in graphs:
        ge = BGE.get_graph_editor_by_name(bp, g)
        for kind, lst in (("ERRO", ge.list_nodes_with_errors()), ("aviso", ge.list_nodes_with_warnings())):
            msgs += ["%s em %s: %s" % (kind, g, str(n.get_node_title()).replace("\n", " ")) for n in lst]
    return msgs


# ------------------------------------------------------------------ assets
def ensure_bp(path, parent_cls):
    # o force delete as vezes deixa o .uasset no disco: nesse caso reaproveita o asset (so o EventGraph e refeito)
    if EAL.does_asset_exist(path):
        w("reaproveitado", path)
        return EAL.load_asset(path)
    w("criado", path)
    return BEL.create_blueprint_asset_with_parent(path, parent_cls)


def ensure_var(bp, name, ptype, editable=True, category="Loop"):
    if name not in [str(n) for n in BEL.list_member_variable_names(bp)]:
        BEL.add_member_variable(bp, name, ptype)
        w("  variavel nova:", name)
    BEL.set_blueprint_variable_instance_editable(bp, name, editable)
    BEL.set_blueprint_variable_category(bp, name, unreal.Text(category))


def clear_event_graph(bp):
    ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
    ge.remove_nodes(list(ge.list_all_nodes()))
    for c in list(ge.list_comment_nodes()):
        ge.remove_comment_node(c)
    return G(ge)


def add_box(bp):
    # So em Blueprint recem-criado. Num Blueprint carregado do disco o get_object nao acha os componentes, a caixa
    # era criada de novo com o mesmo nome e o editor caiu (26/09, 15h01).
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    handles = sds.k2_gather_subobject_data_for_blueprint(bp)
    parent = handles[0]
    for h in handles:
        o = lib.get_object(lib.get_data(h))
        if o and o.get_name().startswith("DefaultSceneRoot"):
            parent = h
    h, fail = sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=parent, new_class=unreal.BoxComponent,
                                                                 blueprint_context=bp))
    sds.rename_subobject(h, unreal.Text("GatilhoFechar"))
    box = lib.get_object_for_blueprint(lib.get_data(h), bp)
    box.set_editor_property("box_extent", unreal.Vector(*GATILHO_EXT))
    box.set_editor_property("line_thickness", 2.0)
    return box


def build_manager():
    actor_t = BEL.get_object_reference_type(unreal.Actor.static_class())
    door_t = BEL.get_object_reference_type(EAL.load_asset(DOOR).generated_class())
    real, integer, boolean = (BEL.get_basic_type_by_name(t) for t in ("real", "int", "bool"))
    created = not EAL.does_asset_exist(MGR)
    bp = ensure_bp(MGR, unreal.Actor.static_class())
    if created:
        add_box(bp)
    sound_t = BEL.get_object_reference_type(unreal.SoundBase.static_class())
    for name, t in (("PortaQuarto", door_t), ("PortaSaida", door_t), ("PortaLoop", door_t), ("Chegada", actor_t),
                    ("CamSala", actor_t), ("CamQuarto", actor_t), ("LoopFinal", integer), ("TempoAproximar", real),
                    ("TempoEscurecer", real), ("TempoApagado", real), ("TempoClarear", real), ("TempoAfastar", real),
                    ("SomTroca", sound_t)):
        ensure_var(bp, name, t)
    for name, t in (("LoopAtual", integer), ("bArmado", boolean), ("bOcupado", boolean), ("SomAbrirPorta", sound_t)):
        ensure_var(bp, name, t, editable=False, category="Loop|Estado")
    BEL.compile_blueprint(bp)  # variaveis novas precisam existir na classe antes de criar os nos get/set
    if "AplicarTag" not in [str(x) for x in BEL.list_graph_names(bp)]:
        build_aplicar_tag(bp)
    w("  refazendo o EventGraph do manager")
    build_manager_graph(bp)
    cdo = unreal.get_default_object(bp.generated_class())
    for k, v in DEFAULTS.items():
        cdo.set_editor_property(k, v)
    EAL.save_loaded_asset(bp, False)
    w("BP_LuxLoopManager:", errors(bp, ("EventGraph", "AplicarTag")) or "compilou sem erros/avisos")
    return bp


def build_aplicar_tag(bp):
    """Funcao AplicarTag(Loop, Sufixo, Mostrar): mostra/esconde todo ator com a tag LOOP<n><Sufixo>."""
    integer, boolean = BEL.get_basic_type_by_name("int"), BEL.get_basic_type_by_name("bool")
    fe = BGE.create_and_edit_function_graph(bp, "AplicarTag")
    if fe.get_graph().get_name() != "AplicarTag":
        raise RuntimeError("grafo criado como " + fe.get_graph().get_name())
    fe.add_graph_input_parameter("Loop", integer)
    fe.add_graph_input_parameter("Sufixo", BEL.get_basic_type_by_name("string"))
    fe.add_graph_input_parameter("Mostrar", boolean)
    f = G(fe)
    entry = fe.find_graph_entry_pin().get_owning_node()
    f.pos(entry, 0, 0)
    i2s = f.call(STR + "Conv_IntToString", 220, 160)
    c1 = f.call(STR + "Concat_StrStr", 440, 140, A="LOOP")
    c2 = f.call(STR + "Concat_StrStr", 660, 160)
    s2n = f.call(STR + "Conv_StringToName", 880, 160)
    tagged = f.call(GS + "GetAllActorsWithTag", 300, 0)
    each = f.macro("ForEachLoop", 620, 0)
    notm = f.call(KML + "Not_PreBool", 900, 300)
    hide = f.call(ACT + "SetActorHiddenInGame", 1000, 0)
    col = f.call(ACT + "SetActorEnableCollision", 1300, 0)
    comp = f.call(ACT + "GetComponentByClass", 1300, 260, ComponentClass="/Script/Engine.AudioComponent")
    if "Audio" in str(comp.find_output_pin("ReturnValue").get_pin_type_display_string()):
        cast = f.macro("IsValid", 1600, 0)          # retorno ja tipado como AudioComponent
        cast_in, cast_out, audio = "InputObject", "Is Valid", comp.find_output_pin("ReturnValue")
    else:
        cast = f.pos(fe.create_node_from_name("Utilities|Casting|CastToAudioComponent", unreal.Vector2D(0, 0), [], None), 1600, 0)
        cast_in, cast_out = "Object", "then"
        audio = [p for p in cast.list_output_pins() if str(p.get_pin_name()).startswith("As")][0]
    br = f.branch(1900, 0)
    play = f.call(AUD + "Play", 2150, -80)
    fade = f.call(AUD + "FadeOut", 2150, 120, FadeOutDuration=1.0, FadeVolumeLevel=0.0)
    f.link(entry, "Loop", i2s, "InInt")
    f.link(i2s, "ReturnValue", c1, "B")
    f.link(c1, "ReturnValue", c2, "A")
    f.link(entry, "Sufixo", c2, "B")
    f.link(c2, "ReturnValue", s2n, "InString")
    f.link(s2n, "ReturnValue", tagged, "Tag")
    f.chain(entry, tagged, each)
    f.link(tagged, "OutActors", each, "Array")
    f.chain((each, "LoopBody"), hide, col, cast)
    f.link(cast, cast_out, br, "execute")
    f.link(entry, "Mostrar", notm, "A")
    f.link(notm, "ReturnValue", hide, "bNewHidden")
    f.link(entry, "Mostrar", col, "bNewActorEnableCollision")
    for n in (hide, col, comp):
        f.link(each, "Array Element", n, "self")
    f.link(comp, "ReturnValue", cast, cast_in)
    for n in (play, fade):
        if not audio.try_create_connection(n.find_input_pin("self")):
            raise RuntimeError("AudioComponent -> Play/FadeOut falhou")
    f.link(entry, "Mostrar", br, "Condition")
    f.chain((br, "then"), play)
    f.chain((br, "else"), fade)
    f.note("Esconde/mostra (render, colisao e som) todo ator com a tag LOOP<Loop><Sufixo>, ex.: LOOP3_ON", -40, -140, 2400, 560)
    BEL.compile_blueprint(bp)


def build_manager_graph(bp):
    g = clear_event_graph(bp)
    mc = MGR_C + ":"

    # BeginPlay: esconde tudo que so aparece em loops futuros e a porta de saida real
    bpl = g.pos(BEL.add_event_override(bp, "ReceiveBeginPlay", unreal.IntPoint(0, 0)), 0, 0)
    fl = g.macro("ForLoop", 300, 0)
    g.val(fl, "FirstIndex", 1)
    g.link(g.get("LoopFinal", 60, 160), "LoopFinal", fl, "LastIndex")
    at0 = g.call(mc + "AplicarTag", 620, -20, Sufixo="_ON", Mostrar="false")
    g.link(fl, "Index", at0, "Loop")
    hs = g.call(ACT + "SetActorHiddenInGame", 620, 200, bNewHidden="true")
    cs = g.call(ACT + "SetActorEnableCollision", 920, 200, bNewActorEnableCollision="false")
    saida = g.get("PortaSaida", 420, 380)
    g.link(saida, "PortaSaida", hs, "self")
    g.link(saida, "PortaSaida", cs, "self")
    g.chain(bpl, fl)
    g.chain((fl, "LoopBody"), at0)
    q0 = g.get("PortaQuarto", 920, 380)
    snd0 = g.get("OpenSound", 1120, 380, DOOR_C)
    g.link(q0, "PortaQuarto", snd0, "self")
    s_som = g.set("SomAbrirPorta", 1220, 200)
    g.link(snd0, "OpenSound", s_som, "SomAbrirPorta")
    g.chain((fl, "Completed"), hs, cs, s_som)
    g.note("Inicio: tudo com tag LOOP<n>_ON (n = 1..LoopFinal) comeca escondido; a porta de saida real tambem. "
           "Guarda o som de abrir da porta do quarto (o manager toca ele na troca)", -40, -120, 1500, 600)

    # PedirTroca: chamado pela BP_LuxLoopDoor quando o jogador interage com a porta da sala.
    # 1) a camera desliza ate a macaneta da porta da sala (CamSala); 2) piscada curta: na tela preta o jogador vai para
    # a Chegada e a vista passa para a mesma macaneta na porta do quarto (CamQuarto); 3) a porta do quarto abre, com o
    # som tocado aqui (o DoOnce da BP_BaseDoor perde o som se o frame da troca engasgar), e a camera volta aos olhos.
    Y = 900
    ev = g.pos(g.ge.add_custom_event_node("PedirTroca"), 0, Y)
    busy = g.branch(250, Y)
    g.link(g.get("bOcupado", 60, Y + 140), "bOcupado", busy, "Condition")
    s_busy = g.set("bOcupado", 500, Y, "true")
    pc = g.call(GS + "GetPlayerController", 500, Y + 320, PlayerIndex=0)
    cam = g.call(GS + "GetPlayerCameraManager", 500, Y + 440, PlayerIndex=0)
    chr_ = g.call(GS + "GetPlayerCharacter", 500, Y + 560, PlayerIndex=0)
    im1 = g.call(CTRL + "SetIgnoreMoveInput", 760, Y, bNewMoveInput="true")
    il1 = g.call(CTRL + "SetIgnoreLookInput", 1020, Y, bNewLookInput="true")
    snd = g.call(GS + "PlaySound2D", 1280, Y)
    g.link(g.get("SomTroca", 1080, Y + 200), "SomTroca", snd, "Sound")
    vt1 = g.call(PCTRL + "SetViewTargetWithBlend", 1540, Y, BlendFunc="VTBlend_EaseInOut", BlendExp=2.0)
    g.link(g.get("CamSala", 1340, Y + 220), "CamSala", vt1, "NewViewTarget")
    g.link(g.get("TempoAproximar", 1340, Y + 300), "TempoAproximar", vt1, "BlendTime")
    d1 = g.call(KSL + "Delay", 1820, Y)
    g.link(g.get("TempoAproximar", 1640, Y + 260), "TempoAproximar", d1, "Duration")
    f_out = g.call(PCM + "StartCameraFade", 2080, Y, FromAlpha=0.0, ToAlpha=1.0, Color="(R=0.0,G=0.0,B=0.0,A=1.0)",
                   bShouldFadeAudio="false", bHoldWhenFinished="true")
    g.link(g.get("TempoEscurecer", 1880, Y + 260), "TempoEscurecer", f_out, "Duration")
    add = g.call(KML + "Add_DoubleDouble", 2360, Y + 200)
    g.link(g.get("TempoEscurecer", 2160, Y + 260), "TempoEscurecer", add, "A")
    g.link(g.get("TempoApagado", 2160, Y + 340), "TempoApagado", add, "B")
    dly = g.call(KSL + "Delay", 2380, Y)
    g.link(add, "ReturnValue", dly, "Duration")
    # -- troca (tela preta)
    che = g.get("Chegada", 2500, Y + 460)
    cl = g.call(ACT + "K2_GetActorLocation", 2700, Y + 420)
    cr = g.call(ACT + "K2_GetActorRotation", 2700, Y + 540)
    g.link(che, "Chegada", cl, "self")
    g.link(che, "Chegada", cr, "self")
    tp = g.call(ACT + "K2_TeleportTo", 2660, Y)
    g.link(chr_, "ReturnValue", tp, "self")
    g.link(cl, "ReturnValue", tp, "DestLocation")
    g.link(cr, "ReturnValue", tp, "DestRotation")
    rot = g.call(CTRL + "SetControlRotation", 2960, Y)
    g.link(cr, "ReturnValue", rot, "NewRotation")
    vt2 = g.call(PCTRL + "SetViewTargetWithBlend", 3220, Y)
    g.link(g.get("CamQuarto", 3040, Y + 220), "CamQuarto", vt2, "NewViewTarget")
    cut = g.call(PCM + "SetGameCameraCutThisFrame", 3480, Y)
    inc = g.call(KML + "Add_IntInt", 3660, Y + 200)  # operador promovivel: tipa ao ligar A, so depois aceita B=1
    g.link(g.get("LoopAtual", 3480, Y + 240), "LoopAtual", inc, "A")
    g.val(inc, "B", 1)
    s_loop = g.set("LoopAtual", 3760, Y)
    g.link(inc, "ReturnValue", s_loop, "LoopAtual")
    on = g.call(mc + "AplicarTag", 4020, Y, Sufixo="_ON", Mostrar="true")
    off = g.call(mc + "AplicarTag", 4300, Y, Sufixo="_OFF", Mostrar="false")
    g.link(s_loop, "Output_Get", on, "Loop")
    g.link(s_loop, "Output_Get", off, "Loop")
    # -- ultimo loop: troca a porta de loop pela porta real (abre de verdade na proxima vez)
    ge_ = g.call(KML + "GreaterEqual_IntInt", 4460, Y + 220)
    g.link(s_loop, "Output_Get", ge_, "A")
    g.link(g.get("LoopFinal", 4300, Y + 300), "LoopFinal", ge_, "B")
    fin = g.branch(4580, Y)
    g.link(ge_, "ReturnValue", fin, "Condition")
    ploop, psaida = g.get("PortaLoop", 4660, Y + 420), g.get("PortaSaida", 4660, Y + 520)
    h1 = g.call(ACT + "SetActorHiddenInGame", 4820, Y - 300, bNewHidden="true")
    c1 = g.call(ACT + "SetActorEnableCollision", 5080, Y - 300, bNewActorEnableCollision="false")
    h2 = g.call(ACT + "SetActorHiddenInGame", 5340, Y - 300, bNewHidden="false")
    c2 = g.call(ACT + "SetActorEnableCollision", 5600, Y - 300, bNewActorEnableCollision="true")
    for n, v in ((h1, ploop), (c1, ploop), (h2, psaida), (c2, psaida)):
        g.link(v, str(v.list_output_pins()[0].get_pin_name()), n, "self")
    armed = g.set("bArmado", 5860, Y, "true")
    f_in = g.call(PCM + "StartCameraFade", 6100, Y, FromAlpha=1.0, ToAlpha=0.0, Color="(R=0.0,G=0.0,B=0.0,A=1.0)",
                  bShouldFadeAudio="false", bHoldWhenFinished="false")
    g.link(g.get("TempoClarear", 5920, Y + 260), "TempoClarear", f_in, "Duration")
    # -- a porta do quarto abre; o som dela vem daqui (o da porta fica mudo durante essa abertura)
    q1 = g.get("PortaQuarto", 6300, Y + 300)
    closed = g.get("IsClosed", 6500, Y + 240, DOOR_C)
    g.link(q1, "PortaQuarto", closed, "self")
    isc = g.branch(6380, Y)
    g.link(closed, "IsClosed", isc, "Condition")
    mute = g.set("OpenSound", 6640, Y - 160, cls=DOOR_C)
    g.link(q1, "PortaQuarto", mute, "self")
    opn = g.call(DOOR_C + ":Interact", 6900, Y - 160)
    g.link(q1, "PortaQuarto", opn, "self")
    creak = g.call(GS + "PlaySound2D", 7160, Y - 160, VolumeMultiplier=0.4)
    g.link(g.get("SomAbrirPorta", 6960, Y), "SomAbrirPorta", creak, "Sound")
    vt3 = g.call(PCTRL + "SetViewTargetWithBlend", 7420, Y, BlendFunc="VTBlend_EaseInOut", BlendExp=2.0)
    g.link(chr_, "ReturnValue", vt3, "NewViewTarget")
    g.link(g.get("TempoAfastar", 7240, Y + 300), "TempoAfastar", vt3, "BlendTime")
    d3 = g.call(KSL + "Delay", 7700, Y)
    g.link(g.get("TempoAfastar", 7520, Y + 260), "TempoAfastar", d3, "Duration")
    unmute = g.set("OpenSound", 7960, Y, cls=DOOR_C)
    g.link(q1, "PortaQuarto", unmute, "self")
    g.link(g.get("SomAbrirPorta", 7780, Y + 200), "SomAbrirPorta", unmute, "OpenSound")
    im0 = g.call(CTRL + "SetIgnoreMoveInput", 8220, Y, bNewMoveInput="false")
    il0 = g.call(CTRL + "SetIgnoreLookInput", 8480, Y, bNewLookInput="false")
    s_free = g.set("bOcupado", 8740, Y, "false")
    g.chain(ev, busy)
    g.chain((busy, "else"), s_busy, im1, il1, snd, vt1, d1, f_out, dly, tp, rot, vt2, cut, s_loop, on, off, fin)
    g.chain((fin, "then"), h1, c1, h2, c2, armed)
    g.chain((fin, "else"), armed, f_in, isc)
    g.chain((isc, "then"), mute, opn, creak, vt3)
    g.chain((isc, "else"), vt3, d3, unmute, im0, il0, s_free)
    for n in (im1, il1, vt1, rot, vt2, vt3, im0, il0):
        g.link(pc, "ReturnValue", n, "self")
    for n in (f_out, cut, f_in):
        g.link(cam, "ReturnValue", n, "self")
    g.note("Troca: camera desliza ate a macaneta da porta da sala -> piscada -> jogador vai para a Chegada e a vista passa "
           "para a mesma macaneta na porta do quarto -> a porta abre (som tocado aqui) e a camera volta aos olhos. "
           "Mudancas do loop N (na tela preta): tags LOOP<N>_ON aparecem, LOOP<N>_OFF somem", -40, Y - 420, 9000, 1100)

    # Gatilho: o jogador entrou no corredor depois da troca -> a porta do quarto fecha atras dele
    Y = 2400
    ov = g.pos(BEL.add_event_override(bp, "ReceiveActorBeginOverlap", unreal.IntPoint(0, 0)), 0, Y)
    pl = g.call(GS + "GetPlayerCharacter", 0, Y + 200, PlayerIndex=0)
    eq = g.call(KML + "EqualEqual_ObjectObject", 260, Y + 160)
    g.link(ov, "OtherActor", eq, "A")
    g.link(pl, "ReturnValue", eq, "B")
    both = g.call(KML + "BooleanAND", 480, Y + 100)
    g.link(g.get("bArmado", 300, Y + 60), "bArmado", both, "A")
    g.link(eq, "ReturnValue", both, "B")
    b1 = g.branch(700, Y)
    g.link(both, "ReturnValue", b1, "Condition")
    s_arm = g.set("bArmado", 950, Y, "false")
    q2 = g.get("PortaQuarto", 950, Y + 240)
    closed2 = g.get("IsClosed", 1150, Y + 200, DOOR_C)
    g.link(q2, "PortaQuarto", closed2, "self")
    b2 = g.branch(1200, Y)
    g.link(closed2, "IsClosed", b2, "Condition")
    shut = g.call(DOOR_C + ":Interact", 1460, Y)
    g.link(q2, "PortaQuarto", shut, "self")
    g.chain(ov, b1)
    g.chain((b1, "then"), s_arm, b2)
    g.chain((b2, "else"), shut)
    g.note("Gatilho no corredor (caixa GatilhoFechar): depois de cada troca, fecha a porta do quarto atras do jogador",
           -40, Y - 120, 1800, 480)

    BEL.compile_blueprint(bp)


def build_loop_door(mgr_bp):
    bp = ensure_bp(LDOOR, EAL.load_asset(DOOR).generated_class())
    ensure_var(bp, "Manager", BEL.get_object_reference_type(mgr_bp.generated_class()))
    g = clear_event_graph(bp)
    ev = g.pos(BEL.add_event_override(bp, "Interact", unreal.IntPoint(0, 0)), 0, 0)
    call = g.call(MGR_C + ":PedirTroca", 320, 0)
    g.link(g.get("Manager", 100, 160), "Manager", call, "self")
    g.chain(ev, call)
    g.note("Porta da sala durante o loop: nunca abre; pede a troca ao BP_LuxLoopManager. "
           "No ultimo loop o manager esconde esta porta e revela a porta real que fica embaixo dela", -40, -120, 900, 380)
    BEL.compile_blueprint(bp)
    EAL.save_loaded_asset(bp, False)
    w("BP_LuxLoopDoor:", errors(bp, ("EventGraph",)) or "compilou sem erros/avisos")
    return bp


# ------------------------------------------------------------------ mapa
def spawn(eas, cls_or_asset, label, loc, yaw=0.0):
    rot = unreal.Rotator(roll=0.0, pitch=0.0, yaw=yaw)
    a = eas.spawn_actor_from_class(cls_or_asset, unreal.Vector(*loc), rot)
    a.set_actor_label(label)
    a.set_folder_path(FOLDER)
    a.set_editor_property("tags", [unreal.Name(TAG)])
    return a


def close_leaf(door):
    # o probe_loop2 deixou a folha da porta 7 aberta (override de instancia); garante as duas fechadas.
    for name in ("Door", "DoorHandle"):
        comps = [c for c in door.get_components_by_class(unreal.StaticMeshComponent) if c.get_name() == name]
        if comps and abs(comps[0].get_editor_property("relative_rotation").yaw) > 0.01:
            comps[0].set_editor_property("relative_rotation", unreal.Rotator(roll=0.0, pitch=0.0, yaw=0.0))
            w("folha %s.%s fechada" % (door.get_actor_label(), name))


def place(mgr_bp, door_bp):
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not world.get_path_name().startswith("/Game/Masion/Mapa_B"):
        raise RuntimeError("abra o Mapa_B antes (aberto: %s)" % world.get_path_name())
    w("atores LUX_LOOP antigos removidos:", remove_level_actors())
    by = {a.get_actor_label(): a for a in eas.get_all_level_actors()}
    sala, quarto = by[SALA], by[QUARTO]
    for d in (sala, quarto):
        close_leaf(d)
    # textos do prompt em portugues (a porta 7 ja usa estes; a 5 estava com o padrao em ingles)
    sala.set_editor_property("DoorCloseText", "Abrir Porta")
    sala.set_editor_property("DoorOpenText", "Fechar Porta")

    ldoor = eas.spawn_actor_from_class(door_bp.generated_class(), sala.get_actor_location(), sala.get_actor_rotation())
    ldoor.set_actor_scale3d(sala.get_actor_scale3d())
    ldoor.set_actor_label("LOOP_PortaSala")
    ldoor.set_folder_path(FOLDER)
    ldoor.set_editor_property("tags", [unreal.Name(TAG)])
    for k in ("OpenDegrees", "ResetCloseSound", "OpenSound", "CloseSound", "TryOpenSound", "CanRotateHandle",
              "Show Door Prompt?", "DoorCloseText", "DoorOpenText"):
        try:
            ldoor.set_editor_property(k, sala.get_editor_property(k))
        except Exception:
            pass  # variavel nao editavel por instancia: fica o padrao da BP_BaseDoor (igual ao da porta 5)

    x, y, z, yaw = CHEGADA
    chegada = spawn(eas, unreal.TargetPoint, "LOOP_Chegada", (x, y, z), yaw)
    cams = {}
    for label, door in (("LOOP_CamSala", ldoor), ("LOOP_CamQuarto", quarto)):
        # mesma pose relativa a macaneta de cada porta: e o quadro que troca na piscada
        h = [c for c in door.get_components_by_class(unreal.StaticMeshComponent) if c.get_name() == "DoorHandle"][0]
        o = unreal.SystemLibrary.get_component_bounds(h)[0]
        loc = (o.x + APROX[0], o.y + APROX[1], o.z + APROX[2])
        c = spawn(eas, unreal.CameraActor, label, loc)
        c.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(unreal.Vector(*loc), o), False)
        cc = c.get_editor_property("camera_component")
        cc.set_editor_property("field_of_view", FOV_CLOSE)
        cc.set_editor_property("constrain_aspect_ratio", False)
        cams[label] = c
    mgr = spawn(eas, mgr_bp.generated_class(), "LOOP_Manager", GATILHO)
    x, y, z, yaw = START
    if not [a for a in eas.get_all_level_actors() if isinstance(a, unreal.PlayerStart)]:
        spawn(eas, unreal.PlayerStart, "LOOP_PlayerStart", (x, y, z), yaw)
        w("PlayerStart criado no corredor")
    for k, v in (("PortaQuarto", quarto), ("PortaSaida", sala), ("PortaLoop", ldoor), ("Chegada", chegada),
                 ("CamSala", cams["LOOP_CamSala"]), ("CamQuarto", cams["LOOP_CamQuarto"])):
        mgr.set_editor_property(k, v)
    ldoor.set_editor_property("Manager", mgr)
    w("montado: LOOP_PortaSala sobre %s, LOOP_Chegada %s, LOOP_Manager %s" % (
        SALA, chegada.get_actor_location(), mgr.get_actor_location()))


def cleanup_probe():
    for k in ("pbp", "ge", "g", "n", "ev", "leaf"):
        globals().pop(k, None)
    gc.collect()
    unreal.SystemLibrary.collect_garbage()
    probe_dir = DIR + "/_Probe"
    if EAL.does_directory_exist(probe_dir):
        for p in EAL.list_assets(probe_dir, True, False):
            ok = EAL.delete_asset(p.split(".")[0])
            w("probe temporario %s apagado: %s" % (p, ok))


def remove_level_actors():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    old = [a for a in eas.get_all_level_actors() if TAG in [str(t) for t in a.tags]]
    for a in old:
        eas.destroy_actor(a)
    return len(old)


def main():
    rebuild = "rebuild" in sys.argv[1:]
    open(LOG, "w", encoding="utf-8").close()
    try:
        cleanup_probe()
        aes = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
        for path in (MGR, LDOOR):  # editar um Blueprint com a janela dele aberta e o que derrubou o editor
            if EAL.does_asset_exist(path):
                aes.close_all_editors_for_asset(EAL.load_asset(path))
        # tira as instancias antes de compilar: sem atores para reinstanciar no meio da edicao (o place() recria)
        w("atores LUX_LOOP removidos antes de editar:", remove_level_actors())
        if EAL.does_asset_exist(MGR) and not rebuild:
            mgr_bp = EAL.load_asset(MGR)
            w("BP_LuxLoopManager existente mantido (use rebuild para refazer o grafo)")
        else:
            mgr_bp = build_manager()
        door_bp = build_loop_door(mgr_bp)  # so o EventGraph: refazer e seguro e mantem a porta em dia com o manager
        with unreal.ScopedEditorTransaction("LUX: loop"):
            place(mgr_bp, door_bp)
        w("OK. Salve o mapa com Ctrl+S.")
    except Exception:
        w("ERRO " + traceback.format_exc())


main()
