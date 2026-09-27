# LUX - porta que bate (item 4). Idempotente. Nao mexe no PedirTroca, na BP_BaseDoor nem na BP_LuxLoopDoor.
#   py "<projeto>/Tools/Loop/add_door_slam.py"
# 1) Assets em /Game/Masion/LUX/Loop/Audio: ATT_LuxPortaBatida (atenuacao) e SC_LuxPortaBatida (placeholder em camadas).
# 2) Variaveis novas no BP_LuxLoopManager (so as que faltam).
# 3) Funcoes BaterPorta(Porta), BaterPorta_Impacto e BaterPorta_Restaurar (so se nao existirem; nunca apaga funcao).
#    Sem no latente: o impacto e a restauracao vem por Set Timer by Function Name.
# 4) Gatilho (GatilhoFechar): se bBaterPortaAtivo e LoopAtual esta em LoopsBatida e ainda nao bateu neste loop,
#    bate a porta do quarto; senao, o fechamento de sempre. O setup_loop.py gera os mesmos nos (rebuild nao apaga).
# Salva o manager e os assets novos. Log: Saved/Loop/door_slam_log.txt
import os, traceback, unreal

EAL = unreal.EditorAssetLibrary
BEL = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor
MGR = "/Game/Masion/LUX/Loop/BP_LuxLoopManager"
MGR_C = MGR + ".BP_LuxLoopManager_C:"
DOOR = "/Game/FPMovement/Blueprints/Doors/BP_BaseDoor"
DOOR_C = DOOR + ".BP_BaseDoor_C"
AUDIO = "/Game/Masion/LUX/Loop/Audio"
ATT = AUDIO + "/ATT_LuxPortaBatida"
CUE = AUDIO + "/SC_LuxPortaBatida"
SHAKE = "/Game/FPMovement/Player/Effects/Headbob/BP_JumpEnd.BP_JumpEnd_C"  # camera shake que ja existe
GS, KSL, KML, ARR = ("/Script/Engine.GameplayStatics:", "/Script/Engine.KismetSystemLibrary:",
                     "/Script/Engine.KismetMathLibrary:", "/Script/Engine.KismetArrayLibrary:")
TL = "/Script/Engine.TimelineComponent:"
VELOCIDADE = 6.0      # play rate da RotateDoor_TL na batida (0,7 s / 6 = ~0,12 s)
T_MIN = 0.02
T_RESTAURAR = 0.2
ESCALA_SHAKE = 0.3
# camadas do placeholder: (onda, pitch, volume)
CAMADAS = (("/Game/FPMovement/Assets/Audio/Abilitys/Door/SW_Close_Door", 0.7, 1.0),
           ("/Game/FPMovement/Assets/Audio/Character/Footsteps/WaveFiles/Footsteps_Metal/SW_Footsteps_Metal05", 0.45, 0.8),
           ("/Game/FPMovement/Assets/Audio/Abilitys/Flashlight/SW_Flashlight_Hit", 1.6, 0.6))

LOG = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "Loop", "door_slam_log.txt")


def w(*a):
    line = " ".join(str(x) for x in a)
    unreal.log("[LUX porta] " + line)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


# ------------------------------------------------------------------ grafo (mesmo estilo do setup_loop.py)
def ok_pin(p):
    return p if p is not None and p.is_valid() else None


