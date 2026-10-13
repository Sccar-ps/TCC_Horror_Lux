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
# Loop 1 v4 (05/10, "o vulto pipoca e foge do compasso"): BP_LuxVultoFluido (a presenca da figura, em Custom Primitive Data, segue a
#   intensidade REAL da luz propria dela; anda de verdade; entra/sai por opacidade). O v3 fica intacto como retorno. Os numeros moram em
#   vulto_cronograma.py. Etapas (cada uma num processo; salvar so o que e do Loop 1):
#   instalar_l1 assets  -> COMMANDLET (editor grafico FECHADO; ver lux_cmdlet_l1.py): cria e salva SO os 4 assets novos
#   instalar_l1 mapa    -> EDITOR, fora do PIE: luzes do Loop 1 + as duas figuras + verificar completo; salva o Mapa_B
#   verificar_assets (so leitura, serve no commandlet) | verificar_mapa (editor) | verificar_l1 (os dois) | desfazer_l1
# Log por operacao (com flush): Saved/LuxSnapshots/vulto_corre_log.txt
import importlib, os, sys, traceback, unreal

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import add_loop_events as ale
importlib.reload(ale)
import vulto_cronograma as vc
importlib.reload(vc)
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
# 05/10: RECONCILIADO COM O MAPA, depois com a decisao do Bruno. Depois do v3 (55dcf08) a equipe moveu as duas luzes a mao para o teto (z 300)
# nos commits edc0795, ed89ce7 e 7bb7ed6 (v3: LuzFundo (-3250, -1080, 110) raio 450; LuzPassos (-3300, -660, 230)). O A/B no PIE de 05/10 mostrou
# que, com a LuzFundo do teto (raio 223), o vulto do vao fica quase imperceptivel (nitido na posicao do v3): decisao do Bruno em 05/10: a
# LuzFundo VOLTA a posicao do v3; a LuzPassos FICA no teto (a figura dos passos e legivel quando o jogador olha para ela; so alcanca o tronco
# da figura ate x ~ -3104). O ensure_l1_luz aplica estes valores.
L1_LUZES = {
    "LUX_L1_LuzFundo": {"pos": (-3250.0, -1080.0, 110.0), "cd": 0.3, "raio": 450.0, "temperatura": 3200.0},
    "LUX_L1_LuzPassos": {"pos": (-3450.0, -720.0, 300.0), "cd": 0.15, "raio": 400.0, "temperatura": 3200.0},
}

# ------------------------------------------------------------------ Loop 1 v3 (30/09, polimento: medo, tensao, confusao de Santos)
# O vulto do Loop 1 so existe "entre as piscadas": aparece no escuro, e visto parado contra a luz e muda de lugar no escuro.
# Peca BP_LuxVultoQuadros (BP NOVO; o BP_LuxVultoCorre do loop 2 nao muda): le o DisparoT do evento por um timer de vigia
# de 0,05 s e, quando ele muda, executa QUADROS ancorados no DisparoT (Tempos/Posicoes/Poses/Yaws): em cada quadro teleporta,
# congela a pose (SetPosition) e vira o rosto para a camera do jogador; esconde em DuracaoS. Os quadros vao por timer (sem Tick).
# Visual "sombra viva" (M_LuxVultoSombra, unlit translucido, emissivo 0: a exposicao do escuro nao a clareia): opacidade com
# borda que se desfaz (Fresnel), fumaca subindo por dentro (ruido 3D em espaco de mundo) e contorno que treme em degraus
# (WPO pela normal, ruido trocado 8 vezes por segundo), corpo 7 % mais alto e mais magro que o manequim (escala da Figura).
# 05/10: o v3 sai do mapa (as figuras viram BP_LuxVultoFluido, abaixo) mas FICA no disco, intacto, como retorno: cria_bp_quadros e
# ensure_bp_quadros so servem para recriar o BP_LuxVultoQuadros se o asset se perder.
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
FOLGA_PAREDE = 8.0                   # cm: a capsula tem de passar a pelo menos isso de qualquer parede (CutPart14: folga estimada 11,2 cm)

# ------------------------------------------------------------------ Loop 1 v4 (05/10): BP_LuxVultoFluido
# Causa do "pipocar": a figura e um preto translucido (opacidade 0,65 fixa, emissivo 0) que so existe como contraste contra o fundo
# iluminado, e a luz muda em DEGRAU (25x em 1 quadro). Ligar/desligar a figura junto desse degrau e o que o jogador ve. Agora a figura
# le a intensidade REAL da luz propria dela (LUX_L1_LuzFundo no vao, LUX_L1_LuzPassos nos passos) a cada 0,02 s e deriva uma presenca
# P (0 a 1) que vai para o Custom Primitive Data 0 e MULTIPLICA a opacidade do corpo e da aura: entra depois de a luz subir, sai antes
# de ela cair, nunca aparece/some em degrau e a figura anda de verdade. Numeros e regras: vulto_cronograma.py.
BPF = DIR + "/BP_LuxVultoFluido"
MEF = BPF + ".BP_LuxVultoFluido_C"
VERSAO_FLUIDO = 1
M_SOMBRA_P = DIR + "/M_LuxVultoSombra_P"    # copia da M_LuxVultoSombra + Presenca (a original nao muda)
M_AURA_L1 = DIR + "/M_LuxVultoAura_L1"      # copia da M_LuxVultoAura + Presenca (a do loop 2 nao muda)
MI_SOMBRA_L1P = DIR + "/MI_LuxVultoSombra_L1P"
SOMBRA_L1P = dict(SOMBRA_L1, Fumaca=0.15)   # a fumaca em coordenadas de mundo cintila numa figura que anda: 0,4 -> 0,15 so na MI nova
PRESENCA = "Presenca"
CPD_INDICE = 0
CLASSE_FLUIDO = "BP_LuxVultoFluido_C"
NOMES_REAIS = dict(bp=BPF, sombra=M_SOMBRA_P, aura=M_AURA_L1, mi=MI_SOMBRA_L1P)
# ensaio em memoria: so o create_blueprint_asset_with_parent aceita /Temp; os materiais (AssetTools recusa /Temp) caem em ZZ_* no DIR
# e nunca sao salvos
NOMES_ENSAIO = dict(bp="/Temp/LuxProbe/BP_LuxVultoFluido_ensaio", sombra=DIR + "/ZZ_M_LuxVultoSombra_P", aura=DIR + "/ZZ_M_LuxVultoAura_L1",
                    mi=DIR + "/ZZ_MI_LuxVultoSombra_L1P")
PROPRIOS_L1 = tuple(NOMES_REAIS.values())                       # so estes 4 sao gravados pela etapa 'assets'
PROPRIOS_V3 = (ANIM_ANDAR, M_SOMBRA, MI_SOMBRA_L1, BPQ)         # v3: nunca gravados por esta etapa (podem aparecer sujos so numa retomada)
FIGURAS_L1 = [dict(chave=k, label=vc.EVENTOS[k]["figura"], evento=vc.EVENTOS[k]["nome"], luz=vc.EVENTOS[k]["luz"],
                   anim=ANIM_IDLE if k == "vulto" else ANIM_ANDAR) for k in ("vulto", "passos")]
