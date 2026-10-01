# LUX: legibilidade com a vela em maos (01/10/2026; pedido do Gabriel: "ajustar a iluminacao e remover o blur excessivo que prejudica a navegacao").
# Duas mudancas no PPV_Global (valem em TODAS as condicoes A-D). Nao toca em BP_Player (D02), vela, luzes nem PPV_Atmosfera:
#  1. MASCARA DE METRAGEM da exposicao (auto_exposure_meter_mask = T_LuxMascaraMetragem): peso 0,1 sobre a regiao da tela onde ficam a mao e a vela.
#     Causa raiz: a mao e a chama sao muito mais claras que o corredor e puxavam a exposicao automatica para baixo; com a vela acesa 89 % dos pixels
#     ficavam < 0,03 no inicio do corredor e so ~4 % do cenario aparecia (com a vela apagada, ~25 %). Com a mascara a vela acesa deixa de esconder o
#     cenario e continua sendo luz (aquece o que ilumina). Vale em todos os niveis de escalabilidade (r.EyeAdaptationQuality=2 em todos).
#  2. MOTION BLUR zerado (motion_blur_amount = 0): o padrao (0,5 / max 5 %) tira 60 a 74 % da nitidez horizontal em qualquer giro de camera
#     (medido com o quadro exibido, 60 a 240 graus/s); zerado volta a ~80 % do quadro parado (o resto e o TSR a 71 %).
# Uso (editor, FORA do PIE):
#   py ".../Tools/Lighting/vela_legibilidade.py" sondar               -> mostra o estado (nada muda)
#   py ".../Tools/Lighting/vela_legibilidade.py" instalar [salvar]    -> cria a textura (se faltar) e aplica no PPV_Global; "salvar" grava o mapa
#   py ".../Tools/Lighting/vela_legibilidade.py" verificar            -> PASS/FAIL (valores, textura, faixa de exposicao [-11, 9], volumes que anulariam)
#   py ".../Tools/Lighting/vela_legibilidade.py" desfazer [salvar] [apagar-asset]   -> volta aos valores anteriores (Saved/VelaLegibilidade_anterior.json)
# Idempotente. Ctrl+Z tambem desfaz ("LUX: vela legibilidade"). Log: Saved/VelaLegibilidade.txt
# CUIDADO (aprendido no laboratorio, ver Registro_de_Diagnosticos): ao testar no PIE, NUNCA escreva propriedades do componente Lampiao com
# set_editor_property (reexecuta o Construction Script e a vela some da mao); use os setters de runtime (set_intensity etc.).
import json, os, struct, sys, zlib
import unreal

TAG = "LUX_PPV_GLOBAL"
MASCARA = "/Game/Masion/LUX/Player/T_LuxMascaraMetragem"
# regiao da tela (fracoes 0..1, 16:9) onde ficam a mao e a vela: vela x 0,51-0,59 / y 0,50-0,77; mao e antebraco x 0,50-0,70 / y 0,76-1,00.
# peso 0,10 dentro (medido: 0 clareia demais as salas escuras; 0,2 e 0,3 nao bastam), 1 fora, com rampa suave de 0,06.
MASC = {"x0": 0.46, "x1": 0.74, "y0": 0.44, "y1": 1.01, "rampa": 0.06, "peso": 0.10, "w": 256, "h": 144}
ALVO = {"motion_blur_amount": 0.0}
META = "LUX_MascaraMetragem"      # metadado gravado na textura com os parametros da mascara (a textura em si so tem pixels)
FAIXA_SEGURA = (-11.0, 9.0)       # D07: exposicao efetiva (EV100 - bias) sempre dentro desta faixa

saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(saved, "VelaLegibilidade.txt")
ANTERIOR = os.path.join(saved, "VelaLegibilidade_anterior.json")
LINHAS = []
EAL = unreal.EditorAssetLibrary


def log(*a):
    s = " ".join(str(x) for x in a)
    LINHAS.append(s)
    print(s)


def grava_log():
    open(OUT, "w", encoding="utf-8").write("\n".join(LINHAS))


# ---------------------------------------------------------------- textura da mascara
def png_cinza(w, h, pixels):
    """PNG 8 bits em tons de cinza (sem dependencias): o Python do editor nao tem PIL."""
    cru = b"".join(b"\x00" + bytes(pixels[y * w:(y + 1) * w]) for y in range(h))

    def bloco(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return b"\x89PNG\r\n\x1a\n" + bloco(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0)) + bloco(b"IDAT", zlib.compress(cru, 9)) + bloco(b"IEND", b"")


