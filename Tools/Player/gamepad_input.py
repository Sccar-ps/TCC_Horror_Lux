# LUX: suporte a controle (Xbox e PlayStation) - ETAPA 1: so dados de entrada (Enhanced Input). Nenhum Blueprint e editado.
# Pedido do Gabriel (01/10/2026): conectar o gamepad as acoes JA existentes, sem quebrar teclado e mouse.
#
# O que faz (idempotente; so grava o que mudar):
#  1) IMC_Default (FPMovement, compartilhado com o Mapa_A): so ADICIONA mapeamentos de gamepad as acoes existentes
#       IA_Interact  <- Gamepad_FaceButton_Bottom   (A / Cross)
#       IA_Crouch    <- Gamepad_FaceButton_Right    (B / Circle)       alterna (ToggleCrouching? = true), como o C
#       IA_Flashlight<- Gamepad_FaceButton_Left     (X / Square)       a vela: puxar e guardar (o F)
#       IA_Inspect   <- Gamepad_FaceButton_Top      (Y / Triangle)
#       IA_Zoom      <- Gamepad_LeftTriggerAxis     (LT / L2)          segurar (Started liga, Completed desliga), como o botao direito
#     IA_Move e IA_Look ja tinham Left2D e Right2D: aqui so se acerta a zona morta (0,2 -> 0,25 radial, teto 0,95) e o Look do
#     gamepad ganha ScaleByDeltaTime x 60, que mantem EXATAMENTE a velocidade de hoje a 60 FPS e a torna independente do FPS
#     (sem isso o giro era 2,5 graus por QUADRO: 150 graus/s a 60 FPS, 75 a 30 e 360 a 144). O x50 do IA_Move fica: o analogico
#     satura na velocidade de caminhada igual as teclas (D09: a velocidade do jogo e desenho, nao deve variar por dispositivo).
#     NAO mapeia IA_Sprint nem IA_Jump (D09, decisao do Gabriel de 27/09: sem corrida e sem pulo). Mapear so no gamepad religaria
#     a corrida so para quem joga de controle.
#     Teclado e mouse ficam IDENTICOS: o verificar compara com o snapshot (Tools/Player/gamepad_input_original.json).
#  2) Acoes novas em /Game/Masion/LUX/Entrada (todas Boolean, gatilho Pressed, rodam em pausa, nao consomem a tecla):
#       IA_Pausa (Menu/Start/Options, Esc, P), IA_UI_Confirmar (A/Cross, Enter, Espaco), IA_UI_Voltar (B/Circle, Backspace),
#       IA_UI_Anterior (LB/L1, D-Pad esq., stick esq., seta esq.), IA_UI_Proximo (RB/R1, D-Pad dir., stick dir., seta dir.),
#       IA_UI_Alternar (Y/Triangle, Tab: troca o estilo dos icones Auto/Xbox/PlayStation no pause).
#  3) IMC_LuxEntrada com esses mapeamentos (o componente BP_LuxEntrada, etapa 3, o registra no BeginPlay com prioridade 1).
#     Os botoes A/B/Y repetem os do jogo DE PROPOSITO: as acoes de UI so agem com o pause ou uma janela aberta (guarda no
#     componente) e nao consomem a tecla, entao o gameplay nao muda. O verificar lista toda tecla repetida entre os contextos.
#   py "<projeto>/Tools/Player/gamepad_input.py" sondar|instalar|verificar|desfazer
import json, os, sys, traceback
import unreal

EAL = unreal.EditorAssetLibrary
IMC = "/Game/FPMovement/Player/Input/IMC_Default"
IA_DIR = "/Game/FPMovement/Player/Input/Actions"
DIR = "/Game/Masion/LUX/Entrada"
IMC_LUX = DIR + "/IMC_LuxEntrada"
AQUI = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(AQUI, "gamepad_input_original.json")
LOG = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "LuxSnapshots", "gamepad_input_log.txt")

