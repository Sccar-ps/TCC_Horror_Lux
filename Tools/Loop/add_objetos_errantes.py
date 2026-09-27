# LUX - Etapa 3: objetos que mudam de lugar (BP_LuxObjetosErrantes, ErrVersao 1).
#   py "<projeto>/Tools/Loop/add_objetos_errantes.py" sondar|instalar|verificar|desfazer
# O jogador nunca ve um objeto se mover: a troca so acontece com origem E destino fora de vista (a tela do PedirTroca
# nao fica preta depois do teleporte -> JanelaPreto = 0), ou "quando nao olha" (depois de ter visto o objeto).
# So LE PedirTroca, LOOP_Manager (LoopAtual, bArmado) e portas. Nunca apaga grafo nem recarrega pacote.
# Plano editavel: Tools/Loop/objetos_errantes_plano.json. Snapshots: Tools/Loop/snapshots/.
import hashlib, importlib, json, math, os, sys, time, traceback, unreal

ERR_VERSAO = 1
EAL, BEL, BGE = unreal.EditorAssetLibrary, unreal.BlueprintEditorLibrary, unreal.BlueprintGraphEditor
BPP = "/Game/Masion/LUX/Loop/BP_LuxObjetosErrantes"
ME = BPP + ".BP_LuxObjetosErrantes_C"
MGR_C = "/Game/Masion/LUX/Loop/BP_LuxLoopManager.BP_LuxLoopManager_C"
DOOR_C = "/Game/FPMovement/Blueprints/Doors/BP_BaseDoor.BP_BaseDoor_C"
AQUI = os.path.dirname(os.path.abspath(__file__))
PLANO = os.path.join(AQUI, "objetos_errantes_plano.json")
SNAPS = os.path.join(AQUI, "snapshots")
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(SAVED, "LuxSnapshots", "objetos_errantes_log.txt")
FOLDER = "LUX/ObjetosErrantes"
ALTURA_OLHO = 166.0     # camera real do BP_Player_Cowboy (capsula 96 + SpringArm 70)
RAIO_CAPSULA = 40.0
sys.path.insert(0, AQUI)
import add_loop_events as ale
importlib.reload(ale)
B, junc, entrada, ok_pin, G = ale.B, ale.junc, ale.entrada, ale.ok_pin, ale.G
KSL, KML, GS, ARR, STR, TXT = ale.KSL, ale.KML, ale.GS, ale.ARR, ale.STR, ale.TXT
MAC = ale.MAC


def w(*a):
    line = " ".join(str(x) for x in a)
    unreal.log("[LUX err] " + line)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


class Aborta(Exception):
    pass


atores, por_label, sujos, erros_bp = ale.atores, ale.por_label, ale.sujos, ale.erros_bp


# ------------------------------------------------------------------ geometria (editor)
def world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def trace(a, b, ignorar=()):
    h = unreal.SystemLibrary.line_trace_single(world(), a, b, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, list(ignorar),
                                               unreal.DrawDebugTrace.NONE, True)
    if not h:
        return None
    t = h.to_tuple()
    return {"loc": t[4], "ator": t[9]}


def bounds(a):
    o, e = a.get_actor_bounds(False)
    return o, e


def pontos9(o, e):
    pts = [o]
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                pts.append(unreal.Vector(o.x + sx * e.x, o.y + sy * e.y, o.z + sz * e.z))
    return pts


