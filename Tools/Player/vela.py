# LUX: vela na mao no lugar do lampiao (pedido do Gabriel, 27/09 21:49). O BP_Player (compartilhado) nao e editado.
# Como fica:
#  - Bracos em 1a pessoa (FirstPersonMesh = SKM_Metahuman_Arms, ABP_Arms_Cowboy): o AnimBP tem a maquina de estados da
#    lanterna (idle/andar/pulo segurando um objeto a frente), ligada pela variavel FlashlightOn? do jogador
#    (true = segurando a vela, false = guardada). Comeca segurando (FlashlightOn? = true nos Class Defaults).
#  - "Vela" (StaticMesh SM_Candles_NN_01c), sem colisao e sem sombra propria, presa no BeginPlay ao socket
#    hand_r_Vela (osso hand_r; 28/09, antes hand_r_Flashlight): acompanha a mao em idle, andar, pulo, puxar e guardar.
#  - 28/09 PEGA DE ESPADA (Tools/Player/vela_pega.py): o punho fecha na haste do castical em pe. Pose calculada dos
#    ossos (dedos fecham ate encostar na haste, punho gira para a haste ficar vertical, ombro/cotovelo por IK) e
#    aplicada como aditiva AS_LuxVela_Pega no ramo da lanterna do ABP_Arms_Cowboy (vale para todas as animacoes dele).
#  - "Lampiao" (PointLight) = luz da chama: filho da Vela, 5 cm acima do pavio, 2200 K, fraca, Light Function M_LuxVelaLuz.
#    "ChamaA"/"ChamaB": dois cartoes cruzados com M_LuxChama, filhos do "ChamaPivo" (no pavio, rotacao absoluta):
#    a chama fica em pe e no pavio com a vela inclinada (olhar para cima/baixo).
#  - 27/09 22h - GUARDAR/PUXAR (F): o F volta ao IA_Flashlight, entao roda o fluxo NATIVO do BP_Player (montagens
#    AS_Flashlight_Eqiup/Unequip, CanDoFlashlight, FlashlightOn?). A lanterna herdada fica oculta no jogo
#    (Hidden in Game) e o SM_Flashlight fica longe, para o clique dela nao tocar. A vela segue os notifies das montagens,
#    pelo NotifyGraph do ABP_Arms_Cowboy (Cast To BP_Player_Cowboy):
#      puxar : ShowFlashlight (inicio) -> Vela_Puxar: vela visivel e APAGADA; timer Vela_Acender = duracao da montagem
#              de equipar (0,8 s) + ESPERA_S (0,25 s; era 1,5 s) -> se ainda segura: chama acende -> luz acende
#      guardar: Flashlight_Off (inicio) -> Vela_Guardar: cancela o timer; chama apaga -> luz apaga
#               HideFlashlight (fim) -> Vela_Aplicar(false, false): a vela sai da mao
#    Chama e luz sao ligadas pelo mesmo booleano (Vela_Aplicar), nunca uma sem a outra. O BeginPlay sincroniza com
#    FlashlightOn?. O no IA_Lampiao -> ToggleVisibility (lampiao.py) sai do grafo.
#   py "<projeto>/Tools/Player/vela.py" sondar|instalar|verificar|desfazer|mundo
#   27/09 21h: vela menor (0.30), mao pega 3 cm acima da base, chama sempre em pe; "mundo" poe chama nas velas do mapa
import json, math, os, shutil, sys, traceback
import unreal

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "Loop"))
sys.path.insert(0, AQUI)
import importlib
import add_loop_events as ale
import lampiao as lp  # IMC_Default, IA_Flashlight, IA_Lampiao e os helpers de tecla
import vela_pega as vp  # 28/09: pega de espada (socket hand_r_Vela + aditiva AS_LuxVela_Pega no ABP)
importlib.reload(vp)

EAL, BEL, BGE, MEL = unreal.EditorAssetLibrary, unreal.BlueprintEditorLibrary, unreal.BlueprintGraphEditor, unreal.MaterialEditingLibrary
BP = "/Game/Characters/MixamoFP/Blueprints/BP_Player_Cowboy"
ME = BP + ".BP_Player_Cowboy_C"
DIR = "/Game/Masion/LUX/Player"
M_CHAMA = DIR + "/M_LuxChama"
M_LUZ = DIR + "/M_LuxVelaLuz"
SM_VELA = "/Game/OldWest/VOL6/Meshes/SM_Candles_NN_01c"
PLANO = "/Engine/BasicShapes/Plane"
# 28/09: a vela vai no socket hand_r_Vela (osso hand_r), criado pelo vela_pega.py no centro da haste dentro do punho,
# com Z = eixo da haste. A Vela so desce HASTE_MEIO ao longo desse eixo (o punho fecha no meio da haste).
# Antes: socket hand_r_Flashlight + pose manual (vela_pose.json, GRIP_CM), que deixava a vela 3,6-10,6 cm dos dedos.
SOCKET = vp.SOCKET
ESCALA_VELA = vp.ESCALA_VELA           # 42 cm -> 17,5 cm (28/09: 0.42, tamanho que cabe no punho; ver vela_pega.py)
TOPO = 41.7 * ESCALA_VELA              # topo da malha (pivo na base)
LUZ = {"cd": 0.5, "raio": 350.0, "temperatura": 2200.0, "fonte": 1.0}
CHAMA = {"largura": 1.8, "altura": 4.2}  # cm
# 27/09: luz 5 cm acima do pavio (antes 2,5) para nao estourar a cera e a mao
# 27/09 22h: a chama saiu da luz: base no pavio (ChamaPivo, rotacao absoluta), centro do cartao 2,5 cm acima dele.
# Presa a luz (5 cm ao longo do eixo da vela), a chama se soltava do pavio quando a vela inclinava (olhar p/ cima/baixo)
LUZ_ACIMA, CHAMA_ACIMA = 5.0, 2.5
LOG = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "LuxSnapshots", "vela_log.txt")
# guardar/puxar
ABP = "/Game/Characters/MixamoFP/Arms/ABP_Arms_Cowboy"
MONT_EQUIP = "/Game/FPMovement/Demo/Character/Animations/Flashlight/Montages/AS_Flashlight_Eqiup_Montage"
ESPERA_S = 0.25                        # vela na mao (fim da animacao de puxar) -> fogo + luz (28/09: era 1,5 s)
FUNCS = ("Vela_Aplicar", "Vela_Acender", "Vela_Puxar", "Vela_Guardar")
KSL, KML = "/Script/Engine.KismetSystemLibrary:", "/Script/Engine.KismetMathLibrary:"
SV = "/Script/Engine.SceneComponent:SetVisibility"
CAST = "Utilities|Casting|CastToBP_Player_Cowboy"
# ponytail: clique da lanterna silenciado estacionando o SM_Flashlight (oculto) a 1 km; o som dela e SpawnSoundAttached
# nele com atenuacao. Trocar por som proprio da vela exigiria editar o BP_Player (compartilhado).
LONGE = unreal.Vector(0.0, 0.0, -100000.0)
ATENUACAO = "/Game/FPMovement/Assets/Audio/Abilitys/Pickup/Effects/ItemAttenuation"
SNAP_LANT = os.path.join(AQUI, "vela_lanterna_original.json")
BACKUP = os.path.join(os.path.dirname(LOG), "backup_vela")
ARQS = ("Characters/MixamoFP/Blueprints/BP_Player_Cowboy.uasset", "Characters/MixamoFP/Arms/ABP_Arms_Cowboy.uasset",
        "FPMovement/Player/Input/IMC_Default.uasset")


