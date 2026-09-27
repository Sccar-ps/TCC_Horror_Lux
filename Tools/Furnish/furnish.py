# Mobilia e ambientacao do Mapa_B (UE 5.8) - idempotente.
#   py ".../Tools/Furnish/furnish.py"          -> (re)aplica tudo
#   py ".../Tools/Furnish/furnish.py" clear    -> remove tudo e restaura materiais/luzes originais
# Tudo que e criado leva a tag LUX_FURNISH e fica na pasta LUX/ do Outliner.
# Os materiais e luzes originais ficam em Saved/Furnish/furnish_backup.json (gravado so na 1a execucao).
# Uma unica transacao: Ctrl+Z desfaz a execucao inteira.
import os, sys, json, math, unreal

TAG = "LUX_FURNISH"
MODE = sys.argv[1] if len(sys.argv) > 1 else "apply"
WALL_MI = sys.argv[2] if len(sys.argv) > 2 else "MI_LUX_Wallpaper_Old"
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
BACKUP = os.path.join(saved, "Furnish", "furnish_backup.json")
LOG = []

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
W = ues.get_editor_world()


def log(s):
    LOG.append(str(s))


def load(p):
    a = unreal.load_asset(p)
    if not a:
        log("FALTANDO: " + p)
    return a


MS = "/Game/Scene_Saloon/Assets/MS/3D/"
OW = "/Game/OldWest/VOL6/Meshes/"
M = {
    "chair_a": MS + "Res_Fur_Chair_Wood_Old_03/SM_Res_Fur_Chair_Wood_Old_03",
    "chair_b": MS + "Res_Fur_Chair_Wood_Worn_02/SM_Res_Fur_Chair_Wood_Worn_02",
    "stool_w": MS + "Res_Fur_Stool_Wood_Armless_01/SM_Res_Fur_Stool_Wood_Armless_01",
    "stool_m": MS + "Res_Fur_Stool_Metal_Worn_01/SM_Res_Fur_Stool_Metal_Worn_01",
    "table": MS + "His_Wil_Furniture_Table_Wood_Worn_01/SM_His_Wil_Furniture_Table_Wood_Worn_01",
    "shelf": MS + "Ind_Old_Furniture_Shelf_Wood_Worn_01/SM_Ind_Old_Furniture_Shelf_Wood_Worn_01",
    "wshelf": MS + "Res_Rur_Furniture_Shelf_Wood_Old_01/SM_Res_Rur_Furniture_Shelf_Wood_Old_01",
    "chest": MS + "Res_Sto_Chest_Wood_Worn_08/SM_Res_Sto_Chest_Wood_Worn_08",
    "frame": MS + "Urb_Dec_PictureFrame_Wood_Worn_01/SM_Urb_Dec_PictureFrame_Wood_Worn_01",
    "book": MS + "Res_Book_Hardback_Paper_Brown_01/SM_Res_Book_Hardback_Paper_Brown_01",
    "flask": MS + "Res_Sto_Flask_Ceramic_Worn_01/SM_Res_Sto_Flask_Ceramic_Worn_01",
    "bone": MS + "Mis_Ant_Bone_Ornate_01/SM_Mis_Ant_Bone_Ornate_01",
    "lamp_a": MS + "His_Sal_Furniture_Lamp_Wood_Old_02/SM_His_Sal_Furniture_Lamp_Wood_Old_02_A",
    "lamp_b": MS + "His_Sal_Furniture_Lamp_Wood_Old_02/SM_His_Sal_Furniture_Lamp_Wood_Old_02_B",
    "bottle": "/Game/Scene_Saloon/Assets/Custom/His_Sal_Bottle_Glass_01/SM_His_Sal_Bottle_Glass_01",
    "glass": "/Game/Scene_Saloon/Assets/Custom/His_Sal_Glass_01/SM_His_Sal_Glass_01",
    "curtain": "/Game/Scene_Saloon/Assets/Custom/His_Sal_Curtain_01/SM_His_Sal_Curtain_01",
    "piano": OW + "SM_Piano_NN_01a",
    "bench": OW + "SM_Piano_NN_01b",
    "cabinet": OW + "SM_Shelf_NN_12a",
    "board": OW + "SM_Job_Board_NN_01b",
    "deer": OW + "SM_Wall_Deer_Mount_NN_01a",
    "candelabra": OW + "SM_Candles_NN_01a",
    "candle_t": OW + "SM_Candles_NN_01b",
    "candle_s": OW + "SM_Candles_NN_01c",
    "sconce": OW + "SM_Lighting_Outdoor_NN_05a",
    "paper": "/Game/FPMovement/Assets/Meshes/Note/SM_Paper",
    "bar_b": MS + "His_Sal_Bar_Wood_Pack_01/SM_His_Sal_Bar_Wood_Pack_01_B",
    "plate": MS + "His_Med_Tableware_Plate_Metal_Old_01/SM_His_Med_Tableware_Plate_Metal_Old_01",
    "cube": "/Engine/BasicShapes/Cube",
}
# eixo local que e a "frente" de cada malha (calibrado no lineup)
FRONT = {"chair_a": "+X", "chair_b": "+X", "piano": "+Y", "bench": "+Y", "cabinet": "+Y", "board": "+Y",
         "deer": "+Y", "chest": "+Y", "shelf": "+Y", "wshelf": "+Y", "frame": "+Y", "sconce": "+Y",
         "curtain": "-Y", "cube": "+X", "bar_b": "+Y"}
FRONT_ANG = {"+X": 0.0, "+Y": 90.0, "-Y": -90.0, "-X": 180.0}
PAINT = {"canon": "/Game/Scene_Saloon/Materials/MaterialInstances/MI_His_Sal_Painting_Canon_01",
         "saloon": "/Game/Scene_Saloon/Materials/MaterialInstances/MI_His_Sal_Painting_Saloon_01"}
