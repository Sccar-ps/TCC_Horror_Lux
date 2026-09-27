# LUX: vela na mao no lugar do lampiao (pedido do Gabriel, 27/09 21:49). O BP_Player (compartilhado) nao e editado.
# Como fica:
#  - Bracos em 1a pessoa (FirstPersonMesh = SKM_Metahuman_Arms, ABP_Arms_Cowboy): o AnimBP tem a maquina de estados da
#    lanterna (idle/andar/pulo segurando um objeto a frente), ligada pela variavel FlashlightOn? do jogador. Com o F da
#    lanterna desligado (IA_Lampiao), FlashlightOn? = true por padrao so muda a POSE dos bracos: a mao direita segura
#    a vela a frente. A SpotLight e o mesh da lanterna continuam ocultos (a logica deles so roda pelo F antigo).
#    A tecla I (inspecionar) passa a tocar a animacao de inspecionar o objeto na mao (a vela).
#  - "Vela" (StaticMesh SM_Candles_NN_01c, o asset pedido; no projeto ele se chama assim), sem colisao e sem sombra
#    propria, presa no BeginPlay ao socket hand_r_Flashlight da mao direita (no ADICIONADO depois do "Pai: BeginPlay"),
#    acompanhando a mao em todas as animacoes.
#  - "Lampiao" (PointLight que ja existia, o F ja o liga/desliga) vira a luz da chama: filho da Vela, no topo do pavio,
#    2200 K, fraca, com Light Function M_LuxVelaLuz (variacao suave continua de ~+-12%, sem piscar).
#  - "ChamaA"/"ChamaB": dois cartoes cruzados, filhos do Lampiao, com M_LuxChama (aditivo, unlit, forma de gota, cor de
#    chama, oscilacao de brilho e balanco por WPO). O toggle do F passa a propagar para os filhos: F apaga/acende chama+luz.
#   py "<projeto>/Tools/Player/vela.py" sondar|instalar|verificar|desfazer
import json, math, os, sys, traceback
import unreal

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "Loop"))
import add_loop_events as ale

EAL, BEL, BGE, MEL = unreal.EditorAssetLibrary, unreal.BlueprintEditorLibrary, unreal.BlueprintGraphEditor, unreal.MaterialEditingLibrary
BP = "/Game/Characters/MixamoFP/Blueprints/BP_Player_Cowboy"
ME = BP + ".BP_Player_Cowboy_C"
DIR = "/Game/Masion/LUX/Player"
M_CHAMA = DIR + "/M_LuxChama"
M_LUZ = DIR + "/M_LuxVelaLuz"
SM_VELA = "/Game/OldWest/VOL6/Meshes/SM_Candles_NN_01c"
PLANO = "/Engine/BasicShapes/Plane"
SOCKET = "hand_r_Flashlight"
ESCALA_VELA = 0.45                     # 42 cm -> ~19 cm (vela com pratinho, de mao)
TOPO = 41.7 * ESCALA_VELA              # topo da malha (pivo na base)
# transformacao da vela em relacao ao socket da mao (medida no PIE: ver POSE_JSON)
POSE_JSON = os.path.join(AQUI, "vela_pose.json")
LUZ = {"cd": 0.6, "raio": 350.0, "temperatura": 2200.0, "fonte": 1.0}
CHAMA = {"largura": 1.8, "altura": 4.2}  # cm
LOG = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "LuxSnapshots", "vela_log.txt")


def w(*a):
    line = " ".join(str(x) for x in a)
    unreal.log("[LUX vela] " + line)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
        fh.flush()


class Aborta(Exception):
    pass


def pose():
    if os.path.exists(POSE_JSON):
        d = json.load(open(POSE_JSON, encoding="utf-8"))
        return unreal.Vector(*d["loc"]), unreal.Rotator(*d["rot"])
    return unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0)


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


def no_attach(bp):
    ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
    for n in ge.list_all_nodes():
        t = str(n.get_node_title())
        if "AttachComponentToComponent" in t.replace(" ", "") or "Anexar componente" in t or "Attach" in t and "Vela" in str([str(p.get_default_value()) for p in n.list_all_pins()]):
            return n
    return None


