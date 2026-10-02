# LUX: corrige dois erros de carga do corpo do jogador (LoadErrors em TODA abertura do editor). So dados: nenhum Blueprint e editado.
#  1) BS_CB_Stand: "amostra A_CB_Run_F ... fora dos limites". Causa: bs_dirspeed.py grava o MAXIMO do eixo Speed com round() (400) e a POSICAO da amostra sem
#     arredondar (400,032 = 360 x 1,1112). O motor marca a amostra invalida e a TIRA da triangulacao (BlendSpace.cpp, ValidateSampleData e ResampleData2D),
#     entao a Run_F nao entra na mistura. Correcao: a posicao volta para dentro do eixo (so a Speed da Run_F, 400,032 -> 400); eixos, rate scales e as outras
#     amostras nao mudam. Amostra editada por Python deixa a triangulacao (BlendSpaceData, serializada) velha: o editor do BlendSpace forca ResampleData() ao
#     abrir (SAnimationBlendSpace.cpp), por isso o script abre o BlendSpace no editor e so entao salva (como o bs_dirspeed.py).
#  2) S_Skeleton_cowboy_character: "pacote dependente /Engine/EngineMeshes/Humanoid nao estava disponivel". O arquivo NAO existe na instalacao do UE 5.8.3
#     nem no manifesto do build (o sistema de Rig legado, URig/RigConfig, saiu do motor); o esqueleto (pack feito para UE4) guarda um RigConfig apontando
#     para ele: propriedade que o motor atual nem declara mais. Correcao: RESALVAR o esqueleto no 5.8 (o pacote e regravado sem a propriedade nem o import
#     orfao). Ossos, pose de referencia e curvas nao mudam (assinatura conferida antes e depois). Nada e substituido nem recriado.
#  Roda no EDITOR GRAFICO (execucao remota ou console "py"); o sondar e o verificar tambem rodam no commandlet. Salva so esses 2 assets, e so se precisar.
#   py "<projeto>/Tools/MixamoFP/corrige_carga_corpo.py" sondar|instalar|verificar|desfazer
import hashlib, json, os, sys, traceback
import unreal

EAL = unreal.EditorAssetLibrary
BS = "/Game/Characters/MixamoFP/BlendSpaces/BS_CB_Stand"
SK = "/Game/Cowboy_character/Mesh/S_Skeleton_cowboy_character"
HUMANOID = "/Engine/EngineMeshes/Humanoid"
AQUI = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(AQUI, "corrige_carga_corpo_original.json")
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
PASTA = os.path.join(SAVED, "LuxSnapshots", "erros_carga")
LOG = os.path.join(SAVED, "LuxSnapshots", "corrige_carga_corpo_log.txt")
ASSIN = os.path.join(PASTA, "esqueleto_assinatura_antes.json")
SK_ARQ = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()), "Cowboy_character", "Mesh", "S_Skeleton_cowboy_character.uasset")
os.makedirs(PASTA, exist_ok=True)
AES = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)


def w(*a):
    linha = " ".join(str(x) for x in a)
    unreal.log("[LUX corpo] " + linha)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(linha + "\n")
        fh.flush()


class Aborta(Exception):
    pass


def carrega(caminho):
    a = EAL.load_asset(caminho)
    if not a:
        raise Aborta("asset nao encontrado: " + caminho)
    return a


# ------------------------------------------------------------------ BlendSpace
def eixos(bs):
    p = list(bs.get_editor_property("blend_parameters"))
    return [(p[i].get_editor_property("min"), p[i].get_editor_property("max")) for i in range(2)]


def amostras(bs):
    out = []
    for i, s in enumerate(bs.get_editor_property("sample_data")):
        v = s.get_editor_property("sample_value")
        a = s.get_editor_property("animation")
        out.append({"i": i, "anim": a.get_name() if a else None, "v": [v.x, v.y, v.z]})
    return out


def fora_dos_limites(bs):
    (x0, x1), (y0, y1) = eixos(bs)
    return [a for a in amostras(bs) if a["anim"] and (a["v"][0] < x0 or a["v"][0] > x1 or a["v"][1] < y0 or a["v"][1] > y1)]