# gamepad nas acoes que ja existem (acao -> tecla)
GAMEPAD = (("IA_Interact", "Gamepad_FaceButton_Bottom"), ("IA_Crouch", "Gamepad_FaceButton_Right"), ("IA_Flashlight", "Gamepad_FaceButton_Left"),
           ("IA_Inspect", "Gamepad_FaceButton_Top"), ("IA_Zoom", "Gamepad_LeftTriggerAxis"))
# nunca no gamepad (D09)
PROIBIDAS = ("IA_Sprint", "IA_Jump")
ZONA = {"lower": 0.25, "upper": 0.95}   # radial; antes 0,2 / 1,0 (padrao do modificador). Microsoft recomenda 0,24 (esq.) e 0,265 (dir.)
LOOK_ESCALA = 60.0                      # ScaleByDeltaTime x 60: 1 quadro a 60 FPS = o valor de hoje
# acoes novas: nome -> (descricao, teclas do IMC_LuxEntrada)
NOVAS = (
    ("IA_Pausa", "Pausar e continuar (Menu/Start/Options)", ("Gamepad_Special_Right", "Escape", "P")),
    ("IA_UI_Confirmar", "Confirmar nos menus (A/Cross)", ("Gamepad_FaceButton_Bottom", "Enter", "SpaceBar")),
    ("IA_UI_Voltar", "Voltar / fechar nos menus (B/Circle)", ("Gamepad_FaceButton_Right", "BackSpace")),
    ("IA_UI_Anterior", "Anterior nos menus (LB/L1, D-Pad, stick esquerdo)", ("Gamepad_LeftShoulder", "Gamepad_DPad_Left", "Gamepad_LeftStick_Left", "Left")),
    ("IA_UI_Proximo", "Proximo nos menus (RB/R1, D-Pad, stick esquerdo)", ("Gamepad_RightShoulder", "Gamepad_DPad_Right", "Gamepad_LeftStick_Right", "Right")),
    ("IA_UI_Alternar", "Alternar o estilo dos icones no pause (Y/Triangle)", ("Gamepad_FaceButton_Top", "Tab")),
)


def w(*a):
    line = " ".join(str(x) for x in a)
    unreal.log("[LUX gamepad] " + line)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
        fh.flush()


class Aborta(Exception):
    pass


def tecla(nome):
    k = unreal.Key()
    k.set_editor_property("key_name", nome)
    return k


def nome_tecla(m):
    return str(m.get_editor_property("key").get_editor_property("key_name"))


def nome_acao(m):
    a = m.get_editor_property("action")
    return a.get_name() if a else None


def eh_gamepad(m):
    return nome_tecla(m).startswith("Gamepad_")


def props(o):
    """propriedades simples (so as do modificador/gatilho) como texto, para comparar e guardar"""
    out = {}
    for n in dir(o):
        if n.startswith("_") or n in ("outer", "name", "class", "package", "world", "unique_id", "transient_package"):
            continue
        try:
            if callable(getattr(o, n)):
                continue
            v = o.get_editor_property(n)
        except Exception:
            continue
        if isinstance(v, unreal.Vector):
            v = [round(v.x, 6), round(v.y, 6), round(v.z, 6)]
        elif isinstance(v, float):
            v = round(v, 6)
        elif not isinstance(v, (int, bool, str)) and v is not None:
            v = str(v)
        out[n] = v
    return out


def assinatura(m):
    return {"acao": nome_acao(m), "tecla": nome_tecla(m),
            "mods": [[x.get_class().get_name(), props(x)] for x in m.get_editor_property("modifiers")],
            "trigs": [[x.get_class().get_name(), props(x)] for x in m.get_editor_property("triggers")]}


def mapeamentos(imc):
    return list(imc.get_editor_property("default_key_mappings").get_editor_property("mappings"))


