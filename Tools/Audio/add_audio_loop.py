# LUX_AUDIO v1 - audio por loop (itens 2 e 3): coracao (MetaSound), vento e faixas Backrooms, escalando do loop 1 ao 5.
# Ator BP_LuxAudioLoop (som 2D). Nao mexe no manager, portas, gatilho, PedirTroca, BP_Player_Cowboy, PPV nem setup_loop.py.
#   py "<projeto>/Tools/Audio/add_audio_loop.py" sondar | instalar [--confirmar-backrooms] | verificar | desfazer
# O ator le o LoopAtual do LOOP_Manager a cada 0,25 s (timer, sem Tick) e faz fades. Console (PIE):
#   ke * DefinirEstimulosAudio true true true | ke * TestarLoopAudio 5 | ke * PararAudio | ke * RetomarAudio |
#   ke * ReaplicarAudio | ke * MostrarRegistroAudio
import hashlib, importlib, json, os, sys, traceback, unreal

VERSAO = 1
EAL, BEL, BGE = unreal.EditorAssetLibrary, unreal.BlueprintEditorLibrary, unreal.BlueprintGraphEditor
DIR = "/Game/Masion/LUX/Audio"
BPP = DIR + "/BP_LuxAudioLoop"
BP_C = BPP + ".BP_LuxAudioLoop_C"
MGR = "/Game/Masion/LUX/Loop/BP_LuxLoopManager"
MGR_C = MGR + ".BP_LuxLoopManager_C"
CORACAO = "/Game/Procedural_Hearbeat/Heartbeat/MS_Procedural_Hearbeat"
VENTO = "/Game/FPMovement/Assets/Audio/Environment/SW_Wind_calm"
# loop -> faixa (escala do mais leve ao mais pesado; troque no Details do BP, variavel BackroomsCue)
BACKROOMS = {2: "5_LOOP_Backrooms_Memories__by_juanjo_sound__", 3: "7_LOOP_Backrooms_Mirage__by_juanjo_sound__",
             4: "4_LOOP_Backrooms_Stalker__by_juanjo_sound__", 5: "8_LOOP_Broken_Backrooms_Portal__by_juanjo_sound__"}
PARAM, TIPO = "Pulse", "bpm"          # MS_Procedural_Hearbeat: entrada Float 'Pulse' -> BPMToSeconds -> TriggerRepeat
RITMO = [70.0, 78.0, 90.0, 102.0, 116.0]
KSL, KML, GS, ARR = ("/Script/Engine.KismetSystemLibrary:", "/Script/Engine.KismetMathLibrary:",
                     "/Script/Engine.GameplayStatics:", "/Script/Engine.KismetArrayLibrary:")
STR, TXT, AC = "/Script/Engine.KismetStringLibrary:", "/Script/Engine.KismetTextLibrary:", "/Script/Engine.AudioComponent:"
MAC = "/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:"
AQUI = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(os.path.dirname(AQUI))
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
LOG = os.path.join(SAVED, "Audio", "audio_log.txt")
sys.path.insert(0, os.path.join(PROJ, "Tools", "Loop"))
import add_door_slam as ads
importlib.reload(ads)
G, ok_pin = ads.G, ads.ok_pin


def w(*a):
    line = " ".join(str(x) for x in a)
    unreal.log("[LUX audio] " + line)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


class Aborta(Exception):
    pass


def sujos():
    U = unreal.EditorLoadingAndSavingUtils
    return sorted(p.get_name() for p in list(U.get_dirty_map_packages()) + list(U.get_dirty_content_packages()))


def atores():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()


def hash_loop():
    pasta = os.path.join(PROJ, "Content", "Masion", "LUX", "Loop")
    h = hashlib.sha256()
    for raiz, _, arqs in sorted(os.walk(pasta)):
        for a in sorted(arqs):
            if a.endswith(".uasset"):
                with open(os.path.join(raiz, a), "rb") as fh:
                    h.update(a.encode() + fh.read())
    return h.hexdigest()


def cue_backrooms(nome):
    """Usa a cue se o WavePlayer dela ja estiver em loop; senao o WAV LOOP (Looping ligado) do pacote."""
    cue = EAL.load_asset("/Game/Backrooms_Ambience/Cues/%sCue" % nome)
    try:
        fn = cue.get_editor_property("first_node")
        if isinstance(fn, unreal.SoundNodeWavePlayer) and fn.get_editor_property("looping"):
            return cue, "cue em loop"
    except Exception:
        pass
    wav = EAL.load_asset("/Game/Backrooms_Ambience/WAVs/%swav" % nome)
    if wav and wav.get_editor_property("looping"):
        return wav, "WAV com Looping (a cue nao tem WavePlayer em loop)"
    raise Aborta("nem a cue nem o WAV de %s tocam em loop" % nome)