def w(*a):
    line = " ".join(str(x) for x in a)
    unreal.log("[LUX vela] " + line)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
        fh.flush()


class Aborta(Exception):
    pass


# ------------------------------------------------------------------ materiais
def expr(m, cls, x, y, **props):
    e = MEL.create_material_expression(m, cls, x, y)
    for k, v in props.items():
        e.set_editor_property(k, v)
    return e


def lig(a, b, pino_b="", pino_a=""):
    if not MEL.connect_material_expressions(a, pino_a, b, pino_b):
        raise Aborta("ligacao de material falhou: %s -> %s.%s" % (a.get_name(), b.get_name(), pino_b))


def seno(m, t, freq, fase, amp, x, y):
    """amp * sin(t*freq + fase)"""
    mt = expr(m, unreal.MaterialExpressionMultiply, x, y, const_b=freq)
    lig(t, mt, "A")
    ad = expr(m, unreal.MaterialExpressionAdd, x + 150, y, const_b=fase)
    lig(mt, ad, "A")
    sn = expr(m, unreal.MaterialExpressionSine, x + 300, y, period=6.283185)
    lig(ad, sn)
    ma = expr(m, unreal.MaterialExpressionMultiply, x + 450, y, const_b=amp)
    lig(sn, ma, "A")
    return ma