def dist2d(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


# ------------------------------------------------------------------ sondar
def pedir_troca():
    """Cadeia do PedirTroca, lida do setup_loop.py (gerador do manager) e do export: fade 0->1 em TempoEscurecer (hold),
    Delay(TempoEscurecer+TempoApagado), teleporte + LoopAtual+1 no mesmo frame, e logo em seguida StartCameraFade 1->0
    (TempoClarear) SEM Delay. Preto depois do teleporte = 0 s -> JanelaPreto = 0."""
    mgr = por_label("LOOP_Manager")
    esc, apa, cla = (mgr.get_editor_property(k) for k in ("TempoEscurecer", "TempoApagado", "TempoClarear"))
    preto_restante = 0.0
    janela = min(0.4, preto_restante - 0.2)
    return {"cadeia": ["SetViewTargetWithBlend(CamSala, TempoAproximar)", "Delay(TempoAproximar)",
                       "StartCameraFade 0->1 (%.2f s, hold)" % esc, "Delay(%.2f)" % (esc + apa), "K2_TeleportTo(Chegada)",
                       "SetControlRotation", "SetViewTargetWithBlend(CamQuarto, 0)", "SetGameCameraCutThisFrame",
                       "SET LoopAtual = LoopAtual+1", "AplicarTag _ON/_OFF", "bArmado = true",
                       "StartCameraFade 1->0 (%.2f s, sem Delay)" % cla, "..."],
            "preto_restante_s": preto_restante, "janela_preto_s": 0.0 if janela < 0.15 else janela}


def lanterna_doc():
    bp = EAL.load_asset("/Game/Characters/MixamoFP/Blueprints/BP_Player_Cowboy")
    out = []
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        o = lib.get_object_for_blueprint(lib.get_data(h), bp)
        if o and "Flashlight" in o.get_name():
            d = {"componente": o.get_name(), "classe": o.get_class().get_name()}
            if isinstance(o, unreal.PrimitiveComponent):
                d["colisao"] = o.get_collision_profile_name()
                d["visibility"] = str(o.get_collision_response_to_channel(unreal.CollisionChannel.ECC_VISIBILITY))
            out.append(d)
    return out


PAPEIS = [  # id, papel, comodo, modo, ator, slots
    {"i": 0, "id": "ABAJUR", "comodo": "Quarto", "modo": 0, "ator": None,
     "vazio": "os abajures sao 3 pecas (base, cupula e luz propria LUX_Luz_*_Abajur): falha no §3 (luz anexada/multi-peca)"},
    {"i": 1, "id": "CANECA", "comodo": "Escritorio", "modo": 0, "ator": "Escritorio_Livro1",
     "obs": "nao ha caneca no Mapa_B; o objeto pequeno da mesa do escritorio que passa no §3 e o Escritorio_Livro1"},
    {"i": 2, "id": "CADEIRA", "comodo": "Escritorio", "modo": 0, "ator": None,
     "vazio": "Escritorio_Cadeira tem a colisao num ator separado (COL_Escritorio_Cadeira): mover so a malha deixaria uma parede "
              "invisivel; falha no §3 (par/anexo)"},
    {"i": 3, "id": "LIVRO", "comodo": "Sala", "modo": 1, "ator": "Sala_Prateleira_Livro1"},
    {"i": 4, "id": "BRINQUEDO", "comodo": "Quarto", "modo": 2, "ator": None, "vazio": "nao existe brinquedo no Mapa_B"},
    {"i": 5, "id": "QUADRO", "comodo": "Sala", "modo": 0, "ator": "Sala_Quadro_N2"}]


def slots_do(p, a):
    """Destinos por papel (N, marcas, transform). Retorna lista de dicts com loc, rot."""
    o, e = bounds(a)
    loc, rot = a.get_actor_location(), a.get_actor_rotation()
    baixo = o.z - e.z                     # fundo dos bounds
    alt_pivo = loc.z - baixo              # pivo acima do fundo
    out = []
    if p["id"] == "CANECA":
        mesa = por_label("Escritorio_Mesa")
        mo, me = bounds(mesa)
        # P1 L2: mesma superficie >= 80 cm -> a mesa tem 142 cm e a vela ocupa o outro lado: testa variantes
        for dy in (-85.0, -95.0, -105.0):
            out.append({"N": 1, "marcas": ["L2"], "loc": unreal.Vector(loc.x, loc.y + dy, loc.z), "rot": rot, "tipo": "superficie"})
        # P2 L4: chao sob a borda da mesa (lado leste, de frente para a porta do escritorio)
        chao = trace(unreal.Vector(mo.x + me.x + 25, loc.y, 50), unreal.Vector(mo.x + me.x + 25, loc.y, -50))
        z = chao["loc"].z if chao else 0.0
        out.append({"N": 2, "marcas": ["L4"], "loc": unreal.Vector(mo.x + me.x + 25, loc.y, z + alt_pivo), "rot": unreal.Rotator(rot.roll, rot.pitch, rot.yaw + 35),
                    "tipo": "chao"})
    elif p["id"] == "LIVRO":
        cad = por_label("Sala_Cadeira_Leitura").get_actor_location()
        for dx, dy in ((100, 140), (120, 160), (80, 170)):
            x, y = cad.x + dx, cad.y + dy
            chao = trace(unreal.Vector(x, y, 50), unreal.Vector(x, y, -50))
            z = chao["loc"].z if chao else 0.0
            out.append({"N": 1, "marcas": ["V3"], "loc": unreal.Vector(x, y, z + alt_pivo), "rot": unreal.Rotator(rot.roll, rot.pitch, rot.yaw + 50), "tipo": "chao"})
    elif p["id"] == "QUADRO":
        # P1 L5: girado 180 graus no plano da parede, em torno do centro dos bounds (eixo = normal da parede)
        eixo = unreal.Vector(0, 1, 0) if e.y < e.x else unreal.Vector(1, 0, 0)
        giro = unreal.MathLibrary.rotator_from_axis_and_angle(eixo, 180.0)
        novo_rot = unreal.MathLibrary.compose_rotators(rot, giro)
        rel = loc - o
        rel2 = unreal.MathLibrary.greater_greater_vector_rotator(rel, giro)
        out.append({"N": 1, "marcas": ["L5"], "loc": o + rel2, "rot": novo_rot, "tipo": "parede", "eixo": eixo})
    return out


def checa_slot(p, a, s, extras):
    """Checagens do §3. Retorna (ok, motivo)."""
    o, e = bounds(a)
    delta = s["loc"] - a.get_actor_location()
    c = o + delta  # centro no destino (rotacoes pequenas: aproximacao)
    ign = [a]
    apoio = []
    if s["tipo"] in ("chao", "superficie"):
        fundo = c.z - e.z
        h = trace(unreal.Vector(c.x, c.y, fundo + 1), unreal.Vector(c.x, c.y, fundo - 3), ign)
        if not h:
            return False, "SEM_APOIO"
        apoio.append(h["ator"])
    if s["tipo"] == "parede":
        eixo = s["eixo"]
        fino = e.y if eixo.y else e.x
        for sgn in (1, -1):
            h = trace(c, c + eixo * (fino + 3) * sgn, ign)
            if h:
                apoio.append(h["ator"])
                break
        else:
            return False, "SEM_PAREDE"
    if s["tipo"] == "chao" and 2 * e.z > 45:
        paredes = [trace(c, c + unreal.Vector(dx, dy, 0), ign) for dx, dy in ((60, 0), (-60, 0), (0, 60), (0, -60))]
        if not any(paredes):
            return False, "LONGE_DA_PAREDE"
    for porta in extras["portas"]:
        po, pe = bounds(porta)
        lim = 160.0 if porta.get_actor_label() == "LOOP_PortaSala" else 140.0
        if dist2d(c, po) - math.hypot(e.x, e.y) < lim:
            return False, "PORTA %s" % porta.get_actor_label()
    if dist2d(c, extras["chegada"]) < 200:
        return False, "CHEGADA"
    for x in extras["loop_atores"]:
        if x is not a and dist2d(c, x.get_actor_location()) < 80:
            return False, "PERTO_LOOP %s" % x.get_actor_label()
    if s["tipo"] == "chao":
        for dx, dy in ((1, 0), (0, 1)):
            livre = 0
            for sgn in (1, -1):
                h = trace(unreal.Vector(c.x, c.y, 60) + unreal.Vector(dx, dy, 0) * (e.x + 1) * sgn,
                          unreal.Vector(c.x, c.y, 60) + unreal.Vector(dx, dy, 0) * (e.x + 2 * RAIO_CAPSULA + 20) * sgn, ign)
                if not h:
                    livre += 1
            if livre == 0:
                return False, "PASSAGEM"
    ov = unreal.SystemLibrary.box_overlap_actors(world(), c, e * 0.9,
                                                 [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1, unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY2,
                                                  unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY3, unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY4],
                                                 None, [a] + [x for x in apoio if x])  # ignora SEMPRE o prop e o apoio
    ov = ov[1] if isinstance(ov, tuple) else ov
    if ov:
        return False, "SOBREPOE %s" % ",".join(x.get_actor_label() for x in ov[:3])
    if any(m.startswith("L") for m in s["marcas"]):
        olho = extras["chegada"] + unreal.Vector(0, 0, ALTURA_OLHO - 98.0)
        for pt in pontos9(c, e):
            if not trace(olho, pt, [a]):
                return False, "VISTO_DA_CHEGADA"
    return True, "ok"


def sondar(gravar=True):
    mgr = por_label("LOOP_Manager")
    if not mgr:
        raise Aborta("LOOP_Manager nao encontrado")
    ps = por_label("LOOP_PortaSala")
    ch = por_label("LOOP_Chegada")
    d = dist2d(ps.get_actor_location(), ch.get_actor_location())
    if d <= 500:
        raise Aborta("FALHA 2b: LOOP_PortaSala -> Chegada = %.0f cm (<= 500)" % d)
    portas = [a for a in atores() if "Door" in a.get_class().get_name()]
    loop_atores = [a for a in atores() if any(str(t).startswith("LOOP") or str(t) == "LUX_LOOP_CONTEUDO" for t in a.tags)]
    extras = {"portas": portas, "chegada": ch.get_actor_location(), "loop_atores": loop_atores}
    pt = pedir_troca()
    plano = {"versao": ERR_VERSAO, "janela_preto_s": pt["janela_preto_s"], "pedir_troca": pt, "porta_chegada_cm": round(d),
             "gatilho_dono": "BP_LuxLoopManager_C (bArmado)", "portas": [p.get_actor_label() for p in portas],
             "lanterna": lanterna_doc(), "ofpa": False, "altura_olho_cm": ALTURA_OLHO, "raio_capsula_cm": RAIO_CAPSULA, "papeis": []}
    for p in PAPEIS:
        e = dict(p)
        e["slots"] = []
        if p["ator"]:
            a = por_label(p["ator"])
            if not a:
                e["vazio"] = "ator %s nao encontrado" % p["ator"]
                e["ator"] = None
            else:
                luzes = [x for x in atores() if isinstance(x, unreal.Light) and (x.get_actor_label().startswith("LUX_Luz_") or "Vela" in x.get_actor_label())
                         and x.get_actor_location().distance(a.get_actor_location()) <= 400]
                e["precisa_luz"] = not luzes
                por_n = {}
                for s in slots_do(p, a):
                    ok, mot = checa_slot(p, a, s, extras)
                    por_n.setdefault(s["N"], []).append((ok, mot, s))
                for n, lst in sorted(por_n.items()):
                    bons = [s for ok, mot, s in lst if ok]
                    if bons:
                        s = bons[0]
                        e["slots"].append({"N": n, "marcas": s["marcas"], "loc": [s["loc"].x, s["loc"].y, s["loc"].z],
                                           "rot": [s["rot"].roll, s["rot"].pitch, s["rot"].yaw], "tipo": s["tipo"]})
                    else:
                        e.setdefault("slots_vazios", []).append({"N": n, "motivos": [m for _, m, _ in lst]})
        plano["papeis"].append(e)
    if gravar:
        if os.path.exists(PLANO):
            w("plano ja existe: mantido (apague para regenerar)")
        else:
            with open(PLANO, "w", encoding="utf-8") as fh:
                json.dump(plano, fh, indent=2, ensure_ascii=False, default=str)
            w("plano gravado:", PLANO)
    w("sondagem:", json.dumps(plano, ensure_ascii=False, default=str))
    return plano


# ------------------------------------------------------------------ BP
def tipos():
    t = ale.tipos_base()
    t["transform"] = BEL.get_struct_type(unreal.Transform.static_struct())
    t["transform[]"] = BEL.get_array_type(t["transform"])
    t["vec[]"] = BEL.get_array_type(t["vec"])
    t["actor[]"] = BEL.get_array_type(t["actor"])
    t["spot"] = BEL.get_object_reference_type(unreal.SpotLightComponent.static_class())
    return t


VARS = [
    ("ObjAlvo", "actor[]", True, None), ("ObjId", "string[]", True, None), ("ObjModo", "int[]", True, None),
    ("ObjMaxPorLoop", "int[]", True, None), ("ObjAtivo", "bool[]", True, None), ("ObjVoltaCasa", "bool[]", True, None),
    ("ObjPrecisaLuz", "bool[]", True, None),
    ("PosMarcador", "actor[]", True, None), ("PosObj", "int[]", True, None), ("PosN", "int[]", True, None),
    ("PosTroca", "int[]", True, None), ("PosNaoOlha", "int[]", True, None),
    ("Portas", "actor[]", True, None), ("PortaLoop", "actor", True, None), ("Chegada", "actor", True, None),
    ("bObjetosAtivos", "bool", True, True), ("LoopsPermitidos", "int", True, 62), ("MaxNaoOlhaPorLoop", "int", True, 1),
    ("bDebugTela", "bool", True, False), ("Bits", "int[]", True, [1, 2, 4, 8, 16, 32]),
    ("IntervaloVigia", "real", True, 0.1), ("LimiarTeleporte", "real", True, 250.0), ("JanelaPreto", "real", True, 0.0),
    ("DistNaoOlha", "real", True, 350.0), ("DistJogador", "real", True, 200.0), ("DistChegada", "real", True, 200.0),
    ("DistPorta", "real", True, 140.0), ("DistPortaLoop", "real", True, 160.0), ("MargemTela", "real", True, 0.1),
    ("DotVisto", "real", True, 0.8), ("DistVisto", "real", True, 800.0), ("VistoMin", "real", True, 1.0),
    ("NaoVistoMin", "real", True, 3.0), ("AtrasoNaoOlha", "real", True, 15.0), ("IntervaloEventos", "real", True, 10.0),
    ("LogMax", "int", True, 400), ("ErrPlanoHash", "string", True, ""),
    # estado
    ("Manager", "mgr", False, None), ("Ignorar", "actor[]", False, None), ("Lanterna", "spot", False, None),
    ("ObjValido", "bool[]", False, None), ("ObjPendente", "bool[]", False, None), ("ObjVistoPos", "bool[]", False, None),
    ("ObjVistoLoop", "bool[]", False, None), ("ObjCasa", "transform[]", False, None), ("ObjPos", "int[]", False, None),
    ("ObjMovesLoop", "int[]", False, None), ("ObjVistoT", "real[]", False, None), ("ObjVistoAcum", "real[]", False, None),
    ("ObjMovT", "real[]", False, None), ("ObjBloqueio", "string[]", False, None), ("ObjPts", "vec[]", False, None),
    ("ObjExt", "vec[]", False, None), ("PosT", "transform[]", False, None),
    ("LoopVisto", "int", False, -1), ("TempoLoop", "real", False, -100.0), ("TempoTeleporte", "real", False, -100.0),
    ("TempoGatilho", "real", False, -100.0), ("UltimoMovT", "real", False, -100.0), ("UltimoMovId", "string", False, ""),
    ("PrevArmado", "bool", False, False), ("PawnPrev", "vec", False, None), ("NaoOlhaNoLoop", "int", False, 0),
    ("LogErr", "string[]", False, None), ("UltN", "int", False, 0), ("UltNTraco", "int", False, 0), ("UltDot", "real", False, 0.0),
    ("UltDist", "real", False, 0.0), ("UltVisivel", "bool", False, False), ("UltAtor", "string", False, ""),
    ("UltSeguro", "bool", False, False), ("UltMotivo", "string", False, ""), ("UltDestino", "int", False, -1),
    ("ErrVersao", "int", False, 0)]

FUNCS = [("ErrLog", [("Evento", "string"), ("Detalhe", "string")]), ("ErrInicializar", []), ("ErrVigiar", []),
         ("ErrPontosVisiveis", [("i", "int"), ("T", "transform")]), ("ErrVisivel", [("i", "int"), ("T", "transform")]),
         ("ErrVisto", [("i", "int")]), ("ErrAplicarTroca", [("i", "int")]), ("ErrTentarNaoOlha", [("i", "int")]),
         ("ErrDestinoSeguro", [("i", "int"), ("T", "transform")]), ("ErrMover", [("i", "int"), ("p", "int"), ("Motivo", "string")]),
         ("ErrResumo", []), ("ErrDefinirAtivo", [("Ativo", "bool")]), ("ErrDefinirLoops", [("Mascara", "int")]),
         ("ErrDefinirObjeto", [("i", "int"), ("Ativo", "bool")]), ("ErrForcarMover", [("i", "int"), ("N", "int")]),
         ("ErrForcarTroca", []), ("ErrMostrarLog", []), ("ErrLimparLog", []), ("ErrFinalizar", []), ("ErrDiagVisivel", [("i", "int")])]


def bits_tem(b, mask, bit_src):
    """(mask & Bits[L]) != 0"""
    a = b.op("And_IntInt", mask, bit_src)
    return b.op("NotEqual_IntInt", a, 0)


def get_arr(b, arr, idx):
    n = b.c(ARR + "Array_Get", 0, 0)
    b.lk(b.v(arr), n, "TargetArray")
    b.lk(idx, n, "Index") if isinstance(idx, tuple) else b.g.val(n, "Index", idx)
    return (n, "Item")


def set_arr(b, arr, idx, item, size=True):
    n = b.c(ARR + "Array_Set", 0, 0, bSizeToFit="true" if size else "false")
    b.lk(b.v(arr), n, "TargetArray")
    b.lk(idx, n, "Index") if isinstance(idx, tuple) else b.g.val(n, "Index", idx)
    if isinstance(item, tuple):
        b.lk(item, n, "Item")
    else:
        b.g.val(n, "Item", item)
    return n


def log(b, ev, det):
    n = b.call("ErrLog")
    b.g.val(n, "Evento", ev)
    if isinstance(det, tuple):
        b.lk(det, n, "Detalhe")
    elif det:
        b.g.val(n, "Detalhe", det)
    return n


def loop_atual(b):
    la = b.v("LoopAtual", cls=MGR_C)
    b.lk(b.v("Manager"), la[0], "self")
    return la


def bit_loop(b):
    cl = b.c(KML + "Clamp", 0, 0, Min=0, Max=5)
    b.lk(loop_atual(b), cl, "Value")
    return get_arr(b, "Bits", (cl, "ReturnValue"))


def cam(b):
    pcm = (b.c(GS + "GetPlayerCameraManager", 0, 0, PlayerIndex=0), "ReturnValue")
    loc = b.c("/Script/Engine.PlayerCameraManager:GetCameraLocation", 0, 0)
    b.lk(pcm, loc, "self")
    rot = b.c("/Script/Engine.PlayerCameraManager:GetCameraRotation", 0, 0)
    b.lk(pcm, rot, "self")
    fw = b.c(KML + "GetForwardVector", 0, 0)
    b.lk((rot, "ReturnValue"), fw, "InRot")
    return (loc, "ReturnValue"), (fw, "ReturnValue")


def ponto(b, i, k, T):
    """TransformLocation(T, ObjPts[i*9+k])"""
    idx = b.op("Add_IntInt", b.op("Multiply_IntInt", i, 9), k)
    p = get_arr(b, "ObjPts", idx)
    n = b.c(KML + "TransformLocation", 0, 0)
    b.lk(T, n, "T")
    b.lk(p, n, "Location")
    return (n, "ReturnValue")


def entrada_log(bp, nome, me):
    w("  build:", nome)  # grava na hora: se o editor cair, o log mostra a ultima funcao
    return entrada(bp, nome, me)


def build(bp):
    t = tipos()
    # ErrLog(Evento, Detalhe)
    b, en = entrada_log(bp, "ErrLog", ME)
    utc = (b.c(KML + "UtcNow", 0, 0), "ReturnValue")
    asdt = b.c(TXT + "AsDateTime_DateTime", 0, 0)
    b.lk(utc, asdt, "In")
    t2s = b.c(TXT + "Conv_TextToString", 0, 0)
    b.lk((asdt, "ReturnValue"), t2s, "InText")
    ms = b.c(KML + "GetMillisecond", 0, 0)
    b.lk(utc, ms, "A")
    sub = b.c(STR + "GetSubstring", 0, 0, StartIndex=1, Length=3)
    b.lk(b.is_(b.op("Add_IntInt", (ms, "ReturnValue"), 1000)), sub, "SourceString")
    lp = b.v("LoopVisto")
    linha = b.s(["UTC=", (t2s, "ReturnValue"), ".", (sub, "ReturnValue"), " | t_jogo=", b.fs(b.now()),
                 " | t_real=", b.fs((b.c(GS + "GetRealTimeSeconds", 0, 0), "ReturnValue")), " | loop=", b.is_(lp),
                 " | evento=", (en, "Evento"), " | ", (en, "Detalhe")])
    add = b.c(ARR + "Array_Add", 0, 0)
    b.lk(b.v("LogErr"), add, "TargetArray")
    b.lk(linha, add, "NewItem")
    ln = b.c(ARR + "Array_Length", 0, 0)
    b.lk(b.v("LogErr"), ln, "TargetArray")
    bmx = b.br(b.op("Greater_IntInt", (ln, "ReturnValue"), b.v("LogMax")))
    rm = b.c(ARR + "Array_Remove", 0, 0, IndexToRemove=0)
    b.lk(b.v("LogErr"), rm, "TargetArray")
    j = junc(b)
    pr = b.c(KSL + "PrintString", 0, 0, bPrintToLog="true", Duration=6.0)
    b.lk(linha, pr, "InString")
    b.lk(b.v("bDebugTela"), pr, "bPrintToScreen")
    b.ch(en, add, bmx)
    b.ch((bmx, "then"), rm, j)
    b.ch((bmx, "else"), j)
    b.ch((j, "then"), pr)

    # ErrPontosVisiveis(i, T) -> UltN, UltNTraco, UltDot, UltDist, UltAtor
    b, en = entrada_log(bp, "ErrPontosVisiveis", ME)
    i, T = (en, "i"), (en, "T")
    C, Fw = cam(b)
    z1, z2, z3 = b.setv("UltN", 0), b.setv("UltNTraco", 0), b.setv("UltAtor", "")
    centro = ponto(b, i, 0, T)
    nrm = b.c(KML + "Normal", 0, 0)
    b.lk(b.op("Subtract_VectorVector", centro, C), nrm, "A")
    sdot = b.setv("UltDot", src=b.op("Dot_VectorVector", Fw, (nrm, "ReturnValue")))
    vd = b.c(KML + "Vector_Distance", 0, 0)
    b.lk(centro, vd, "V1")
    b.lk(C, vd, "V2")
    sdist = b.setv("UltDist", src=(vd, "ReturnValue"))
    fl = b.g.pos(b.ge.add_macro_node(MAC + "ForLoop"), 0, 0)
    b.g.val(fl, "FirstIndex", 0)
    b.g.val(fl, "LastIndex", 8)
    pk = ponto(b, i, (fl, "Index"), T)
    pc = (b.c(GS + "GetPlayerController", 0, 0, PlayerIndex=0), "ReturnValue")
    proj = b.c(GS + "ProjectWorldToScreen", 0, 0, bPlayerViewportRelative="false")
    b.lk(pc, proj, "Player")
    b.lk(pk, proj, "WorldPosition")
    vp = b.c("/Script/Engine.PlayerController:GetViewportSize", 0, 0)
    b.lk(pc, vp, "self")
    sx = b.c(KML + "Conv_IntToDouble", 0, 0)
    b.lk((vp, "SizeX"), sx, "InInt")
    sy = b.c(KML + "Conv_IntToDouble", 0, 0)
    b.lk((vp, "SizeY"), sy, "InInt")
    br_ = b.c(KML + "BreakVector2D", 0, 0)
    b.lk((proj, "ScreenPosition"), br_, "InVec")
    mg = b.v("MargemTela")

    def dentro(val, tam):
        lo = b.op("Multiply_DoubleDouble", tam, b.op("Multiply_DoubleDouble", mg, -1.0))
        hi = b.op("Multiply_DoubleDouble", tam, b.op("Add_DoubleDouble", mg, 1.0))
        return b.e(b.op("GreaterEqual_DoubleDouble", val, lo), b.op("LessEqual_DoubleDouble", val, hi))

    na_tela = b.e(b.e((proj, "ReturnValue"), dentro((br_, "X"), (sx, "ReturnValue"))), dentro((br_, "Y"), (sy, "ReturnValue")))
    btela = b.br(na_tela)
    inc1 = b.setv("UltN", src=b.op("Add_IntInt", b.v("UltN"), 1))
    dirv = b.c(KML + "Normal", 0, 0)
    b.lk(b.op("Subtract_VectorVector", pk, C), dirv, "A")
    dk = b.c(KML + "Vector_Distance", 0, 0)
    b.lk(pk, dk, "V1")
    b.lk(C, dk, "V2")
    fim = b.op("Add_VectorVector", C, b.op("Multiply_VectorFloat", (dirv, "ReturnValue"), b.op("Subtract_DoubleDouble", (dk, "ReturnValue"), 30.0)))
    ign = b.c(ARR + "Array_Add", 0, 0)   # Ignorar + Alvo (copia local nao existe em BP: adiciona e remove depois)
    b.lk(b.v("Ignorar"), ign, "TargetArray")
    b.lk(get_arr(b, "ObjAlvo", i), ign, "NewItem")
    lt = b.c(KSL + "LineTraceSingle", 0, 0, TraceChannel="TraceTypeQuery1", bTraceComplex="false", bIgnoreSelf="true")
    b.lk(C, lt, "Start")
    b.lk(fim, lt, "End")
    b.lk(b.v("Ignorar"), lt, "ActorsToIgnore")
    rmi = b.c(ARR + "Array_RemoveItem", 0, 0)
    b.lk(b.v("Ignorar"), rmi, "TargetArray")
    b.lk(get_arr(b, "ObjAlvo", i), rmi, "Item")
    bhit = b.br((lt, "ReturnValue"))
    inc2 = b.setv("UltNTraco", src=b.op("Add_IntInt", b.v("UltNTraco"), 1))
    bh = b.c(GS + "BreakHitResult", 0, 0)
    b.lk((lt, "OutHit"), bh, "Hit")
    dn = b.c(KSL + "GetDisplayName", 0, 0)
    b.lk((bh, "HitActor"), dn, "Object")
    sat = b.setv("UltAtor", src=(dn, "ReturnValue"))
    # conta so se esta na tela E o traco chega livre; UltN = pontos visiveis
    dec = b.setv("UltN", src=b.op("Subtract_IntInt", b.v("UltN"), 1))
    j1 = junc(b)
    b.ch(en, z1, z2, z3, sdot, sdist, fl)
    b.ch((fl, "LoopBody"), btela)
    b.ch((btela, "then"), inc1, ign, lt, rmi, bhit)
    b.ch((bhit, "then"), dec, sat, j1)
    b.ch((bhit, "else"), inc2, j1)

    # ErrVisivel(i, T) -> UltVisivel = Dist<DistNaoOlha OU N>=1
    b, en = entrada_log(bp, "ErrVisivel", ME)
    pv = b.call("ErrPontosVisiveis")
    b.lk((en, "i"), pv, "i")
    b.lk((en, "T"), pv, "T")
    sv = b.setv("UltVisivel", src=b.ou(b.op("Less_DoubleDouble", b.v("UltDist"), b.v("DistNaoOlha")), b.op("GreaterEqual_IntInt", b.v("UltN"), 1)))
    b.ch(en, pv, sv)

    # ErrDestinoSeguro(i, T) -> UltSeguro, UltMotivo
    b, en = entrada_log(bp, "ErrDestinoSeguro", ME)
    i, T = (en, "i"), (en, "T")
    C = ponto(b, i, 0, T)

    def falha(m):
        a = b.setv("UltSeguro", "false")
        c = b.setv("UltMotivo", src=m) if isinstance(m, tuple) else b.setv("UltMotivo", m)
        b.ch(a, c)
        return a

    pawnloc = b.c("/Script/Engine.Actor:K2_GetActorLocation", 0, 0)
    b.lk((b.c(GS + "GetPlayerPawn", 0, 0, PlayerIndex=0), "ReturnValue"), pawnloc, "self")
    vd = b.c(KML + "Vector_Distance", 0, 0)
    b.lk(C, vd, "V1")
    b.lk((pawnloc, "ReturnValue"), vd, "V2")
    bj = b.br(b.op("Less_DoubleDouble", (vd, "ReturnValue"), b.v("DistJogador")))
    s0 = b.setv("UltSeguro", "true")
    s0m = b.setv("UltMotivo", "ok")
    fe = b.g.pos(b.ge.add_macro_node(MAC + "ForEachLoop"), 0, 0)
    b.lk(b.v("Portas"), fe, "Array")
    pl = b.c("/Script/Engine.Actor:K2_GetActorLocation", 0, 0)
    b.lk((fe, "Array Element"), pl, "self")
    d2 = b.c(KML + "Vector_Distance2D", 0, 0)
    b.lk(C, d2, "V1")
    b.lk((pl, "ReturnValue"), d2, "V2")
    ext = get_arr(b, "ObjExt", i)
    bv = b.c(KML + "BreakVector", 0, 0)
    b.lk(ext, bv, "InVec")
    ext2 = b.c(KML + "Sqrt", 0, 0)
    b.lk(b.op("Add_DoubleDouble", b.op("Multiply_DoubleDouble", (bv, "X"), (bv, "X")), b.op("Multiply_DoubleDouble", (bv, "Y"), (bv, "Y"))), ext2, "A")
    eqp = b.c(KML + "EqualEqual_ObjectObject", 0, 0)
    b.lk((fe, "Array Element"), eqp, "A")
    b.lk(b.v("PortaLoop"), eqp, "B")
    lim = b.c(KML + "SelectFloat", 0, 0)
    b.lk(b.v("DistPortaLoop"), lim, "A")
    b.lk(b.v("DistPorta"), lim, "B")
    b.lk((eqp, "ReturnValue"), lim, "bPickA")
    bp_ = b.br(b.op("Less_DoubleDouble", b.op("Subtract_DoubleDouble", (d2, "ReturnValue"), (ext2, "ReturnValue")), (lim, "ReturnValue")))
    fporta = falha("PORTA")
    cl = b.c("/Script/Engine.Actor:K2_GetActorLocation", 0, 0)
    b.lk(b.v("Chegada"), cl, "self")
    vdc = b.c(KML + "Vector_Distance", 0, 0)
    b.lk(C, vdc, "V1")
    b.lk((cl, "ReturnValue"), vdc, "V2")
    bc = b.br(b.e(b.valido(b.v("Chegada")), b.op("Less_DoubleDouble", (vdc, "ReturnValue"), b.v("DistChegada"))))
    fe2 = b.g.pos(b.ge.add_macro_node(MAC + "ForEachLoop"), 0, 0)
    b.lk(b.v("ObjAlvo"), fe2, "Array")
    ol = b.c("/Script/Engine.Actor:K2_GetActorLocation", 0, 0)
    b.lk((fe2, "Array Element"), ol, "self")
    vdo = b.c(KML + "Vector_Distance", 0, 0)
    b.lk(C, vdo, "V1")
    b.lk((ol, "ReturnValue"), vdo, "V2")
    bo = b.br(b.e(b.e(b.op("NotEqual_IntInt", (fe2, "Array Index"), i), b.valido((fe2, "Array Element"))),
                  b.op("Less_DoubleDouble", (vdo, "ReturnValue"), 60.0)))
    # sobreposicao: BoxTrace (Visibility) parado no centro, extent x0.9, ignorando o proprio alvo e o jogador
    igno = b.c(ARR + "Array_Add", 0, 0)
    b.lk(b.v("Ignorar"), igno, "TargetArray")
    b.lk(get_arr(b, "ObjAlvo", i), igno, "NewItem")
    ov = b.c(KSL + "BoxTraceSingle", 0, 0, TraceChannel="TraceTypeQuery1", bTraceComplex="false", bIgnoreSelf="true")
    b.lk(C, ov, "Start")
    b.lk(b.op("Add_VectorVector", C, (b.c(KML + "MakeVector", 0, 0, X=0.0, Y=0.0, Z=0.1), "ReturnValue")), ov, "End")
    b.lk(b.op("Multiply_VectorFloat", ext, 0.9), ov, "HalfSize")
    b.lk(b.v("Ignorar"), ov, "ActorsToIgnore")
    rmi = b.c(ARR + "Array_RemoveItem", 0, 0)
    b.lk(b.v("Ignorar"), rmi, "TargetArray")
    b.lk(get_arr(b, "ObjAlvo", i), rmi, "Item")
    bhr = b.c(GS + "BreakHitResult", 0, 0)
    b.lk((ov, "OutHit"), bhr, "Hit")
    bov = b.br((ov, "ReturnValue"))
    dn = b.c(KSL + "GetDisplayName", 0, 0)
    b.lk((bhr, "HitActor"), dn, "Object")
    fov = falha(b.s(["SOBREPOE ", (dn, "ReturnValue")]))
    b.ch(en, bj)
    b.ch((bj, "then"), falha("JOGADOR"))
    b.ch((bj, "else"), s0, s0m, fe)
    b.ch((fe, "LoopBody"), bp_)
    b.ch((bp_, "then"), fporta)
    b.ch((fe, "Completed"), bc)
    b.ch((bc, "then"), falha("CHEGADA"))
    b.ch((bc, "else"), fe2)
    b.ch((fe2, "LoopBody"), bo)
    b.ch((bo, "then"), falha("OUTRO_ERRANTE"))
    b.ch((fe2, "Completed"), igno, ov, rmi, bov)
    b.ch((bov, "then"), fov)

    # ErrMover(i, p, Motivo)
    b, en = entrada_log(bp, "ErrMover", ME)
    i, p = (en, "i"), (en, "p")
    alvo = get_arr(b, "ObjAlvo", i)
    b0 = b.br(b.e(get_arr(b, "ObjValido", i), b.valido(alvo)))
    ecasa = b.op("EqualEqual_IntInt", p, -1)
    selT = b.c(KML + "SelectTransform", 0, 0)
    b.lk(get_arr(b, "ObjCasa", i), selT, "A")
    cl = b.c(KML + "Max", 0, 0, B=0)
    b.lk(p, cl, "A")
    b.lk(get_arr(b, "PosT", (cl, "ReturnValue")), selT, "B")
    b.lk(ecasa, selT, "bPickA")
    T = (selT, "ReturnValue")
    # (sem fisica: nenhum prop do plano simula fisica; o no IsSimulatingPhysics nao e criavel pela API)
    st = b.c("/Script/Engine.Actor:K2_SetActorTransform", 0, 0, bSweep="false", bTeleport="true")
    b.lk(alvo, st, "self")
    b.lk(T, st, "NewTransform")
    gl = b.c("/Script/Engine.Actor:K2_GetActorLocation", 0, 0)
    b.lk(alvo, gl, "self")
    btl = b.c(KML + "BreakTransform", 0, 0)
    b.lk(T, btl, "InTransform")
    dd = b.c(KML + "Vector_Distance", 0, 0)
    b.lk((gl, "ReturnValue"), dd, "V1")
    b.lk((btl, "Location"), dd, "V2")
    bf = b.br(b.op("Greater_DoubleDouble", (dd, "ReturnValue"), 1.0))
    ffal = log(b, "ERR_FALHA", b.s(["obj=", get_arr(b, "ObjId", i), " para=", b.is_(p), " erro_cm=", b.fs((dd, "ReturnValue"))]))
    de = get_arr(b, "ObjPos", i)
    det = b.s(["obj=", get_arr(b, "ObjId", i), " de=", b.is_(de), " para=", b.is_(p), " motivo=", (en, "Motivo")])
    lmove = log(b, "ERR_MOVE", det)
    sets = [set_arr(b, "ObjPos", i, p), set_arr(b, "ObjPendente", i, "false"), set_arr(b, "ObjVistoPos", i, "false"),
            set_arr(b, "ObjVistoAcum", i, 0.0), set_arr(b, "ObjMovT", i, b.now()), b.setv("UltimoMovT", src=b.now()),
            b.setv("UltimoMovId", src=get_arr(b, "ObjId", i))]
    b.ch(en, b0)
    b.ch((b0, "then"), st, bf)
    b.ch((bf, "then"), ffal)
    b.ch((bf, "else"), lmove, *sets)

    # ErrAplicarTroca(i)
    b, en = entrada_log(bp, "ErrAplicarTroca", ME)
    i = (en, "i")
    alvo = get_arr(b, "ObjAlvo", i)
    b0 = b.br(b.e(get_arr(b, "ObjValido", i), b.valido(alvo)))
    bitL = bit_loop(b)
    permitido = b.e(b.e(b.v("bObjetosAtivos"), bits_tem(b, b.v("LoopsPermitidos"), bitL)), get_arr(b, "ObjAtivo", i))
    bperm = b.br(permitido)
    sd_casa = b.setv("UltDestino", -1)
    # procura o 1o slot deste objeto com a marca L deste loop (modo != 1)
    sd0 = b.setv("UltDestino", -2)
    fe = b.g.pos(b.ge.add_macro_node(MAC + "ForEachLoop"), 0, 0)
    b.lk(b.v("PosObj"), fe, "Array")
    cond = b.e(b.e(b.op("EqualEqual_IntInt", (fe, "Array Element"), i), bits_tem(b, get_arr(b, "PosTroca", (fe, "Array Index")), bitL)),
               b.e(b.op("NotEqual_IntInt", get_arr(b, "ObjModo", i), 1), b.op("EqualEqual_IntInt", b.v("UltDestino"), -2)))
    bsl = b.br(cond)
    sdi = b.setv("UltDestino", src=(fe, "Array Index"))
    bnenhum = b.br(b.op("EqualEqual_IntInt", b.v("UltDestino"), -2))
    bvolta = b.br(get_arr(b, "ObjVoltaCasa", i))
    sdc2 = b.setv("UltDestino", -1)
    fim_nada = set_arr(b, "ObjPendente", i, "false")
    j = junc(b)
    biguais = b.br(b.op("EqualEqual_IntInt", b.v("UltDestino"), get_arr(b, "ObjPos", i)))
    fim_ig = set_arr(b, "ObjPendente", i, "false")
    preto = b.e(b.op("Greater_DoubleDouble", b.v("JanelaPreto"), 0.0), b.op("LessEqual_DoubleDouble", b.menos_agora("TempoTeleporte"), b.v("JanelaPreto")))
    bpreto = b.br(preto)
    # destino: transform
    selT = b.c(KML + "SelectTransform", 0, 0)
    b.lk(get_arr(b, "ObjCasa", i), selT, "A")
    mx = b.c(KML + "Max", 0, 0, B=0)
    b.lk(b.v("UltDestino"), mx, "A")
    b.lk(get_arr(b, "PosT", (mx, "ReturnValue")), selT, "B")
    b.lk(b.op("EqualEqual_IntInt", b.v("UltDestino"), -1), selT, "bPickA")
    Tdest = (selT, "ReturnValue")
    gt = b.c("/Script/Engine.Actor:GetTransform", 0, 0)
    b.lk(alvo, gt, "self")
    v1 = b.call("ErrVisivel")
    b.lk(i, v1, "i")
    b.lk((gt, "ReturnValue"), v1, "T")
    bv1 = b.br(b.v("UltVisivel"))
    v2 = b.call("ErrVisivel")
    b.lk(i, v2, "i")
    b.lk(Tdest, v2, "T")
    bv2 = b.br(b.v("UltVisivel"))
    blq = set_arr(b, "ObjBloqueio", i, "VISIVEL")
    jseg = junc(b)
    seg = b.call("ErrDestinoSeguro")
    b.lk(i, seg, "i")
    b.lk(Tdest, seg, "T")
    bseg = b.br(b.v("UltSeguro"))
    mot = b.c(KML + "SelectString", 0, 0, A="TROCA_PRETO", B="TROCA_OCULTO")
    b.lk(preto, mot, "bPickA")
    mv = b.call("ErrMover")
    b.lk(i, mv, "i")
    b.lk(b.v("UltDestino"), mv, "p")
    b.lk((mot, "ReturnValue"), mv, "Motivo")
    lsk = log(b, "ERR_SKIP", b.s(["obj=", get_arr(b, "ObjId", i), " motivo=", b.v("UltMotivo")]))
    psk = set_arr(b, "ObjPendente", i, "false")
    b.ch(en, b0)
    b.ch((b0, "then"), bperm)
    b.ch((bperm, "else"), sd_casa, j)
    b.ch((bperm, "then"), sd0, fe)
    b.ch((fe, "LoopBody"), bsl)
    b.ch((bsl, "then"), sdi)
    b.ch((fe, "Completed"), bnenhum)
    b.ch((bnenhum, "then"), bvolta)
    b.ch((bvolta, "then"), sdc2, j)
    b.ch((bvolta, "else"), fim_nada)
    b.ch((bnenhum, "else"), j)
    b.ch((j, "then"), biguais)
    b.ch((biguais, "then"), fim_ig)
    b.ch((biguais, "else"), bpreto)
    b.ch((bpreto, "then"), jseg)
    b.ch((bpreto, "else"), v1, bv1)
    b.ch((bv1, "then"), blq)
    b.ch((bv1, "else"), v2, bv2)
    b.ch((bv2, "then"), blq)
    b.ch((bv2, "else"), jseg)
    b.ch((jseg, "then"), seg, bseg)
    b.ch((bseg, "then"), mv)
    b.ch((bseg, "else"), lsk, psk)

    # ErrVisto(i)
    b, en = entrada_log(bp, "ErrVisto", ME)
    i = (en, "i")
    alvo = get_arr(b, "ObjAlvo", i)
    gt = b.c("/Script/Engine.Actor:GetTransform", 0, 0)
    b.lk(alvo, gt, "self")
    pv = b.call("ErrPontosVisiveis")
    b.lk(i, pv, "i")
    b.lk((gt, "ReturnValue"), pv, "T")
    # luz: nao precisa, ou lanterna valida e visivel e o objeto dentro do cone e do raio
    lant_ok = b.valido(b.v("Lanterna"))
    ang = b.v("OuterConeAngle", cls="/Script/Engine.SpotLightComponent")
    b.lk(b.v("Lanterna"), ang[0], "self")
    lloc = b.c("/Script/Engine.SceneComponent:K2_GetComponentLocation", 0, 0)
    b.lk(b.v("Lanterna"), lloc, "self")
    lfw = b.c("/Script/Engine.SceneComponent:GetForwardVector", 0, 0)
    b.lk(b.v("Lanterna"), lfw, "self")
    olc = b.c("/Script/Engine.Actor:K2_GetActorLocation", 0, 0)
    b.lk(alvo, olc, "self")
    dl = b.c(KML + "Normal", 0, 0)
    b.lk(b.op("Subtract_VectorVector", (olc, "ReturnValue"), (lloc, "ReturnValue")), dl, "A")
    cosang = b.c(KML + "DegCos", 0, 0)
    b.lk(ang, cosang, "A")
    no_cone = b.op("GreaterEqual_DoubleDouble", b.op("Dot_VectorVector", (lfw, "ReturnValue"), (dl, "ReturnValue")), (cosang, "ReturnValue"))
    rad = b.v("AttenuationRadius", cls="/Script/Engine.LocalLightComponent")
    b.lk(b.v("Lanterna"), rad[0], "self")
    dlz = b.c(KML + "Vector_Distance", 0, 0)
    b.lk((olc, "ReturnValue"), dlz, "V1")
    b.lk((lloc, "ReturnValue"), dlz, "V2")
    vis = b.c("/Script/Engine.SceneComponent:IsVisible", 0, 0)
    b.lk(b.v("Lanterna"), vis, "self")
    luz = b.ou(b.nao(get_arr(b, "ObjPrecisaLuz", i)),
               b.e(b.e(lant_ok, (vis, "ReturnValue")), b.e(no_cone, b.op("Less_DoubleDouble", (dlz, "ReturnValue"), rad))))
    visto = b.e(b.e(b.op("GreaterEqual_IntInt", b.v("UltN"), 2), b.op("Greater_DoubleDouble", b.v("UltDot"), b.v("DotVisto"))),
                b.e(b.op("Less_DoubleDouble", b.v("UltDist"), b.v("DistVisto")), luz))
    bvi = b.br(visto)
    s1 = set_arr(b, "ObjVistoT", i, b.now())
    s2 = set_arr(b, "ObjVistoAcum", i, b.op("Add_DoubleDouble", get_arr(b, "ObjVistoAcum", i), b.v("IntervaloVigia")))
    bprim = b.br(b.nao(get_arr(b, "ObjVistoLoop", i)))
    s3 = set_arr(b, "ObjVistoLoop", i, "true")
    lv = log(b, "ERR_VISTO", b.s(["obj=", get_arr(b, "ObjId", i), " pos=", b.is_(get_arr(b, "ObjPos", i)), " dist=", b.fs(b.v("UltDist")), " dot=", b.fs(b.v("UltDot"))]))
    j = junc(b)
    bpos = b.br(b.e(b.op("GreaterEqual_DoubleDouble", get_arr(b, "ObjVistoAcum", i), b.v("VistoMin")), b.nao(get_arr(b, "ObjVistoPos", i))))
    s4 = set_arr(b, "ObjVistoPos", i, "true")
    lvp = log(b, "ERR_VISTO_POS", b.s(["obj=", get_arr(b, "ObjId", i), " desde_move=", b.fs(b.op("Subtract_DoubleDouble", b.now(), get_arr(b, "ObjMovT", i)))]))
    b.ch(en, pv, bvi)
    b.ch((bvi, "then"), s1, s2, bprim)
    b.ch((bprim, "then"), s3, lv, j)
    b.ch((bprim, "else"), j)
    b.ch((j, "then"), bpos)
    b.ch((bpos, "then"), s4, lvp)

    # ErrTentarNaoOlha(i)
    b, en = entrada_log(bp, "ErrTentarNaoOlha", ME)
    i = (en, "i")
    alvo = get_arr(b, "ObjAlvo", i)
    bitL = bit_loop(b)
    base = b.e(b.e(b.e(b.op("NotEqual_IntInt", get_arr(b, "ObjModo", i), 0), get_arr(b, "ObjValido", i)),
                   b.e(get_arr(b, "ObjAtivo", i), b.v("bObjetosAtivos"))),
               b.e(b.e(bits_tem(b, b.v("LoopsPermitidos"), bitL), b.op("Less_IntInt", get_arr(b, "ObjMovesLoop", i), get_arr(b, "ObjMaxPorLoop", i))),
                   b.e(b.op("Less_IntInt", b.v("NaoOlhaNoLoop"), b.v("MaxNaoOlhaPorLoop")), b.nao(get_arr(b, "ObjPendente", i)))))
    bbase = b.br(base)
    tempo = b.e(b.e(b.op("GreaterEqual_DoubleDouble", b.op("Subtract_DoubleDouble", b.now(), get_arr(b, "ObjVistoT", i)), b.v("NaoVistoMin")),
                    b.op("GreaterEqual_DoubleDouble", b.menos_agora("TempoLoop"), b.v("AtrasoNaoOlha"))),
                b.e(b.op("GreaterEqual_DoubleDouble", b.menos_agora("TempoGatilho"), b.v("IntervaloEventos")),
                    b.op("GreaterEqual_DoubleDouble", b.menos_agora("UltimoMovT"), b.v("IntervaloEventos"))))
    bvp = b.br(get_arr(b, "ObjVistoPos", i))
    bt = b.br(tempo)
    btv = set_arr(b, "ObjBloqueio", i, "VISTO")
    btt = set_arr(b, "ObjBloqueio", i, "TEMPO")
    sd0 = b.setv("UltDestino", -2)
    fe = b.g.pos(b.ge.add_macro_node(MAC + "ForEachLoop"), 0, 0)
    b.lk(b.v("PosObj"), fe, "Array")
    cond = b.e(b.e(b.op("EqualEqual_IntInt", (fe, "Array Element"), i), bits_tem(b, get_arr(b, "PosNaoOlha", (fe, "Array Index")), bitL)),
               b.e(b.op("NotEqual_IntInt", (fe, "Array Index"), get_arr(b, "ObjPos", i)), b.op("EqualEqual_IntInt", b.v("UltDestino"), -2)))
    bsl = b.br(cond)
    sdi = b.setv("UltDestino", src=(fe, "Array Index"))
    bnada = b.br(b.op("NotEqual_IntInt", b.v("UltDestino"), -2))
    gt = b.c("/Script/Engine.Actor:GetTransform", 0, 0)
    b.lk(alvo, gt, "self")
    v1 = b.call("ErrVisivel")
    b.lk(i, v1, "i")
    b.lk((gt, "ReturnValue"), v1, "T")
    bv1 = b.br(b.nao(b.v("UltVisivel")))
    mx = b.c(KML + "Max", 0, 0, B=0)
    b.lk(b.v("UltDestino"), mx, "A")
    Td = get_arr(b, "PosT", (mx, "ReturnValue"))
    v2 = b.call("ErrVisivel")
    b.lk(i, v2, "i")
    b.lk(Td, v2, "T")
    bv2 = b.br(b.nao(b.v("UltVisivel")))
    seg = b.call("ErrDestinoSeguro")
    b.lk(i, seg, "i")
    b.lk(Td, seg, "T")
    bseg = b.br(b.v("UltSeguro"))
    mv = b.call("ErrMover")
    b.lk(i, mv, "i")
    b.lk(b.v("UltDestino"), mv, "p")
    b.lk(b.s(["NAO_OLHOU visto_s=", b.fs(get_arr(b, "ObjVistoAcum", i))]), mv, "Motivo")
    c1 = set_arr(b, "ObjMovesLoop", i, b.op("Add_IntInt", get_arr(b, "ObjMovesLoop", i), 1))
    c2 = b.setv("NaoOlhaNoLoop", src=b.op("Add_IntInt", b.v("NaoOlhaNoLoop"), 1))
    b.ch(en, bbase)
    b.ch((bbase, "then"), bvp)
    b.ch((bvp, "else"), btv)
    b.ch((bvp, "then"), bt)
    b.ch((bt, "else"), btt)
    b.ch((bt, "then"), sd0, fe)
    b.ch((fe, "LoopBody"), bsl)
    b.ch((bsl, "then"), sdi)
    b.ch((fe, "Completed"), bnada)
    b.ch((bnada, "then"), v1, bv1)
    b.ch((bv1, "then"), v2, bv2)
    b.ch((bv2, "then"), seg, bseg)
    b.ch((bseg, "then"), mv, c1, c2)

    # ErrResumo
    b, en = entrada_log(bp, "ErrResumo", ME)
    fe = b.g.pos(b.ge.add_macro_node(MAC + "ForEachLoop"), 0, 0)
    b.lk(b.v("ObjId"), fe, "Array")
    ix = (fe, "Array Index")
    det = b.s(["obj=", (fe, "Array Element"), " pos=", b.is_(get_arr(b, "ObjPos", ix)), " visto=", b.bs(get_arr(b, "ObjVistoLoop", ix)),
               " movido=", b.is_(get_arr(b, "ObjMovesLoop", ix)), " pendente=", b.bs(get_arr(b, "ObjPendente", ix)),
               " bloqueio=", get_arr(b, "ObjBloqueio", ix)])
    lr = log(b, "ERR_RESUMO", det)
    b.ch(en, fe)
    b.ch((fe, "LoopBody"), lr)

    # ErrInicializar
    b, en = entrada_log(bp, "ErrInicializar", ME)
    fm = b.c(GS + "GetActorOfClass", 0, 0, ActorClass="/Script/Engine.BlueprintGeneratedClass'%s'" % MGR_C)
    sm = b.setv("Manager", src=(fm, "ReturnValue"))
    fe = b.g.pos(b.ge.add_macro_node(MAC + "ForEachLoop"), 0, 0)
    b.lk(b.v("ObjId"), fe, "Array")
    ix = (fe, "Array Index")
    alvo = get_arr(b, "ObjAlvo", ix)
    # defaults por objeto
    base_sets = [set_arr(b, "ObjValido", ix, "true"), set_arr(b, "ObjPendente", ix, "false"), set_arr(b, "ObjVistoPos", ix, "false"),
                 set_arr(b, "ObjVistoLoop", ix, "false"), set_arr(b, "ObjPos", ix, -1), set_arr(b, "ObjMovesLoop", ix, 0),
                 set_arr(b, "ObjVistoT", ix, -100.0), set_arr(b, "ObjVistoAcum", ix, 0.0), set_arr(b, "ObjMovT", ix, -100.0),
                 set_arr(b, "ObjBloqueio", ix, "")]
    bval = b.br(b.valido(alvo))
    sin = set_arr(b, "ObjValido", ix, "false")
    lsin = log(b, "ERR_CONFIG", b.s(["obj=", (fe, "Array Element"), " SEM_ALVO"]))
    root = b.c("/Script/Engine.Actor:K2_GetRootComponent", 0, 0)
    b.lk(alvo, root, "self")
    mob = b.v("Mobility", cls="/Script/Engine.SceneComponent")
    b.lk((root, "ReturnValue"), mob[0], "self")
    eqm = b.c(KML + "EqualEqual_ByteByte", 0, 0)
    b.lk(mob, eqm, "A")
    b.g.val(eqm, "B", 2)
    bmov = b.br((eqm, "ReturnValue"))
    snm = set_arr(b, "ObjValido", ix, "false")
    lnm = log(b, "ERR_CONFIG", b.s(["obj=", (fe, "Array Element"), " NAO_MOVABLE"]))
    par = b.c("/Script/Engine.Actor:GetAttachParentActor", 0, 0)
    b.lk(alvo, par, "self")
    banx = b.br(b.valido((par, "ReturnValue")))
    sax = set_arr(b, "ObjValido", ix, "false")
    lax = log(b, "ERR_CONFIG", b.s(["obj=", (fe, "Array Element"), " ANEXADO"]))
    gt = b.c("/Script/Engine.Actor:GetTransform", 0, 0)
    b.lk(alvo, gt, "self")
    scasa = set_arr(b, "ObjCasa", ix, (gt, "ReturnValue"))
    gb = b.c("/Script/Engine.Actor:GetActorBounds", 0, 0, bOnlyCollidingComponents="false")
    b.lk(alvo, gb, "self")
    sext = set_arr(b, "ObjExt", ix, (gb, "BoxExtent"))
    fl = b.g.pos(b.ge.add_macro_node(MAC + "ForLoop"), 0, 0)
    b.g.val(fl, "FirstIndex", 0)
    b.g.val(fl, "LastIndex", 8)
    # canto k: k=0 centro; k=1..8 sinais de (k-1) em bits
    km1 = b.op("Subtract_IntInt", (fl, "Index"), 1)
    def sinal(bit):
        v = b.op("And_IntInt", km1, bit)
        s = b.c(KML + "SelectFloat", 0, 0, A=1.0, B=-1.0)
        b.lk(b.op("NotEqual_IntInt", v, 0), s, "bPickA")
        return (s, "ReturnValue")
    eh0 = b.op("EqualEqual_IntInt", (fl, "Index"), 0)
    ext = b.c(KML + "BreakVector", 0, 0)
    b.lk((gb, "BoxExtent"), ext, "InVec")
    mkv = b.c(KML + "MakeVector", 0, 0)
    b.lk(b.op("Multiply_DoubleDouble", (ext, "X"), sinal(4)), mkv, "X")
    b.lk(b.op("Multiply_DoubleDouble", (ext, "Y"), sinal(2)), mkv, "Y")
    b.lk(b.op("Multiply_DoubleDouble", (ext, "Z"), sinal(1)), mkv, "Z")
    offv = b.c(KML + "SelectVector", 0, 0, A="0, 0, 0")
    b.lk((mkv, "ReturnValue"), offv, "B")
    b.lk(eh0, offv, "bPickA")
    pw = b.op("Add_VectorVector", (gb, "Origin"), (offv, "ReturnValue"))
    inv = b.c(KML + "InverseTransformLocation", 0, 0)
    b.lk((gt, "ReturnValue"), inv, "T")
    b.lk(pw, inv, "Location")
    spts = set_arr(b, "ObjPts", b.op("Add_IntInt", b.op("Multiply_IntInt", ix, 9), (fl, "Index")), (inv, "ReturnValue"))
    # posicoes
    fp = b.g.pos(b.ge.add_macro_node(MAC + "ForEachLoop"), 0, 0)
    b.lk(b.v("PosMarcador"), fp, "Array")
    px = (fp, "Array Index")
    bpv = b.br(b.valido((fp, "Array Element")))
    ml = b.c("/Script/Engine.Actor:K2_GetActorLocation", 0, 0)
    b.lk((fp, "Array Element"), ml, "self")
    mr = b.c("/Script/Engine.Actor:K2_GetActorRotation", 0, 0)
    b.lk((fp, "Array Element"), mr, "self")
    casa = get_arr(b, "ObjCasa", get_arr(b, "PosObj", px))
    bkc = b.c(KML + "BreakTransform", 0, 0)
    b.lk(casa, bkc, "InTransform")
    mt = b.c(KML + "MakeTransform", 0, 0)
    b.lk((ml, "ReturnValue"), mt, "Location")
    b.lk((mr, "ReturnValue"), mt, "Rotation")
    b.lk((bkc, "Scale"), mt, "Scale")
    spt = set_arr(b, "PosT", px, (mt, "ReturnValue"))
    z1 = set_arr(b, "PosTroca", px, 0, size=False)
    z2 = set_arr(b, "PosNaoOlha", px, 0, size=False)
    lma = log(b, "ERR_CONFIG", b.s(["pos=", b.is_(px), " MARCADOR_AUSENTE"]))
    tm = b.timer("ErrVigiar", b.v("IntervaloVigia"), loop=True)
    lnobj = b.c(ARR + "Array_Length", 0, 0)
    b.lk(b.v("ObjId"), lnobj, "TargetArray")
    lnpos = b.c(ARR + "Array_Length", 0, 0)
    b.lk(b.v("PosMarcador"), lnpos, "TargetArray")
    lini = log(b, "ERR_INICIO", b.s(["objs=", b.is_((lnobj, "ReturnValue")), " pos=", b.is_((lnpos, "ReturnValue")), " janela=", b.fs(b.v("JanelaPreto"))]))
    b.ch(en, fm, sm, fe)
    b.ch((fe, "LoopBody"), *base_sets)
    b.ch(base_sets[-1], bval)
    b.ch((bval, "else"), sin, lsin)
    b.ch((bval, "then"), bmov)
    b.ch((bmov, "else"), snm, lnm)
    b.ch((bmov, "then"), banx)
    b.ch((banx, "then"), sax, lax)
    b.ch((banx, "else"), scasa, sext, fl)
    b.ch((fl, "LoopBody"), spts)
    b.ch((fe, "Completed"), fp)
    b.ch((fp, "LoopBody"), bpv)
    b.ch((bpv, "then"), spt)
    b.ch((bpv, "else"), z1, z2, lma)
    b.ch((fp, "Completed"), tm, lini)

    # ErrVigiar
    b, en = entrada_log(bp, "ErrVigiar", ME)
    bm = b.br(b.valido(b.v("Manager")))
    fm = b.c(GS + "GetActorOfClass", 0, 0, ActorClass="/Script/Engine.BlueprintGeneratedClass'%s'" % MGR_C)
    sm = b.setv("Manager", src=(fm, "ReturnValue"))
    lcf = log(b, "ERR_CONFIG", "MANAGER_REFEITO")
    bm2 = b.br(b.valido(b.v("Manager")))
    j0 = junc(b)
    pawn = (b.c(GS + "GetPlayerPawn", 0, 0, PlayerIndex=0), "ReturnValue")
    bpaw = b.br(b.valido(pawn))
    att = b.c("/Script/Engine.Actor:GetAttachedActors", 0, 0)
    b.lk(pawn, att, "self")
    sig = b.setv("Ignorar", src=(att, "OutActors"))
    aig = b.c(ARR + "Array_Add", 0, 0)
    b.lk(b.v("Ignorar"), aig, "TargetArray")
    b.lk(pawn, aig, "NewItem")
    blan = b.br(b.valido(b.v("Lanterna")))
    gsp = b.c("/Script/Engine.Actor:GetComponentByClass", 0, 0, ComponentClass="/Script/CoreUObject.Class'/Script/Engine.SpotLightComponent'")
    b.lk(pawn, gsp, "self")
    slan = b.setv("Lanterna", src=(gsp, "ReturnValue"))
    jl = junc(b)
    pl = b.c("/Script/Engine.Actor:K2_GetActorLocation", 0, 0)
    b.lk(pawn, pl, "self")
    vd = b.c(KML + "Vector_Distance", 0, 0)
    b.lk((pl, "ReturnValue"), vd, "V1")
    b.lk(b.v("PawnPrev"), vd, "V2")
    btp = b.br(b.op("Greater_DoubleDouble", (vd, "ReturnValue"), b.v("LimiarTeleporte")))
    stp = b.setv("TempoTeleporte", src=b.now())
    jt = junc(b)
    spp = b.setv("PawnPrev", src=(pl, "ReturnValue"))
    la = loop_atual(b)
    bl = b.br(b.op("NotEqual_IntInt", la, b.v("LoopVisto")))
    res = b.call("ErrResumo")
    slv = b.setv("LoopVisto", src=la)
    stl = b.setv("TempoLoop", src=b.now())
    snl = b.setv("NaoOlhaNoLoop", 0)
    fe = b.g.pos(b.ge.add_macro_node(MAC + "ForEachLoop"), 0, 0)
    b.lk(b.v("ObjId"), fe, "Array")
    ix = (fe, "Array Index")
    r1 = set_arr(b, "ObjMovesLoop", ix, 0)
    r2 = set_arr(b, "ObjVistoLoop", ix, "false")
    r3 = set_arr(b, "ObjPendente", ix, get_arr(b, "ObjValido", ix))
    llo = log(b, "ERR_LOOP", b.s(["loop=", b.is_(b.v("LoopVisto"))]))
    jlp = junc(b)
    arm = b.v("bArmado", cls=MGR_C)
    b.lk(b.v("Manager"), arm[0], "self")
    bga = b.br(b.e(b.v("PrevArmado"), b.nao(arm)))
    stg = b.setv("TempoGatilho", src=b.now())
    jg = junc(b)
    spa = b.setv("PrevArmado", src=arm)
    fe2 = b.g.pos(b.ge.add_macro_node(MAC + "ForEachLoop"), 0, 0)
    b.lk(b.v("ObjId"), fe2, "Array")
    ix2 = (fe2, "Array Index")
    bpend = b.br(b.e(get_arr(b, "ObjPendente", ix2), get_arr(b, "ObjValido", ix2)))
    at = b.call("ErrAplicarTroca")
    b.lk(ix2, at, "i")
    jpe = junc(b)
    bvl = b.br(get_arr(b, "ObjValido", ix2))
    vi = b.call("ErrVisto")
    b.lk(ix2, vi, "i")
    tn = b.call("ErrTentarNaoOlha")
    b.lk(ix2, tn, "i")
    b.ch(en, bm)
    b.ch((bm, "else"), fm, sm, lcf, bm2)
    b.ch((bm2, "then"), j0)
    b.ch((bm, "then"), j0)
    b.ch((j0, "then"), bpaw)
    b.ch((bpaw, "then"), sig, aig, blan)
    b.ch((blan, "else"), slan, jl)
    b.ch((blan, "then"), jl)
    b.ch((jl, "then"), btp)
    b.ch((btp, "then"), stp, jt)
    b.ch((btp, "else"), jt)
    b.ch((jt, "then"), spp, bl)
    b.ch((bl, "then"), res, slv, stl, snl, fe)
    b.ch((fe, "LoopBody"), r1, r2, r3)
    b.ch((fe, "Completed"), llo, jlp)
    b.ch((bl, "else"), jlp)
    b.ch((jlp, "then"), bga)
    b.ch((bga, "then"), stg, jg)
    b.ch((bga, "else"), jg)
    b.ch((jg, "then"), spa, fe2)
    b.ch((fe2, "LoopBody"), bpend)
    b.ch((bpend, "then"), at, jpe)
    b.ch((bpend, "else"), jpe)
    b.ch((jpe, "then"), bvl)
    b.ch((bvl, "then"), vi, tn)

    # API
    b, en = entrada_log(bp, "ErrDefinirAtivo", ME)
    fe = b.g.pos(b.ge.add_macro_node(MAC + "ForEachLoop"), 0, 0)
    b.lk(b.v("ObjId"), fe, "Array")
    b.ch(en, b.setv("bObjetosAtivos", src=(en, "Ativo")), fe)
    b.ch((fe, "LoopBody"), set_arr(b, "ObjPendente", (fe, "Array Index"), "true"))
    b.ch((fe, "Completed"), log(b, "ERR_API", b.s(["ativo=", b.bs((en, "Ativo"))])))
    b, en = entrada_log(bp, "ErrDefinirLoops", ME)
    b.ch(en, b.setv("LoopsPermitidos", src=(en, "Mascara")), log(b, "ERR_API", b.s(["loops=", b.is_((en, "Mascara"))])))
    b, en = entrada_log(bp, "ErrDefinirObjeto", ME)
    b.ch(en, set_arr(b, "ObjAtivo", (en, "i"), (en, "Ativo"), size=False), set_arr(b, "ObjPendente", (en, "i"), "true", size=False),
         log(b, "ERR_API", b.s(["obj=", b.is_((en, "i")), " ativo=", b.bs((en, "Ativo"))])))
    b, en = entrada_log(bp, "ErrForcarMover", ME)
    i = (en, "i")
    bz = b.br(b.op("EqualEqual_IntInt", (en, "N"), 0))
    sdc = b.setv("UltDestino", -1)
    sd0 = b.setv("UltDestino", -2)
    fe = b.g.pos(b.ge.add_macro_node(MAC + "ForEachLoop"), 0, 0)
    b.lk(b.v("PosObj"), fe, "Array")
    cnd = b.e(b.op("EqualEqual_IntInt", (fe, "Array Element"), i), b.op("EqualEqual_IntInt", get_arr(b, "PosN", (fe, "Array Index")), (en, "N")))
    bs_ = b.br(cnd)
    sdi = b.setv("UltDestino", src=(fe, "Array Index"))
    j = junc(b)
    bnd = b.br(b.op("EqualEqual_IntInt", b.v("UltDestino"), -2))
    lnd = log(b, "ERR_SKIP", "FORCADO sem destino")
    selT = b.c(KML + "SelectTransform", 0, 0)
    b.lk(get_arr(b, "ObjCasa", i), selT, "A")
    mx = b.c(KML + "Max", 0, 0, B=0)
    b.lk(b.v("UltDestino"), mx, "A")
    b.lk(get_arr(b, "PosT", (mx, "ReturnValue")), selT, "B")
    b.lk(b.op("EqualEqual_IntInt", b.v("UltDestino"), -1), selT, "bPickA")
    seg = b.call("ErrDestinoSeguro")
    b.lk(i, seg, "i")
    b.lk((selT, "ReturnValue"), seg, "T")
    bseg = b.br(b.v("UltSeguro"))
    mv = b.call("ErrMover", Motivo="FORCADO")
    b.lk(i, mv, "i")
    b.lk(b.v("UltDestino"), mv, "p")
    lsk = log(b, "ERR_SKIP", b.s(["FORCADO ", b.v("UltMotivo")]))
    b.ch(en, bz)
    b.ch((bz, "then"), sdc, j)
    b.ch((bz, "else"), sd0, fe)
    b.ch((fe, "LoopBody"), bs_)
    b.ch((bs_, "then"), sdi)
    b.ch((fe, "Completed"), j)
    b.ch((j, "then"), bnd)
    b.ch((bnd, "then"), lnd)
    b.ch((bnd, "else"), seg, bseg)
    b.ch((bseg, "then"), mv)
    b.ch((bseg, "else"), lsk)
    b, en = entrada_log(bp, "ErrForcarTroca", ME)
    fe = b.g.pos(b.ge.add_macro_node(MAC + "ForEachLoop"), 0, 0)
    b.lk(b.v("ObjId"), fe, "Array")
    b.ch(en, b.setv("TempoTeleporte", src=b.now()), fe)
    b.ch((fe, "LoopBody"), set_arr(b, "ObjPendente", (fe, "Array Index"), "true"))
    b.ch((fe, "Completed"), log(b, "ERR_API", "FORCAR_TROCA"))
    b, en = entrada_log(bp, "ErrMostrarLog", ME)
    ln = b.c(ARR + "Array_Length", 0, 0)
    b.lk(b.v("LogErr"), ln, "TargetArray")
    mx = b.c(KML + "Max", 0, 0, B=0)
    b.lk(b.op("Subtract_IntInt", (ln, "ReturnValue"), 20), mx, "A")
    fl = b.g.pos(b.ge.add_macro_node(MAC + "ForLoop"), 0, 0)
    b.lk((mx, "ReturnValue"), fl, "FirstIndex")
    b.lk(b.op("Subtract_IntInt", (ln, "ReturnValue"), 1), fl, "LastIndex")
    pr = b.c(KSL + "PrintString", 0, 0, bPrintToScreen="true", bPrintToLog="true", Duration=10.0)
    b.lk(get_arr(b, "LogErr", (fl, "Index")), pr, "InString")
    b.ch(en, fl)
    b.ch((fl, "LoopBody"), pr)
    b, en = entrada_log(bp, "ErrLimparLog", ME)
    clr = b.c(ARR + "Array_Clear", 0, 0)
    b.lk(b.v("LogErr"), clr, "TargetArray")
    b.ch(en, clr)
    b, en = entrada_log(bp, "ErrFinalizar", ME)
    b.ch(en, b.call("ErrResumo"), log(b, "ERR_FIM", ""))
    b, en = entrada_log(bp, "ErrDiagVisivel", ME)
    i = (en, "i")
    alvo = get_arr(b, "ObjAlvo", i)
    gt = b.c("/Script/Engine.Actor:GetTransform", 0, 0)
    b.lk(alvo, gt, "self")
    pv = b.call("ErrPontosVisiveis")
    b.lk(i, pv, "i")
    b.lk((gt, "ReturnValue"), pv, "T")

    def diag(rot):
        return log(b, "ERR_DIAG", b.s([rot, " dist=", b.fs(b.v("UltDist")), " dot=", b.fs(b.v("UltDot")), " N_tela=",
                                        b.is_(b.v("UltN")), " N_traco_bloq=", b.is_(b.v("UltNTraco")), " ator=", b.v("UltAtor")]))
    d1 = diag("atual")
    fe = b.g.pos(b.ge.add_macro_node(MAC + "ForEachLoop"), 0, 0)
    b.lk(b.v("PosObj"), fe, "Array")
    bi = b.br(b.op("EqualEqual_IntInt", (fe, "Array Element"), i))
    pv2 = b.call("ErrPontosVisiveis")
    b.lk(i, pv2, "i")
    b.lk(get_arr(b, "PosT", (fe, "Array Index")), pv2, "T")
    d2 = diag("destino")
    b.ch(en, pv, d1, fe)
    b.ch((fe, "LoopBody"), bi)
    b.ch((bi, "then"), pv2, d2)

    # BeginPlay/EndPlay
    w("  build: EventGraph")
    ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
    ge.remove_nodes(list(ge.list_all_nodes()))
    g = G(ge)
    bpl = g.pos(BEL.add_event_override(bp, "ReceiveBeginPlay", unreal.IntPoint(0, 0)), 0, 0)
    g.chain(bpl, g.call(ME + ":ErrInicializar", 300, 0))
    enp = g.pos(BEL.add_event_override(bp, "ReceiveEndPlay", unreal.IntPoint(0, 300)), 0, 300)
    g.chain(enp, g.call(ME + ":ErrFinalizar", 300, 300))
    g.note("LUX objetos errantes v%d (Tools/Loop/add_objetos_errantes.py). Console: ke * ErrMostrarLog | ErrDiagVisivel i | "
           "ErrForcarMover i N | ErrForcarTroca | ErrDefinirAtivo 0/1 | ErrDefinirLoops mascara | ErrFinalizar" % ERR_VERSAO,
           -40, -200, 1200, 700)


def ensure_bp():
    if EAL.does_asset_exist(BPP):
        bp = EAL.load_asset(BPP)
        v = unreal.get_default_object(bp.generated_class()).get_editor_property("ErrVersao")
        if v != ERR_VERSAO:
            raise Aborta("BP_LuxObjetosErrantes existe com ErrVersao=%s (esperado %d): incompleto ou outra versao" % (v, ERR_VERSAO))
        w("BP v%d ja existe: mantido" % ERR_VERSAO)
        return bp, False
    bp = BEL.create_blueprint_asset_with_parent(BPP, unreal.Actor)
    t = tipos()
    ale.cria_vars(bp, VARS, t, "LUX Objetos")
    BEL.compile_blueprint(bp)
    ale.padroes(bp, [(n, tp, e, p) for n, tp, e, p in VARS if p is not None])
    ale.cria_funcoes(bp, FUNCS, t)
    BEL.compile_blueprint(bp)
    build(bp)
    BEL.compile_blueprint(bp)
    e = erros_bp(bp)
    if e:
        raise Aborta("BP_LuxObjetosErrantes com erros/avisos (nada salvo): %s" % e)
    for nome, _ in FUNCS:
        if len(list(BGE.get_graph_editor_by_name(bp, nome).list_all_nodes())) < 2:
            raise Aborta("funcao %s vazia" % nome)
    unreal.get_default_object(bp.generated_class()).set_editor_property("ErrVersao", ERR_VERSAO)
    BEL.compile_blueprint(bp)
    w("BP criado e compilado limpo")
    return bp, True


# ------------------------------------------------------------------ instalar
def hash_plano(p):
    return hashlib.sha256(json.dumps(p, sort_keys=True, default=str).encode()).hexdigest()[:16]


def snap_props(plano):
    out = {}
    for p in plano["papeis"]:
        if not p.get("ator"):
            continue
        a = por_label(p["ator"])
        rc = a.get_editor_property("root_component")
        out[p["ator"]] = {"path": a.get_path_name(), "pacote": a.get_outermost().get_name(),
                          "loc": list(a.get_actor_location().to_tuple()), "rot": list(a.get_actor_rotation().to_tuple()),
                          "mobilidade": str(rc.get_editor_property("mobility")), "tags": [str(t) for t in a.tags],
                          "fisica": rc.is_simulating_physics() if isinstance(rc, unreal.PrimitiveComponent) else False,
                          "colisao": rc.get_collision_profile_name() if isinstance(rc, unreal.PrimitiveComponent) else None,
                          "anexo": a.get_attach_parent_actor().get_actor_label() if a.get_attach_parent_actor() else None}
    ch = por_label("LOOP_Chegada")
    out["LOOP_Chegada"] = {"tags": [str(t) for t in ch.tags]}
    return out


def instalar():
    if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():
        raise Aborta("feche o PIE")
    if sujos():
        raise Aborta("ha pacotes nao salvos: %s" % sujos())
    if not os.path.exists(PLANO):
        raise Aborta("sem plano: rode sondar primeiro")
    plano = json.load(open(PLANO, encoding="utf-8"))
    if plano.get("janela_preto_s") is None:
        raise Aborta("plano sem JanelaPreto")
    papeis = [p for p in plano["papeis"] if p.get("ator") and p.get("slots")]
    for p in papeis:
        if len([a for a in atores() if a.get_actor_label() == p["ator"]]) != 1:
            raise Aborta("label nao unico: %s" % p["ator"])
    os.makedirs(SNAPS, exist_ok=True)
    antes = os.path.join(SNAPS, "antes.json")
    snap = snap_props(plano)
    if os.path.exists(antes):
        old = json.load(open(antes, encoding="utf-8"))
        for k, v in snap.items():
            old.setdefault(k, v)
        snap = old
    with open(antes, "w", encoding="utf-8") as fh:
        json.dump(snap, fh, indent=2, ensure_ascii=False, default=str)
    with open(os.path.join(SNAPS, "antes_%s.json" % time.strftime("%Y%m%d_%H%M%S")), "w", encoding="utf-8") as fh:
        json.dump(snap, fh, indent=2, ensure_ascii=False, default=str)
    bp, criou = ensure_bp()
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    inst = [a for a in atores() if a.get_class().get_name().startswith("BP_LuxObjetosErrantes")]
    if len(inst) > 1:
        raise Aborta("mais de uma instancia do controlador")
    if not inst:
        mgr = por_label("LOOP_Manager")
        c = eas.spawn_actor_from_class(bp.generated_class(), mgr.get_actor_location() + unreal.Vector(0, -150, 300), unreal.Rotator())
        c.set_actor_label("LOOP_ObjetosErrantes")
        c.set_folder_path(FOLDER)
        inst = [c]
    c = inst[0]
    h = hash_plano(plano)
    marcadores = []
    obj_alvo, obj_id, obj_modo, obj_luz = [], [], [], []
    pos_marc, pos_obj, pos_n, pos_troca, pos_nao = [], [], [], [], []
    existentes = {a.get_actor_label(): a for a in atores() if "LUX_POS" in [str(t) for t in a.tags]}
    for i, p in enumerate(papeis):
        a = por_label(p["ator"])
        rc = a.get_editor_property("root_component")
        rc.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
        tags = [str(t) for t in a.tags]
        for t_ in ("LUX_ERRANTE", "ERR_" + p["id"]):
            if t_ not in tags:
                tags.append(t_)
        a.set_editor_property("tags", [unreal.Name(x) for x in tags])
        obj_alvo.append(a)
        obj_id.append(p["id"])
        obj_modo.append(p["modo"])
        obj_luz.append(bool(p.get("precisa_luz")))
        for s in p["slots"]:
            lab = "LUX_POS_%s_%d" % (p["id"], s["N"])
            m = existentes.get(lab)
            if not m:
                m = eas.spawn_actor_from_class(unreal.TargetPoint, unreal.Vector(*s["loc"]), unreal.Rotator(*s["rot"]))
                m.set_actor_label(lab)
                m.set_folder_path(FOLDER)
            m.set_actor_location_and_rotation(unreal.Vector(*s["loc"]), unreal.Rotator(*s["rot"]), False, True)
            mt = ["LUX_POS", "POS_" + p["id"], "N%d" % s["N"]] + s["marcas"]
            m.set_editor_property("tags", [unreal.Name(x) for x in mt])
            troca = sum(1 << int(x[1:]) for x in s["marcas"] if x.startswith("L"))
            nao = sum(1 << int(x[1:]) for x in s["marcas"] if x.startswith("V"))
            pos_marc.append(m)
            pos_obj.append(i)
            pos_n.append(s["N"])
            pos_troca.append(troca)
            pos_nao.append(nao)
            marcadores.append(lab)
    ch = por_label("LOOP_Chegada")
    tch = [str(t) for t in ch.tags]
    if "LUX_CHEGADA" not in tch:
        ch.set_editor_property("tags", [unreal.Name(x) for x in tch + ["LUX_CHEGADA"]])
    if c.get_editor_property("ErrPlanoHash") != h:
        n = len(papeis)
        for k, v in (("ObjAlvo", obj_alvo), ("ObjId", obj_id), ("ObjModo", obj_modo), ("ObjMaxPorLoop", [1] * n),
                     ("ObjAtivo", [True] * n), ("ObjVoltaCasa", [False] * n), ("ObjPrecisaLuz", obj_luz),
                     ("PosMarcador", pos_marc), ("PosObj", pos_obj), ("PosN", pos_n), ("PosTroca", pos_troca), ("PosNaoOlha", pos_nao),
                     ("Portas", [a for a in atores() if "Door" in a.get_class().get_name()]), ("PortaLoop", por_label("LOOP_PortaSala")),
                     ("Chegada", ch), ("JanelaPreto", float(plano["janela_preto_s"])), ("ErrPlanoHash", h)):
            c.set_editor_property(k, v)
        w("arrays do LOOP_ObjetosErrantes gravados (hash %s)" % h)
    else:
        w("plano sem mudanca (hash %s): arrays mantidos" % h)
    f = verificar(plano)
    if f:
        raise Aborta("verificar FAIL (nada salvo): %s" % f)
    esperado = {BPP, "/Game/Masion/Mapa_B"}
    extra = set(sujos()) - esperado
    if extra:
        raise Aborta("pacotes sujos inesperados: %s" % sorted(extra))
    if criou or BPP in sujos():
        w("salvo BP:", EAL.save_loaded_asset(bp, False))
    U = unreal.EditorLoadingAndSavingUtils
    mapa = [p for p in U.get_dirty_map_packages() if p.get_name() == "/Game/Masion/Mapa_B"]
    if mapa:
        w("salvo Mapa_B:", U.save_packages(mapa, True))
    with open(os.path.join(SNAPS, "depois.json"), "w", encoding="utf-8") as fh:
        json.dump(snap_props(plano), fh, indent=2, ensure_ascii=False, default=str)
    if sujos():
        raise Aborta("ainda ha pacotes sujos: %s" % sujos())
    w("instalado: %d objetos, marcadores %s" % (len(papeis), marcadores))


# ------------------------------------------------------------------ verificar
def simular(plano):
    """Conta ERR_MOVE por loop: trocas (marcas L) no inicio do loop e 'nao olhou' (marcas V) depois de visto."""
    papeis = [p for p in plano["papeis"] if p.get("ator") and p.get("slots")]
    pos = {p["id"]: 0 for p in papeis}
    loops_mov = {p["id"]: set() for p in papeis}
    res = {}
    for L in range(1, 6):
        moves = []
        oculto = 0
        for p in papeis:
            for s in p["slots"]:
                if "L%d" % L in s["marcas"] and p["modo"] != 1 and pos[p["id"]] != s["N"]:
                    moves.append((p["id"], "TROCA_OCULTO", pos[p["id"]], s["N"]))
                    pos[p["id"]] = s["N"]
                    loops_mov[p["id"]].add(L)
        for p in papeis:
            for s in p["slots"]:
                if "V%d" % L in s["marcas"] and p["modo"] != 0 and pos[p["id"]] != s["N"] and oculto < 1:
                    moves.append((p["id"], "NAO_OLHOU", pos[p["id"]], s["N"]))
                    pos[p["id"]] = s["N"]
                    oculto += 1
                    loops_mov[p["id"]].add(L)
        res[L] = {"moves": moves, "posicoes": dict(pos)}
    return res, loops_mov


def verificar(plano=None):
    falhas = []
    plano = plano or (json.load(open(PLANO, encoding="utf-8")) if os.path.exists(PLANO) else None)
    if not plano:
        return ["sem plano"]
    if not EAL.does_asset_exist(BPP):
        return ["BP ausente"]
    bp = EAL.load_asset(BPP)
    e = erros_bp(bp)
    if e:
        falhas.append("compilacao: %s" % e)
    cdo = unreal.get_default_object(bp.generated_class())
    if cdo.get_editor_property("ErrVersao") != ERR_VERSAO and BPP not in sujos():
        falhas.append("ErrVersao != %d" % ERR_VERSAO)
    g = [str(x) for x in BEL.list_graph_names(bp)]
    for nome, _ in FUNCS:
        if nome not in g or len(list(BGE.get_graph_editor_by_name(bp, nome).list_all_nodes())) < 2:
            falhas.append("funcao %s ausente/vazia" % nome)
    inst = [a for a in atores() if a.get_class().get_name().startswith("BP_LuxObjetosErrantes")]
    if len(inst) != 1:
        falhas.append("esperava 1 LOOP_ObjetosErrantes (%d)" % len(inst))
    else:
        c = inst[0]
        arrs = {k: list(c.get_editor_property(k)) for k in ("ObjAlvo", "ObjId", "ObjModo", "ObjMaxPorLoop", "ObjAtivo", "ObjVoltaCasa", "ObjPrecisaLuz")}
        if len(set(len(v) for v in arrs.values())) != 1:
            falhas.append("arrays por objeto com tamanhos diferentes")
        parr = {k: list(c.get_editor_property(k)) for k in ("PosMarcador", "PosObj", "PosN", "PosTroca", "PosNaoOlha")}
        if len(set(len(v) for v in parr.values())) != 1:
            falhas.append("arrays por posicao com tamanhos diferentes")
        if any(x is None for x in arrs["ObjAlvo"] + parr["PosMarcador"]) or not c.get_editor_property("Chegada") or not c.get_editor_property("PortaLoop"):
            falhas.append("referencia nula no controlador")
        if list(c.get_editor_property("Bits")) != [1, 2, 4, 8, 16, 32]:
            falhas.append("Bits errados")
        for idx, oid in enumerate(arrs["ObjId"]):
            alv = [a for a in atores() if "ERR_" + oid in [str(t) for t in a.tags]]
            if len(alv) != 1:
                falhas.append("ERR_%s -> %d atores" % (oid, len(alv)))
            else:
                a = alv[0]
                if str(a.get_editor_property("root_component").get_editor_property("mobility")).find("MOVABLE") < 0:
                    falhas.append("%s nao e Movable" % a.get_actor_label())
                if any(str(t).startswith("LOOP") for t in a.tags):
                    falhas.append("%s tem tag LOOP" % a.get_actor_label())
        vistos = set()
        for m, n, o in zip(parr["PosMarcador"], parr["PosN"], parr["PosObj"]):
            k = (arrs["ObjId"][o], n)
            if k in vistos:
                falhas.append("POS_%s N%d repetido" % k)
            vistos.add(k)
    sim, loops_mov = simular(plano)
    for L, r in sim.items():
        n = len(r["moves"])
        oc = len([m for m in r["moves"] if m[1] == "NAO_OLHOU"])
        if n > 3 or oc > 1:
            falhas.append("loop %d: %d moves (%d ocultos)" % (L, n, oc))
        w("simulacao loop %d: moves=%s posicoes=%s" % (L, r["moves"], r["posicoes"]))
    for pid, ls in loops_mov.items():
        if len(ls) > 2:
            falhas.append("%s muda em %d loops" % (pid, len(ls)))
    return falhas


def desfazer():
    antes = os.path.join(SNAPS, "antes.json")
    if not os.path.exists(antes):
        w("nada a desfazer")
        return
    snap = json.load(open(antes, encoding="utf-8"))
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    n = 0
    for lab, s in snap.items():
        a = por_label(lab)
        if not a:
            continue
        if lab == "LOOP_Chegada":
            a.set_editor_property("tags", [unreal.Name(x) for x in s["tags"]])
            continue
        tags = [str(t) for t in a.tags]
        a.set_editor_property("tags", [unreal.Name(x) for x in tags if x not in ("LUX_ERRANTE",) and not x.startswith("ERR_")])
        rc = a.get_editor_property("root_component")
        if "STATIC" in s["mobilidade"]:
            rc.set_editor_property("mobility", unreal.ComponentMobility.STATIC)
        n += 1
    for a in [a for a in atores() if "LUX_POS" in [str(t) for t in a.tags] or a.get_class().get_name().startswith("BP_LuxObjetosErrantes")]:
        eas.destroy_actor(a)
    if EAL.does_asset_exist(BPP):
        bp = EAL.load_asset(BPP)
        unreal.get_default_object(bp.generated_class()).set_editor_property("bObjetosAtivos", False)
        BEL.compile_blueprint(bp)
        EAL.save_loaded_asset(bp, False)
    U = unreal.EditorLoadingAndSavingUtils
    U.save_packages([p for p in U.get_dirty_map_packages() if p.get_name() == "/Game/Masion/Mapa_B"], True)
    os.rename(antes, antes + ".desfeito_%s" % time.strftime("%Y%m%d_%H%M%S"))
    w("desfeito: %d props restaurados (mobilidade/tags), marcadores e controlador removidos" % n)


def main():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    open(LOG, "w", encoding="utf-8").close()
    modo = next((a for a in sys.argv[1:] if a in ("sondar", "instalar", "verificar", "desfazer")), "sondar")
    w("modo:", modo)
    try:
        if modo == "verificar":
            f = verificar()
            w("verificar:", ("FAIL %s" % f) if f else "PASS")
        else:
            {"sondar": sondar, "instalar": instalar, "desfazer": desfazer}[modo]()
    except Aborta as ex:
        w("ABORTADO:", ex, "| sujos:", sujos())
    except Exception:
        w("ERRO " + traceback.format_exc(), "| sujos:", sujos())


if __name__ == "__main__":
    main()