# ------------------------------------------------------------------ sondar
def sondar():
    out = {}
    ms = EAL.load_asset(CORACAO)
    sub = unreal.get_editor_subsystem(unreal.MetaSoundEditorSubsystem)
    b = sub.find_or_begin_building(ms)[0]
    nomes = b.get_graph_input_names()[0]
    ent = []
    for nome in nomes:
        r = b.find_graph_input_node(nome)
        outs = b.find_node_outputs(r[0])[0]
        lit = b.get_graph_input_default(nome)[0]
        ent.append({"nome": str(nome), "tipo": str(r[1]), "constructor": [b.get_node_output_is_constructor_pin(h) for h in outs],
                    "default": lit.export_text() if hasattr(lit, "export_text") else str(lit)})
    out["coracao"] = {"entradas": ent, "oneshot": b.interface_is_declared("UE.Source.OneShot"),
                      "duration": ms.get_editor_property("duration")}
    v = EAL.load_asset(VENTO)
    out["vento"] = {"looping": v.get_editor_property("looping"), "duration": v.get_editor_property("duration")}
    out["backrooms"] = {}
    for loop, nome in BACKROOMS.items():
        snd, como = cue_backrooms(nome)
        out["backrooms"][loop] = {"asset": snd.get_path_name(), "como": como, "duration": round(snd.get_editor_property("duration"), 1)}
    mgrs = [a for a in atores() if a.get_class().get_name().startswith("BP_LuxLoopManager")]
    out["manager"] = {"instancias": len(mgrs), "LoopFinal": mgrs[0].get_editor_property("LoopFinal") if mgrs else None}
    out["sujos"] = sujos()
    with open(os.path.join(AQUI, "audio_probe.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False, default=str)
    w("sondagem:", json.dumps(out, ensure_ascii=False, default=str))
    return out


# ------------------------------------------------------------------ tipos e variaveis
def tipos():
    t = {k: BEL.get_basic_type_by_name(k) for k in ("bool", "int", "real", "string", "name")}
    snd = BEL.get_object_reference_type(unreal.SoundBase.static_class())
    t.update({"int[]": BEL.get_array_type(t["int"]), "real[]": BEL.get_array_type(t["real"]), "string[]": BEL.get_array_type(t["string"]),
              "snd": snd, "snd[]": BEL.get_array_type(snd),
              "mgr": BEL.get_object_reference_type(EAL.load_asset(MGR).generated_class()),
              "timer": BEL.get_struct_type(unreal.TimerHandle.static_struct())})
    return t


def lista_vars(cues):
    return [  # nome, tipo, editavel, padrao
        ("bCoracaoAtivo", "bool", True, True), ("bVentoAtivo", "bool", True, True), ("bBackroomsAtivo", "bool", True, True),
        ("LoopsCoracao", "int[]", True, [1, 2, 3, 4, 5]), ("LoopsVento", "int[]", True, [1, 2, 3, 4, 5]),
        ("LoopsBackrooms", "int[]", True, [2, 3, 4, 5]),
        ("CoracaoVolume", "real[]", True, [.12, .16, .21, .28, .36]), ("VentoVolume", "real[]", True, [.10, .13, .17, .22, .28]),
        ("BackroomsVolume", "real[]", True, [0.0, .10, .14, .19, .25]), ("VentoPitch", "real[]", True, [.92, .96, 1.0, 1.05, 1.10]),
        ("BackroomsCue", "snd[]", True, cues), ("CoracaoRitmo", "real[]", True, RITMO),
        ("CoracaoPitch", "real[]", True, [1.0, 1.04, 1.08, 1.13, 1.18]), ("NomeParamCoracao", "name", True, PARAM),
        ("CoracaoTipo", "string", True, TIPO),
        ("GanhoCoracao", "real", True, 1.0), ("GanhoVento", "real", True, 1.0), ("GanhoBackrooms", "real", True, 1.0),
        ("GanhoMestre", "real", True, 1.0), ("VolumeMax", "real", True, 0.6),
        ("TempoInicio", "real", True, 3.0), ("TempoVolume", "real", True, 4.0), ("TempoCrossfade", "real", True, 6.0),
        ("TempoParada", "real", True, 3.0), ("VelPitch", "real", True, 0.04), ("VelRitmo", "real", True, 0.06 * RITMO[0]),
        ("LoopForcado", "int", True, 0), ("bDebugAudio", "bool", True, False),
        ("Manager", "mgr", False, None), ("LoopAplicado", "int", False, 0), ("LoopCalc", "int", False, 0),
        ("bIniciado", "bool", False, False), ("bParado", "bool", False, False), ("bAvisouManager", "bool", False, False),
        ("bCoracaoTocando", "bool", False, False), ("bVentoTocando", "bool", False, False), ("iBackAtivo", "int", False, 0),
        ("CueAtual", "snd", False, None), ("CueAlvo", "snd", False, None),
        ("CoracaoAtual", "real", False, 0.0), ("CoracaoAlvo", "real", False, 0.0), ("VentoAtual", "real", False, 1.0),
        ("VentoAlvo", "real", False, 1.0), ("RegistroAudio", "string[]", False, []), ("TimerAudio", "timer", False, None),
        ("VersaoAudio", "int", False, 0)]


FUNCOES = [  # nome, parametros
    ("Registrar", [("E", "string"), ("D", "string")]), ("RegistrarConfig", [("E", "string")]), ("ResolverManager", []),
    ("AplicarRitmo", [("Valor", "real")]), ("AplicarCoracao", [("L", "int"), ("T", "real")]),
    ("AplicarVento", [("L", "int"), ("T", "real")]), ("AplicarBackrooms", [("L", "int"), ("T", "real")]),
    ("AplicarLoop", [("L", "int"), ("T", "real")]), ("Rampas", [("dt", "real")]), ("Vigia", []), ("VerificarLoop", []),
    ("Fn_Iniciar", []), ("Fn_Encerrar", []), ("DefinirEstimulosAudio", [("C", "bool"), ("V", "bool"), ("B", "bool")]),
    ("ReaplicarAudio", []), ("TestarLoopAudio", [("L", "int")]), ("PararAudio", []), ("RetomarAudio", []),
    ("MostrarRegistroAudio", [])]


# ------------------------------------------------------------------ componentes
COMPS = ("AC_Coracao", "AC_Vento", "AC_BackroomsA", "AC_BackroomsB")


def add_comps(bp):
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    raiz = sds.k2_gather_subobject_data_for_blueprint(bp)[0]
    sons = {"AC_Coracao": EAL.load_asset(CORACAO), "AC_Vento": EAL.load_asset(VENTO), "AC_BackroomsA": None, "AC_BackroomsB": None}
    for nome in COMPS:
        h, _ = sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=raiz, new_class=unreal.AudioComponent, blueprint_context=bp))
        sds.rename_subobject(h, unreal.Text(nome))
        c = lib.get_object_for_blueprint(lib.get_data(h), bp)
        configura_comp(c, sons[nome])


def configura_comp(c, som):
    c.set_editor_property("sound", som)
    c.set_editor_property("auto_activate", False)
    c.set_editor_property("allow_spatialization", False)
    c.set_editor_property("override_attenuation", True)
    at = c.get_editor_property("attenuation_overrides")
    at.set_editor_property("attenuate", False)
    at.set_editor_property("spatialize", False)
    c.set_editor_property("attenuation_overrides", at)
    c.set_editor_property("is_ui_sound", False)
    c.set_editor_property("override_priority", True)
    c.set_editor_property("priority", 10.0)
    c.set_editor_property("volume_multiplier", 1.0)
    c.set_editor_property("pitch_multiplier", 1.0)


def comps_do_template(bp):
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    out = {}
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        o = lib.get_object_for_blueprint(lib.get_data(h), bp)
        if isinstance(o, unreal.AudioComponent):
            out[o.get_name().replace("_GEN_VARIABLE", "")] = o
    return out