def cria_m_chama():
    at = unreal.AssetToolsHelpers.get_asset_tools()
    m = at.create_asset("M_LuxChama", DIR, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_ADDITIVE)
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property("two_sided", True)
    uv = expr(m, unreal.MaterialExpressionTextureCoordinate, -1800, 0)
    t = expr(m, unreal.MaterialExpressionTime, -1800, 500)
    # forma de gota: centro (0.5, 0.65), mais estreita que alta
    c = expr(m, unreal.MaterialExpressionConstant2Vector, -1800, 150, r=0.5, g=0.65)
    d = expr(m, unreal.MaterialExpressionSubtract, -1600, 0)
    lig(uv, d, "A")
    lig(c, d, "B")
    esc = expr(m, unreal.MaterialExpressionConstant2Vector, -1600, 150, r=2.6, g=1.45)
    ds = expr(m, unreal.MaterialExpressionMultiply, -1450, 0)
    lig(d, ds, "A")
    lig(esc, ds, "B")
    dot = expr(m, unreal.MaterialExpressionDotProduct, -1300, 0)
    lig(ds, dot, "A")
    lig(ds, dot, "B")
    sq = expr(m, unreal.MaterialExpressionSquareRoot, -1150, 0)
    lig(dot, sq)
    om = expr(m, unreal.MaterialExpressionOneMinus, -1000, 0)
    lig(sq, om)
    sat = expr(m, unreal.MaterialExpressionSaturate, -850, 0)
    lig(om, sat)
    pw = expr(m, unreal.MaterialExpressionPower, -700, 0, const_exponent=2.0)
    lig(sat, pw, "Base")
    # ponta: some em cima (V pequeno)
    v = expr(m, unreal.MaterialExpressionComponentMask, -1600, 300, r=False, g=True, b=False, a=False)
    lig(uv, v)
    vv = expr(m, unreal.MaterialExpressionMultiply, -1450, 300, const_b=1.8)
    lig(v, vv, "A")
    vs = expr(m, unreal.MaterialExpressionSaturate, -1300, 300)
    lig(vv, vs)
    forma = expr(m, unreal.MaterialExpressionMultiply, -550, 100)
    lig(pw, forma, "A")
    lig(vs, forma, "B")
    # brilho que oscila devagar (0.85 +- 0.15), sem piscar
    s1 = seno(m, t, 11.0, 0.0, 0.08, -1600, 600)
    s2 = seno(m, t, 23.0, 1.3, 0.05, -1600, 750)
    s3 = seno(m, t, 5.3, 2.1, 0.04, -1600, 900)
    a1 = expr(m, unreal.MaterialExpressionAdd, -900, 650)
    lig(s1, a1, "A")
    lig(s2, a1, "B")
    a2 = expr(m, unreal.MaterialExpressionAdd, -750, 700)
    lig(a1, a2, "A")
    lig(s3, a2, "B")
    fl = expr(m, unreal.MaterialExpressionAdd, -600, 700, const_b=0.85)
    lig(a2, fl, "A")
    # cor: laranja nas bordas, amarelo claro no centro
    raiz = expr(m, unreal.MaterialExpressionSquareRoot, -550, -150)
    lig(forma, raiz)
    borda = expr(m, unreal.MaterialExpressionConstant3Vector, -550, -350, constant=unreal.LinearColor(1.0, 0.33, 0.06, 1))
    miolo = expr(m, unreal.MaterialExpressionConstant3Vector, -550, -250, constant=unreal.LinearColor(1.0, 0.85, 0.5, 1))
    cor = expr(m, unreal.MaterialExpressionLinearInterpolate, -350, -250)
    lig(borda, cor, "A")
    lig(miolo, cor, "B")
    lig(raiz, cor, "Alpha")
    k1 = expr(m, unreal.MaterialExpressionMultiply, -200, -100)
    lig(cor, k1, "A")
    lig(forma, k1, "B")
    k2 = expr(m, unreal.MaterialExpressionMultiply, -50, 0)
    lig(k1, k2, "A")
    lig(fl, k2, "B")
    k3 = expr(m, unreal.MaterialExpressionMultiply, 100, 0, const_b=7.0)
    lig(k2, k3, "A")
    MEL.connect_material_property(k3, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    # balanco: X += (sin(t*4.3)*0.25 + sin(t*7.9)*0.12) * (1 - V)  (so a ponta balanca)
    b1 = seno(m, t, 4.3, 0.0, 0.25, -1600, 1100)
    b2 = seno(m, t, 7.9, 0.7, 0.12, -1600, 1250)
    bs = expr(m, unreal.MaterialExpressionAdd, -900, 1150)
    lig(b1, bs, "A")
    lig(b2, bs, "B")
    iv = expr(m, unreal.MaterialExpressionOneMinus, -900, 1350)
    lig(v, iv)
    bm = expr(m, unreal.MaterialExpressionMultiply, -750, 1200)
    lig(bs, bm, "A")
    lig(iv, bm, "B")
    zero = expr(m, unreal.MaterialExpressionConstant, -750, 1400, r=0.0)
    wpo = expr(m, unreal.MaterialExpressionAppendVector, -550, 1250)
    lig(bm, wpo, "A")
    ap2 = expr(m, unreal.MaterialExpressionAppendVector, -400, 1300)
    lig(zero, ap2, "A")
    lig(zero, ap2, "B")
    wpo3 = expr(m, unreal.MaterialExpressionAppendVector, -250, 1250)
    lig(bm, wpo3, "A")
    lig(ap2, wpo3, "B")
    MEL.connect_material_property(wpo3, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    MEL.recompile_material(m)
    return m


def cria_m_luz():
    at = unreal.AssetToolsHelpers.get_asset_tools()
    m = at.create_asset("M_LuxVelaLuz", DIR, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("material_domain", unreal.MaterialDomain.MD_LIGHT_FUNCTION)
    t = expr(m, unreal.MaterialExpressionTime, -1200, 0)
    s1 = seno(m, t, 9.1, 0.0, 0.07, -1000, 0)
    s2 = seno(m, t, 14.3, 1.7, 0.04, -1000, 150)
    s3 = seno(m, t, 3.7, 0.4, 0.03, -1000, 300)
    a1 = expr(m, unreal.MaterialExpressionAdd, -300, 50)
    lig(s1, a1, "A")
    lig(s2, a1, "B")
    a2 = expr(m, unreal.MaterialExpressionAdd, -150, 100)
    lig(a1, a2, "A")
    lig(s3, a2, "B")
    base = expr(m, unreal.MaterialExpressionAdd, 0, 100, const_b=0.86)  # 0.86 +- 0.14 (~+-16% em volta de 0.86)
    lig(a2, base, "A")
    MEL.connect_material_property(base, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.recompile_material(m)
    return m


# ------------------------------------------------------------------ BP
def handles(bp):
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    out = {}
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        d = lib.get_data(h)
        o = lib.get_object_for_blueprint(d, bp)
        if o:
            out.setdefault(o.get_name().replace("_GEN_VARIABLE", ""), (h, o))
    return out


def add_comp(bp, cls, nome, pai_nome):
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    hs = handles(bp)
    ph = hs[pai_nome][0]
    h, _ = sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=ph, new_class=cls, blueprint_context=bp))
    sds.rename_subobject(h, unreal.Text(nome))
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    return h, lib.get_object_for_blueprint(lib.get_data(h), bp)


def reparent(bp, filho, pai):
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    hs = handles(bp)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    ph = lib.get_parent_handle(lib.get_data(hs[filho][0]))
    atual = lib.get_object_for_blueprint(lib.get_data(ph), bp)
    if atual and atual.get_name().replace("_GEN_VARIABLE", "") == pai:
        return False
    ok = sds.reparent_subobject(unreal.ReparentSubobjectParams(new_parent_handle=hs[pai][0], blueprint_context=bp), hs[filho][0])
    if not ok:
        raise Aborta("reparent %s -> %s falhou" % (filho, pai))
    return True


def props(o, pares):
    mud = False
    for k, v in pares:
        if o.get_editor_property(k) != v:
            o.set_editor_property(k, v)
            mud = True
    return mud


def instalar():
    if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():
        raise Aborta("feche o PIE")
    salvar = set()
    for p_, fn in ((M_CHAMA, cria_m_chama), (M_LUZ, cria_m_luz)):
        if not EAL.does_asset_exist(p_):
            w("criando", p_)
            fn()
            salvar.add(p_)
    # 0) pega: socket hand_r_Vela + aditiva da pose de espada no ABP (salva AS_LuxVela_Pega, SKM e ABP); log proprio
    try:
        vp.instalar()
    except vp.Aborta as ex:
        raise Aborta("pega: %s (ver vela_pega_log.txt)" % ex)
    w("pega instalada: socket %s, AS_LuxVela_Pega no ABP (detalhes em vela_pega_log.txt)" % SOCKET)
    bp = EAL.load_asset(BP)
    hs = handles(bp)
    if "Lampiao" not in hs:
        raise Aborta("sem o componente Lampiao (rode Tools/Player/lampiao.py instalar antes)")
    # 1) vela
    if "Vela" not in hs:
        w("adicionando Vela (filha do FirstPersonMesh; o socket e aplicado no BeginPlay)")
        add_comp(bp, unreal.StaticMeshComponent, "Vela", "FirstPersonMesh")
        salvar.add(BP)
        hs = handles(bp)
    vela = hs["Vela"][1]
    # no socket hand_r_Vela o Z ja e o eixo da haste: a vela so desce ate o punho ficar no meio da haste
    loc, rot = unreal.Vector(0.0, 0.0, -vp.HASTE_MEIO), unreal.Rotator(0.0, 0.0, 0.0)
    if props(vela,(("static_mesh", EAL.load_asset(SM_VELA)), ("relative_scale3d", unreal.Vector(ESCALA_VELA, ESCALA_VELA, ESCALA_VELA)),
                    ("relative_location", loc), ("relative_rotation", rot), ("cast_shadow", False), ("visible", True))):
        salvar.add(BP)
    if vela.get_collision_profile_name() != "NoCollision":
        vela.set_collision_profile_name("NoCollision")
        salvar.add(BP)
    # 2) luz da chama = Lampiao, filho da vela, no topo
    # o Lampiao continua filho do corpo no template (reparent para baixo de um componente herdado nao e aceito) e e
    # preso ao topo da Vela no BeginPlay (KeepRelative: a posicao abaixo e relativa a Vela)
    lamp = hs["Lampiao"][1]
    if props(lamp, (("relative_location", unreal.Vector(0, 0, (TOPO + LUZ_ACIMA) / ESCALA_VELA)), ("relative_scale3d", unreal.Vector(1, 1, 1)),
                    ("intensity_units", unreal.LightUnits.CANDELAS), ("intensity", LUZ["cd"]), ("attenuation_radius", LUZ["raio"]),
                    ("use_temperature", True), ("temperature", LUZ["temperatura"]), ("source_radius", LUZ["fonte"]), ("cast_shadows", True),
                    ("light_function_material", EAL.load_asset(M_LUZ)), ("visible", True),
                    # 27/09: rotacao absoluta -> a chama (filha da luz) fica sempre em pe, mesmo com a mao inclinada
                    ("absolute_rotation", True), ("relative_rotation", unreal.Rotator(0.0, 0.0, 0.0)))):
        salvar.add(BP)
    # 3) chama: ChamaPivo no pavio (filho da Vela, rotacao absoluta = sempre em pe) + dois cartoes cruzados, filhos dele
    if "ChamaPivo" not in hs:
        add_comp(bp, unreal.SceneComponent, "ChamaPivo", "Vela")
        salvar.add(BP)
        hs = handles(bp)
    if props(hs["ChamaPivo"][1], (("relative_location", unreal.Vector(0, 0, TOPO / ESCALA_VELA)), ("absolute_rotation", True),
                                  ("relative_rotation", unreal.Rotator(0.0, 0.0, 0.0)))):
        salvar.add(BP)
    # ChamaA/B ja existentes ficam no Lampiao no template (reparent de componente existente e recusado pelo editor, como no
    # Lampiao): o BeginPlay os prende ao ChamaPivo (KeepRelative), entao a posicao abaixo e relativa ao ChamaPivo
    for nome, yaw in (("ChamaA", 0.0), ("ChamaB", 90.0)):
        if nome not in hs:
            add_comp(bp, unreal.StaticMeshComponent, nome, "ChamaPivo")
            salvar.add(BP)
            hs = handles(bp)
        c = hs[nome][1]
        # Plane 100x100 no plano XY; roll 90 deixa em pe; escala em cm/100 (compensa a escala herdada da vela)
        k = 1.0 / ESCALA_VELA
        if props(c, (("static_mesh", EAL.load_asset(PLANO)), ("relative_location", unreal.Vector(0, 0, CHAMA_ACIMA / ESCALA_VELA)),
                     ("relative_rotation", unreal.Rotator(90.0, 0.0, yaw)),
                     ("relative_scale3d", unreal.Vector(CHAMA["largura"] / 100 * k, CHAMA["altura"] / 100 * k, 1.0)),
                     ("cast_shadow", False), ("visible", True))):
            salvar.add(BP)
        if c.get_material(0) != EAL.load_asset(M_CHAMA):
            c.set_material(0, EAL.load_asset(M_CHAMA))
            salvar.add(BP)
        if c.get_collision_profile_name() != "NoCollision":
            c.set_collision_profile_name("NoCollision")
            salvar.add(BP)
    # 4) pose dos bracos segurando a vela
    cdo = unreal.get_default_object(bp.generated_class())
    if not cdo.get_editor_property("FlashlightOn?"):
        cdo.set_editor_property("FlashlightOn?", True)
        salvar.add(BP)
    BEL.compile_blueprint(bp)
    # 5) grafo (so ADICIONA): BeginPlay -> prende a Vela no socket da mao e o Lampiao no topo da Vela
    ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
    g = ale.G(ge)
    nos = list(ge.list_all_nodes())
    if not marcador(bp):
        w("adicionando no de anexar a Vela no BeginPlay")
        pai = [n for n in nos if str(n.get_node_title()).startswith("Pai: BeginPlay") or str(n.get_node_title()).startswith("Parent: BeginPlay")][0]
        att = g.call("/Script/Engine.SceneComponent:K2_AttachToComponent", 600, 0, SocketName=SOCKET, LocationRule="KeepRelative",
                     RotationRule="KeepRelative", ScaleRule="KeepRelative", bWeldSimulatedBodies="false")
        g.link(g.get("Vela", 400, 120), "Vela", att, "self")
        g.link(g.get("FirstPersonMesh", 400, 200), "FirstPersonMesh", att, "Parent")
        g.link(pai, "then", att, g.exec_in(att))
        att2 = g.call("/Script/Engine.SceneComponent:K2_AttachToComponent", 900, 0, SocketName="None", LocationRule="KeepRelative",
                      RotationRule="KeepRelative", ScaleRule="KeepRelative", bWeldSimulatedBodies="false")
        g.link(g.get("Lampiao", 700, 120), "Lampiao", att2, "self")
        g.link(g.get("Vela", 700, 200), "Vela", att2, "Parent")
        g.link(att, "then", att2, g.exec_in(att2))
        g.note("LUX vela (Tools/Player/vela.py): prende a Vela no socket %s da mao direita" % SOCKET, 560, -80, 500, 80)
        salvar.add(BP)
    if socket_do_attach(bp, SOCKET):
        salvar.add(BP)
    # 6) guardar/puxar: F volta ao fluxo nativo da lanterna (ver cabecalho)
    backup()
    if entrada_f():
        salvar.add(lp.IMC)
    if lanterna_oculta(bp):
        salvar.add(BP)
    if tira_toggle(bp):
        salvar.add(BP)
    if funcoes(bp):
        salvar.add(BP)
    if espera(bp):
        salvar.add(BP)
    if sincroniza_beginplay(bp):
        salvar.add(BP)
    if prende_chama(bp):
        salvar.add(BP)
    BEL.compile_blueprint(bp)
    e = ale.erros_bp(bp)
    if e:
        raise Aborta("BP_Player_Cowboy com erros (nada salvo): %s" % e)
    if ganchos_abp():
        salvar.add(ABP)
    f = verificar()
    if f:
        raise Aborta("verificar FAIL (nada salvo): %s" % f)
    for p_ in sorted(salvar):
        w("salvo", p_, EAL.save_loaded_asset(EAL.load_asset(p_), False))
    w("PIE: F guarda (apaga fogo e luz, a vela sai da mao) / F puxa (vela apagada; %.2f s depois do fim da animacao acende)" % ESPERA_S)


def no_attach_vela(bp):
    """o Attach do BeginPlay que prende a Vela no FirstPersonMesh"""
    for n in BGE.get_graph_editor_by_name(bp, "EventGraph").list_all_nodes():
        if not tem(n.get_node_title(), "Attach Component To Component"):
            continue
        alvo = [str(q.get_pin_name()) for q in n.find_input_pin("self").list_connected_pins()]
        pai = [str(q.get_pin_name()) for q in n.find_input_pin("Parent").list_connected_pins()]
        if alvo == ["Vela"] and pai == ["FirstPersonMesh"]:
            return n
    return None


def socket_do_attach(bp, socket):
    """28/09: o Attach da Vela passa para o socket da pega (so troca o valor do pino SocketName)"""
    n = no_attach_vela(bp)
    if not n:
        raise Aborta("Attach da Vela no BeginPlay nao encontrado")
    if str(n.find_input_pin("SocketName").get_pin_value()) == socket:
        return False
    ale.G(BGE.get_graph_editor_by_name(bp, "EventGraph")).val(n, "SocketName", socket)
    w("Attach da Vela: socket -> %s" % socket)
    return True


# ------------------------------------------------------------------ guardar/puxar
def tem(titulo, nome):
    """titulo de no contem o nome (o editor mostra Vela_Aplicar como 'Vela Aplicar')"""
    return nome.replace("_", "").replace(" ", "").lower() in str(titulo).replace("_", "").replace(" ", "").lower()


def ligados(n, pino):
    p = n.find_output_pin(pino)
    return list(p.list_connected_pins()) if p and p.is_valid() else []


def backup():
    """copia os 3 .uasset que este passo altera (uma vez so) para Saved/LuxSnapshots/backup_vela"""
    if os.path.isdir(BACKUP):
        return
    cont = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()))
    for r in ARQS:
        dst = os.path.join(BACKUP, r.replace("/", "__"))
        os.makedirs(BACKUP, exist_ok=True)
        shutil.copy2(os.path.join(cont, r), dst)
    w("backup dos assets em", BACKUP)