class G:
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
        if p and not ok and "." in str(v) and str(v).startswith("/"):
            for fmt in ("/Script/Engine.BlueprintGeneratedClass'%s'", "/Script/CoreUObject.Class'%s'", "/Script/Engine.SoundAttenuation'%s'"):
                ok = p.set_pin_value(fmt % v)
                if ok:
                    break
        if not ok:
            raise RuntimeError("valor %s=%s nao aceito em %s" % (pin, v, n.get_node_title()))

    def link(self, a, ap, b, bp):
        pa = ok_pin(a.find_output_pin(ap))
        pb = ok_pin(b.find_input_pin(bp))
        if not (pa and pb and pa.try_create_connection(pb)):
            names = lambda n: ["%s:%s" % (p.get_pin_name(), p.get_pin_type_display_string()) for p in n.list_all_pins()]
            raise RuntimeError("ligacao falhou: %s.%s -> %s.%s (achou %s/%s)\n  %s\n  %s" % (
                str(a.get_node_title()).replace("\n", " "), ap, str(b.get_node_title()).replace("\n", " "), bp,
                bool(pa), bool(pb), names(a), names(b)))

    def exec_in(self, n):
        # o nome exibido do tipo e traduzido ("Exec"/"Execucao"); o schema JSON nao
        return next(str(p.get_pin_name()) for p in n.list_input_pins() if '"exec"' in str(p.get_pin_type_as_json_schema()))

    def chain(self, *steps):
        for a, b in zip(steps, steps[1:]):
            an, ap = a if isinstance(a, tuple) else (a, "then")
            bn = b[0] if isinstance(b, tuple) else b
            self.link(an, ap, bn, self.exec_in(bn))

    def note(self, text, x, y, wd, ht):
        self.ge.add_comment_node(text, unreal.Vector2D(x, y), unreal.Vector2D(wd, ht))


# ------------------------------------------------------------------ assets de audio
def ensure_audio():
    at = unreal.AssetToolsHelpers.get_asset_tools()
    if not EAL.does_directory_exist(AUDIO):
        EAL.make_directory(AUDIO)
    if EAL.does_asset_exist(ATT):
        att = EAL.load_asset(ATT)
        w("ATT_LuxPortaBatida existente mantida")
    else:
        att = at.create_asset("ATT_LuxPortaBatida", AUDIO, unreal.SoundAttenuation, unreal.SoundAttenuationFactory())
        s = att.get_editor_property("attenuation")
        s.set_editor_property("attenuate", True)
        s.set_editor_property("spatialize", True)
        s.set_editor_property("attenuation_shape", unreal.AttenuationShape.SPHERE)
        s.set_editor_property("attenuation_shape_extents", unreal.Vector(250.0, 0.0, 0.0))  # Inner Radius
        s.set_editor_property("falloff_distance", 2250.0)                                    # conta a partir do raio interno
        s.set_editor_property("distance_algorithm", unreal.AttenuationDistanceModel.NATURAL_SOUND)
        att.set_editor_property("attenuation", s)
        EAL.save_loaded_asset(att, False)
        w("ATT_LuxPortaBatida criada: inner 250, falloff 2250, natural sound, spatialize")
    if EAL.does_asset_exist(CUE):
        cue = EAL.load_asset(CUE)
        w("SC_LuxPortaBatida existente mantida")
    else:
        cue = at.create_asset("SC_LuxPortaBatida", AUDIO, unreal.SoundCue, unreal.SoundCueFactoryNew())
        mix = unreal.new_object(unreal.SoundNodeMixer, cue)
        filhos, vols, todos = [], [], [mix]
        for onda, pitch, vol in CAMADAS:
            wp = unreal.new_object(unreal.SoundNodeWavePlayer, cue)
            wp.set_editor_property("sound_wave", EAL.load_asset(onda))
            mod = unreal.new_object(unreal.SoundNodeModulator, cue)
            for k, v in (("pitch_min", pitch), ("pitch_max", pitch), ("volume_min", 1.0), ("volume_max", 1.0)):
                mod.set_editor_property(k, v)
            mod.set_editor_property("child_nodes", [wp])
            filhos.append(mod)
            vols.append(vol)
            todos += [mod, wp]
        mix.set_editor_property("child_nodes", filhos)
        mix.set_editor_property("input_volume", vols)
        cue.set_editor_property("first_node", mix)
        try:
            cue.set_editor_property("all_nodes", todos)
        except Exception as e:
            w("  aviso: all_nodes nao exposto (%s)" % e)
        cue.set_editor_property("attenuation_settings", att)
        cue.set_editor_property("override_attenuation", False)
        EAL.save_loaded_asset(cue, False)
        w("SC_LuxPortaBatida criado: Mixer com %s" % ", ".join("%s pitch %.2f vol %.1f" % (o.rsplit("/", 1)[-1], p, v)
                                                          for o, p, v in CAMADAS))
    return att, cue


