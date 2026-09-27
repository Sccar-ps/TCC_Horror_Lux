# LUX - Etapas 2 e 4: barulhos e sustos por loop (Mapa_B). LUX_EVT v1.
#   py "<projeto>/Tools/Loop/add_loop_events.py" sondar|instalar|verificar|desfazer
# Pecas:
#   BP_LuxEventHub (ator EVENTS_Hub): regras globais (gap, cotas, janela pos-troca, bloqueios, distorcao), rolos
#     deterministicos por semente, log (Saved/SaveGames/LuxLog_*.sav) e API de console (ke * LigarSustos etc.).
#   BP_LuxLoopEvent (atores EV_* e MARCA_*): caixa-gatilho + ponto de som + aparicao; configurado por instancia.
#   Assets: SA_LuxEvento, CS_LuxSusto, MI_LuxSombra, BP_LuxLogSave (pasta /Game/Masion/LUX/Loop/Eventos).
# So LE PedirTroca, BP_LuxLoopManager, BP_LuxCeu, BP_LuxAudioLoop e o dono do GatilhoFechar. Nunca apaga grafo,
# nunca recarrega pacote. Funcoes de BP no lugar de eventos com parametro (ke * Funcao args).
import importlib, json, math, os, sys, traceback, unreal

INSTALAR_SUSTOS = True        # etapa 4 (27/09): rodar instalar de novo so cria o que falta
ESCRITORIO_NO_LUGAR_DA_COZINHA = True   # o Mapa_B nao tem cozinha; o Gabriel escolheu o escritorio (27/09)
ALTURA_OLHO = 166.0   # camera do BP_Player_Cowboy: capsula 96 + SpringArm 70 (o BaseEyeHeight 64 nao e usado pela camera)
VERSAO = 1
EAL, BEL, BGE = unreal.EditorAssetLibrary, unreal.BlueprintEditorLibrary, unreal.BlueprintGraphEditor
DIR = "/Game/Masion/LUX/Loop/Eventos"
HUB = DIR + "/BP_LuxEventHub"
EVT = DIR + "/BP_LuxLoopEvent"
SAVE = DIR + "/BP_LuxLogSave"
SA = DIR + "/SA_LuxEvento"
CS = DIR + "/CS_LuxSusto"
MI = DIR + "/MI_LuxSombra"
HUB_C, EVT_C, SAVE_C = HUB + ".BP_LuxEventHub_C", EVT + ".BP_LuxLoopEvent_C", SAVE + ".BP_LuxLogSave_C"
MGR_C = "/Game/Masion/LUX/Loop/BP_LuxLoopManager.BP_LuxLoopManager_C"
CEU_C = "/Game/Masion/LUX/Ceu/BP_LuxCeu.BP_LuxCeu_C"
TAG = "LUX_LOOP_EVENTO"
FOLDER = "LuxEventos"
KSL, KML, GS, ARR = ("/Script/Engine.KismetSystemLibrary:", "/Script/Engine.KismetMathLibrary:",
                     "/Script/Engine.GameplayStatics:", "/Script/Engine.KismetArrayLibrary:")
STR, TXT = "/Script/Engine.KismetStringLibrary:", "/Script/Engine.KismetTextLibrary:"
MAC = "/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:"
AQUI = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(os.path.dirname(AQUI))
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
SNAP = os.path.join(SAVED, "LuxSnapshots")
LOG = os.path.join(SNAP, "loop_events_log.txt")
sys.path.insert(0, AQUI)
import add_door_slam as ads
importlib.reload(ads)
G, ok_pin = ads.G, ads.ok_pin

SONS = {
    "HL": "/Game/FPMovement/Assets/Audio/Abilitys/Flashlight/SW_Flashlight_Hit",
    "SCD": "/Game/FPMovement/Assets/Audio/Abilitys/Door/SW_Close_Door",
    "PASSOS": "/Game/FPMovement/Assets/Audio/Character/Footsteps/SoundCues/Footsteps_Metal_Cue",
    "MADEIRA": "/Game/FPMovement/Assets/Audio/Character/Footsteps/SoundCues/Footsteps_Wood_Cue",
    "VULTO_PASSO": "/Game/Masion/LUX/Loop/Eventos/SC_LuxVultoPasso",  # criado pelo Tools/Loop/add_vulto_corre.py (rode antes)
    "PORTAL": "/Game/Backrooms_Ambience/Cues/2_FULL_Backrooms_Portal__by_juanjo_sound__Cue",
    "MEMORIES": "/Game/Backrooms_Ambience/Cues/5_FULL_Backrooms_Memories__by_juanjo_sound__Cue",
    "MIRAGE": "/Game/Backrooms_Ambience/Cues/7_FULL_Backrooms_Mirage__by_juanjo_sound__Cue",
    "BROKEN": "/Game/Backrooms_Ambience/Cues/8_FULL_Broken_Backrooms_Portal__by_juanjo_sound__Cue"}


def w(*a):
    line = " ".join(str(x) for x in a)
    unreal.log("[LUX evt] " + line)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


class Aborta(Exception):
    pass


def atores():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()


def por_label(lab):
    lst = [a for a in atores() if a.get_actor_label() == lab]
    return lst[0] if len(lst) == 1 else None


def sujos():
    U = unreal.EditorLoadingAndSavingUtils
    return sorted(p.get_name() for p in list(U.get_dirty_map_packages()) + list(U.get_dirty_content_packages()))


# ------------------------------------------------------------------ helpers de grafo
class B:
    def __init__(self, ge, me):
        self.g, self.ge, self.me = G(ge), ge, me

    def v(self, nome, x=0, y=0, cls=""):
        return (self.g.get(nome, x, y, cls), nome)

    def lk(self, src, node, pin):
        self.g.link(src[0], src[1], node, pin)

    def c(self, path, x, y, **vals):
        return self.g.call(path, x, y, **vals)

    def out(self, node, pin="ReturnValue"):
        return (node, pin)

    def s(self, partes, x=0, y=0):
        acc = None
        for p in partes:
            a = self.c(STR + "Concat_StrStr", x, y)
            x += 20
            if acc is None:
                self.g.val(a, "A", "")
            else:
                self.lk(acc, a, "A")
            if isinstance(p, str):
                if p:
                    self.g.val(a, "B", p)
            else:
                self.lk(p, a, "B")
            acc = (a, "ReturnValue")
        return acc

    def fs(self, src):
        n = self.c(STR + "Conv_DoubleToString", 0, 0)
        self.lk(src, n, "InDouble")
        return (n, "ReturnValue")

    def is_(self, src):
        n = self.c(STR + "Conv_IntToString", 0, 0)
        self.lk(src, n, "InInt")
        return (n, "ReturnValue")

    def bs(self, src):
        n = self.c(STR + "Conv_BoolToString", 0, 0)
        self.lk(src, n, "InBool")
        return (n, "ReturnValue")

    def now(self):
        return (self.c(GS + "GetTimeSeconds", 0, 0), "ReturnValue")

    def op(self, fn, a, b):
        """operador promovivel/binario: liga A e B (tipa ao ligar); b pode ser literal"""
        n = self.c(KML + fn, 0, 0)
        self.lk(a, n, "A")
        if isinstance(b, tuple):
            self.lk(b, n, "B")
        else:
            self.g.val(n, "B", b)
        return (n, "ReturnValue")

    def menos_agora(self, var):
        """Now - var"""
        return self.op("Subtract_DoubleDouble", self.now(), self.v(var))

    def e(self, a, b):
        return self.op("BooleanAND", a, b)

    def ou(self, a, b):
        return self.op("BooleanOR", a, b)

    def nao(self, a):
        n = self.c(KML + "Not_PreBool", 0, 0)
        self.lk(a, n, "A")
        return (n, "ReturnValue")

    def br(self, cond, x=0, y=0):
        b = self.g.branch(x, y)
        self.lk(cond, b, "Condition")
        return b

    def valido(self, src):
        n = self.c(KSL + "IsValid", 0, 0)
        self.lk(src, n, "Object")
        return (n, "ReturnValue")

    def setv(self, nome, valor=None, src=None, alvo=None, cls=""):
        n = self.g.set(nome, 0, 0, valor, cls)
        if src is not None:
            self.lk(src, n, nome)
        if alvo is not None:
            self.lk(alvo, n, "self")
        return n

    def call(self, fn, alvo=None, cls=None, **vals):
        n = self.c((cls or self.me) + ":" + fn, 0, 0, **vals)
        if alvo is not None:
            self.lk(alvo, n, "self")
        return n

    def timer(self, fn, t, loop=False):
        n = self.c(KSL + "K2_SetTimer", 0, 0, FunctionName=fn, bLooping="true" if loop else "false")
        if isinstance(t, tuple):
            self.lk(t, n, "Time")
        else:
            self.g.val(n, "Time", t)
        return n

    def clear(self, fn):
        return self.c(KSL + "K2_ClearTimer", 0, 0, FunctionName=fn)

    def contem(self, arr, item):
        n = self.c(ARR + "Array_Contains", 0, 0)
        self.lk(arr, n, "TargetArray")
        if isinstance(item, tuple):
            self.lk(item, n, "ItemToFind")
        else:
            self.g.val(n, "ItemToFind", item)
        return (n, "ReturnValue")

    def ch(self, *steps):
        self.g.chain(*steps)


def junc(b):
    """no de juncao (Branch com Condition=true) para convergir caminhos"""
    n = b.g.branch(0, 0)
    b.g.val(n, "Condition", "true")
    return n


def entrada(bp, nome, me):
    fe = BGE.get_graph_editor_by_name(bp, nome)
    return B(fe, me), fe.find_graph_entry_pin().get_owning_node()


def cria_funcoes(bp, lista, tipos):
    graficos = [str(x) for x in BEL.list_graph_names(bp)]
    for nome, params in lista:
        if nome in graficos:
            raise Aborta("%s ja tem a funcao %s: BP incompleto de uma execucao anterior (feche o editor sem salvar)" % (bp.get_name(), nome))
        fe = BGE.create_and_edit_function_graph(bp, nome)
        if fe.get_graph().get_name() != nome:
            raise Aborta("grafo %s criado como %s" % (nome, fe.get_graph().get_name()))
        for pn, pt in params:
            fe.add_graph_input_parameter(pn, tipos[pt])


def cria_vars(bp, lista, tipos, cat):
    exist = [str(n) for n in BEL.list_member_variable_names(bp)]
    for nome, tp, ed, _ in lista:
        if nome not in exist:
            BEL.add_member_variable(bp, nome, tipos[tp])
        BEL.set_blueprint_variable_instance_editable(bp, nome, ed)
        BEL.set_blueprint_variable_category(bp, nome, unreal.Text(cat if ed else cat + "|Estado"))


def padroes(bp, lista):
    cdo = unreal.get_default_object(bp.generated_class())
    for nome, _, _, pad in lista:
        if pad is not None:
            cdo.set_editor_property(nome, pad)


def erros_bp(bp):
    out = []
    for gname in [str(x) for x in BEL.list_graph_names(bp)]:
        try:
            ge = BGE.get_graph_editor_by_name(bp, gname)
        except Exception:
            continue
        for kind, lst in (("ERRO", ge.list_nodes_with_errors()), ("aviso", ge.list_nodes_with_warnings())):
            out += ["%s em %s: %s" % (kind, gname, str(n.get_node_title()).replace("\n", " ")) for n in lst]
    return out


def tipos_base():
    t = {k: BEL.get_basic_type_by_name(k) for k in ("bool", "int", "real", "string", "name")}
    for k in ("bool", "int", "real", "string"):
        t[k + "[]"] = BEL.get_array_type(t[k])
    obj = lambda c: BEL.get_object_reference_type(c.static_class())
    t.update({"actor": obj(unreal.Actor), "lsa": obj(unreal.LevelSequenceActor), "snd": obj(unreal.SoundBase),
              "att": obj(unreal.SoundAttenuation), "ac": obj(unreal.AudioComponent),
              "light[]": BEL.get_array_type(obj(unreal.LightComponent)),
              "shake": BEL.get_class_reference_type(unreal.CameraShakeBase.static_class()),
              "rot": BEL.get_struct_type(unreal.Rotator.static_struct()), "vec": BEL.get_struct_type(unreal.Vector.static_struct()),
              "mgr": BEL.get_object_reference_type(EAL.load_asset(MGR_C.split(".")[0]).generated_class()),
              "ceu": BEL.get_object_reference_type(EAL.load_asset(CEU_C.split(".")[0]).generated_class())})
    return t