LUXM = "/Game/Masion/LUX/Materials/"

_bounds = {}


def bounds(key):
    if key not in _bounds:
        sm = load(M[key])
        bb = sm.get_bounding_box()
        _bounds[key] = (sm, bb.min, bb.max)
    return _bounds[key]


def rot2(x, y, yaw):
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    return x * c - y * s, x * s + y * c


def put(key, x, y, face=0.0, z=0.0, folder="LUX", label=None, anchor="center", zmode="bottom",
        scale=(1.0, 1.0, 1.0), roll=0.0, pitch=0.0, yaw_add=0.0, mat=None):
    """Coloca a malha com a 'frente' virada para 'face' (graus, mundo).
    anchor=center: centro do bounding box em (x,y). anchor=back: face traseira em (x,y) (encostar na parede).
    zmode: bottom|center|top -> essa parte do bounding box fica na altura z."""
    sm, mn, mx = bounds(key)
    sx, sy, sz = scale
    mnx, mny, mnz = mn.x * sx, mn.y * sy, mn.z * sz
    mxx, mxy, mxz = mx.x * sx, mx.y * sy, mx.z * sz
    f = FRONT.get(key, "+X")
    yaw = face - FRONT_ANG[f] + yaw_add
    px, py = (mnx + mxx) / 2, (mny + mxy) / 2
    if anchor == "back":
        if f == "+X":
            px = mnx
        elif f == "-X":
            px = mxx
        elif f == "+Y":
            py = mny
        elif f == "-Y":
            py = mxy
    pz = {"bottom": mnz, "center": (mnz + mxz) / 2, "top": mxz}[zmode]
    ox, oy = rot2(px, py, yaw)
    loc = unreal.Vector(x - ox, y - oy, z - pz)
    a = eas.spawn_actor_from_object(sm, loc, unreal.Rotator(roll=roll, pitch=pitch, yaw=yaw))
    a.set_actor_scale3d(unreal.Vector(sx, sy, sz))
    if key in COLLIDE and label:
        cxl, cyl = rot2((mnx + mxx) / 2, (mny + mxy) / 2, yaw)
        collider("COL_" + label, unreal.Vector(loc.x + cxl, loc.y + cyl, loc.z + (mnz + mxz) / 2), yaw,
                 (mxx - mnx, mxy - mny, mxz - mnz))
    a.tags = [unreal.Name(TAG)]
    a.set_folder_path(folder)
    if label:
        a.set_actor_label(label)
    if mat:
        a.static_mesh_component.set_material(0, load(mat))
    return a


# Malhas Megascans do Scene_Saloon nao tem colisao simples: o jogador atravessaria.
# Em vez de re-salvar esses .uasset (100+ MB cada no LFS), cada movel ganha um cubo invisivel com perfil InvisibleWall
# (bloqueia o Pawn, nao bloqueia trace de Visibility -> nao atrapalha a interacao).
COLLIDE = {"chair_a", "chair_b", "stool_w", "stool_m", "table", "shelf", "chest", "lamp_a", "bar_b"}


def collider(label, center, yaw, size, folder="LUX/Colisao"):
    cube = load(M["cube"])
    a = eas.spawn_actor_from_object(cube, center, unreal.Rotator(roll=0, pitch=0, yaw=yaw))
    a.set_actor_scale3d(unreal.Vector(max(size[0], 2) / 100.0, max(size[1], 2) / 100.0, max(size[2], 2) / 100.0))
    a.set_actor_label(label)
    a.tags = [unreal.Name(TAG)]
    a.set_folder_path(folder)
    a.set_actor_hidden_in_game(True)
    c = a.static_mesh_component
    c.set_editor_property("visible", False)
    c.set_editor_property("cast_shadow", False)
    c.set_editor_property("affect_distance_field_lighting", False)
    c.set_collision_profile_name("InvisibleWall")
    return a


def floor_lamp(x, y, folder, label):
    """Abajur de chao = haste (_A) + cupula (_B), mesmo pivo."""
    for key, suf in (("lamp_a", "_Base"), ("lamp_b", "_Cupula")):
        sm, mn, mx = bounds(key)
        a = eas.spawn_actor_from_object(sm, unreal.Vector(x, y, 0), unreal.Rotator(0, 0, 0))
        a.tags = [unreal.Name(TAG)]
        a.set_folder_path(folder)
        a.set_actor_label(label + suf)
        if key == "lamp_a":
            collider("COL_" + label, unreal.Vector(x, y, 80), 0, (34, 34, 160))


def frame(x, y, face, zc, folder, label, paint=None, roll=0.0):
    put("frame", x, y, face, zc, folder, label, anchor="back", zmode="center", roll=roll)
    if paint:
        # tela fina atras da moldura (cubo de 1 cm)
        dx, dy = math.cos(math.radians(face)), math.sin(math.radians(face))
        put("cube", x + dx * 0.6, y + dy * 0.6, face, zc, folder, label + "_Tela", anchor="back", zmode="center",
            scale=(0.006, 0.56, 0.80), roll=roll, mat=PAINT[paint])


def light(label, x, y, z, cd, radius, kelvin, shadows, folder="LUX/Luzes"):
    a = eas.spawn_actor_from_class(unreal.PointLight, unreal.Vector(x, y, z), unreal.Rotator(0, 0, 0))
    a.set_actor_label(label)
    a.tags = [unreal.Name(TAG)]
    a.set_folder_path(folder)
    c = a.point_light_component
    c.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
    c.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
    c.set_editor_property("intensity", cd)
    c.set_editor_property("attenuation_radius", radius)
    c.set_editor_property("use_temperature", True)
    c.set_editor_property("temperature", kelvin)
    c.set_editor_property("cast_shadows", shadows)
    c.set_editor_property("source_radius", 3.0)
    c.set_editor_property("soft_source_radius", 6.0)
    c.set_editor_property("volumetric_scattering_intensity", 0.6)
    return a