def grava_mapeamentos(imc, maps):
    km = imc.get_editor_property("default_key_mappings")
    km.set_editor_property("mappings", maps)
    imc.set_editor_property("default_key_mappings", km)


def carrega(caminho):
    a = EAL.load_asset(caminho)
    if not a:
        raise Aborta("asset nao encontrado: " + caminho)
    return a


# ------------------------------------------------------------------ modificadores desejados nos sticks
def mod_de(m, cls):
    return next((x for x in m.get_editor_property("modifiers") if isinstance(x, cls)), None)


def ajusta_sticks(imc):
    """Left2D: zona morta 0,25 / 0,95 radial (o x50 fica). Right2D: zona morta + ScaleByDeltaTime + Scalar(60,60,1)."""
    maps = mapeamentos(imc)
    mudou = False
    for i, m in enumerate(maps):
        k, a = nome_tecla(m), nome_acao(m)
        if (a, k) not in (("IA_Move", "Gamepad_Left2D"), ("IA_Look", "Gamepad_Right2D")):
            continue
        mods = list(m.get_editor_property("modifiers"))
        dz = mod_de(m, unreal.InputModifierDeadZone)
        if dz is None:
            raise Aborta("%s <- %s sem InputModifierDeadZone (estado inesperado)" % (a, k))
        if abs(dz.get_editor_property("lower_threshold") - ZONA["lower"]) > 1e-6 or abs(dz.get_editor_property("upper_threshold") - ZONA["upper"]) > 1e-6 \
                or dz.get_editor_property("type") != unreal.DeadZoneType.RADIAL:
            dz.set_editor_property("lower_threshold", ZONA["lower"])
            dz.set_editor_property("upper_threshold", ZONA["upper"])
            dz.set_editor_property("type", unreal.DeadZoneType.RADIAL)
            mudou = True
        if a == "IA_Look":
            if mod_de(m, unreal.InputModifierScaleByDeltaTime) is None or mod_de(m, unreal.InputModifierScalar) is None:
                # ordem: zona morta -> x delta tempo -> x60
                novos = [dz]
                novos.append(unreal.new_object(unreal.InputModifierScaleByDeltaTime, outer=imc))
                sc = unreal.new_object(unreal.InputModifierScalar, outer=imc)
                sc.set_editor_property("scalar", unreal.Vector(LOOK_ESCALA, LOOK_ESCALA, 1.0))
                novos.append(sc)
                m.set_editor_property("modifiers", novos)
                maps[i] = m
                mudou = True
    if mudou:
        grava_mapeamentos(imc, maps)
    return mudou


# ------------------------------------------------------------------ assets novos
def cria_ia(nome, descricao, objeto_de_edicao):
    caminho = DIR + "/" + nome
    if EAL.does_asset_exist(caminho):
        ia = EAL.load_asset(caminho)
        novo = False
    else:
        ia = unreal.AssetToolsHelpers.get_asset_tools().create_asset(nome, DIR, unreal.InputAction, unreal.InputAction_Factory())
        novo = True
    ia.set_editor_property("value_type", unreal.InputActionValueType.BOOLEAN)
    ia.set_editor_property("trigger_when_paused", True)
    ia.set_editor_property("consume_input", False)
    ia.set_editor_property("action_description", unreal.Text(descricao))
    if not [t for t in ia.get_editor_property("triggers") if isinstance(t, unreal.InputTriggerPressed)]:
        ia.set_editor_property("triggers", [unreal.new_object(unreal.InputTriggerPressed, outer=ia)])
    objeto_de_edicao.add(caminho)
    return ia, novo