# ------------------------------------------------------------------ esqueleto
def assinatura_esqueleto(sk):
    """o que o esqueleto TEM (ossos, pose de referencia, curvas): para provar que o resalvar nao mudou o conteudo"""
    ass = {}
    pose = sk.get_reference_pose()
    try:
        ass["ossos"] = [str(n) for n in pose.get_bone_names()]
    except Exception as e:
        ass["ossos"] = "nao legivel: " + type(e).__name__
    try:
        ass["modos_translacao"] = [str(b.get_editor_property("translation_retargeting_mode")) for b in sk.get_editor_property("bone_tree")]
    except Exception as e:
        ass["modos_translacao"] = "nao legivel: " + type(e).__name__
    try:
        ass["pose_ref"] = []
        for n in ass["ossos"]:
            for esp in (unreal.AnimPoseSpaces.LOCAL, unreal.AnimPoseSpaces.WORLD):
                t = pose.get_ref_bone_pose(n, esp)
                ass["pose_ref"].append([round(c, 4) + 0.0 for c in (t.translation.x, t.translation.y, t.translation.z, t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w,
                                                                    t.scale3d.x, t.scale3d.y, t.scale3d.z)])
    except Exception as e:
        ass["pose_ref"] = "nao legivel: " + type(e).__name__ + " " + str(e)[:80]
    try:
        ass["curvas"] = sorted(str(x) for x in sk.get_curve_meta_data_names())
    except Exception as e:
        ass["curvas"] = "nao legivel: " + type(e).__name__
    try:
        ass["compativeis"] = sorted(str(x) for x in sk.get_editor_property("compatible_skeletons"))
    except Exception as e:
        ass["compativeis"] = "nao legivel: " + type(e).__name__
    ass["hash"] = hashlib.sha1(json.dumps(ass, sort_keys=True).encode("utf-8")).hexdigest()
    return ass


def humanoid_no_arquivo():
    """o .uasset em disco ainda cita o pacote orfao? (nome do import e do RigConfig)"""
    return b"EngineMeshes/Humanoid" in open(SK_ARQ, "rb").read()


def ar_humanoid():
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    return [str(x) for x in (ar.get_referencers(HUMANOID, unreal.AssetRegistryDependencyOptions(include_soft_package_references=True, include_hard_package_references=True)) or [])]


# ------------------------------------------------------------------ comandos
def sondar():
    bs, sk = carrega(BS), carrega(SK)
    w("BS_CB_Stand eixos (min, max):", eixos(bs))
    for a in amostras(bs):
        w("   amostra %2d %-12s (%.4f, %.4f, %.4f)" % (a["i"], a["anim"], a["v"][0], a["v"][1], a["v"][2]))
    w("   fora dos limites:", [(a["anim"], a["v"]) for a in fora_dos_limites(bs)] or "nenhuma")
    w("esqueleto: .uasset cita /Engine/EngineMeshes/Humanoid:", humanoid_no_arquivo(), "| referenciadores do Humanoid no registro:", ar_humanoid())
    ass = assinatura_esqueleto(sk)
    w("esqueleto: assinatura", ass["hash"], "| ossos:", len(ass["ossos"]) if isinstance(ass["ossos"], list) else ass["ossos"], "| pose_ref:", len(ass["pose_ref"]) if isinstance(ass["pose_ref"], list) else ass["pose_ref"],
      "| curvas:", len(ass["curvas"]) if isinstance(ass["curvas"], list) else ass["curvas"])
    verificar()


def verificar():
    falhas = []
    bs = carrega(BS)
    for a in fora_dos_limites(bs):
        falhas.append("BS_CB_Stand: amostra %s em %s fora dos limites %s" % (a["anim"], a["v"], eixos(bs)))
    if humanoid_no_arquivo():
        falhas.append("S_Skeleton_cowboy_character.uasset ainda cita /Engine/EngineMeshes/Humanoid")
    if ar_humanoid():
        falhas.append("o registro ainda aponta para o Humanoid: %s" % ar_humanoid())
    if os.path.exists(ASSIN):
        antes = json.load(open(ASSIN, encoding="utf-8"))
        depois = assinatura_esqueleto(carrega(SK))
        for k in ("ossos", "modos_translacao", "pose_ref", "curvas", "compativeis"):
            if antes.get(k) != depois.get(k):
                falhas.append("esqueleto: %s mudou depois do resalvar" % k)
    else:
        w("(sem assinatura anterior do esqueleto: so confere a ausencia do Humanoid)")
    w("verificar:", ("FAIL %s" % falhas) if falhas else "PASS")
    return falhas