# ------------------------------------------------------------------ variaveis
def ensure_var(bp, name, ptype, editable, category):
    if name not in [str(n) for n in BEL.list_member_variable_names(bp)]:
        BEL.add_member_variable(bp, name, ptype)
        w("  variavel nova:", name)
    BEL.set_blueprint_variable_instance_editable(bp, name, editable)
    BEL.set_blueprint_variable_category(bp, name, unreal.Text(category))


def ensure_vars(bp, cue):
    door_t = BEL.get_object_reference_type(EAL.load_asset(DOOR).generated_class())
    sound_t = BEL.get_object_reference_type(unreal.SoundBase.static_class())
    integer, boolean = BEL.get_basic_type_by_name("int"), BEL.get_basic_type_by_name("bool")
    novas = [n for n in ("bBaterPortaAtivo", "LoopsBatida", "UltimoLoopBatida", "SomBatida")
             if n not in [str(x) for x in BEL.list_member_variable_names(bp)]]
    ensure_var(bp, "bBaterPortaAtivo", boolean, True, "Loop|Porta")
    ensure_var(bp, "LoopsBatida", BEL.get_array_type(integer), True, "Loop|Porta")
    ensure_var(bp, "SomBatida", sound_t, True, "Loop|Porta")
    for n, t in (("UltimoLoopBatida", integer), ("bBatendo", boolean), ("PortaBatendo", door_t), ("CloseSoundSalvo", sound_t)):
        ensure_var(bp, n, t, False, "Loop|Estado")
    BEL.compile_blueprint(bp)
    cdo = unreal.get_default_object(bp.generated_class())
    padroes = {"bBaterPortaAtivo": True, "LoopsBatida": [4], "UltimoLoopBatida": -1, "SomBatida": cue}
    for k, v in padroes.items():
        if k in novas:  # so na criacao: nao sobrescreve ajuste feito a mao
            cdo.set_editor_property(k, v)
    w("  padroes:", {k: cdo.get_editor_property(k) for k in padroes})


# ------------------------------------------------------------------ funcoes
def nova_funcao(bp, nome):
    if nome in [str(x) for x in BEL.list_graph_names(bp)]:
        w("  funcao %s ja existe: mantida" % nome)
        return None
    fe = BGE.create_and_edit_function_graph(bp, nome)
    if fe.get_graph().get_name() != nome:
        raise RuntimeError("grafo criado como " + fe.get_graph().get_name())
    w("  funcao nova:", nome)
    return fe


