# LUX - vulto que corre (pedido do Gabriel, 27/09): silhueta humana PRETA, com aura preta, correndo da esquerda para a
# direita no fim do corredor (loop 2). Dispara junto com o EV_Susto_Vulto (as regras continuam no evento: loop, olhar,
# linha de visao, reserva, gap).
# Como: BP NOVO BP_LuxVultoCorre (nenhum grafo existente e editado). Ele tem um SkeletalMeshComponent "Figura"
# (SKM_Manny_Simple + anim_Jog_Loop_Fwd em loop, material unlit preto, OverlayMaterial = aura), oculto no jogo, sem
# colisao e sem sombra. Um timer de 0,02 s le EV_Susto_Vulto.DisparoT (o Executar do evento grava a hora do disparo);
# quando muda, mostra a figura e a leva de PontoA a PontoB em Duracao s, depois esconde e volta para PontoA.
#   py "<projeto>/Tools/Loop/add_vulto_corre.py" instalar|verificar|desfazer
# Loop 1 (30/09): instalar_l1|verificar_l1|desfazer_l1 (rode DEPOIS do add_loop_events.py instalar). v3 = BP_LuxVultoQuadros
#   (vulto por quadros ancorados no piscar do evento) + M_LuxVultoSombra; nada do loop 2 e tocado.
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
# v2 usava MI_LuxVultoCorpo_L1 (corpo chapado, opacidade 0,5) e BP_LuxVultoCorre (so interpola de A a B: a figura dos passos
# deslizava ~1 m em 4,1 s). A v3 (abaixo) substitui as duas pecas; o instalar_l1 troca as figuras v2 que encontrar no mapa.
ANIM_IDLE = "/Game/FreeAnimationLibrary/Animations/Idle/anim_Idle"
ANIM_ANDAR_SRC = "/Game/FreeAnimationLibrary/Animations/Walk/anim_Walk_Fwd_Loop_L"
ANIM_ANDAR = DIR + "/A_LuxVultoAndar"   # copia com ForceRootLock (o original anda na propria raiz e "respawna" a cada ciclo)
# luzes so do Loop 1 (LOOP1_ON/LOOP2_OFF), piscando com as arandelas (tag do corredor). Preto translucido so aparece contra
# fundo iluminado:
#  - LUX_L1_LuzFundo (v2, Bruno): dentro do escritorio; e o fundo do vulto do vao, visto do corredor.
#  - LUX_L1_LuzPassos (v3): lado oeste da juncao corredor/escritorio. Visto da entrada da sala (S1), o fundo da figura dos
#    passos e a parede oeste da juncao (4,6-5,8 m), que estava no breu: no PIE de 30/09 a figura estava no quadro (desvio de
#    4-17 graus, 2,8-3,6 m) e nao aparecia em nenhuma janela acesa. Junto ao batente oeste do vao (CutPart10): acende o
#    batente, a parede oeste e o chao, que sao o fundo de P0-P2 vistos da S1.
L1_LUZES = {
    "LUX_L1_LuzFundo": {"pos": (-3250.0, -1080.0, 110.0), "cd": 0.3, "raio": 450.0, "temperatura": 3200.0},
    "LUX_L1_LuzPassos": {"pos": (-3300.0, -660.0, 230.0), "cd": 0.15, "raio": 400.0, "temperatura": 3200.0},
}

# ------------------------------------------------------------------ Loop 1 v3 (30/09, polimento: medo, tensao, confusao de Santos)
# O vulto do Loop 1 so existe "entre as piscadas": aparece no escuro, e visto parado contra a luz e muda de lugar no escuro.
# Peca nova BP_LuxVultoQuadros (BP NOVO; o BP_LuxVultoCorre do loop 2 nao muda): le o DisparoT do evento por um timer de vigia
# de 0,05 s e, quando ele muda, executa QUADROS ancorados no DisparoT (Tempos/Posicoes/Poses/Yaws): em cada quadro teleporta,
# congela a pose (SetPosition) e vira o rosto para a camera do jogador; esconde em DuracaoS. Os quadros vao por timer (sem Tick).
# Visual "sombra viva" (M_LuxVultoSombra, unlit translucido, emissivo 0: a exposicao do escuro nao a clareia): opacidade com
# borda que se desfaz (Fresnel), fumaca subindo por dentro (ruido 3D em espaco de mundo) e contorno que treme em degraus
# (WPO pela normal, ruido trocado 8 vezes por segundo), corpo 7 % mais alto e mais magro que o manequim (escala da Figura).
BPQ = DIR + "/BP_LuxVultoQuadros"
MEQ = BPQ + ".BP_LuxVultoQuadros_C"
VERSAO_QUADROS = 1
M_SOMBRA = DIR + "/M_LuxVultoSombra"
MI_SOMBRA_L1 = DIR + "/MI_LuxVultoSombra_L1"
# parametros (o material nasce com estes padroes; a MI do Loop 1 guarda os valores em uso)
SOMBRA_L1 = {"Opacidade": 0.65, "Borda": 0.7, "BordaExpoente": 2.0, "Fumaca": 0.4, "EscalaFumaca": 0.015, "VelFumaca": 18.0,
             "Tremor": 2.0, "TaxaTremor": 8.0, "EscalaTremor": 0.02}