# variaveis do BP: nome, tipo, editavel na instancia, padrao no CDO (None = sem padrao). Os padroes vem de vc.PADROES_BP; os valores
# reais, de vc.dados_instancia() aplicado pelo ensure_l1_figuras.
VARS_FLUIDO = [("Evento", "evt", True, None), ("ActorLuz", "actor", True, None), ("DuracaoS", "real", True, vc.PADROES_BP["DuracaoS"]),
               ("JanAcesa", "real[]", True, None), ("TSubNom", "real[]", True, None),
               ("EntradaS", "real", True, vc.PADROES_BP["EntradaS"]), ("SaidaS", "real", True, vc.PADROES_BP["SaidaS"]),
               ("MargemS", "real", True, vc.PADROES_BP["MargemS"]), ("TolS", "real", True, vc.PADROES_BP["TolS"]),
               ("PontoA", "vec", True, None), ("PontoB", "vec", True, None), ("TMovI", "real", True, vc.PADROES_BP["TMovI"]),
               ("TMovF", "real", True, vc.PADROES_BP["TMovF"]), ("bEncarar", "bool", True, vc.PADROES_BP["bEncarar"]),
               ("YawFixo", "real", True, vc.PADROES_BP["YawFixo"]), ("OffsetYaw", "real", True, vc.PADROES_BP["OffsetYaw"]),
               ("FaseIni", "real", True, vc.PADROES_BP["FaseIni"]), ("TaxaAnim", "real", True, vc.PADROES_BP["TaxaAnim"]),
               ("DistMinCam", "real", True, vc.PADROES_BP["DistMinCam"]), ("DistPlenaCam", "real", True, vc.PADROES_BP["DistPlenaCam"]),
               ("bLog", "bool", True, vc.PADROES_BP["bLog"]),
               # estado (nao editavel)
               ("UltDisparo", "real", False, -1000.0), ("T0", "real", False, 0.0), ("bAtivo", "bool", False, False),
               ("bLuzAnt", "bool", False, False), ("NSub", "int", False, 0), ("TSub", "real", False, 0.0), ("YawBase", "real", False, 0.0),
               ("IntensOrig", "real", False, 1.0), ("PAtual", "real", False, 0.0), ("Luz", "lc", False, None),
               ("VersaoFluido", "int", False, 0)]
FUNCOES_FLUIDO = ("Inicializar", "Atualizar", "Iniciar", "Amostrar", "Encerrar")

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


# ------------------------------------------------------------------ Loop 1 v4: materiais (copias com a Presenca)
def _duplica(origem, destino):
    """AssetTools.duplicate_asset (so /Game: /Temp e recusado). Devolve o asset novo."""
    pasta, nome = destino.rsplit("/", 1)
    d = unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(nome, pasta, EAL.load_asset(origem))
    if not d:
        raise Aborta("duplicate_asset falhou: %s -> %s" % (origem, destino))
    return d


def _multiplica_pela_presenca(m):
    """MP_OPACITY := fonte atual x ScalarParameter 'Presenca' (Custom Primitive Data, indice 0, padrao 0). Na sombra a fonte e o Saturate
    final; na aura, o Multiply da opacidade (0,3). O emissivo continua constante 0 e o resto do grafo nao muda."""
    MEL = unreal.MaterialEditingLibrary
    fonte = MEL.get_material_property_input_node(m, unreal.MaterialProperty.MP_OPACITY)
    if fonte is None:
        raise Aborta("%s sem entrada em MP_OPACITY" % m.get_name())
    pres = MEL.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -700, 300)
    pres.set_editor_property("parameter_name", PRESENCA)
    pres.set_editor_property("default_value", 0.0)
    pres.set_editor_property("use_custom_primitive_data", True)
    pres.set_editor_property("primitive_data_index", CPD_INDICE)
    mul = MEL.create_material_expression(m, unreal.MaterialExpressionMultiply, -300, 100)
    if not (MEL.connect_material_expressions(fonte, "", mul, "A") and MEL.connect_material_expressions(pres, "", mul, "B")
            and MEL.connect_material_property(mul, "", unreal.MaterialProperty.MP_OPACITY)):
        raise Aborta("%s: ligar a Presenca em MP_OPACITY falhou" % m.get_name())
    # sob -nullrhi (commandlet) o recompile NAO compila de verdade (Material.cpp:2606, MEDIDO em 05/10): a 1a compilacao real e ao abrir
    # o editor grafico; conferir o Log de Saida por 'Failed to compile Material'
    MEL.recompile_material(m)


def cria_material_fluido(n=NOMES_REAIS):
    """M_LuxVultoSombra_P e M_LuxVultoAura_L1 (copias das do v3 + Presenca) e MI_LuxVultoSombra_L1P (parent a sombra nova, valores de
    SOMBRA_L1P). Idempotente: o que ja existe e reusado (so confere a Presenca). Devolve {'sombra', 'aura', 'mi'}: os 3 objetos."""
    MEL = unreal.MaterialEditingLibrary
    obj = {}
    for chave, origem in (("sombra", M_SOMBRA), ("aura", M_AURA)):
        if EAL.does_asset_exist(n[chave]):
            m = EAL.load_asset(n[chave])
            if PRESENCA not in [str(x) for x in MEL.get_scalar_parameter_names(m)]:
                raise Aborta("%s existe sem a Presenca: estado incompleto (feche o editor sem salvar)" % n[chave])
            w("%s ja existe: mantido" % n[chave])
        else:
            w("duplicando %s -> %s" % (origem, n[chave]))
            m = _duplica(origem, n[chave])
            _multiplica_pela_presenca(m)
        obj[chave] = m
    nova = not EAL.does_asset_exist(n["mi"])
    if nova:
        w("criando %s" % n["mi"])
        pasta, nome = n["mi"].rsplit("/", 1)
        mi = unreal.AssetToolsHelpers.get_asset_tools().create_asset(nome, pasta, unreal.MaterialInstanceConstant,
                                                                      unreal.MaterialInstanceConstantFactoryNew())
        mi.set_editor_property("parent", obj["sombra"])
    else:
        mi = EAL.load_asset(n["mi"])
    mud = nova
    for k, v in SOMBRA_L1P.items():
        if nova or abs(MEL.get_material_instance_scalar_parameter_value(mi, k) - v) > 1e-6:
            MEL.set_material_instance_scalar_parameter_value(mi, k, v)
            mud = True
    if mud:
        MEL.update_material_instance(mi)
    obj["mi"] = mi
    return obj


# ------------------------------------------------------------------ Loop 1 v4: o BP (grafo)
PC, SC, SKC, ACT = "/Script/Engine.PrimitiveComponent:", "/Script/Engine.SceneComponent:", "/Script/Engine.SkeletalMeshComponent:", "/Script/Engine.Actor:"
CLS_LUZ = "/Script/CoreUObject.Class'/Script/Engine.LightComponent'"
LCB = "/Script/Engine.LightComponentBase"


def _disparo(b):
    """Evento.DisparoT (puro): o instante em que o Executar do evento rodou"""
    d = b.v("DisparoT", cls=ale.EVT_C)
    b.lk(b.v("Evento"), d[0], "self")
    return d


def _fator_luz(b):
    """f = SafeDivide(Luz.Intensity, IntensOrig) (puro): a intensidade REAL da luz propria da figura / a original"""
    n = b.v("Intensity", cls=LCB)
    b.lk(b.v("Luz"), n[0], "self")
    d = b.c(KML + "SafeDivide", 0, 0)
    b.lk(n, d, "A")
    b.lk(b.v("IntensOrig"), d, "B")
    return (d, "ReturnValue")


def _cpd(b, valor):
    """Figura.SetCustomPrimitiveDataFloat(CPD_INDICE, valor); valor = (no, pino) ou literal"""
    n = b.c(PC + "SetCustomPrimitiveDataFloat", 0, 0, DataIndex=CPD_INDICE)
    b.lk(b.v("Figura"), n, "self")
    if isinstance(valor, tuple):
        b.lk(valor, n, "Value")
    else:
        b.g.val(n, "Value", valor)
    return n


def _oculta(b, sim):
    n = b.c(SC + "SetHiddenInGame", 0, 0, NewHidden="true" if sim else "false")
    b.lk(b.v("Figura"), n, "self")
    return n


def _clamp01(b, x):
    n = b.c(KML + "FClamp", 0, 0, Min=0.0, Max=1.0)
    b.lk(x, n, "Value")
    return (n, "ReturnValue")