# ------------------------------------------------------------------ assets simples
def ensure_assets():
    at = unreal.AssetToolsHelpers.get_asset_tools()
    if not EAL.does_directory_exist(DIR):
        EAL.make_directory(DIR)
    criados = []
    if not EAL.does_asset_exist(SA):
        a = at.create_asset("SA_LuxEvento", DIR, unreal.SoundAttenuation, unreal.SoundAttenuationFactory())
        s = a.get_editor_property("attenuation")
        for k, v in (("attenuate", True), ("spatialize", True), ("attenuation_shape", unreal.AttenuationShape.SPHERE),
                     ("attenuation_shape_extents", unreal.Vector(200.0, 0, 0)), ("falloff_distance", 1800.0),
                     ("distance_algorithm", unreal.AttenuationDistanceModel.NATURAL_SOUND), ("d_b_attenuation_at_max", -24.0)):
            s.set_editor_property(k, v)
        a.set_editor_property("attenuation", s)
        criados.append(a)
    if not EAL.does_asset_exist(CS):
        bp = BEL.create_blueprint_asset_with_parent(CS, unreal.LegacyCameraShake)
        BEL.compile_blueprint(bp)
        cdo = unreal.get_default_object(bp.generated_class())
        for k, v in (("oscillation_duration", 0.40), ("oscillation_blend_in_time", 0.05), ("oscillation_blend_out_time", 0.20)):
            try:
                cdo.set_editor_property(k, v)
            except Exception as ex:
                w("  AVISO CS_LuxSusto: %s nao definido (%s)" % (k, ex))
        ro = cdo.get_editor_property("rot_oscillation")
        for eixo, amp, freq in (("pitch", 1.5, 12.0), ("yaw", 1.0, 10.0)):
            o = ro.get_editor_property(eixo)
            o.set_editor_property("amplitude", amp)
            o.set_editor_property("frequency", freq)
            ro.set_editor_property(eixo, o)
        cdo.set_editor_property("rot_oscillation", ro)
        lo = cdo.get_editor_property("loc_oscillation")
        z = lo.get_editor_property("z")
        z.set_editor_property("amplitude", 2.0)
        z.set_editor_property("frequency", 15.0)
        lo.set_editor_property("z", z)
        cdo.set_editor_property("loc_oscillation", lo)
        criados.append(bp)
    if not EAL.does_asset_exist(MI):
        mi = at.create_asset("MI_LuxSombra", DIR, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        mi.set_editor_property("parent", EAL.load_asset("/Engine/BasicShapes/BasicShapeMaterial"))
        unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(mi, "Color", unreal.LinearColor(0.02, 0.02, 0.02, 1.0))
        criados.append(mi)
    if not EAL.does_asset_exist(SAVE):
        bp = BEL.create_blueprint_asset_with_parent(SAVE, unreal.SaveGame)
        BEL.add_member_variable(bp, "Linhas", BEL.get_array_type(BEL.get_basic_type_by_name("string")))
        BEL.compile_blueprint(bp)
        criados.append(bp)
    criados += ensure_vulto()
    return criados


def ensure_vulto():
    """SM_LuxVulto (Geometry Script: malha do SKM_Manny_Simple na pose de referencia), M_LuxVulto (unlit) e MI_LuxVulto."""
    out = []
    MEL = unreal.MaterialEditingLibrary
    if not EAL.does_asset_exist(VULTO_M):
        m = unreal.AssetToolsHelpers.get_asset_tools().create_asset("M_LuxVulto", DIR, unreal.Material, unreal.MaterialFactoryNew())
        m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
        cor = MEL.create_material_expression(m, unreal.MaterialExpressionVectorParameter, -400, 0)
        cor.set_editor_property("parameter_name", "Cor")
        cor.set_editor_property("default_value", unreal.LinearColor(*VULTO_COR, 1.0))
        MEL.connect_material_property(cor, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        MEL.recompile_material(m)
        out.append(m)
    if not EAL.does_asset_exist(VULTO_MI):
        mi = unreal.AssetToolsHelpers.get_asset_tools().create_asset("MI_LuxVulto", DIR, unreal.MaterialInstanceConstant,
                                                                     unreal.MaterialInstanceConstantFactoryNew())
        mi.set_editor_property("parent", EAL.load_asset(VULTO_M))
        out.append(mi)
    mi = EAL.load_asset(VULTO_MI)
    atual = MEL.get_material_instance_vector_parameter_value(mi, "Cor")
    if max(abs(atual.r - VULTO_COR[0]), abs(atual.g - VULTO_COR[1]), abs(atual.b - VULTO_COR[2])) > 1e-6:
        MEL.set_material_instance_vector_parameter_value(mi, "Cor", unreal.LinearColor(*VULTO_COR, 1.0))
        MEL.update_material_instance(mi)
    if not EAL.does_asset_exist(VULTO_SM):
        skm = EAL.load_asset("/Game/FreeAnimationLibrary/Demo/Characters/Mannequins/Meshes/SKM_Manny_Simple")
        dm = unreal.DynamicMesh()
        unreal.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(skm, dm, unreal.GeometryScriptCopyMeshFromAssetOptions(),
                                                                     unreal.GeometryScriptMeshReadLOD())
        op = unreal.GeometryScriptCreateNewStaticMeshAssetOptions()
        op.set_editor_property("enable_collision", False)
        unreal.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dm, VULTO_SM, op)
        out.append(EAL.load_asset(VULTO_SM))
    sm = EAL.load_asset(VULTO_SM)
    for i in range(len(sm.get_editor_property("static_materials"))):
        if sm.get_material(i) != mi:
            sm.set_material(i, mi)
    return out


# ------------------------------------------------------------------ BP_LuxLoopEvent: variaveis e funcoes
def vars_evento():
    sa = EAL.load_asset(SA)
    cs = EAL.load_asset(CS)
    return [  # nome, tipo, editavel, padrao
        ("Id", "string", True, ""), ("IdNum", "int", True, 0), ("bAtivo", "bool", True, True), ("Categoria", "int", True, 0),
        ("Loops", "int[]", True, None), ("LoopMinimo", "int", True, 0), ("bUmaVezPorSessao", "bool", True, False),
        ("Probabilidade", "real", True, 1.0), ("AtrasoS", "real", True, 0.0), ("JanelaS", "real", True, 6.0),
        ("bExigirDentro", "bool", True, False), ("DistMaxJogador", "real", True, 0.0), ("bSoQuandoOlhando", "bool", True, False),
        ("CosOlhar", "real", True, 0.8), ("bSoQuandoDeCostas", "bool", True, False), ("CosCostas", "real", True, -0.2),
        ("bExigirLinhaVisao", "bool", True, False), ("bExigirVistoAntes", "bool", True, False), ("Som", "snd", True, None),
        ("Volume", "real", True, 0.5), ("Pitch", "real", True, 1.0), ("InicioS", "real", True, 0.0), ("SomCamada", "snd", True, None),
        ("RelCamada", "real", True, 0.75), ("PitchCamada", "real", True, 1.0), ("Atenuacao", "att", True, sa),
        ("Repeticoes", "int", True, 1), ("IntervaloRepS", "real", True, 0.5), ("DeslocPorRep", "vec", True, None),
        ("DuracaoMaxS", "real", True, 4.0), ("FadeS", "real", True, 1.0), ("bSomNoFimDoPiscar", "bool", True, False),
        ("TagLuzes", "name", True, None), ("PadraoPiscar", "real[]", True, None), ("IntensidadeApagada", "real", True, 0.15),
        ("bApagarNoFim", "bool", True, False), ("RestaurarAposS", "real", True, 0.0), ("EscalaTremor", "real", True, 0.0),
        ("ClasseTremor", "shake", True, cs.generated_class()), ("bAparicao", "bool", True, False), ("AparicaoS", "real", True, 0.5),
        ("AparicaoDistMin", "real", True, 500.0), ("AlvoGirar", "actor", True, None), ("GiroYaw", "real", True, 0.0),
        ("BloqueioS", "real", True, 0.0),
        # estado
        ("Hub", "hub", False, None), ("GeracaoVista", "int", False, 0), ("LoopDisp", "int", False, -1), ("LoopRolado", "int", False, -1),
        ("LoopTent", "int", False, -1), ("bDisparouSessao", "bool", False, False), ("bSkipLogado", "bool", False, False),
        ("bVisto", "bool", False, False), ("bDentro", "bool", False, False), ("EntradaT", "real", False, -1000.0),
        ("TentT", "real", False, -1000.0), ("Estado", "string", False, ""), ("LoopEstado", "int", False, -1),
        ("UltAplica", "bool", False, False), ("UltOlhando", "bool", False, False), ("UltCostas", "bool", False, False),
        ("VB", "real", False, 0.0), ("VC", "real", False, 0.0), ("LoopDoDisparo", "int", False, -1), ("DisparoT", "real", False, -1000.0),
        ("Rep", "int", False, 0), ("Passo", "int", False, 0), ("SomAtual", "ac", False, None), ("SomCamadaAtual", "ac", False, None),
        ("Luzes", "light[]", False, None), ("IntensOrig", "real[]", False, None), ("RotOrig", "rot", False, None),
        ("MotivosEspera", "string[]", False, ["troca", "pos_troca", "aguarda_marca", "externo", "distorcao", "reserva"]),
        ("MotivosReserva", "string[]", False, MOTIVOS_RESERVA), ("VersaoSpec", "int", False, 0)]


# 27/09: susto esperando o bloqueio da troca/distorcao/batida tambem reserva a vez (senao um barulho passa na frente
# no mesmo instante e o susto perde a janela na caminhada direta)
MOTIVOS_RESERVA = ["gap", "vista", "costas", "nao_visto", "pos_troca", "externo", "distorcao", "aguarda_marca"]
TAG_LUZES = "LUX_EV_Arandela"
LUZES_SUSTO = ["LUX_Luz_Sala_Candelabro", "LUX_Luz_Sala_Candelabro2", "LUX_Luz_Sala_Candelabro3",
               "LUX_Luz_Sala_Abajur"]  # 27/09: abajur (0.63) junto, os candelabros (0.05) sozinhos passavam despercebidos
GAP_MIN_S = 3.0  # 27/09: gap do EVENTS_Hub (instancia) 10 -> 5 -> 3 s (teste do Gabriel: sustos e barulhos precisam caber)
VOLUME_MAX = 2.1  # 27/09 17:33: 1.5 -> 2.1 (sustos x1.4 de novo, pedido do Gabriel). 27/09: VolumeMax do EVENTS_Hub (instancia) 0.8 -> 1.5; sustos com som x1.8 (pedido do Gabriel: mais altos)
TREMOR_MAX = 1.5  # 27/09: EscalaTremorMax do EVENTS_Hub (instancia); o estrondo a 0.5 passava despercebido
VULTO_SM = DIR + "/SM_LuxVulto"   # silhueta humana (pose de referencia do SKM_Manny_Simple) no lugar do cilindro
VULTO_M = DIR + "/M_LuxVulto"     # unlit; a silhueta preta sumia no corredor escuro (capturas 27/09)
VULTO_MI = DIR + "/MI_LuxVulto"
VULTO_COR = (0.004, 0.0045, 0.0055)  # cinza-sombra levemente azulado, nada vermelho
CADEIRA_YAW_BASE = 180.0  # LOOPC_L4_Cadeira comeca virada para a parede do piano...
CADEIRA_ALVO = (-2330.0, -1800.0)  # ...e gira para ficar de frente para a regiao entre ela e a LOOP_PortaSala


FUNC_EVT = [("Inicializar", []), ("Aplica", [("L", "int")]), ("TentarDisparar", []), ("Repetir", [("M", "string")]),
            ("Olhando", []), ("DeCostas", []), ("Executar", []), ("TocarRepeticao", []), ("CortarSom", []),
            ("PassoPiscar", []), ("FimPiscar", []), ("RestaurarLuzes", []), ("EsconderAparicao", []),
            ("VigiarTroca", []), ("VigiarVisto", []), ("ForcarSe", [("IdAlvo", "string")])]


def vars_hub():
    return [
        ("bEventosAtivos", "bool", True, True), ("bBarulhos", "bool", True, True), ("bSustos", "bool", True, True),
        ("bReservarSuprimidos", "bool", True, False), ("bLogBloqueios", "bool", True, True), ("bDebugTela", "bool", True, False),
        ("GapMinS", "real", True, 10.0), ("JanelaPosTrocaS", "real", True, 3.0), ("MaxSustosPorLoop", "int", True, 1),
        ("MaxBarulhosPorLoop", "int", True, 3), ("VolumeGlobal", "real", True, 1.0), ("VolumeMax", "real", True, 0.8),
        ("EscalaTremorMax", "real", True, 1.0), ("Semente", "int", True, 0), ("Participante", "string", True, ""),
        ("Condicao", "string", True, ""),
        ("Manager", "mgr", False, None), ("Ceu", "ceu", False, None), ("SeqDist", "lsa", False, None), ("Eventos", "evt[]", False, None),
        ("Geracao", "int", False, 0), ("LoopCache", "int", False, 0), ("TrocaT", "real", False, -1000.0),
        ("UltimoEventoT", "real", False, -1000.0), ("BloqueioAteT", "real", False, -1000.0), ("SustoPendenteAteT", "real", False, -1000.0),
        ("bMarcaPendente", "bool", False, False), ("ContBarulhos", "int", False, 0), ("ContSustos", "int", False, 0),
        ("Rolos", "real[]", False, None), ("UltRolo", "real", False, 0.0), ("UltOk", "bool", False, False),
        ("UltMotivo", "string", False, ""), ("UltSuprimir", "bool", False, False), ("UltVB", "real", False, 0.0),
        ("UltVC", "real", False, 0.0), ("Log", "string[]", False, None), ("Slot", "string", False, ""), ("VersaoSpec", "int", False, 0)]


FUNC_HUB = [("Registrar", [("IdEv", "string"), ("Acao", "string"), ("Det", "string")]), ("SalvarLog", []), ("GerarRolos", []),
            ("Rolar", [("N", "int")]), ("VigiarLoop", []), ("PodeDisparar", [("Cat", "int")]),
            ("Notificar", [("Cat", "int"), ("IdEv", "string"), ("Acao", "string"), ("Det", "string")]),
            ("MarcarInicio", [("IdEv", "string")]), ("Bloquear", [("S", "real")]), ("ReservarSusto", []),
            ("Volumes", [("V", "real"), ("Rel", "real")]), ("Inicializar", []), ("Finalizar", []),
            ("LigarBarulhos", []), ("DesligarBarulhos", []), ("LigarSustos", []), ("DesligarSustos", []), ("LigarTudo", []),
            ("DesligarTudo", []), ("DefinirSemente", [("Valor", "int")]), ("DefinirVolumeGlobal", [("Valor", "real")]),
            ("DebugTela", [("Ligar", "bool")]), ("ImprimirLog", []), ("Resetar", [])]


def registrar(b, hub_ref, idev, acao, det):
    """chama Hub.Registrar; idev/acao/det: literal ou (no,pino)"""
    n = b.call("Registrar", alvo=hub_ref, cls=HUB_C)
    for pin, val in (("IdEv", idev), ("Acao", acao), ("Det", det)):
        if isinstance(val, tuple):
            b.lk(val, n, pin)
        elif val:
            b.g.val(n, pin, val)
    return n


# ------------------------------------------------------------------ grafo do hub
def build_hub(bp):
    me = HUB_C
    # Registrar(IdEv, Acao, Det)
    b, en = entrada(bp, "Registrar", me)
    asdt = b.c(TXT + "AsDateTime_DateTime", 0, 0)
    b.lk((b.c(KML + "UtcNow", 0, 0), "ReturnValue"), asdt, "In")
    t2s = b.c(TXT + "Conv_TextToString", 0, 0)
    b.lk((asdt, "ReturnValue"), t2s, "InText")
    linha = b.s([(t2s, "ReturnValue"), "|jogo=", b.fs(b.now()), "|real=", b.fs((b.c(GS + "GetRealTimeSeconds", 0, 0), "ReturnValue")),
                 "|loop=", b.is_(b.v("LoopCache")), "|", (en, "IdEv"), "|", (en, "Acao"), "|", (en, "Det")])
    add = b.c(ARR + "Array_Add", 0, 0)
    b.lk(b.v("Log"), add, "TargetArray")
    b.lk(linha, add, "NewItem")
    pr = b.c(KSL + "PrintString", 0, 0, bPrintToLog="true", Duration=6.0)
    b.lk(linha, pr, "InString")
    b.lk(b.v("bDebugTela"), pr, "bPrintToScreen")
    b.ch(en, add, pr)

    # SalvarLog
    b, en = entrada(bp, "SalvarLog", me)
    cr = b.c(GS + "CreateSaveGameObject", 0, 0, SaveGameClass="/Script/Engine.BlueprintGeneratedClass'%s'" % SAVE_C)
    nome_cast = next((str(a) for a in b.ge.list_available_nodes([]) if str(a).replace(" ", "").endswith("CastToBP_LuxLogSave")), None)
    if not nome_cast:
        raise Aborta("no 'Cast To BP_LuxLogSave' nao encontrado")
    cast = b.ge.create_node_from_name(nome_cast, unreal.Vector2D(300, 0), [])
    b.lk((cr, "ReturnValue"), cast, next(str(p.get_pin_name()) for p in cast.list_input_pins() if '"exec"' not in str(p.get_pin_type_as_json_schema())))
    como = next(str(p.get_pin_name()) for p in cast.list_output_pins() if str(p.get_pin_name()).startswith("As"))
    sl = b.setv("Linhas", src=b.v("Log"), alvo=(cast, como), cls=SAVE_C)
    sv = b.c(GS + "SaveGameToSlot", 0, 0, UserIndex=0)
    b.lk((cast, como), sv, "SaveGameObject")
    b.lk(b.v("Slot"), sv, "SlotName")
    b.ch(en, cr, cast)
    b.ch((cast, next(str(p.get_pin_name()) for p in cast.list_output_pins() if '"exec"' in str(p.get_pin_type_as_json_schema()))), sl, sv)

    # GerarRolos: Rolos[i] = Frac(Sin(i*12.9898 + Semente*0.001*78.233) * 43758.5453), 500 valores
    b, en = entrada(bp, "GerarRolos", me)
    clr = b.c(ARR + "Array_Clear", 0, 0)
    b.lk(b.v("Rolos"), clr, "TargetArray")
    fl = b.g.pos(b.ge.add_macro_node(MAC + "ForLoop"), 400, 0)
    b.g.val(fl, "FirstIndex", 0)
    b.g.val(fl, "LastIndex", 499)
    idx = b.c(KML + "Conv_IntToDouble", 0, 0)
    b.lk((fl, "Index"), idx, "InInt")
    semd = b.c(KML + "Conv_IntToDouble", 0, 0)
    b.lk(b.v("Semente"), semd, "InInt")
    a1 = b.op("Multiply_DoubleDouble", (idx, "ReturnValue"), 12.9898)
    a2 = b.op("Multiply_DoubleDouble", (semd, "ReturnValue"), 0.078233)
    sn = b.c(KML + "Sin", 0, 0)
    b.lk(b.op("Add_DoubleDouble", a1, a2), sn, "A")
    fr = b.c(KML + "Fraction", 0, 0)
    b.lk(b.op("Multiply_DoubleDouble", (sn, "ReturnValue"), 43758.5453), fr, "A")
    add = b.c(ARR + "Array_Add", 0, 0)
    b.lk(b.v("Rolos"), add, "TargetArray")
    b.lk((fr, "ReturnValue"), add, "NewItem")
    b.ch(en, clr, fl)
    b.ch((fl, "LoopBody"), add)

    # Rolar(N): UltRolo = Rolos[(Clamp(LoopCache,1,5)-1)*100 + N%100]
    b, en = entrada(bp, "Rolar", me)
    cl = b.c(KML + "Clamp", 0, 0, Min=1, Max=5)
    b.lk(b.v("LoopCache"), cl, "Value")
    base = b.op("Multiply_IntInt", b.op("Subtract_IntInt", (cl, "ReturnValue"), 1), 100)
    pct = b.op("Percent_IntInt", (en, "N"), 100)
    get = b.c(ARR + "Array_Get", 0, 0)
    b.lk(b.v("Rolos"), get, "TargetArray")
    b.lk(b.op("Add_IntInt", base, pct), get, "Index")
    s = b.setv("UltRolo", src=(get, "Item"))
    b.ch(en, s)

    # Volumes(V, Rel): k=min(1, VolumeMax/(V*(1+Rel)*VolumeGlobal)); VB=V*VolumeGlobal*k; VC=VB*Rel
    b, en = entrada(bp, "Volumes", me)
    den = b.op("Multiply_DoubleDouble", b.op("Multiply_DoubleDouble", (en, "V"), b.op("Add_DoubleDouble", (en, "Rel"), 1.0)), b.v("VolumeGlobal"))
    k = b.c(KML + "FMin", 0, 0)
    sd = b.c(KML + "SafeDivide", 0, 0)
    b.lk(b.v("VolumeMax"), sd, "A")
    b.lk(den, sd, "B")
    b.lk((sd, "ReturnValue"), k, "A")
    b.g.val(k, "B", 1.0)
    vb = b.op("Multiply_DoubleDouble", b.op("Multiply_DoubleDouble", (en, "V"), b.v("VolumeGlobal")), (k, "ReturnValue"))
    s1 = b.setv("UltVB", src=vb)
    s2 = b.setv("UltVC", src=b.op("Multiply_DoubleDouble", b.v("UltVB"), (en, "Rel")))
    b.ch(en, s1, s2)

    # MarcarInicio(IdEv), Bloquear(S), ReservarSusto
    b, en = entrada(bp, "MarcarInicio", me)
    s = b.setv("UltimoEventoT", src=b.now())
    r = registrar(b, None, (en, "IdEv"), "ONSET", "")
    b.ch(en, s, r)
    b, en = entrada(bp, "Bloquear", me)
    mx = b.c(KML + "FMax", 0, 0)
    b.lk(b.v("BloqueioAteT"), mx, "A")
    b.lk(b.op("Add_DoubleDouble", b.now(), (en, "S")), mx, "B")
    s1 = b.setv("BloqueioAteT", src=(mx, "ReturnValue"))
    s2 = b.setv("bMarcaPendente", "false")
    b.ch(en, s1, s2)
    b, en = entrada(bp, "ReservarSusto", me)
    s = b.setv("SustoPendenteAteT", src=b.op("Add_DoubleDouble", b.now(), 0.5))
    b.ch(en, s)

    # Notificar(Cat, IdEv, Acao, Det)
    b, en = entrada(bp, "Notificar", me)
    s = b.setv("UltimoEventoT", src=b.now())
    c0 = b.br(b.op("EqualEqual_IntInt", (en, "Cat"), 0))
    ib = b.setv("ContBarulhos", src=b.op("Add_IntInt", b.v("ContBarulhos"), 1))
    c1 = b.br(b.op("EqualEqual_IntInt", (en, "Cat"), 1))
    isu = b.setv("ContSustos", src=b.op("Add_IntInt", b.v("ContSustos"), 1))
    r = registrar(b, None, (en, "IdEv"), (en, "Acao"), (en, "Det"))
    b.ch(en, s, c0)
    b.ch((c0, "then"), ib, r)
    b.ch((c0, "else"), c1)
    b.ch((c1, "then"), isu, r)
    b.ch((c1, "else"), r)

    # PodeDisparar(Cat) -> UltOk, UltMotivo, UltSuprimir
    b, en = entrada(bp, "PodeDisparar", me)
    cat = (en, "Cat")

    def falha(m):
        a = b.setv("UltOk", "false")
        c = b.setv("UltMotivo", m)
        d = b.setv("UltSuprimir", "false")
        b.ch(a, c, d)
        return a

    off = b.ou(b.ou(b.nao(b.v("bEventosAtivos")), b.e(b.op("EqualEqual_IntInt", cat, 0), b.nao(b.v("bBarulhos")))),
               b.e(b.op("EqualEqual_IntInt", cat, 1), b.nao(b.v("bSustos"))))
    b1 = b.br(off)
    b1r = b.br(b.v("bReservarSuprimidos"))
    sup = [b.setv("UltOk", "true"), b.setv("UltMotivo", "suprimido"), b.setv("UltSuprimir", "true")]
    b.ch(*sup)
    pc = (b.c(GS + "GetPlayerController", 0, 0, PlayerIndex=0), "ReturnValue")
    vt = b.c("/Script/Engine.Controller:GetViewTarget", 0, 0)
    b.lk(pc, vt, "self")
    ne = b.c(KML + "NotEqual_ObjectObject", 0, 0)
    b.lk((vt, "ReturnValue"), ne, "A")
    b.lk((b.c(GS + "GetPlayerPawn", 0, 0, PlayerIndex=0), "ReturnValue"), ne, "B")
    b2 = b.br((ne, "ReturnValue"))
    b3 = b.br(b.op("Less_DoubleDouble", b.menos_agora("TrocaT"), b.v("JanelaPosTrocaS")))
    b4 = b.br(b.v("bMarcaPendente"))
    b4t = b.br(b.op("Greater_DoubleDouble", b.menos_agora("TrocaT"), 60.0))
    mt = b.setv("bMarcaPendente", "false")
    mtl = registrar(b, None, "HUB", "MARCA_TIMEOUT", "")
    b.ch(mt, mtl)
    j5 = junc(b)
    b5 = b.br(b.op("Less_DoubleDouble", b.now(), b.v("BloqueioAteT")))
    b6v = b.br(b.valido(b.v("SeqDist")))
    gp = b.c("/Script/LevelSequence.LevelSequenceActor:GetSequencePlayer", 0, 0)
    b.lk(b.v("SeqDist"), gp, "self")
    ip = b.c("/Script/MovieScene.MovieSceneSequencePlayer:IsPlaying", 0, 0)
    b.lk((gp, "ReturnValue"), ip, "self")
    b6p = b.br(b.e(b.valido((gp, "ReturnValue")), (ip, "ReturnValue")))
    j7 = junc(b)
    b7 = b.br(b.e(b.op("EqualEqual_IntInt", cat, 0), b.op("Less_DoubleDouble", b.now(), b.v("SustoPendenteAteT"))))
    b8 = b.br(b.op("Less_DoubleDouble", b.menos_agora("UltimoEventoT"), b.v("GapMinS")))
    cota = b.ou(b.e(b.op("EqualEqual_IntInt", cat, 0), b.op("GreaterEqual_IntInt", b.v("ContBarulhos"), b.v("MaxBarulhosPorLoop"))),
                b.e(b.op("EqualEqual_IntInt", cat, 1), b.op("GreaterEqual_IntInt", b.v("ContSustos"), b.v("MaxSustosPorLoop"))))
    b9 = b.br(cota)
    okn = [b.setv("UltOk", "true"), b.setv("UltMotivo", "ok"), b.setv("UltSuprimir", "false")]
    b.ch(*okn)
    b.ch(en, b1)
    b.ch((b1, "then"), b1r)
    b.ch((b1r, "then"), sup[0])
    b.ch((b1r, "else"), falha("categoria"))
    b.ch((b1, "else"), b2)
    b.ch((b2, "then"), falha("troca"))
    b.ch((b2, "else"), b3)
    b.ch((b3, "then"), falha("pos_troca"))
    b.ch((b3, "else"), b4)
    b.ch((b4, "then"), b4t)
    b.ch((b4t, "then"), mt)
    b.ch(mtl, j5)
    b.ch((b4t, "else"), falha("aguarda_marca"))
    b.ch((b4, "else"), j5)
    b.ch((j5, "then"), b5)
    b.ch((b5, "then"), falha("externo"))
    b.ch((b5, "else"), b6v)
    b.ch((b6v, "then"), b6p)
    b.ch((b6p, "then"), falha("distorcao"))
    b.ch((b6p, "else"), j7)
    b.ch((b6v, "else"), j7)
    b.ch((j7, "then"), b7)
    b.ch((b7, "then"), falha("reserva"))
    b.ch((b7, "else"), b8)
    b.ch((b8, "then"), falha("gap"))
    b.ch((b8, "else"), b9)
    b.ch((b9, "then"), falha("cota"))
    b.ch((b9, "else"), okn[0])

    # VigiarLoop
    b, en = entrada(bp, "VigiarLoop", me)
    bv = b.br(b.valido(b.v("Manager")))
    la = b.v("LoopAtual", cls=MGR_C)
    b.lk(b.v("Manager"), la[0], "self")
    bm = b.br(b.op("NotEqual_IntInt", la, b.v("LoopCache")))
    fe1 = b.g.pos(b.ge.add_macro_node(MAC + "ForEachLoop"), 0, 0)
    b.lk(b.v("Eventos"), fe1, "Array")
    ap = b.call("Aplica", alvo=(fe1, "Array Element"), cls=EVT_C)
    b.lk(b.v("LoopCache"), ap, "L")
    ua = b.v("UltAplica", cls=EVT_C)
    b.lk((fe1, "Array Element"), ua[0], "self")
    bap = b.br(ua)
    le = b.v("LoopEstado", cls=EVT_C)
    b.lk((fe1, "Array Element"), le[0], "self")
    es = b.v("Estado", cls=EVT_C)
    b.lk((fe1, "Array Element"), es[0], "self")
    sel = b.c(KML + "SelectString", 0, 0, B="NAO_ALCANCADO")
    b.lk(es, sel, "A")
    b.lk(b.op("EqualEqual_IntInt", le, b.v("LoopCache")), sel, "bPickA")
    idv = b.v("Id", cls=EVT_C)
    b.lk((fe1, "Array Element"), idv[0], "self")
    rres = registrar(b, None, idv, "RESUMO", (sel, "ReturnValue"))
    s_lc = b.setv("LoopCache", src=la)
    s_tt = b.setv("TrocaT", src=b.now())
    z1 = b.setv("ContBarulhos", 0)
    z2 = b.setv("ContSustos", 0)
    s_mp = b.setv("bMarcaPendente", "false")
    fe2 = b.g.pos(b.ge.add_macro_node(MAC + "ForEachLoop"), 0, 0)
    b.lk(b.v("Eventos"), fe2, "Array")
    cat2 = b.v("Categoria", cls=EVT_C)
    b.lk((fe2, "Array Element"), cat2[0], "self")
    bmk = b.br(b.op("EqualEqual_IntInt", cat2, 2))
    ap2 = b.call("Aplica", alvo=(fe2, "Array Element"), cls=EVT_C)
    b.lk(b.v("LoopCache"), ap2, "L")
    ua2 = b.v("UltAplica", cls=EVT_C)
    b.lk((fe2, "Array Element"), ua2[0], "self")
    bap2 = b.br(ua2)
    s_mt = b.setv("bMarcaPendente", "true")
    rt = registrar(b, None, "HUB", "TROCA", b.s(["loop=", b.is_(b.v("LoopCache")), " marca_pendente=", b.bs(b.v("bMarcaPendente"))]))
    sl = b.call("SalvarLog")
    b.ch(en, bv)
    b.ch((bv, "then"), bm)
    b.ch((bm, "then"), fe1)
    b.ch((fe1, "LoopBody"), ap, bap)
    b.ch((bap, "then"), rres)
    b.ch((fe1, "Completed"), s_lc, s_tt, z1, z2, s_mp, fe2)
    b.ch((fe2, "LoopBody"), bmk)
    b.ch((bmk, "then"), ap2, bap2)
    b.ch((bap2, "then"), s_mt)
    b.ch((fe2, "Completed"), rt, sl)

    # Inicializar (BeginPlay)
    b, en = entrada(bp, "Inicializar", me)
    fm = b.c(GS + "GetActorOfClass", 0, 0, ActorClass="/Script/Engine.BlueprintGeneratedClass'%s'" % MGR_C)
    sm = b.setv("Manager", src=(fm, "ReturnValue"))
    fc = b.c(GS + "GetActorOfClass", 0, 0, ActorClass="/Script/Engine.BlueprintGeneratedClass'%s'" % CEU_C)
    sc = b.setv("Ceu", src=(fc, "ReturnValue"))
    ga = b.c(GS + "GetAllActorsOfClassWithTag", 0, 0, ActorClass="/Script/CoreUObject.Class'/Script/LevelSequence.LevelSequenceActor'", Tag="LuxDistorcao")
    bl = b.br(b.op("Greater_IntInt", (lambda n: (n, "ReturnValue"))(b.c(ARR + "Array_Length", 0, 0)), 0)) if False else None
    ln = b.c(ARR + "Array_Length", 0, 0)
    b.lk((ga, "OutActors"), ln, "TargetArray")
    bl = b.br(b.op("Greater_IntInt", (ln, "ReturnValue"), 0))
    g0 = b.c(ARR + "Array_Get", 0, 0, Index=0)
    b.lk((ga, "OutActors"), g0, "TargetArray")
    ss = b.setv("SeqDist", src=(g0, "Item"))
    gev = b.c(GS + "GetAllActorsOfClass", 0, 0, ActorClass="/Script/Engine.BlueprintGeneratedClass'%s'" % EVT_C)
    se = b.setv("Eventos", src=(gev, "OutActors"))
    bs0 = b.br(b.op("EqualEqual_IntInt", b.v("Semente"), 0))
    rnd = b.c(KML + "RandomIntegerInRange", 0, 0, Min=1, Max=2147483646)
    ssem = b.setv("Semente", src=(rnd, "ReturnValue"))
    gr = b.call("GerarRolos")
    bmv = b.br(b.valido(b.v("Manager")))
    la = b.v("LoopAtual", cls=MGR_C)
    b.lk(b.v("Manager"), la[0], "self")
    slc = b.setv("LoopCache", src=la)
    j = junc(b)
    stt = b.setv("TrocaT", src=b.now())
    ux = b.c(KML + "ToUnixTimestamp", 0, 0)
    b.lk((b.c(KML + "UtcNow", 0, 0), "ReturnValue"), ux, "Time")
    uxs = b.c(STR + "Conv_Int64ToString", 0, 0)
    b.lk((ux, "ReturnValue"), uxs, "InInt")
    sslot = b.setv("Slot", src=b.s(["LuxLog_", b.v("Participante"), "_", (uxs, "ReturnValue")]))
    tm = b.timer("VigiarLoop", 0.25, loop=True)
    dist_on = b.v("bDistorcaoAtiva", cls=CEU_C)
    b.lk(b.v("Ceu"), dist_on[0], "self")
    bat = b.v("bBaterPortaAtivo", cls=MGR_C)
    b.lk(b.v("Manager"), bat[0], "self")
    head = b.s(["participante=", b.v("Participante"), " condicao=", b.v("Condicao"), " semente=", b.is_(b.v("Semente")),
                " versao=", b.is_(b.v("VersaoSpec")), " eventos=", b.bs(b.v("bEventosAtivos")), " barulhos=", b.bs(b.v("bBarulhos")),
                " sustos=", b.bs(b.v("bSustos")), " vol=", b.fs(b.v("VolumeGlobal")), " volmax=", b.fs(b.v("VolumeMax")),
                " gap=", b.fs(b.v("GapMinS")), " postroca=", b.fs(b.v("JanelaPosTrocaS")), " distorcao=", b.bs(dist_on),
                " batida=", b.bs(bat), " n_eventos=", b.is_((lambda n: (b.lk(b.v("Eventos"), n, "TargetArray"), (n, "ReturnValue"))[1])(b.c(ARR + "Array_Length", 0, 0)))])
    rh = registrar(b, None, "HUB", "HEADER", head)
    b.ch(en, fm, sm, fc, sc, ga, bl)
    b.ch((bl, "then"), ss, gev)
    b.ch((bl, "else"), gev)
    b.ch(gev, se, bs0)
    b.ch((bs0, "then"), ssem, gr)
    b.ch((bs0, "else"), gr)
    b.ch(gr, bmv)
    b.ch((bmv, "then"), slc, j)
    b.ch((bmv, "else"), j)
    b.ch((j, "then"), stt, sslot, tm, rh)

    # Finalizar (EndPlay)
    b, en = entrada(bp, "Finalizar", me)
    r = registrar(b, None, "HUB", "FIM", "")
    b.ch(en, r, b.call("SalvarLog"))

    # API
    for nome, var, val in (("LigarBarulhos", "bBarulhos", "true"), ("DesligarBarulhos", "bBarulhos", "false"),
                           ("LigarSustos", "bSustos", "true"), ("DesligarSustos", "bSustos", "false"),
                           ("LigarTudo", "bEventosAtivos", "true"), ("DesligarTudo", "bEventosAtivos", "false")):
        b, en = entrada(bp, nome, me)
        b.ch(en, b.setv(var, val), registrar(b, None, "HUB", nome.upper(), ""))
    b, en = entrada(bp, "DefinirSemente", me)
    b.ch(en, b.setv("Semente", src=(en, "Valor")), b.call("GerarRolos"), registrar(b, None, "HUB", "SEMENTE", b.is_((en, "Valor"))))
    b, en = entrada(bp, "DefinirVolumeGlobal", me)
    cl = b.c(KML + "FClamp", 0, 0, Min=0.0, Max=1.0)
    b.lk((en, "Valor"), cl, "Value")
    b.ch(en, b.setv("VolumeGlobal", src=(cl, "ReturnValue")), registrar(b, None, "HUB", "VOLUME_GLOBAL", b.fs(b.v("VolumeGlobal"))))
    b, en = entrada(bp, "DebugTela", me)
    b.ch(en, b.setv("bDebugTela", src=(en, "Ligar")), registrar(b, None, "HUB", "DEBUG_TELA", b.bs((en, "Ligar"))))
    b, en = entrada(bp, "ImprimirLog", me)
    ln = b.c(ARR + "Array_Length", 0, 0)
    b.lk(b.v("Log"), ln, "TargetArray")
    mx = b.c(KML + "Max", 0, 0, B=0)
    b.lk(b.op("Subtract_IntInt", (ln, "ReturnValue"), 20), mx, "A")
    fl = b.g.pos(b.ge.add_macro_node(MAC + "ForLoop"), 0, 0)
    b.lk((mx, "ReturnValue"), fl, "FirstIndex")
    b.lk(b.op("Subtract_IntInt", (ln, "ReturnValue"), 1), fl, "LastIndex")
    gt = b.c(ARR + "Array_Get", 0, 0)
    b.lk(b.v("Log"), gt, "TargetArray")
    b.lk((fl, "Index"), gt, "Index")
    pr = b.c(KSL + "PrintString", 0, 0, bPrintToScreen="true", bPrintToLog="true", Duration=20.0)
    b.lk((gt, "Item"), pr, "InString")
    b.ch(en, fl)
    b.ch((fl, "LoopBody"), pr)
    b, en = entrada(bp, "Resetar", me)
    b.ch(en, b.setv("Geracao", src=b.op("Add_IntInt", b.v("Geracao"), 1)), b.setv("ContBarulhos", 0), b.setv("ContSustos", 0),
         b.setv("BloqueioAteT", -1000.0), b.setv("SustoPendenteAteT", -1000.0), b.setv("bMarcaPendente", "false"),
         b.setv("UltimoEventoT", -1000.0), registrar(b, None, "HUB", "RESET", b.is_(b.v("Geracao"))))

    # stubs
    ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
    ge.remove_nodes(list(ge.list_all_nodes()))
    g = G(ge)
    bpl = g.pos(BEL.add_event_override(bp, "ReceiveBeginPlay", unreal.IntPoint(0, 0)), 0, 0)
    g.chain(bpl, g.call(me + ":Inicializar", 300, 0))
    enp = g.pos(BEL.add_event_override(bp, "ReceiveEndPlay", unreal.IntPoint(0, 300)), 0, 300)
    g.chain(enp, g.call(me + ":Finalizar", 300, 300))
    g.note("LUX_EVT v%d (Tools/Loop/add_loop_events.py). Console: ke * LigarSustos | DesligarSustos | LigarBarulhos | "
           "DesligarBarulhos | LigarTudo | DesligarTudo | DefinirSemente N | DefinirVolumeGlobal 0.5 | DebugTela 1 | ImprimirLog | Resetar"
           % VERSAO, -40, -200, 1200, 700)


# ------------------------------------------------------------------ grafo do evento
def build_evento(bp):
    me = EVT_C
    H = lambda b: b.v("Hub")

    def hubv(b, nome):
        v = b.v(nome, cls=HUB_C)
        b.lk(H(b), v[0], "self")
        return v

    def hcall(b, fn, **vals):
        return b.call(fn, alvo=H(b), cls=HUB_C, **vals)

    def reg(b, acao, det):
        return registrar(b, H(b), b.v("Id"), acao, det)

    # Aplica(L)
    b, en = entrada(bp, "Aplica", me)
    ln = b.c(ARR + "Array_Length", 0, 0)
    b.lk(b.v("Loops"), ln, "TargetArray")
    ok = b.ou(b.contem(b.v("Loops"), (en, "L")),
              b.e(b.e(b.op("EqualEqual_IntInt", (ln, "ReturnValue"), 0), b.op("Greater_IntInt", b.v("LoopMinimo"), 0)),
                  b.op("GreaterEqual_IntInt", (en, "L"), b.v("LoopMinimo"))))
    b.ch(en, b.setv("UltAplica", src=ok))

    # camera
    def cam(b):
        pcm = (b.c(GS + "GetPlayerCameraManager", 0, 0, PlayerIndex=0), "ReturnValue")
        loc = b.c("/Script/Engine.PlayerCameraManager:GetCameraLocation", 0, 0)
        b.lk(pcm, loc, "self")
        rot = b.c("/Script/Engine.PlayerCameraManager:GetCameraRotation", 0, 0)
        b.lk(pcm, rot, "self")
        fw = b.c(KML + "GetForwardVector", 0, 0)
        b.lk((rot, "ReturnValue"), fw, "InRot")
        return (loc, "ReturnValue"), (fw, "ReturnValue")

    def ponto_som(b):
        n = b.c("/Script/Engine.SceneComponent:K2_GetComponentLocation", 0, 0)
        b.lk(b.v("PontoSom"), n, "self")
        return (n, "ReturnValue")

    # Olhando -> UltOlhando
    b, en = entrada(bp, "Olhando", me)
    C, Fw = cam(b)
    bo = b.c(KSL + "GetComponentBounds", 0, 0)
    b.lk(b.v("Aparicao"), bo, "Component")
    sel = b.c(KML + "SelectVector", 0, 0)
    b.lk((bo, "Origin"), sel, "A")
    b.lk(ponto_som(b), sel, "B")
    b.lk(b.v("bAparicao"), sel, "bPickA")
    A = (sel, "ReturnValue")
    d = b.op("Subtract_VectorVector", A, C)
    nrm = b.c(KML + "Normal", 0, 0)
    b.lk(d, nrm, "A")
    dot = b.op("Dot_VectorVector", Fw, (nrm, "ReturnValue"))
    t1 = b.op("GreaterEqual_DoubleDouble", dot, b.v("CosOlhar"))
    vl = b.c(KML + "VSize", 0, 0)
    b.lk(d, vl, "A")
    t2 = b.ou(b.nao(b.v("bAparicao")), b.op("GreaterEqual_DoubleDouble", (vl, "ReturnValue"), b.v("AparicaoDistMin")))
    pawn = (b.c(GS + "GetPlayerPawn", 0, 0, PlayerIndex=0), "ReturnValue")
    att = b.c("/Script/Engine.Actor:GetAttachedActors", 0, 0)
    b.lk(pawn, att, "self")
    ign = b.c(ARR + "Array_Add", 0, 0)
    b.lk((att, "OutActors"), ign, "TargetArray")
    b.lk(pawn, ign, "NewItem")
    lt = b.c(KSL + "LineTraceSingle", 0, 0, TraceChannel="TraceTypeQuery1", bTraceComplex="false", bIgnoreSelf="true")
    b.lk(b.op("Add_VectorVector", C, b.op("Multiply_VectorFloat", (nrm, "ReturnValue"), 50.0)), lt, "Start")
    b.lk(A, lt, "End")
    b.lk((att, "OutActors"), lt, "ActorsToIgnore")
    t3 = b.ou(b.nao(b.v("bExigirLinhaVisao")), b.nao((lt, "ReturnValue")))
    s = b.setv("UltOlhando", src=b.e(b.e(t1, t2), t3))
    b.ch(en, ign, lt, s)  # GetAttachedActors e puro

    # DeCostas -> UltCostas
    b, en = entrada(bp, "DeCostas", me)
    C, Fw = cam(b)
    nrm = b.c(KML + "Normal", 0, 0)
    b.lk(b.op("Subtract_VectorVector", ponto_som(b), C), nrm, "A")
    s = b.setv("UltCostas", src=b.op("LessEqual_DoubleDouble", b.op("Dot_VectorVector", Fw, (nrm, "ReturnValue")), b.v("CosCostas")))
    b.ch(en, s)

    # Inicializar (BeginPlay)
    b, en = entrada(bp, "Inicializar", me)
    fh = b.c(GS + "GetActorOfClass", 0, 0, ActorClass="/Script/Engine.BlueprintGeneratedClass'%s'" % HUB_C)
    sh = b.setv("Hub", src=(fh, "ReturnValue"))
    bh = b.br(b.valido(b.v("Hub")))
    pr = b.c(KSL + "PrintString", 0, 0, InString="sem EVENTS_Hub", bPrintToScreen="true", bPrintToLog="true")
    sa = b.setv("bAtivo", "false")
    sg = b.setv("GeracaoVista", src=hubv(b, "Geracao"))
    hid = b.c("/Script/Engine.SceneComponent:SetHiddenInGame", 0, 0, NewHidden="true")
    b.lk(b.v("Aparicao"), hid, "self")
    bt = b.br(b.op("NotEqual_NameName", b.v("TagLuzes"), "None"))
    ga = b.c(GS + "GetAllActorsWithTag", 0, 0)
    b.lk(b.v("TagLuzes"), ga, "Tag")
    fe = b.g.pos(b.ge.add_macro_node(MAC + "ForEachLoop"), 0, 0)
    b.lk((ga, "OutActors"), fe, "Array")
    gc = b.c("/Script/Engine.Actor:GetComponentByClass", 0, 0, ComponentClass="/Script/CoreUObject.Class'/Script/Engine.LightComponent'")
    b.lk((fe, "Array Element"), gc, "self")
    bl = b.br(b.valido((gc, "ReturnValue")))
    a1 = b.c(ARR + "Array_Add", 0, 0)
    b.lk(b.v("Luzes"), a1, "TargetArray")
    b.lk((gc, "ReturnValue"), a1, "NewItem")
    inten = b.v("Intensity", cls="/Script/Engine.LightComponentBase")
    b.lk((gc, "ReturnValue"), inten[0], "self")
    a2 = b.c(ARR + "Array_Add", 0, 0)
    b.lk(b.v("IntensOrig"), a2, "TargetArray")
    b.lk(inten, a2, "NewItem")
    j = junc(b)
    bg = b.br(b.valido(b.v("AlvoGirar")))
    gr = b.c("/Script/Engine.Actor:K2_GetActorRotation", 0, 0)
    b.lk(b.v("AlvoGirar"), gr, "self")
    sr = b.setv("RotOrig", src=(gr, "ReturnValue"))
    b.ch(en, fh, sh, bh)
    b.ch((bh, "else"), pr, sa)
    b.ch((bh, "then"), sg, hid, bt)
    b.ch((bt, "then"), ga, fe)
    b.ch((fe, "LoopBody"), bl)
    b.ch((bl, "then"), a1, a2)
    b.ch((fe, "Completed"), j)
    b.ch((bt, "else"), j)
    b.ch((j, "then"), bg)
    b.ch((bg, "then"), sr)

    # Repetir(M)
    b, en = entrada(bp, "Repetir", me)
    M = (en, "M")
    s_est = b.setv("Estado", src=M)
    s_le = b.setv("LoopEstado", src=hubv(b, "LoopCache"))
    b1 = b.br(b.contem(b.v("MotivosEspera"), M))
    stt = b.setv("TentT", src=b.now())
    j1 = junc(b)
    b2 = b.br(b.e(b.op("EqualEqual_IntInt", b.v("Categoria"), 1), b.contem(b.v("MotivosReserva"), M)))
    rs = hcall(b, "ReservarSusto")
    j2 = junc(b)
    dentro = b.ou(b.nao(b.v("bExigirDentro")), b.v("bDentro"))
    b3 = b.br(b.e(b.op("LessEqual_DoubleDouble", b.menos_agora("TentT"), b.v("JanelaS")), dentro))
    tm = b.timer("TentarDisparar", 0.25)
    b4 = b.br(b.v("bSkipLogado"))
    ssk = b.setv("bSkipLogado", "true")
    sld = b.setv("LoopDisp", src=b.v("LoopTent"))
    b5 = b.br(hubv(b, "bLogBloqueios"))
    r = reg(b, "SKIP", M)
    b.ch(en, s_est, s_le, b1)
    b.ch((b1, "then"), stt, j1)
    b.ch((b1, "else"), j1)
    b.ch((j1, "then"), b2)
    b.ch((b2, "then"), rs, j2)
    b.ch((b2, "else"), j2)
    b.ch((j2, "then"), b3)
    b.ch((b3, "then"), tm)
    b.ch((b3, "else"), b4)
    b.ch((b4, "else"), ssk, sld, b5)
    b.ch((b5, "then"), r)

    # TentarDisparar
    b, en = entrada(bp, "TentarDisparar", me)
    b0 = b.br(b.e(b.v("bAtivo"), b.valido(b.v("Hub"))))
    vg = hcall(b, "VigiarLoop")
    bger = b.br(b.op("NotEqual_IntInt", hubv(b, "Geracao"), b.v("GeracaoVista")))
    rg = [b.setv("GeracaoVista", src=hubv(b, "Geracao")), b.setv("LoopDisp", -1), b.setv("LoopRolado", -1), b.setv("LoopTent", -1),
          b.setv("bDisparouSessao", "false"), b.setv("bSkipLogado", "false")]
    jg = junc(b)
    L = hubv(b, "LoopCache")
    ap = b.call("Aplica")
    b.lk(L, ap, "L")
    bap = b.br(b.v("UltAplica"))
    marc_retry = b.br(b.e(b.e(b.op("EqualEqual_IntInt", b.v("Categoria"), 2), b.v("bDentro")),
                          b.op("Less_DoubleDouble", b.menos_agora("EntradaT"), 3.0)))
    tmr = b.timer("TentarDisparar", 0.25)
    ja = b.br(b.ou(b.op("EqualEqual_IntInt", b.v("LoopDisp"), L), b.e(b.v("bUmaVezPorSessao"), b.v("bDisparouSessao"))))
    bt = b.br(b.op("NotEqual_IntInt", b.v("LoopTent"), L))
    nt = [b.setv("LoopTent", src=L), b.setv("TentT", src=b.now()), b.setv("bSkipLogado", "false"), b.setv("bVisto", "false")]
    jt = junc(b)
    bmk = b.br(b.op("EqualEqual_IntInt", b.v("Categoria"), 2))
    blq = hcall(b, "Bloquear")
    b.lk(b.v("BloqueioS"), blq, "S")
    rmk = reg(b, "MARCA", b.s(["bloqueio=", b.fs(b.v("BloqueioS"))]))
    sld = b.setv("LoopDisp", src=L)
    slem = b.setv("Estado", "MARCA")
    sleml = b.setv("LoopEstado", src=L)
    brol = b.br(b.op("NotEqual_IntInt", b.v("LoopRolado"), L))
    slr = b.setv("LoopRolado", src=L)
    rol = hcall(b, "Rolar")
    b.lk(b.v("IdNum"), rol, "N")
    bprob = b.br(b.op("Greater_DoubleDouble", hubv(b, "UltRolo"), b.v("Probabilidade")))
    sldp = b.setv("LoopDisp", src=L)
    rsk = reg(b, "SKIP", "prob")
    sprob = b.setv("Estado", "prob")
    jr = junc(b)
    bvis = b.br(b.v("bExigirVistoAntes"))
    olh = b.call("Olhando")
    bol = b.br(b.v("UltOlhando"))
    svis = b.setv("bVisto", "true")
    jv = junc(b)
    # checagens em ordem -> Repetir(M)
    pawnloc = b.c("/Script/Engine.Actor:K2_GetActorLocation", 0, 0)
    b.lk((b.c(GS + "GetPlayerPawn", 0, 0, PlayerIndex=0), "ReturnValue"), pawnloc, "self")
    dist = b.c(KML + "Vector_Distance", 0, 0)
    b.lk((pawnloc, "ReturnValue"), dist, "V1")
    b.lk((lambda n: (b.lk(b.v("PontoSom"), n, "self"), (n, "ReturnValue"))[1])(b.c("/Script/Engine.SceneComponent:K2_GetComponentLocation", 0, 0)), dist, "V2")
    c_dist = b.br(b.e(b.op("Greater_DoubleDouble", b.v("DistMaxJogador"), 0.0), b.op("Greater_DoubleDouble", (dist, "ReturnValue"), b.v("DistMaxJogador"))))
    rep_dist = b.call("Repetir", M="dist")
    pd = hcall(b, "PodeDisparar")
    b.lk(b.v("Categoria"), pd, "Cat")
    c_pd = b.br(b.nao(hubv(b, "UltOk")))
    rep_pd = b.call("Repetir")
    b.lk(hubv(b, "UltMotivo"), rep_pd, "M")
    c_ol = b.br(b.v("bSoQuandoOlhando"))
    olh2 = b.call("Olhando")
    c_ol2 = b.br(b.v("UltOlhando"))
    rep_ol = b.call("Repetir", M="vista")
    jo = junc(b)
    c_vi = b.br(b.e(b.v("bExigirVistoAntes"), b.nao(b.v("bVisto"))))
    rep_vi = b.call("Repetir", M="nao_visto")
    c_co = b.br(b.v("bSoQuandoDeCostas"))
    cos = b.call("DeCostas")
    c_co2 = b.br(b.v("UltCostas"))
    rep_co = b.call("Repetir", M="costas")
    jc = junc(b)
    # dispara
    sd1 = b.setv("LoopDisp", src=L)
    sd2 = b.setv("bDisparouSessao", "true")
    vol = hcall(b, "Volumes")
    b.lk(b.v("Volume"), vol, "V")
    relsel = b.c(KML + "SelectFloat", 0, 0, B=0.0)
    b.lk(b.v("RelCamada"), relsel, "A")
    b.lk(b.valido(b.v("SomCamada")), relsel, "bPickA")
    b.lk((relsel, "ReturnValue"), vol, "Rel")
    svb = b.setv("VB", src=hubv(b, "UltVB"))
    svc = b.setv("VC", src=hubv(b, "UltVC"))
    det = b.s(["cat=", b.is_(b.v("Categoria")), " dist=", b.fs((dist, "ReturnValue")), " VB=", b.fs(b.v("VB")), " VC=", b.fs(b.v("VC"))])
    bsup = b.br(hubv(b, "UltSuprimir"))
    nsup = hcall(b, "Notificar", Acao="SUPRIMIDO")
    b.lk(b.v("Categoria"), nsup, "Cat")
    b.lk(b.v("Id"), nsup, "IdEv")
    b.lk(det, nsup, "Det")
    nfir = hcall(b, "Notificar", Acao="FIRED")
    b.lk(b.v("Categoria"), nfir, "Cat")
    b.lk(b.v("Id"), nfir, "IdEv")
    b.lk(det, nfir, "Det")
    sfe = b.setv("Estado", "FIRED")
    sfl = b.setv("LoopEstado", src=L)
    bat = b.br(b.op("Greater_DoubleDouble", b.v("AtrasoS"), 0.0))
    tex = b.timer("Executar", b.v("AtrasoS"))
    ex = b.call("Executar")
    b.ch(en, b0)
    b.ch((b0, "then"), vg, bger)
    b.ch((bger, "then"), *rg)
    b.ch(rg[-1], jg)
    b.ch((bger, "else"), jg)
    b.ch((jg, "then"), ap, bap)
    b.ch((bap, "else"), marc_retry)
    b.ch((marc_retry, "then"), tmr)
    b.ch((bap, "then"), ja)
    b.ch((ja, "else"), bt)
    b.ch((bt, "then"), *nt)
    b.ch(nt[-1], jt)
    b.ch((bt, "else"), jt)
    b.ch((jt, "then"), bmk)
    b.ch((bmk, "then"), blq, rmk, sld, slem, sleml)
    b.ch((bmk, "else"), brol)
    b.ch((brol, "then"), slr, rol, bprob)
    b.ch((bprob, "then"), sldp, sprob, rsk)
    b.ch((bprob, "else"), jr)
    b.ch((brol, "else"), jr)
    b.ch((jr, "then"), bvis)
    b.ch((bvis, "then"), olh, bol)
    b.ch((bol, "then"), svis, jv)
    b.ch((bol, "else"), jv)
    b.ch((bvis, "else"), jv)
    b.ch((jv, "then"), c_dist)  # K2_GetActorLocation e puro
    b.ch((c_dist, "then"), rep_dist)
    b.ch((c_dist, "else"), pd, c_pd)
    b.ch((c_pd, "then"), rep_pd)
    b.ch((c_pd, "else"), c_ol)
    b.ch((c_ol, "then"), olh2, c_ol2)
    b.ch((c_ol2, "else"), rep_ol)
    b.ch((c_ol2, "then"), jo)
    b.ch((c_ol, "else"), jo)
    b.ch((jo, "then"), c_vi)
    b.ch((c_vi, "then"), rep_vi)
    b.ch((c_vi, "else"), c_co)
    b.ch((c_co, "then"), cos, c_co2)
    b.ch((c_co2, "else"), rep_co)
    b.ch((c_co2, "then"), jc)
    b.ch((c_co, "else"), jc)
    b.ch((jc, "then"), sd1, sd2, vol, svb, svc, bsup)
    b.ch((bsup, "then"), nsup)
    b.ch((bsup, "else"), nfir, sfe, sfl, bat)
    b.ch((bat, "then"), tex)
    b.ch((bat, "else"), ex)

    # Executar
    b, en = entrada(bp, "Executar", me)
    s1 = b.setv("LoopDoDisparo", src=hubv(b, "LoopCache"))
    s2 = b.setv("DisparoT", src=b.now())
    mi = hcall(b, "MarcarInicio")
    b.lk(b.v("Id"), mi, "IdEv")
    bs_ = b.br(b.e(b.valido(b.v("Som")), b.nao(b.v("bSomNoFimDoPiscar"))))
    r0 = b.setv("Rep", 0)
    tr = b.call("TocarRepeticao")
    j1 = junc(b)
    lnl = b.c(ARR + "Array_Length", 0, 0)
    b.lk(b.v("Luzes"), lnl, "TargetArray")
    bl = b.br(b.op("Greater_IntInt", (lnl, "ReturnValue"), 0))
    p0 = b.setv("Passo", 0)
    pp = b.call("PassoPiscar")
    j2 = junc(b)
    btr = b.br(b.op("Greater_DoubleDouble", b.v("EscalaTremor"), 0.0))
    pc = (b.c(GS + "GetPlayerController", 0, 0, PlayerIndex=0), "ReturnValue")
    sh = b.c("/Script/Engine.PlayerController:ClientStartCameraShake", 0, 0)
    b.lk(pc, sh, "self")
    b.lk(b.v("ClasseTremor"), sh, "Shake")
    esc = b.c(KML + "FMin", 0, 0)
    b.lk(b.v("EscalaTremor"), esc, "A")
    b.lk(hubv(b, "EscalaTremorMax"), esc, "B")
    b.lk((esc, "ReturnValue"), sh, "Scale")
    j3 = junc(b)
    bap_ = b.br(b.v("bAparicao"))
    most = b.c("/Script/Engine.SceneComponent:SetHiddenInGame", 0, 0, NewHidden="false")
    b.lk(b.v("Aparicao"), most, "self")
    tesc = b.timer("EsconderAparicao", b.v("AparicaoS"))
    j4 = junc(b)
    bgi = b.br(b.valido(b.v("AlvoGirar")))
    mk = b.c(KML + "MakeRotator", 0, 0, Roll=0.0, Pitch=0.0)
    b.lk(b.v("GiroYaw"), mk, "Yaw")
    gir = b.c("/Script/Engine.Actor:K2_AddActorWorldRotation", 0, 0, bSweep="false", bTeleport="true")
    b.lk(b.v("AlvoGirar"), gir, "self")
    b.lk((mk, "ReturnValue"), gir, "DeltaRotation")
    tvt = b.timer("VigiarTroca", 0.5, loop=True)
    j5 = junc(b)
    bvi = b.br(b.v("bExigirVistoAntes"))
    tvv = b.timer("VigiarVisto", 0.25, loop=True)
    b.ch(en, s1, s2, mi, bs_)
    b.ch((bs_, "then"), r0, tr, j1)
    b.ch((bs_, "else"), j1)
    b.ch((j1, "then"), bl)
    b.ch((bl, "then"), p0, pp, j2)
    b.ch((bl, "else"), j2)
    b.ch((j2, "then"), btr)
    b.ch((btr, "then"), sh, j3)
    b.ch((btr, "else"), j3)
    b.ch((j3, "then"), bap_)
    b.ch((bap_, "then"), most, tesc, j4)
    b.ch((bap_, "else"), j4)
    b.ch((j4, "then"), bgi)
    b.ch((bgi, "then"), gir, tvt, j5)
    b.ch((bgi, "else"), j5)
    b.ch((j5, "then"), bvi)
    b.ch((bvi, "then"), tvv)

    # TocarRepeticao
    b, en = entrada(bp, "TocarRepeticao", me)
    b0 = b.br(b.op("EqualEqual_IntInt", b.v("Rep"), 0))
    fos = []
    for var in ("SomAtual", "SomCamadaAtual"):
        bb = b.br(b.valido(b.v(var)))
        fo = b.c("/Script/Engine.AudioComponent:FadeOut", 0, 0, FadeOutDuration=0.1, FadeVolumeLevel=0.0)
        b.lk(b.v(var), fo, "self")
        b.ch((bb, "then"), fo)
        fos.append((bb, fo))
    jf = junc(b)
    b.ch(fos[0][1], fos[1][0])
    b.ch((fos[0][0], "else"), fos[1][0])
    b.ch(fos[1][1], jf)
    b.ch((fos[1][0], "else"), jf)
    rpd = b.c(KML + "Conv_IntToDouble", 0, 0)
    b.lk(b.v("Rep"), rpd, "InInt")
    desl = b.op("Multiply_VectorFloat", b.v("DeslocPorRep"), (rpd, "ReturnValue"))
    tdir = b.c(KML + "TransformDirection", 0, 0)
    b.lk((lambda n: (n, "ReturnValue"))(b.c("/Script/Engine.Actor:GetTransform", 0, 0)), tdir, "T")
    b.lk(desl, tdir, "Direction")
    loc = b.op("Add_VectorVector", (lambda n: (b.lk(b.v("PontoSom"), n, "self"), (n, "ReturnValue"))[1])(b.c("/Script/Engine.SceneComponent:K2_GetComponentLocation", 0, 0)), (tdir, "ReturnValue"))
    rol = hcall(b, "Rolar")
    b.lk(b.op("Add_IntInt", b.v("IdNum"), b.op("Multiply_IntInt", b.v("Rep"), 7)), rol, "N")
    jit = b.op("Add_DoubleDouble", b.op("Multiply_DoubleDouble", hubv(b, "UltRolo"), 0.1), 0.95)
    sp = b.c(GS + "SpawnSoundAtLocation", 0, 0)
    b.lk(b.v("Som"), sp, "Sound")
    b.lk(loc, sp, "Location")
    b.lk(b.v("VB"), sp, "VolumeMultiplier")
    b.lk(b.op("Multiply_DoubleDouble", b.v("Pitch"), jit), sp, "PitchMultiplier")
    b.lk(b.v("InicioS"), sp, "StartTime")
    b.lk(b.v("Atenuacao"), sp, "AttenuationSettings")
    ssa = b.setv("SomAtual", src=(sp, "ReturnValue"))
    bc = b.br(b.e(b.op("EqualEqual_IntInt", b.v("Rep"), 0), b.valido(b.v("SomCamada"))))
    sp2 = b.c(GS + "SpawnSoundAtLocation", 0, 0)
    b.lk(b.v("SomCamada"), sp2, "Sound")
    b.lk(loc, sp2, "Location")
    b.lk(b.v("VC"), sp2, "VolumeMultiplier")
    b.lk(b.v("PitchCamada"), sp2, "PitchMultiplier")
    b.lk(b.v("Atenuacao"), sp2, "AttenuationSettings")
    ssc = b.setv("SomCamadaAtual", src=(sp2, "ReturnValue"))
    jc = junc(b)
    inc = b.setv("Rep", src=b.op("Add_IntInt", b.v("Rep"), 1))
    bmais = b.br(b.op("Less_IntInt", b.v("Rep"), b.v("Repeticoes")))
    t1 = b.timer("TocarRepeticao", b.v("IntervaloRepS"))
    t2 = b.timer("CortarSom", b.v("DuracaoMaxS"))
    b.ch(en, b0)
    b.ch((b0, "then"), fos[0][0])
    b.ch((b0, "else"), jf)
    b.ch((jf, "then"), rol, sp, ssa, bc)
    b.ch((bc, "then"), sp2, ssc, jc)
    b.ch((bc, "else"), jc)
    b.ch((jc, "then"), inc, bmais)
    b.ch((bmais, "then"), t1)
    b.ch((bmais, "else"), t2)

    # CortarSom
    b, en = entrada(bp, "CortarSom", me)
    prev = (en, "then")
    for var in ("SomAtual", "SomCamadaAtual"):
        bb = b.br(b.valido(b.v(var)))
        fo = b.c("/Script/Engine.AudioComponent:FadeOut", 0, 0, FadeVolumeLevel=0.0)
        b.lk(b.v(var), fo, "self")
        b.lk(b.v("FadeS"), fo, "FadeOutDuration")
        jj = junc(b)
        b.g.link(prev[0], prev[1], bb, "execute")
        b.ch((bb, "then"), fo, jj)
        b.ch((bb, "else"), jj)
        prev = (jj, "then")

    # RestaurarLuzes / EsconderAparicao
    b, en = entrada(bp, "RestaurarLuzes", me)
    fe = b.g.pos(b.ge.add_macro_node(MAC + "ForEachLoop"), 0, 0)
    b.lk(b.v("Luzes"), fe, "Array")
    gi = b.c(ARR + "Array_Get", 0, 0)
    b.lk(b.v("IntensOrig"), gi, "TargetArray")
    b.lk((fe, "Array Index"), gi, "Index")
    si = b.c("/Script/Engine.LightComponent:SetIntensity", 0, 0)
    b.lk((fe, "Array Element"), si, "self")
    b.lk((gi, "Item"), si, "NewIntensity")
    b.ch(en, fe)
    b.ch((fe, "LoopBody"), si)
    b, en = entrada(bp, "EsconderAparicao", me)
    hid = b.c("/Script/Engine.SceneComponent:SetHiddenInGame", 0, 0, NewHidden="true")
    b.lk(b.v("Aparicao"), hid, "self")
    b.ch(en, hid)

    def loop_mudou(b):
        return b.op("NotEqual_IntInt", hubv(b, "LoopCache"), b.v("LoopDoDisparo"))

    def aplica_fator(b, fator):
        fe = b.g.pos(b.ge.add_macro_node(MAC + "ForEachLoop"), 0, 0)
        b.lk(b.v("Luzes"), fe, "Array")
        gi = b.c(ARR + "Array_Get", 0, 0)
        b.lk(b.v("IntensOrig"), gi, "TargetArray")
        b.lk((fe, "Array Index"), gi, "Index")
        si = b.c("/Script/Engine.LightComponent:SetIntensity", 0, 0)
        b.lk((fe, "Array Element"), si, "self")
        b.lk(b.op("Multiply_DoubleDouble", (gi, "Item"), fator), si, "NewIntensity")
        b.ch((fe, "LoopBody"), si)
        return fe

    # PassoPiscar
    b, en = entrada(bp, "PassoPiscar", me)
    bm = b.br(loop_mudou(b))
    rl = b.call("RestaurarLuzes")
    lnp = b.c(ARR + "Array_Length", 0, 0)
    b.lk(b.v("PadraoPiscar"), lnp, "TargetArray")
    nmax = b.c(KML + "Min", 0, 0, B=8)
    b.lk((lnp, "ReturnValue"), nmax, "A")
    bfim = b.br(b.op("GreaterEqual_IntInt", b.v("Passo"), (nmax, "ReturnValue")))
    fim = b.call("FimPiscar")
    par = b.op("EqualEqual_IntInt", b.op("Percent_IntInt", b.v("Passo"), 2), 0)
    fsel = b.c(KML + "SelectFloat", 0, 0, B=1.0)
    b.lk(b.v("IntensidadeApagada"), fsel, "A")
    b.lk(par, fsel, "bPickA")
    fe = aplica_fator(b, (fsel, "ReturnValue"))
    gp = b.c(ARR + "Array_Get", 0, 0)
    b.lk(b.v("PadraoPiscar"), gp, "TargetArray")
    b.lk(b.v("Passo"), gp, "Index")
    mx = b.c(KML + "FMax", 0, 0, B=0.25)
    b.lk((gp, "Item"), mx, "A")
    tp = b.timer("PassoPiscar", (mx, "ReturnValue"))
    inc = b.setv("Passo", src=b.op("Add_IntInt", b.v("Passo"), 1))
    b.ch(en, bm)
    b.ch((bm, "then"), rl)
    b.ch((bm, "else"), bfim)
    b.ch((bfim, "then"), fim)
    b.ch((bfim, "else"), fe)
    b.ch((fe, "Completed"), tp, inc)

    # FimPiscar
    b, en = entrada(bp, "FimPiscar", me)
    bm = b.br(loop_mudou(b))
    rl = b.call("RestaurarLuzes")
    fsel = b.c(KML + "SelectFloat", 0, 0, A=0.0, B=1.0)
    b.lk(b.v("bApagarNoFim"), fsel, "bPickA")
    fe = aplica_fator(b, (fsel, "ReturnValue"))
    bso = b.br(b.e(b.v("bSomNoFimDoPiscar"), b.valido(b.v("Som"))))
    r0 = b.setv("Rep", 0)
    tr = b.call("TocarRepeticao")
    mi = hcall(b, "MarcarInicio")
    b.lk(b.s([b.v("Id"), ":sting"]), mi, "IdEv")
    j = junc(b)
    bap_ = b.br(b.v("bApagarNoFim"))
    brs = b.br(b.op("Greater_DoubleDouble", b.v("RestaurarAposS"), 0.0))
    tr1 = b.timer("RestaurarLuzes", b.v("RestaurarAposS"))
    tr2 = b.timer("VigiarTroca", 0.5, loop=True)
    b.ch(en, bm)
    b.ch((bm, "then"), rl)
    b.ch((bm, "else"), fe)
    b.ch((fe, "Completed"), bso)
    b.ch((bso, "then"), r0, tr, mi, j)
    b.ch((bso, "else"), j)
    b.ch((j, "then"), bap_)
    b.ch((bap_, "then"), brs)
    b.ch((brs, "then"), tr1)
    b.ch((brs, "else"), tr2)

    # VigiarTroca
    b, en = entrada(bp, "VigiarTroca", me)
    bm = b.br(loop_mudou(b))
    rl = b.call("RestaurarLuzes")
    bg = b.br(b.valido(b.v("AlvoGirar")))
    sr = b.c("/Script/Engine.Actor:K2_SetActorRotation", 0, 0, bTeleportPhysics="true")
    b.lk(b.v("AlvoGirar"), sr, "self")
    b.lk(b.v("RotOrig"), sr, "NewRotation")
    j = junc(b)
    cl = b.clear("VigiarTroca")
    b.ch(en, bm)
    b.ch((bm, "then"), rl, bg)
    b.ch((bg, "then"), sr, j)
    b.ch((bg, "else"), j)
    b.ch((j, "then"), cl)

    # VigiarVisto
    b, en = entrada(bp, "VigiarVisto", me)
    ol = b.call("Olhando")
    bo = b.br(b.v("UltOlhando"))
    rv = reg(b, "VISTO", b.s(["t=", b.fs(b.menos_agora("DisparoT"))]))
    c1 = b.clear("VigiarVisto")
    bm = b.br(loop_mudou(b))
    rn = reg(b, "NAO_VISTO", "")
    c2 = b.clear("VigiarVisto")
    b.ch(en, ol, bo)
    b.ch((bo, "then"), rv, c1)
    b.ch((bo, "else"), bm)
    b.ch((bm, "then"), rn, c2)

    # ForcarSe(IdAlvo)
    b, en = entrada(bp, "ForcarSe", me)
    eq = b.c(KSL + "EqualEqual_StrStr", 0, 0) if False else b.c(STR + "EqualEqual_StrStr", 0, 0)
    b.lk((en, "IdAlvo"), eq, "A")
    b.lk(b.v("Id"), eq, "B")
    b0 = b.br(b.e((eq, "ReturnValue"), b.valido(b.v("Hub"))))
    vg = hcall(b, "VigiarLoop")
    pd = hcall(b, "PodeDisparar")
    b.lk(b.v("Categoria"), pd, "Cat")
    mot = hubv(b, "UltMotivo")
    recusa = b.ou(b.ou(b.op("EqualEqual_StrStr", mot, "categoria") if False else b.contem(b.v("MotivosEspera"), mot) if False else b.op("EqualEqual_IntInt", b.v("Categoria"), -99), b.nao(hubv(b, "bEventosAtivos"))), b.nao(b.v("bAtivo")))
    # recusa so por: mestre, categoria, troca, distorcao; externo so se luz/tremor
    def eqs(a, lit):
        n = b.c(STR + "EqualEqual_StrStr", 0, 0)
        b.lk(a, n, "A")
        b.g.val(n, "B", lit)
        return (n, "ReturnValue")
    luz_tremor = b.ou(b.op("Greater_IntInt", (lambda n: (b.lk(b.v("Luzes"), n, "TargetArray"), (n, "ReturnValue"))[1])(b.c(ARR + "Array_Length", 0, 0)), 0),
                      b.op("Greater_DoubleDouble", b.v("EscalaTremor"), 0.0))
    rec = b.ou(b.ou(b.ou(eqs(mot, "categoria"), eqs(mot, "troca")), eqs(mot, "distorcao")), b.e(eqs(mot, "externo"), luz_tremor))
    brc = b.br(b.ou(rec, b.nao(hubv(b, "bEventosAtivos"))))
    rk = reg(b, "SKIP", b.s(["forcado:", mot]))
    sld = b.setv("LoopDisp", src=hubv(b, "LoopCache"))
    nf = hcall(b, "Notificar", Acao="FORCADO", Det="")
    b.lk(b.v("Categoria"), nf, "Cat")
    b.lk(b.v("Id"), nf, "IdEv")
    ex = b.call("Executar")
    b.ch(en, b0)
    b.ch((b0, "then"), vg, pd, brc)
    b.ch((brc, "then"), rk)
    b.ch((brc, "else"), sld, nf, ex)

    # EventGraph: BeginPlay + overlaps
    ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
    ge.remove_nodes(list(ge.list_all_nodes()))
    g = G(ge)
    bb = B(ge, me)
    bpl = g.pos(BEL.add_event_override(bp, "ReceiveBeginPlay", unreal.IntPoint(0, 0)), 0, 0)
    g.chain(bpl, g.call(me + ":Inicializar", 300, 0))
    ov = g.pos(BEL.add_event_override(bp, "ReceiveActorBeginOverlap", unreal.IntPoint(0, 300)), 0, 300)
    eq = bb.c(KML + "EqualEqual_ObjectObject", 0, 0)
    g.link(ov, "OtherActor", eq, "A")
    bb.lk((bb.c(GS + "GetPlayerPawn", 0, 0, PlayerIndex=0), "ReturnValue"), eq, "B")
    b1 = bb.br((eq, "ReturnValue"))
    s1 = bb.setv("bDentro", "true")
    s2 = bb.setv("EntradaT", src=bb.now())
    td = g.call(me + ":TentarDisparar", 900, 300)
    g.chain(ov, b1)
    g.chain((b1, "then"), s1, s2, td)
    eo = g.pos(BEL.add_event_override(bp, "ReceiveActorEndOverlap", unreal.IntPoint(0, 700)), 0, 700)
    eq2 = bb.c(KML + "EqualEqual_ObjectObject", 0, 0)
    g.link(eo, "OtherActor", eq2, "A")
    bb.lk((bb.c(GS + "GetPlayerPawn", 0, 0, PlayerIndex=0), "ReturnValue"), eq2, "B")
    b2 = bb.br((eq2, "ReturnValue"))
    g.chain(eo, b2)
    g.chain((b2, "then"), bb.setv("bDentro", "false"))
    g.note("LUX_EVT v%d (Tools/Loop/add_loop_events.py). Evento por loop: caixa Gatilho -> TentarDisparar (regras no EVENTS_Hub). "
           "Console: ke * ForcarSe <Id>" % VERSAO, -40, -200, 1200, 1100)


# ------------------------------------------------------------------ criacao dos BPs
def add_comp(bp, cls, nome, parent=None):
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    hs = sds.k2_gather_subobject_data_for_blueprint(bp)
    ph = parent or hs[0]
    h, _ = sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=ph, new_class=cls, blueprint_context=bp))
    sds.rename_subobject(h, unreal.Text(nome))
    return h, lib.get_object_for_blueprint(lib.get_data(h), bp)