def instalar():
    if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():
        raise Aborta("feche o PIE")
    salvar = set()
    imc = carrega(IMC)
    maps0 = mapeamentos(imc)
    if not os.path.exists(SNAP):
        json.dump({"data": "2026-10-01", "mapeamentos": [assinatura(m) for m in maps0]}, open(SNAP, "w", encoding="utf-8"), indent=1)
        w("snapshot do IMC_Default gravado:", SNAP, "(%d mapeamentos)" % len(maps0))
    # 1) gamepad nas acoes existentes (so adiciona)
    with unreal.ScopedEditorTransaction("LUX: gamepad no IMC_Default"):
        imc.modify()
        for acao, t in GAMEPAD:
            ia = carrega(IA_DIR + "/" + acao)
            if not [m for m in mapeamentos(imc) if nome_acao(m) == acao and nome_tecla(m) == t]:
                imc.map_key(ia, tecla(t))
                w("IMC_Default: %s <- %s" % (acao, t))
                salvar.add(IMC)
        if ajusta_sticks(imc):
            w("IMC_Default: zona morta %.2f/%.2f radial nos dois sticks; Look do gamepad com ScaleByDeltaTime x%d" % (ZONA["lower"], ZONA["upper"], LOOK_ESCALA))
            salvar.add(IMC)
    # 2) acoes novas + IMC_LuxEntrada
    if not EAL.does_directory_exist(DIR):
        EAL.make_directory(DIR)
    novos = set()
    ias = {}
    for nome, desc, _ in NOVAS:
        ias[nome], novo = cria_ia(nome, desc, salvar)
        if novo:
            w("criada", nome)
    if not EAL.does_asset_exist(IMC_LUX):
        unreal.AssetToolsHelpers.get_asset_tools().create_asset("IMC_LuxEntrada", DIR, unreal.InputMappingContext, unreal.InputMappingContext_Factory())
        w("criado IMC_LuxEntrada")
    lux = carrega(IMC_LUX)
    lux.set_editor_property("context_description", unreal.Text("LUX: pausa, confirmar, voltar e navegar nos menus (teclado e gamepad). Registrado por BP_LuxEntrada."))
    with unreal.ScopedEditorTransaction("LUX: IMC_LuxEntrada"):
        lux.modify()
        for nome, _, teclas in NOVAS:
            for t in teclas:
                if not [m for m in mapeamentos(lux) if nome_acao(m) == nome and nome_tecla(m) == t]:
                    lux.map_key(ias[nome], tecla(t))
                    w("IMC_LuxEntrada: %s <- %s" % (nome, t))
    salvar.add(IMC_LUX)
    f = verificar()
    if f:
        raise Aborta("verificar FAIL (nada salvo): %s" % f)
    for p in sorted(salvar):
        a = EAL.load_asset(p)
        w("salvo", p, EAL.save_loaded_asset(a, False))