def _divide(b, a, d):
    """SafeDivide(a, d); d = (no, pino) ou literal"""
    n = b.c(KML + "SafeDivide", 0, 0)
    b.lk(a, n, "A")
    if isinstance(d, tuple):
        b.lk(d, n, "B")
    else:
        b.g.val(n, "B", d)
    return (n, "ReturnValue")


def _item(b, arr):
    """arr[NSub - 1] (puro): so e avaliado quando NSub esta entre 1 e Length (o Branch 'valida' guarda)"""
    g = b.c(ale.ARR + "Array_Get", 0, 0)
    b.lk(b.v(arr), g, "TargetArray")
    b.lk(b.op("Subtract_IntInt", b.v("NSub"), 1), g, "Index")
    return (g, "Item")


def _camera(b):
    """posicao da camera do jogador 0 (puro)"""
    pcm = (b.c(GS + "GetPlayerCameraManager", 0, 0, PlayerIndex=0), "ReturnValue")
    cam = b.c("/Script/Engine.PlayerCameraManager:GetCameraLocation", 0, 0)
    b.lk(pcm, cam, "self")
    return (cam, "ReturnValue")


def grafo_fluido(bp, me):
    """As 5 funcoes e o EventGraph do BP_LuxVultoFluido (especificacao: brief de 05/10, secao 2). NENHUM compile aqui dentro: no UE 5.8.3
    criar um no de operador X (Add/Multiply/EqualEqual...) depois de um compile em que ja existia outro do mesmo operador derruba o editor
    (P21, MEDIDO). Ordem da chamada: variaveis -> compile -> funcoes (sem nos) -> compile -> ESTA funcao -> UM compile."""
    # ---------------------------------------------------------------- Inicializar (BeginPlay)
    # P = 0 e escondida; SE ActorLuz valido guarda o LightComponent da luz propria (puro, sem exec) e a intensidade original; SE Evento
    # valido guarda o DisparoT e arma o UNICO timer (loop 0,02 s). Os dois SE sao independentes (brief, secao 2); ActorLuz invalido nunca
    # chega a uma instancia salva: o verificar_mapa exige ActorLuz == a luz propria da figura
    b, en = entrada(bp, "Inicializar", me)
    gc = b.c(ACT + "GetComponentByClass", 0, 0, ComponentClass=CLS_LUZ)
    b.lk(b.v("ActorLuz"), gc, "self")
    b_luz = b.br(b.valido(b.v("ActorLuz")))
    s_luz = b.setv("Luz", src=(gc, "ReturnValue"))
    intens = b.v("Intensity", cls=LCB)
    b.lk(b.v("Luz"), intens[0], "self")
    s_int = b.setv("IntensOrig", src=intens)
    b_evt = b.br(b.valido(b.v("Evento")))
    s_ult = b.setv("UltDisparo", src=_disparo(b))
    tm = b.timer("Atualizar", vc.TIMER_S, loop=True)
    j0 = junc(b)
    b.ch(en, _cpd(b, 0.0), _oculta(b, True), b_luz)
    b.ch((b_luz, "then"), s_luz, s_int, j0)
    b.ch((b_luz, "else"), j0)
    b.ch((j0, "then"), b_evt)
    b.ch((b_evt, "then"), s_ult, tm)

    # ---------------------------------------------------------------- Atualizar (timer): DisparoT novo -> Iniciar (vale tambem com bAtivo: re-disparo
    # reinicia tudo); senao, se bAtivo -> Amostrar
    b, en = entrada(bp, "Atualizar", me)
    b0 = b.br(b.valido(b.v("Evento")))
    b1 = b.br(b.op("NotEqual_DoubleDouble", _disparo(b), b.v("UltDisparo")))
    ini = b.call("Iniciar")
    b2 = b.br(b.v("bAtivo"))
    am = b.call("Amostrar")
    b.ch(en, b0)
    b.ch((b0, "then"), b1)
    b.ch((b1, "then"), ini)
    b.ch((b1, "else"), b2)
    b.ch((b2, "then"), am)

    # ---------------------------------------------------------------- Iniciar
    # zera o estado; bLuzAnt := luz acesa AGORA (f > 0,5; no disparo a luz real ja caiu); P = 0; YawBase uma vez; mostra (P = 0 e luz
    # apagada); poe o pe na fase de contato (FaseIni + TaxaAnim x (Now - T0)) se FaseIni >= 0; ativa
    b, en = entrada(bp, "Iniciar", me)
    s_ult = b.setv("UltDisparo", src=_disparo(b))
    s_t0 = b.setv("T0", src=_disparo(b))
    s_n = b.setv("NSub", 0)
    s_ts = b.setv("TSub", 0.0)
    s_la = b.setv("bLuzAnt", src=b.op("Greater_DoubleDouble", _fator_luz(b), 0.5))
    olha = b.c(KML + "FindLookAtRotation", 0, 0)
    b.lk(b.v("PontoA"), olha, "Start")
    b.lk(_camera(b), olha, "Target")
    qb = b.c(KML + "BreakRotator", 0, 0)
    b.lk((olha, "ReturnValue"), qb, "InRot")
    s_yaw = b.setv("YawBase", src=(qb, "Yaw"))
    b_fase = b.br(b.op("GreaterEqual_DoubleDouble", b.v("FaseIni"), 0.0))
    avanco = b.op("Multiply_DoubleDouble", b.v("TaxaAnim"), b.menos_agora("T0"))                     # TaxaAnim x (Now - T0)
    fase = b.op("Subtract_DoubleDouble", b.v("FaseIni"), b.op("Multiply_DoubleDouble", avanco, -1.0))  # FaseIni + avanco (sem Add)
    sp = b.c(SKC + "SetPosition", 0, 0, bFireNotifies="false")
    b.lk(b.v("Figura"), sp, "self")
    b.lk(fase, sp, "InPos")
    j = junc(b)
    s_at = b.setv("bAtivo", "true")
    b.ch(en, s_ult, s_t0, s_n, s_ts, s_la, _cpd(b, 0.0), s_yaw, _oculta(b, False), b_fase)
    b.ch((b_fase, "then"), sp, j)
    b.ch((b_fase, "else"), j)
    b.ch((j, "then"), s_at)

    # ---------------------------------------------------------------- Encerrar
    b, en = entrada(bp, "Encerrar", me)
    b.ch(en, _cpd(b, 0.0), _oculta(b, True), b.setv("bAtivo", "false"))

    # ---------------------------------------------------------------- Amostrar (a cada 0,02 s enquanto bAtivo)
    b, en = entrada(bp, "Amostrar", me)
    # 1. f = Intensity / IntensOrig; L = FClamp((f - 0,2) / 0,6); acesa = f > 0,5
    f = _fator_luz(b)
    L = _clamp01(b, _divide(b, b.op("Subtract_DoubleDouble", f, 0.2), 0.6))
    acesa = b.op("Greater_DoubleDouble", f, 0.5)
    # 2. subida REAL da luz (acesa e antes apagada): NSub + 1 (Subtract(NSub, -1): sem Add) e TSub := Now; depois bLuzAnt := acesa
    b_sub = b.br(b.e(acesa, b.nao(b.v("bLuzAnt"))))
    s_n = b.setv("NSub", src=b.op("Subtract_IntInt", b.v("NSub"), -1))
    s_ts = b.setv("TSub", src=b.now())
    j1 = junc(b)
    s_la = b.setv("bLuzAnt", src=acesa)
    # 3. janela valida: 1 <= NSub <= Length(JanAcesa); Dur = JanAcesa[NSub-1]
    ln = b.c(ale.ARR + "Array_Length", 0, 0)
    b.lk(b.v("JanAcesa"), ln, "TargetArray")
    b_val = b.br(b.e(b.op("Greater_IntInt", b.v("NSub"), 0), b.op("LessEqual_IntInt", b.v("NSub"), (ln, "ReturnValue"))))
    dec = b.op("Subtract_DoubleDouble", b.now(), b.v("TSub"))                                   # Now - TSub
    p_in = _clamp01(b, _divide(b, dec, b.v("EntradaS")))                                         # entrada
    resta = b.op("Subtract_DoubleDouble", b.op("Subtract_DoubleDouble", _item(b, "JanAcesa"), b.v("MargemS")), dec)   # Dur - Margem - (Now - TSub)
    p_out = _clamp01(b, _divide(b, resta, b.v("SaidaS")))                                        # saida
    pmin = b.c(KML + "FMin", 0, 0)
    b.lk(p_in, pmin, "A")
    b.lk(p_out, pmin, "B")
    err = b.c(KML + "Abs", 0, 0)                                                                  # |(TSub - T0) - TSubNom[NSub-1]|
    b.lk(b.op("Subtract_DoubleDouble", b.op("Subtract_DoubleDouble", b.v("TSub"), b.v("T0")), _item(b, "TSubNom")), err, "A")
    sel = b.c(KML + "SelectFloat", 0, 0, A=1.0, B=0.0)                                            # ok ? 1 : 0
    b.lk(b.op("Less_DoubleDouble", (err, "ReturnValue"), b.v("TolS")), sel, "bPickA")
    p_base = b.op("Multiply_DoubleDouble", b.op("Multiply_DoubleDouble", (pmin, "ReturnValue"), L), (sel, "ReturnValue"))
    # posicao pelo relogio absoluto: alfa = FClamp(((Now - T0) - TMovI) / (TMovF - TMovI)); pos = VLerp(PontoA, PontoB, alfa)
    alfa = _clamp01(b, _divide(b, b.op("Subtract_DoubleDouble", b.menos_agora("T0"), b.v("TMovI")),
                               b.op("Subtract_DoubleDouble", b.v("TMovF"), b.v("TMovI"))))
    lerp = b.c(KML + "VLerp", 0, 0)
    b.lk(b.v("PontoA"), lerp, "A")
    b.lk(b.v("PontoB"), lerp, "B")
    b.lk(alfa, lerp, "Alpha")
    pos = (lerp, "ReturnValue")
    # 4. protecao de camera: P x FClamp((Dist2D(pos, camera) - DistMinCam) / (DistPlenaCam - DistMinCam))
    d2 = b.c(KML + "Vector_Distance2D", 0, 0)
    b.lk(pos, d2, "V1")
    b.lk(_camera(b), d2, "V2")
    guarda = _clamp01(b, _divide(b, b.op("Subtract_DoubleDouble", (d2, "ReturnValue"), b.v("DistMinCam")),
                                 b.op("Subtract_DoubleDouble", b.v("DistPlenaCam"), b.v("DistMinCam"))))
    s_p = b.setv("PAtual", src=b.op("Multiply_DoubleDouble", p_base, guarda))                    # janela valida
    s_p0 = b.setv("PAtual", 0.0)                                                                  # fora das janelas
    j2 = junc(b)
    # 5. UM so SetCustomPrimitiveDataFloat (P = 0 tambem fora da janela)
    cpd = _cpd(b, b.v("PAtual"))
    # 6. posicao e yaw SEMPRE (a figura anda no escuro): bEncarar -> YawBase + OffsetYaw x (1 - FClamp((Now - T0) / DuracaoS)), senao YawFixo
    giro = _clamp01(b, _divide(b, b.menos_agora("T0"), b.v("DuracaoS")))
    yaw_enc = b.op("Subtract_DoubleDouble", b.v("YawBase"), b.op("Multiply_DoubleDouble", b.v("OffsetYaw"), b.op("Subtract_DoubleDouble", giro, 1.0)))
    ysel = b.c(KML + "SelectFloat", 0, 0)
    b.lk(yaw_enc, ysel, "A")
    b.lk(b.v("YawFixo"), ysel, "B")
    b.lk(b.v("bEncarar"), ysel, "bPickA")
    rot = b.c(KML + "MakeRotator", 0, 0, Roll=0.0, Pitch=0.0)
    b.lk((ysel, "ReturnValue"), rot, "Yaw")
    sloc = b.c(ACT + "K2_SetActorLocationAndRotation", 0, 0, bSweep="false", bTeleport="true")
    b.lk(pos, sloc, "NewLocation")
    b.lk((rot, "ReturnValue"), sloc, "NewRotation")
    # 7. log (so se bLog): formato FIXO "[FLUIDO] t= f= L= NSub= P= x= y=" (o harness do PIE le)
    b_log = b.br(b.v("bLog"))
    bv = b.c(KML + "BreakVector", 0, 0)
    b.lk(pos, bv, "InVec")
    pr = b.c(KSL + "PrintString", 0, 0, bPrintToScreen="false", bPrintToLog="true")
    b.lk(b.s(["[FLUIDO] t=", b.fs(b.menos_agora("T0")), " f=", b.fs(f), " L=", b.fs(L), " NSub=", b.is_(b.v("NSub")), " P=",
              b.fs(b.v("PAtual")), " x=", b.fs((bv, "X")), " y=", b.fs((bv, "Y"))]), pr, "InString")
    j3 = junc(b)
    # 8. fim: Now - T0 >= DuracaoS -> Encerrar
    b_fim = b.br(b.op("GreaterEqual_DoubleDouble", b.menos_agora("T0"), b.v("DuracaoS")))
    enc = b.call("Encerrar")
    b.ch(en, b_sub)
    b.ch((b_sub, "then"), s_n, s_ts, j1)
    b.ch((b_sub, "else"), j1)
    b.ch((j1, "then"), s_la, b_val)
    b.ch((b_val, "then"), s_p, j2)
    b.ch((b_val, "else"), s_p0, j2)
    b.ch((j2, "then"), cpd, sloc, b_log)
    b.ch((b_log, "then"), pr, j3)
    b.ch((b_log, "else"), j3)
    b.ch((j3, "then"), b_fim)
    b.ch((b_fim, "then"), enc)

    # ---------------------------------------------------------------- EventGraph
    ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
    g = G(ge)
    bpl = g.pos(BEL.add_event_override(bp, "ReceiveBeginPlay", unreal.IntPoint(0, 0)), 0, 0)
    g.chain(bpl, g.call(me + ":Inicializar", 300, 0))