def salva_bs_pelo_editor(fim):
    """abre o BlendSpace no editor (ele forca ResampleData ao construir) e so entao salva; chama fim() no final"""
    st = {"t": 0.0, "aberto": False, "feito": False, "h": None}

    def _tick(dt):
        if st["feito"]:
            return
        try:
            st["t"] += dt
            if not st["aberto"]:
                AES.open_editor_for_assets([carrega(BS)])
                st["aberto"], st["t"] = True, 0.0
            elif st["t"] > 0.8:
                st["feito"] = True
                a = carrega(BS)
                ok = EAL.save_loaded_asset(a, False)
                AES.close_all_editors_for_asset(a)
                w("BS_CB_Stand: aberto no editor (triangulacao refeita) e salvo:", ok)
                unreal.unregister_slate_post_tick_callback(st["h"])
                fim()
        except Exception:
            st["feito"] = True
            w("ERRO ao salvar o BlendSpace:", traceback.format_exc())
            unreal.unregister_slate_post_tick_callback(st["h"])

    st["h"] = unreal.register_slate_post_tick_callback(_tick)


def instalar():
    if os.environ.get("LUX_CMDLET"):
        raise Aborta("instalar precisa do editor grafico (o BlendSpace tem de abrir no editor); use sondar/verificar no commandlet")
    if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():
        raise Aborta("feche o PIE")
    bs, sk = carrega(BS), carrega(SK)
    # snapshot do que vai mudar (so na 1a vez)
    if not os.path.exists(SNAP):
        json.dump({"data": "2026-10-02", "bs_amostras_fora": fora_dos_limites(bs), "bs_eixos": eixos(bs)}, open(SNAP, "w", encoding="utf-8"), indent=1)
        w("snapshot gravado:", SNAP)
    if not os.path.exists(ASSIN):
        json.dump(assinatura_esqueleto(sk), open(ASSIN, "w", encoding="utf-8"), indent=1)
        w("assinatura do esqueleto (antes) gravada:", ASSIN)
    # 2) esqueleto: resalva so se ainda cita o Humanoid
    if humanoid_no_arquivo():
        w("esqueleto: resalvando (so a referencia orfa ao Humanoid sai):", EAL.save_loaded_asset(sk, False))
    else:
        w("esqueleto: ja sem referencia ao Humanoid (nada a salvar)")
    # 1) BlendSpace: amostras fora do eixo voltam para dentro (clamp), no lugar, so a posicao
    fora = fora_dos_limites(bs)
    if not fora:
        w("BS_CB_Stand: nenhuma amostra fora dos limites (nada a salvar)")
        verificar()
        return
    (x0, x1), (y0, y1) = eixos(bs)
    sd = list(bs.get_editor_property("sample_data"))
    bs.modify()
    for a in fora:
        s = sd[a["i"]]
        novo = unreal.Vector(min(max(a["v"][0], x0), x1), min(max(a["v"][1], y0), y1), a["v"][2])
        s.set_editor_property("sample_value", novo)
        sd[a["i"]] = s
        w("BS_CB_Stand: %s (%.4f, %.4f) -> (%.4f, %.4f)" % (a["anim"], a["v"][0], a["v"][1], novo.x, novo.y))
    bs.set_editor_property("sample_data", sd)
    salva_bs_pelo_editor(lambda: w("instalar: fim |", "PASS" if not verificar() else "FAIL (ver acima)"))


def desfazer():
    if os.environ.get("LUX_CMDLET"):
        raise Aborta("desfazer precisa do editor grafico")
    if not os.path.exists(SNAP):
        raise Aborta("sem snapshot: nada a desfazer")
    orig = json.load(open(SNAP, encoding="utf-8"))
    bs = carrega(BS)
    sd = list(bs.get_editor_property("sample_data"))
    bs.modify()
    for a in orig["bs_amostras_fora"]:
        s = sd[a["i"]]
        s.set_editor_property("sample_value", unreal.Vector(*a["v"]))
        sd[a["i"]] = s
        w("BS_CB_Stand: %s volta para (%.4f, %.4f)" % (a["anim"], a["v"][0], a["v"][1]))
    bs.set_editor_property("sample_data", sd)
    w("esqueleto: para voltar o .uasset original use  git checkout -- Content/Cowboy_character/Mesh/S_Skeleton_cowboy_character.uasset  (copia em %s\\antes)" % PASTA)
    salva_bs_pelo_editor(lambda: w("desfazer: fim"))


modo = sys.argv[1] if len(sys.argv) > 1 else "sondar"
w("modo:", modo)
try:
    {"sondar": sondar, "instalar": instalar, "verificar": verificar, "desfazer": desfazer}[modo]()
except Aborta as e:
    w("ABORTA:", e)
except Exception:
    w("ERRO:", traceback.format_exc())