# ------------------------------------------------------------------ verificacao
def verificar(silencioso=False):
    falhas = []
    imc = carrega(IMC)
    maps = mapeamentos(imc)
    # teclado e mouse identicos ao snapshot (so as acoes que nao sao gamepad)
    if os.path.exists(SNAP):
        orig = [s for s in json.load(open(SNAP, encoding="utf-8"))["mapeamentos"] if not s["tecla"].startswith("Gamepad_")]
        atual = [assinatura(m) for m in maps if not eh_gamepad(m)]
        if sorted(json.dumps(x, sort_keys=True) for x in orig) != sorted(json.dumps(x, sort_keys=True) for x in atual):
            falhas.append("teclado/mouse DIFERE do snapshot: %d original x %d atual" % (len(orig), len(atual)))
    else:
        falhas.append("sem snapshot (%s): rode instalar antes" % SNAP)
    # gamepad esperado, uma vez cada
    for acao, t in GAMEPAD:
        n = len([m for m in maps if nome_acao(m) == acao and nome_tecla(m) == t])
        if n != 1:
            falhas.append("%s <- %s aparece %d vezes (esperado 1)" % (acao, t, n))
    for acao in PROIBIDAS:
        gp = [nome_tecla(m) for m in maps if nome_acao(m) == acao and eh_gamepad(m)]
        if gp:
            falhas.append("%s no gamepad (%s): viola a D09" % (acao, gp))
    # nenhuma tecla de gamepad em duas acoes diferentes no mesmo contexto; nada duplicado
    vistos = {}
    for m in maps:
        chave = (nome_acao(m), nome_tecla(m))
        vistos[chave] = vistos.get(chave, 0) + 1
    falhas += ["mapeamento duplicado no IMC_Default: %s <- %s (x%d)" % (a, k, n) for (a, k), n in vistos.items() if n > 1]
    por_tecla = {}
    for m in maps:
        if eh_gamepad(m):
            por_tecla.setdefault(nome_tecla(m), set()).add(nome_acao(m))
    falhas += ["tecla %s ligada a mais de uma acao no IMC_Default: %s" % (k, sorted(v)) for k, v in por_tecla.items() if len(v) > 1]
    # sticks
    for acao, k in (("IA_Move", "Gamepad_Left2D"), ("IA_Look", "Gamepad_Right2D")):
        m = next((x for x in maps if nome_acao(x) == acao and nome_tecla(x) == k), None)
        if not m:
            falhas.append("%s <- %s sumiu" % (acao, k))
            continue
        dz = mod_de(m, unreal.InputModifierDeadZone)
        if dz is None or abs(dz.get_editor_property("lower_threshold") - ZONA["lower"]) > 1e-6 or dz.get_editor_property("type") != unreal.DeadZoneType.RADIAL:
            falhas.append("%s <- %s sem zona morta radial %.2f" % (acao, k, ZONA["lower"]))
        if acao == "IA_Look":
            sc = mod_de(m, unreal.InputModifierScalar)
            if mod_de(m, unreal.InputModifierScaleByDeltaTime) is None or sc is None or abs(sc.get_editor_property("scalar").x - LOOK_ESCALA) > 1e-6:
                falhas.append("Look do gamepad sem ScaleByDeltaTime x%d" % LOOK_ESCALA)
    # acoes novas e IMC_LuxEntrada
    if not EAL.does_asset_exist(IMC_LUX):
        falhas.append("IMC_LuxEntrada nao existe")
    else:
        lux = carrega(IMC_LUX)
        lm = mapeamentos(lux)
        for nome, _, teclas in NOVAS:
            ia = EAL.load_asset(DIR + "/" + nome) if EAL.does_asset_exist(DIR + "/" + nome) else None
            if not ia:
                falhas.append(nome + " nao existe")
                continue
            if not ia.get_editor_property("trigger_when_paused") or ia.get_editor_property("consume_input"):
                falhas.append("%s: trigger_when_paused/consume_input errados" % nome)
            tem = sorted(nome_tecla(m) for m in lm if nome_acao(m) == nome)
            if tem != sorted(teclas):
                falhas.append("%s no IMC_LuxEntrada: %s (esperado %s)" % (nome, tem, sorted(teclas)))
        vl = {}
        for m in lm:
            c = (nome_acao(m), nome_tecla(m))
            vl[c] = vl.get(c, 0) + 1
        falhas += ["duplicado no IMC_LuxEntrada: %s <- %s" % c for c, n in vl.items() if n > 1]
        # teclas repetidas entre os dois contextos (esperado: so as de UI, que nao consomem)
        jogo = {}
        for m in maps:
            jogo.setdefault(nome_tecla(m), set()).add(nome_acao(m))
        rep = []
        for m in lm:
            k = nome_tecla(m)
            if k in jogo:
                rep.append("%s: %s (UI) x %s (jogo)" % (k, nome_acao(m), sorted(jogo[k])))
        if not silencioso:
            w("teclas em comum entre IMC_Default e IMC_LuxEntrada (intencional; as de UI nao consomem e so agem em pausa/janela):")
            for r in sorted(set(rep)):
                w("   ", r)
    if not silencioso:
        w("verificar:", ("FAIL %s" % falhas) if falhas else "PASS")
    return falhas