def entrada_f():
    """IMC_Default: F sai do IA_Lampiao e volta ao IA_Flashlight (teclas originais em lampiao_original.json)"""
    imc, ia_f, ia_l = EAL.load_asset(lp.IMC), EAL.load_asset(lp.IA_FLASH), EAL.load_asset(lp.IA_LAMP)
    orig = json.load(open(lp.SNAP, encoding="utf-8"))["IA_Flashlight"] if os.path.exists(lp.SNAP) else ["F"]
    if (not ia_l or not lp.teclas(imc, ia_l)) and all(k in lp.teclas(imc, ia_f) for k in orig):
        return False
    with unreal.ScopedEditorTransaction("LUX vela: F -> IA_Flashlight"):
        imc.modify()
        if ia_l:
            imc.unmap_all_keys_from_action(ia_l)
        for k in orig:
            if k not in lp.teclas(imc, ia_f):
                imc.map_key(ia_f, lp.tecla(k))
    w("IMC_Default: %s -> IA_Flashlight (IA_Lampiao sem tecla)" % orig)
    return True


def lanterna_oculta(bp):
    """SM_Flashlight e Flashlight_Light (herdados) Hidden in Game: o SetVisibility do pai nao os mostra mais"""
    sm, luz = herdado(bp, "SM_Flashlight"), herdado(bp, "Flashlight_Light")
    if not os.path.exists(SNAP_LANT):
        json.dump({"SM_Flashlight": {"relative_location": [sm.get_editor_property("relative_location").x, sm.get_editor_property("relative_location").y,
                                                           sm.get_editor_property("relative_location").z],
                                     "hidden_in_game": sm.get_editor_property("hidden_in_game")},
                   "Flashlight_Light": {"hidden_in_game": luz.get_editor_property("hidden_in_game")}},
                  open(SNAP_LANT, "w", encoding="utf-8"), indent=1)
    mud = props(sm, (("hidden_in_game", True), ("relative_location", LONGE)))
    mud = props(luz, (("hidden_in_game", True),)) or mud
    try:
        st = EAL.load_asset(ATENUACAO).get_editor_property("attenuation")
        w("atenuacao do clique: atenua=%s raio=%s queda=%s (lanterna a %.0f m)" % (
            st.get_editor_property("attenuate"), st.get_editor_property("attenuation_shape_extents"),
            st.get_editor_property("falloff_distance"), -LONGE.z / 100))
    except Exception as ex:
        w("atenuacao do clique: nao lida (%s)" % ex)
    return mud