def comp_template(bp, nome):
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        o = lib.get_object_for_blueprint(lib.get_data(h), bp)
        if o and o.get_name().replace("_GEN_VARIABLE", "") == nome:
            return o
    return None


def ensure_bps():
    """Cria BP_LuxEventHub e BP_LuxLoopEvent se faltarem. v1 integro -> pula; incompleto -> Aborta."""
    existem = [EAL.does_asset_exist(p) for p in (HUB, EVT)]
    if all(existem):
        hub, evt = EAL.load_asset(HUB), EAL.load_asset(EVT)
        for bp in (hub, evt):
            if unreal.get_default_object(bp.generated_class()).get_editor_property("VersaoSpec") != VERSAO:
                raise Aborta("%s existe sem VersaoSpec=%d (incompleto ou outra versao): feche o editor sem salvar ou rode desfazer" % (bp.get_name(), VERSAO))
        w("BPs v%d ja existem: mantidos" % VERSAO)
        return hub, evt, False
    if any(existem):
        raise Aborta("so um dos BPs existe: estado incompleto (%s)" % existem)
    evt = BEL.create_blueprint_asset_with_parent(EVT, unreal.Actor)
    hub = BEL.create_blueprint_asset_with_parent(HUB, unreal.Actor)
    t = tipos_base()
    t["hub"] = BEL.get_object_reference_type(hub.generated_class())
    t["evt[]"] = BEL.get_array_type(BEL.get_object_reference_type(evt.generated_class()))
    # componentes do evento
    hbox, box = add_comp(evt, unreal.BoxComponent, "Gatilho")
    box.set_editor_property("box_extent", unreal.Vector(150, 150, 110))
    box.set_collision_profile_name("Trigger")
    box.set_editor_property("hidden_in_game", True)
    add_comp(evt, unreal.SceneComponent, "PontoSom")
    _, ap = add_comp(evt, unreal.StaticMeshComponent, "Aparicao")
    ap.set_editor_property("static_mesh", EAL.load_asset("/Engine/BasicShapes/Cylinder"))
    ap.set_collision_profile_name("NoCollision")
    ap.set_editor_property("hidden_in_game", True)
    ap.set_editor_property("cast_shadow", False)
    ap.set_material(0, EAL.load_asset(MI))
    cria_vars(evt, vars_evento(), t, "LUX Evento")
    cria_vars(hub, vars_hub(), t, "LUX Eventos")
    BEL.compile_blueprint(evt)
    BEL.compile_blueprint(hub)
    padroes(evt, [(n, tp, e, p) for n, tp, e, p in vars_evento() if p is not None])
    padroes(hub, [(n, tp, e, p) for n, tp, e, p in vars_hub() if p is not None])
    cria_funcoes(evt, FUNC_EVT, t)
    cria_funcoes(hub, FUNC_HUB, t)
    BEL.compile_blueprint(evt)
    BEL.compile_blueprint(hub)
    build_hub(hub)
    build_evento(evt)
    BEL.compile_blueprint(evt)
    BEL.compile_blueprint(hub)
    BEL.compile_blueprint(evt)
    e = erros_bp(hub) + erros_bp(evt)
    if e:
        raise Aborta("compilacao com erros/avisos (nada salvo): %s" % e)
    estrutural(hub, evt)
    for bp in (hub, evt):
        unreal.get_default_object(bp.generated_class()).set_editor_property("VersaoSpec", VERSAO)
        BEL.compile_blueprint(bp)
    w("BPs criados e compilados limpos")
    return hub, evt, True