def decal(label, mat, x, y, z, yaw, pitch, size, folder="LUX/Decals", roll=0.0):
    a = eas.spawn_actor_from_class(unreal.DecalActor, unreal.Vector(x, y, z),
                                   unreal.Rotator(roll=roll, pitch=pitch, yaw=yaw))
    a.set_actor_label(label)
    a.tags = [unreal.Name(TAG)]
    a.set_folder_path(folder)
    d = a.decal
    d.set_decal_material(load(mat))
    d.set_editor_property("decal_size", unreal.Vector(*size))
    return a


def sound(label, snd, x, y, z, volume, spatial, radius=150.0, falloff=700.0, folder="LUX/Som"):
    a = eas.spawn_actor_from_class(unreal.AmbientSound, unreal.Vector(x, y, z), unreal.Rotator(0, 0, 0))
    a.set_actor_label(label)
    a.tags = [unreal.Name(TAG)]
    a.set_folder_path(folder)
    ac = a.audio_component
    ac.set_sound(load(snd))
    ac.set_editor_property("volume_multiplier", volume)
    ac.set_editor_property("allow_spatialization", spatial)
    if spatial:
        ac.set_editor_property("override_attenuation", True)
        att = ac.get_editor_property("attenuation_overrides")
        att.set_editor_property("attenuation_shape_extents", unreal.Vector(radius, 0, 0))
        att.set_editor_property("falloff_distance", falloff)
        ac.set_editor_property("attenuation_overrides", att)
    return a


# ---------------------------------------------------------------- prateleiras (trace para achar os niveis)
import random
RNG = random.Random(1311)


TRACE_VIS = getattr(unreal.TraceTypeQuery, "VISIBILITY", None) or unreal.TraceTypeQuery.TRACE_TYPE_QUERY1


def trace_down(x, y, z0, z1=-5.0):
    hit = unreal.SystemLibrary.line_trace_single(
        W, unreal.Vector(x, y, z0), unreal.Vector(x, y, z1), TRACE_VIS, True, [],
        unreal.DrawDebugTrace.NONE, True)
    if hit is None:
        return None, None
    t = hit.to_tuple()
    if not t[0]:
        return None, None
    return t[5].z, t[9]


def shelf_levels(actor, x, y, ztop):
    zs, z = [], ztop + 10.0
    for _ in range(8):
        hz, ha = trace_down(x, y, z)
        if hz is None or ha != actor or hz < 4.0:
            break
        zs.append(hz)
        z = hz - 4.0
    return zs


def fill_shelf(actor, key, folder, prefix, fill=0.7, extras=("flask", "bottle"), skip_top=False):
    """Enche cada nivel da estante com livros em pe (e um pote/garrafa de vez em quando)."""
    sm, mn, mx = bounds(key)
    yaw = actor.get_actor_rotation().yaw
    ux, uy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    vx, vy = -uy, ux
    org, ext = actor.get_actor_bounds(False)
    L = mx.x - mn.x
    cx, cy = org.x, org.y
    probe = []
    for f in (-0.3, 0.3):
        probe.append(shelf_levels(actor, cx + ux * L * f, cy + uy * L * f, org.z + ext.z))
    levels = sorted(set(round(z, 0) for z in probe[0]) & set(round(z, 0) for z in probe[1]), reverse=True)
    if not levels:
        levels = sorted(set(round(z, 0) for z in probe[0]), reverse=True)
    n = 0
    prev = None
    for i, lz in enumerate(levels):
        clear = (prev - 3.0 - lz) if prev is not None else 999.0
        prev = lz
        if clear < 23.0 or (i == 0 and skip_top):
            continue
        t = -L / 2 + 9.0
        while t < L / 2 - 9.0:
            if RNG.random() > fill:
                t += RNG.uniform(6, 14)
                continue
            if RNG.random() < 0.08 and extras:
                k = RNG.choice(extras)
                put(k, cx + ux * (t + 4) + vx * 2, cy + uy * (t + 4) + vy * 2, 0, lz + 0.2, folder,
                    "%s_Item%d" % (prefix, n))
                t += 11.0
                n += 1
                continue
            for _ in range(RNG.randint(4, 11)):
                if t >= L / 2 - 9.0:
                    break
                sz = RNG.uniform(0.82, 1.18)
                sy = RNG.uniform(0.88, 1.12)
                sx = RNG.uniform(0.8, 1.6)
                put("book", cx + ux * t + vx * 2, cy + uy * t + vy * 2, 0, lz + 0.1, folder,
                    "%s_Livro%d" % (prefix, n), yaw_add=yaw + RNG.uniform(-4, 4), scale=(sx, sy, sz))
                t += 2.2 * sx + 0.3
                n += 1
            t += RNG.uniform(3, 12)
    log("%s: niveis %s, %d itens" % (prefix, levels, n))


# ---------------------------------------------------------------- limpeza
def clear_spawned():
    n = 0
    for tag in (TAG, "LUX_TEMP"):
        for a in unreal.GameplayStatics.get_all_actors_with_tag(W, tag):
            eas.destroy_actor(a)
            n += 1
    log("removidos %d atores LUX" % n)


def actors_by_label():
    d = {}
    for a in unreal.GameplayStatics.get_all_actors_of_class(W, unreal.Actor):
        d[a.get_actor_label()] = a
    return d