def build_bater_porta(bp):
    fe = nova_funcao(bp, "BaterPorta")
    if not fe:
        return
    fe.add_graph_input_parameter("Porta", BEL.get_object_reference_type(EAL.load_asset(DOOR).generated_class()))
    f = G(fe)
    entry = f.pos(fe.find_graph_entry_pin().get_owning_node(), 0, 0)
    # guardas: ja batendo -> sai; porta fechada -> sai (o Interact alterna: numa porta fechada ela abriria)
    b_busy = f.branch(260, 0)
    f.link(f.get("bBatendo", 60, 160), "bBatendo", b_busy, "Condition")
    closed = f.get("IsClosed", 400, 200, DOOR_C)
    f.link(entry, "Porta", closed, "self")
    b_closed = f.branch(560, 0)
    f.link(closed, "IsClosed", b_closed, "Condition")
    s_busy = f.set("bBatendo", 800, 0, "true")
    s_porta = f.set("PortaBatendo", 1040, 0)
    f.link(entry, "Porta", s_porta, "PortaBatendo")
    # guarda o CloseSound so se ainda nao houver um guardado
    salvo_ok = f.call(KSL + "IsValid", 1200, 220)
    f.link(f.get("CloseSoundSalvo", 1040, 260), "CloseSoundSalvo", salvo_ok, "Object")
    b_salvo = f.branch(1300, 0)
    f.link(salvo_ok, "ReturnValue", b_salvo, "Condition")
    cs_get = f.get("CloseSound", 1400, 300, DOOR_C)
    f.link(entry, "Porta", cs_get, "self")
    s_salvo = f.set("CloseSoundSalvo", 1560, 120)
    f.link(cs_get, "CloseSound", s_salvo, "CloseSoundSalvo")
    # silencia o som da propria porta (na batida a folha pula a janela de +-3 graus do DoOnce)
    mute = f.set("CloseSound", 1820, 0, cls=DOOR_C)
    f.link(entry, "Porta", mute, "self")
    shut = f.call(DOOR_C + ":Interact", 2080, 0)
    f.link(entry, "Porta", shut, "self")
    tl = f.get("RotateDoor_TL", 2080, 260, DOOR_C)
    f.link(entry, "Porta", tl, "self")
    rate = f.call(TL + "SetPlayRate", 2340, 0, NewRate=VELOCIDADE)   # depois do Interact
    f.link(tl, "RotateDoor_TL", rate, "self")
    # t = posicao / play rate (fecha em reverse ate 0), minimo T_MIN
    posn = f.call(TL + "GetPlaybackPosition", 2340, 260)
    f.link(tl, "RotateDoor_TL", posn, "self")
    div = f.call(KML + "SafeDivide", 2580, 260, B=VELOCIDADE)  # Divide_DoubleDouble resolvia para FrameNumber / FrameNumber
    f.link(posn, "ReturnValue", div, "A")
    mx = f.call(KML + "FMax", 2800, 260, B=T_MIN)
    f.link(div, "ReturnValue", mx, "A")
    timer = f.call(KSL + "K2_SetTimer", 2600, 0, FunctionName="BaterPorta_Impacto", bLooping="false")
    f.link(mx, "ReturnValue", timer, "Time")
    f.chain(entry, b_busy)
    f.chain((b_busy, "else"), b_closed)
    f.chain((b_closed, "else"), s_busy, s_porta, b_salvo)
    f.chain((b_salvo, "else"), s_salvo, mute)
    f.chain((b_salvo, "then"), mute)
    f.chain(mute, shut, rate, timer)
    f.note("BaterPorta: fecha a porta ABERTA com violencia. Silencia o CloseSound (guardado em CloseSoundSalvo), "
           "Interact, play rate %.0f na RotateDoor_TL e agenda BaterPorta_Impacto para posicao/rate (min %.2f s). "
           "Sem Delay: funcoes nao aceitam no latente" % (VELOCIDADE, T_MIN), -40, -160, 3100, 620)


def build_impacto(bp, att):
    fe = nova_funcao(bp, "BaterPorta_Impacto")
    if not fe:
        return
    f = G(fe)
    entry = f.pos(fe.find_graph_entry_pin().get_owning_node(), 0, 0)
    porta = f.get("PortaBatendo", 60, 200)
    ok = f.call(KSL + "IsValid", 260, 200)
    f.link(porta, "PortaBatendo", ok, "Object")
    b_ok = f.branch(260, 0)
    f.link(ok, "ReturnValue", b_ok, "Condition")
    handle = f.get("DoorHandle", 460, 260, DOOR_C)       # lado da macaneta = batente, onde a folha bate
    f.link(porta, "PortaBatendo", handle, "self")
    bounds = f.call(KSL + "GetComponentBounds", 680, 240)
    f.link(handle, "DoorHandle", bounds, "Component")
    snd = f.call(GS + "PlaySoundAtLocation", 900, 0, AttenuationSettings=att.get_path_name())
    f.link(f.get("SomBatida", 700, 160), "SomBatida", snd, "Sound")
    f.link(bounds, "Origin", snd, "Location")
    pc = f.call(GS + "GetPlayerController", 1000, 300, PlayerIndex=0)
    shake = f.call("/Script/Engine.PlayerController:ClientStartCameraShake", 1200, 0, Shake=SHAKE, Scale=ESCALA_SHAKE)
    f.link(pc, "ReturnValue", shake, "self")
    timer = f.call(KSL + "K2_SetTimer", 1500, 0, FunctionName="BaterPorta_Restaurar", Time=T_RESTAURAR, bLooping="false")
    f.chain(entry, b_ok)
    f.chain((b_ok, "then"), snd, shake, timer)
    f.chain((b_ok, "else"), timer)
    f.note("BaterPorta_Impacto: som SomBatida no batente (bounds do DoorHandle), shake curto (BP_JumpEnd x%.1f) "
           "e restauracao %.1f s depois" % (ESCALA_SHAKE, T_RESTAURAR), -40, -160, 1800, 560)