def estrutural(hub, evt):
    for bp, lista in ((hub, FUNC_HUB), (evt, FUNC_EVT)):
        g = [str(x) for x in BEL.list_graph_names(bp)]
        for nome, _ in lista:
            if nome not in g:
                raise Aborta("%s sem funcao %s" % (bp.get_name(), nome))
            n = len(list(BGE.get_graph_editor_by_name(bp, nome).list_all_nodes()))
            if n < 2:
                raise Aborta("%s.%s vazia" % (bp.get_name(), nome))
    for nome in ("Gatilho", "PontoSom", "Aparicao"):
        if not comp_template(evt, nome):
            raise Aborta("BP_LuxLoopEvent sem componente %s" % nome)


# ------------------------------------------------------------------ geometria e plano
def geo():
    g = {}
    for lab in ("LOOP_Chegada", "LOOP_PortaSala", "LOOP_Manager", "BP_BaseDoor7", "Sala_Cadeira_Leitura", "LOOPC_L4_Cadeira",
                "LUX_Luz_Corredor_Arandela3", "LUX_Luz_Corredor_Arandela5"):
        a = por_label(lab)
        if not a:
            raise Aborta("ator %s nao encontrado (ou nao unico)" % lab)
        g[lab] = a
    mgr = g["LOOP_Manager"]
    box = [c for c in mgr.get_components_by_class(unreal.BoxComponent) if c.get_name() == "GatilhoFechar"][0]
    gl, ge_ = box.get_world_location(), box.get_editor_property("box_extent")
    g["gatilho"] = (gl, ge_)
    ch = g["LOOP_Chegada"].get_actor_location()
    far = g["LUX_Luz_Corredor_Arandela5"].get_actor_location()
    g["eixo"] = (unreal.Vector(-3275.0, ch.y - 150, 0.0), unreal.Vector(-3275.0, -350.0, 0.0))  # centro do corredor, perto -> longe
    g["meia_largura"] = ge_.x
    return g