def restore_backup():
    if not os.path.exists(BACKUP):
        return
    b = json.load(open(BACKUP, encoding="utf-8"))
    by = actors_by_label()
    for rec in b.get("materials", []):
        a = by.get(rec["actor"])
        if not a:
            continue
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            if c.get_name() == rec["comp"]:
                c.set_editor_property("override_materials",
                                      [unreal.load_asset(p) if p else None for p in rec["overrides"]])
    for rec in b.get("transforms", []):
        a = by.get(rec["actor"])
        if a:
            a.set_actor_scale3d(unreal.Vector(*rec["scale"]))
            a.set_actor_rotation(unreal.Rotator(roll=rec["rot"][0], pitch=rec["rot"][1], yaw=rec["rot"][2]), False)
            a.set_actor_location(unreal.Vector(*rec["loc"]), False, False)
            c = a.static_mesh_component
            c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            c.set_collision_enabled(getattr(unreal.CollisionEnabled, rec.get("collision", "QUERY_AND_PHYSICS")))
    for rec in b.get("lights", []):
        a = by.get(rec["actor"])
        if a:
            lc = a.get_component_by_class(unreal.LightComponent)
            lc.set_editor_property("use_temperature", rec["use_temperature"])
            lc.set_editor_property("temperature", rec["temperature"])
    log("materiais/luzes originais restaurados do backup")


# ---------------------------------------------------------------- superficies
WALL_SKIP_MATS = ("MM_Glass_01a",)
CEILINGS = ("CubeGridToolOutput5", "CubeGridToolOutput6")
EXTRA_WALL_ACTORS = ("Tile_InnerCurveEdge2", "Tile_InnerCurveEdge4")
WARM_LIGHTS = ("RectLight", "RectLight2", "RectLight3", "RectLight5", "RectLight6", "RectLight7")


def surfaces(backup):
    wall = load(LUXM + WALL_MI)
    ceil = load(LUXM + "MI_LUX_Plaster_Ceiling")
    if not wall or not ceil:
        log("materiais LUX ausentes: rode make_materials.py antes")
        return
    n = 0
    for a in unreal.GameplayStatics.get_all_actors_of_class(W, unreal.StaticMeshActor):
        lab = a.get_actor_label()
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            sm = c.get_editor_property("static_mesh")
            if not sm:
                continue
            gen = "/Masion/_GENERATED/" in sm.get_path_name()
            if not gen and lab not in EXTRA_WALL_ACTORS:
                continue
            backup.append({"actor": lab, "comp": c.get_name(),
                           "overrides": [(m.get_path_name() if m else None)
                                         for m in c.get_editor_property("override_materials")]})
            mats = c.get_materials()
            for i, m in enumerate(mats):
                if m and m.get_name() in WALL_SKIP_MATS:
                    continue
                c.set_material(i, ceil if lab in CEILINGS else wall)
                n += 1
    log("slots de material trocados: %d" % n)


def warm_lights(backup):
    by = actors_by_label()
    for lab in WARM_LIGHTS:
        a = by.get(lab)
        if not a:
            continue
        lc = a.get_component_by_class(unreal.LightComponent)
        backup.append({"actor": lab, "use_temperature": lc.get_editor_property("use_temperature"),
                       "temperature": lc.get_editor_property("temperature")})
        lc.set_editor_property("use_temperature", True)
        lc.set_editor_property("temperature", 4500.0)


# ---------------------------------------------------------------- comodos
# Faces internas das paredes (cm), medidas da malha:
#   Sala       x[-3000,-2052]  y[-1940,-350]   porta de saida em x~-2294 (parede sul)
#   Corredor   x[-3402,-3149]  y[-700,850]
#   Quarto     x[-3614,-2510]  y[900,1740]
#   Escritorio x[-3855,-3107]  y[-1500,-729]
# ---------------------------------------------------------------- escala de referencia
# Personagem (BP_Player_Cowboy): capsula 192 x 80 cm (half 96, raio 40), cabeca ~175 cm, camera/olho a 166 cm
# (medido no PIE, claude/MixamoFP_setup.md). Tudo que e "de parede" usa essas alturas.
EYE = 166.0
ART_C = 155.0      # centro de quadro em parede livre (~10 cm abaixo do olho, padrao de galeria)
SCONCE_C = 180.0   # centro da arandela (lampada acima da linha do olho, sem ofuscar)
ABOVE_FURN = 22.0  # folga entre o topo do movel e a base do quadro pendurado acima dele
NS_H = 52.3        # altura do criado-mudo (mesa Megascans na altura natural, tampo 47 x 47)

# Moveis do Fab que ja estavam no mapa, em tamanho real (escala uniforme):
#   rack+TV 180 x 41 x 96 | sofa 3 lugares 210 x 109 x 92 | cama king 198 x 217 x 83 | capacho 90 x 60
EXISTING_SCALE = {"meubletv1": 0.2034, "vintage_sofa_23mb": 0.105, "Bed": 0.027}