def instalar():
    if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():
        raise Aborta("feche o PIE")
    salvar = set()
    for p_, fn in ((M_CHAMA, cria_m_chama), (M_LUZ, cria_m_luz)):
        if not EAL.does_asset_exist(p_):
            w("criando", p_)
            fn()
            salvar.add(p_)
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
    loc, rot = pose()
    if props(vela, (("static_mesh", EAL.load_asset(SM_VELA)), ("relative_scale3d", unreal.Vector(ESCALA_VELA, ESCALA_VELA, ESCALA_VELA)),
                    ("relative_location", loc), ("relative_rotation", rot), ("cast_shadow", False), ("visible", True))):
        salvar.add(BP)
    if vela.get_collision_profile_name() != "NoCollision":
        vela.set_collision_profile_name("NoCollision")
        salvar.add(BP)
    # 2) luz da chama = Lampiao, filho da vela, no topo
    # o Lampiao continua filho do corpo no template (reparent para baixo de um componente herdado nao e aceito) e e
    # preso ao topo da Vela no BeginPlay (KeepRelative: a posicao abaixo e relativa a Vela)
    lamp = hs["Lampiao"][1]
    if props(lamp, (("relative_location", unreal.Vector(0, 0, (TOPO + 2.5) / ESCALA_VELA)), ("relative_scale3d", unreal.Vector(1, 1, 1)),
                    ("intensity_units", unreal.LightUnits.CANDELAS), ("intensity", LUZ["cd"]), ("attenuation_radius", LUZ["raio"]),
                    ("use_temperature", True), ("temperature", LUZ["temperatura"]), ("source_radius", LUZ["fonte"]), ("cast_shadows", True),
                    ("light_function_material", EAL.load_asset(M_LUZ)), ("visible", True))):
        salvar.add(BP)
    # 3) chama: dois cartoes cruzados, filhos da luz
    for nome, yaw in (("ChamaA", 0.0), ("ChamaB", 90.0)):
        if nome not in hs:
            add_comp(bp, unreal.StaticMeshComponent, nome, "Lampiao")
            salvar.add(BP)
            hs = handles(bp)
        c = hs[nome][1]
        # Plane 100x100 no plano XY; roll 90 deixa em pe; escala em cm/100 (compensa a escala 0.45 herdada da vela)
        k = 1.0 / ESCALA_VELA
        if props(c, (("static_mesh", EAL.load_asset(PLANO)), ("relative_location", unreal.Vector(0, 0, 0)),
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
    # 5) grafo (so ADICIONA): BeginPlay -> prende a Vela no socket da mao; toggle do F propaga para chama
    ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
    g = ale.G(ge)
    nos = list(ge.list_all_nodes())
    tg = [n for n in nos if "ToggleVisibility" in str(n.get_node_title()).replace(" ", "") or "Alternar" in str(n.get_node_title())]
    if not tg:
        raise Aborta("no ToggleVisibility do IA_Lampiao nao encontrado")
    if not marcador(bp):
        g.val(tg[0], "bPropagateToChildren", "true")
        w("toggle do F agora propaga para a chama")
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
    BEL.compile_blueprint(bp)
    e = ale.erros_bp(bp)
    if e:
        raise Aborta("BP_Player_Cowboy com erros (nada salvo): %s" % e)
    f = verificar()
    if f:
        raise Aborta("verificar FAIL (nada salvo): %s" % f)
    for p_ in sorted(salvar):
        w("salvo", p_, EAL.save_loaded_asset(EAL.load_asset(p_), False))


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
    if not marcador(bp):
        falhas.append("sem o no que prende a Vela no socket da mao")
    if not unreal.get_default_object(bp.generated_class()).get_editor_property("FlashlightOn?"):
        falhas.append("FlashlightOn? falso: os bracos nao seguram a vela")
    falhas += ale.erros_bp(bp)
    w("verificar:", ("FAIL %s" % falhas) if falhas else "PASS")
    return falhas


def sondar():
    bp = EAL.load_asset(BP)
    w("componentes:", sorted(handles(bp)))
    w("pose da vela:", pose())


def desfazer():
    """Volta ao lampiao: vela e chama ocultas, Lampiao volta ao corpo com os valores do lampiao, bracos sem a pose."""
    bp = EAL.load_asset(BP)
    hs = handles(bp)
    for nome in ("Vela", "ChamaA", "ChamaB"):
        if nome in hs:
            hs[nome][1].set_editor_property("visible", False)
    if "Lampiao" in hs:
        props(hs["Lampiao"][1], (("relative_location", unreal.Vector(30, 25, 30)), ("intensity", 0.8), ("attenuation_radius", 500.0),
                                 ("temperature", 2800.0), ("light_function_material", None)))
    unreal.get_default_object(bp.generated_class()).set_editor_property("FlashlightOn?", False)
    # os nos do BeginPlay ficam (nao se apagam grafos); sem a pose e com a vela oculta eles so reposicionam a luz: o
    # desfazer completo do lampiao pede tambem desligar esses dois nos a mao
    BEL.compile_blueprint(bp)
    w("salvo", EAL.save_loaded_asset(bp, False))


def main():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    open(LOG, "w", encoding="utf-8").close()
    modo = next((a for a in sys.argv[1:] if a in ("sondar", "instalar", "verificar", "desfazer")), "sondar")
    w("modo:", modo)
    try:
        {"sondar": sondar, "instalar": instalar, "verificar": verificar, "desfazer": desfazer}[modo]()
    except Aborta as ex:
        w("ABORTADO:", ex, "| sujos:", ale.sujos())
    except Exception:
        w("ERRO " + traceback.format_exc(), "| sujos:", ale.sujos())


if __name__ == "__main__":
    main()