def ev(label, idnum, cat, loops, caixa, som_pt, **cfg):
    return {"label": label, "Id": label, "IdNum": idnum, "Categoria": cat, "Loops": loops, "caixa": caixa, "som": som_pt, "cfg": cfg}


def plano(g):
    gl, gx = g["gatilho"]
    mw = g["meia_largura"]
    d7 = g["BP_BaseDoor7"].get_actor_location()
    ps = g["LOOP_PortaSala"].get_actor_location()
    y_gat_min, y_gat_max = gl.y - gx.y, gl.y + gx.y
    marcas = [
        # bloqueio = efeito real + 1 s (27/09): distorcao DuracaoS 13.6; batida 0.12 s fechando + ~1.26 s de impacto
        # (SW_Close_Door a pitch 0.7) + 0.2 s de restauracao
        ev("MARCA_Distorcao", 1, 2, [3, 5], ((gl.x, gl.y, gl.z), (gx.x, gx.y, gx.z)), None, BloqueioS=13.6 + 1.0),
        ev("MARCA_Batida", 2, 2, [4], ((gl.x, gl.y, gl.z), (gx.x, gx.y, gx.z)), None, BloqueioS=0.12 + 1.26 + 0.2 + 1.0)]
    # EV 11: entre a porta do quarto e o gatilho (loop 2 pode ficar a montante)
    # EV 11: entre a porta do quarto e o gatilho. 27/09: o vulto agora dispara mais perto (~6 m), depois do gap; as batidas
    # voltam a vir primeiro (~3 s)
    y0, y1 = y_gat_max + 20.0, d7.y
    bat = ev("EV_Bat_Quarto", 11, 0, [2], ((d7.x, (y0 + y1) / 2, 110.0), (mw, (y1 - y0) / 2, 110.0)), (d7.x, d7.y + 60.0, 110.0),
             Som="HL", Repeticoes=3, IntervaloRepS=0.45, Pitch=0.5, Volume=0.35, JanelaS=20.0, DistMaxJogador=800.0)
    # EV 14: 60% do eixo; som 200 cm atras (rumo ao quarto); de costas
    yl = y_gat_min - 20.0
    far_y = -350.0
    y60 = y_gat_min + 0.6 * (far_y - y_gat_min)
    # 27/09: a memoria (1a metade apos o gatilho) toca primeiro; o gap de 10 s poe o sussurro na entrada da sala,
    # com o som atras do jogador, no fim do corredor
    # 27/09 (etapa 4): caixa menor, termina em y -900 para a caixa da cadeira (susto do loop 4) comecar logo depois
    sus = ev("EV_Sussurro_Corredor", 14, 0, [4], ((-2800.0, -820.0, 110.0), (100.0, 80.0, 110.0)), (-3275.0, -420.0, 110.0),
             Som="PORTAL", Volume=0.3, DuracaoMaxS=3.5, FadeS=1.5, bSoQuandoDeCostas=True, CosCostas=-0.2, JanelaS=20.0, DistMaxJogador=1100.0,
             InicioS=54.5)  # 27/09: o inicio da faixa e fade-in (2 s: rms -34.1/pico -18.5 dBFS); 54.5 s: rms -18.3/pico -3.9
    # EV 15: 1a metade depois do gatilho; som 250 cm dentro do quarto
    ym = (yl + y60 + 80.0 + 20.0) / 2
    mem = ev("EV_Memoria_Quarto", 15, 0, [4], ((-3275.0, (yl + (y60 + 100.0)) / 2, 110.0), (mw, (yl - (y60 + 100.0)) / 2, 110.0)),
             (d7.x, d7.y + 250.0, 110.0), Som="MEMORIES", Volume=0.25, DuracaoMaxS=5.0, FadeS=2.0, JanelaS=25.0, DistMaxJogador=1000.0,
             InicioS=96.5)  # 27/09: 2 s iniciais rms -33.3/pico -14.8; 96.5 s: rms -19.2/pico -4.6, crescendo (-18.1 nos 2 s seguintes)
    # EV 16: LOOP_PortaSala + 300 cm rumo a Sala; som 150 cm atras da porta
    por = ev("EV_Portal_Sala", 16, 0, [5], ((ps.x, ps.y + 300.0, 110.0), (150.0, 100.0, 110.0)), (ps.x, ps.y - 150.0, 110.0),
             Som="MIRAGE", Pitch=0.7, Volume=0.3, DuracaoMaxS=4.0, FadeS=2.0, JanelaS=8.0, DistMaxJogador=900.0,
             InicioS=40.5)  # 27/09: 2 s iniciais rms -48.8/pico -35.5; 40.5 s: rms -17.8/pico -6.2, crescendo (-17.3)
    barulhos = [bat, sus, mem, por]
    if ESCRITORIO_NO_LUGAR_DA_COZINHA:
        esc = escritorio()
        barulhos += [
            ev("EV_Passos_Escritorio", 12, 0, [2], esc["caixa"], esc["dentro"], Som="PASSOS", Repeticoes=5, IntervaloRepS=0.6,
               Pitch=0.75, Volume=0.3, DeslocPorRep=(0.0, 45.0, 0.0), JanelaS=15.0, DistMaxJogador=900.0),
            ev("EV_Rangido_Escritorio", 13, 0, [3], esc["caixa"], esc["porta"], Som="SCD", Pitch=0.6, Volume=0.3, DuracaoMaxS=2.5,
               JanelaS=20.0, DistMaxJogador=1100.0)]
    sustos = []
    if INSTALAR_SUSTOS:
        y_perto, y_longe = g["eixo"][0].y, g["eixo"][1].y
        comprimento = y_perto - y_longe
        dmin = min(600.0, 0.45 * comprimento)
        y_meio = (y_perto + y_longe) / 2
        cad = g["LOOPC_L4_Cadeira"].get_actor_location()
        alvo_yaw = math.degrees(math.atan2(CADEIRA_ALVO[1] - cad.y, CADEIRA_ALVO[0] - cad.x))
        giro = (alvo_yaw - CADEIRA_YAW_BASE + 180.0) % 360.0 - 180.0
        sustos = [
            # vulto (27/09, pedido do Gabriel): a figura preta com aura que CORRE da esquerda para a direita no fim do corredor
            # e o LUX_Vulto_Figura (Tools/Loop/add_vulto_corre.py), que dispara quando este evento dispara. A silhueta
            # estatica sai (bAparicao false, Aparicao invisivel). PontoSom = meio do caminho da corrida, na altura do peito
            # (alvo do "olhando" e dos passos de madeira). Caixa mais perto: o jogador entra a ~7 m e sai a ~5 m do caminho
            ev("EV_Susto_Vulto", 21, 1, [2], ((-3275.0, 40.0, 110.0), (mw, 100.0, 110.0)), (-3215.0, -560.0, 130.0),
               aparicao=(-3250.0, -560.0), bAparicao=False, bSoQuandoOlhando=True, CosOlhar=0.90, bExigirLinhaVisao=True,
               JanelaS=30.0, Som="VULTO_PASSO", Repeticoes=4, IntervaloRepS=0.2, Pitch=1.0, Volume=1.1,
               SomCamada=None, RelCamada=0.0,  # 17:33: passos altos e pesados (o peso esta no proprio SC_LuxVultoPasso)
               DeslocPorRep=(70.0, 0.0, 0.0)),
            # 27/09 17:33: InicioS 51.4 -> o inicio da faixa BROKEN e quase mudo (-31.5 dBFS nos 2.5 s iniciais)
            # piscar: o corredor nao tem outras luzes (arandelas 3/5 ja apagam no loop 3; RectLight5/7 estao em 0) -> candelabros
            # da sala perto da porta (desvio aprovado 27/09). Caixa na entrada da sala: o jogador entra nela ainda durante o
            # bloqueio da distorcao, o susto reserva a vez e dispara quando o bloqueio acaba, antes do rangido
            ev("EV_Susto_Arandelas", 22, 1, [3], ((-2600.0, -1130.0, 110.0), (150.0, 150.0, 110.0)), (-2955.0, -1890.0, 160.0),
               TagLuzes=TAG_LUZES, PadraoPiscar=[0.30, 0.45, 0.25, 0.60, 0.35, 0.40], bApagarNoFim=True, bSomNoFimDoPiscar=True,
               Som="BROKEN", Pitch=1.25, Volume=1.13, SomCamada="HL", PitchCamada=0.4, RelCamada=0.75, DuracaoMaxS=2.0, FadeS=0.8, InicioS=51.4,
               JanelaS=30.0, DistMaxJogador=1100.0),
            # cadeira do loop 4 gira para o limiar corredor->sala depois de ser vista, quando o jogador esta de costas.
            # Caixa comeca 5 cm depois da do sussurro: o jogador entra nela antes do sussurro sair do gap e o susto reserva a vez
            # 27/09: comeca virada para o piano e gira para ficar de frente para quem vai para a porta; dispara assim que ela sai
            # da tela (CosCostas 0.3, ~72 graus), antes de o jogador chegar perto da porta; rangido 0.35 para ele se virar
            ev("EV_Susto_Cadeira", 23, 1, [4], ((-2465.0, -1327.5, 110.0), (235.0, 422.5, 110.0)), (cad.x, cad.y, 60.0),
               AlvoGirar="LOOPC_L4_Cadeira", GiroYaw=round(giro, 1), bExigirVistoAntes=True, bSoQuandoDeCostas=True, CosCostas=0.3,
               Som="SCD", Pitch=0.45, Volume=0.88, JanelaS=25.0, DistMaxJogador=900.0),
            # estrondo entre a sala e a porta, som no limiar corredor->sala, atras do jogador
            # 27/09: disparou a 7 m no teste e passou despercebido. Som na entrada da sala (~4 m atras de quem vai para a porta),
            # tremor 1.5, costas relaxado (-0.2) e caixa cobrindo a entrada da sala inteira
            ev("EV_Susto_Estrondo", 24, 1, [5], ((-2650.0, -1100.0, 110.0), (250.0, 250.0, 110.0)), (-2800.0, -950.0, 110.0),
               Som="SCD", Pitch=0.55, Volume=1.13, SomCamada="HL", PitchCamada=0.35, RelCamada=0.75, EscalaTremor=1.5,
               bSoQuandoDeCostas=True, CosCostas=-0.2, JanelaS=25.0, DistMaxJogador=1100.0)]
    return marcas + barulhos + sustos