def herdado(bp, nome):
    """template do componente herdado DENTRO do BP_Player_Cowboy (nunca o do BP_Player, que e compartilhado)"""
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    achados = [lib.get_object_for_blueprint(lib.get_data(h), bp) for h in sds.k2_gather_subobject_data_for_blueprint(bp)]
    achados = [o for o in achados if o and o.get_name().replace("_GEN_VARIABLE", "") == nome]
    meus = [o for o in achados if o.get_path_name().startswith(BP + ".")]
    if not meus:
        raise Aborta("%s: sem template proprio no Cowboy (achados: %s)" % (nome, [o.get_path_name() for o in achados]))
    return meus[0]


def remover(ge, n):
    for fn in ("remove_node", "delete_node", "destroy_node"):
        if hasattr(ge, fn):
            getattr(ge, fn)(n)
            return "removido"
    for p in n.list_all_pins():
        p.break_pin_links()
    return "desligado"


def tira_toggle(bp):
    """o F antigo (IA_Lampiao -> ToggleVisibility do Lampiao) acendia a luz sem a chama: sai do grafo"""
    ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
    ev = [n for n in ge.list_all_nodes() if "IA_Lampiao" in str(n.get_node_title()) and ligados(n, "Started")]
    for n in ev:
        tg = [q.get_owning_node() for q in ligados(n, "Started")]
        gets = [q.get_owning_node() for t in tg for p in t.list_input_pins() for q in p.list_connected_pins()]
        for x in tg + gets + [n]:
            w("  no antigo %s: %s" % (str(x.get_node_title()).replace("\n", " "), remover(ge, x)))
    return bool(ev)


def get_var(g, nome, x, y):
    try:
        n = g.ge.add_get_member_variable_node(nome, "")
        if n:
            return g.pos(n, x, y)
    except Exception:
        pass
    return g.get(nome, x, y, "/Game/FPMovement/Player/Blueprints/BP_Player.BP_Player_C")


def funcoes(bp):
    """Vela_Aplicar(Visivel, Acesa) e as 3 chamadas pelo AnimBP. Sem no latente (timer por nome)."""
    graficos = [str(x) for x in BEL.list_graph_names(bp)]
    faltam = [f for f in FUNCS if f not in graficos]
    if not faltam:
        return False
    if len(faltam) != len(FUNCS):
        raise Aborta("BP_Player_Cowboy tem so parte das funcoes da vela (%s): feche o editor sem salvar" % faltam)
    tb = BEL.get_basic_type_by_name("bool")
    fe = BGE.create_and_edit_function_graph(bp, "Vela_Aplicar")
    fe.add_graph_input_parameter("Visivel", tb)
    fe.add_graph_input_parameter("Acesa", tb)
    g = ale.G(fe)
    e = g.pos(fe.find_graph_entry_pin().get_owning_node(), 0, 0)
    e_ = g.call(KML + "BooleanAND", 380, 260)
    g.link(e, "Visivel", e_, "A")
    g.link(e, "Acesa", e_, "B")
    passos = [e]
    for i, comp in enumerate(("Vela", "ChamaA", "ChamaB", "Lampiao")):
        n = g.call(SV, 300 + 300 * i, 0, bPropagateToChildren="false")
        g.link(g.get(comp, 160 + 300 * i, 160), comp, n, "self")
        g.link(e if comp == "Vela" else e_, "Visivel" if comp == "Vela" else "ReturnValue", n, "bNewVisibility")
        passos.append(n)
    g.chain(*passos)
    g.note("LUX vela: a Vela segue Visivel; chama (ChamaA/B) e luz (Lampiao) seguem Visivel E Acesa, nesta ordem: "
           "fogo e luz nunca ficam um sem o outro", -40, -120, 1500, 460)
    BEL.compile_blueprint(bp)
    ap = lambda gg, x, vis, ac: gg.call(ME + ":Vela_Aplicar", x, 0, Visivel=vis, Acesa=ac)
    # Vela_Acender (alvo do timer): so acende se ainda estiver segurando
    fe = BGE.create_and_edit_function_graph(bp, "Vela_Acender")
    g = ale.G(fe)
    e = g.pos(fe.find_graph_entry_pin().get_owning_node(), 0, 0)
    br = g.branch(260, 0)
    g.link(get_var(g, "FlashlightOn?", 80, 160), "FlashlightOn?", br, "Condition")
    g.chain(e, br)
    g.chain((br, "then"), ap(g, 520, "true", "true"))
    # Vela_Puxar (notify ShowFlashlight): vela na mao, apagada; acende depois da animacao + ESPERA_S
    t = tempo_acender()
    fe = BGE.create_and_edit_function_graph(bp, "Vela_Puxar")
    g = ale.G(fe)
    e = g.pos(fe.find_graph_entry_pin().get_owning_node(), 0, 0)
    tm = g.call(KSL + "K2_SetTimer", 560, 0, FunctionName="Vela_Acender", Time=t, bLooping="false")
    g.chain(e, ap(g, 260, "true", "false"), tm)
    g.note("LUX vela: ShowFlashlight -> vela apagada na mao; Vela_Acender em %.2f s = montagem de equipar (%.2f s) + %.1f s "
           "com a vela na mao" % (t, t - ESPERA_S, ESPERA_S), -40, -120, 900, 300)
    # Vela_Guardar (notify Flashlight_Off): cancela o acender pendente; fogo e luz apagam, a vela segue na mao ate o fim
    fe = BGE.create_and_edit_function_graph(bp, "Vela_Guardar")
    g = ale.G(fe)
    e = g.pos(fe.find_graph_entry_pin().get_owning_node(), 0, 0)
    g.chain(e, g.call(KSL + "K2_ClearTimer", 260, 0, FunctionName="Vela_Acender"), ap(g, 560, "true", "false"))
    w("funcoes criadas: %s (acende %.2f s apos o inicio de puxar)" % (", ".join(FUNCS), t))
    return True


