# LUX - memoria (27/09): teto de textura por regra + remove o redirector circular do PSX + escalabilidade do editor.
#   py "<projeto>/Tools/Memoria/lux_memoria.py"            -> sondar (so le e mostra o que faria)
#   py "<projeto>/Tools/Memoria/lux_memoria.py" aplicar    -> aplica e salva SO as texturas alteradas
#   py "<projeto>/Tools/Memoria/lux_memoria.py" desfazer   -> volta os tetos originais e restaura o redirector
# Idempotente. Nao mexe em mapa, Blueprint, BP_Player nem em outros assets.
# Log: Saved/Memoria/memoria_log.txt   Snapshot dos valores originais: Tools/Memoria/texturas_original.json
import json, os, shutil, sys, traceback
import unreal

EAL = unreal.EditorAssetLibrary
AR = unreal.AssetRegistryHelpers.get_asset_registry()
AQUI = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(os.path.dirname(AQUI))
SNAP = os.path.join(AQUI, "texturas_original.json")
BACKUP = os.path.join(AQUI, "backup")
LOGDIR = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "Memoria")
LOG = os.path.join(LOGDIR, "memoria_log.txt")

# (pasta, trecho do nome (minusculo), teto). A primeira regra que casar vale.
REGRAS = [
    ("/Game/Cowboy_character/Textures", "head", 512),
    ("/Game/Cowboy_character/Textures", "hands", 512),
    ("/Game/Cowboy_character/Textures", "hair", 512),
    ("/Game/Cowboy_character/Textures", "eye", 512),
    ("/Game/Cowboy_character/Textures", "", 1024),   # pernas, tronco (e coldre/colt, que o SKM_Cowboy_NoGun nem usa)
    ("/Game/Fab/TV_Table", "", 2048),                # Wood_Dark (rack da TV) usa Wood013_4K
]
REDIRECTOR = "/Game/MR_PSX_Shader/Maps/L_MR_PSX_Overview"
REDIRECTOR_ARQ = os.path.join(PROJ, "Content", "MR_PSX_Shader", "Maps", "L_MR_PSX_Overview.umap")

MODO = "sondar"
for a in sys.argv[1:]:
    if str(a).lower() in ("aplicar", "desfazer", "sondar"):
        MODO = str(a).lower()


def w(*a):
    line = " ".join(str(x) for x in a)
    unreal.log("[LUX mem] " + line)
    os.makedirs(LOGDIR, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
        fh.flush()


def alvos():
    out = {}
    for pasta, trecho, teto in REGRAS:
        for p in EAL.list_assets(pasta, recursive=True, include_folder=False):
            pkg = p.split(".")[0]
            if pkg in out or trecho not in pkg.lower():
                continue
            d = EAL.find_asset_data(pkg)
            if not d.is_valid() or str(d.asset_class_path.asset_name) != "Texture2D":
                continue
            out[pkg] = teto
    return out


def texturas(modo):
    snap = {}
    if os.path.exists(SNAP):
        with open(SNAP, encoding="utf-8") as fh:
            snap = json.load(fh)
    mudou = 0
    for pkg, teto in sorted(alvos().items()):
        t = EAL.load_asset(pkg)
        atual = t.get_editor_property("max_texture_size")
        if modo == "desfazer":
            if pkg not in snap:
                continue
            novo = snap[pkg]
        else:
            if pkg not in snap:
                snap[pkg] = atual
            novo = teto if (atual == 0 or atual > teto) else atual
        if novo == atual:
            w("  ok   %-95s %d" % (pkg, atual))
            continue
        w("  %s %-95s %d -> %d" % ("MUDA" if modo != "sondar" else "faria", pkg, atual, novo))
        if modo == "sondar":
            continue
        t.modify()
        t.set_editor_property("max_texture_size", novo)
        # salvar espera a compilacao da textura: uma por vez, para nao estourar a RAM
        w("       salvo:", EAL.save_loaded_asset(t, False))
        mudou += 1
    if modo == "aplicar":
        with open(SNAP, "w", encoding="utf-8") as fh:
            json.dump(snap, fh, indent=1)
    w("texturas alteradas:", mudou)


def redirector(modo):
    os.makedirs(BACKUP, exist_ok=True)
    bak = os.path.join(BACKUP, "L_MR_PSX_Overview.umap")
    if modo == "desfazer":
        if os.path.exists(bak) and not os.path.exists(REDIRECTOR_ARQ):
            shutil.copy2(bak, REDIRECTOR_ARQ)
            w("redirector restaurado de", bak)
        return
    if not os.path.exists(REDIRECTOR_ARQ):
        w("redirector ja nao existe: ok")
        return
    tam = os.path.getsize(REDIRECTOR_ARQ)
    refs = [str(r) for r in AR.get_referencers(REDIRECTOR, unreal.AssetRegistryDependencyOptions()) if str(r) != REDIRECTOR]
    w("redirector %s (%d bytes); referenciadores: %s" % (REDIRECTOR, tam, refs or "nenhum"))
    if refs or tam > 8192:
        w("  NAO removido (tem referenciador ou nao parece um redirector)")
        return
    if modo == "sondar":
        w("  faria: backup + remover o arquivo")
        return
    shutil.copy2(REDIRECTOR_ARQ, bak)
    os.remove(REDIRECTOR_ARQ)
    AR.scan_paths_synchronous(["/Game/MR_PSX_Shader/Maps"], True)
    w("  removido (backup em %s). Faca commit da remocao." % bak)


try:
    w("=== modo:", MODO)
    texturas(MODO)
    redirector(MODO)
    w("=== fim")
except Exception:
    w(traceback.format_exc())