def escritorio():
    """O escritorio fica ao sul do fim do corredor. Vao sem porta (x -3340..-3160, y ~ -650/-705), medido por traces.
    Caixa do lado do corredor/sala, na juncao antes do vao; passos 300 cm dentro; rangido no vao."""
    vao = (-3250.0, -690.0, 110.0)
    return {"caixa": ((-3250.0, -520.0, 110.0), (110.0, 90.0, 110.0)), "porta": vao, "dentro": (vao[0], vao[1] - 300.0, 110.0)}


# ------------------------------------------------------------------ atores
def aplica_cfg(a, e):
    a.set_editor_property("Id", e["Id"])
    a.set_editor_property("IdNum", e["IdNum"])
    a.set_editor_property("Categoria", e["Categoria"])
    a.set_editor_property("Loops", e["Loops"])
    if list(a.get_editor_property("MotivosReserva")) != MOTIVOS_RESERVA:
        a.set_editor_property("MotivosReserva", MOTIVOS_RESERVA)  # instancias ja no mapa guardam a lista antiga
    for k, v in e["cfg"].items():
        if k == "aparicao":
            continue
        if k in ("Som", "SomCamada"):
            v = EAL.load_asset(SONS[v]) if v else None
        if k == "DeslocPorRep":
            v = unreal.Vector(*v)
        if k == "AlvoGirar":
            v = por_label(v)
        if k == "TagLuzes":
            v = unreal.Name(v)
        a.set_editor_property(k, v)
    if "aparicao" in e["cfg"]:
        x, y = e["cfg"]["aparicao"]
        ap = [c for c in a.get_components_by_class(unreal.StaticMeshComponent) if c.get_name().startswith("Aparicao")][0]
        sm, mi = EAL.load_asset(VULTO_SM), EAL.load_asset(VULTO_MI)
        if ap.get_editor_property("static_mesh") != sm:
            ap.set_static_mesh(sm)
        for i in range(ap.get_num_materials()):
            if ap.get_material(i) != mi:
                ap.set_material(i, mi)
        ap.set_world_scale3d(unreal.Vector(1, 1, 1))
        chao = unreal.SystemLibrary.line_trace_single(a.get_world(), unreal.Vector(x, y, 150), unreal.Vector(x, y, -100),
                                                      unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [a], unreal.DrawDebugTrace.NONE, True)
        z0 = chao.to_tuple()[4].z if chao else 0.0
        # pe no chao; a malha do manequim olha para +Y (para quem vem da Chegada)
        ap.set_world_location_and_rotation(unreal.Vector(x, y, z0), unreal.Rotator(0, 0, 0), False, True)
        ap.set_hidden_in_game(True)
        ap.set_visibility(bool(e["cfg"].get("bAparicao")), False)  # 27/09: silhueta estatica desligada (a figura corre)
    snd = a.get_editor_property("Som")
    if snd:
        # um som curto termina antes do corte: Dur <= duracao / pitch (pitch grave alonga o som)
        lim = snd.get_editor_property("duration") / max(0.1, a.get_editor_property("Pitch"))
        pedido = e["cfg"].get("DuracaoMaxS", 4.0)
        if pedido > lim + 1e-6:
            w("  desvio %s: DuracaoMaxS %.2f -> %.2f (som dura %.2f s a pitch %.2f)" % (e["label"], pedido, lim,
              snd.get_editor_property("duration"), a.get_editor_property("Pitch")))
        a.set_editor_property("DuracaoMaxS", round(min(pedido, lim), 3))