def tempo_acender():
    """duracao da montagem de puxar + ESPERA_S (o timer parte do ShowFlashlight, no inicio da montagem)"""
    return round(unreal.AnimationLibrary.get_sequence_length(EAL.load_asset(MONT_EQUIP)) + ESPERA_S, 3)


def no_timer(bp):
    ge = BGE.get_graph_editor_by_name(bp, "Vela_Puxar")
    tms = [n for n in ge.list_all_nodes() if ale.ok_pin(n.find_input_pin("FunctionName")) and ale.ok_pin(n.find_input_pin("Time"))]
    if len(tms) != 1:
        raise Aborta("Vela_Puxar deveria ter 1 timer (achou %d)" % len(tms))
    return ge, tms[0]


def espera(bp):
    """28/09: ESPERA_S mudou (1,5 -> 0,25 s): ajusta o UNICO timer da vela (Vela_Puxar) em vez de criar outro"""
    ge, tm = no_timer(bp)
    alvo = tempo_acender()
    atual = float(tm.find_input_pin("Time").get_pin_value() or 0)
    if abs(atual - alvo) < 1e-3:
        return False
    ale.G(ge).val(tm, "Time", alvo)
    for n in ge.list_all_nodes():
        if "LUX vela: ShowFlashlight" in str(n.get_node_title()):
            try:
                n.set_editor_property("node_comment", "LUX vela: ShowFlashlight -> vela apagada na mao; Vela_Acender em %.2f s = montagem "
                                      "de puxar (%.2f s) + %.2f s com a vela na mao" % (alvo, alvo - ESPERA_S, ESPERA_S))
            except Exception as ex:
                w("  comentario do Vela_Puxar nao atualizado (%s)" % ex)
    w("timer do Vela_Puxar: %.3f s -> %.3f s (ESPERA_S %.2f s)" % (atual, alvo, ESPERA_S))
    return True


def sincroniza_beginplay(bp):
    """depois dos 2 Attach do BeginPlay: Vela_Aplicar(FlashlightOn?, FlashlightOn?)"""
    ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
    nos = list(ge.list_all_nodes())
    if [n for n in nos if tem(n.get_node_title(), "Vela_Aplicar")]:
        return False
    fim = [n for n in nos if tem(n.get_node_title(), "Attach Component To Component") and not ligados(n, "then")]
    if len(fim) != 1:
        raise Aborta("fim da cadeia de Attach do BeginPlay nao encontrado (%d)" % len(fim))
    g = ale.G(ge)
    ap = g.call(ME + ":Vela_Aplicar", 1200, 0)
    on = get_var(g, "FlashlightOn?", 1000, 160)
    g.link(on, "FlashlightOn?", ap, "Visivel")
    g.link(on, "FlashlightOn?", ap, "Acesa")
    g.chain(fim[0], ap)
    w("BeginPlay: vela sincronizada com FlashlightOn?")
    return True


def chamas_presas(bp):
    """componentes que o BeginPlay prende ao ChamaPivo (Attach com self = Get ChamaA/B e Parent = Get ChamaPivo)"""
    out = set()
    for n in BGE.get_graph_editor_by_name(bp, "EventGraph").list_all_nodes():
        if not tem(n.get_node_title(), "Attach Component To Component"):
            continue
        pai = [str(q.get_pin_name()) for q in n.find_input_pin("Parent").list_connected_pins()]
        if pai == ["ChamaPivo"]:
            out.update(str(q.get_pin_name()) for q in n.find_input_pin("self").list_connected_pins())
    return out


def prende_chama(bp):
    """fim do BeginPlay: ChamaA/B -> ChamaPivo (KeepRelative)"""
    faltam = [c for c in ("ChamaA", "ChamaB") if c not in chamas_presas(bp)]
    if not faltam:
        return False
    ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
    fim = [n for n in ge.list_all_nodes() if (tem(n.get_node_title(), "Attach Component To Component") or tem(n.get_node_title(), "Vela_Aplicar"))
           and not ligados(n, "then")]
    if len(fim) != 1:
        raise Aborta("fim da cadeia do BeginPlay nao encontrado (%d)" % len(fim))
    g = ale.G(ge)
    ant, x = fim[0], 1500
    for c in faltam:
        att = g.call("/Script/Engine.SceneComponent:K2_AttachToComponent", x, 0, SocketName="None", LocationRule="KeepRelative",
                     RotationRule="KeepRelative", ScaleRule="KeepRelative", bWeldSimulatedBodies="false")
        g.link(g.get(c, x - 200, 120), c, att, "self")
        g.link(g.get("ChamaPivo", x - 200, 200), "ChamaPivo", att, "Parent")
        g.chain(ant, att)
        ant, x = att, x + 300
    w("BeginPlay: %s presos ao ChamaPivo (chama no pavio)" % faltam)
    return True