def tabela():
    imc = carrega(IMC)
    w("IMC_Default (%d mapeamentos):" % len(mapeamentos(imc)))
    for m in sorted(mapeamentos(imc), key=lambda x: (nome_acao(x) or "", nome_tecla(x))):
        w("  %-14s <- %-28s mods=%s" % (nome_acao(m), nome_tecla(m), [x.get_class().get_name().replace("InputModifier", "") for x in m.get_editor_property("modifiers")]))
    if EAL.does_asset_exist(IMC_LUX):
        lux = carrega(IMC_LUX)
        w("IMC_LuxEntrada (%d mapeamentos):" % len(mapeamentos(lux)))
        for m in sorted(mapeamentos(lux), key=lambda x: (nome_acao(x) or "", nome_tecla(x))):
            w("  %-16s <- %s" % (nome_acao(m), nome_tecla(m)))


def sondar():
    tabela()
    w("snapshot:", "existe" if os.path.exists(SNAP) else "nao existe")
    verificar()


def desfazer():
    """Devolve o IMC_Default ao snapshot (sem os mapeamentos de gamepad e com os sticks originais). As acoes novas e o IMC_LuxEntrada ficam (sem uso)."""
    if not os.path.exists(SNAP):
        raise Aborta("sem snapshot: nada a desfazer")
    imc = carrega(IMC)
    orig = json.load(open(SNAP, encoding="utf-8"))["mapeamentos"]
    with unreal.ScopedEditorTransaction("LUX: desfaz gamepad"):
        imc.modify()
        maps = mapeamentos(imc)
        for acao, t in GAMEPAD:
            ia = carrega(IA_DIR + "/" + acao)
            if [m for m in maps if nome_acao(m) == acao and nome_tecla(m) == t] and not [s for s in orig if s["acao"] == acao and s["tecla"] == t]:
                imc.unmap_key(ia, tecla(t))
                w("removido", acao, "<-", t)
        maps = mapeamentos(imc)
        for i, m in enumerate(maps):
            for s in orig:
                if s["acao"] == nome_acao(m) and s["tecla"] == nome_tecla(m) and nome_tecla(m) in ("Gamepad_Left2D", "Gamepad_Right2D"):
                    mods = list(m.get_editor_property("modifiers"))
                    novos = []
                    for cls_nome, p in s["mods"]:
                        cls = getattr(unreal, cls_nome)
                        o = next((x for x in mods if isinstance(x, cls)), None) or unreal.new_object(cls, outer=imc)
                        for pn, pv in p.items():
                            try:
                                if cls_nome == "InputModifierScalar" and pn == "scalar":
                                    o.set_editor_property(pn, unreal.Vector(*pv))
                                elif cls_nome == "InputModifierDeadZone" and pn == "type":
                                    o.set_editor_property(pn, unreal.DeadZoneType.RADIAL if "RADIAL" in pv else unreal.DeadZoneType.AXIAL)
                                elif isinstance(pv, (int, float, bool)):
                                    o.set_editor_property(pn, pv)
                            except Exception:
                                pass
                        novos.append(o)
                    m.set_editor_property("modifiers", novos)
                    maps[i] = m
        grava_mapeamentos(imc, maps)
    w("salvo IMC_Default", EAL.save_loaded_asset(imc, False))
    w("(snapshot original em", SNAP, ")")


def main():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    open(LOG, "w", encoding="utf-8").close()
    modo = next((a for a in sys.argv[1:] if a in ("sondar", "instalar", "verificar", "desfazer")), "sondar")
    w("modo:", modo)
    try:
        {"sondar": sondar, "instalar": instalar, "verificar": verificar, "desfazer": desfazer}[modo]()
    except Aborta as ex:
        w("ABORTADO:", ex)
    except Exception:
        w("ERRO " + traceback.format_exc())


if __name__ == "__main__":
    main()