def ensure_atores(hub_bp, evt_bp, g):
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    mudou = []
    hubs = [a for a in atores() if a.get_class().get_name().startswith("BP_LuxEventHub")]
    if len(hubs) > 1:
        raise Aborta("mais de um EVENTS_Hub")
    if not hubs:
        loc = g["LOOP_Manager"].get_actor_location() + unreal.Vector(0, 150, 250)
        h = eas.spawn_actor_from_class(hub_bp.generated_class(), loc, unreal.Rotator())
        h.set_actor_label("EVENTS_Hub")
        h.set_folder_path(FOLDER)
        h.set_editor_property("tags", [unreal.Name(TAG)])
        mudou.append("EVENTS_Hub")
    hub_i = [a for a in atores() if a.get_class().get_name().startswith("BP_LuxEventHub")][0]
    if abs(hub_i.get_editor_property("GapMinS") - GAP_MIN_S) > 1e-6:
        hub_i.set_editor_property("GapMinS", GAP_MIN_S)
        mudou.append("EVENTS_Hub.GapMinS=%.1f" % GAP_MIN_S)
    if abs(hub_i.get_editor_property("VolumeMax") - VOLUME_MAX) > 1e-6:
        hub_i.set_editor_property("VolumeMax", VOLUME_MAX)
        mudou.append("EVENTS_Hub.VolumeMax=%.1f" % VOLUME_MAX)
    if abs(hub_i.get_editor_property("EscalaTremorMax") - TREMOR_MAX) > 1e-6:
        hub_i.set_editor_property("EscalaTremorMax", TREMOR_MAX)
        mudou.append("EVENTS_Hub.EscalaTremorMax=%.1f" % TREMOR_MAX)
    if INSTALAR_SUSTOS:
        mudou += prepara_sustos()
    existentes = {a.get_actor_label(): a for a in atores() if a.get_class().get_name().startswith("BP_LuxLoopEvent")}
    for e in plano(g):
        if e["label"] in existentes:
            a = existentes[e["label"]]
            (cx, cy, cz), (ex, ey, ez) = e["caixa"]
            if (a.get_actor_location() - unreal.Vector(cx, cy, cz)).length() > 0.5:
                a.set_actor_location(unreal.Vector(cx, cy, cz), False, True)
                mudou.append(e["label"] + " (movido)")
            box = [c for c in a.get_components_by_class(unreal.BoxComponent)][0]
            if (box.get_editor_property("box_extent") - unreal.Vector(ex, ey, ez)).length() > 0.5:
                box.set_editor_property("box_extent", unreal.Vector(ex, ey, ez))
            ps = [c for c in a.get_components_by_class(unreal.SceneComponent) if c.get_name().startswith("PontoSom")][0]
            if e["som"] and (ps.get_world_location() - unreal.Vector(*e["som"])).length() > 0.5:
                ps.set_world_location(unreal.Vector(*e["som"]), False, True)
            aplica_cfg(a, e)  # configuracao da instancia (idempotente)
            continue
        (cx, cy, cz), (ex, ey, ez) = e["caixa"]
        a = eas.spawn_actor_from_class(evt_bp.generated_class(), unreal.Vector(cx, cy, cz), unreal.Rotator())
        a.set_actor_label(e["label"])
        a.set_folder_path(FOLDER)
        a.set_editor_property("tags", [unreal.Name(TAG)])
        box = [c for c in a.get_components_by_class(unreal.BoxComponent)][0]
        box.set_editor_property("box_extent", unreal.Vector(ex, ey, ez))
        ps = [c for c in a.get_components_by_class(unreal.SceneComponent) if c.get_name().startswith("PontoSom")][0]
        if e["som"]:
            ps.set_world_location(unreal.Vector(*e["som"]), False, True)
        aplica_cfg(a, e)
        mudou.append(e["label"])
    return mudou


def prepara_sustos():
    """Tags LUX_EV_Arandela nas luzes do piscar, cadeira do loop 4 Movable e MotivosReserva no Class Default do evento."""
    mud = []
    for lab in LUZES_SUSTO:
        a = por_label(lab)
        if not a:
            raise Aborta("luz %s nao encontrada" % lab)
        c = a.get_components_by_class(unreal.LightComponent)[0]
        if "STATIC" in str(c.get_editor_property("mobility")):
            c.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
            mud.append(lab + " -> Movable")
        tags = [str(t) for t in a.tags]
        if TAG_LUZES not in tags:
            a.set_editor_property("tags", [unreal.Name(x) for x in tags + [TAG_LUZES]])
            mud.append(lab + " +" + TAG_LUZES)
    cad = por_label("LOOPC_L4_Cadeira")
    rc = cad.get_editor_property("root_component")
    if "MOVABLE" not in str(rc.get_editor_property("mobility")):
        rc.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
        mud.append("LOOPC_L4_Cadeira -> Movable")
    r = cad.get_actor_rotation()
    if abs(((r.yaw - CADEIRA_YAW_BASE) + 180.0) % 360.0 - 180.0) > 0.5:
        cad.set_actor_rotation(unreal.Rotator(r.roll, r.pitch, CADEIRA_YAW_BASE), False)
        mud.append("LOOPC_L4_Cadeira yaw %.1f -> %.1f" % (r.yaw, CADEIRA_YAW_BASE))
    evt = EAL.load_asset(EVT)
    cdo = unreal.get_default_object(evt.generated_class())
    if list(cdo.get_editor_property("MotivosReserva")) != MOTIVOS_RESERVA:
        cdo.set_editor_property("MotivosReserva", MOTIVOS_RESERVA)
        BEL.compile_blueprint(evt)
        mud.append("BP_LuxLoopEvent.MotivosReserva")
    return mud


# ------------------------------------------------------------------ verificar + simulacao
def eventos_mapa():
    out = []
    for a in atores():
        if not a.get_class().get_name().startswith("BP_LuxLoopEvent"):
            continue
        box = [c for c in a.get_components_by_class(unreal.BoxComponent)][0]
        ps = [c for c in a.get_components_by_class(unreal.SceneComponent) if c.get_name().startswith("PontoSom")][0]
        e = {"a": a, "label": a.get_actor_label(), "c": box.get_world_location(), "x": box.get_editor_property("box_extent"),
             "som": ps.get_world_location()}
        for k in ("Id", "IdNum", "Categoria", "Loops", "JanelaS", "DistMaxJogador", "bSoQuandoDeCostas", "CosCostas",
                  "bSoQuandoOlhando", "bExigirVistoAntes", "Volume", "RelCamada", "Som", "SomCamada", "InicioS", "DuracaoMaxS",
                  "BloqueioS", "Probabilidade", "AtrasoS", "PadraoPiscar", "Repeticoes", "IntervaloRepS",
                  "bAparicao", "CosOlhar", "AparicaoDistMin", "bExigirLinhaVisao", "AlvoGirar", "GiroYaw", "TagLuzes"):
            e[k] = a.get_editor_property(k)
        e["Loops"] = list(e["Loops"])
        ap = [c for c in a.get_components_by_class(unreal.StaticMeshComponent) if c.get_name().startswith("Aparicao")][0]
        e["alvo_olhar"] = unreal.SystemLibrary.get_component_bounds(ap)[0] if e["bAparicao"] else e["som"]
        out.append(e)
    return out


def caminho(g):
    """Chegada -> corredor (eixo) -> Sala -> LOOP_PortaSala"""
    ch = g["LOOP_Chegada"].get_actor_location()
    ps = g["LOOP_PortaSala"].get_actor_location()
    return [(ch.x, ch.y), (-3275.0, -350.0), (-3275.0, -500.0), (-2700.0, -900.0), (ps.x, ps.y + 150.0)]


def dentro(e, x, y):
    return abs(x - e["c"].x) <= e["x"].x and abs(y - e["c"].y) <= e["x"].y


def olhando(e, pos, ang):
    """Olhando() do evento: camera na altura do olho olhando para onde anda; cos >= CosOlhar, distancia minima da aparicao
    e linha de visao (trace de verdade no mapa)."""
    cam = unreal.Vector(pos[0], pos[1], ALTURA_OLHO)
    alvo = e["alvo_olhar"]
    d = alvo - cam
    n = d.normal()
    if math.cos(ang) * n.x + math.sin(ang) * n.y < e["CosOlhar"]:
        return False
    if e["bAparicao"] and d.length() < e["AparicaoDistMin"]:
        return False
    if e["bExigirLinhaVisao"]:
        hit = unreal.SystemLibrary.line_trace_single(e["a"].get_world(), cam + n * 50.0, alvo, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
                                                     False, [], unreal.DrawDebugTrace.NONE, True)
        if hit:
            return False
    return True


# 27/09: corrida desligada (Tools/Player/disable_sprint.py): perfil "correndo" fica fora (N/A)
PERFIS = (("andando", 150.0, False), ("olhando_em_volta", 150.0, True))