def ganchos_abp():
    """NotifyGraph do ABP_Arms_Cowboy: ShowFlashlight -> Vela_Puxar, Flashlight_Off -> Vela_Guardar (depois do
    SetVisibility que ja existe), HideFlashlight -> Vela_Aplicar(false, false). So adiciona."""
    abp = EAL.load_asset(ABP)
    ge = BGE.get_graph_editor_by_name(abp, "NotifyGraph")
    g = ale.G(ge)
    nos = list(ge.list_all_nodes())
    mud = False

    def gancho(no, pino, fn, x, y, **vals):
        c = ge.create_node_from_name(CAST, unreal.Vector2D(x, y), [])
        if not c:
            raise Aborta("no %s nao criado" % CAST)
        g.pos(c, x, y)
        g.link(g.get("Player", x - 220, y + 140), "Player", c, "Object")
        k = g.call(ME + ":" + fn, x + 320, y, **vals)
        g.link(c, next(str(p.get_pin_name()) for p in c.list_output_pins() if str(p.get_pin_name()).startswith("As")), k, "self")
        g.link(no, pino, c, g.exec_in(c))
        g.chain(c, k)

    for notify, fn, y, vals in (("ShowFlashlight", "Vela_Puxar", 900, {}), ("HideFlashlight", "Vela_Aplicar", 1200, {"Visivel": "false", "Acesa": "false"})):
        if [n for n in nos if tem(n.get_node_title(), notify)]:
            continue
        ev = ge.create_node_from_name("AddAnimNotifyEvent|EventAnimNotify_" + notify, unreal.Vector2D(0, y), [])
        if not ev:
            raise Aborta("evento AnimNotify_%s nao criado" % notify)
        g.pos(ev, 0, y)
        gancho(ev, "then", fn, 400, y, **vals)
        w("ABP: AnimNotify_%s -> %s" % (notify, fn))
        mud = True
    off = [n for n in nos if tem(n.get_node_title(), "AnimNotify_Flashlight_Off")]
    if len(off) != 1:
        raise Aborta("AnimNotify_Flashlight_Off do ABP nao encontrado")
    sv = [q.get_owning_node() for q in ligados(off[0], "then")]
    if len(sv) != 1:
        raise Aborta("AnimNotify_Flashlight_Off do ABP sem o SetVisibility esperado")
    if not ligados(sv[0], "then"):
        pos = sv[0].get_node_pos()
        gancho(sv[0], "then", "Vela_Guardar", pos.x + 360, pos.y)
        w("ABP: AnimNotify_Flashlight_Off -> (SetVisibility da lanterna) -> Vela_Guardar")
        mud = True
    if mud:
        g.note("LUX vela (Tools/Player/vela.py): notifies das montagens da lanterna -> vela do BP_Player_Cowboy "
               "(puxar: ShowFlashlight; guardar: Flashlight_Off apaga, HideFlashlight tira da mao)", -40, 800, 1300, 80)
    BEL.compile_blueprint(abp)
    e = ale.erros_bp(abp)
    if e:
        raise Aborta("ABP_Arms_Cowboy com erros (nada salvo): %s" % e)
    return mud


def marcador(bp):
    ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
    for n in ge.list_all_nodes():
        t = str(n.get_node_title())
        if "LUX vela" in t or "Attach Component To Component" in t or "Anexar" in t:
            return n
    return None


def verificar():
    falhas = []
    bp = EAL.load_asset(BP)
    hs = handles(bp)
    for nome in ("Vela", "Lampiao", "ChamaA", "ChamaB"):
        if nome not in hs:
            falhas.append("sem componente %s" % nome)
    if not falhas:
        v = hs["Vela"][1]
        if v.get_editor_property("static_mesh") != EAL.load_asset(SM_VELA):
            falhas.append("Vela sem o mesh SM_Candles_NN_01c")
        for nome in ("Vela", "ChamaA", "ChamaB"):
            if hs[nome][1].get_collision_profile_name() != "NoCollision":
                falhas.append("%s com colisao" % nome)
        if not hs["Lampiao"][1].get_editor_property("light_function_material"):
            falhas.append("luz da vela sem variacao (light function)")
        if "ChamaPivo" not in hs or not hs["ChamaPivo"][1].get_editor_property("absolute_rotation"):
            falhas.append("chama nao fica em pe no pavio (sem ChamaPivo com rotacao absoluta)")
        else:
            presos = chamas_presas(bp)
            falhas += ["%s nao e preso ao ChamaPivo no BeginPlay (a chama se solta do pavio ao inclinar)" % n
                       for n in ("ChamaA", "ChamaB") if n not in presos]
    if not marcador(bp):
        falhas.append("sem o no que prende a Vela no socket da mao")
    else:
        n = no_attach_vela(bp)
        if not n or str(n.find_input_pin("SocketName").get_pin_value()) != SOCKET:
            falhas.append("a Vela nao e presa no socket %s (pega de espada)" % SOCKET)
    falhas += vp.verificar()
    cdo = unreal.get_default_object(bp.generated_class())
    for k in ("FlashlightOn?", "HasFlashlight?", "CanDoFlashlight"):
        if not cdo.get_editor_property(k):
            falhas.append("%s falso nos Class Defaults (comeca segurando a vela; F depende dele)" % k)
    # guardar/puxar
    imc = EAL.load_asset(lp.IMC)
    if "F" not in lp.teclas(imc, EAL.load_asset(lp.IA_FLASH)):
        falhas.append("F nao esta no IA_Flashlight (sem guardar/puxar)")
    if EAL.does_asset_exist(lp.IA_LAMP) and lp.teclas(imc, EAL.load_asset(lp.IA_LAMP)):
        falhas.append("IA_Lampiao ainda tem tecla")
    try:
        for nome in ("SM_Flashlight", "Flashlight_Light"):
            if not herdado(bp, nome).get_editor_property("hidden_in_game"):
                falhas.append("%s aparece no jogo (a lanterna surgiria junto com a vela)" % nome)
    except Aborta as ex:
        falhas.append(str(ex))
    graficos = [str(x) for x in BEL.list_graph_names(bp)]
    falhas += ["sem a funcao %s" % f for f in FUNCS if f not in graficos]
    if "Vela_Puxar" in graficos:
        try:
            _, tm = no_timer(bp)
            t = float(tm.find_input_pin("Time").get_pin_value() or 0)
            if abs(t - tempo_acender()) > 1e-3:
                falhas.append("timer do Vela_Puxar em %.3f s (esperado %.3f = puxar + ESPERA_S)" % (t, tempo_acender()))
        except Aborta as ex:
            falhas.append(str(ex))
    ev = BGE.get_graph_editor_by_name(bp, "EventGraph").list_all_nodes()
    if [n for n in ev if "IA_Lampiao" in str(n.get_node_title()) and ligados(n, "Started")]:
        falhas.append("o F antigo (IA_Lampiao -> ToggleVisibility) ainda esta ligado")
    if not [n for n in ev if tem(n.get_node_title(), "Vela_Aplicar")]:
        falhas.append("BeginPlay nao sincroniza a vela com FlashlightOn?")
    abp = EAL.load_asset(ABP)
    ng = list(BGE.get_graph_editor_by_name(abp, "NotifyGraph").list_all_nodes())
    for notify in ("ShowFlashlight", "HideFlashlight"):
        if not [n for n in ng if tem(n.get_node_title(), notify) and ligados(n, "then")]:
            falhas.append("ABP sem o gancho AnimNotify_%s" % notify)
    off = [n for n in ng if tem(n.get_node_title(), "AnimNotify_Flashlight_Off")]
    sv = [q.get_owning_node() for n in off for q in ligados(n, "then")]
    if not (sv and ligados(sv[0], "then")):
        falhas.append("ABP: Flashlight_Off nao chama Vela_Guardar")
    falhas += ale.erros_bp(bp) + ale.erros_bp(abp)
    w("verificar:", ("FAIL %s" % falhas) if falhas else "PASS")
    return falhas