# ------------------------------------------------------------------ grafo
class B:
    """Atalhos de nos sobre o G do add_door_slam (strings, tabelas, volumes, registro)."""

    def __init__(self, ge):
        self.g = G(ge)
        self.ge = ge

    def s(self, partes, x, y):
        """concatena partes: str literal ou (no, pino) -> (no, 'ReturnValue')"""
        acc = None
        for p in partes:
            a = self.g.call(STR + "Concat_StrStr", x, y)
            x += 30
            if acc is None:
                self.g.val(a, "A", "")
            else:
                self.g.link(acc[0], acc[1], a, "A")
            if isinstance(p, str):
                self.g.val(a, "B", p)
            else:
                self.g.link(p[0], p[1], a, "B")
            acc = (a, "ReturnValue")
        return acc

    def num(self, src, x, y):
        c = self.g.call(STR + "Conv_DoubleToString", x, y)
        self.g.link(src[0], src[1], c, "InDouble")
        return (c, "ReturnValue")

    def int_s(self, src, x, y):
        c = self.g.call(STR + "Conv_IntToString", x, y)
        self.g.link(src[0], src[1], c, "InInt")
        return (c, "ReturnValue")

    def bool_s(self, src, x, y):
        c = self.g.call(STR + "Conv_BoolToString", x, y)
        self.g.link(src[0], src[1], c, "InBool")
        return (c, "ReturnValue")

    def var(self, nome, x, y, cls=""):
        return (self.g.get(nome, x, y, cls), nome)

    def tab(self, arr, L, x, y):
        """arr[Clamp(L,1,Len)-1]"""
        g = self.g
        ln = g.call(ARR + "Array_Length", x, y + 80)
        g.link(*self.var(arr, x - 200, y + 80), ln, "TargetArray")
        cl = g.call(KML + "Clamp", x + 200, y + 40)
        g.link(L[0], L[1], cl, "Value")
        g.val(cl, "Min", 1)
        g.link(ln, "ReturnValue", cl, "Max")
        sub = g.call(KML + "Subtract_IntInt", x + 400, y + 40)
        g.link(cl, "ReturnValue", sub, "A")
        g.val(sub, "B", 1)
        get = g.call(ARR + "Array_Get", x + 600, y)
        g.link(*self.var(arr, x + 400, y - 60), get, "TargetArray")
        g.link(sub, "ReturnValue", get, "Index")
        return (get, "Item")

    def mul(self, a, b, x, y):
        m = self.g.call(KML + "Multiply_DoubleDouble", x, y)
        self.g.link(a[0], a[1], m, "A")
        self.g.link(b[0], b[1], m, "B")
        return (m, "ReturnValue")

    def vol(self, tabela, ganho, L, x, y):
        t = self.tab(tabela, L, x, y)
        v = self.mul(self.mul(t, self.var(ganho, x + 600, y + 160), x + 800, y), self.var("GanhoMestre", x + 800, y + 160), x + 1000, y)
        mn = self.g.call(KML + "FMin", x + 1200, y)
        self.g.link(v[0], v[1], mn, "A")
        self.g.link(*self.var("VolumeMax", x + 1000, y + 200), mn, "B")
        return (mn, "ReturnValue")

    def gt(self, a, lim, x, y):
        n = self.g.call(KML + "Greater_DoubleDouble", x, y)
        self.g.link(a[0], a[1], n, "A")
        self.g.val(n, "B", lim)
        return (n, "ReturnValue")

    def e(self, a, b, x, y):
        n = self.g.call(KML + "BooleanAND", x, y)
        self.g.link(a[0], a[1], n, "A")
        self.g.link(b[0], b[1], n, "B")
        return (n, "ReturnValue")

    def nao(self, a, x, y):
        n = self.g.call(KML + "Not_PreBool", x, y)
        self.g.link(a[0], a[1], n, "A")
        return (n, "ReturnValue")

    def contem(self, arr, item, x, y):
        n = self.g.call(ARR + "Array_Contains", x, y)
        self.g.link(*self.var(arr, x - 200, y), n, "TargetArray")
        self.g.link(item[0], item[1], n, "ItemToFind")
        return (n, "ReturnValue")

    def br(self, cond, x, y):
        b = self.g.branch(x, y)
        self.g.link(cond[0], cond[1], b, "Condition")
        return b

    def reg(self, E, D, x, y):
        n = self.g.call(BP_C + ":Registrar", x, y)
        self.g.val(n, "E", E)
        if isinstance(D, str):
            if D:
                self.g.val(n, "D", D)
        else:
            self.g.link(D[0], D[1], n, "D")
        return n

    def comp_call(self, comp, fn, x, y, **vals):
        n = self.g.call(AC + fn, x, y, **vals)
        self.g.link(*self.var(comp, x - 200, y + 150), n, "self")
        return n

    def call(self, fn, x, y, **vals):
        return self.g.call(BP_C + ":" + fn, x, y, **vals)

    def setv(self, nome, x, y, valor=None, src=None):
        n = self.g.set(nome, x, y, valor)
        if src:
            self.g.link(src[0], src[1], n, nome)
        return n


def entry(bp, nome):
    fe = BGE.get_graph_editor_by_name(bp, nome)
    return fe, fe.find_graph_entry_pin().get_owning_node()


def ep(en, pin):
    return (en, pin)