def cria_bp_fluido(n=NOMES_REAIS, mats=None):
    """BP NOVO (nome sem o prefixo BP_LuxVultoQuadros): componente Figura (SKM_Manny_Simple, rotacao -90, escala ESCALA_FIGURA, sem colisao
    e sem sombra, ALWAYS_TICK_POSE, escondida, corpo MI_SOMBRA_L1P, aura M_AURA_L1) + variaveis + 5 funcoes. UM compile com nos (P21),
    erros_bp vazio ou Aborta, VersaoFluido no CDO e um compile final (sem no novo). `mats` = {'mi', 'aura'} com os objetos (o ensaio nao
    reabre por caminho os ZZ_* que so existem em memoria)."""
    mats = mats or {k: EAL.load_asset(n[k]) for k in ("mi", "aura")}
    w("criando %s" % n["bp"])
    bp = BEL.create_blueprint_asset_with_parent(n["bp"], unreal.Actor)
    me = MEF if n["bp"] == BPF else n["bp"] + "." + n["bp"].rsplit("/", 1)[-1] + "_C"
    t = ale.tipos_base()
    t["evt"] = BEL.get_object_reference_type(EAL.load_asset(ale.EVT).generated_class())
    t["lc"] = BEL.get_object_reference_type(unreal.LightComponent.static_class())
    w("  componente Figura")
    _, fig = ale.add_comp(bp, unreal.SkeletalMeshComponent, "Figura")
    fig.set_editor_property("skeletal_mesh_asset", EAL.load_asset(SKM))
    fig.set_editor_property("animation_mode", unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    fig.set_editor_property("animation_data", unreal.SingleAnimationPlayData(anim_to_play=EAL.load_asset(ANIM_IDLE), saved_looping=True,
                                                                               saved_playing=True, saved_position=0.0, saved_play_rate=1.0))
    nslots = len(EAL.load_asset(SKM).get_editor_property("materials"))
    fig.set_editor_property("override_materials", [mats["mi"]] * nslots)
    fig.set_editor_property("overlay_material", mats["aura"])
    fig.set_collision_profile_name("NoCollision")
    fig.set_editor_property("cast_shadow", False)
    fig.set_editor_property("hidden_in_game", True)
    fig.set_editor_property("visibility_based_anim_tick_option", unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE)
    fig.set_editor_property("relative_rotation", unreal.Rotator(0, 0, -90))  # manequim olha para +Y; o ator olha para +X
    fig.set_editor_property("relative_scale3d", unreal.Vector(*ESCALA_FIGURA))
    w("  variaveis")
    ale.cria_vars(bp, VARS_FLUIDO, t, "LUX Vulto")
    BEL.compile_blueprint(bp)            # sem nos ainda: seguro
    ale.padroes(bp, [v for v in VARS_FLUIDO if v[3] is not None])
    w("  funcoes")
    ale.cria_funcoes(bp, [(nome, []) for nome in FUNCOES_FLUIDO], t)
    BEL.compile_blueprint(bp)            # sem nos ainda: seguro
    w("  grafos (nenhum compile ate o fim)")
    grafo_fluido(bp, me)
    BEL.compile_blueprint(bp)            # o UNICO compile com nos
    e = ale.erros_bp(bp)
    if e or bp.get_editor_property("status") != unreal.BlueprintStatus.BS_UP_TO_DATE:
        raise Aborta("BP_LuxVultoFluido com erros/avisos (nada salvo): %s | status %s" % (e, bp.get_editor_property("status")))
    unreal.get_default_object(bp.generated_class()).set_editor_property("VersaoFluido", VERSAO_FLUIDO)
    BEL.compile_blueprint(bp)            # so o CDO mudou: nenhum no novo
    w("  BP limpo")
    return bp


def ensure_bp_fluido(n=NOMES_REAIS, mats=None):
    if n["bp"].startswith("/Game") and EAL.does_asset_exist(n["bp"]):
        bp = EAL.load_asset(n["bp"])
        if unreal.get_default_object(bp.generated_class()).get_editor_property("VersaoFluido") != VERSAO_FLUIDO:
            raise Aborta("%s existe sem VersaoFluido=%d: estado incompleto ou outra versao (feche o editor sem salvar; a mudanca de versao "
                         "pede nome novo ou apagar o asset)" % (n["bp"], VERSAO_FLUIDO))
        w("BP_LuxVultoFluido v%d ja existe: mantido" % VERSAO_FLUIDO)
        return bp, False
    return cria_bp_fluido(n, mats), True


# ------------------------------------------------------------------ Loop 1 v4: figuras no mapa
def _unreal(v):
    """tupla (x, y, z) -> Vector; o resto passa direto"""
    return unreal.Vector(*v) if isinstance(v, tuple) else v


def ensure_l1_figuras(bpf, n=NOMES_REAIS):
    """Uma instancia de BP_LuxVultoFluido por evento do Loop 1: dados de instancia de vc.dados_instancia() (nenhum numero copiado a mao),
    ActorLuz = a luz propria da figura, animacao TOCANDO (animation_data da instancia), corpo MI_SOMBRA_L1P e aura. Figura de OUTRA classe
    com o mesmo label (BP_LuxVultoQuadros, BP_LuxVultoCorre) e destruida e recriada (mesmo label, pasta e tag)."""
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    mi, aura = EAL.load_asset(n["mi"]), EAL.load_asset(n["aura"])
    n_mat = len(EAL.load_asset(SKM).get_editor_property("materials"))
    mud = []
    for cfg in FIGURAS_L1:
        dados = vc.dados_instancia(cfg["chave"])
        lst = [x for x in ale.atores() if x.get_actor_label() == cfg["label"]]
        if len(lst) > 1:
            raise Aborta("mais de um %s" % cfg["label"])
        a = lst[0] if lst else None
        if a and a.get_class().get_name() != CLASSE_FLUIDO:
            w("  %s era %s: recriado como %s" % (cfg["label"], a.get_class().get_name(), CLASSE_FLUIDO))
            eas.destroy_actor(a)
            a = None
        yaw0 = vc.YAW0_VULTO if cfg["chave"] == "vulto" else dados["YawFixo"]
        p0, r0 = unreal.Vector(*dados["PontoA"]), unreal.Rotator(0.0, 0.0, yaw0)
        if not a:
            a = eas.spawn_actor_from_class(bpf.generated_class(), p0, r0)
            a.set_actor_label(cfg["label"])
            a.set_folder_path(ale.FOLDER)
            a.set_editor_property("tags", [unreal.Name(ale.TAG)])
            mud.append(cfg["label"])
        ev, luz = ale.por_label(cfg["evento"]), ale.por_label(cfg["luz"])
        if not ev:
            raise Aborta("%s nao encontrado (rode add_loop_events.py instalar)" % cfg["evento"])
        if not luz:
            raise Aborta("%s nao encontrada (a etapa mapa cria as luzes antes das figuras)" % cfg["luz"])
        quer = {k: _unreal(v) for k, v in dados.items()}
        quer.update(Evento=ev, ActorLuz=luz)
        for k, v in quer.items():
            if not igual(a.get_editor_property(k), v):
                a.set_editor_property(k, v)
                mud.append("%s.%s" % (cfg["label"], k))
        if (a.get_actor_location() - p0).length() > 0.5 or abs(a.get_actor_rotation().yaw - yaw0) > 0.1:
            a.set_actor_location_and_rotation(p0, r0, False, True)
            mud.append("%s transform" % cfg["label"])
        fig = a.get_components_by_class(unreal.SkeletalMeshComponent)[0]
        anim = EAL.load_asset(cfg["anim"])
        play = fig.get_editor_property("animation_data")
        if (play.get_editor_property("anim_to_play") != anim or not play.get_editor_property("saved_playing")
                or not play.get_editor_property("saved_looping") or abs(play.get_editor_property("saved_play_rate") - dados["TaxaAnim"]) > 1e-6):
            fig.set_editor_property("animation_data", unreal.SingleAnimationPlayData(anim_to_play=anim, saved_looping=True, saved_playing=True,
                                                                                       saved_position=0.0, saved_play_rate=dados["TaxaAnim"]))
            mud.append("%s anim" % cfg["label"])
        mats = list(fig.get_editor_property("override_materials"))
        if len(mats) != n_mat or any(m_ != mi for m_ in mats):
            fig.set_editor_property("override_materials", [mi] * n_mat)
            mud.append("%s material" % cfg["label"])
        if fig.get_editor_property("overlay_material") != aura:
            fig.set_editor_property("overlay_material", aura)
            mud.append("%s aura" % cfg["label"])
    return mud


# ------------------------------------------------------------------ verificar
def livre(world, p, folga=0.0):
    """None se a capsula da figura (raio CAPSULA[0] + folga) em p nao encosta em nada no canal Visibility; senao o label de quem bate"""
    r, hh = CAPSULA
    c = unreal.Vector(p.x, p.y, p.z + hh + 4.0)
    h = unreal.SystemLibrary.capsule_trace_single(world, c, c + unreal.Vector(0, 0, 1.0), r + folga, hh, VIS, False, [],
                                                  unreal.DrawDebugTrace.NONE, True)
    if not h:
        return None
    quem = h.to_tuple()[9]
    return quem.get_actor_label() if quem else "?"


def chao(world, p):
    h = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(p.x, p.y, p.z + 150.0), unreal.Vector(p.x, p.y, p.z - 150.0), VIS, False, [],
                                               unreal.DrawDebugTrace.NONE, True)
    return h.to_tuple()[4].z if h else None