def escala_existentes(tbk):
    by = actors_by_label()

    def rec(a):
        l, r, s = a.get_actor_location(), a.get_actor_rotation(), a.get_actor_scale3d()
        tbk.append({"actor": a.get_actor_label(), "loc": [l.x, l.y, l.z], "rot": [r.roll, r.pitch, r.yaw],
                    "scale": [s.x, s.y, s.z]})

    def refresh(a):
        # set_actor_scale3d por Python nao reconstroi o corpo de colisao complexa no editor;
        # desligar/religar a colisao forca a reconstrucao (senao traces batem na escala antiga)
        c = a.static_mesh_component
        ce = c.get_collision_enabled()
        c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        c.set_collision_enabled(ce)

    def mesh_bb(a):
        bb = a.static_mesh_component.get_editor_property("static_mesh").get_bounding_box()
        return bb.min, bb.max

    a = by.get("meubletv1")          # yaw ~180: +Y local aponta para o sul; costas na parede norte (y=-350)
    if a:
        rec(a)
        s = EXISTING_SCALE["meubletv1"]
        mn, mx = mesh_bb(a)
        a.set_actor_scale3d(unreal.Vector(s, s, s))
        a.set_actor_location(unreal.Vector(-2316.5, -350.0 - mx.y * s - 0.5, -mn.z * s), False, False)
        refresh(a)
    a = by.get("vintage_sofa_23mb")  # yaw 0, frente em +Y; frente a 2,3 m da tela (TV de ~40")
    if a:
        rec(a)
        s = EXISTING_SCALE["vintage_sofa_23mb"]
        mn, mx = mesh_bb(a)
        a.set_actor_scale3d(unreal.Vector(s, s, s))
        a.set_actor_location(unreal.Vector(-2316.5 - (mn.x + mx.x) / 2 * s, SOFA_FRONT - mx.y * s, -mn.z * s),
                             False, False)
        refresh(a)
    a = by.get("Bed")                # yaw ~180: cabeceira em -Y local = parede norte (y=1740)
    if a:
        rec(a)
        s = EXISTING_SCALE["Bed"]
        mn, mx = mesh_bb(a)
        a.set_actor_scale3d(unreal.Vector(s, s, s))
        a.set_actor_location(unreal.Vector(BED_X, 1738.0 + mn.y * s, -mn.z * s), False, False)
        refresh(a)
        # A colisao simples do asset Bed e uma caixa com Z = 11063 (3,6x a altura da malha) e o asset usa
        # "Simple as Complex": sobrava uma parede invisivel ate ~190 cm acima da cama que bloqueava traces
        # (lanterna/interacao). Colisao do componente desligada; o cubo COL_Bed (InvisibleWall) bloqueia o jogador.
        a.static_mesh_component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    a = by.get("SM_Doormat")
    if a:
        rec(a)
        a.set_actor_scale3d(unreal.Vector(1.5, 1.5, 1.0))
        a.set_actor_location(unreal.Vector(-2289.0, -1940.0 + 30.0 + 6.0, 0.0), False, False)
        refresh(a)


TV_FRONT = -350.0 - 101.617 * 0.2034 * 2 - 0.5      # face da frente do rack (~ -392)
SOFA_FRONT = TV_FRONT - 230.0                         # distancia de visao ~2,3 m
SOFA_BACK = SOFA_FRONT - 1038.1 * 0.105               # profundidade 109 cm
SOFA_Y = (SOFA_FRONT + SOFA_BACK) / 2
BED_X = -2900.0
BED_HALF_W = 3660.726 * 0.027                         # 98,8
BED_FOOT = 1738.0 - 2 * 4017.3 * 0.027                # ~1521


def sala():
    F = "LUX/Sala"
    # --- canto da TV (medidas reais: mesa de centro 40 cm a frente do sofa, 1,1 m livres ate o rack)
    ct_y = SOFA_FRONT + 40.0 + 39.3
    put("table", -2316, ct_y, 0, 0, F, "Sala_MesaCentro")
    put("book", -2326, ct_y - 12, 0, 53.4, F, "Sala_Livro1", pitch=90, yaw_add=10)
    put("book", -2328, ct_y - 9, 0, 55.6, F, "Sala_Livro2", pitch=90, yaw_add=-15)
    put("glass", -2290, ct_y + 14, 0, 52.4, F, "Sala_Copo")
    put("bottle", -2350, ct_y + 18, 0, 52.4, F, "Sala_Garrafa")
    floor_lamp(-2316 + 105 + 8 + 31, SOFA_Y, F, "Sala_Abajur")
    put("stool_m", -2316 - 105 - 8 - 20, SOFA_Y, 0, 0, F, "Sala_BanquinhoLateral")
    put("candle_s", -2316 - 105 - 8 - 20, SOFA_Y, 0, 58.2, F, "Sala_Vela_Banquinho")
    # quadros ao lado da TV, simetricos ao eixo do rack, centro na altura de galeria
    frame(-2520, -350, -90, ART_C, F, "Sala_Quadro_N1", paint="saloon", roll=1)
    frame(-2112, -350, -90, ART_C + 6, F, "Sala_Quadro_N2", roll=-3)
    # --- piano na parede oeste (piano de armario real: 163 x 73 x 142)
    put("piano", -2999, -1080, 0, 0, F, "Sala_Piano", anchor="back")
    put("bench", -2896, -1080, 0, 0, F, "Sala_Piano_Banco")
    put("candle_t", -2985, -1150, 0, 141.8, F, "Sala_Piano_Vela1")
    put("candle_t", -2985, -1010, 0, 141.8, F, "Sala_Piano_Vela2")
    # cervo: base 43 cm acima do tampo do piano (acima das velas de 51 cm)
    put("deer", -2999, -1080, 0, 141.7 + 51.5 + 12, F, "Sala_Cervo", anchor="back")
    frame(-3000, -1550, 0, ART_C, F, "Sala_Quadro_O1", paint="canon", roll=1)
    # --- mesa de jantar posta para tres (150 x 90 x 76), centro livre da sala
    dx, dy = -2350.0, -1250.0
    put("table", dx, dy, 0, 0, F, "Sala_MesaJantar", scale=(1.9, 1.15, 1.45))
    dtop = 52.3 * 1.45 + 0.1
    hx, hy = 39.2 * 1.9, 39.3 * 1.15
    put("chair_a", dx - 37, dy + hy + 16, -90, 0, F, "Sala_Jantar_Cadeira1")
    put("chair_b", dx + 37, dy + hy + 16, -90, 0, F, "Sala_Jantar_Cadeira2", yaw_add=7)
    put("chair_b", dx - 37, dy - hy - 14, 90, 0, F, "Sala_Jantar_Cadeira3", yaw_add=-5)
    put("chair_a", dx + 37, dy - hy - 30, 90, 0, F, "Sala_Jantar_Cadeira4", yaw_add=18)   # afastada
    put("chair_a", dx + hx + 40, dy, 180, 0, F, "Sala_Jantar_Cabeceira")
    for i, (px, py) in enumerate(((dx - 37, dy + hy - 20), (dx + 37, dy + hy - 20), (dx + hx - 20, dy))):
        put("plate", px, py, 0, dtop, F, "Sala_Jantar_Prato%d" % (i + 1))
        put("glass", px + 16, py - 12 if py > dy else py + 12, 0, dtop, F, "Sala_Jantar_Copo%d" % (i + 1))
    put("candle_t", dx, dy, 0, dtop, F, "Sala_Jantar_Vela")
    put("bottle", dx - 20, dy - 18, 0, dtop, F, "Sala_Jantar_Garrafa")
    # --- entrada (parede sul)
    put("chest", -2600, -1939, 90, 0, F, "Sala_Bau", anchor="back", scale=(0.85, 0.85, 0.85))  # 88 x 58 x 69
    est = put("shelf", -2150, -1939, 90, 0, F, "Sala_Estante", anchor="back")
    fill_shelf(est, "shelf", F, "Sala_Estante", fill=0.55)
    # --- parede leste
    put("wshelf", -2052, -1500, 180, 145, F, "Sala_Prateleira", anchor="back", zmode="center")
    for i, by in enumerate((-1525, -1521, -1517)):
        put("book", -2062, by, 180, 156.6, F, "Sala_Prateleira_Livro%d" % (i + 1), yaw_add=90)
    put("flask", -2062, -1480, 0, 156.6, F, "Sala_Prateleira_Pote")
    frame(-2052, -1000, 180, ART_C, F, "Sala_Quadro_L1", roll=-2)
    # --- canto de leitura (sudoeste)
    put("chair_a", -2880, -1790, 55, 0, F, "Sala_Cadeira_Leitura")
    put("candelabra", -2955, -1890, 0, 0, F, "Sala_Candelabro")