def build_functions(bp):
    t = tipos()
    for nome, params in FUNCOES:
        fe = BGE.create_and_edit_function_graph(bp, nome)
        if fe.get_graph().get_name() != nome:
            raise Aborta("grafo %s criado como %s" % (nome, fe.get_graph().get_name()))
        for pn, pt in params:
            fe.add_graph_input_parameter(pn, t[pt])
    BEL.compile_blueprint(bp)

    # Registrar(E, D)
    fe, en = entry(bp, "Registrar")
    b = B(fe)
    utc = b.g.call(KML + "UtcNow", 200, 300)
    asdt = b.g.call(TXT + "AsDateTime_DateTime", 400, 300)
    b.g.link(utc, "ReturnValue", asdt, "In")
    t2s = b.g.call(TXT + "Conv_TextToString", 600, 300)
    b.g.link(asdt, "ReturnValue", t2s, "InText")
    s = b.s(["UTC=", (t2s, "ReturnValue"), " | jogo=", b.num((b.g.call(GS + "GetTimeSeconds", 200, 400), "ReturnValue"), 400, 400),
             " | real=", b.num((b.g.call(GS + "GetRealTimeSeconds", 200, 480), "ReturnValue"), 400, 480),
             " | loop=", b.int_s(b.var("LoopAplicado", 200, 560), 400, 560), " | ", ep(en, "E"), " | ", ep(en, "D")], 800, 300)
    add = b.g.call(ARR + "Array_Add", 1400, 0)
    b.g.link(*b.var("RegistroAudio", 1200, 120), add, "TargetArray")
    b.g.link(s[0], s[1], add, "NewItem")
    pr = b.g.call(KSL + "PrintString", 1700, 0, bPrintToLog="true", Duration=5.0)
    b.g.link(s[0], s[1], pr, "InString")
    b.g.link(*b.var("bDebugAudio", 1500, 200), pr, "bPrintToScreen")
    b.g.chain(en, add, pr)

    # RegistrarConfig(E)
    fe, en = entry(bp, "RegistrarConfig")
    b = B(fe)
    y = 300
    partes = []
    for i, v in enumerate(("bCoracaoAtivo", "bVentoAtivo", "bBackroomsAtivo")):
        partes += [" %s=" % v[1:2], b.bool_s(b.var(v, 200, y + i * 60), 400, y + i * 60)]
    for i, v in enumerate(("GanhoCoracao", "GanhoVento", "GanhoBackrooms", "GanhoMestre", "VolumeMax")):
        partes += [" %s=" % v, b.num(b.var(v, 200, y + 200 + i * 60), 400, y + 200 + i * 60)]
    partes += [" forcado=", b.int_s(b.var("LoopForcado", 200, y + 520), 400, y + 520)]
    nm = b.g.call(STR + "Conv_NameToString", 400, y + 580)
    b.g.link(*b.var("NomeParamCoracao", 200, y + 580), nm, "InName")
    partes += [" param=", (nm, "ReturnValue"), " tipo=", b.var("CoracaoTipo", 400, y + 640)]
    s = b.s(partes, 800, y)
    r = b.g.call(BP_C + ":Registrar", 1500, 0)
    b.g.link(en, "E", r, "E")
    b.g.link(s[0], s[1], r, "D")
    b.g.chain(en, r)

    # ResolverManager
    fe, en = entry(bp, "ResolverManager")
    b = B(fe)
    ok = b.g.call(KSL + "IsValid", 200, 200)
    b.g.link(*b.var("Manager", 0, 200), ok, "Object")
    br = b.br((ok, "ReturnValue"), 300, 0)
    find = b.g.call(GS + "GetActorOfClass", 550, 100, ActorClass="/Script/Engine.BlueprintGeneratedClass'%s'" % MGR_C)
    sm = b.setv("Manager", 850, 100, src=(find, "ReturnValue"))
    b.g.chain(en, br)
    b.g.chain((br, "else"), find, sm)

    # AplicarRitmo(Valor): sem parametro no MetaSound -> pitch
    fe, en = entry(bp, "AplicarRitmo")
    b = B(fe)
    eqn = b.g.call(KML + "EqualEqual_NameName", 200, 200)
    b.g.link(*b.var("NomeParamCoracao", 0, 200), eqn, "A")
    b.g.val(eqn, "B", "None")
    br = b.br((eqn, "ReturnValue"), 400, 0)
    sp = b.comp_call("AC_Coracao", "SetPitchMultiplier", 700, -150)
    b.g.link(en, "Valor", sp, "NewPitchMultiplier")
    sf = b.comp_call("AC_Coracao", "SetFloatParameter", 700, 150)
    b.g.link(*b.var("NomeParamCoracao", 500, 300), sf, "InName")
    b.g.link(en, "Valor", sf, "InFloat")
    b.g.chain(en, br)
    b.g.chain((br, "then"), sp)
    b.g.chain((br, "else"), sf)

    # AplicarCoracao / AplicarVento
    for camada in ("Coracao", "Vento"):
        fe, en = entry(bp, "Aplicar" + camada)
        b = B(fe)
        L, T = ep(en, "L"), ep(en, "T")
        on = b.e(b.e(b.var("b%sAtivo" % camada, 200, 200), b.contem("Loops" + camada, L, 400, 260), 600, 200),
                 b.gt(b.tab(camada + "Volume", L, 200, 400), 0.001, 1000, 400), 1200, 200)
        v = b.vol(camada + "Volume", "Ganho" + camada, L, 200, 700)
        if camada == "Coracao":
            eqn = b.g.call(KML + "EqualEqual_NameName", 1400, 1100)
            b.g.link(*b.var("NomeParamCoracao", 1200, 1100), eqn, "A")
            b.g.val(eqn, "B", "None")
            sel = b.g.call(KML + "SelectFloat", 1600, 1000)
            b.g.link(*b.tab("CoracaoPitch", L, 200, 1000), sel, "A")
            b.g.link(*b.tab("CoracaoRitmo", L, 200, 1200), sel, "B")
            b.g.link(eqn, "ReturnValue", sel, "bPickA")
            alvo = (sel, "ReturnValue")
        else:
            alvo = b.tab("VentoPitch", L, 200, 1000)
        s_alvo = b.setv(camada + "Alvo", 300, 0, src=alvo)
        b_on = b.br(on, 600, 0)
        b_toc = b.br(b.var("b%sTocando" % camada, 700, -200), 900, -300)
        # entra
        if camada == "Coracao":
            aplica = b.call("AplicarRitmo", 1200, -600)
            b.g.link(*b.var("CoracaoAlvo", 1000, -500), aplica, "Valor")
        else:
            aplica = b.comp_call("AC_Vento", "SetPitchMultiplier", 1200, -600)
            b.g.link(*b.var("VentoAlvo", 1000, -500), aplica, "NewPitchMultiplier")
        s_at = b.setv(camada + "Atual", 1500, -600, src=b.var(camada + "Alvo", 1300, -450))
        fi = b.comp_call("AC_" + camada, "FadeIn", 1800, -600, StartTime=0.0, FadeCurve="Linear")
        b.g.link(T[0], T[1], fi, "FadeInDuration")
        b.g.link(v[0], v[1], fi, "FadeVolumeLevel")
        s_toc = b.setv("b%sTocando" % camada, 2100, -600, "true")
        det = b.s(["v=", b.num(v, 2100, -300), " T=", b.num(T, 2100, -250), " alvo=", b.num(b.var(camada + "Alvo", 1900, -200), 2100, -200),
                   " tipo=", b.var("CoracaoTipo", 2100, -150)], 2300, -300)
        r_on = b.reg(camada.upper() + "_ON", det, 2400, -600)
        # ja tocando: ajusta volume
        adj = b.comp_call("AC_" + camada, "AdjustVolume", 1200, -100, FadeCurve="Linear")
        b.g.link(T[0], T[1], adj, "AdjustVolumeDuration")
        b.g.link(v[0], v[1], adj, "AdjustVolumeLevel")
        r_adj = b.reg(camada.upper(), det, 1500, -100)
        # sai
        b_toc2 = b.br(b.var("b%sTocando" % camada, 700, 300), 900, 300)
        fo = b.comp_call("AC_" + camada, "FadeOut", 1200, 300, FadeVolumeLevel=0.0, FadeCurve="Linear")
        b.g.link(*b.var("TempoParada", 1000, 450), fo, "FadeOutDuration")
        s_off = b.setv("b%sTocando" % camada, 1500, 300, "false")
        r_off = b.reg(camada.upper() + "_OFF", "", 1800, 300)
        b.g.chain(en, s_alvo, b_on)
        b.g.chain((b_on, "then"), b_toc)
        b.g.chain((b_toc, "else"), aplica, s_at, fi, s_toc, r_on)
        b.g.chain((b_toc, "then"), adj, r_adj)
        b.g.chain((b_on, "else"), b_toc2)
        b.g.chain((b_toc2, "then"), fo, s_off, r_off)

    # AplicarBackrooms(L, T): crossfade entre AC_BackroomsA e AC_BackroomsB
    fe, en = entry(bp, "AplicarBackrooms")
    b = B(fe)
    L, T = ep(en, "L"), ep(en, "T")
    v = b.vol("BackroomsVolume", "GanhoBackrooms", L, 200, 900)
    cond = b.e(b.e(b.var("bBackroomsAtivo", 200, 200), b.contem("LoopsBackrooms", L, 400, 260), 600, 200), b.gt(v, 0.001, 1600, 900), 1800, 200)
    b_c = b.br(cond, 300, 0)
    s_cue = b.setv("CueAlvo", 600, -150, src=b.tab("BackroomsCue", L, 300, -500))
    s_none = b.setv("CueAlvo", 600, 150)
    eq = b.g.call(KML + "EqualEqual_ObjectObject", 800, 300)
    b.g.link(*b.var("CueAlvo", 600, 300), eq, "A")
    b.g.link(*b.var("CueAtual", 600, 380), eq, "B")
    b_igual = b.br((eq, "ReturnValue"), 900, 0)

    def ativo_zero(x, y):
        z = b.g.call(KML + "EqualEqual_IntInt", x, y + 150)
        b.g.link(*b.var("iBackAtivo", x - 200, y + 150), z, "A")
        b.g.val(z, "B", 0)
        return b.br((z, "ReturnValue"), x, y)

    def valido(nome, x, y):
        ok = b.g.call(KSL + "IsValid", x, y + 150)
        b.g.link(*b.var(nome, x - 200, y + 150), ok, "Object")
        return b.br((ok, "ReturnValue"), x, y)

    # mesma faixa: so ajusta o volume da ativa
    i_val = valido("CueAlvo", 1200, -400)
    z1 = ativo_zero(1450, -400)
    adjA = b.comp_call("AC_BackroomsA", "AdjustVolume", 1750, -500, FadeCurve="Linear")
    adjB = b.comp_call("AC_BackroomsB", "AdjustVolume", 1750, -300, FadeCurve="Linear")
    for n in (adjA, adjB):
        b.g.link(*b.var("TempoVolume", 1550, -200), n, "AdjustVolumeDuration")
        b.g.link(v[0], v[1], n, "AdjustVolumeLevel")
    # troca: sai a ativa, entra a outra
    a_val = valido("CueAtual", 1200, 200)
    z2 = ativo_zero(1450, 200)
    foA = b.comp_call("AC_BackroomsA", "FadeOut", 1750, 100, FadeVolumeLevel=0.0, FadeCurve="SCurve")
    foB = b.comp_call("AC_BackroomsB", "FadeOut", 1750, 300, FadeVolumeLevel=0.0, FadeCurve="SCurve")
    for n in (foA, foB):
        b.g.link(T[0], T[1], n, "FadeOutDuration")
    n_val = valido("CueAlvo", 2100, 200)
    z3 = ativo_zero(2350, 200)
    trilhas = {}
    for lado, y in (("B", 100), ("A", 400)):   # iBackAtivo == 0 -> ativa e A -> entra B
        st = b.comp_call("AC_Backrooms" + lado, "Stop", 2650, y)
        ss = b.comp_call("AC_Backrooms" + lado, "SetSound", 2900, y)
        b.g.link(*b.var("CueAlvo", 2750, y + 150), ss, "NewSound")
        fi = b.comp_call("AC_Backrooms" + lado, "FadeIn", 3150, y, StartTime=0.0, FadeCurve="Sin")
        b.g.link(T[0], T[1], fi, "FadeInDuration")
        b.g.link(v[0], v[1], fi, "FadeVolumeLevel")
        b.g.chain(st, ss, fi)
        trilhas[lado] = (st, fi)
    sub = b.g.call(KML + "Subtract_IntInt", 3400, 450)
    b.g.link(*b.var("iBackAtivo", 3200, 500), sub, "B")  # liga antes: o operador promovivel so tipa depois
    b.g.val(sub, "A", 1)
    s_i = b.setv("iBackAtivo", 3500, 250, src=(sub, "ReturnValue"))
    nomes = []
    for nome, y in (("CueAtual", 700), ("CueAlvo", 800)):
        dn = b.g.call(KSL + "GetDisplayName", 3600, y)
        b.g.link(*b.var(nome, 3400, y), dn, "Object")
        nomes.append((dn, "ReturnValue"))
    det = b.s([nomes[0], " -> ", nomes[1], " v=", b.num(v, 3800, 900), " T=", b.num(T, 3800, 950)], 4000, 700)
    r = b.reg("BACKROOMS", det, 3800, 250)
    s_at = b.setv("CueAtual", 4100, 250, src=b.var("CueAlvo", 3900, 400))
    b.g.chain(en, b_c)
    b.g.chain((b_c, "then"), s_cue, b_igual)
    b.g.chain((b_c, "else"), s_none, b_igual)
    b.g.chain((b_igual, "then"), i_val)
    b.g.chain((i_val, "then"), z1)
    b.g.chain((z1, "then"), adjA)
    b.g.chain((z1, "else"), adjB)
    b.g.chain((b_igual, "else"), a_val)
    b.g.chain((a_val, "then"), z2)
    b.g.chain((z2, "then"), foA, n_val)
    b.g.chain((z2, "else"), foB, n_val)
    b.g.chain((a_val, "else"), n_val)
    b.g.chain((n_val, "then"), z3)
    b.g.chain((z3, "then"), trilhas["B"][0])
    b.g.chain((z3, "else"), trilhas["A"][0])
    b.g.chain(trilhas["B"][1], s_i)
    b.g.chain(trilhas["A"][1], s_i)
    b.g.chain(s_i, r)
    b.g.chain((n_val, "else"), r)
    b.g.chain(r, s_at)

    # AplicarLoop(L, T)
    fe, en = entry(bp, "AplicarLoop")
    b = B(fe)
    c1 = b.call("AplicarCoracao", 300, 0)
    c2 = b.call("AplicarVento", 600, 0)
    c3 = b.call("AplicarBackrooms", 900, 0)
    for n in (c1, c2):
        b.g.link(en, "L", n, "L")
        b.g.link(en, "T", n, "T")
    b.g.link(en, "L", c3, "L")
    b.g.link(*b.var("TempoCrossfade", 700, 200), c3, "T")
    b.g.chain(en, c1, c2, c3)

    # Rampas(dt)
    fe, en = entry(bp, "Rampas")
    b = B(fe)
    ants = []
    for i, camada in enumerate(("Coracao", "Vento")):
        y = i * 700
        ne = b.g.call(KML + "NearlyEqual_FloatFloat", 400, y + 200, ErrorTolerance=0.001)
        b.g.link(*b.var(camada + "Atual", 200, y + 200), ne, "A")
        b.g.link(*b.var(camada + "Alvo", 200, y + 280), ne, "B")
        br = b.br(b.e(b.var("b%sTocando" % camada, 400, y + 100), b.nao((ne, "ReturnValue"), 600, y + 200), 800, y + 100), 900, y)
        fi = b.g.call(KML + "FInterpTo_Constant", 1100, y + 200)
        b.g.link(*b.var(camada + "Atual", 900, y + 200), fi, "Current")
        b.g.link(*b.var(camada + "Alvo", 900, y + 280), fi, "Target")
        b.g.link(en, "dt", fi, "DeltaTime")
        if camada == "Coracao":
            eqn = b.g.call(KML + "EqualEqual_NameName", 900, y + 420)
            b.g.link(*b.var("NomeParamCoracao", 700, y + 420), eqn, "A")
            b.g.val(eqn, "B", "None")
            sel = b.g.call(KML + "SelectFloat", 1000, y + 360)
            b.g.link(*b.var("VelPitch", 800, y + 340), sel, "A")
            b.g.link(*b.var("VelRitmo", 800, y + 380), sel, "B")
            b.g.link(eqn, "ReturnValue", sel, "bPickA")
            b.g.link(sel, "ReturnValue", fi, "InterpSpeed")
        else:
            b.g.link(*b.var("VelPitch", 900, y + 360), fi, "InterpSpeed")
        s = b.setv(camada + "Atual", 1400, y, src=(fi, "ReturnValue"))
        if camada == "Coracao":
            ap = b.call("AplicarRitmo", 1700, y)
            b.g.link(*b.var("CoracaoAtual", 1500, y + 150), ap, "Valor")
        else:
            ap = b.comp_call("AC_Vento", "SetPitchMultiplier", 1700, y)
            b.g.link(*b.var("VentoAtual", 1500, y + 150), ap, "NewPitchMultiplier")
        b.g.chain((br, "then"), s, ap)
        ants.append((br, ap))
    b.g.chain(en, ants[0][0])
    b.g.chain(ants[0][1], ants[1][0])
    b.g.chain((ants[0][0], "else"), ants[1][0])

    # Vigia: camada que deveria tocar e parou -> volta
    fe, en = entry(bp, "Vigia")
    b = B(fe)
    anterior = (en, "then")
    for i, (camada, comp, cond_var, tabela, ganho) in enumerate((
            ("coracao", "AC_Coracao", "bCoracaoTocando", "CoracaoVolume", "GanhoCoracao"),
            ("vento", "AC_Vento", "bVentoTocando", "VentoVolume", "GanhoVento"),
            ("backroomsA", "AC_BackroomsA", None, "BackroomsVolume", "GanhoBackrooms"),
            ("backroomsB", "AC_BackroomsB", None, "BackroomsVolume", "GanhoBackrooms"))):
        y = i * 900
        ip = b.g.call(AC + "IsPlaying", 400, y + 200)
        b.g.link(*b.var(comp, 200, y + 200), ip, "self")
        if cond_var:
            deve = b.var(cond_var, 400, y + 100)
        else:  # a faixa ativa e a que tem o som atual: A se iBackAtivo == 1 depois da troca? ativa = (iBackAtivo==1 ? B : A)
            z = b.g.call(KML + "EqualEqual_IntInt", 300, y + 300)
            b.g.link(*b.var("iBackAtivo", 100, y + 300), z, "A")
            b.g.val(z, "B", 0 if camada == "backroomsA" else 1)
            ok = b.g.call(KSL + "IsValid", 300, y + 400)
            b.g.link(*b.var("CueAtual", 100, y + 400), ok, "Object")
            deve = b.e((z, "ReturnValue"), (ok, "ReturnValue"), 500, y + 350)
        br = b.br(b.e(deve, b.nao((ip, "ReturnValue"), 600, y + 200), 800, y + 100), 900, y)
        v = b.vol(tabela, ganho, b.var("LoopAplicado", 900, y + 500), 1000, y + 500)
        fi = b.comp_call(comp, "FadeIn", 1300, y, FadeInDuration=1.0, StartTime=0.0, FadeCurve="Linear")
        b.g.link(v[0], v[1], fi, "FadeVolumeLevel")
        r = b.reg("REINICIO", camada, 1600, y)
        b.g.link(anterior[0], anterior[1], br, "execute")
        b.g.chain((br, "then"), fi, r)
        prox = b.g.branch(1900, y + 300)  # juncao: Branch(true) que so repassa para a proxima camada
        b.g.val(prox, "Condition", "true")
        b.g.chain(r, prox)
        b.g.chain((br, "else"), prox)
        anterior = (prox, "then")

    # VerificarLoop (timer de 0,25 s)
    fe, en = entry(bp, "VerificarLoop")
    b = B(fe)
    b_par = b.br(b.var("bParado", 100, 200), 250, 0)
    rm = b.call("ResolverManager", 500, 0)
    okm = b.g.call(KSL + "IsValid", 700, 200)
    b.g.link(*b.var("Manager", 500, 200), okm, "Object")
    b_m = b.br((okm, "ReturnValue"), 800, 0)
    b_av = b.br(b.var("bAvisouManager", 900, 400), 1000, 300)
    s_av = b.setv("bAvisouManager", 1250, 300, "true")
    r_aus = b.reg("MANAGER_AUSENTE", "", 1500, 300)
    gt0 = b.g.call(KML + "Greater_IntInt", 1100, 250)
    b.g.link(*b.var("LoopForcado", 900, 250), gt0, "A")
    b.g.val(gt0, "B", 0)
    la = b.g.get("LoopAtual", 1100, 350, MGR_C)
    b.g.link(*b.var("Manager", 900, 350), la, "self")
    sel = b.g.call(KML + "SelectInt", 1300, 200)
    b.g.link(*b.var("LoopForcado", 1100, 150), sel, "A")
    b.g.link(la, "LoopAtual", sel, "B")
    b.g.link(gt0, "ReturnValue", sel, "bPickA")
    cl = b.g.call(KML + "Clamp", 1500, 200, Min=1, Max=5)
    b.g.link(sel, "ReturnValue", cl, "Value")
    s_lc = b.setv("LoopCalc", 1100, 0, src=(cl, "ReturnValue"))
    b_ini = b.br(b.var("bIniciado", 1300, 150), 1400, 0)
    s_ini = b.setv("bIniciado", 1650, -300, "true")
    s_la = b.setv("LoopAplicado", 1900, -300, src=b.var("LoopCalc", 1700, -150))
    rc = b.call("RegistrarConfig", 2150, -300, E="INICIO")
    al1 = b.call("AplicarLoop", 2400, -300)
    b.g.link(*b.var("LoopCalc", 2200, -150), al1, "L")
    b.g.link(*b.var("TempoInicio", 2200, -100), al1, "T")
    ne = b.g.call(KML + "NotEqual_IntInt", 1600, 250)
    b.g.link(*b.var("LoopCalc", 1400, 250), ne, "A")
    b.g.link(*b.var("LoopAplicado", 1400, 330), ne, "B")
    b_mud = b.br((ne, "ReturnValue"), 1700, 100)
    det = b.s([b.int_s(b.var("LoopAplicado", 1800, 400), 2000, 400), " -> ", b.int_s(b.var("LoopCalc", 1800, 460), 2000, 460)], 2200, 400)
    r_mud = b.reg("LOOP_MUDOU", det, 1950, 100)
    s_la2 = b.setv("LoopAplicado", 2200, 100, src=b.var("LoopCalc", 2000, 250))
    al2 = b.call("AplicarLoop", 2450, 100)
    b.g.link(*b.var("LoopCalc", 2250, 250), al2, "L")
    b.g.link(*b.var("TempoVolume", 2250, 300), al2, "T")
    rp = b.call("Rampas", 2750, 0, dt=0.25)
    vg = b.call("Vigia", 3000, 0)
    b.g.chain(en, b_par)
    b.g.chain((b_par, "else"), rm, b_m)
    b.g.chain((b_m, "else"), b_av)
    b.g.chain((b_av, "else"), s_av, r_aus)
    b.g.chain((b_m, "then"), s_lc, b_ini)
    b.g.chain((b_ini, "else"), s_ini, s_la, rc, al1, rp)
    b.g.chain((b_ini, "then"), b_mud)
    b.g.chain((b_mud, "then"), r_mud, s_la2, al2, rp)
    b.g.chain((b_mud, "else"), rp)
    b.g.chain(rp, vg)

    # Fn_Iniciar / Fn_Encerrar
    fe, en = entry(bp, "Fn_Iniciar")
    b = B(fe)
    r = b.reg("BEGINPLAY", "", 250, 0)
    rm = b.call("ResolverManager", 500, 0)
    tm = b.g.call(KSL + "K2_SetTimer", 750, 0, FunctionName="VerificarLoop", Time=0.25, bLooping="true")
    s_t = b.setv("TimerAudio", 1050, 0, src=(tm, "ReturnValue"))
    b.g.chain(en, r, rm, tm, s_t)
    fe, en = entry(bp, "Fn_Encerrar")
    b = B(fe)
    ct = b.g.call(KSL + "K2_ClearAndInvalidateTimerHandle", 250, 0)
    b.g.link(*b.var("TimerAudio", 50, 200), ct, "Handle")
    r = b.reg("ENDPLAY", "", 550, 0)
    b.g.chain(en, ct, r)

    # comandos de console
    def reaplicar(b, x, y):
        cond = b.e(b.var("bIniciado", x, y + 200), b.nao(b.var("bParado", x, y + 280), x + 200, y + 280), x + 400, y + 200)
        br = b.br(cond, x + 500, y)
        al = b.call("AplicarLoop", x + 800, y)
        b.g.link(*b.var("LoopAplicado", x + 600, y + 150), al, "L")
        b.g.link(*b.var("TempoVolume", x + 600, y + 200), al, "T")
        b.g.chain((br, "then"), al)
        return br

    fe, en = entry(bp, "DefinirEstimulosAudio")
    b = B(fe)
    ss = [b.setv(v, 250 + i * 250, 0) for i, v in enumerate(("bCoracaoAtivo", "bVentoAtivo", "bBackroomsAtivo"))]
    for n, p, v in zip(ss, ("C", "V", "B"), ("bCoracaoAtivo", "bVentoAtivo", "bBackroomsAtivo")):
        b.g.link(en, p, n, v)
    rc = b.call("RegistrarConfig", 1000, 0, E="SWITCH")
    br = reaplicar(b, 1250, 0)
    b.g.chain(en, ss[0], ss[1], ss[2], rc, br)

    fe, en = entry(bp, "ReaplicarAudio")
    b = B(fe)
    rc = b.call("RegistrarConfig", 250, 0, E="REAPLICAR")
    br = reaplicar(b, 500, 0)
    b.g.chain(en, rc, br)

    fe, en = entry(bp, "TestarLoopAudio")
    b = B(fe)
    s = b.setv("LoopForcado", 250, 0)
    b.g.link(en, "L", s, "LoopForcado")
    r = b.reg("TESTE_LOOP", b.int_s(ep(en, "L"), 300, 200), 500, 0)
    b.g.chain(en, s, r)

    fe, en = entry(bp, "PararAudio")
    b = B(fe)
    s = b.setv("bParado", 250, 0, "true")
    fos = []
    for i, c in enumerate(COMPS):
        fo = b.comp_call(c, "FadeOut", 500 + i * 250, 0, FadeVolumeLevel=0.0, FadeCurve="Linear")
        b.g.link(*b.var("TempoParada", 400 + i * 250, 200), fo, "FadeOutDuration")
        fos.append(fo)
    s1 = b.setv("bCoracaoTocando", 1600, 0, "false")
    s2 = b.setv("bVentoTocando", 1850, 0, "false")
    s3 = b.setv("CueAtual", 2100, 0)
    r = b.reg("PARAR", "", 2350, 0)
    b.g.chain(en, s, *fos)
    b.g.chain(fos[-1], s1, s2, s3, r)

    fe, en = entry(bp, "RetomarAudio")
    b = B(fe)
    s1 = b.setv("bParado", 250, 0, "false")
    s2 = b.setv("bIniciado", 500, 0, "false")
    r = b.reg("RETOMAR", "", 750, 0)
    b.g.chain(en, s1, s2, r)

    fe, en = entry(bp, "MostrarRegistroAudio")
    b = B(fe)
    ln = b.g.call(ARR + "Array_Length", 200, 200)
    b.g.link(*b.var("RegistroAudio", 0, 200), ln, "TargetArray")
    sub = b.g.call(KML + "Subtract_IntInt", 400, 200)
    b.g.link(ln, "ReturnValue", sub, "A")
    b.g.val(sub, "B", 20)
    mx = b.g.call(KML + "Max", 600, 200, B=0)
    b.g.link(sub, "ReturnValue", mx, "A")
    last = b.g.call(KML + "Subtract_IntInt", 400, 300)
    b.g.link(ln, "ReturnValue", last, "A")
    b.g.val(last, "B", 1)
    fl = b.g.pos(fe.add_macro_node(MAC + "ForLoop"), 800, 0)
    b.g.link(mx, "ReturnValue", fl, "FirstIndex")
    b.g.link(last, "ReturnValue", fl, "LastIndex")
    get = b.g.call(ARR + "Array_Get", 1000, 200)
    b.g.link(*b.var("RegistroAudio", 800, 300), get, "TargetArray")
    b.g.link(fl, "Index", get, "Index")
    pr = b.g.call(KSL + "PrintString", 1200, 0, bPrintToScreen="true", bPrintToLog="true", Duration=10.0)
    b.g.link(get, "Item", pr, "InString")
    b.g.chain(en, fl)
    b.g.chain((fl, "LoopBody"), pr)


