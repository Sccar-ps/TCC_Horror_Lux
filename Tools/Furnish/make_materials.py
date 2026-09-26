# Cria (ou atualiza) o material mestre M_LUX_Surface e as instancias usadas nas paredes e tetos do Mapa_B.
# py ".../Tools/Furnish/make_materials.py"
# Assets em /Game/Masion/LUX/Materials. Idempotente: se ja existir, so atualiza parametros.
import unreal

DIR = "/Game/Masion/LUX/Materials"
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
at = unreal.AssetToolsHelpers.get_asset_tools()
SRF = "/Game/Scene_Saloon/Assets/MS/Surfaces/"


def tex(p):
    t = unreal.load_asset(p)
    if not t:
        raise RuntimeError("textura nao encontrada: " + p)
    return t


def sampler_for(t):
    ST = unreal.MaterialSamplerType
    TC = unreal.TextureCompressionSettings
    vt = bool(t.get_editor_property("virtual_texture_streaming"))
    cs = t.get_editor_property("compression_settings")
    srgb = bool(t.get_editor_property("srgb"))
    if cs == TC.TC_NORMALMAP:
        return ST.SAMPLERTYPE_VIRTUAL_NORMAL if vt else ST.SAMPLERTYPE_NORMAL
    if cs == TC.TC_MASKS:
        return ST.SAMPLERTYPE_VIRTUAL_MASKS if vt else ST.SAMPLERTYPE_MASKS
    if cs == TC.TC_GRAYSCALE:
        if vt:
            return ST.SAMPLERTYPE_VIRTUAL_GRAYSCALE if srgb else ST.SAMPLERTYPE_VIRTUAL_LINEAR_GRAYSCALE
        return ST.SAMPLERTYPE_GRAYSCALE if srgb else ST.SAMPLERTYPE_LINEAR_GRAYSCALE
    if cs == TC.TC_ALPHA:
        return ST.SAMPLERTYPE_VIRTUAL_ALPHA if vt else ST.SAMPLERTYPE_ALPHA
    if vt:
        return ST.SAMPLERTYPE_VIRTUAL_COLOR if srgb else ST.SAMPLERTYPE_VIRTUAL_LINEAR_COLOR
    return ST.SAMPLERTYPE_COLOR if srgb else ST.SAMPLERTYPE_LINEAR_COLOR


def sample_param(m, name, t, x, y):
    e = mel.create_material_expression(m, unreal.MaterialExpressionTextureSampleParameter2D, x, y)
    e.set_editor_property("parameter_name", name)
    e.set_editor_property("texture", t)
    e.set_editor_property("sampler_type", sampler_for(t))
    unreal.log("LUX %s: %s vt=%s" % (name, sampler_for(t), t.get_editor_property("virtual_texture_streaming")))
    return e


def scalar(m, name, val, x, y):
    e = mel.create_material_expression(m, unreal.MaterialExpressionScalarParameter, x, y)
    e.set_editor_property("parameter_name", name)
    e.set_editor_property("default_value", val)
    return e