def corredor():
    F = "LUX/Corredor"
    apa = put("shelf", -3150, 350, 180, 0, F, "Corredor_Aparador", anchor="back")
    fill_shelf(apa, "shelf", F, "Corredor_Aparador", fill=0.45)
    put("candle_s", -3165, 300, 0, 127.5, F, "Corredor_Aparador_Vela")
    put("book", -3165, 385, 0, 128.6, F, "Corredor_Aparador_Livro1", pitch=90, yaw_add=80)
    put("book", -3165, 388, 0, 130.8, F, "Corredor_Aparador_Livro2", pitch=90, yaw_add=95)
    put("chair_b", -3150, -250, 180, 0, F, "Corredor_Cadeira", anchor="back")
    for lab, sy in (("Corredor_Arandela1", -100), ("Corredor_Arandela2", 620)):
        a = put("sconce", -3149, sy, 180, SCONCE_C, F, lab, anchor="back", zmode="center")
        a.static_mesh_component.set_editor_property("cast_shadow", False)  # a luz fica dentro da lanterna
    # molduras vazias (memorias perdidas) + uma com pintura, todas na linha do olho
    frame(-3402, 69, 0, ART_C + 3, F, "Corredor_Quadro_O1", roll=3)
    frame(-3402, -450, 0, ART_C - 3, F, "Corredor_Quadro_O2")
    frame(-3402, 560, 0, ART_C + 5, F, "Corredor_Quadro_O3", paint="canon", roll=-6)
    frame(-3149, 150, 180, ART_C, F, "Corredor_Quadro_L1")
    # acima do aparador (topo 127): base 22 cm acima
    frame(-3149, 350, 180, 127.4 + ABOVE_FURN + 45.1, F, "Corredor_Quadro_L2", roll=2)


def quarto():
    global NS_H
    F = "LUX/Quarto"
    # altura do colchao da cama ja escalada -> criados-mudos na mesma altura
    # colchao da cama escalada fica a ~48 cm (medido na vista lateral); criado-mudo na altura natural da mesa
    NS_H = 52.3
    ns_s = (0.6, 0.6, 1.0)
    for side, sx in (("L", BED_X + BED_HALF_W + 5 + 23.6), ("O", BED_X - BED_HALF_W - 5 - 23.6)):
        put("table", sx, 1712, 0, 0, F, "Quarto_CriadoMudo_" + side, scale=ns_s)
        put("book", sx - 6, 1705, 0, NS_H + 1.2, F, "Quarto_Livro_" + side, pitch=90, yaw_add=25 if side == "L" else -30)
        put("glass", sx + 12, 1698, 0, NS_H + 0.1, F, "Quarto_Copo_" + side)
    put("candle_s", BED_X + BED_HALF_W + 5 + 23.6 + 8, 1722, 0, NS_H + 0.1, F, "Quarto_Vela")
    arm = put("cabinet", -3613, 1300, 0, 0, F, "Quarto_Armario", anchor="back")
    fill_shelf(arm, "cabinet", F, "Quarto_Armario", fill=0.5, skip_top=True)
    # comoda: balcao de 150 x 70 x 106 reduzido para 150 x 49 x 95
    put("bar_b", -3500, 901, 90, 0, F, "Quarto_Comoda", anchor="back", scale=(1.0, 0.7, 0.9))
    ctop = 106.1 * 0.9 + 0.1
    put("candle_t", -3545, 918, 0, ctop, F, "Quarto_Comoda_Vela")
    put("flask", -3470, 920, 0, ctop, F, "Quarto_Comoda_Pote")
    put("book", -3440, 918, 0, ctop + 1.1, F, "Quarto_Comoda_Livro", pitch=90, yaw_add=15)
    frame(-3500, 900, 90, ctop + ABOVE_FURN + 45.1, F, "Quarto_Quadro_Comoda", roll=-1)
    put("chest", BED_X, BED_FOOT - 30 - 26, -90, 0, F, "Quarto_Bau", scale=(0.75, 0.75, 0.75))  # 77 x 51 x 61, abaixo do colchao+edredom
    # canto de estar (sudeste): mesinha + 2 cadeiras
    tx, ty = -2700.0, 1130.0
    put("table", tx, ty, 0, 0, F, "Quarto_Mesinha")
    put("candle_t", tx + 10, ty + 8, 0, 52.4, F, "Quarto_Mesinha_Vela")
    put("book", tx - 12, ty - 10, 0, 53.5, F, "Quarto_Mesinha_Livro", pitch=90, yaw_add=40)
    put("chair_a", tx, ty - 39.3 - 18, 90, 0, F, "Quarto_Cadeira")
    put("chair_b", tx + 39.2 + 34, ty + 6, 180, 0, F, "Quarto_Cadeira2", yaw_add=12)
    floor_lamp(-2546, 1698, F, "Quarto_Abajur")
    # quadro acima da cabeceira (~83 cm): base 30 cm acima
    frame(BED_X, 1740, -90, 83 + 30 + 45.1, F, "Quarto_Quadro_Cama", paint="canon")
    frame(-2510, 1400, 180, ART_C, F, "Quarto_Quadro_L1", roll=-3)