def _nos(bp, nome):
    """nos do grafo `nome` do BP, ou [] se a funcao nao existe"""
    if nome not in [str(x) for x in BEL.list_graph_names(bp)]:
        return []
    return list(BGE.get_graph_editor_by_name(bp, nome).list_all_nodes())


def _tem_no(bp, nome, *pinos):
    """True se o grafo `nome` tem um no com TODOS estes pinos de entrada (pelo nome interno do pino, que nao e traduzido: o titulo do no
    muda com o idioma do editor). Lista os pinos em vez de find_input_pin: este loga 'Missing input pin named' (um aviso por no sem o pino;
    eram 264 por verificar_assets, medido em 05/10)."""
    quer = set(pinos)
    return any(quer <= {str(p.get_pin_name()) for p in x.list_input_pins()} for x in _nos(bp, nome))


def _entrada_presenca(m):
    """(Multiply de MP_OPACITY, ScalarParameter Presenca ligado a ele ou None)"""
    MEL = unreal.MaterialEditingLibrary
    mul = MEL.get_material_property_input_node(m, unreal.MaterialProperty.MP_OPACITY)
    if not isinstance(mul, unreal.MaterialExpressionMultiply):
        return mul, None
    for x in MEL.get_inputs_for_material_expression(m, mul):
        if isinstance(x, unreal.MaterialExpressionScalarParameter) and str(x.get_editor_property("parameter_name")) == PRESENCA:
            return mul, x
    return mul, None


