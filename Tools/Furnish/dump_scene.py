# Somente leitura: dump do mapa aberto + catalogo de assets para mobiliar (UE 5.8).
# Rodar no console do editor:
#   py "C:/Users/bruno/Documents/Unreal Projects/TCC_Horror_Lux/Tools/Furnish/dump_scene.py"
# Saida: Saved/Furnish/scene_actors.tsv, Saved/Furnish/assets.tsv, Saved/Furnish/dump_log.txt
import os, unreal

saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUTDIR = os.path.join(saved, "Furnish")
os.makedirs(OUTDIR, exist_ok=True)
LOG = []


def log(s):
    LOG.append(str(s))


def gp(obj, name, default=None):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return default


def v3(v):
    return "%.1f,%.1f,%.1f" % (v.x, v.y, v.z)


def r3(r):
    return "%.1f,%.1f,%.1f" % (r.roll, r.pitch, r.yaw)


ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
w = ues.get_editor_world()
log("mapa: %s" % w.get_path_name())

# ---------------- atores ----------------
rows = ["label\tclass\tfolder\tloc\trot\tscale\tb_origin\tb_extent\tmesh\tmaterials\textra\thidden"]
actors = unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor)
for a in actors:
    try:
        cls = a.get_class().get_name()
        if cls in ("WorldSettings", "Brush", "AbstractNavData", "GameplayDebuggerPlayerManager", "ChaosDebugDrawActor"):
            continue
        org, ext = a.get_actor_bounds(False)
        folder = str(a.get_folder_path())
        mesh, mats, extra = "", "", ""
        smcs = a.get_components_by_class(unreal.StaticMeshComponent)
        meshes = []
        for c in smcs:
            sm = gp(c, "static_mesh")
            if sm:
                meshes.append(sm.get_path_name().split(".")[0])
                if not mats:
                    try:
                        mats = "|".join([(m.get_path_name().split(".")[0] if m else "None") for m in c.get_materials()])
                    except Exception:
                        pass
        mesh = "|".join(meshes[:6]) + ("|+%d" % (len(meshes) - 6) if len(meshes) > 6 else "")
        for lc in a.get_components_by_class(unreal.LightComponentBase):
            col = gp(lc, "light_color")
            extra += "%s I=%s col=(%s,%s,%s) rad=%s shadows=%s mob=%s; " % (
                lc.get_class().get_name(), round(gp(lc, "intensity", 0), 3),
                getattr(col, "r", "?"), getattr(col, "g", "?"), getattr(col, "b", "?"),
                gp(lc, "attenuation_radius"), gp(lc, "cast_shadows"), gp(lc, "mobility"))
        for dc in a.get_components_by_class(unreal.DecalComponent):
            m = gp(dc, "decal_material")
            extra += "Decal %s size=%s; " % (m.get_path_name() if m else None, gp(dc, "decal_size"))
        for ac in a.get_components_by_class(unreal.AudioComponent):
            s = gp(ac, "sound")
            extra += "Audio %s; " % (s.get_path_name() if s else None)
        hid = a.is_hidden_ed() if hasattr(a, "is_hidden_ed") else ""
        rows.append("\t".join([a.get_actor_label(), cls, folder, v3(a.get_actor_location()), r3(a.get_actor_rotation()),
                               v3(a.get_actor_scale3d()), v3(org), v3(ext), mesh, mats, extra.strip(), str(hid)]))
    except Exception as e:
        log("erro ator %s: %s" % (a, e))
open(os.path.join(OUTDIR, "scene_actors.tsv"), "w", encoding="utf-8").write("\n".join(rows))
log("atores: %d" % (len(rows) - 1))

# ---------------- catalogo de assets ----------------
ar = unreal.AssetRegistryHelpers.get_asset_registry()


def tag(ad, name):
    for fn in (lambda: ad.get_tag_value(name),
               lambda: unreal.AssetRegistryHelpers.get_tag_value(ad, name)):
        try:
            r = fn()
            if isinstance(r, tuple):
                r = [x for x in r if isinstance(x, str)]
                r = r[-1] if r else ""
            if r is None:
                r = ""
            return str(r)
        except Exception:
            continue
    return ""


def by_class(pkg, name):
    try:
        return ar.get_assets_by_class(unreal.TopLevelAssetPath(pkg, name), True)
    except Exception as e:
        log("get_assets_by_class %s falhou: %s" % (name, e))
        return []


arows = ["type\tpath\tapprox_size\ttris\tnanite\tmats\textra"]
for ad in by_class("/Script/Engine", "StaticMesh"):
    p = str(ad.package_name)
    if not p.startswith("/Game"):
        continue
    arows.append("\t".join(["SM", p, tag(ad, "ApproxSize"), tag(ad, "Triangles"), tag(ad, "NaniteEnabled"),
                            tag(ad, "Materials"), ""]))
for ad in by_class("/Script/Engine", "Blueprint"):
    p = str(ad.package_name)
    if not p.startswith("/Game"):
        continue
    arows.append("\t".join(["BP", p, "", "", "", "", tag(ad, "ParentClass")]))
for cname in ("MaterialInstanceConstant", "Material"):
    for ad in by_class("/Script/Engine", cname):
        p = str(ad.package_name)
        if not p.startswith("/Game"):
            continue
        arows.append("\t".join(["MAT" if cname == "Material" else "MI", p, "", "", "", "", ""]))
for cname in ("SoundCue", "SoundWave"):
    for ad in by_class("/Script/Engine", cname):
        p = str(ad.package_name)
        if not p.startswith("/Game"):
            continue
        arows.append("\t".join(["SND", p, "", "", "", "", cname]))
open(os.path.join(OUTDIR, "assets.tsv"), "w", encoding="utf-8").write("\n".join(arows))
log("assets: %d" % (len(arows) - 1))
open(os.path.join(OUTDIR, "dump_log.txt"), "w", encoding="utf-8").write("\n".join(LOG))
unreal.log("Furnish dump OK -> " + OUTDIR)