def escritorio():
    F = "LUX/Escritorio"
    # mesa (mesa baixa esticada para altura de escrivaninha)
    put("table", -3854, -1122, 0, 0, F, "Escritorio_Mesa", anchor="back", scale=(1.0, 1.75, 1.45))
    top = 52.3 * 1.45 + 0.1
    for i, (px, py, yw) in enumerate(((-3812, -1150, 12), (-3800, -1100, -20), (-3788, -1132, 35),
                                      (-3818, -1076, 5), (-3796, -1168, -8))):
        put("paper", px, py, 0, top + i * 0.15, F, "Escritorio_Papel%d" % (i + 1), yaw_add=yw)
    put("book", -3833, -1066, 0, top + 1.1, F, "Escritorio_Livro1", pitch=90, yaw_add=5)
    put("book", -3832, -1068, 0, top + 3.3, F, "Escritorio_Livro2", pitch=90, yaw_add=-12)
    put("candle_s", -3836, -1176, 0, top, F, "Escritorio_Vela")
    put("bottle", -3840, -1045, 0, top, F, "Escritorio_Garrafa")
    put("glass", -3806, -1052, 0, top, F, "Escritorio_Copo")
    put("bone", -3786, -1186, 0, top, F, "Escritorio_Osso", yaw_add=40)
    put("chair_b", -3742, -1118, 180, 0, F, "Escritorio_Cadeira", yaw_add=-12)
    for i, (px, py, yw) in enumerate(((-3700, -1180, 50), (-3660, -1050, -70), (-3720, -960, 15))):
        put("paper", px, py, 0, 0.2, F, "Escritorio_PapelChao%d" % (i + 1), yaw_add=yw)
    # quadro de investigacao
    put("board", -3232, -1499, 90, 0, F, "Escritorio_QuadroInvestigacao", anchor="back")
    for i, (px, pz) in enumerate(((-3280, 150), (-3246, 166), (-3206, 146), (-3182, 118), (-3262, 112), (-3218, 104))):
        put("paper", px, -1487.5, 0, pz, F, "Escritorio_QuadroPapel%d" % (i + 1), zmode="center", roll=-90)
    # moveis na parede leste
    arm = put("cabinet", -3108, -900, 180, 0, F, "Escritorio_Armario", anchor="back")
    fill_shelf(arm, "cabinet", F, "Escritorio_Armario", fill=0.75, skip_top=True)
    est = put("shelf", -3108, -1220, 180, 0, F, "Escritorio_Estante", anchor="back")
    fill_shelf(est, "shelf", F, "Escritorio_Estante", fill=0.85)
    put("chest", -3700, -730, -90, 0, F, "Escritorio_Bau", anchor="back", scale=(0.85, 0.85, 0.85))
    put("candelabra", -3780, -1392, 0, 0, F, "Escritorio_Candelabro")
    frame(-3550, -729, -90, ART_C, F, "Escritorio_Quadro", paint="saloon", roll=-2)
    # cortinas nas 3 janelas
    put("curtain", -3854, -895, 0, 306, F, "Escritorio_Cortina_O1", anchor="back", zmode="top")
    put("curtain", -3854, -1348, 0, 306, F, "Escritorio_Cortina_O2", anchor="back", zmode="top")
    put("curtain", -3468, -1499, 90, 306, F, "Escritorio_Cortina_S", anchor="back", zmode="top")


def colisao_existentes():
    """Cama que ja estava no mapa: colisao do asset desligada (ver escala_existentes), cubo no tamanho real."""
    by = actors_by_label()
    for lab in ("Bed",):   # sofa e rack ja tem colisao convexa no asset
        a = by.get(lab)
        if not a:
            continue
        org, ext = a.get_actor_bounds(False)
        collider("COL_" + lab, org, 0, (ext.x * 2, ext.y * 2, ext.z * 2))