def verificar_assets(n=NOMES_REAIS, obj=None):
    """Metade do verificar que NAO precisa de mapa (roda no commandlet, so leitura): animacao, materiais (Presenca em CPD, emissivo 0,
    originais intactos), MI, BP (sem erros, versao, funcoes, SetCustomPrimitiveDataFloat, padroes, Figura) e as regras do cronograma
    sobre os numeros do desenho (vulto_cronograma.verifica). `obj` = {'bp','sombra','aura','mi'} com os objetos ja carregados (o ensaio,
    cujos assets so existem em memoria); sem `obj`, abre por caminho. Devolve a lista de falhas."""
    MEL = unreal.MaterialEditingLibrary
    f = []
    for pth in (ANIM_ANDAR, M_SOMBRA, M_AURA, MI_SOMBRA_L1):
        if not EAL.does_asset_exist(pth):
            f.append("asset ausente: %s" % pth)
    for k, pth in n.items():
        if not (obj[k] if obj else EAL.does_asset_exist(pth)):
            f.append("asset ausente: %s" % pth)
    if f:
        w("verificar_assets: FAIL %s" % f)
        return f
    pega = lambda k: obj[k] if obj else EAL.load_asset(n[k])
    if not EAL.load_asset(ANIM_ANDAR).get_editor_property("force_root_lock"):
        f.append("A_LuxVultoAndar sem ForceRootLock")
    for orig in (M_SOMBRA, M_AURA):   # v3 intacto: sem Presenca
        if PRESENCA in [str(x) for x in MEL.get_scalar_parameter_names(EAL.load_asset(orig))]:
            f.append("%s (original) ganhou a %s: nao pode mudar" % (orig, PRESENCA))
    sombra, aura = pega("sombra"), pega("aura")
    for rot, m in (("sombra", sombra), ("aura", aura)):
        if (m.get_editor_property("blend_mode") != unreal.BlendMode.BLEND_TRANSLUCENT or
                m.get_editor_property("shading_model") != unreal.MaterialShadingModel.MSM_UNLIT):
            f.append("%s: nao e unlit translucido" % n[rot])
        nomes = [str(x) for x in MEL.get_scalar_parameter_names(m)]
        if nomes.count(PRESENCA) != 1:
            f.append("%s: %d parametros '%s' (esperado 1)" % (n[rot], nomes.count(PRESENCA), PRESENCA))
        mul, pres = _entrada_presenca(m)
        if pres is None:
            f.append("%s: MP_OPACITY nao e um Multiply com a %s" % (n[rot], PRESENCA))
        elif not pres.get_editor_property("use_custom_primitive_data") or pres.get_editor_property("primitive_data_index") != CPD_INDICE:
            f.append("%s: %s sem Custom Primitive Data no indice %d" % (n[rot], PRESENCA, CPD_INDICE))
        elif abs(pres.get_editor_property("default_value")) > 1e-9:
            f.append("%s: %s com padrao != 0" % (n[rot], PRESENCA))
        emi = MEL.get_material_property_input_node(m, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        cor = emi.get_editor_property("constant") if isinstance(emi, unreal.MaterialExpressionConstant3Vector) else None
        if not cor or max(cor.r, cor.g, cor.b) > 0.0:
            f.append("%s: emissivo != 0 (no escuro a exposicao multiplica o emissivo por ~213 e o vulto clareia)" % n[rot])
    if not sombra.get_editor_property("used_with_skeletal_mesh"):
        f.append("%s: sem used_with_skeletal_mesh" % n["sombra"])
    if not MEL.get_material_property_input_node(sombra, unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET):
        f.append("%s sem entrada em WORLD_POSITION_OFFSET (o tremor do contorno)" % n["sombra"])
    for k in SOMBRA_L1:
        if k not in [str(x) for x in MEL.get_scalar_parameter_names(sombra)]:
            f.append("%s perdeu o parametro %s" % (n["sombra"], k))
    mi = pega("mi")
    if mi.get_editor_property("parent") != sombra:
        f.append("%s nao deriva de %s" % (n["mi"], n["sombra"]))
    for k, v in SOMBRA_L1P.items():
        if abs(MEL.get_material_instance_scalar_parameter_value(mi, k) - v) > 1e-4:
            f.append("%s.%s != %s" % (n["mi"], k, v))
    bp = pega("bp")
    f += ["BP_LuxVultoFluido: %s" % e for e in ale.erros_bp(bp)]
    if bp.get_editor_property("status") != unreal.BlueprintStatus.BS_UP_TO_DATE:
        f.append("BP_LuxVultoFluido: status %s (esperado UP_TO_DATE)" % bp.get_editor_property("status"))
    cdo = unreal.get_default_object(bp.generated_class())
    if cdo.get_editor_property("VersaoFluido") != VERSAO_FLUIDO:
        f.append("BP_LuxVultoFluido sem VersaoFluido=%d" % VERSAO_FLUIDO)
    vars_bp = [str(x) for x in BEL.list_member_variable_names(bp)]
    f += ["BP_LuxVultoFluido: variavel %s ausente" % v[0] for v in VARS_FLUIDO if v[0] not in vars_bp]
    for nome in FUNCOES_FLUIDO:
        if len(_nos(bp, nome)) < 3:
            f.append("BP_LuxVultoFluido: funcao %s ausente/vazia (< 3 nos)" % nome)
    for nome in ("Amostrar", "Encerrar"):
        if not _tem_no(bp, nome, "DataIndex", "Value"):
            f.append("BP_LuxVultoFluido.%s sem SetCustomPrimitiveDataFloat (pinos DataIndex/Value)" % nome)
    if not _tem_no(bp, "Amostrar", "NewLocation", "NewRotation") or not _tem_no(bp, "Amostrar", "V1", "V2"):
        f.append("BP_LuxVultoFluido.Amostrar sem a posicao (NewLocation/NewRotation) ou a protecao de camera (Vector_Distance2D: V1/V2)")
    for k, v in vc.PADROES_BP.items():
        atual = cdo.get_editor_property(k)
        if (abs(atual - v) > 1e-6) if isinstance(v, float) else (atual != v):
            f.append("BP_LuxVultoFluido: padrao %s = %s (esperado %s)" % (k, atual, v))
    fig = ale.comp_template(bp, "Figura")
    if fig is None:
        f.append("BP_LuxVultoFluido sem o componente Figura")
    else:
        if not fig.get_editor_property("hidden_in_game"):
            f.append("Figura visivel no jogo por padrao")
        if fig.get_collision_profile_name() != "NoCollision" or fig.get_editor_property("cast_shadow"):
            f.append("Figura com colisao ou sombra")
        if fig.get_editor_property("overlay_material") != aura:
            f.append("Figura: aura != %s" % n["aura"])
        if any(m_ != mi for m_ in fig.get_editor_property("override_materials")):
            f.append("Figura: corpo != %s em algum slot" % n["mi"])
        if (fig.get_editor_property("relative_scale3d") - unreal.Vector(*ESCALA_FIGURA)).length() > 1e-3:
            f.append("Figura: escala != %s" % (ESCALA_FIGURA,))
        if fig.get_editor_property("visibility_based_anim_tick_option") != unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE:
            f.append("Figura: sem ALWAYS_TICK_POSE (o pe nao anda escondida por ocultacao)")
    for chave in ("vulto", "passos"):   # as regras do cronograma sobre os numeros do desenho
        f += ["cronograma/%s: %s %s" % (chave, regra, msg) for regra, msg in vc.verifica(vc.dados_novo(chave))]
    w("verificar_assets:", ("FAIL %s" % f) if f else "PASS")
    return f


def _vals(a, chaves):
    """valores de instancia do ator `a` no formato de vc.dados_instancia (Vector -> tupla, array -> lista)"""
    out = {}
    for k in chaves:
        v = a.get_editor_property(k)
        if isinstance(v, unreal.Vector):
            v = (v.x, v.y, v.z)
        elif not isinstance(v, (bool, int, float, str)):
            v = list(v)
        out[k] = v
    return out


def verificar_mapa(n=NOMES_REAIS):
    """Metade do verificar que PRECISA do mapa (editor, fora do PIE): luzes do Loop 1, as duas figuras (classe exata, evento, luz, dados de
    instancia == vulto_cronograma, regras do cronograma sobre os VALORES REAIS dos atores, componente), e a varredura de capsula, chao e
    folga a cada <= 10 cm em TODO o percurso. Devolve a lista de falhas."""
    f = []
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
    mi, aura = EAL.load_asset(n["mi"]), EAL.load_asset(n["aura"])
    for cfg in FIGURAS_L1:
        lab, chave = cfg["label"], cfg["chave"]
        dados = vc.dados_instancia(chave)
        lst = [x for x in ale.atores() if x.get_actor_label() == lab]
        if len(lst) != 1:
            f.append("esperava 1 %s (%d)" % (lab, len(lst)))
            continue
        a = lst[0]
        if a.get_class().get_name() != CLASSE_FLUIDO:      # igualdade exata: o startswith do v3 aceitaria o BP_LuxVultoQuadros
            f.append("%s e %s (esperado %s)" % (lab, a.get_class().get_name(), CLASSE_FLUIDO))
            continue
        ev, luz = a.get_editor_property("Evento"), a.get_editor_property("ActorLuz")
        if not ev or ev.get_actor_label() != cfg["evento"]:
            f.append("%s: Evento nao aponta para %s" % (lab, cfg["evento"]))
            continue
        if not luz or luz.get_actor_label() != cfg["luz"]:
            f.append("%s: ActorLuz != %s" % (lab, cfg["luz"]))
        elif ale.TAG_CORREDOR not in [str(t) for t in luz.tags]:
            f.append("%s: a luz %s nao tem a tag %s (o evento nao a apagaria)" % (lab, cfg["luz"], ale.TAG_CORREDOR))
        if ev.get_editor_property("bAparicao"):
            f.append("%s ainda com bAparicao (a silhueta estatica branca voltaria)" % cfg["evento"])
        if unreal.get_default_object(a.get_class()).get_editor_property("VersaoFluido") != VERSAO_FLUIDO:
            f.append("%s: classe sem VersaoFluido=%d" % (lab, VERSAO_FLUIDO))
        # dados de instancia == cronograma (fonte unica)
        for k, v in dados.items():
            if not igual(a.get_editor_property(k), _unreal(v)):
                f.append("%s.%s = %s (esperado %s)" % (lab, k, a.get_editor_property(k), v))
        # regras do cronograma sobre os valores REAIS dos atores (luz, visibilidade, posicao, animacao, som)
        fig = a.get_components_by_class(unreal.SkeletalMeshComponent)[0]
        play = fig.get_editor_property("animation_data")
        figv = _vals(a, dados.keys())
        figv.update(saved_playing=bool(play.get_editor_property("saved_playing")), saved_play_rate=play.get_editor_property("saved_play_rate"))
        ps = [c for c in ev.get_components_by_class(unreal.SceneComponent) if c.get_name().startswith("PontoSom")][0].get_world_location()
        evtv = _vals(ev, ("PadraoPiscar", "bApagarNoFim", "RestaurarAposS", "Repeticoes", "IntervaloRepS", "DeslocPorRep"))
        evtv["PontoSom"] = (ps.x, ps.y, ps.z)
        f += ["%s: %s %s" % (lab, regra, msg) for regra, msg in vc.verifica(vc.dados_de_instancia(chave, figv, evtv))]
        # percurso: capsula livre, chao (+-5 cm) e folga de FOLGA_PAREDE cm a cada <= 10 cm, em TODA a reta D / reposicao V0-V1
        for i, p in enumerate(vc.pontos_percurso(chave)):
            v = unreal.Vector(*p)
            b_ = livre(world, v)
            if b_:
                f.append("%s: ponto %d do percurso (%.0f, %.0f) encosta em %s" % (lab, i, p[0], p[1], b_))
            else:
                b_ = livre(world, v, FOLGA_PAREDE)
                if b_:
                    f.append("%s: ponto %d do percurso (%.0f, %.0f) a menos de %.0f cm de %s" % (lab, i, p[0], p[1], FOLGA_PAREDE, b_))
            z = chao(world, v)
            if z is None or abs(z - p[2]) > 5.0:
                f.append("%s: ponto %d do percurso fora do chao (chao em z %s)" % (lab, i, z))
        # componente
        if not fig.get_editor_property("hidden_in_game"):
            f.append("%s: Figura visivel no jogo por padrao" % lab)
        if fig.get_collision_profile_name() != "NoCollision" or fig.get_editor_property("cast_shadow"):
            f.append("%s: Figura com colisao ou sombra" % lab)
        if fig.get_editor_property("overlay_material") != aura:
            f.append("%s: aura != %s" % (lab, n["aura"]))
        if any(m_ != mi for m_ in fig.get_editor_property("override_materials")):
            f.append("%s: material do corpo != %s" % (lab, n["mi"]))
        if (fig.get_editor_property("relative_scale3d") - unreal.Vector(*ESCALA_FIGURA)).length() > 1e-3:
            f.append("%s: escala da Figura != %s" % (lab, ESCALA_FIGURA))
        if play.get_editor_property("anim_to_play") != EAL.load_asset(cfg["anim"]) or not play.get_editor_property("saved_looping"):
            f.append("%s: animacao != %s em loop" % (lab, cfg["anim"]))
        if cfg["anim"] == ANIM_ANDAR and not EAL.load_asset(ANIM_ANDAR).get_editor_property("force_root_lock"):
            f.append("%s: A_LuxVultoAndar sem ForceRootLock (anda na propria raiz e 'respawna')" % lab)
    lf = [x for x in ale.atores() if x.get_actor_label() == LUZ_FUNDO]
    if lf and sorted(str(t) for t in lf[0].tags) != sorted([ale.TAG, "LOOP2_ON", "LOOP3_OFF"]):
        f.append("%s (loop 2) teve as tags alteradas" % LUZ_FUNDO)
    w("verificar_mapa:", ("FAIL %s" % f) if f else "PASS")
    return f


def verificar_l1():
    f = verificar_assets() + verificar_mapa()
    w("verificar_l1:", ("FAIL %s" % f) if f else "PASS")
    return f


# ------------------------------------------------------------------ instalar / desfazer (Loop 1 v4)
def _sujos():
    """pacotes sujos; [] se o commandlet nao expuser os de mapa"""
    try:
        return ale.sujos()
    except Exception:
        return sorted(p.get_name() for p in list(unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()))


def instalar_l1_assets(n=NOMES_REAIS, salvar=None):
    """ETAPA 'assets' (COMMANDLET, editor grafico FECHADO: P21 derruba o editor se ja houve compile com o mesmo operador; sem mapa e sem
    LevelEditorSubsystem): confere que os assets do v3 batem (nao muda nenhum), cria o que falta dos 4 novos, roda verificar_assets e salva
    SO os 4 (os valores de `n`). Carregar o BP_LuxLoopEvent suja um pacote alheio no commandlet (AS_Flashlight_Inspection_Montage): nao e
    salvo. `n`/`salvar` so mudam num ensaio da propria etapa com outros nomes e um `salvar` que nao grava."""
    salvar = salvar or (lambda o: EAL.save_loaded_asset(o, False))
    if not os.environ.get("LUX_CMDLET"):
        raise Aborta("a etapa 'assets' gera Blueprint com nos: rode no COMMANDLET (lux_cmdlet_l1.py assets), nunca no editor grafico (P21)")
    if _sujos():
        raise Aborta("ha pacotes nao salvos antes de comecar: %s" % _sujos())
    v3 = ensure_l1_assets()
    if v3:
        raise Aborta("os assets do v3 mudariam (%s): estado inesperado, nada salvo" % [x.get_path_name() for x in v3])
    mats = cria_material_fluido(n)
    bp, criou = ensure_bp_fluido(n, mats)
    obj = dict(mats, bp=bp)
    f = verificar_assets(n, obj)
    if f:
        raise Aborta("verificar_assets FAIL (nada salvo): %s" % f)
    sujos = _sujos()
    for k in ("sombra", "aura", "mi", "bp"):
        if n[k] in sujos or (k == "bp" and criou):          # o BP recem-criado e salvo mesmo que o pacote nao conste como sujo
            if not salvar(obj[k]):
                raise Aborta("o save falhou em %s" % n[k])
            w("salvo", n[k])
    w("pacotes ainda sujos, NAO salvos (alheios ao Loop 1):", [p for p in _sujos() if p not in n.values()] or "nenhum")
    w("assets prontos: %s | proximo passo: instalar_l1 mapa (editor grafico, fora do PIE)" % ", ".join(n.values()))


def ensaio_l1_assets():
    """ENSAIO em memoria (COMMANDLET, nada salvo): cria o conjunto com NOMES_ENSAIO (BP em /Temp/LuxProbe, materiais ZZ_* no DIR) e roda
    verificar_assets nele. Prova que o gerador compila limpo antes de gravar os 4 assets reais."""
    if not os.environ.get("LUX_CMDLET"):
        raise Aborta("o ensaio gera Blueprint com nos: rode no COMMANDLET (lux_cmdlet_l1.py ensaio)")
    mats = cria_material_fluido(NOMES_ENSAIO)
    bp, _ = ensure_bp_fluido(NOMES_ENSAIO, mats)
    f = verificar_assets(NOMES_ENSAIO, dict(mats, bp=bp))
    w("ensaio:", ("FAIL %s" % f) if f else "PASS", "| pacotes sujos em memoria (nada foi salvo):", _sujos())
    return f


def instalar_l1_mapa():
    """ETAPA 'mapa' (EDITOR grafico, fora do PIE; o Mapa_B e LFS: avise antes de salvar): confere os 4 assets (verificar_assets), poe as
    luzes do Loop 1 e as duas figuras BP_LuxVultoFluido (destroi e recria as do v3 com o mesmo label), roda o verificar completo e
    SO ENTAO salva o Mapa_B."""
    if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():
        raise Aborta("feche o PIE")
    if not set(ale.sujos()) <= {"/Game/Masion/Mapa_B"}:
        raise Aborta("ha pacotes nao salvos antes de comecar: %s" % ale.sujos())
    f = verificar_assets()
    if f:
        raise Aborta("verificar_assets FAIL (rode a etapa 'assets' no commandlet): %s" % f)
    bpf = EAL.load_asset(BPF)
    mud = ensure_l1_luz() + ensure_l1_figuras(bpf)
    w("mudou (loop 1):", mud or "nada")
    f = verificar_mapa()
    if f:
        raise Aborta("verificar_mapa FAIL (nada salvo): %s" % f)
    U = unreal.EditorLoadingAndSavingUtils
    mapa = [p for p in U.get_dirty_map_packages() if p.get_name() == "/Game/Masion/Mapa_B"]
    if mapa:
        w("salvo Mapa_B", U.save_packages(mapa, True))
    extra = [p for p in ale.sujos() if p != "/Game/Masion/Mapa_B"]
    if extra:
        w("aviso: pacotes ainda sujos:", extra)


def desfazer_l1():
    """Tira so o que e do Loop 1 do MAPA (figuras, de qualquer versao, e as luzes). Os assets NAO sao apagados: os 4 novos (PROPRIOS_L1) sao
    arquivos sem rastreio (apague-os no Content Browser ou do disco) e os do v3 (PROPRIOS_V3) nunca saem. Para voltar ao v3 inteiro:
    git checkout -- do Mapa_B."""
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    alvo = [c["label"] for c in FIGURAS_L1] + list(L1_LUZES)
    for a in [a for a in ale.atores() if a.get_actor_label() in alvo]:
        eas.destroy_actor(a)
    U = unreal.EditorLoadingAndSavingUtils
    U.save_packages([p for p in U.get_dirty_map_packages() if p.get_name() == "/Game/Masion/Mapa_B"], True)
    w("Loop 1 removido do mapa (%s); assets novos que ficam em %s: %s; os do v3 (%s) nao sao tocados" % (
        ", ".join(alvo), DIR, ", ".join(p.rsplit("/", 1)[-1] for p in PROPRIOS_L1), ", ".join(p.rsplit("/", 1)[-1] for p in PROPRIOS_V3)))


def main():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    open(LOG, "w", encoding="utf-8").close()
    modos = ("instalar", "verificar", "desfazer", "instalar_l1", "verificar_l1", "verificar_assets", "verificar_mapa", "desfazer_l1")
    modo = next((x for x in sys.argv[1:] if x in modos), "verificar")
    etapa = next((x for x in sys.argv[1:] if x in ("assets", "mapa")), None)
    w("modo:", modo, etapa or "")
    try:
        if modo == "instalar_l1":
            if etapa not in ("assets", "mapa"):
                raise Aborta("instalar_l1 pede a etapa: 'assets' (commandlet, lux_cmdlet_l1.py) ou 'mapa' (editor)")
            {"assets": instalar_l1_assets, "mapa": instalar_l1_mapa}[etapa]()
        else:
            {"instalar": instalar, "verificar": verificar, "desfazer": desfazer, "verificar_l1": verificar_l1,
             "verificar_assets": verificar_assets, "verificar_mapa": verificar_mapa, "desfazer_l1": desfazer_l1}[modo]()
    except Aborta as ex:
        w("ABORTADO:", ex, "| sujos:", ale.sujos())
    except Exception:
        w("ERRO " + traceback.format_exc(), "| sujos:", ale.sujos())


if __name__ == "__main__":
    main()
