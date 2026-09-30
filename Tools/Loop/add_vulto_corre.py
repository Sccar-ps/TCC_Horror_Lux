# LUX - vulto que corre (pedido do Gabriel, 27/09): silhueta humana PRETA, com aura preta, correndo da esquerda para a
# direita no fim do corredor (loop 2). Dispara junto com o EV_Susto_Vulto (as regras continuam no evento: loop, olhar,
# linha de visao, reserva, gap).
# Como: BP NOVO BP_LuxVultoCorre (nenhum grafo existente e editado). Ele tem um SkeletalMeshComponent "Figura"
# (SKM_Manny_Simple + anim_Jog_Loop_Fwd em loop, material unlit preto, OverlayMaterial = aura), oculto no jogo, sem
# colisao e sem sombra. Um timer de 0,02 s le EV_Susto_Vulto.DisparoT (o Executar do evento grava a hora do disparo);
# quando muda, mostra a figura e a leva de PontoA a PontoB em Duracao s, depois esconde e volta para PontoA.
#   py "<projeto>/Tools/Loop/add_vulto_corre.py" instalar|verificar|desfazer
# Log por operacao (com flush): Saved/LuxSnapshots/vulto_corre_log.txt
import importlib, os, sys, traceback, unreal

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import add_loop_events as ale
importlib.reload(ale)
B, entrada, junc, G = ale.B, ale.entrada, ale.junc, ale.G
KSL, KML, GS = ale.KSL, ale.KML, ale.GS
EAL, BEL, BGE = unreal.EditorAssetLibrary, unreal.BlueprintEditorLibrary, unreal.BlueprintGraphEditor

DIR = ale.DIR
BPP = DIR + "/BP_LuxVultoCorre"
ME = BPP + ".BP_LuxVultoCorre_C"
M_AURA = DIR + "/M_LuxVultoAura"
MI_PRETO = DIR + "/MI_LuxVultoPreto"
SKM = "/Game/FreeAnimationLibrary/Demo/Characters/Mannequins/Meshes/SKM_Manny_Simple"
ANIM = "/Game/FreeAnimationLibrary/Animations/Jog/anim_Jog_Loop_Fwd"  # esqueleto SK_Mannequin, sem root motion
LABEL = "LUX_Vulto_Figura"
EVENTO = "EV_Susto_Vulto"
# caminho: sai de dentro da parede oeste do fim do corredor (x -3450) e some atras da quina leste, passando pelo local
# da silhueta (-3250, -560); da esquerda para a direita de quem vem pelo corredor (olhando para -Y, a direita e +X)
PONTO_A = (-3490.0, -560.0, 0.0)
PONTO_B = (-2950.0, -560.0, 0.0)
DURACAO = 0.6           # ~9 m/s (27/09 21:49: 1.0 -> 0.6, "passa rapido")
TAXA_ANIM = 4.0          # jog acelerado na mesma proporcao (2.4 * 1.0/0.6)
# 27/09 18:22 (teste do Gabriel: "trava no fim e meio que respawna, como se tivessem dois"): o anim_Jog_Loop_Fwd anda
# 3,77 m por ciclo na propria raiz (root motion desligado, raiz livre) e volta ao inicio a cada ciclo. Copia no nosso
# diretorio com ForceRootLock (o asset do pack nao e alterado); quem move a figura e so o ator.
ANIM_LUX = DIR + "/A_LuxVultoJog"
# corpo menos opaco (pedido do Gabriel): unlit, translucido, preto
M_CORPO = DIR + "/M_LuxVultoCorpo"
OPACIDADE_CORPO = 0.35  # 27/09 21:49: 0.6 -> 0.35 (mais sutil, sem sumir)
OPACIDADE_AURA = 0.3    # 0.45 -> 0.3
# luz bem fraca no fundo do caminho, so no loop 2 (tags LOOP2_ON + LOOP3_OFF do LOOP_Manager): com a vela o fundo do
# corredor e preto e o vulto sumiria de vez
LUZ_FUNDO = "LUX_Vulto_LuzFundo"
LUZ_FUNDO_CFG = {"pos": (-3250.0, -1080.0, 110.0), "cd": 0.25, "raio": 450.0, "temperatura": 3500.0}
AURA_CM = 5.0
# passos do vulto (27/09 17:33: "altos e pesados"): SC_LuxVultoPasso = Mixer[ Modulator(pitch 0.72..0.80) <- Random(4 passos
# de madeira mais graves do pack, medidos pela energia abaixo de ~200 Hz), Modulator(pitch 0.5) <- Flashlight_Hit ] com o
# impacto a 0.3. Sem atenuacao propria: o evento toca com a SA_LuxEvento (raio 2 m, some ~20 m). Volume/categoria no evento.
CUE_PASSO = DIR + "/SC_LuxVultoPasso"
MADEIRA = "/Game/FPMovement/Assets/Audio/Character/Footsteps/WaveFiles/Footsteps_Wood/SW_Footsteps_Wood%02d"
PASSOS_GRAVES = (3, 5, 4, 10)
PASSO_PITCH = (0.72, 0.80)
IMPACTO = ("/Game/FPMovement/Assets/Audio/Abilitys/Flashlight/SW_Flashlight_Hit", 0.5, 0.3)  # onda, pitch, volume no mixer
VERSAO = 1
LOG = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "LuxSnapshots", "vulto_corre_log.txt")