def luzes():
    # Escala relativa as luzes do mapa (RectLights de teto: 0,6-1,3 cd). Vela ~ 1/30 de uma luz de teto.
    # Alturas: lampada do abajur no centro da cupula (138 cm); chama = topo do castical + 4 cm.
    dtop = 52.3 * 1.45 + 0.1
    light("LUX_Luz_Sala_Abajur", -2316 + 105 + 8 + 31, SOFA_Y, 138, 1.0, 480, 2700, True)
    light("LUX_Luz_Sala_VelasPiano", -2975, -1080, 141.7 + 51.2 + 4, 0.05, 240, 2200, False)
    light("LUX_Luz_Sala_Candelabro", -2955, -1890, 164, 0.05, 240, 2200, False)
    light("LUX_Luz_Sala_Vela", -2316 - 105 - 8 - 20, SOFA_Y, 58.2 + 41.7 + 4, 0.04, 200, 2200, False)
    light("LUX_Luz_Sala_VelaJantar", -2350, -1250, dtop + 51.2 + 4, 0.05, 260, 2200, False)
    light("LUX_Luz_Corredor_Arandela1", -3172, -100, SCONCE_C - 2, 0.35, 360, 2700, True)
    light("LUX_Luz_Corredor_Arandela2", -3172, 620, SCONCE_C - 2, 0.35, 360, 2700, False)
    light("LUX_Luz_Corredor_Vela", -3168, 300, 127.5 + 41.7 + 4, 0.04, 200, 2200, False)
    light("LUX_Luz_Quarto_Abajur", -2546, 1698, 138, 0.9, 480, 2700, True)
    light("LUX_Luz_Quarto_Vela", BED_X + BED_HALF_W + 5 + 23.6 + 8, 1722, NS_H + 41.7 + 4, 0.05, 240, 2200, False)
    light("LUX_Luz_Quarto_VelaComoda", -3545, 918, 106.1 * 0.9 + 51.2 + 4, 0.04, 220, 2200, False)
    light("LUX_Luz_Quarto_VelaMesinha", -2690, 1138, 52.4 + 51.2 + 4, 0.04, 220, 2200, False)
    light("LUX_Luz_Escritorio_Vela", -3836, -1176, 52.3 * 1.45 + 41.7 + 4, 0.1, 380, 2200, True)
    light("LUX_Luz_Escritorio_Candelabro", -3780, -1392, 164, 0.05, 240, 2200, False)


def decals():
    D = "/Game/Scene_Saloon/Assets/MS/Decals/"
    dirt_a = D + "Decal_Debris_Dirt_02/MI_Decal_Debris_Dirt_02_A"
    dirt_b = D + "Decal_Debris_Dirt_02/MI_Decal_Debris_Dirt_02_B"
    leak = D + "Decal_Leak_Dirt_02/MI_Decal_Leak_Dirt_02"
    # dirt_b (poeira clara) ficou branco demais sob a exposicao do mapa; so o _A (mancha escura)
    for i, (x, y, m, yw) in enumerate(((-2880, -1850, dirt_a, 20), (-2150, -1600, dirt_a, 70), (-3280, 150, dirt_a, 0),
                                       (-3300, -560, dirt_a, 45), (-3480, -1250, dirt_a, 110), (-3450, 1480, dirt_a, 10),
                                       (-2650, -1150, dirt_a, 160))):
        decal("LUX_Decal_Chao%d" % (i + 1), m, x, y, 0, yw, -90, (40, 180, 180))
    for i, (x, y, yaw) in enumerate(((-2960, -350, 90), (-3000, -1330, 180), (-3402, 420, 180), (-3149, 20, 0),
                                     (-3720, -1500, -90), (-3450, 1694, 90), (-2510, 1080, 0))):
        decal("LUX_Decal_Infiltracao%d" % (i + 1), leak, x, y, 262, yaw, 0, (30, 160, 260))


def sons():
    amb = "/Game/Masion/LUX/Audio/SW_LUX_Amb_Memorias"
    wind = "/Game/FPMovement/Assets/Audio/Environment/SW_Wind_calm"
    if unreal.EditorAssetLibrary.does_asset_exist(amb):
        sound("LUX_Som_Ambiente", amb, -3000, -400, 200, 0.33, False)  # 27/09: 0.22 -> 0.33 (ambiente x1.5, pedido do Gabriel)
    for i, (x, y) in enumerate(((-3390, 70), (-3830, -1120), (-2075, -1760))):
        sound("LUX_Som_Vento%d" % (i + 1), wind, x, y, 200, 0.53, True, 120, 650)  # 27/09: 0.35 -> 0.53 (x1.5)


def prepare_audio():
    src = "/Game/Backrooms_Ambience/WAVs/5_LOOP_Backrooms_Memories__by_juanjo_sound__wav"
    dst = "/Game/Masion/LUX/Audio/SW_LUX_Amb_Memorias"
    eal = unreal.EditorAssetLibrary
    if not eal.does_asset_exist(dst):
        if not eal.does_directory_exist("/Game/Masion/LUX/Audio"):
            eal.make_directory("/Game/Masion/LUX/Audio")
        if eal.does_asset_exist(src):
            eal.duplicate_asset(src, dst)
    s = unreal.load_asset(dst)
    if s:
        if not s.get_editor_property("looping"):
            s.set_editor_property("looping", True)
        eal.save_asset(dst, False)


# ---------------------------------------------------------------- main
if MODE not in ("apply", "clear"):
    raise SystemExit("modo desconhecido: " + MODE)
if MODE == "apply":
    prepare_audio()  # fora da transacao: cria asset
with unreal.ScopedEditorTransaction("LUX: mobiliar Mapa_B (%s)" % MODE):
    clear_spawned()
    restore_backup()
    if MODE == "apply":
        mats_bk, lights_bk, tr_bk = [], [], []
        surfaces(mats_bk)
        warm_lights(lights_bk)
        escala_existentes(tr_bk)
        bk = json.load(open(BACKUP, encoding="utf-8")) if os.path.exists(BACKUP) else {}
        changed = False
        for k, v in (("materials", mats_bk), ("lights", lights_bk), ("transforms", tr_bk)):
            if k not in bk:
                bk[k] = v
                changed = True
        if changed:
            json.dump(bk, open(BACKUP, "w", encoding="utf-8"), indent=1)
        for fn in (sala, corredor, quarto, escritorio, colisao_existentes, luzes, decals, sons):
            try:
                fn()
            except Exception as e:
                log("ERRO em %s: %s" % (fn.__name__, e))
        log("atores LUX: %d" % len(unreal.GameplayStatics.get_all_actors_with_tag(W, TAG)))
open(os.path.join(saved, "Furnish", "furnish_log.txt"), "w", encoding="utf-8").write("\n".join(LOG))
unreal.log("LUX furnish (%s) OK" % MODE)