def build_stubs(bp):
    ge = BGE.get_graph_editor_by_name(bp, "EventGraph")
    ge.remove_nodes(list(ge.list_all_nodes()))  # BP novo: tira os fantasmas; so os 2 stubs ficam
    g = G(ge)
    bpl = g.pos(BEL.add_event_override(bp, "ReceiveBeginPlay", unreal.IntPoint(0, 0)), 0, 0)
    ini = g.call(BP_C + ":Fn_Iniciar", 300, 0)
    g.chain(bpl, ini)
    enp = g.pos(BEL.add_event_override(bp, "ReceiveEndPlay", unreal.IntPoint(0, 300)), 0, 300)
    fim = g.call(BP_C + ":Fn_Encerrar", 300, 300)
    g.chain(enp, fim)
    g.note("LUX_AUDIO v%d (Tools/Audio/add_audio_loop.py): BeginPlay liga um timer de 0,25 s (VerificarLoop) que le o LoopAtual "
           "do LOOP_Manager e ajusta coracao, vento e Backrooms. Nada aqui usa Tick" % VERSAO, -40, -160, 900, 600)


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


# ------------------------------------------------------------------ instalar / verificar / desfazer
def instalar():
    if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():
        raise Aborta("feche o PIE")
    if sujos():
        raise Aborta("ha pacotes nao salvos: %s" % sujos())
    if "--confirmar-backrooms" not in sys.argv:
        raise Aborta("rode com --confirmar-backrooms (mapa loop->faixa: %s)" % BACKROOMS)
    probe = sondar()
    h0 = hash_loop()
    alteracoes = []
    cues = [None] + [unreal.load_asset(probe["backrooms"][L]["asset"]) for L in (2, 3, 4, 5)]
    if EAL.does_asset_exist(BPP):
        bp = EAL.load_asset(BPP)
        cdo = unreal.get_default_object(bp.generated_class())
        if cdo.get_editor_property("VersaoAudio") != VERSAO:
            raise Aborta("BP_LuxAudioLoop existe numa versao diferente; rode 'desfazer' antes (nao apago funcoes com o BP carregado)")
        w("BP_LuxAudioLoop ja na versao %d: mantido" % VERSAO)
    else:
        if not EAL.does_directory_exist(DIR):
            EAL.make_directory(DIR)
        bp = BEL.create_blueprint_asset_with_parent(BPP, unreal.Actor)
        add_comps(bp)
        t = tipos()
        vs = lista_vars(cues)
        for nome, tp, ed, _ in vs:
            BEL.add_member_variable(bp, nome, t[tp])
            BEL.set_blueprint_variable_instance_editable(bp, nome, ed)
            BEL.set_blueprint_variable_category(bp, nome, unreal.Text("LUX Audio" if ed else "LUX Audio|Estado"))
        BEL.compile_blueprint(bp)
        cdo = unreal.get_default_object(bp.generated_class())
        for nome, tp, _, pad in vs:
            if pad is not None and pad != []:
                cdo.set_editor_property(nome, pad)
        build_functions(bp)
        build_stubs(bp)
        BEL.compile_blueprint(bp)
        unreal.get_default_object(bp.generated_class()).set_editor_property("VersaoAudio", VERSAO)
        BEL.compile_blueprint(bp)
        alteracoes.append("BP_LuxAudioLoop criado")
    e = erros_bp(bp)
    if e:
        raise Aborta("BP_LuxAudioLoop nao compilou limpo (nada salvo): %s" % e)
    if "BP_LuxAudioLoop criado" in alteracoes:
        w("salvo BP:", EAL.save_loaded_asset(bp, False))
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    ja = [a for a in atores() if a.get_class().get_name().startswith("BP_LuxAudioLoop")]
    if not ja:
        mgr = [a for a in atores() if a.get_class().get_name().startswith("BP_LuxLoopManager")][0]
        try:
            a = eas.spawn_actor_from_class(bp.generated_class(), mgr.get_actor_location() + unreal.Vector(0, 150, 150), unreal.Rotator())
            a.set_actor_label("AUDIO_LuxLoop")
            a.set_folder_path("LUX/Audio")
        except Exception:
            for x in [x for x in atores() if x.get_class().get_name().startswith("BP_LuxAudioLoop")]:
                eas.destroy_actor(x)
            raise
        alteracoes.append("AUDIO_LuxLoop colocado")
    extra = set(sujos()) - {BPP, "/Game/Masion/Mapa_B"}
    if extra:
        raise Aborta("pacotes sujos inesperados: %s" % sorted(extra))
    U = unreal.EditorLoadingAndSavingUtils
    mapa = [p for p in U.get_dirty_map_packages() if p.get_name() == "/Game/Masion/Mapa_B"]
    if mapa:
        w("salvo Mapa_B:", U.save_packages(mapa, True))
    h1 = hash_loop()
    if h0 != h1:
        raise Aborta("FAIL: os assets de /Game/Masion/LUX/Loop mudaram (hash)")
    man = {"versao": VERSAO, "bp": BPP, "ator": "AUDIO_LuxLoop", "param": PARAM, "tipo": TIPO, "ritmo": RITMO,
           "backrooms": {L: probe["backrooms"][L] for L in (2, 3, 4, 5)}, "vento": VENTO, "hash_loop": h1,
           "alteracoes": alteracoes}
    with open(os.path.join(AQUI, "audio_loop_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(man, fh, indent=2, ensure_ascii=False, default=str)
    w("alteracoes:", alteracoes or "0 alteracoes")
    f = verificar(h0)
    w("verificar:", f or "PASS")


def verificar(h0=None):
    falhas = []
    if not EAL.does_asset_exist(BPP):
        return ["BP_LuxAudioLoop ausente"]
    bp = EAL.load_asset(BPP)
    e = erros_bp(bp)
    if e:
        falhas.append("compilacao: %s" % e)
    comps = comps_do_template(bp)
    for c in COMPS:
        o = comps.get(c)
        if not o:
            falhas.append("componente %s ausente" % c)
            continue
        at = o.get_editor_property("attenuation_overrides")
        if o.get_editor_property("auto_activate") or o.get_editor_property("allow_spatialization") or at.get_editor_property("spatialize"):
            falhas.append("flags de %s" % c)
    cdo = unreal.get_default_object(bp.generated_class())
    for nome in ("CoracaoVolume", "VentoVolume", "BackroomsVolume", "VentoPitch", "BackroomsCue", "CoracaoRitmo", "CoracaoPitch"):
        if len(cdo.get_editor_property(nome)) != 5:
            falhas.append("%s nao tem 5 itens" % nome)
    for nome in ("VentoPitch", "CoracaoPitch"):
        if not all(0.85 <= v <= 1.25 for v in cdo.get_editor_property(nome)):
            falhas.append("%s fora de 0.85..1.25" % nome)
    for nome, g in (("CoracaoVolume", "GanhoCoracao"), ("VentoVolume", "GanhoVento"), ("BackroomsVolume", "GanhoBackrooms")):
        if max(cdo.get_editor_property(nome)) * cdo.get_editor_property(g) * cdo.get_editor_property("GanhoMestre") > cdo.get_editor_property("VolumeMax") + 1e-6:
            falhas.append("%s passa do VolumeMax" % nome)
    ritmo = list(cdo.get_editor_property("CoracaoRitmo"))
    if not all(50 <= v <= 130 for v in ritmo) or ritmo != sorted(ritmo) or len(set(ritmo)) != 5:
        falhas.append("CoracaoRitmo fora de 50..130 BPM ou nao acelera: %s" % ritmo)
    for i, c in enumerate(cdo.get_editor_property("BackroomsCue")):
        if i > 0 and (not c or c.get_editor_property("duration") <= 0):
            falhas.append("BackroomsCue[%d] invalida" % i)
    vento = EAL.load_asset(VENTO)
    if not vento.get_editor_property("looping"):
        falhas.append("vento sem looping")
    graficos = [str(x) for x in BEL.list_graph_names(bp)]
    for nome, _ in FUNCOES:
        if nome not in graficos:
            falhas.append("funcao %s ausente" % nome)
    audios = [a for a in atores() if a.get_class().get_name().startswith("BP_LuxAudioLoop")]
    if len(audios) != 1:
        falhas.append("esperava 1 AUDIO_LuxLoop (%d)" % len(audios))
    elif audios[0].get_editor_property("LoopForcado") != 0 or audios[0].get_editor_property("bDebugAudio"):
        falhas.append("instancia com LoopForcado/bDebugAudio alterados")
    if len([a for a in atores() if a.get_class().get_name().startswith("BP_LuxLoopManager")]) != 1:
        falhas.append("esperava 1 BP_LuxLoopManager")
    if h0 and hash_loop() != h0:
        falhas.append("hash de /Game/Masion/LUX/Loop mudou")
    if sujos():
        falhas.append("pacotes sujos: %s" % sujos())
    w("valores: ritmo %s (%s, param %s) | pitch coracao %s | volumes coracao %s vento %s backrooms %s | faixas %s" % (
        ritmo, cdo.get_editor_property("CoracaoTipo"), cdo.get_editor_property("NomeParamCoracao"),
        list(cdo.get_editor_property("CoracaoPitch")), list(cdo.get_editor_property("CoracaoVolume")),
        list(cdo.get_editor_property("VentoVolume")), list(cdo.get_editor_property("BackroomsVolume")),
        [c.get_name() if c else None for c in cdo.get_editor_property("BackroomsCue")]))
    return falhas


def desfazer():
    if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():
        raise Aborta("feche o PIE")
    if EAL.does_asset_exist(BPP):
        unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(EAL.load_asset(BPP))
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in [a for a in atores() if a.get_class().get_name().startswith("BP_LuxAudioLoop")]:
        eas.destroy_actor(a)
    U = unreal.EditorLoadingAndSavingUtils
    U.save_packages([p for p in U.get_dirty_map_packages() if p.get_name() == "/Game/Masion/Mapa_B"], True)
    unreal.SystemLibrary.collect_garbage()
    if EAL.does_asset_exist(BPP):
        w("BP apagado:", EAL.delete_asset(BPP))


def main():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    open(LOG, "w", encoding="utf-8").close()
    modo = next((a for a in sys.argv[1:] if a in ("sondar", "instalar", "verificar", "desfazer")), "sondar")
    w("modo:", modo, "| argv:", sys.argv[1:])
    try:
        {"sondar": sondar, "instalar": instalar, "desfazer": desfazer,
         "verificar": lambda: w("verificar:", verificar() or "PASS")}[modo]()
    except Aborta as ex:
        w("ABORTADO:", ex, "| sujos:", sujos())
    except Exception:
        w("ERRO " + traceback.format_exc(), "| sujos:", sujos())


if __name__ == "__main__":
    main()