# ------------------------------------------------------------------ Loop 1 v2 (30/09, pedido do Bruno)
# O vulto do Loop 1 era a malha estatica SM_LuxVulto com MI_LuxVulto (unlit, emissivo Cor 0,004): no escuro a exposicao trava
# em EV100 -7 com compensacao +1 e multiplica o emissivo por ~213 -> 0,85 = quase BRANCO. Agora o Loop 1 usa a MESMA figura
# do loop 2 (BP_LuxVultoCorre: SKM_Manny_Simple, corpo translucido preto, aura) em instancias NOVAS ligadas aos eventos
# EV_L1_* (os eventos continuam em add_loop_events.py). Preto verdadeiro nao e amplificado pela exposicao; para ser visto
# precisa de FUNDO iluminado (capturas de 30/09: sem fundo a figura some no breu) -> LUX_L1_LuzFundo, luz quente fraca
# dentro do escritorio, so no loop 1, que tambem pisca junto com as arandelas do corredor.
# Modos proprios (NAO chamam ensure_luz_fundo/aplica_figura: nada do loop 2 e tocado):
#   py ".../add_vulto_corre.py" instalar_l1 | verificar_l1 | desfazer_l1
L1_MI = DIR + "/MI_LuxVultoCorpo_L1"
L1_OPACIDADE = 0.5   # loop 2 usa 0,35 (correndo, com luz de fundo); parado a ~11 m, 0,35 e fumaca demais, 0,6 nitido demais
ANIM_IDLE = "/Game/FreeAnimationLibrary/Animations/Idle/anim_Idle"
ANIM_ANDAR_SRC = "/Game/FreeAnimationLibrary/Animations/Walk/anim_Walk_Fwd_Loop_L"
ANIM_ANDAR = DIR + "/A_LuxVultoAndar"   # copia com ForceRootLock (o original anda na propria raiz e "respawna" a cada ciclo)
L1_LUZ = "LUX_L1_LuzFundo"
L1_LUZ_CFG = {"pos": (-3250.0, -1080.0, 110.0), "cd": 0.3, "raio": 450.0, "temperatura": 3200.0}
# figura: label, evento, PontoA, PontoB, Duracao, yaw do ator (a malha olha para o +X do ator), animacao
FIGURAS_L1 = [
    # beat 1: parada no vao do escritorio, encarando quem vem do quarto; aparece no 1o apagao e some no 2o (add_loop_events)
    {"label": "LUX_Vulto_L1_Porta", "evento": "EV_L1_VultoParado", "a": (-3250.0, -700.0, 0.0), "b": (-3250.0, -700.0, 0.0),
     "duracao": 1.97, "yaw": 90.0, "anim": ANIM_IDLE, "tocando": False, "pos": 0.5, "taxa": 0.0},
    # beat 3: sai do vao e vem na direcao da entrada da sala durante os passos; so e vista nas janelas acesas do piscar e
    # some no escuro final (4o passo em 3,9 s; luz volta em 6,4 s)
    {"label": "LUX_Vulto_L1_Passos", "evento": "EV_L1_PassosPesados", "a": (-3250.0, -720.0, 0.0), "b": (-3165.0, -655.0, 0.0),
     "duracao": 4.1, "yaw": 37.4, "anim": ANIM_ANDAR, "tocando": True, "pos": 0.0, "taxa": 0.45},
]


def w(*a):
    line = " ".join(str(x) for x in a)
    unreal.log("[LUX vulto] " + line)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
        fh.flush()


class Aborta(Exception):
    pass