def pixels_mascara(m=MASC):
    w, h = m["w"], m["h"]
    px = []
    for j in range(h):
        y = (j + 0.5) / h
        for i in range(w):
            x = (i + 0.5) / w
            dx = max(m["x0"] - x, x - m["x1"], 0.0)
            dy = max(m["y0"] - y, y - m["y1"], 0.0)
            t = min(max(((dx * dx + dy * dy) ** 0.5) / m["rampa"], 0.0), 1.0)
            v = m["peso"] + (1.0 - m["peso"]) * (t * t * (3.0 - 2.0 * t))
            px.append(int(v * 255 + 0.5))
    return px


def assinatura():
    return json.dumps({k: MASC[k] for k in sorted(MASC)}, sort_keys=True)


def textura_ok(tex):
    """a textura precisa ter os parametros desta versao do script, ser tons de cinza, sem sRGB, sem mips e sem streaming (o histograma a le a cada quadro)"""
    if tex is None:
        return ["textura ausente: " + MASCARA]
    f = []
    if EAL.get_metadata_tag(tex, META) != assinatura():
        f.append("textura com parametros diferentes dos deste script (metadado %s: %s)" % (META, EAL.get_metadata_tag(tex, META)))
    if (tex.blueprint_get_size_x(), tex.blueprint_get_size_y()) != (MASC["w"], MASC["h"]):
        f.append("tamanho %sx%s (esperado %dx%d)" % (tex.blueprint_get_size_x(), tex.blueprint_get_size_y(), MASC["w"], MASC["h"]))
    if tex.get_editor_property("compression_settings") != unreal.TextureCompressionSettings.TC_GRAYSCALE:
        f.append("compressao != TC_GRAYSCALE")
    if tex.get_editor_property("srgb"):
        f.append("sRGB ligado")
    if tex.get_editor_property("mip_gen_settings") != unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS:
        f.append("mips ligados")
    if not tex.get_editor_property("never_stream"):
        f.append("never_stream desligado")
    return f


def cria_textura(forcar=False):
    tex = EAL.load_asset(MASCARA) if EAL.does_asset_exist(MASCARA) else None
    if tex is not None and not forcar and not textura_ok(tex):
        log("textura ja existe e esta correta:", MASCARA)
        return tex
    png = os.path.join(saved, "LuxMascaraMetragem.png")
    open(png, "wb").write(png_cinza(MASC["w"], MASC["h"], pixels_mascara()))
    pasta, nome = MASCARA.rsplit("/", 1)
    tk = unreal.AssetImportTask()
    for k, v in (("filename", png.replace("\\", "/")), ("destination_path", pasta), ("destination_name", nome), ("automated", True),
                 ("replace_existing", True), ("replace_existing_settings", True), ("save", False)):
        tk.set_editor_property(k, v)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([tk])
    tex = EAL.load_asset(MASCARA)
    if tex is None:
        raise RuntimeError("importacao da mascara falhou: " + MASCARA)
    tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_GRAYSCALE)
    tex.set_editor_property("srgb", False)
    tex.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    tex.set_editor_property("never_stream", True)
    tex.set_editor_property("filter", unreal.TextureFilter.TF_BILINEAR)
    tex.set_editor_property("address_x", unreal.TextureAddress.TA_CLAMP)
    tex.set_editor_property("address_y", unreal.TextureAddress.TA_CLAMP)
    EAL.set_metadata_tag(tex, META, assinatura())
    EAL.save_loaded_asset(tex, False)
    log("textura criada:", MASCARA, "| regiao", {k: MASC[k] for k in ("x0", "x1", "y0", "y1", "rampa", "peso")})
    return tex


# ---------------------------------------------------------------- volumes
def mundo():
    ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    if ues.get_game_world():
        raise RuntimeError("Pare o PIE antes.")
    return ues.get_editor_world()


def volumes(w):
    return [a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.PostProcessVolume)]


def ppv_global(w):
    vs = volumes(w)
    for a in vs:
        if a.actor_has_tag(TAG):
            return a
    for a in vs:
        if a.get_actor_label() == "PPV_Global":
            return a
    raise RuntimeError("PPV_Global nao encontrado (rode apply_ppv_global.py antes)")


