"""Aplica um teto de resolucao em todas as Texture2D do projeto.

Uso (com o editor FECHADO):

    UnrealEditor-Cmd.exe <projeto>.uproject -run=pythonscript \
        -script="<projeto>/Tools/optimize_textures.py" -unattended -nopause -nosplash -stdout

O teto padrao e 2048 px. Passe outro valor como argumento para sobrescrever.

O que o script faz: seta MaxTextureSize nas texturas cujo lado maior passa do teto.
Isso corta VRAM e o tamanho do build empacotado. NAO encolhe o .uasset em disco --
o source art continua serializado dentro do arquivo e a engine nao expoe resize
de source a script.

Relatorio: Saved/texture_optimization_report.csv
"""

import csv
import os
import sys

import unreal

DEFAULT_CAP = 2048

# Texturas de UI nao devem ser reduzidas: sao authored no tamanho exato de tela.
SKIP_LOD_GROUPS = {"TEXTUREGROUP_UI"}

REPORT_NAME = "texture_optimization_report.csv"


def resolve_cap():
    """Le o teto de sys.argv, caindo pro default se nao vier nada utilizavel."""
    for arg in sys.argv[1:]:
        if arg.isdigit() and int(arg) > 0:
            return int(arg)
    return DEFAULT_CAP


def imported_size_from_tag(asset_data):
    """Le 'Dimensions' do asset registry: e o tamanho do SOURCE, sem carregar o asset.

    Retorna (w, h) ou None quando a tag nao existe.
    """
    raw = asset_data.get_tag_value("Dimensions")
    if not raw:
        return None
    try:
        w, h = str(raw).lower().split("x")
        return int(w), int(h)
    except ValueError:
        return None


def built_size(texture):
    """Tamanho do maior mip depois de aplicar MaxTextureSize/LODBias."""
    try:
        size = texture.blueprint_get_built_texture_size()
        return int(size.x), int(size.y)
    except Exception:
        return 0, 0


def main():
    cap = resolve_cap()
    unreal.log("=== Otimizacao de textura: teto de {0} px ===".format(cap))

    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    registry.scan_paths_synchronous(["/Game"])
    registry.wait_for_completion()

    class_path = unreal.TopLevelAssetPath("/Script/Engine", "Texture2D")
    assets = registry.get_assets_by_class(class_path, False)
    unreal.log("Texture2D encontradas: {0}".format(len(assets)))

    rows = []
    changed = 0
    skipped_ui = 0
    already_ok = 0
    failed = 0

    for asset_data in assets:
        path = str(asset_data.package_name)

        lod_group = str(asset_data.get_tag_value("LODGroup") or "")
        if lod_group in SKIP_LOD_GROUPS:
            skipped_ui += 1
            continue

        imported = imported_size_from_tag(asset_data)
        if imported and max(imported) <= cap:
            # Ja esta dentro do teto pelo proprio source: nao suja o asset.
            continue

        try:
            texture = asset_data.get_asset()
            if not isinstance(texture, unreal.Texture2D):
                continue

            if imported is None:
                imported = (texture.blueprint_get_size_x(), texture.blueprint_get_size_y())
                if max(imported) <= cap:
                    continue

            current_cap = int(texture.get_editor_property("max_texture_size"))
            if current_cap != 0 and current_cap <= cap:
                already_ok += 1
                continue

            before_w, before_h = built_size(texture)
            texture.set_editor_property("max_texture_size", cap)
            unreal.EditorAssetLibrary.save_loaded_asset(texture, False)
            after_w, after_h = built_size(texture)

            rows.append({
                "path": path,
                "imported_w": imported[0],
                "imported_h": imported[1],
                "built_w_antes": before_w,
                "built_h_antes": before_h,
                "built_w_depois": after_w,
                "built_h_depois": after_h,
                "lod_group": lod_group,
                "format": str(asset_data.get_tag_value("Format") or ""),
                "status": "ok",
            })
            changed += 1
            unreal.log("  {0}  {1}x{2} -> teto {3}".format(path, imported[0], imported[1], cap))

        except Exception as err:
            failed += 1
            rows.append({
                "path": path,
                "imported_w": imported[0] if imported else 0,
                "imported_h": imported[1] if imported else 0,
                "built_w_antes": 0,
                "built_h_antes": 0,
                "built_w_depois": 0,
                "built_h_depois": 0,
                "lod_group": lod_group,
                "format": "",
                "status": "ERRO: {0}".format(err),
            })
            unreal.log_error("Falhou em {0}: {1}".format(path, err))

    saved_dir = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
    report_path = os.path.join(saved_dir, REPORT_NAME)
    if not os.path.isdir(saved_dir):
        os.makedirs(saved_dir)

    fields = ["path", "imported_w", "imported_h", "built_w_antes", "built_h_antes",
              "built_w_depois", "built_h_depois", "lod_group", "format", "status"]
    with open(report_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    unreal.log("=== Resumo ===")
    unreal.log("  alteradas       : {0}".format(changed))
    unreal.log("  ja dentro do teto: {0}".format(already_ok))
    unreal.log("  UI ignoradas    : {0}".format(skipped_ui))
    unreal.log("  falhas          : {0}".format(failed))
    unreal.log("  relatorio       : {0}".format(report_path))


main()