def build_master():
    """Reconstroi o grafo do mestre a cada execucao (as MIs mantem o parent)."""
    path = DIR + "/M_LUX_Surface"
    if eal.does_asset_exist(path):
        m = unreal.load_asset(path)
        mel.delete_all_material_expressions(m)
    else:
        m = at.create_asset("M_LUX_Surface", DIR, unreal.Material, unreal.MaterialFactoryNew())
    E = unreal
    # UV projetada no mundo (independe do UV das malhas CubeGrid, que varia entre paredes):
    #   parede virada para X -> (y, -z);  parede virada para Y -> (x, -z);  escala = Tiling / 100 cm
    wp = mel.create_material_expression(m, E.MaterialExpressionWorldPosition, -2100, 0)
    vn = mel.create_material_expression(m, E.MaterialExpressionVertexNormalWS, -2100, -200)

    def mask(src, r=False, g=False, b=False, x=-1900, y=0):
        e = mel.create_material_expression(m, E.MaterialExpressionComponentMask, x, y)
        e.set_editor_property("r", r)
        e.set_editor_property("g", g)
        e.set_editor_property("b", b)
        e.set_editor_property("a", False)
        mel.connect_material_expressions(src, "", e, "")
        return e

    def absn(src, x, y):
        e = mel.create_material_expression(m, E.MaterialExpressionAbs, x, y)
        mel.connect_material_expressions(src, "", e, "")
        return e

    nx = absn(mask(vn, r=True, x=-1900, y=-260), -1750, -260)
    ny = absn(mask(vn, g=True, x=-1900, y=-160), -1750, -160)
    wx = mask(wp, r=True, x=-1900, y=0)
    wy = mask(wp, g=True, x=-1900, y=80)
    wz = mask(wp, b=True, x=-1900, y=160)
    neg = mel.create_material_expression(m, E.MaterialExpressionConstant, -1900, 240)
    neg.set_editor_property("r", -1.0)
    wzn = mel.create_material_expression(m, E.MaterialExpressionMultiply, -1750, 180)
    mel.connect_material_expressions(wz, "", wzn, "A")
    mel.connect_material_expressions(neg, "", wzn, "B")
    uvx = mel.create_material_expression(m, E.MaterialExpressionAppendVector, -1600, 40)
    mel.connect_material_expressions(wy, "", uvx, "A")
    mel.connect_material_expressions(wzn, "", uvx, "B")
    uvy = mel.create_material_expression(m, E.MaterialExpressionAppendVector, -1600, 140)
    mel.connect_material_expressions(wx, "", uvy, "A")
    mel.connect_material_expressions(wzn, "", uvy, "B")
    sel = mel.create_material_expression(m, E.MaterialExpressionIf, -1450, 0)
    mel.connect_material_expressions(nx, "", sel, "A")
    mel.connect_material_expressions(ny, "", sel, "B")
    for src, names in ((uvx, ("A > B", "AGreaterThanB")), (uvx, ("A == B", "AEqualsB")),
                       (uvy, ("A < B", "ALessThanB"))):
        ok = False
        for nm in names:
            if mel.connect_material_expressions(src, "", sel, nm):
                ok = True
                break
        unreal.log("LUX If %s -> %s" % (names[1], ok))
    til = scalar(m, "Tiling", 0.4, -1450, 200)
    cm = mel.create_material_expression(m, E.MaterialExpressionConstant, -1450, 300)
    cm.set_editor_property("r", 0.01)
    tils = mel.create_material_expression(m, E.MaterialExpressionMultiply, -1300, 220)
    mel.connect_material_expressions(til, "", tils, "A")
    mel.connect_material_expressions(cm, "", tils, "B")
    uv = mel.create_material_expression(m, E.MaterialExpressionMultiply, -1150, 40)
    mel.connect_material_expressions(sel, "", uv, "A")
    mel.connect_material_expressions(tils, "", uv, "B")
    offu = scalar(m, "OffsetU", 0.0, -1300, 340)
    offv = scalar(m, "OffsetV", 0.0, -1300, 440)
    app = mel.create_material_expression(m, E.MaterialExpressionAppendVector, -1150, 380)
    mel.connect_material_expressions(offu, "", app, "A")
    mel.connect_material_expressions(offv, "", app, "B")
    uvf = mel.create_material_expression(m, E.MaterialExpressionAdd, -1000, 100)
    mel.connect_material_expressions(uv, "", uvf, "A")
    mel.connect_material_expressions(app, "", uvf, "B")

    # cor: dessatura (lerp com a luminancia) e multiplica pelo Tint
    alb = sample_param(m, "Albedo", tex(SRF + "Wall_Fabric_Panel_Old_01/T_Wall_Fabric_Panel_Old_01_D"), -850, -350)
    mel.connect_material_expressions(uvf, "", alb, "UVs")
    lumc = mel.create_material_expression(m, E.MaterialExpressionConstant3Vector, -850, -520)
    lumc.set_editor_property("constant", unreal.LinearColor(0.3, 0.59, 0.11, 1))
    dot = mel.create_material_expression(m, E.MaterialExpressionDotProduct, -600, -500)
    mel.connect_material_expressions(alb, "RGB", dot, "A")
    mel.connect_material_expressions(lumc, "", dot, "B")
    des = scalar(m, "Desaturation", 0.0, -600, -620)
    lerp = mel.create_material_expression(m, E.MaterialExpressionLinearInterpolate, -400, -450)
    mel.connect_material_expressions(alb, "RGB", lerp, "A")
    mel.connect_material_expressions(dot, "", lerp, "B")
    mel.connect_material_expressions(des, "", lerp, "Alpha")
    tint = mel.create_material_expression(m, E.MaterialExpressionVectorParameter, -400, -650)
    tint.set_editor_property("parameter_name", "Tint")
    tint.set_editor_property("default_value", unreal.LinearColor(1, 1, 1, 1))
    bc = mel.create_material_expression(m, E.MaterialExpressionMultiply, -200, -500)
    mel.connect_material_expressions(lerp, "", bc, "A")
    mel.connect_material_expressions(tint, "", bc, "B")
    mel.connect_material_property(bc, "", unreal.MaterialProperty.MP_BASE_COLOR)

    nrm = sample_param(m, "Normal", tex(SRF + "Wall_Fabric_Panel_Old_01/T_Wall_Fabric_Panel_Old_01_N"), -850, 0)
    mel.connect_material_expressions(uvf, "", nrm, "UVs")
    mel.connect_material_property(nrm, "RGB", unreal.MaterialProperty.MP_NORMAL)

    ordp = sample_param(m, "ORD", tex(SRF + "Wall_Fabric_Panel_Old_01/T_Wall_Fabric_Panel_Old_01_ORDp"), -850, 300)
    mel.connect_material_expressions(uvf, "", ordp, "UVs")
    rs = scalar(m, "RoughnessScale", 1.0, -850, 520)
    rm = mel.create_material_expression(m, E.MaterialExpressionMultiply, -500, 350)
    mel.connect_material_expressions(ordp, "G", rm, "A")
    mel.connect_material_expressions(rs, "", rm, "B")
    mel.connect_material_property(rm, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.connect_material_property(ordp, "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    mel.recompile_material(m)
    eal.save_loaded_asset(m)
    return m


def make_mi(name, parent, textures=None, scalars=None, vectors=None):
    path = DIR + "/" + name
    mi = unreal.load_asset(path) if eal.does_asset_exist(path) else \
        at.create_asset(name, DIR, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mi, parent)
    for k, v in (textures or {}).items():
        t = tex(v)
        unreal.log("LUX MI %s %s vt=%s cs=%s" % (name, k, t.get_editor_property("virtual_texture_streaming"),
                                                 t.get_editor_property("compression_settings")))
        mel.set_material_instance_texture_parameter_value(mi, k, t)
    for k, v in (scalars or {}).items():
        mel.set_material_instance_scalar_parameter_value(mi, k, v)
    for k, v in (vectors or {}).items():
        mel.set_material_instance_vector_parameter_value(mi, k, v)
    mel.update_material_instance(mi)
    eal.save_loaded_asset(mi)
    return mi


if not eal.does_directory_exist(DIR):
    eal.make_directory(DIR)
master = build_master()
W = SRF + "Wall_Fabric_Panel_Old_01/T_Wall_Fabric_Panel_Old_01_"
make_mi("MI_LUX_Wallpaper_Old", master,
        textures={"Albedo": W + "D", "Normal": W + "N", "ORD": W + "ORDp"},
        scalars={"Tiling": 0.4, "RoughnessScale": 1.1, "Desaturation": 0.65, "OffsetV": 0.0},
        vectors={"Tint": unreal.LinearColor(0.26, 0.25, 0.23, 1)})
P = SRF + "Wall_Wood_Planks_Cracked_01/T_Wall_Wood_Planks_Cracked_01_"
make_mi("MI_LUX_WoodPlanks_Old", master,
        textures={"Albedo": P + "D", "Normal": P + "N", "ORD": P + "ORDp"},
        scalars={"Tiling": 0.5, "RoughnessScale": 1.0, "Desaturation": 0.3},
        vectors={"Tint": unreal.LinearColor(0.55, 0.5, 0.45, 1)})
A = SRF + "Fabric_Antique_Plain_01/T_Fabric_Antique_Plain_01_"
make_mi("MI_LUX_Wallpaper_Plain", master,
        textures={"Albedo": A + "D", "Normal": A + "N", "ORD": A + "ORDp"},
        scalars={"Tiling": 0.5, "RoughnessScale": 1.0, "Desaturation": 0.3},
        vectors={"Tint": unreal.LinearColor(0.32, 0.30, 0.27, 1)})
plaster = unreal.load_asset("/Game/SICKA_MouldingSet/Materials/MI_PlasterCream")
make_mi("MI_LUX_Plaster_Ceiling", plaster,
        scalars={"Tile": 4.0, "Normal Intensity": 0.35, "Roughness": 0.8},
        vectors={"BaseColor": unreal.LinearColor(0.12, 0.118, 0.11, 1)})
unreal.log("LUX materiais OK")