def build_restaurar(bp):
    fe = nova_funcao(bp, "BaterPorta_Restaurar")
    if not fe:
        return
    f = G(fe)
    entry = f.pos(fe.find_graph_entry_pin().get_owning_node(), 0, 0)
    porta = f.get("PortaBatendo", 60, 200)
    ok = f.call(KSL + "IsValid", 260, 200)
    f.link(porta, "PortaBatendo", ok, "Object")
    b_ok = f.branch(260, 0)
    f.link(ok, "ReturnValue", b_ok, "Condition")
    tl = f.get("RotateDoor_TL", 460, 260, DOOR_C)
    f.link(porta, "PortaBatendo", tl, "self")
    rate = f.call(TL + "SetPlayRate", 700, 0, NewRate=1.0)
    f.link(tl, "RotateDoor_TL", rate, "self")
    back = f.set("CloseSound", 960, 0, cls=DOOR_C)
    f.link(porta, "PortaBatendo", back, "self")
    f.link(f.get("CloseSoundSalvo", 760, 200), "CloseSoundSalvo", back, "CloseSound")
    c1 = f.set("CloseSoundSalvo", 1220, 0)
    c2 = f.set("bBatendo", 1460, 0, "false")
    c3 = f.set("PortaBatendo", 1700, 0)
    f.chain(entry, b_ok)
    f.chain((b_ok, "then"), rate, back, c1)
    f.chain((b_ok, "else"), c1)
    f.chain(c1, c2, c3)
    f.note("BaterPorta_Restaurar: play rate 1 e CloseSound devolvidos; limpa o estado", -40, -160, 1900, 520)


# ------------------------------------------------------------------ gatilho
def inserir_no_gatilho(ge, s_arm, b_fechar, x, y):
    """Entre o 'bArmado = false' e o Branch(IsClosed) do fechamento normal, pergunta se este loop bate a porta.
    then -> UltimoLoopBatida = LoopAtual; BaterPorta(PortaQuarto). else -> o fechamento de sempre (b_fechar)."""
    g = G(ge)
    ativo = g.get("bBaterPortaAtivo", x, y + 200)
    loop1 = g.get("LoopAtual", x, y + 300)
    cont = g.call(ARR + "Array_Contains", x + 220, y + 260)
    g.link(g.get("LoopsBatida", x, y + 400), "LoopsBatida", cont, "TargetArray")
    g.link(loop1, "LoopAtual", cont, "ItemToFind")
    ne = g.call(KML + "NotEqual_IntInt", x + 220, y + 420)
    g.link(g.get("UltimoLoopBatida", x, y + 500), "UltimoLoopBatida", ne, "A")
    g.link(g.get("LoopAtual", x, y + 580), "LoopAtual", ne, "B")
    and1 = g.call(KML + "BooleanAND", x + 460, y + 200)
    g.link(ativo, "bBaterPortaAtivo", and1, "A")
    g.link(cont, "ReturnValue", and1, "B")
    and2 = g.call(KML + "BooleanAND", x + 620, y + 260)
    g.link(and1, "ReturnValue", and2, "A")
    g.link(ne, "ReturnValue", and2, "B")
    br = g.branch(x + 700, y)
    g.link(and2, "ReturnValue", br, "Condition")
    s_ult = g.set("UltimoLoopBatida", x + 950, y - 220)
    g.link(g.get("LoopAtual", x + 760, y - 80), "LoopAtual", s_ult, "UltimoLoopBatida")
    bate = g.call(MGR_C + "BaterPorta", x + 1200, y - 220)
    g.link(g.get("PortaQuarto", x + 1000, y - 60), "PortaQuarto", bate, "Porta")
    g.chain(s_arm, br)
    g.chain((br, "then"), s_ult, bate)
    g.chain((br, "else"), b_fechar)
    g.note("Porta que bate (Tools/Loop/add_door_slam.py): se bBaterPortaAtivo e LoopAtual em LoopsBatida e ainda nao "
           "bateu neste loop -> BaterPorta(PortaQuarto). Senao, o fechamento de sempre", x - 40, y - 360, 1500, 1000)
    return br