def sondar():
    bp = EAL.load_asset(BP)
    w("componentes:", sorted(handles(bp)))
    try:
        vp.relatorio(*vp.calcula()[:8])
    except vp.Aborta as ex:
        w("pega: %s" % ex)


def desfazer():
    """O guardar/puxar mexe em grafos (BP_Player_Cowboy, ABP_Arms_Cowboy) e no IMC_Default; grafo nao se desfaz por
    script aqui (regra: nao apagar funcoes). Desfazer = restaurar os 3 .uasset com o editor FECHADO."""
    w("desfazer: feche o editor e copie de volta os arquivos de %s para Content/ (o nome usa __ no lugar de /)," % BACKUP)
    w("          ou 'git checkout' em: %s" % ", ".join("Content/" + r for r in ARQS))
    w("          e apague Tools/Player/vela_lanterna_original.json")


# ------------------------------------------------------------------ velas do mapa
def mundo():
    """Chama (2 cartoes M_LuxChama) + oscilacao (M_LuxVelaLuz) em cada luz de vela/candelabro acesa do mapa aberto.
    As chamas sao StaticMeshActors presos a luz, com as tags LOOPn_ON/OFF dela (somem junto) + LUX_CHAMA.
    Rodar de novo depois de furnish.py ou apply_loop_tags.py (eles recriam as luzes).
    Idempotente (apaga as LUX_CHAMA antigas). Nao salva o mapa: Ctrl+S. Desfazer: Ctrl+Z ("LUX: chamas das velas")."""
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    plano, mat, lf = EAL.load_asset(PLANO), EAL.load_asset(M_CHAMA), EAL.load_asset(M_LUZ)
    velas = [c for a in eas.get_all_level_actors() for c in a.get_components_by_class(unreal.StaticMeshComponent)
             if c.get_editor_property("static_mesh") and "SM_Candles" in c.get_editor_property("static_mesh").get_name()]
    n = 0
    with unreal.ScopedEditorTransaction("LUX: chamas das velas"):
        for a in eas.get_all_level_actors():
            if "LUX_CHAMA" in [str(t) for t in a.tags]:
                eas.destroy_actor(a)
        for luz in eas.get_all_level_actors():
            lab = luz.get_actor_label()
            if not isinstance(luz, unreal.PointLight) or not any(k in lab for k in ("Vela", "Candelabro")):
                continue
            lc = luz.get_editor_property("point_light_component")
            if lc.get_editor_property("intensity") <= 0:
                w("  sem chama (luz apagada):", lab)
                continue
            lc.modify()
            if not lc.get_editor_property("light_function_material"):
                lc.set_editor_property("light_function_material", lf)
            # base da chama no topo da vela (bounds da malha SM_Candles mais proxima); sem vela perto, 2 cm abaixo da luz
            lz = luz.get_actor_location()
            pos = lz - unreal.Vector(0, 0, 2.0)
            perto = [(math.hypot(c.get_world_location().x - lz.x, c.get_world_location().y - lz.y), c) for c in velas]
            perto = [x for x in perto if x[0] < 45.0]
            if perto:
                dist, c = min(perto, key=lambda x: x[0])
                o, e, _ = unreal.SystemLibrary.get_component_bounds(c)
                topo = o.z + e.z
                x, y = lz.x, lz.y
                if "01a" in c.get_editor_property("static_mesh").get_name():
                    # candelabro: 3 velas no eixo X da malha, a 0 e +-25 cm (medido no viewport); a chama vai para a
                    # vela mais proxima da luz. ponytail: offsets fixos do SM_Candles_NN_01a; outro candelabro pede medir
                    cl, fx = c.get_world_location(), c.get_forward_vector()
                    d = (lz.x - cl.x) * fx.x + (lz.y - cl.y) * fx.y
                    k = min((-25.0, 0.0, 25.0), key=lambda v: abs(d - v))
                    x, y = cl.x + fx.x * k, cl.y + fx.y * k
                    if k:
                        topo -= 3.0   # velas laterais ~3 cm abaixo da central
                pos = unreal.Vector(x, y, topo + CHAMA["altura"] / 2 + 0.2)
                w("  %s: topo da vela %.1f cm abaixo da luz" % (lab, lz.z - topo))
            tags = [t for t in luz.tags if str(t).startswith("LOOP") and str(t).endswith(("_ON", "_OFF"))] + [unreal.Name("LUX_CHAMA")]
            for suf, yaw in (("A", 0.0), ("B", 90.0)):
                c = eas.spawn_actor_from_object(plano, pos, unreal.Rotator(90.0, 0.0, yaw))
                c.set_actor_scale3d(unreal.Vector(CHAMA["largura"] / 100, CHAMA["altura"] / 100, 1.0))
                smc = c.get_editor_property("static_mesh_component")
                smc.set_mobility(unreal.ComponentMobility.MOVABLE)
                smc.set_material(0, mat)
                smc.set_collision_profile_name("NoCollision")
                smc.set_editor_property("cast_shadow", False)
                c.set_actor_label("CHAMA_%s_%s" % (lab, suf))
                c.set_folder_path("LUX/Chamas")
                c.set_editor_property("tags", tags)
                c.attach_to_actor(luz, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD,
                                  unreal.AttachmentRule.KEEP_WORLD, False)
            n += 1
            w("  chama em", lab, "tags", [str(t) for t in tags])
    w("velas com chama:", n, "| salve o mapa com Ctrl+S")


def main():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    open(LOG, "w", encoding="utf-8").close()
    modo = next((a for a in sys.argv[1:] if a in ("sondar", "instalar", "verificar", "desfazer", "mundo")), "sondar")
    w("modo:", modo)
    try:
        {"sondar": sondar, "instalar": instalar, "verificar": verificar, "desfazer": desfazer, "mundo": mundo}[modo]()
    except Aborta as ex:
        w("ABORTADO:", ex, "| sujos:", ale.sujos())
    except Exception:
        w("ERRO " + traceback.format_exc(), "| sujos:", ale.sujos())


if __name__ == "__main__":
    main()