def simular(evs, g, v=150.0, varre=False):
    """Replica as regras do hub/evento andando no caminho a v cm/s, 1 vez por loop. Retorna {loop: [(id, acao, t, motivo)]}.
    varre=True: a camera oscila +-60 graus em volta da direcao da caminhada (periodo 4 s).
    Barulhos sao avaliados antes dos sustos em cada passo (pior caso para a reserva).
    FIRED de susto leva a distancia do jogador ate o som/aparicao; a cadeira leva tambem se foi vista depois de girar."""
    evs = sorted(evs, key=lambda e: e["Categoria"])
    pts = caminho(g)
    gl, gx = g["gatilho"]
    hub_i = [a for a in atores() if a.get_class().get_name().startswith("BP_LuxEventHub")][0]
    hub_cfg = {"gap": hub_i.get_editor_property("GapMinS"), "post": hub_i.get_editor_property("JanelaPosTrocaS"),
               "maxb": hub_i.get_editor_property("MaxBarulhosPorLoop"), "maxs": hub_i.get_editor_property("MaxSustosPorLoop")}
    res = {}
    for L in range(1, 6):
        t, dt = 0.0, 0.25
        seg, pos, ang, ang_passo = 0, list(pts[0]), 0.0, 0.0
        bloqueio, ultimo, cont = -1000.0, -1000.0, {0: 0, 1: 0}
        marca_pend = any(e["Categoria"] == 2 and L in e["Loops"] for e in evs)
        dist_ate, reserva_ate = -1.0, -1.0
        st = {e["label"]: {"tent": None, "feito": False, "entrada": None} for e in evs}
        out = []
        while seg < len(pts) - 1 and t < 120:
            ax, ay = pts[seg + 1]
            dx, dy = ax - pos[0], ay - pos[1]
            dd = math.hypot(dx, dy)
            passo = v * dt
            if dd <= passo:
                pos, seg = [ax, ay], seg + 1
            else:
                pos = [pos[0] + dx / dd * passo, pos[1] + dy / dd * passo]
            ang_passo = math.atan2(dy, dx) if dd > 1e-6 else ang_passo
            ang = ang_passo + (math.radians(60.0) * math.sin(2 * math.pi * t / 4.0) if varre else 0.0)
            t += dt
            for lab, s in st.items():
                if s.get("girou") and not s.get("visto_depois"):
                    e = [x for x in evs if x["label"] == lab][0]
                    if olhando(dict(e, CosOlhar=0.8, bAparicao=False, bExigirLinhaVisao=False), pos, ang):
                        s["visto_depois"] = round(t - s["girou"], 2)
            for e in evs:
                s = st[e["label"]]
                if s["feito"] or L not in e["Loops"]:
                    continue
                den = dentro(e, pos[0], pos[1])
                if den and s["entrada"] is None:
                    s["entrada"] = t
                    s["tent"] = t
                if s["tent"] is None:
                    continue
                if e["Categoria"] == 2:
                    bloqueio = max(bloqueio, t + e["BloqueioS"])
                    marca_pend = False
                    if e["label"] == "MARCA_Distorcao":
                        dist_ate = t + 13.6
                    out.append((e["label"], "MARCA", round(t, 2), ""))
                    s["feito"] = True
                    continue
                # mesma ordem do TentarDisparar: visto -> dist -> PodeDisparar -> vista -> nao_visto -> costas
                if e["bExigirVistoAntes"] and olhando(e, pos, ang):
                    s["visto"] = True
                d = math.hypot(pos[0] - e["som"].x, pos[1] - e["som"].y)
                m = None
                if e["DistMaxJogador"] > 0 and d > e["DistMaxJogador"]:
                    m = "dist"
                elif t < hub_cfg["post"]:
                    m = "pos_troca"
                elif marca_pend and t < 60:
                    m = "aguarda_marca"
                elif t < bloqueio:
                    m = "externo"
                elif t < dist_ate:
                    m = "distorcao"
                elif e["Categoria"] == 0 and t < reserva_ate:
                    m = "reserva"
                elif t - ultimo < hub_cfg["gap"]:
                    m = "gap"
                elif cont[e["Categoria"]] >= (hub_cfg["maxb"] if e["Categoria"] == 0 else hub_cfg["maxs"]):
                    m = "cota"
                elif e["bSoQuandoOlhando"] and not olhando(e, pos, ang):
                    m = "vista"
                elif e["bExigirVistoAntes"] and not s.get("visto"):
                    m = "nao_visto"
                elif e["bSoQuandoDeCostas"]:
                    fx, fy = math.cos(ang), math.sin(ang)
                    nx, ny = e["som"].x - pos[0], e["som"].y - pos[1]
                    nn = math.hypot(nx, ny) or 1
                    if (fx * nx + fy * ny) / nn > e["CosCostas"]:
                        m = "costas"
                if m is None:
                    alvo = e["alvo_olhar"]
                    out.append((e["label"], "FIRED", round(t, 2), "d=%.0f" % math.hypot(pos[0] - alvo.x, pos[1] - alvo.y)
                                if e["Categoria"] == 1 else ""))
                    if e["AlvoGirar"]:
                        s["girou"] = t
                    ultimo = t
                    cont[e["Categoria"]] += 1
                    s["feito"] = True
                else:
                    s["ultimo_m"] = m
                    if e["Categoria"] == 1 and m in MOTIVOS_RESERVA:
                        reserva_ate = t + 0.5
                    if m in ("troca", "pos_troca", "aguarda_marca", "externo", "distorcao", "reserva"):
                        s["tent"] = t
                    if t - s["tent"] > e["JanelaS"]:
                        out.append((e["label"], "SKIP", round(t, 2), m))
                        s["feito"] = True
        for lab, s in st.items():
            if s.get("girou"):
                out.append((lab, "VISTO_DEPOIS" if s.get("visto_depois") else "NAO_VISTO_DEPOIS", s.get("visto_depois", 0), ""))
        for e in evs:
            s = st[e["label"]]
            if L in e["Loops"] and not s["feito"]:
                out.append((e["label"], "PENDENTE_NA_PORTA" if s["tent"] is not None else "NAO_ALCANCADO", round(t, 2), s.get("ultimo_m", "")))
        res[L] = out
    return res


def verificar():
    falhas, avisos = [], []
    if not (EAL.does_asset_exist(HUB) and EAL.does_asset_exist(EVT)):
        return ["BPs ausentes"], [], {}
    hub, evt = EAL.load_asset(HUB), EAL.load_asset(EVT)
    for bp in (hub, evt):
        e = erros_bp(bp)
        if e:
            falhas.append("%s: %s" % (bp.get_name(), e))
        if unreal.get_default_object(bp.generated_class()).get_editor_property("VersaoSpec") != VERSAO:
            falhas.append("%s sem VersaoSpec" % bp.get_name())
    try:
        estrutural(hub, evt)
    except Aborta as ex:
        falhas.append(str(ex))
    hubs = [a for a in atores() if a.get_class().get_name().startswith("BP_LuxEventHub")]
    if len(hubs) != 1:
        falhas.append("esperava 1 EVENTS_Hub (%d)" % len(hubs))
    elif abs(hubs[0].get_editor_property("GapMinS") - GAP_MIN_S) > 1e-6:
        falhas.append("EVENTS_Hub.GapMinS = %s (esperado %s)" % (hubs[0].get_editor_property("GapMinS"), GAP_MIN_S))
    evs = eventos_mapa()
    ids = [e["Id"] for e in evs]
    nums = [e["IdNum"] for e in evs]
    if len(set(ids)) != len(ids) or len(set(nums)) != len(nums) or any(n >= 100 or n <= 0 for n in nums):
        falhas.append("Id/IdNum repetidos ou fora de 1..99: %s" % list(zip(ids, nums)))
    g = geo()
    gl, gx = g["gatilho"]
    for e in evs:
        s = e["Som"]
        if e["Categoria"] == 2:
            continue
        if not s:
            if not e["bAparicao"]:
                falhas.append("%s sem som" % e["label"])
            continue
        dur = s.get_editor_property("duration")
        loop_ = getattr(s, "looping", None)
        if isinstance(s, unreal.SoundWave) and s.get_editor_property("looping"):
            falhas.append("%s: som em loop" % e["label"])
        lim = dur / max(0.1, e["a"].get_editor_property("Pitch"))
        if e["InicioS"] + e["DuracaoMaxS"] > lim + 1e-3:
            falhas.append("%s: InicioS+Dur %.2f > duracao/pitch %.2f" % (e["label"], e["InicioS"] + e["DuracaoMaxS"], lim))
        if e["DuracaoMaxS"] > 5.0:
            falhas.append("%s: Dur > 5 s" % e["label"])
        rel = e["RelCamada"] if e["SomCamada"] else 0.0
        if e["Volume"] * (1 + rel) > VOLUME_MAX + 1e-6:
            falhas.append("%s: volume %.2f > %.1f" % (e["label"], e["Volume"] * (1 + rel), VOLUME_MAX))
        db = -24.0 * max(0.0, e["DistMaxJogador"] - 200.0) / 1800.0
        if db < -12.0 - 1e-6:
            falhas.append("%s: ganho em D=%.0f = %.1f dB (< -12)" % (e["label"], e["DistMaxJogador"], db))
        if e["Categoria"] != 2 and 1 in e["Loops"]:
            falhas.append("%s no loop 1" % e["label"])
        if e["Categoria"] != 2 and any(L >= 3 for L in e["Loops"]) and (e["c"].y - e["x"].y) > (gl.y + gx.y):
            falhas.append("%s (loop 3-5) a montante do GatilhoFechar" % e["label"])
        if e["Categoria"] != 2:
            gap_y = max(gl.y - gx.y - (e["c"].y + e["x"].y), (e["c"].y - e["x"].y) - (gl.y + gx.y))
            gap_x = max(gl.x - gx.x - (e["c"].x + e["x"].x), (e["c"].x - e["x"].x) - (gl.x + gx.x))
            if max(gap_x, gap_y) < 20.0:
                falhas.append("%s a menos de 20 cm do GatilhoFechar" % e["label"])
    for e in evs:
        if e["Categoria"] == 1 and list(e["a"].get_editor_property("MotivosReserva")) != MOTIVOS_RESERVA:
            falhas.append("%s: MotivosReserva desatualizado" % e["label"])
        if e["TagLuzes"] and str(e["TagLuzes"]) != "None":
            luzes = [a for a in atores() if str(e["TagLuzes"]) in [str(t) for t in a.tags]]
            if not luzes:
                falhas.append("%s: nenhuma luz com a tag %s" % (e["label"], e["TagLuzes"]))
            for a in luzes:
                c = a.get_components_by_class(unreal.LightComponent)[0]
                cor = c.get_editor_property("light_color")
                if "MOVABLE" not in str(c.get_editor_property("mobility")) or (cor.r > 1.3 * max(cor.g, cor.b, 1)):
                    falhas.append("%s: luz %s nao Movable ou avermelhada" % (e["label"], a.get_actor_label()))
        pp = list(e["PadraoPiscar"] or [])
        if pp and (min(pp) < 0.25 or len(pp) > 8 or sum(pp) > 4.0):
            falhas.append("%s: piscar fora da regra (passo>=0.25, <=8 passos, <=4 s)" % e["label"])
        if e["AlvoGirar"] and "MOVABLE" not in str(e["AlvoGirar"].get_editor_property("root_component").get_editor_property("mobility")):
            falhas.append("%s: %s nao e Movable" % (e["label"], e["AlvoGirar"].get_actor_label()))
    for L in range(1, 6):
        nb = len([e for e in evs if e["Categoria"] == 0 and L in e["Loops"]])
        ns = len([e for e in evs if e["Categoria"] == 1 and L in e["Loops"]])
        if nb > 3 or ns > 1:
            falhas.append("loop %d: %d barulhos, %d sustos configurados" % (L, nb, ns))
    nao_marc = [e for e in evs if e["Categoria"] != 2]
    for i, a in enumerate(nao_marc):
        for b_ in nao_marc[i + 1:]:
            if set(a["Loops"]) & set(b_["Loops"]) and abs(a["c"].x - b_["c"].x) < a["x"].x + b_["x"].x and abs(a["c"].y - b_["c"].y) < a["x"].y + b_["x"].y:
                falhas.append("caixas sobrepostas no mesmo loop: %s e %s" % (a["label"], b_["label"]))
    sim = {}
    for nome, v, varre in PERFIS:
        sim[nome] = simular(evs, g, v, varre)
        for L, res in sim[nome].items():
            dist_loop = any(e["label"] == "MARCA_Distorcao" and L in e["Loops"] for e in evs)
            for lab, acao, t, m in res:
                if acao in ("SKIP", "PENDENTE_NA_PORTA", "NAO_ALCANCADO") and [e for e in evs if e["label"] == lab and e["Categoria"] == 1]:
                    msg = "susto %s nao disparou (%s, %s) no loop %d, perfil %s" % (lab, acao, m, L, nome)
                    # correndo, a porta chega antes de a distorcao (14.6 s) acabar: limite conhecido, vira aviso
                    (avisos if (nome == "correndo" and dist_loop) else falhas).append(msg)
    if sujos():
        avisos.append("pacotes sujos: %s" % sujos())
    return falhas, avisos, sim


# ------------------------------------------------------------------ modos
def sondar():
    g = geo()
    gl, gx = g["gatilho"]
    w("GatilhoFechar: centro %s extent %s (dono LOOP_Manager, bool bArmado)" % (gl, gx))
    w("Chegada %s | LOOP_PortaSala %s | BP_BaseDoor7 %s" % (g["LOOP_Chegada"].get_actor_location(), g["LOOP_PortaSala"].get_actor_location(),
                                                           g["BP_BaseDoor7"].get_actor_location()))
    for lab in ("LUX_Luz_Corredor_Arandela3", "LUX_Luz_Corredor_Arandela5"):
        c = g[lab].get_components_by_class(unreal.LightComponent)[0]
        w("%s: cor %s, mobilidade %s, tags %s" % (lab, c.get_editor_property("light_color"), c.get_editor_property("mobility"), [str(t) for t in g[lab].tags]))
    for k, pth in SONS.items():
        s = EAL.load_asset(pth)
        w("som %s: %s dur=%.2f" % (k, pth, s.get_editor_property("duration")))
    ceu = [a for a in atores() if a.get_class().get_name().startswith("BP_LuxCeu")]
    w("BP_LuxCeu: bDistorcaoAtiva=%s DuracaoS=%s | LevelSequenceActor LuxDistorcao: %s" % (
        ceu[0].get_editor_property("bDistorcaoAtiva") if ceu else None, ceu[0].get_editor_property("DuracaoS") if ceu else 13.6,
        [a.get_actor_label() for a in atores() if "LuxDistorcao" in [str(t) for t in a.tags]]))
    pawn = unreal.get_default_object(EAL.load_asset("/Game/Characters/MixamoFP/Blueprints/BP_Player_Cowboy").generated_class())
    w("Pawn: MaxWalkSpeed=%s BaseEyeHeight=%s" % (pawn.get_editor_property("character_movement").get_editor_property("max_walk_speed"),
                                                  pawn.get_editor_property("base_eye_height")))
    w("cozinha: nao existe no Mapa_B (portas: BP_BaseDoor5/sala, BP_BaseDoor7/quarto); ESCRITORIO_NO_LUGAR_DA_COZINHA=%s" % ESCRITORIO_NO_LUGAR_DA_COZINHA)
    try:
        for e in plano(g):
            w("plano: %s id=%d cat=%d loops=%s caixa=%s som=%s" % (e["label"], e["IdNum"], e["Categoria"], e["Loops"], e["caixa"], e["som"]))
    except Aborta as ex:
        w("plano incompleto:", ex)


def instalar():
    if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():
        raise Aborta("feche o PIE")
    if unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence():
        raise Aborta("feche o Sequencer")
    proprios = {HUB, EVT, SA, CS, MI, SAVE, VULTO_SM, VULTO_M, VULTO_MI, "/Game/Masion/Mapa_B"}
    if sujos() and not ("retomar" in sys.argv and set(sujos()) <= proprios):
        raise Aborta("ha pacotes nao salvos antes de comecar: %s" % sujos())
    if ESCRITORIO_NO_LUGAR_DA_COZINHA is None:
        raise Aborta("defina ESCRITORIO_NO_LUGAR_DA_COZINHA (o Mapa_B nao tem cozinha)")
    g = geo()
    plano(g)  # valida o plano antes de criar qualquer coisa
    novos = ensure_assets()
    hub, evt, criou = ensure_bps()
    mud = ensure_atores(hub, evt, g)
    w("atores novos:", mud or "nenhum")
    f, av, sim = verificar()
    for nome, res_p in sim.items():
        for L, res in res_p.items():
            w("simulacao %s loop %d: %s" % (nome, L, res))
    if f:
        raise Aborta("verificar FAIL (nada salvo): %s" % f)
    esperado = {HUB, EVT, SA, CS, MI, SAVE, VULTO_SM, VULTO_M, VULTO_MI, "/Game/Masion/Mapa_B"}
    extra = set(sujos()) - esperado
    if extra:
        raise Aborta("pacotes sujos inesperados: %s" % sorted(extra))
    for a in novos + [hub, evt] + [EAL.load_asset(p) for p in (SA, CS, MI, SAVE, VULTO_M, VULTO_MI, VULTO_SM) if p in sujos()]:
        if a.get_outermost().get_name() not in sujos():
            continue
        w("salvo", a.get_path_name(), EAL.save_loaded_asset(a, False))
    U = unreal.EditorLoadingAndSavingUtils
    mapa = [p for p in U.get_dirty_map_packages() if p.get_name() == "/Game/Masion/Mapa_B"]
    if mapa:
        w("salvo Mapa_B", U.save_packages(mapa, True))
    if sujos():
        raise Aborta("ainda ha pacotes sujos: %s" % sujos())
    w("verificar: PASS", "| avisos:", av or "nenhum")


def desfazer():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    n = 0
    for a in [a for a in atores() if TAG in [str(t) for t in a.tags]]:
        eas.destroy_actor(a)
        n += 1
    U = unreal.EditorLoadingAndSavingUtils
    U.save_packages([p for p in U.get_dirty_map_packages() if p.get_name() == "/Game/Masion/Mapa_B"], True)
    w("removidos %d atores; BPs e assets ficam em %s (apague no Content Browser se quiser)" % (n, DIR))


def main():
    os.makedirs(SNAP, exist_ok=True)
    open(LOG, "w", encoding="utf-8").close()
    modo = next((a for a in sys.argv[1:] if a in ("sondar", "instalar", "verificar", "desfazer")), "sondar")
    w("modo:", modo, "| INSTALAR_SUSTOS =", INSTALAR_SUSTOS)
    try:
        if modo == "verificar":
            f, av, sim = verificar()
            for nome, res_p in sim.items():
                for L, res in res_p.items():
                    w("simulacao %s loop %d: %s" % (nome, L, res))
            w("verificar:", ("FAIL %s" % f) if f else "PASS", "| avisos:", av or "nenhum")
        else:
            {"sondar": sondar, "instalar": instalar, "desfazer": desfazer}[modo]()
    except Aborta as ex:
        w("ABORTADO:", ex, "| sujos:", sujos())
    except Exception:
        w("ERRO " + traceback.format_exc(), "| sujos:", sujos())


if __name__ == "__main__":
    main()