def patch_gatilho(bp):
    ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
    nodes = list(ge.list_all_nodes())
    for n in nodes:
        if n.get_class().get_name() == "K2Node_CallFunction" and "BaterPorta" in str(n.get_node_title()).replace(" ", ""):
            w("  gatilho ja chama BaterPorta: nada a fazer")
            return False

    def pin_links(n, name, out):
        p = ok_pin(n.find_output_pin(name) if out else n.find_input_pin(name))
        return [q.get_owning_node() for q in p.list_connected_pins()] if p else []

    # s_arm = Set bArmado cujo exec leva a um Branch com Condition ligada a um Get IsClosed
    alvo = None
    for n in nodes:
        if n.get_class().get_name() != "K2Node_VariableSet" or not ok_pin(n.find_input_pin("bArmado")):
            continue
        for nx in pin_links(n, "then", True):
            if nx.get_class().get_name() == "K2Node_IfThenElse":
                cond = pin_links(nx, "Condition", False)
                if cond and ok_pin(cond[0].find_output_pin("IsClosed")):
                    alvo = (n, nx)
    if not alvo:
        raise RuntimeError("nao achei 'bArmado = false -> Branch(IsClosed)' no gatilho; nada foi mudado no EventGraph")
    s_arm, b_fechar = alvo
    ok_pin(s_arm.find_output_pin("then")).break_pin_links()
    inserir_no_gatilho(ge, s_arm, b_fechar, 950, 3000)
    w("  gatilho: Branch da batida inserido entre 'bArmado = false' e o Branch(IsClosed) do fechamento normal")
    return True


def main():
    open(LOG, "w", encoding="utf-8").close()
    try:
        aes = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
        bp = EAL.load_asset(MGR)
        aes.close_all_editors_for_asset(bp)  # editar Blueprint com a janela aberta ja derrubou o editor
        att, cue = ensure_audio()
        ensure_vars(bp, cue)
        build_bater_porta(bp)
        build_impacto(bp, att)
        build_restaurar(bp)
        BEL.compile_blueprint(bp)
        patch_gatilho(bp)
        BEL.compile_blueprint(bp)
        erros = []
        for gname in ("EventGraph", "BaterPorta", "BaterPorta_Impacto", "BaterPorta_Restaurar", "AplicarTag"):
            ge = BGE.get_graph_editor_by_name(bp, gname)
            for kind, lst in (("ERRO", ge.list_nodes_with_errors()), ("aviso", ge.list_nodes_with_warnings())):
                erros += ["%s em %s: %s" % (kind, gname, str(n.get_node_title()).replace("\n", " ")) for n in lst]
        w("compilacao:", erros or "sem erros nem avisos")
        if erros:
            w("NAO SALVEI o manager por causa dos erros acima")
            return
        w("manager salvo:", EAL.save_loaded_asset(bp, False))
    except Exception:
        w("ERRO " + traceback.format_exc())


if __name__ == "__main__":
    main()