def valor(s, prop):
    v = s.get_editor_property(prop)
    if isinstance(v, unreal.Object):
        return v.get_path_name().split(".")[0]
    return v


def estado(a):
    s = a.get_editor_property("settings")
    d = {"auto_exposure_meter_mask": (bool(s.get_editor_property("override_auto_exposure_meter_mask")), valor(s, "auto_exposure_meter_mask"))}
    for p in ALVO:
        d[p] = (bool(s.get_editor_property("override_" + p)), valor(s, p))
    return d


def mostra(w):
    for a in sorted(volumes(w), key=lambda x: x.get_editor_property("priority")):
        s = a.get_editor_property("settings")
        log("  %s | prioridade %.1f | enabled %s | unbound %s | EV min %s max %s bias %s | mascara %s | motion_blur_amount %s" % (
            a.get_actor_label(), a.get_editor_property("priority"), a.get_editor_property("enabled"), a.get_editor_property("unbound"),
            (s.get_editor_property("auto_exposure_min_brightness") if s.get_editor_property("override_auto_exposure_min_brightness") else "-"),
            (s.get_editor_property("auto_exposure_max_brightness") if s.get_editor_property("override_auto_exposure_max_brightness") else "-"),
            (s.get_editor_property("auto_exposure_bias") if s.get_editor_property("override_auto_exposure_bias") else "-"),
            ("%s" % valor(s, "auto_exposure_meter_mask")) if s.get_editor_property("override_auto_exposure_meter_mask") else "-",
            ("%s" % s.get_editor_property("motion_blur_amount")) if s.get_editor_property("override_motion_blur_amount") else "-"))


# ---------------------------------------------------------------- comandos
def sondar():
    w = mundo()
    log("mapa:", w.get_path_name())
    mostra(w)
    tex = EAL.load_asset(MASCARA) if EAL.does_asset_exist(MASCARA) else None
    log("textura:", MASCARA, "->", "ausente" if tex is None else ("ok" if not textura_ok(tex) else "PROBLEMAS: " + "; ".join(textura_ok(tex))))
    log("estado do PPV_Global:", estado(ppv_global(w)))
    log("anterior gravado:", os.path.exists(ANTERIOR))


def instalar(salvar=False):
    w = mundo()
    tex = cria_textura()
    g = ppv_global(w)
    if not os.path.exists(ANTERIOR):
        s0 = g.get_editor_property("settings")
        ant = {"auto_exposure_meter_mask": [bool(s0.get_editor_property("override_auto_exposure_meter_mask")), valor(s0, "auto_exposure_meter_mask")]}
        for p in ALVO:
            ant[p] = [bool(s0.get_editor_property("override_" + p)), valor(s0, p)]
        json.dump(ant, open(ANTERIOR, "w"), indent=1)
        log("valores anteriores gravados em", ANTERIOR, ant)
    with unreal.ScopedEditorTransaction("LUX: vela legibilidade"):
        g.modify()
        s = g.get_editor_property("settings")
        s.set_editor_property("override_auto_exposure_meter_mask", True)
        s.set_editor_property("auto_exposure_meter_mask", tex)
        for p, v in ALVO.items():
            s.set_editor_property("override_" + p, True)
            s.set_editor_property(p, v)
        g.set_editor_property("settings", s)
    log("PPV_Global atualizado:", estado(g))
    if salvar:
        ok = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
        log("mapa salvo:", ok)
    else:
        log("NAO SALVO: revise e salve o mapa (Ctrl+S) ou rode 'instalar salvar'.")