# ------------------------------------------------------------------ materiais
def ensure_materiais():
    MEL = unreal.MaterialEditingLibrary
    at = unreal.AssetToolsHelpers.get_asset_tools()
    novos = []
    if not EAL.does_asset_exist(MI_PRETO):
        w("criando MI_LuxVultoPreto")
        mi = at.create_asset("MI_LuxVultoPreto", DIR, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        mi.set_editor_property("parent", EAL.load_asset(ale.VULTO_M))
        MEL.set_material_instance_vector_parameter_value(mi, "Cor", unreal.LinearColor(0, 0, 0, 1))
        MEL.update_material_instance(mi)
        novos.append(mi)
    if not EAL.does_asset_exist(M_AURA):
        w("criando M_LuxVultoAura")
        m = at.create_asset("M_LuxVultoAura", DIR, unreal.Material, unreal.MaterialFactoryNew())
        m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
        m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
        # WPO = normal * AURA_CM (infla a casca)
        vn = MEL.create_material_expression(m, unreal.MaterialExpressionVertexNormalWS, -700, 300)
        mw = MEL.create_material_expression(m, unreal.MaterialExpressionMultiply, -450, 300)
        mw.set_editor_property("const_b", AURA_CM)
        MEL.connect_material_expressions(vn, "", mw, "A")
        MEL.connect_material_property(mw, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
        # Opacity = 0.7 * (1 - Fresnel)^1.5 (some para fora)
        fr = MEL.create_material_expression(m, unreal.MaterialExpressionFresnel, -900, 0)
        fr.set_editor_property("exponent", 1.5)
        om = MEL.create_material_expression(m, unreal.MaterialExpressionOneMinus, -700, 0)
        MEL.connect_material_expressions(fr, "", om, "")
        pw = MEL.create_material_expression(m, unreal.MaterialExpressionPower, -550, 0)
        pw.set_editor_property("const_exponent", 1.5)
        MEL.connect_material_expressions(om, "", pw, "Base")
        mo = MEL.create_material_expression(m, unreal.MaterialExpressionMultiply, -400, 0)
        mo.set_editor_property("const_b", 0.7)
        MEL.connect_material_expressions(pw, "", mo, "A")
        MEL.connect_material_property(mo, "", unreal.MaterialProperty.MP_OPACITY)
        preto = MEL.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -400, -200)
        preto.set_editor_property("constant", unreal.LinearColor(0, 0, 0, 1))
        MEL.connect_material_property(preto, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        MEL.recompile_material(m)
        novos.append(m)
    return novos


def ensure_v2():
    """Animacao com raiz travada + material translucido do corpo + aura menos opaca."""
    MEL = unreal.MaterialEditingLibrary
    novos = []
    if not EAL.does_asset_exist(ANIM_LUX):
        w("duplicando anim -> A_LuxVultoJog (ForceRootLock)")
        a = EAL.duplicate_asset(ANIM, ANIM_LUX)
        a.set_editor_property("force_root_lock", True)
        novos.append(a)
    a = EAL.load_asset(ANIM_LUX)
    if not a.get_editor_property("force_root_lock"):
        a.set_editor_property("force_root_lock", True)
        novos.append(a)
    if not EAL.does_asset_exist(M_CORPO):
        w("criando M_LuxVultoCorpo")
        m = unreal.AssetToolsHelpers.get_asset_tools().create_asset("M_LuxVultoCorpo", DIR, unreal.Material, unreal.MaterialFactoryNew())
        m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
        m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
        preto = MEL.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -400, -100)
        preto.set_editor_property("constant", unreal.LinearColor(0, 0, 0, 1))
        MEL.connect_material_property(preto, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        op = MEL.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -400, 100)
        op.set_editor_property("parameter_name", "Opacidade")
        op.set_editor_property("default_value", OPACIDADE_CORPO)
        MEL.connect_material_property(op, "", unreal.MaterialProperty.MP_OPACITY)
        MEL.recompile_material(m)
        novos.append(m)
    corpo = EAL.load_asset(M_CORPO)
    op = MEL.get_material_property_input_node(corpo, unreal.MaterialProperty.MP_OPACITY)
    if op and abs(op.get_editor_property("default_value") - OPACIDADE_CORPO) > 1e-6:
        op.set_editor_property("default_value", OPACIDADE_CORPO)
        MEL.recompile_material(corpo)
        novos.append(corpo)
    aura = EAL.load_asset(M_AURA)
    for e in MEL.get_material_property_input_node(aura, unreal.MaterialProperty.MP_OPACITY) and [MEL.get_material_property_input_node(aura, unreal.MaterialProperty.MP_OPACITY)] or []:
        if isinstance(e, unreal.MaterialExpressionMultiply) and abs(e.get_editor_property("const_b") - OPACIDADE_AURA) > 1e-6:
            e.set_editor_property("const_b", OPACIDADE_AURA)
            MEL.recompile_material(aura)
            novos.append(aura)
    return novos


def ensure_luz_fundo():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    lst = [a for a in ale.atores() if a.get_actor_label() == LUZ_FUNDO]
    mud = []
    a = lst[0] if lst else None
    if not a:
        a = eas.spawn_actor_from_class(unreal.PointLight, unreal.Vector(*LUZ_FUNDO_CFG["pos"]), unreal.Rotator())
        a.set_actor_label(LUZ_FUNDO)
        a.set_folder_path(ale.FOLDER)
        mud.append(LUZ_FUNDO)
    c = a.point_light_component
    for k, v in (("mobility", unreal.ComponentMobility.MOVABLE), ("intensity_units", unreal.LightUnits.CANDELAS), ("intensity", LUZ_FUNDO_CFG["cd"]),
                 ("attenuation_radius", LUZ_FUNDO_CFG["raio"]), ("use_temperature", True), ("temperature", LUZ_FUNDO_CFG["temperatura"]),
                 ("cast_shadows", False)):
        if c.get_editor_property(k) != v:
            c.set_editor_property(k, v)
            mud.append("%s.%s" % (LUZ_FUNDO, k))
    tags = [str(t) for t in a.tags]
    quer = [ale.TAG, "LOOP2_ON", "LOOP3_OFF"]
    if sorted(tags) != sorted(quer):
        a.set_editor_property("tags", [unreal.Name(x) for x in quer])
        mud.append("%s tags" % LUZ_FUNDO)
    return mud


def aplica_figura(bp):
    """Template da Figura: animacao com raiz travada, taxa e material translucido (propriedades, sem grafo)."""
    fig = ale.comp_template(bp, "Figura")
    mud = False
    dados = fig.get_editor_property("animation_data")
    if dados.get_editor_property("anim_to_play") != EAL.load_asset(ANIM_LUX) or abs(dados.get_editor_property("saved_play_rate") - TAXA_ANIM) > 1e-6:
        fig.set_editor_property("animation_data", unreal.SingleAnimationPlayData(anim_to_play=EAL.load_asset(ANIM_LUX), saved_looping=True,
                                                                                   saved_playing=True, saved_position=0.0,
                                                                                   saved_play_rate=TAXA_ANIM))
        mud = True
    corpo = EAL.load_asset(M_CORPO)
    mats = list(fig.get_editor_property("override_materials"))
    if any(m_ != corpo for m_ in mats):
        fig.set_editor_property("override_materials", [corpo] * len(mats))
        mud = True
    if mud:
        w("template Figura atualizado (anim %s, taxa %.1f, corpo translucido %.2f)" % (ANIM_LUX, TAXA_ANIM, OPACIDADE_CORPO))
        BEL.compile_blueprint(bp)
    return mud


def ensure_cue():
    if EAL.does_asset_exist(CUE_PASSO):
        return []
    w("criando SC_LuxVultoPasso")
    at = unreal.AssetToolsHelpers.get_asset_tools()
    cue = at.create_asset("SC_LuxVultoPasso", DIR, unreal.SoundCue, unreal.SoundCueFactoryNew())
    rnd = unreal.new_object(unreal.SoundNodeRandom, cue)
    wps = []
    for n in PASSOS_GRAVES:
        wp = unreal.new_object(unreal.SoundNodeWavePlayer, cue)
        wp.set_editor_property("sound_wave", EAL.load_asset(MADEIRA % n))
        wps.append(wp)
    rnd.set_editor_property("child_nodes", wps)
    rnd.set_editor_property("weights", [1.0] * len(wps))
    m1 = unreal.new_object(unreal.SoundNodeModulator, cue)
    for k, v in (("pitch_min", PASSO_PITCH[0]), ("pitch_max", PASSO_PITCH[1]), ("volume_min", 1.0), ("volume_max", 1.0)):
        m1.set_editor_property(k, v)
    m1.set_editor_property("child_nodes", [rnd])
    onda, pit, vol = IMPACTO
    wi = unreal.new_object(unreal.SoundNodeWavePlayer, cue)
    wi.set_editor_property("sound_wave", EAL.load_asset(onda))
    m2 = unreal.new_object(unreal.SoundNodeModulator, cue)
    for k, v in (("pitch_min", pit), ("pitch_max", pit), ("volume_min", 1.0), ("volume_max", 1.0)):
        m2.set_editor_property(k, v)
    m2.set_editor_property("child_nodes", [wi])
    mix = unreal.new_object(unreal.SoundNodeMixer, cue)
    mix.set_editor_property("child_nodes", [m1, m2])
    mix.set_editor_property("input_volume", [1.0, vol])
    cue.set_editor_property("first_node", mix)
    try:
        cue.set_editor_property("all_nodes", [mix, m1, rnd] + wps + [m2, wi])
    except Exception as ex:
        w("  aviso: all_nodes nao exposto (%s)" % ex)
    return [cue]


def ensure_som_evento():
    """EV_Susto_Vulto toca o SC_LuxVultoPasso (o resto da configuracao do evento fica no add_loop_events.py)."""
    ev = ale.por_label(EVENTO)
    cue = EAL.load_asset(CUE_PASSO)
    if ev and ev.get_editor_property("Som") != cue:
        ev.set_editor_property("Som", cue)
        return ["%s.Som" % EVENTO]
    return []


# ------------------------------------------------------------------ BP
def cria_bp():
    w("criando BP_LuxVultoCorre")
    bp = BEL.create_blueprint_asset_with_parent(BPP, unreal.Actor)
    t = ale.tipos_base()
    t["evt"] = BEL.get_object_reference_type(EAL.load_asset(ale.EVT).generated_class())
    w("  componente Figura")
    _, fig = ale.add_comp(bp, unreal.SkeletalMeshComponent, "Figura")
    fig.set_editor_property("skeletal_mesh_asset", EAL.load_asset(SKM))
    fig.set_editor_property("animation_mode", unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    fig.set_editor_property("animation_data", unreal.SingleAnimationPlayData(anim_to_play=EAL.load_asset(ANIM), saved_looping=True,
                                                                               saved_playing=True, saved_position=0.0,
                                                                               saved_play_rate=TAXA_ANIM))
    preto = EAL.load_asset(MI_PRETO)
    n = len(EAL.load_asset(SKM).get_editor_property("materials"))
    fig.set_editor_property("override_materials", [preto] * n)
    fig.set_editor_property("overlay_material", EAL.load_asset(M_AURA))
    fig.set_collision_profile_name("NoCollision")
    fig.set_editor_property("cast_shadow", False)
    fig.set_editor_property("hidden_in_game", True)
    fig.set_editor_property("visibility_based_anim_tick_option", unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE)
    fig.set_editor_property("relative_rotation", unreal.Rotator(0, 0, -90))  # manequim olha para +Y; corre para +X
    vars_ = [("Evento", "evt", True, None), ("PontoA", "vec", True, None), ("PontoB", "vec", True, None),
             ("Duracao", "real", True, DURACAO), ("UltDisparo", "real", False, -1000.0), ("T0", "real", False, 0.0),
             ("bCorrendo", "bool", False, False), ("VersaoCorre", "int", False, 0)]
    w("  variaveis")
    ale.cria_vars(bp, vars_, t, "LUX Vulto")
    BEL.compile_blueprint(bp)
    ale.padroes(bp, [v for v in vars_ if v[3] is not None])
    w("  funcoes")
    ale.cria_funcoes(bp, [("Inicializar", []), ("Atualizar", [])], t)
    BEL.compile_blueprint(bp)

    w("  grafo Inicializar")
    b, en = entrada(bp, "Inicializar", ME)
    bv = b.br(b.valido(b.v("Evento")))
    dt = b.v("DisparoT", cls=ale.EVT_C)
    b.lk(b.v("Evento"), dt[0], "self")
    su = b.setv("UltDisparo", src=dt)
    sl = b.c("/Script/Engine.Actor:K2_SetActorLocation", 0, 0, bSweep="false", bTeleport="true")
    b.lk(b.v("PontoA"), sl, "NewLocation")
    tm = b.timer("Atualizar", 0.02, loop=True)
    b.ch(en, bv)
    b.ch((bv, "then"), su, sl, tm)
    BEL.compile_blueprint(bp)
    w("  Inicializar compilado", ale.erros_bp(bp))

    w("  grafo Atualizar")
    b, en = entrada(bp, "Atualizar", ME)
    b0 = b.br(b.valido(b.v("Evento")))
    dt = b.v("DisparoT", cls=ale.EVT_C)
    b.lk(b.v("Evento"), dt[0], "self")
    b1 = b.br(b.op("NotEqual_DoubleDouble", dt, b.v("UltDisparo")))
    dt2 = b.v("DisparoT", cls=ale.EVT_C)
    b.lk(b.v("Evento"), dt2[0], "self")
    s_ult = b.setv("UltDisparo", src=dt2)
    s_t0 = b.setv("T0", src=b.now())
    s_run = b.setv("bCorrendo", "true")
    mostra = b.c("/Script/Engine.SceneComponent:SetHiddenInGame", 0, 0, NewHidden="false")
    b.lk(b.v("Figura"), mostra, "self")
    j1 = junc(b)
    b2 = b.br(b.v("bCorrendo"))
    alfa_div = b.c(KML + "SafeDivide", 0, 0)
    b.lk(b.menos_agora("T0"), alfa_div, "A")
    b.lk(b.v("Duracao"), alfa_div, "B")
    alfa = b.c(KML + "FClamp", 0, 0, Min=0.0, Max=1.0)
    b.lk((alfa_div, "ReturnValue"), alfa, "Value")
    lerp = b.c(KML + "VLerp", 0, 0)
    b.lk(b.v("PontoA"), lerp, "A")
    b.lk(b.v("PontoB"), lerp, "B")
    b.lk((alfa, "ReturnValue"), lerp, "Alpha")
    sl = b.c("/Script/Engine.Actor:K2_SetActorLocation", 0, 0, bSweep="false", bTeleport="true")
    b.lk((lerp, "ReturnValue"), sl, "NewLocation")
    b3 = b.br(b.op("GreaterEqual_DoubleDouble", (alfa, "ReturnValue"), 1.0))
    s_fim = b.setv("bCorrendo", "false")
    esconde = b.c("/Script/Engine.SceneComponent:SetHiddenInGame", 0, 0, NewHidden="true")
    b.lk(b.v("Figura"), esconde, "self")
    volta = b.c("/Script/Engine.Actor:K2_SetActorLocation", 0, 0, bSweep="false", bTeleport="true")
    b.lk(b.v("PontoA"), volta, "NewLocation")
    b.ch(en, b0)
    b.ch((b0, "then"), b1)
    b.ch((b1, "then"), s_ult, s_t0, s_run, mostra, j1)
    b.ch((b1, "else"), j1)
    b.ch((j1, "then"), b2)
    b.ch((b2, "then"), sl, b3)
    b.ch((b3, "then"), s_fim, esconde, volta)
    BEL.compile_blueprint(bp)
    w("  Atualizar compilado", ale.erros_bp(bp))

    w("  EventGraph")
    ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
    g = G(ge)
    bpl = g.pos(BEL.add_event_override(bp, "ReceiveBeginPlay", unreal.IntPoint(0, 0)), 0, 0)
    g.chain(bpl, g.call(ME + ":Inicializar", 300, 0))
    BEL.compile_blueprint(bp)
    e = ale.erros_bp(bp)
    if e:
        raise Aborta("BP_LuxVultoCorre com erros/avisos (nada salvo): %s" % e)
    unreal.get_default_object(bp.generated_class()).set_editor_property("VersaoCorre", VERSAO)
    BEL.compile_blueprint(bp)
    w("  BP limpo")
    return bp


def ensure_bp():
    if EAL.does_asset_exist(BPP):
        bp = EAL.load_asset(BPP)
        if unreal.get_default_object(bp.generated_class()).get_editor_property("VersaoCorre") != VERSAO:
            raise Aborta("BP_LuxVultoCorre existe sem VersaoCorre=%d: estado incompleto (feche o editor sem salvar)" % VERSAO)
        w("BP v%d ja existe: mantido" % VERSAO)
        return bp, False
    return cria_bp(), True


def ensure_ator(bp):
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    lst = [a for a in ale.atores() if a.get_actor_label() == LABEL]
    if len(lst) > 1:
        raise Aborta("mais de um %s" % LABEL)
    a = lst[0] if lst else None
    mud = []
    if not a:
        a = eas.spawn_actor_from_class(bp.generated_class(), unreal.Vector(*PONTO_A), unreal.Rotator())
        a.set_actor_label(LABEL)
        a.set_folder_path(ale.FOLDER)
        a.set_editor_property("tags", [unreal.Name(ale.TAG)])
        mud.append(LABEL)
    ev = ale.por_label(EVENTO)
    if not ev:
        raise Aborta("%s nao encontrado" % EVENTO)
    for k, v in (("Evento", ev), ("PontoA", unreal.Vector(*PONTO_A)), ("PontoB", unreal.Vector(*PONTO_B)), ("Duracao", DURACAO)):
        atual = a.get_editor_property(k)
        if atual != v:
            a.set_editor_property(k, v)
            mud.append("%s.%s" % (LABEL, k))
    if (a.get_actor_location() - unreal.Vector(*PONTO_A)).length() > 0.5:
        a.set_actor_location(unreal.Vector(*PONTO_A), False, True)
        mud.append("%s posicao" % LABEL)
    return a, mud


def verificar():
    falhas = []
    if not EAL.does_asset_exist(BPP):
        return ["BP ausente"]
    bp = EAL.load_asset(BPP)
    falhas += ale.erros_bp(bp)
    for nome in ("Inicializar", "Atualizar"):
        if nome not in [str(x) for x in BEL.list_graph_names(bp)] or len(list(BGE.get_graph_editor_by_name(bp, nome).list_all_nodes())) < 3:
            falhas.append("funcao %s ausente/vazia" % nome)
    lst = [a for a in ale.atores() if a.get_actor_label() == LABEL]
    if len(lst) != 1:
        return falhas + ["esperava 1 %s (%d)" % (LABEL, len(lst))]
    a = lst[0]
    fig = a.get_components_by_class(unreal.SkeletalMeshComponent)[0]
    if not fig.get_editor_property("hidden_in_game"):
        falhas.append("Figura visivel no jogo por padrao")
    if fig.get_collision_profile_name() != "NoCollision" or fig.get_editor_property("cast_shadow"):
        falhas.append("Figura com colisao ou sombra")
    if not fig.get_editor_property("overlay_material"):
        falhas.append("Figura sem aura (OverlayMaterial)")
    anim = fig.get_editor_property("animation_data").get_editor_property("anim_to_play")
    if not anim or not anim.get_editor_property("force_root_lock"):
        falhas.append("animacao da Figura sem raiz travada (a figura 'respawna' a cada ciclo)")
    if abs(a.get_editor_property("Duracao") - DURACAO) > 1e-6:
        falhas.append("Duracao da corrida != %.1f" % DURACAO)
    lf = [x for x in ale.atores() if x.get_actor_label() == LUZ_FUNDO]
    if len(lf) != 1 or sorted(str(t) for t in lf[0].tags) != sorted([ale.TAG, "LOOP2_ON", "LOOP3_OFF"]):
        falhas.append("%s ausente ou sem as tags de loop (so no loop 2)" % LUZ_FUNDO)
    ev = a.get_editor_property("Evento")
    if not ev or ev.get_actor_label() != EVENTO:
        falhas.append("Evento nao aponta para %s" % EVENTO)
    elif ev.get_editor_property("bAparicao"):
        falhas.append("%s ainda com bAparicao (silhueta estatica)" % EVENTO)
    elif not EAL.does_asset_exist(CUE_PASSO) or ev.get_editor_property("Som") != EAL.load_asset(CUE_PASSO):
        falhas.append("%s nao toca o SC_LuxVultoPasso" % EVENTO)
    w("verificar:", ("FAIL %s" % falhas) if falhas else "PASS")
    return falhas


def instalar():
    if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():
        raise Aborta("feche o PIE")
    novos = ensure_materiais() + ensure_cue() + ensure_v2()
    bp, criou = ensure_bp()
    if aplica_figura(bp):
        criou = True
    a, mud = ensure_ator(bp)
    mud += ensure_som_evento()
    mud += ensure_luz_fundo()
    w("mudou:", mud or "nada")
    f = verificar()
    if f:
        raise Aborta("verificar FAIL (nada salvo): %s" % f)
    for x in novos + ([bp] if criou or bp.get_outermost().get_name() in ale.sujos() else []):
        w("salvo", x.get_path_name(), EAL.save_loaded_asset(x, False))
    U = unreal.EditorLoadingAndSavingUtils
    mapa = [p for p in U.get_dirty_map_packages() if p.get_name() == "/Game/Masion/Mapa_B"]
    if mapa:
        w("salvo Mapa_B", U.save_packages(mapa, True))


def desfazer():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in [a for a in ale.atores() if a.get_actor_label() in (LABEL, LUZ_FUNDO)]:
        eas.destroy_actor(a)
    U = unreal.EditorLoadingAndSavingUtils
    U.save_packages([p for p in U.get_dirty_map_packages() if p.get_name() == "/Game/Masion/Mapa_B"], True)
    w("figura removida do mapa; BP, materiais e SC_LuxVultoPasso ficam em %s. O EV_Susto_Vulto continua com bAparicao "
      "false (sem vulto visivel, so os passos); para a silhueta parada voltar, bAparicao=True no plano do add_loop_events.py" % DIR)


# ------------------------------------------------------------------ Loop 1 v2
def ensure_l1_assets():
    MEL = unreal.MaterialEditingLibrary
    novos = []
    if not EAL.does_asset_exist(L1_MI):
        w("criando MI_LuxVultoCorpo_L1")
        mi = unreal.AssetToolsHelpers.get_asset_tools().create_asset("MI_LuxVultoCorpo_L1", DIR, unreal.MaterialInstanceConstant,
                                                                      unreal.MaterialInstanceConstantFactoryNew())
        mi.set_editor_property("parent", EAL.load_asset(M_CORPO))
        novos.append(mi)
    mi = EAL.load_asset(L1_MI)
    if abs(MEL.get_material_instance_scalar_parameter_value(mi, "Opacidade") - L1_OPACIDADE) > 1e-6:
        MEL.set_material_instance_scalar_parameter_value(mi, "Opacidade", L1_OPACIDADE)
        MEL.update_material_instance(mi)
        if mi not in novos:
            novos.append(mi)
    if not EAL.does_asset_exist(ANIM_ANDAR):
        w("duplicando anim -> A_LuxVultoAndar (ForceRootLock)")
        EAL.duplicate_asset(ANIM_ANDAR_SRC, ANIM_ANDAR)
    a = EAL.load_asset(ANIM_ANDAR)
    if not a.get_editor_property("force_root_lock"):
        a.set_editor_property("force_root_lock", True)
        novos.append(a)
    return novos


def ensure_l1_luz():
    """Luz quente fraca no escritorio, so no loop 1 (LOOP1_ON/LOOP2_OFF), piscando com as arandelas (tag do corredor).
    Cor por temperatura, nao por light_color: o verificar dos eventos reprova luz de piscar avermelhada (fotossensibilidade)."""
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    lst = [x for x in ale.atores() if x.get_actor_label() == L1_LUZ]
    mud = []
    a = lst[0] if lst else None
    if not a:
        a = eas.spawn_actor_from_class(unreal.PointLight, unreal.Vector(*L1_LUZ_CFG["pos"]), unreal.Rotator())
        a.set_actor_label(L1_LUZ)
        a.set_folder_path(ale.FOLDER)
        mud.append(L1_LUZ)
    if (a.get_actor_location() - unreal.Vector(*L1_LUZ_CFG["pos"])).length() > 0.5:
        a.set_actor_location(unreal.Vector(*L1_LUZ_CFG["pos"]), False, True)
        mud.append("%s posicao" % L1_LUZ)
    c = a.point_light_component
    for k, v in (("mobility", unreal.ComponentMobility.MOVABLE), ("intensity_units", unreal.LightUnits.CANDELAS), ("intensity", L1_LUZ_CFG["cd"]),
                 ("attenuation_radius", L1_LUZ_CFG["raio"]), ("use_temperature", True), ("temperature", L1_LUZ_CFG["temperatura"]),
                 ("cast_shadows", True)):  # com sombra: sem ela a luz atravessa a parede e acende o piano da sala (~2,75 m)
        atual = c.get_editor_property(k)
        if (abs(atual - v) > 1e-4) if isinstance(v, float) else (atual != v):
            c.set_editor_property(k, v)
            mud.append("%s.%s" % (L1_LUZ, k))
    quer = [ale.TAG, "LOOP1_ON", "LOOP2_OFF", ale.TAG_CORREDOR]
    if sorted(str(t) for t in a.tags) != sorted(quer):
        a.set_editor_property("tags", [unreal.Name(x) for x in quer])
        mud.append("%s tags" % L1_LUZ)
    return mud


def ensure_l1_figuras(bp):
    """Instancias NOVAS de BP_LuxVultoCorre (o grafo e o template nao mudam): Evento, PontoA/B, Duracao e, na Figura DESTA
    instancia, animacao e material (sobrescrita por instancia, salva no mapa)."""
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    mi = EAL.load_asset(L1_MI)
    mud = []
    for cfg in FIGURAS_L1:
        lst = [x for x in ale.atores() if x.get_actor_label() == cfg["label"]]
        if len(lst) > 1:
            raise Aborta("mais de um %s" % cfg["label"])
        a = lst[0] if lst else None
        if not a:
            a = eas.spawn_actor_from_class(bp.generated_class(), unreal.Vector(*cfg["a"]), unreal.Rotator(0.0, 0.0, cfg["yaw"]))
            a.set_actor_label(cfg["label"])
            a.set_folder_path(ale.FOLDER)
            a.set_editor_property("tags", [unreal.Name(ale.TAG)])
            mud.append(cfg["label"])
        ev = ale.por_label(cfg["evento"])
        if not ev:
            raise Aborta("%s nao encontrado (rode add_loop_events.py instalar)" % cfg["evento"])
        for k, v in (("Evento", ev), ("PontoA", unreal.Vector(*cfg["a"])), ("PontoB", unreal.Vector(*cfg["b"])), ("Duracao", cfg["duracao"])):
            atual = a.get_editor_property(k)
            if (abs(atual - v) > 1e-6) if isinstance(v, float) else (atual != v):
                a.set_editor_property(k, v)
                mud.append("%s.%s" % (cfg["label"], k))
        if (a.get_actor_location() - unreal.Vector(*cfg["a"])).length() > 0.5 or abs(a.get_actor_rotation().yaw - cfg["yaw"]) > 0.1:
            a.set_actor_location_and_rotation(unreal.Vector(*cfg["a"]), unreal.Rotator(0.0, 0.0, cfg["yaw"]), False, True)
            mud.append("%s transform" % cfg["label"])
        fig = a.get_components_by_class(unreal.SkeletalMeshComponent)[0]
        anim = EAL.load_asset(cfg["anim"])
        dados = fig.get_editor_property("animation_data")
        if (dados.get_editor_property("anim_to_play") != anim or dados.get_editor_property("saved_playing") != cfg["tocando"]
                or abs(dados.get_editor_property("saved_play_rate") - cfg["taxa"]) > 1e-6
                or abs(dados.get_editor_property("saved_position") - cfg["pos"]) > 1e-6):
            fig.set_editor_property("animation_data", unreal.SingleAnimationPlayData(anim_to_play=anim, saved_looping=True,
                                                                                       saved_playing=cfg["tocando"], saved_position=cfg["pos"],
                                                                                       saved_play_rate=cfg["taxa"]))
            mud.append("%s anim" % cfg["label"])
        mats = list(fig.get_editor_property("override_materials"))
        if not mats or any(m_ != mi for m_ in mats):
            fig.set_editor_property("override_materials", [mi] * max(1, len(mats)))
            mud.append("%s material" % cfg["label"])
    return mud


def verificar_l1():
    f = []
    if not EAL.does_asset_exist(L1_MI) or not EAL.does_asset_exist(ANIM_ANDAR):
        return ["assets do Loop 1 ausentes (MI_LuxVultoCorpo_L1 / A_LuxVultoAndar)"]
    mi = EAL.load_asset(L1_MI)
    if mi.get_editor_property("parent") != EAL.load_asset(M_CORPO):
        f.append("MI_LuxVultoCorpo_L1 nao deriva de M_LuxVultoCorpo (corpo preto translucido)")
    if not EAL.load_asset(ANIM_ANDAR).get_editor_property("force_root_lock"):
        f.append("A_LuxVultoAndar sem ForceRootLock")
    luz = [x for x in ale.atores() if x.get_actor_label() == L1_LUZ]
    if len(luz) != 1:
        f.append("esperava 1 %s (%d)" % (L1_LUZ, len(luz)))
    else:
        if sorted(str(t) for t in luz[0].tags) != sorted([ale.TAG, "LOOP1_ON", "LOOP2_OFF", ale.TAG_CORREDOR]):
            f.append("%s sem as tags LOOP1_ON/LOOP2_OFF/%s" % (L1_LUZ, ale.TAG_CORREDOR))
        if "MOVABLE" not in str(luz[0].point_light_component.get_editor_property("mobility")):
            f.append("%s nao e Movable" % L1_LUZ)
    for cfg in FIGURAS_L1:
        lst = [x for x in ale.atores() if x.get_actor_label() == cfg["label"]]
        if len(lst) != 1:
            f.append("esperava 1 %s (%d)" % (cfg["label"], len(lst)))
            continue
        a = lst[0]
        fig = a.get_components_by_class(unreal.SkeletalMeshComponent)[0]
        ev = a.get_editor_property("Evento")
        if not ev or ev.get_actor_label() != cfg["evento"]:
            f.append("%s: Evento nao aponta para %s" % (cfg["label"], cfg["evento"]))
        elif ev.get_editor_property("bAparicao"):
            f.append("%s ainda com bAparicao (a silhueta estatica branca voltaria)" % cfg["evento"])
        if not fig.get_editor_property("hidden_in_game"):
            f.append("%s: Figura visivel no jogo por padrao" % cfg["label"])
        if fig.get_collision_profile_name() != "NoCollision" or fig.get_editor_property("cast_shadow"):
            f.append("%s: Figura com colisao ou sombra" % cfg["label"])
        if not fig.get_editor_property("overlay_material"):
            f.append("%s: Figura sem aura" % cfg["label"])
        if any(m_ != mi for m_ in fig.get_editor_property("override_materials")):
            f.append("%s: material do corpo != MI_LuxVultoCorpo_L1" % cfg["label"])
        if fig.get_editor_property("animation_data").get_editor_property("anim_to_play") != EAL.load_asset(cfg["anim"]):
            f.append("%s: animacao != %s" % (cfg["label"], cfg["anim"]))
        if abs(a.get_editor_property("Duracao") - cfg["duracao"]) > 1e-6:
            f.append("%s: Duracao %.2f != %.2f" % (cfg["label"], a.get_editor_property("Duracao"), cfg["duracao"]))
    lf = [x for x in ale.atores() if x.get_actor_label() == LUZ_FUNDO]
    if lf and sorted(str(t) for t in lf[0].tags) != sorted([ale.TAG, "LOOP2_ON", "LOOP3_OFF"]):
        f.append("%s (loop 2) teve as tags alteradas" % LUZ_FUNDO)
    w("verificar_l1:", ("FAIL %s" % f) if f else "PASS")
    return f


def instalar_l1():
    if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():
        raise Aborta("feche o PIE")
    if ale.sujos():
        raise Aborta("ha pacotes nao salvos antes de comecar: %s" % ale.sujos())
    bp, _ = ensure_bp()
    novos = ensure_l1_assets()
    mud = ensure_l1_luz() + ensure_l1_figuras(bp)
    w("mudou (loop 1):", mud or "nada")
    f = verificar_l1()
    if f:
        raise Aborta("verificar_l1 FAIL (nada salvo): %s" % f)
    for x in novos:
        w("salvo", x.get_path_name(), EAL.save_loaded_asset(x, False))
    U = unreal.EditorLoadingAndSavingUtils
    mapa = [p for p in U.get_dirty_map_packages() if p.get_name() == "/Game/Masion/Mapa_B"]
    if mapa:
        w("salvo Mapa_B", U.save_packages(mapa, True))
    extra = [p for p in ale.sujos() if p != "/Game/Masion/Mapa_B"]
    if extra:
        w("aviso: pacotes ainda sujos:", extra)


def desfazer_l1():
    """Tira so o que e do Loop 1 v2 (figuras e luz). Os assets (MI, anim) ficam; o loop 2 nao e tocado."""
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    alvo = [c["label"] for c in FIGURAS_L1] + [L1_LUZ]
    for a in [a for a in ale.atores() if a.get_actor_label() in alvo]:
        eas.destroy_actor(a)
    U = unreal.EditorLoadingAndSavingUtils
    U.save_packages([p for p in U.get_dirty_map_packages() if p.get_name() == "/Game/Masion/Mapa_B"], True)
    w("Loop 1 v2 removido do mapa (%s)" % ", ".join(alvo))


def main():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    open(LOG, "w", encoding="utf-8").close()
    modos = ("instalar", "verificar", "desfazer", "instalar_l1", "verificar_l1", "desfazer_l1")
    modo = next((x for x in sys.argv[1:] if x in modos), "verificar")
    w("modo:", modo)
    try:
        {"instalar": instalar, "verificar": verificar, "desfazer": desfazer, "instalar_l1": instalar_l1,
         "verificar_l1": verificar_l1, "desfazer_l1": desfazer_l1}[modo]()
    except Aborta as ex:
        w("ABORTADO:", ex, "| sujos:", ale.sujos())
    except Exception:
        w("ERRO " + traceback.format_exc(), "| sujos:", ale.sujos())


if __name__ == "__main__":
    main()