ESCALA_FIGURA = (0.93, 0.95, 1.07)   # malha: X ombros, Y profundidade, Z altura (~1,93 m): alta e magra demais
CAPSULA = (28.0, 88.0)               # raio e meia-altura da checagem de folga da figura (canal Visibility)
MARGEM_ESCURO = 0.06                 # s: quadro e sumico precisam cair dentro de um apagao com esta folga (vigia 0,05 s + 1 quadro)
# s depois do INICIO do apagao: o piscar do evento e uma corrente de timers relativos (cada passo agenda o proximo) e atrasa ate
# 1 quadro por passo; os quadros do vulto sao ancorados no DisparoT. Medido no PIE a ~3 quadros/s (editor em 2o plano): o
# piscar atrasou 0,37 s no 3o passo e a figura saltou com a luz acesa. A 60 FPS o atraso fica em ~0,1 s nos 6 passos.
MARGEM_INICIO = 0.08
P_DIR = 0.333                        # pose de contato com o pe DIREITO a frente (anim_Walk_Fwd_Loop_L: 56,7 cm de passada)
P_ESQ = 0.800                        # pose de contato com o pe ESQUERDO a frente (56,9 cm)
# Pontos: fonte unica em add_loop_events.py (L1_VAO, L1_PASSOS), que tambem poe o som e o alvo do olhar dos eventos neles.
# no_claro: indices de quadro que PODEM cair na luz acesa (o tranco do vao e de proposito); o resto tem de cair no escuro.
FIGURAS_L1 = [
    # beat 1: no vao do escritorio, encarando quem vem do quarto. Aparece no 1o apagao (t 0), e vista contra a LUX_L1_LuzFundo;
    # no estalo do meio (0,925 s, luz acesa) da um tranco para o eixo do corredor, na direcao do jogador; some no 2o apagao
    {"label": "LUX_Vulto_L1_Porta", "evento": "EV_L1_VultoParado", "anim": ANIM_IDLE, "tempos": [0.0, 0.925],
     "posicoes": [(x, y, 0.0) for x, y in ale.L1_VAO], "poses": [0.5, 2.9], "yaws": [90.0, 90.0], "duracao": 1.97, "no_claro": [1]},
    # beat 3: sai do vao rumo a entrada da sala. Cada passo (inicio de cada apagao, 0 / 1,3 / 2,6 s) leva a figura 55 cm adiante
    # 0,1 s depois (folga para o atraso do piscar, MARGEM_INICIO); nas janelas acesas ela esta congelada no meio da passada (pe da
    # frente alternando) e cada vez mais perto; some 0,4 s dentro do escuro final (4o passo em 3,9 s, so som, em L1_PASSOS[3]);
    # a luz volta em 6,4 s e nao ha ninguem
    {"label": "LUX_Vulto_L1_Passos", "evento": "EV_L1_PassosPesados", "anim": ANIM_ANDAR, "tempos": [0.0, 1.4, 2.7],
     "posicoes": [(x, y, 0.0) for x, y in ale.L1_PASSOS[:3]], "poses": [P_ESQ, P_DIR, P_ESQ], "yaws": [37.2, 37.2, 37.2],
     "duracao": 4.3, "no_claro": []},
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


# ------------------------------------------------------------------ Loop 1 v3
VIS = unreal.TraceTypeQuery.ECC_VISIBILITY if hasattr(unreal.TraceTypeQuery, "ECC_VISIBILITY") else unreal.TraceTypeQuery.TRACE_TYPE_QUERY1


def igual(a, b):
    if isinstance(b, float):
        return abs(a - b) < 1e-6
    if isinstance(b, list):
        a = list(a)
        return len(a) == len(b) and all(igual(x, y) for x, y in zip(a, b))
    if isinstance(b, unreal.Vector):
        return (a - b).length() < 1e-3
    return a == b


def cria_sombra():
    """'Sombra viva' (unlit, translucido, emissivo 0). Opacidade = Opacidade x lerp(1, 1 - Fresnel, Borda) x lerp(1 - Fumaca, 1,
    ruido subindo a VelFumaca cm/s); WPO = normal x ruido trocado TaxaTremor vezes por segundo x Tremor (cm)."""
    MEL = unreal.MaterialEditingLibrary
    w("criando M_LuxVultoSombra")
    m = unreal.AssetToolsHelpers.get_asset_tools().create_asset("M_LuxVultoSombra", DIR, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property("used_with_skeletal_mesh", True)

    def ex(cls, x, y, **props):
        n = MEL.create_material_expression(m, cls, x, y)
        for k, v in props.items():
            n.set_editor_property(k, v)
        return n

    def par(nome, x, y):
        return ex(unreal.MaterialExpressionScalarParameter, x, y, parameter_name=nome, default_value=SOMBRA_L1[nome])

    def liga(a, b, pino=""):
        if not MEL.connect_material_expressions(a, "", b, pino):
            raise Aborta("M_LuxVultoSombra: ligacao falhou -> %s.%s" % (b.get_class().get_name(), pino))

    def bin_(cls, a, b, x, y):
        n = ex(cls, x, y)
        liga(a, n, "A")
        liga(b, n, "B")
        return n

    def mul(a, b, x, y):
        return bin_(unreal.MaterialExpressionMultiply, a, b, x, y)

    preto = ex(unreal.MaterialExpressionConstant3Vector, -400, -300, constant=unreal.LinearColor(0, 0, 0, 1))
    MEL.connect_material_property(preto, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    # borda que se desfaz: no centro do corpo a opacidade e cheia; no contorno cai (a silhueta nao tem linha dura)
    fr = ex(unreal.MaterialExpressionFresnel, -1300, 0)
    liga(par("BordaExpoente", -1500, 0), fr, "ExponentIn")
    om = ex(unreal.MaterialExpressionOneMinus, -1150, 0)
    liga(fr, om)
    lb = ex(unreal.MaterialExpressionLinearInterpolate, -950, 0, const_a=1.0)
    liga(om, lb, "B")
    liga(par("Borda", -1150, 120), lb, "Alpha")
    # fumaca subindo por dentro do corpo (ruido 3D em espaco de mundo, deslocado para cima com o tempo)
    esc = par("EscalaFumaca", -1900, 420)
    pf = mul(ex(unreal.MaterialExpressionWorldPosition, -1900, 300), esc, -1700, 300)
    tv = mul(mul(ex(unreal.MaterialExpressionTime, -1900, 540), par("VelFumaca", -1900, 640), -1700, 540), esc, -1550, 540)
    sobe = mul(tv, ex(unreal.MaterialExpressionConstant3Vector, -1550, 660, constant=unreal.LinearColor(0, 0, 1, 0)), -1400, 540)
    sub = bin_(unreal.MaterialExpressionSubtract, pf, sobe, -1250, 300)
    nz = ex(unreal.MaterialExpressionNoise, -1050, 300, noise_function=unreal.NoiseFunction.NOISEFUNCTION_GRADIENT_TEX3D, scale=1.0,
            quality=1, turbulence=True, levels=3, level_scale=2.0, output_min=0.0, output_max=1.0)
    liga(sub, nz, "World Position")   # o pino do Noise chama "World Position" (nao "Position")
    omf = ex(unreal.MaterialExpressionOneMinus, -1050, 480)
    liga(par("Fumaca", -1250, 480), omf)
    lf = ex(unreal.MaterialExpressionLinearInterpolate, -850, 300, const_b=1.0)
    liga(omf, lf, "A")
    liga(nz, lf, "Alpha")
    sat = ex(unreal.MaterialExpressionSaturate, -450, 100)
    liga(mul(mul(par("Opacidade", -950, -150), lb, -750, 0), lf, -600, 100), sat)
    MEL.connect_material_property(sat, "", unreal.MaterialProperty.MP_OPACITY)
    # contorno que treme em degraus (a figura "ferve", nao e solida): ruido pela normal, trocado TaxaTremor vezes por segundo
    wp = ex(unreal.MaterialExpressionWorldPosition, -1900, 900,
            world_position_shader_offset=unreal.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    q = mul(wp, par("EscalaTremor", -1900, 1020), -1700, 900)
    fl = ex(unreal.MaterialExpressionFloor, -1550, 1140)
    liga(mul(ex(unreal.MaterialExpressionTime, -1900, 1140), par("TaxaTremor", -1900, 1240), -1700, 1140), fl)
    k = ex(unreal.MaterialExpressionConstant3Vector, -1550, 1260, constant=unreal.LinearColor(0.37, 0.61, 0.83, 0))
    pos = bin_(unreal.MaterialExpressionAdd, q, mul(fl, k, -1400, 1140), -1250, 900)
    nt = ex(unreal.MaterialExpressionNoise, -1050, 900, noise_function=unreal.NoiseFunction.NOISEFUNCTION_GRADIENT_ALU, scale=1.0,
            quality=1, turbulence=False, levels=1, output_min=-1.0, output_max=1.0)
    liga(pos, nt, "World Position")
    wpo = mul(mul(ex(unreal.MaterialExpressionVertexNormalWS, -1050, 1100), nt, -850, 1000), par("Tremor", -1050, 1200), -650, 1000)
    MEL.connect_material_property(wpo, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    MEL.recompile_material(m)
    return m


def ensure_l1_assets():
    """A_LuxVultoAndar (passada com raiz travada), M_LuxVultoSombra e MI_LuxVultoSombra_L1 (valores de SOMBRA_L1)."""
    MEL = unreal.MaterialEditingLibrary
    novos = []
    if not EAL.does_asset_exist(ANIM_ANDAR):
        w("duplicando anim -> A_LuxVultoAndar (ForceRootLock)")
        EAL.duplicate_asset(ANIM_ANDAR_SRC, ANIM_ANDAR)
    a = EAL.load_asset(ANIM_ANDAR)
    if not a.get_editor_property("force_root_lock"):
        a.set_editor_property("force_root_lock", True)
        novos.append(a)
    if not EAL.does_asset_exist(M_SOMBRA):
        novos.append(cria_sombra())
    nova = not EAL.does_asset_exist(MI_SOMBRA_L1)
    if nova:
        w("criando MI_LuxVultoSombra_L1")
        mi = unreal.AssetToolsHelpers.get_asset_tools().create_asset("MI_LuxVultoSombra_L1", DIR, unreal.MaterialInstanceConstant,
                                                                      unreal.MaterialInstanceConstantFactoryNew())
        mi.set_editor_property("parent", EAL.load_asset(M_SOMBRA))
    mi = EAL.load_asset(MI_SOMBRA_L1)
    mud = nova
    for k, v in SOMBRA_L1.items():
        if nova or abs(MEL.get_material_instance_scalar_parameter_value(mi, k) - v) > 1e-6:
            MEL.set_material_instance_scalar_parameter_value(mi, k, v)
            mud = True
    if mud:
        MEL.update_material_instance(mi)
        novos.append(mi)
    return novos


def ensure_l1_luz():
    """Luzes quentes fracas de L1_LUZES, so no loop 1 (LOOP1_ON/LOOP2_OFF), piscando com as arandelas (tag do corredor).
    Cor por temperatura, nao por light_color: o verificar dos eventos reprova luz de piscar avermelhada (fotossensibilidade)."""
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    mud = []
    for lab, cfg in L1_LUZES.items():
        lst = [x for x in ale.atores() if x.get_actor_label() == lab]
        a = lst[0] if lst else None
        if not a:
            a = eas.spawn_actor_from_class(unreal.PointLight, unreal.Vector(*cfg["pos"]), unreal.Rotator())
            a.set_actor_label(lab)
            a.set_folder_path(ale.FOLDER)
            mud.append(lab)
        if (a.get_actor_location() - unreal.Vector(*cfg["pos"])).length() > 0.5:
            a.set_actor_location(unreal.Vector(*cfg["pos"]), False, True)
            mud.append("%s posicao" % lab)
        c = a.point_light_component
        for k, v in (("mobility", unreal.ComponentMobility.MOVABLE), ("intensity_units", unreal.LightUnits.CANDELAS), ("intensity", cfg["cd"]),
                     ("attenuation_radius", cfg["raio"]), ("use_temperature", True), ("temperature", cfg["temperatura"]),
                     ("cast_shadows", True)):  # com sombra: sem ela a luz atravessa a parede e acende o piano da sala (~2,75 m)
            atual = c.get_editor_property(k)
            if (abs(atual - v) > 1e-4) if isinstance(v, float) else (atual != v):
                c.set_editor_property(k, v)
                mud.append("%s.%s" % (lab, k))
        quer = [ale.TAG, "LOOP1_ON", "LOOP2_OFF", ale.TAG_CORREDOR]
        if sorted(str(t) for t in a.tags) != sorted(quer):
            a.set_editor_property("tags", [unreal.Name(x) for x in quer])
            mud.append("%s tags" % lab)
    return mud


def cria_bp_quadros():
    """BP NOVO: Figura (SKM_Manny_Simple, pose unica congelada, corpo M_LuxVultoSombra, aura, sem colisao e sem sombra) + vigia
    de 0,05 s do DisparoT do Evento + quadros por timer ancorados no DisparoT + esconder em DuracaoS."""
    w("criando BP_LuxVultoQuadros")
    bp = BEL.create_blueprint_asset_with_parent(BPQ, unreal.Actor)
    t = ale.tipos_base()
    t["evt"] = BEL.get_object_reference_type(EAL.load_asset(ale.EVT).generated_class())
    t["vec[]"] = BEL.get_array_type(t["vec"])
    w("  componente Figura")
    _, fig = ale.add_comp(bp, unreal.SkeletalMeshComponent, "Figura")
    fig.set_editor_property("skeletal_mesh_asset", EAL.load_asset(SKM))
    fig.set_editor_property("animation_mode", unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    fig.set_editor_property("animation_data", unreal.SingleAnimationPlayData(anim_to_play=EAL.load_asset(ANIM_IDLE), saved_looping=True,
                                                                               saved_playing=False, saved_position=0.5, saved_play_rate=0.0))
    n = len(EAL.load_asset(SKM).get_editor_property("materials"))
    fig.set_editor_property("override_materials", [EAL.load_asset(MI_SOMBRA_L1)] * n)
    fig.set_editor_property("overlay_material", EAL.load_asset(M_AURA))
    fig.set_collision_profile_name("NoCollision")
    fig.set_editor_property("cast_shadow", False)
    fig.set_editor_property("hidden_in_game", True)
    fig.set_editor_property("visibility_based_anim_tick_option", unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE)
    fig.set_editor_property("relative_rotation", unreal.Rotator(0, 0, -90))  # manequim olha para +Y; o ator olha para +X
    fig.set_editor_property("relative_scale3d", unreal.Vector(*ESCALA_FIGURA))
    vars_ = [("Evento", "evt", True, None), ("Tempos", "real[]", True, None), ("Posicoes", "vec[]", True, None),
             ("Poses", "real[]", True, None), ("Yaws", "real[]", True, None), ("bEncarar", "bool", True, True),
             ("DuracaoS", "real", True, 2.0), ("UltDisparo", "real", False, -1000.0), ("T0", "real", False, 0.0),
             ("Indice", "int", False, 0), ("VersaoQuadros", "int", False, 0)]
    w("  variaveis")
    ale.cria_vars(bp, vars_, t, "LUX Vulto")
    BEL.compile_blueprint(bp)
    ale.padroes(bp, [v for v in vars_ if v[3] is not None])
    w("  funcoes")
    ale.cria_funcoes(bp, [("Inicializar", []), ("Vigiar", []), ("Quadro", []), ("Esconder", [])], t)
    BEL.compile_blueprint(bp)

    def disparo(b):
        d = b.v("DisparoT", cls=ale.EVT_C)
        b.lk(b.v("Evento"), d[0], "self")
        return d

    def ocultar(b, sim):
        n = b.c("/Script/Engine.SceneComponent:SetHiddenInGame", 0, 0, NewHidden="true" if sim else "false")
        b.lk(b.v("Figura"), n, "self")
        return n

    w("  grafo Inicializar")
    b, en = entrada(bp, "Inicializar", MEQ)
    hid = ocultar(b, True)
    bv = b.br(b.valido(b.v("Evento")))
    su = b.setv("UltDisparo", src=disparo(b))
    tm = b.timer("Vigiar", 0.05, loop=True)
    b.ch(en, hid, bv)
    b.ch((bv, "then"), su, tm)
    # 30/09: SEM compilar entre os grafos. No UE 5.8.3, criar um no Add_* (add_call_function_node) depois de compilar um BP que
    # ja tem outro Add_* derruba o editor (ponteiro nulo em UBlueprintGraphEditor::AddCallFunctionNode; reproduzido 5 de 5 em
    # commandlet). Compila uma vez, no fim, como o build_evento do add_loop_events.py.

    w("  grafo Vigiar")
    b, en = entrada(bp, "Vigiar", MEQ)
    b0 = b.br(b.valido(b.v("Evento")))
    b1 = b.br(b.op("NotEqual_DoubleDouble", disparo(b), b.v("UltDisparo")))
    s_ult = b.setv("UltDisparo", src=disparo(b))
    s_t0 = b.setv("T0", src=disparo(b))      # ancora no relogio do evento: o atraso da vigia nao desloca os quadros
    s_i = b.setv("Indice", 0)
    c1, c2 = b.clear("Quadro"), b.clear("Esconder")
    q = b.call("Quadro")
    fim = b.c(KML + "FMax", 0, 0, B=0.01)
    b.lk(b.op("Subtract_DoubleDouble", b.op("Add_DoubleDouble", b.v("T0"), b.v("DuracaoS")), b.now()), fim, "A")
    te = b.timer("Esconder", (fim, "ReturnValue"))
    b.ch(en, b0)
    b.ch((b0, "then"), b1)
    b.ch((b1, "then"), s_ult, s_t0, s_i, c1, c2, q, te)

    w("  grafo Quadro")
    b, en = entrada(bp, "Quadro", MEQ)

    def tamanho():
        n = b.c(ale.ARR + "Array_Length", 0, 0)
        b.lk(b.v("Tempos"), n, "TargetArray")
        return (n, "ReturnValue")

    def item(arr):
        n = b.c(ale.ARR + "Array_Get", 0, 0)
        b.lk(b.v(arr), n, "TargetArray")
        b.lk(b.v("Indice"), n, "Index")
        return (n, "Item")

    bq = b.br(b.op("Less_IntInt", b.v("Indice"), tamanho()))
    pcm = (b.c(GS + "GetPlayerCameraManager", 0, 0, PlayerIndex=0), "ReturnValue")
    be = b.br(b.e(b.v("bEncarar"), b.valido(pcm)))
    cam = b.c("/Script/Engine.PlayerCameraManager:GetCameraLocation", 0, 0)
    b.lk(pcm, cam, "self")
    olha = b.c(KML + "FindLookAtRotation", 0, 0)
    b.lk(item("Posicoes"), olha, "Start")
    b.lk((cam, "ReturnValue"), olha, "Target")
    qb = b.c(KML + "BreakRotator", 0, 0)
    b.lk((olha, "ReturnValue"), qb, "InRot")
    r1 = b.c(KML + "MakeRotator", 0, 0, Roll=0.0, Pitch=0.0)
    b.lk((qb, "Yaw"), r1, "Yaw")
    s1 = b.c("/Script/Engine.Actor:K2_SetActorLocationAndRotation", 0, 0, bSweep="false", bTeleport="true")
    b.lk(item("Posicoes"), s1, "NewLocation")
    b.lk((r1, "ReturnValue"), s1, "NewRotation")
    r2 = b.c(KML + "MakeRotator", 0, 0, Roll=0.0, Pitch=0.0)
    b.lk(item("Yaws"), r2, "Yaw")
    s2 = b.c("/Script/Engine.Actor:K2_SetActorLocationAndRotation", 0, 0, bSweep="false", bTeleport="true")
    b.lk(item("Posicoes"), s2, "NewLocation")
    b.lk((r2, "ReturnValue"), s2, "NewRotation")
    j = junc(b)
    sp = b.c("/Script/Engine.SkeletalMeshComponent:SetPosition", 0, 0, bFireNotifies="false")
    b.lk(b.v("Figura"), sp, "self")
    b.lk(item("Poses"), sp, "InPos")
    mo = ocultar(b, False)
    inc = b.setv("Indice", src=b.op("Add_IntInt", b.v("Indice"), 1))
    bm = b.br(b.op("Less_IntInt", b.v("Indice"), tamanho()))
    prox = b.c(KML + "FMax", 0, 0, B=0.01)
    b.lk(b.op("Subtract_DoubleDouble", b.op("Add_DoubleDouble", b.v("T0"), item("Tempos")), b.now()), prox, "A")
    tq = b.timer("Quadro", (prox, "ReturnValue"))
    b.ch(en, bq)
    b.ch((bq, "then"), be)
    b.ch((be, "then"), s1, j)
    b.ch((be, "else"), s2, j)
    b.ch((j, "then"), sp, mo, inc, bm)
    b.ch((bm, "then"), tq)

    w("  grafo Esconder")
    b, en = entrada(bp, "Esconder", MEQ)
    b.ch(en, ocultar(b, True), b.clear("Quadro"), b.setv("Indice", 0))

    w("  EventGraph")
    ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
    g = G(ge)
    bpl = g.pos(BEL.add_event_override(bp, "ReceiveBeginPlay", unreal.IntPoint(0, 0)), 0, 0)
    g.chain(bpl, g.call(MEQ + ":Inicializar", 300, 0))
    BEL.compile_blueprint(bp)
    e = ale.erros_bp(bp)
    if e:
        raise Aborta("BP_LuxVultoQuadros com erros/avisos (nada salvo): %s" % e)
    unreal.get_default_object(bp.generated_class()).set_editor_property("VersaoQuadros", VERSAO_QUADROS)
    BEL.compile_blueprint(bp)
    w("  BP limpo")
    return bp


def ensure_bp_quadros():
    if EAL.does_asset_exist(BPQ):
        bp = EAL.load_asset(BPQ)
        if unreal.get_default_object(bp.generated_class()).get_editor_property("VersaoQuadros") != VERSAO_QUADROS:
            raise Aborta("BP_LuxVultoQuadros existe sem VersaoQuadros=%d: estado incompleto (feche o editor sem salvar)" % VERSAO_QUADROS)
        w("BP_LuxVultoQuadros v%d ja existe: mantido" % VERSAO_QUADROS)
        return bp, False
    return cria_bp_quadros(), True


def ensure_l1_figuras(bpq):
    """Uma instancia de BP_LuxVultoQuadros por evento do Loop 1 (dados de instancia + pose e material na Figura desta instancia).
    Figura de outra classe com o mesmo nome (a v2 era BP_LuxVultoCorre) e trocada."""
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    mi = EAL.load_asset(MI_SOMBRA_L1)
    n_mat = len(EAL.load_asset(SKM).get_editor_property("materials"))
    mud = []
    for cfg in FIGURAS_L1:
        lst = [x for x in ale.atores() if x.get_actor_label() == cfg["label"]]
        if len(lst) > 1:
            raise Aborta("mais de um %s" % cfg["label"])
        a = lst[0] if lst else None
        if a and not a.get_class().get_name().startswith("BP_LuxVultoQuadros"):
            w("  %s era %s: trocado por BP_LuxVultoQuadros" % (cfg["label"], a.get_class().get_name()))
            eas.destroy_actor(a)
            a = None
        p0, r0 = unreal.Vector(*cfg["posicoes"][0]), unreal.Rotator(0.0, 0.0, cfg["yaws"][0])
        if not a:
            a = eas.spawn_actor_from_class(bpq.generated_class(), p0, r0)
            a.set_actor_label(cfg["label"])
            a.set_folder_path(ale.FOLDER)
            a.set_editor_property("tags", [unreal.Name(ale.TAG)])
            mud.append(cfg["label"])
        ev = ale.por_label(cfg["evento"])
        if not ev:
            raise Aborta("%s nao encontrado (rode add_loop_events.py instalar)" % cfg["evento"])
        quer = {"Evento": ev, "Tempos": [float(x) for x in cfg["tempos"]], "Posicoes": [unreal.Vector(*p) for p in cfg["posicoes"]],
                "Poses": [float(x) for x in cfg["poses"]], "Yaws": [float(x) for x in cfg["yaws"]], "bEncarar": True,
                "DuracaoS": float(cfg["duracao"])}
        for k, v in quer.items():
            if not igual(a.get_editor_property(k), v):
                a.set_editor_property(k, v)
                mud.append("%s.%s" % (cfg["label"], k))
        if (a.get_actor_location() - p0).length() > 0.5 or abs(a.get_actor_rotation().yaw - cfg["yaws"][0]) > 0.1:
            a.set_actor_location_and_rotation(p0, r0, False, True)
            mud.append("%s transform" % cfg["label"])
        fig = a.get_components_by_class(unreal.SkeletalMeshComponent)[0]
        anim = EAL.load_asset(cfg["anim"])
        dados = fig.get_editor_property("animation_data")
        if (dados.get_editor_property("anim_to_play") != anim or dados.get_editor_property("saved_playing")
                or abs(dados.get_editor_property("saved_position") - cfg["poses"][0]) > 1e-6):
            fig.set_editor_property("animation_data", unreal.SingleAnimationPlayData(anim_to_play=anim, saved_looping=True, saved_playing=False,
                                                                                       saved_position=cfg["poses"][0], saved_play_rate=0.0))
            mud.append("%s anim" % cfg["label"])
        mats = list(fig.get_editor_property("override_materials"))
        if len(mats) != n_mat or any(m_ != mi for m_ in mats):
            fig.set_editor_property("override_materials", [mi] * n_mat)
            mud.append("%s material" % cfg["label"])
    return mud


def janelas(ev, ate=12.0):
    """(apagadas, acesas) em s depois do DisparoT, como o PassoPiscar/FimPiscar do evento: passos pares do PadraoPiscar apagados
    (no maximo 8, cada um com 0,25 s ou mais); no fim, com bApagarNoFim, apagado ate RestaurarAposS (0 = para sempre)."""
    pp = [max(0.25, x) for x in list(ev.get_editor_property("PadraoPiscar"))[:8]]
    esc, ace, t = [], [], 0.0
    for i, d in enumerate(pp):
        (esc if i % 2 == 0 else ace).append((t, t + d))
        t += d
    if ev.get_editor_property("bApagarNoFim"):
        r = ev.get_editor_property("RestaurarAposS")
        esc.append((t, t + r if r > 0 else 1e9))
        if r > 0:
            ace.append((t + r, ate))
    else:
        ace.append((t, ate))
    return esc, ace


def livre(world, p):
    r, hh = CAPSULA
    c = unreal.Vector(p.x, p.y, p.z + hh + 4.0)
    h = unreal.SystemLibrary.capsule_trace_single(world, c, c + unreal.Vector(0, 0, 1.0), r, hh, VIS, False, [],
                                                  unreal.DrawDebugTrace.NONE, True)
    if not h:
        return None
    quem = h.to_tuple()[9]
    return quem.get_actor_label() if quem else "?"


def chao(world, p):
    h = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(p.x, p.y, p.z + 150.0), unreal.Vector(p.x, p.y, p.z - 150.0), VIS, False, [],
                                               unreal.DrawDebugTrace.NONE, True)
    return h.to_tuple()[4].z if h else None


def verificar_l1():
    MEL = unreal.MaterialEditingLibrary
    f = []
    for pth in (ANIM_ANDAR, M_SOMBRA, MI_SOMBRA_L1, BPQ):
        if not EAL.does_asset_exist(pth):
            f.append("asset ausente: %s" % pth)
    if f:
        w("verificar_l1: FAIL %s" % f)
        return f
    if not EAL.load_asset(ANIM_ANDAR).get_editor_property("force_root_lock"):
        f.append("A_LuxVultoAndar sem ForceRootLock")
    m = EAL.load_asset(M_SOMBRA)
    if (m.get_editor_property("blend_mode") != unreal.BlendMode.BLEND_TRANSLUCENT or
            m.get_editor_property("shading_model") != unreal.MaterialShadingModel.MSM_UNLIT or not m.get_editor_property("used_with_skeletal_mesh")):
        f.append("M_LuxVultoSombra nao e unlit translucido para malha esqueletica")
    for prop in (unreal.MaterialProperty.MP_OPACITY, unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET):
        if not MEL.get_material_property_input_node(m, prop):
            f.append("M_LuxVultoSombra sem entrada em %s" % prop)
    emi = MEL.get_material_property_input_node(m, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    cor = emi.get_editor_property("constant") if isinstance(emi, unreal.MaterialExpressionConstant3Vector) else None
    if not cor or max(cor.r, cor.g, cor.b) > 0.0:
        f.append("M_LuxVultoSombra com emissivo != 0 (no escuro a exposicao multiplica o emissivo por ~213 e o vulto clareia)")
    mi = EAL.load_asset(MI_SOMBRA_L1)
    if mi.get_editor_property("parent") != m:
        f.append("MI_LuxVultoSombra_L1 nao deriva de M_LuxVultoSombra")
    for k, v in SOMBRA_L1.items():
        if abs(MEL.get_material_instance_scalar_parameter_value(mi, k) - v) > 1e-4:
            f.append("MI_LuxVultoSombra_L1.%s != %s" % (k, v))
    bpq = EAL.load_asset(BPQ)
    f += ["BP_LuxVultoQuadros: %s" % e for e in ale.erros_bp(bpq)]
    if unreal.get_default_object(bpq.generated_class()).get_editor_property("VersaoQuadros") != VERSAO_QUADROS:
        f.append("BP_LuxVultoQuadros sem VersaoQuadros=%d" % VERSAO_QUADROS)
    for nome in ("Inicializar", "Vigiar", "Quadro", "Esconder"):
        if nome not in [str(x) for x in BEL.list_graph_names(bpq)] or len(list(BGE.get_graph_editor_by_name(bpq, nome).list_all_nodes())) < 3:
            f.append("BP_LuxVultoQuadros: funcao %s ausente/vazia" % nome)
    for lab, cfg in L1_LUZES.items():
        luz = [x for x in ale.atores() if x.get_actor_label() == lab]
        if len(luz) != 1:
            f.append("esperava 1 %s (%d)" % (lab, len(luz)))
            continue
        c = luz[0].point_light_component
        if sorted(str(t) for t in luz[0].tags) != sorted([ale.TAG, "LOOP1_ON", "LOOP2_OFF", ale.TAG_CORREDOR]):
            f.append("%s sem as tags LOOP1_ON/LOOP2_OFF/%s" % (lab, ale.TAG_CORREDOR))
        if "MOVABLE" not in str(c.get_editor_property("mobility")) or not c.get_editor_property("cast_shadows"):
            f.append("%s nao e Movable ou nao faz sombra (sem sombra a luz atravessa as paredes)" % lab)
        if abs(c.get_editor_property("intensity") - cfg["cd"]) > 1e-4 or (luz[0].get_actor_location() - unreal.Vector(*cfg["pos"])).length() > 0.5:
            f.append("%s diferente de L1_LUZES" % lab)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    for cfg in FIGURAS_L1:
        lab = cfg["label"]
        lst = [x for x in ale.atores() if x.get_actor_label() == lab]
        if len(lst) != 1:
            f.append("esperava 1 %s (%d)" % (lab, len(lst)))
            continue
        a = lst[0]
        if not a.get_class().get_name().startswith("BP_LuxVultoQuadros"):
            f.append("%s e %s (esperado BP_LuxVultoQuadros)" % (lab, a.get_class().get_name()))
            continue
        ev = a.get_editor_property("Evento")
        if not ev or ev.get_actor_label() != cfg["evento"]:
            f.append("%s: Evento nao aponta para %s" % (lab, cfg["evento"]))
            continue
        if ev.get_editor_property("bAparicao"):
            f.append("%s ainda com bAparicao (a silhueta estatica branca voltaria)" % cfg["evento"])
        tempos, pos = list(a.get_editor_property("Tempos")), list(a.get_editor_property("Posicoes"))
        poses, yaws = list(a.get_editor_property("Poses")), list(a.get_editor_property("Yaws"))
        dur = a.get_editor_property("DuracaoS")
        if not (len(tempos) == len(pos) == len(poses) == len(yaws) == len(cfg["tempos"])):
            f.append("%s: Tempos/Posicoes/Poses/Yaws com tamanhos diferentes" % lab)
            continue
        if not (igual(tempos, [float(x) for x in cfg["tempos"]]) and igual(pos, [unreal.Vector(*p) for p in cfg["posicoes"]])
                and igual(poses, [float(x) for x in cfg["poses"]]) and abs(dur - cfg["duracao"]) < 1e-6):
            f.append("%s: quadros diferentes de FIGURAS_L1" % lab)
        if tempos[0] != 0.0 or tempos != sorted(tempos) or dur <= tempos[-1]:
            f.append("%s: quadros fora de ordem, sem o quadro 0 ou sumindo antes do ultimo" % lab)
        # sincronia com o piscar: entra, muda de lugar e some no escuro (menos os quadros no_claro, de proposito)
        esc, ace = janelas(ev)
        # o quadro 0 nasce junto com o 1o apagao (o Executar chama o PassoPiscar no mesmo quadro); os outros e o sumico precisam
        # de MARGEM_INICIO depois do inicio do apagao (o piscar atrasa) e de MARGEM_ESCURO antes do fim
        no_escuro = lambda t, ini: any(a0 + ini - 1e-6 <= t and t + MARGEM_ESCURO <= b0 for a0, b0 in esc)
        for i, t in enumerate(tempos):
            if i not in cfg["no_claro"] and not no_escuro(t, 0.0 if t == 0.0 else MARGEM_INICIO):
                f.append("%s: quadro %d (%.2f s) fora de um apagao do %s (com folga)" % (lab, i, t, cfg["evento"]))
        if not no_escuro(dur, MARGEM_INICIO):
            f.append("%s: some em %.2f s, fora de um apagao (com folga)" % (lab, dur))
        visto = sum(max(0.0, min(b0, dur) - max(a0, tempos[0])) for a0, b0 in ace)
        if visto < 0.5:
            f.append("%s: so %.2f s visivel com a luz acesa (minimo 0,5)" % (lab, visto))
        for i, p in enumerate(pos):
            b_ = livre(world, p)
            if b_:
                f.append("%s: quadro %d em (%.0f, %.0f) encosta em %s" % (lab, i, p.x, p.y, b_))
            z = chao(world, p)
            if z is None or abs(z - p.z) > 5.0:
                f.append("%s: quadro %d fora do chao (chao em z %s)" % (lab, i, z))
        fig = a.get_components_by_class(unreal.SkeletalMeshComponent)[0]
        if not fig.get_editor_property("hidden_in_game"):
            f.append("%s: Figura visivel no jogo por padrao" % lab)
        if fig.get_collision_profile_name() != "NoCollision" or fig.get_editor_property("cast_shadow"):
            f.append("%s: Figura com colisao ou sombra" % lab)
        if not fig.get_editor_property("overlay_material"):
            f.append("%s: Figura sem aura" % lab)
        if any(m_ != mi for m_ in fig.get_editor_property("override_materials")):
            f.append("%s: material do corpo != MI_LuxVultoSombra_L1" % lab)
        dados = fig.get_editor_property("animation_data")
        if dados.get_editor_property("anim_to_play") != EAL.load_asset(cfg["anim"]) or dados.get_editor_property("saved_playing"):
            f.append("%s: animacao != %s congelada" % (lab, cfg["anim"]))
        if (fig.get_editor_property("relative_scale3d") - unreal.Vector(*ESCALA_FIGURA)).length() > 1e-3:
            f.append("%s: escala da Figura != %s" % (lab, ESCALA_FIGURA))
        if cfg["evento"] == "EV_L1_PassosPesados":
            ps = [c for c in ev.get_components_by_class(unreal.SceneComponent) if c.get_name().startswith("PontoSom")][0].get_world_location()
            d = ev.get_editor_property("DeslocPorRep")
            passo = pos[1] - pos[0] if len(pos) > 1 else unreal.Vector()
            if ((unreal.Vector(ps.x, ps.y, 0) - unreal.Vector(pos[0].x, pos[0].y, 0)).length() > 1.0 or
                    (unreal.Vector(d.x, d.y, 0) - unreal.Vector(passo.x, passo.y, 0)).length() > 1.0):
                f.append("%s: os passos nao soam onde a figura esta (PontoSom/DeslocPorRep do evento)" % lab)
    lf = [x for x in ale.atores() if x.get_actor_label() == LUZ_FUNDO]
    if lf and sorted(str(t) for t in lf[0].tags) != sorted([ale.TAG, "LOOP2_ON", "LOOP3_OFF"]):
        f.append("%s (loop 2) teve as tags alteradas" % LUZ_FUNDO)
    w("verificar_l1:", ("FAIL %s" % f) if f else "PASS")
    return f


PROPRIOS_L1 = (ANIM_ANDAR, M_SOMBRA, MI_SOMBRA_L1, BPQ)


def instalar_l1():
    if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():
        raise Aborta("feche o PIE")
    if ale.sujos():
        # retomada: so os proprios assets do Loop 1 podem estar sujos (execucao anterior abortada antes de salvar)
        if not set(ale.sujos()) <= set(PROPRIOS_L1) | {"/Game/Masion/Mapa_B"}:
            raise Aborta("ha pacotes nao salvos antes de comecar: %s" % ale.sujos())
        w("retomando com pacotes proprios sujos:", ale.sujos())
    novos = ensure_l1_assets()
    bpq, criou = ensure_bp_quadros()
    mud = ensure_l1_luz() + ensure_l1_figuras(bpq)
    w("mudou (loop 1):", mud or "nada")
    f = verificar_l1()
    if f:
        raise Aborta("verificar_l1 FAIL (nada salvo): %s" % f)
    for x in novos + [EAL.load_asset(p) for p in PROPRIOS_L1 if p in ale.sujos()]:
        if x.get_outermost().get_name() in ale.sujos():
            w("salvo", x.get_path_name(), EAL.save_loaded_asset(x, False))
    U = unreal.EditorLoadingAndSavingUtils
    mapa = [p for p in U.get_dirty_map_packages() if p.get_name() == "/Game/Masion/Mapa_B"]
    if mapa:
        w("salvo Mapa_B", U.save_packages(mapa, True))
    extra = [p for p in ale.sujos() if p != "/Game/Masion/Mapa_B"]
    if extra:
        w("aviso: pacotes ainda sujos:", extra)


def desfazer_l1():
    """Tira so o que e do Loop 1 (figuras, de qualquer versao, e a luz). Os assets (BP, materiais, anim) ficam; o loop 2 nao e tocado."""
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    alvo = [c["label"] for c in FIGURAS_L1] + list(L1_LUZES)
    for a in [a for a in ale.atores() if a.get_actor_label() in alvo]:
        eas.destroy_actor(a)
    U = unreal.EditorLoadingAndSavingUtils
    U.save_packages([p for p in U.get_dirty_map_packages() if p.get_name() == "/Game/Masion/Mapa_B"], True)
    w("Loop 1 removido do mapa (%s); assets ficam em %s" % (", ".join(alvo), DIR))


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