def verificar():
    w = mundo()
    falhas, avisos = [], []
    tex = EAL.load_asset(MASCARA) if EAL.does_asset_exist(MASCARA) else None
    falhas += textura_ok(tex)
    vs = volumes(w)
    g = ppv_global(w)
    s = g.get_editor_property("settings")
    if not s.get_editor_property("override_auto_exposure_meter_mask") or valor(s, "auto_exposure_meter_mask") != MASCARA:
        falhas.append("PPV_Global sem a mascara de metragem")
    for p, v in ALVO.items():
        if not s.get_editor_property("override_" + p) or abs(s.get_editor_property(p) - v) > 1e-6:
            falhas.append("PPV_Global.%s != %s" % (p, v))
    if not (g.get_editor_property("enabled") and g.get_editor_property("unbound")):
        falhas.append("PPV_Global precisa estar enabled e unbound")
    # nenhum volume de prioridade maior pode anular a mascara ou o motion blur
    pg = g.get_editor_property("priority")
    for a in vs:
        if a is g or not a.get_editor_property("enabled") or a.get_editor_property("priority") < pg:
            continue
        sa = a.get_editor_property("settings")
        for p in ("auto_exposure_meter_mask",) + tuple(ALVO):
            if sa.get_editor_property("override_" + p):
                falhas.append("%s (prioridade %.1f) sobrescreve %s e anula o PPV_Global" % (a.get_actor_label(), a.get_editor_property("priority"), p))
    # faixa de exposicao efetiva (D07): [min - bias, max - bias] com e sem a PPV_Atmosfera
    def efetivo(prop, ativos):
        for a in sorted(ativos, key=lambda x: -x.get_editor_property("priority")):
            sa = a.get_editor_property("settings")
            if sa.get_editor_property("override_" + prop):
                return sa.get_editor_property(prop)
        return None
    for nome, ativos in (("com PPV_Atmosfera", [a for a in vs if a.get_editor_property("enabled")]),
                         ("sem PPV_Atmosfera (condicao A)", [a for a in vs if a.get_editor_property("enabled") and a.get_actor_label() != "PPV_Atmosfera"])):
        mn, mx, bias = (efetivo("auto_exposure_" + k, ativos) for k in ("min_brightness", "max_brightness", "bias"))
        if mn is None or mx is None or bias is None:
            avisos.append("faixa de exposicao %s indeterminada (min %s max %s bias %s)" % (nome, mn, mx, bias))
            continue
        lo, hi = mn - bias, mx - bias
        log("exposicao efetiva %s: [%.1f, %.1f]" % (nome, lo, hi))
        if lo < FAIXA_SEGURA[0] or hi > FAIXA_SEGURA[1]:
            falhas.append("exposicao efetiva %s [%.1f, %.1f] fora de %s" % (nome, lo, hi, FAIXA_SEGURA))
    for x in avisos:
        log("AVISO:", x)
    if falhas:
        for x in falhas:
            log("FALHA:", x)
        log("RESULTADO: FAIL (%d)" % len(falhas))
    else:
        log("RESULTADO: PASS (PPV_Global com mascara de metragem e motion blur 0; textura correta; faixa de exposicao dentro de %s)" % (FAIXA_SEGURA,))
    return not falhas


def desfazer(salvar=False, apagar_asset=False):
    w = mundo()
    g = ppv_global(w)
    ant = json.load(open(ANTERIOR)) if os.path.exists(ANTERIOR) else {"auto_exposure_meter_mask": [False, None], "motion_blur_amount": [False, 0.5]}
    with unreal.ScopedEditorTransaction("LUX: desfazer vela legibilidade"):
        g.modify()
        s = g.get_editor_property("settings")
        ov, caminho = ant["auto_exposure_meter_mask"]
        s.set_editor_property("override_auto_exposure_meter_mask", bool(ov))
        s.set_editor_property("auto_exposure_meter_mask", EAL.load_asset(caminho) if caminho else None)
        for p in ALVO:
            ov, v = ant[p]
            s.set_editor_property("override_" + p, bool(ov))
            s.set_editor_property(p, v)
        g.set_editor_property("settings", s)
    log("PPV_Global restaurado:", estado(g))
    if apagar_asset and EAL.does_asset_exist(MASCARA):
        log("textura apagada:", EAL.delete_asset(MASCARA))
    if salvar:
        log("mapa salvo:", unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level())
    else:
        log("NAO SALVO: salve o mapa (Ctrl+S) ou rode 'desfazer salvar'.")


def main():
    args = [a.lower() for a in sys.argv[1:]]
    cmd = args[0] if args else "sondar"
    log("== vela_legibilidade.py", cmd, args[1:])
    try:
        if cmd == "sondar":
            sondar()
        elif cmd == "instalar":
            instalar("salvar" in args)
        elif cmd == "verificar":
            verificar()
        elif cmd == "desfazer":
            desfazer("salvar" in args, "apagar-asset" in args)
        else:
            log("comando desconhecido:", cmd, "(sondar | instalar [salvar] | verificar | desfazer [salvar] [apagar-asset])")
    finally:
        grava_log()


main()
