# LUX: pega de "espada" para a vela (28/09, pedido: a mao fecha na HASTE do castical, em pe).
# Diagnostico (vela_mao_probe*.py): as animacoes da lanterna fecham o punho num cilindro HORIZONTAL apontado para a frente
# (eixo = Y do socket hand_r_Flashlight, raio ~2,9 cm), com o antebraco em pe. Uma haste vertical nao passa nesse punho:
# a vela ficava 3,6-10,6 cm longe dos dedos, alinhada com o comprimento da mao.
# Correcao estrutural (nao mexe nas animacoes da lanterna, que sao do FPMovement):
#  1) Pose de pega calculada dos ossos reais (idle, quadro 0): a haste fica na palma, logo abaixo dos nos dos dedos
#     (MCP); cada dedo (e o polegar) fecha ate encostar na haste; o punho gira para a haste ficar VERTICAL; ombro e
#     cotovelo saem de um IK de 2 ossos, escolhendo o alvo que menos muda o pulso da animacao original.
#  2) AS_LuxVela_Pega: essa pose gravada como ADITIVA em espaco local (base = AS_Flashlight_Idle, quadro 0).
#  3) ABP_Arms_Cowboy: Apply Additive (AS_LuxVela_Pega) no ramo da lanterna, antes do Blend Poses by bool.
#     Vale para idle, andar, pulo e para as montagens de puxar/guardar (o Slot 'Arms' esta dentro do ramo).
#  4) Socket hand_r_Vela no osso hand_r (SKM_Metahuman_Arms), no centro da haste dentro do punho, Z = eixo da haste.
# Modos: sondar (so calcula e mostra) | instalar | verificar.   py "<projeto>/Tools/Player/vela_pega.py" sondar
import math, os, shutil, sys, traceback
import unreal

EAL, BEL, BGE = unreal.EditorAssetLibrary, unreal.BlueprintEditorLibrary, unreal.BlueprintGraphEditor
AL, APE = unreal.AnimationLibrary, unreal.AnimPoseExtensions
IDLE = "/Game/FPMovement/Demo/Character/Animations/Flashlight/AS_Flashlight_Idle"
SKM = "/Game/FPMovement/Demo/Character/Arms/MetaHuman/SKM_Metahuman_Arms"
ABP = "/Game/Characters/MixamoFP/Arms/ABP_Arms_Cowboy"
DIR = "/Game/Masion/LUX/Player/Anim"
PEGA = DIR + "/AS_LuxVela_Pega"
SOCKET = "hand_r_Vela"
# camera <- FirstPersonMesh (template herdado do BP_Player; lido no PIE: loc (-13.77, 0, -163.17), yaw -90)
MESH_NA_CAMERA = ((-13.765, 0.0, -163.173), -90.0)
# 28/09: 0.42 = menor escala em que os 4 dedos fecham na haste sem entrar no prato/copinho (modo "escalas":
# 0.30 -> indicador 0,6 cm dentro do copinho e minimo 0,5 cm dentro do colar; 0.42 -> folga 0,0 em todos).
# O punho tem ~7 cm do minimo ao indicador; a haste livre precisa de ~7,5 cm. Vela de 17,5 cm (castical de mao real).
ESCALA_VELA = 0.42
HASTE_R = 1.75 * ESCALA_VELA          # raio da haste do SM_Candles_NN_01c (1,75 na malha) -> 0,53 cm
HASTE_MEIO = 15.6 * ESCALA_VELA       # meio da haste livre (6,7..24,5 na malha) acima da base -> 4,7 cm: onde o punho fecha
PALMA = 1.2                           # centro da haste: 1,2 cm + raio abaixo da linha dos nos (MCP), lado da palma
PUNHO_AO_PULSO = 0.8                  # e 0,8 cm na direcao do pulso (a haste fica na dobra da palma)
DEDO_R = 0.75                         # meia espessura do dedo: contato quando a falange fica a HASTE_R + DEDO_R do eixo
PONTA = {"index": 2.2, "middle": 2.4, "ring": 2.3, "pinky": 2.0, "thumb": 2.6}   # falange distal (cm)
DEDOS = ("index", "middle", "ring", "pinky")
# cm do olho ate a haste (None = o solver escolhe o menor esforco do pulso, que da ~44 cm com o braco quase esticado).
# 40 cm: pulso flexao ~15, desvio ~5, torcao ~37 (pronacao natural), cotovelo ~124; mais perto o pulso dobra 30-50 graus
DIST_ALVO = 40
LOG = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "LuxSnapshots", "vela_pega_log.txt")


def w(*a):
    line = " ".join(str(x) for x in a)
    unreal.log("[LUX pega] " + line)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


class Aborta(Exception):
    pass


# ------------------------------------------------------------------ vetores/quaternions (x, y, z) / (x, y, z, w)
def add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def mul(a, k): return (a[0] * k, a[1] * k, a[2] * k)
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def nrm(a): return math.sqrt(dot(a, a))
def unit(a): return mul(a, 1.0 / (nrm(a) or 1.0))
def f3(a): return "(%.1f, %.1f, %.1f)" % tuple(a)


def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz)


def qinv(q): return (-q[0], -q[1], -q[2], q[3])


def qrot(q, v):
    return qmul(qmul(q, (v[0], v[1], v[2], 0.0)), qinv(q))[:3]


def qaxis(axis, graus):
    a = unit(axis)
    s = math.sin(math.radians(graus) / 2)
    return (a[0] * s, a[1] * s, a[2] * s, math.cos(math.radians(graus) / 2))


def qentre(a, b):
    """menor rotacao que leva a direcao a em b"""
    a, b = unit(a), unit(b)
    c = max(-1.0, min(1.0, dot(a, b)))
    ax = cross(a, b)
    if nrm(ax) < 1e-6:
        ax = cross(a, (1, 0, 0)) if abs(a[0]) < 0.9 else cross(a, (0, 1, 0))
    return qaxis(ax, math.degrees(math.acos(c)))


def qang(a, b):
    """angulo (graus) entre duas orientacoes"""
    d = abs(sum(x * y for x, y in zip(a, b)))
    return math.degrees(2 * math.acos(min(1.0, d)))


def uq(q): return (q.x, q.y, q.z, q.w)
def uv(v): return (v.x, v.y, v.z)


# ------------------------------------------------------------------ pose de referencia
class Pose:
    """ossos do quadro 0 do idle: local (pos, rot) e componente (pos, rot)"""

    def __init__(self):
        self.seq = EAL.load_asset(IDLE)
        pose = APE.get_anim_pose_at_frame(self.seq, 0, unreal.AnimPoseEvaluationOptions())
        self.nomes = [str(b) for b in APE.get_bone_names(pose)]
        if "hand_r" not in self.nomes:
            raise Aborta("pose do idle sem ossos (%d)" % len(self.nomes))
        self.loc, self.cs = {}, {}
        # pulso neutro = pose de referencia do esqueleto (mao reta em relacao ao antebraco)
        self.ref_hand = uq(APE.get_ref_bone_pose(pose, "hand_r", unreal.AnimPoseSpaces.LOCAL).rotation)
        for b in self.nomes:
            t = APE.get_bone_pose(pose, b, unreal.AnimPoseSpaces.LOCAL)
            self.loc[b] = (uv(t.translation), uq(t.rotation))
            t = APE.get_bone_pose(pose, b, unreal.AnimPoseSpaces.WORLD)
            self.cs[b] = (uv(t.translation), uq(t.rotation))


def mesh_na_camera():
    (x, y, z), yaw = MESH_NA_CAMERA
    return (x, y, z), qaxis((0, 0, 1), yaw)


def cs_para_cam(p):
    t, q = mesh_na_camera()
    return add(qrot(q, p), t)


def dir_cs_para_cam(v):
    return qrot(mesh_na_camera()[1], v)


def cam_para_cs(p):
    t, q = mesh_na_camera()
    return qrot(qinv(q), sub(p, t))


def dir_cam_para_cs(v):
    return qrot(qinv(mesh_na_camera()[1]), v)


# ------------------------------------------------------------------ dedos (no espaco da mao, hand_r = identidade)
def fk_dedo(P, cadeia, deltas):
    """cadeia de ossos a partir do hand_r; deltas (graus) somados no eixo Z local de cada falange -> pontos e rots"""
    pos, rot = (0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)
    pts, rots = [], []
    for i, b in enumerate(cadeia):
        lp, lq = P.loc[b]
        pos = add(pos, qrot(rot, lp))
        lq = qmul(lq, qaxis((0, 0, 1), deltas.get(b, 0.0)))
        rot = qmul(rot, lq)
        pts.append(pos)
        rots.append(rot)
    return pts, rots


def dist_eixo(p, c, a):
    r = sub(p, c)
    return nrm(sub(r, mul(a, dot(r, a))))


def haste_na_mao(P):
    """centro e direcao (minimo -> indicador) da haste no espaco do hand_r.
    Os nos dos dedos (MCP) formam um arco: cada dedo ganha um ponto de pega (MCP + lado da palma + um pouco para o
    pulso) e a haste e a reta que melhor passa pelos 4 pontos."""
    mcp = {d: fk_dedo(P, ["%s_metacarpal_r" % d, "%s_01_r" % d], {})[0][1] for d in DEDOS}
    eixo0 = unit(sub(mcp["index"], mcp["pinky"]))
    meio = mul(add(mcp["middle"], mcp["ring"]), 0.5)
    # lado da palma: para onde os dedos fecham (media das pontas dos 4 dedos), perpendicular ao eixo
    pontas = []
    for d in DEDOS:
        pts, rots = fk_dedo(P, ["%s_metacarpal_r" % d] + ["%s_0%d_r" % (d, i) for i in (1, 2, 3)], {})
        pontas.append(add(pts[-1], qrot(rots[-1], (-PONTA[d], 0, 0))))
    v = sub(mul(add(add(pontas[0], pontas[1]), add(pontas[2], pontas[3])), 0.25), meio)
    palma = unit(sub(v, mul(eixo0, dot(v, eixo0))))
    pulso = unit(sub((0, 0, 0), meio))
    pulso = unit(sub(pulso, mul(eixo0, dot(pulso, eixo0))))
    pega = [add(add(mcp[d], mul(palma, PALMA + HASTE_R)), mul(pulso, PUNHO_AO_PULSO)) for d in DEDOS]
    centro = mul(add(add(pega[0], pega[1]), add(pega[2], pega[3])), 0.25)
    # reta de minimos quadrados: iteracao de potencia na covariancia (4 pontos, 3x3)
    cov = [[sum((p[i] - centro[i]) * (p[j] - centro[j]) for p in pega) for j in range(3)] for i in range(3)]
    eixo = eixo0
    for _ in range(50):
        eixo = unit(tuple(sum(cov[i][j] * eixo[j] for j in range(3)) for i in range(3)))
    if dot(eixo, eixo0) < 0:
        eixo = mul(eixo, -1)
    return centro, eixo, palma


# perfil do SM_Candles_NN_01c (altura na malha: raio na malha), medido nos vertices (vela_malhas_probe):
# prato 0-3,3 (10,2), colar 3,4-6 (4,3), haste 6,7-24,5 (1,8), copinho 25,5-33 (ate 4,9), vela 33,5-41,7 (2,5)
PERFIL = ((0.0, 10.2), (3.0, 10.2), (3.4, 4.3), (6.0, 4.3), (6.7, 1.8), (24.5, 1.8), (25.5, 4.6), (33.0, 4.9), (33.5, 2.5),
          (41.7, 2.5))


def raio_em(h_cm):
    """raio (cm) do castical na altura h (cm acima da base), com a escala da vela"""
    h = h_cm / ESCALA_VELA
    if h <= PERFIL[0][0] or h >= PERFIL[-1][0]:
        return 0.0
    for (h0, r0), (h1, r1) in zip(PERFIL, PERFIL[1:]):
        if h0 <= h <= h1:
            return (r0 + (r1 - r0) * (h - h0) / ((h1 - h0) or 1)) * ESCALA_VELA
    return 0.0


def menor_dist(P, cadeia, dd, d, centro, eixo):
    """menor folga das falanges (3 ultimos ossos + ponta) ate a SUPERFICIE do castical (perfil real na altura de cada
    ponto): 0 = encostando, negativo = entrando no metal"""
    pts, rots = fk_dedo(P, cadeia, dd)
    pts = pts[-3:] + [add(pts[-1], qrot(rots[-1], (-PONTA[d], 0, 0)))]
    m = 1e9
    for a, b in zip(pts, pts[1:]):
        for s in range(6):
            q = add(a, mul(sub(b, a), s / 5.0))
            h = dot(sub(q, centro), eixo) + HASTE_MEIO          # altura do ponto na vela (o centro do punho = meio da haste)
            m = min(m, dist_eixo(q, centro, eixo) - raio_em(h) - DEDO_R)
    return m


def fecha_dedos(P, centro, eixo):
    """rotacoes extras (graus, eixo local) ate as falanges encostarem no castical (folga 0 na superficie real).
    Dedos: flexao = Z local negativo (e o sentido que as animacoes ja usam) em _01/_02/_03.
    Polegar: busca 2D (base thumb_01 no eixo local que mais aproxima + flexao de _02/_03)."""
    alvo = 0.0
    rots, relato = {}, []
    for d in DEDOS:
        cadeia = ["%s_metacarpal_r" % d] + ["%s_0%d_r" % (d, i) for i in (1, 2, 3)]
        juntas, pesos = cadeia[1:], (1.0, 1.0, 0.7)
        md = lambda k: menor_dist(P, cadeia, {b: k * p for b, p in zip(juntas, pesos)}, d, centro, eixo)
        base, k = md(0.0), 0.0
        if base > alvo:
            while k > -85 and md(k) > alvo:
                k -= 0.5
        else:
            while k < 40 and md(k) < alvo:
                k += 0.5
        for b, p in zip(juntas, pesos):
            rots[b] = qaxis((0, 0, 1), k * p)
        relato.append("%s %+.0f graus (folga %.1f -> %.1f cm)" % (d, k, base, md(k)))
    cadeia = ["thumb_01_r", "thumb_02_r", "thumb_03_r"]
    base = menor_dist(P, cadeia, {}, "thumb", centro, eixo)
    melhor = (abs(base - alvo), None, 0.0, 0.0, base)
    for ax in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
        for k1 in range(-60, 61, 5):
            for k2 in range(-80, 21, 5):
                def fk_t(k1=k1, k2=k2, ax=ax):
                    pos, rot, pts, rr = (0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0), [], []
                    for b, extra in zip(cadeia, (qaxis(ax, k1), qaxis((0, 0, 1), k2), qaxis((0, 0, 1), 0.8 * k2))):
                        lp, lq = P.loc[b]
                        pos = add(pos, qrot(rot, lp))
                        rot = qmul(rot, qmul(lq, extra))
                        pts.append(pos)
                        rr.append(rot)
                    pts.append(add(pts[-1], qrot(rr[-1], (-PONTA["thumb"], 0, 0))))
                    folga = lambda q: dist_eixo(q, centro, eixo) - raio_em(dot(sub(q, centro), eixo) + HASTE_MEIO) - DEDO_R
                    return min(folga(add(a, mul(sub(b, a), s / 5.0))) for a, b in zip(pts, pts[1:]) for s in range(6))

                m = fk_t()
                if m >= alvo - 0.05 and abs(m - alvo) < melhor[0]:
                    melhor = (abs(m - alvo), ax, k1, k2, m)
    if melhor[1]:
        rots["thumb_01_r"] = qaxis(melhor[1], melhor[2])
        rots["thumb_02_r"] = qaxis((0, 0, 1), melhor[3])
        rots["thumb_03_r"] = qaxis((0, 0, 1), 0.8 * melhor[3])
    relato.append("thumb base %s %+.0f, flexao %+.0f (folga %.1f -> %.1f cm)" % (melhor[1], melhor[2], melhor[3], base, melhor[4]))
    return rots, relato


# ------------------------------------------------------------------ braco (IK de 2 ossos no espaco do componente)
def ik(S, W, L1, L2, polo):
    d = sub(W, S)
    dist = min(nrm(d), L1 + L2 - 0.01)
    n = unit(d)
    a = (L1 * L1 - L2 * L2 + dist * dist) / (2 * dist)
    h = math.sqrt(max(0.0, L1 * L1 - a * a))
    pp = unit(sub(polo, mul(n, dot(polo, n))))
    return add(add(S, mul(n, a)), mul(pp, h)), add(S, mul(n, dist))


def solve(P, centro_h, eixo_h, alvo_cam, giro):
    """pose do braco para a haste (centro_h/eixo_h no espaco da mao) ficar vertical no ponto alvo_cam (camera)"""
    S, qu = P.cs["upperarm_r"]
    E0, ql = P.cs["lowerarm_r"]
    W0, qh = P.cs["hand_r"]
    L1, L2 = nrm(sub(E0, S)), nrm(sub(W0, E0))
    cima = dir_cam_para_cs((0, 0, 1))
    eixo_cs = qrot(qh, eixo_h)
    qh2 = qmul(qaxis(cima, giro), qmul(qentre(eixo_cs, cima), qh))
    C = cam_para_cs(alvo_cam)
    W = sub(C, qrot(qh2, centro_h))
    E, W = ik(S, W, L1, L2, sub(E0, S))
    qu2 = qmul(qentre(sub(E0, S), sub(E, S)), qu)
    ql_tmp = qmul(qentre(sub(E0, S), sub(E, S)), ql)
    dir_l = qrot(ql_tmp, (-1, 0, 0))
    ql2 = qmul(qentre(dir_l, sub(W, E)), ql_tmp)
    alcance = nrm(sub(add(W, qrot(qh2, centro_h)), C))
    return dict(pulso(P, qmul(qinv(ql2), qh2)), qu=qu2, ql=ql2, qh=qh2, E=E, W=W, C=C, erro=alcance,
                cotovelo=math.degrees(math.acos(max(-1, min(1, dot(unit(sub(S, E)), unit(sub(W, E))))))))


def pulso(P, local_mao):
    """angulos do pulso (graus, com sinal) em relacao ao pulso neutro da pose de referencia: torcao em volta do
    antebraco (X local; quem gira e o antebraco), flexao/extensao (Z da mao ~ eixo da haste) e desvio (Y = normal da palma)"""
    d = qmul(qinv(P.ref_hand), local_mao)          # rotacao da mao a partir do neutro, no espaco da propria mao neutra
    tor = math.degrees(2 * math.atan2(d[0], d[3]))
    sw = qmul(d, qaxis((1, 0, 0), -tor))
    ang = qang(sw, (0, 0, 0, 1))
    ax = unit(sw[:3]) if nrm(sw[:3]) > 1e-9 else (0, 0, 0)
    s = 1 if sw[3] >= 0 else -1
    return {"torcao": (tor + 180) % 360 - 180, "flexao": s * ax[2] * ang, "desvio": s * ax[1] * ang}


def visivel(p_cam, margem=0.9):
    return p_cam[0] > 5 and abs(p_cam[1] / p_cam[0]) < margem and abs(p_cam[2] / p_cam[0]) < 0.5625 * margem


def escolhe(P, centro_h, eixo_h):
    """procura onde por a haste na tela e quanto girar o punho em volta dela para o braco ficar natural:
    cotovelo dobrado, pulso dentro da amplitude real (neutro = pose de referencia), vela e chama a vista"""
    cands, motivo = [], {}
    for x in range(24, 45, 2):
        for y in range(4, 25, 2):
            for z in range(-26, -1, 2):
                for giro in range(-90, 91, 15):
                    r = solve(P, centro_h, eixo_h, (x, y, z), giro)
                    chama = (x, y, z + (41.7 * ESCALA_VELA - HASTE_MEIO) + 2.5)
                    punho_baixo = (x, y, z - 3.0)       # o punho inteiro (e a mao segurando) tem de aparecer
                    if r["erro"] > 0.3:
                        motivo["alcance"] = motivo.get("alcance", 0) + 1
                        continue
                    if not visivel(chama) or not visivel(punho_baixo, 0.97):
                        motivo["fora da tela"] = motivo.get("fora da tela", 0) + 1
                        continue
                    if not 70 <= r["cotovelo"] <= 140:
                        motivo["cotovelo"] = motivo.get("cotovelo", 0) + 1
                        continue
                    # amplitude do pulso: flexao/extensao 60, desvio 30 (segurar em pe usa desvio radial, como numa
                    # espada), torcao do antebraco 90
                    if abs(r["flexao"]) > 60 or abs(r["desvio"]) > 30 or abs(r["torcao"]) > 90:
                        motivo["pulso"] = motivo.get("pulso", 0) + 1
                        continue
                    nota = (abs(r["flexao"]) + 1.5 * abs(r["desvio"]) + 0.3 * abs(r["torcao"]) + abs(r["cotovelo"] - 100) / 5
                            + 0.5 * abs(x - 34))          # distancia de segurar algo a frente (~34 cm do olho)
                    cands.append((nota, (x, y, z), giro, r))
    w("   busca: %d candidatos; descartes %s" % (len(cands), motivo))
    if not cands:
        raise Aborta("nenhum alvo alcancavel com a chama e o punho a vista dentro dos limites do braco")
    cands.sort(key=lambda c: c[0])
    for dist in sorted(set(c[1][0] for c in cands)):
        c = [c for c in cands if c[1][0] == dist][0]
        w("   melhor a %d cm: nota %.1f alvo %s giro %d: flexao %.0f desvio %.0f torcao %.0f cotovelo %.0f" % (
            dist, c[0], f3(c[1]), c[2], c[3]["flexao"], c[3]["desvio"], c[3]["torcao"], c[3]["cotovelo"]))
    if DIST_ALVO:
        cands = [c for c in cands if c[1][0] == DIST_ALVO] or cands
    for c in cands[:5]:
        w("   candidato nota %.1f alvo %s giro %d: flexao %.0f desvio %.0f torcao %.0f cotovelo %.0f" % (
            c[0], f3(c[1]), c[2], c[3]["flexao"], c[3]["desvio"], c[3]["torcao"], c[3]["cotovelo"]))
    return cands[0]


# ------------------------------------------------------------------ calculo completo
def calcula():
    P = Pose()
    centro_h, eixo_h, _ = haste_na_mao(P)
    dedos, rel = fecha_dedos(P, centro_h, eixo_h)
    nota, alvo, giro, r = escolhe(P, centro_h, eixo_h)
    locais = {}
    cl = P.cs["clavicle_r"][1]
    locais["upperarm_r"] = qmul(qinv(cl), r["qu"])
    locais["lowerarm_r"] = qmul(qinv(r["qu"]), r["ql"])
    locais["hand_r"] = qmul(qinv(r["ql"]), r["qh"])
    for b, q in dedos.items():
        locais[b] = qmul(P.loc[b][1], q)
    return P, centro_h, eixo_h, dedos, rel, alvo, giro, r, locais


def relatorio(P, centro_h, eixo_h, dedos, rel, alvo, giro, r):
    w("haste na mao (hand_r): centro %s eixo %s | raio %.2f cm" % (f3(centro_h), f3(eixo_h), HASTE_R))
    w("dedos fecham: " + "; ".join(rel))
    S = P.cs["upperarm_r"][0]
    w("ombro cam %s | cotovelo cam %s -> %s | pulso cam %s -> %s" % (
        f3(cs_para_cam(S)), f3(cs_para_cam(P.cs["lowerarm_r"][0])), f3(cs_para_cam(r["E"])),
        f3(cs_para_cam(P.cs["hand_r"][0])), f3(cs_para_cam(r["W"]))))
    w("alvo da haste na camera %s, giro %d graus | pulso: flexao %.0f, desvio %.0f, torcao %.0f graus | cotovelo %.0f graus | erro %.2f cm" % (
        f3(alvo), giro, r["flexao"], r["desvio"], r["torcao"], r["cotovelo"], r["erro"]))
    eixo_cam = dir_cs_para_cam(qrot(r["qh"], eixo_h))
    w("eixo da haste na camera %s (deve ser (0, 0, 1)) | antebraco %s | dedos apontam %s" % (
        f3(eixo_cam), f3(dir_cs_para_cam(unit(sub(r["W"], r["E"])))), f3(dir_cs_para_cam(qrot(r["qh"], (-1, 0, 0))))))
    # antes (animacao da lanterna) para comparar
    E0, W0, qh = P.cs["lowerarm_r"][0], P.cs["hand_r"][0], P.cs["hand_r"][1]
    p0 = pulso(P, qmul(qinv(P.cs["lowerarm_r"][1]), qh))
    w("antes: antebraco %s | dedos apontam %s | pulso: flexao %.0f, desvio %.0f, torcao %.0f" % (
        f3(dir_cs_para_cam(unit(sub(W0, E0)))), f3(dir_cs_para_cam(qrot(qh, (-1, 0, 0)))), p0["flexao"], p0["desvio"], p0["torcao"]))


# ------------------------------------------------------------------ assets
def cria_aditiva(P, locais):
    """AS_LuxVela_Pega: todos os ossos parados no quadro 0 do idle, com a pega nos ossos alterados; aditiva local"""
    idle = P.seq
    if not EAL.does_directory_exist(DIR):
        EAL.make_directory(DIR)
    seq = EAL.load_asset(PEGA) if EAL.does_asset_exist(PEGA) else EAL.duplicate_asset(IDLE, PEGA)
    if not seq:
        raise Aborta("nao consegui criar " + PEGA)
    n = AL.get_num_keys(idle)
    ctl = seq.controller
    ctl.open_bracket(unreal.Text("LUX pega da vela"), True)
    try:
        falhas = []
        for b in P.nomes:
            if AL.does_bone_name_exist(idle, b) is False:
                continue
            lp, lq = P.loc[b]
            q = locais.get(b, lq)
            ok = False
            for V, Q in ((unreal.Vector3f, unreal.Quat4f), (unreal.Vector, unreal.Quat)):
                try:
                    ok = ctl.set_bone_track_keys(b, [V(*lp)] * n, [Q(*q)] * n, [V(1.0, 1.0, 1.0)] * n, False)
                    if ok:
                        break
                except Exception:
                    ok = False
            if not ok and b in locais:
                falhas.append(b)
        if falhas:
            raise Aborta("trilhas nao gravadas: %s" % falhas)
    finally:
        ctl.close_bracket(True)
    AL.set_additive_animation_type(seq, unreal.AdditiveAnimationType.AAT_LOCAL_SPACE_BASE)
    AL.set_additive_base_pose_type(seq, unreal.AdditiveBasePoseType.ABPT_ANIM_FRAME)
    seq.set_editor_property("ref_pose_seq", idle)
    seq.set_editor_property("ref_frame_index", 0)
    w("AS_LuxVela_Pega gravada (%d quadros, %d ossos com pega)" % (n, len(locais)))
    return seq


def socket_vela(centro_h, eixo_h):
    """socket hand_r_Vela: no centro da haste dentro do punho, Z = eixo da haste (vela para cima), X = frente da mao"""
    sk = EAL.load_asset(SKM)
    # copia de seguranca do .uasset antes do primeiro socket (uma vez so)
    bak = os.path.join(os.path.dirname(LOG), "backup_vela", "FPMovement__Demo__Character__Arms__MetaHuman__SKM_Metahuman_Arms.uasset")
    if not os.path.exists(bak):
        os.makedirs(os.path.dirname(bak), exist_ok=True)
        cont = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())
        shutil.copy2(os.path.join(cont, "FPMovement/Demo/Character/Arms/MetaHuman/SKM_Metahuman_Arms.uasset"), bak)
        w("backup do SKM_Metahuman_Arms em", bak)
    frente = (-1.0, 0.0, 0.0)
    frente = unit(sub(frente, mul(eixo_h, dot(frente, eixo_h))))
    rot = unreal.MathLibrary.make_rot_from_zx(unreal.Vector(*eixo_h), unreal.Vector(*frente))
    s = sk.find_socket(SOCKET)
    if not s:
        # SocketName/BoneName sao so-leitura no Python: o socket nasce "Socket" no root, e renomeado e reapontado
        s = unreal.new_object(unreal.SkeletalMeshSocket, sk)
        sk.add_socket(s, False)
        sk.rename_socket(s.get_editor_property("socket_name"), SOCKET)
        w("socket %s criado" % SOCKET)
    s.modify()
    if str(s.get_editor_property("bone_name")) != "hand_r":
        try:
            s.set_socket_parent(sk, "hand_r")
        except TypeError as ex:
            w("  set_socket_parent(sk, osso) recusado (%s); tentando so o osso por nome" % ex)
            s.set_socket_parent(None, "hand_r")
    if str(s.get_editor_property("bone_name")) != "hand_r" or str(s.get_editor_property("socket_name")) != SOCKET:
        raise Aborta("socket %s no osso %s (esperado %s em hand_r)" % (s.get_editor_property("socket_name"), s.get_editor_property("bone_name"), SOCKET))
    s.set_editor_property("relative_location", unreal.Vector(*centro_h))
    s.set_editor_property("relative_rotation", rot)
    s.set_editor_property("relative_scale", unreal.Vector(1, 1, 1))
    sk.modify()
    w("socket %s: loc %s rot %s" % (SOCKET, f3(centro_h), rot))
    return sk


def aditivo_no_abp(seq):
    """ramo da lanterna: Use cached pose 'FlashlightAnimations' -> Apply Additive(AS_LuxVela_Pega) -> Blend Poses by bool"""
    abp = EAL.load_asset(ABP)
    ge = BGE.get_graph_editor_by_name(abp, "AnimGraph")
    nos = list(ge.list_all_nodes())
    if [n for n in nos if "AS_LuxVela_Pega" in str(n.get_node_title())]:
        return False
    uso = [n for n in nos if "FlashlightAnimations" in str(n.get_node_title()) and "Use" in str(n.get_node_title())]
    bl = [n for n in nos if "Blend Poses by bool" in str(n.get_node_title())]
    if len(uso) != 1 or len(bl) != 1:
        raise Aborta("ABP: cached pose da lanterna (%d) ou Blend Poses by bool (%d) nao encontrado" % (len(uso), len(bl)))
    uso, bl = uso[0], bl[0]
    entrada = bl.find_input_pin("BlendPose_0")
    pos = uso.get_node_pos()
    add_n = ge.create_node_from_name("Animation|Blends|ApplyAdditive", unreal.Vector2D(pos.x + 300, pos.y + 150), [])
    sp = ge.create_node_from_name("Animation|Sequences|Play'AS_LuxVela_Pega'", unreal.Vector2D(pos.x, pos.y + 300), [])
    if not sp:
        sp = ge.create_node_from_name("Animation|Sequences|Play'AS_Flashlight_Idle'", unreal.Vector2D(pos.x, pos.y + 300), [])
        no = sp.get_editor_property("node")
        no.set_editor_property("sequence", seq)
        sp.set_editor_property("node", no)
    if not add_n or not sp:
        raise Aborta("ABP: nos Apply Additive / Sequence Player nao criados")
    entrada.break_pin_links()
    for a, ap, b, bp in ((uso, "Pose", add_n, "Base"), (sp, "Pose", add_n, "Additive"), (add_n, "Pose", bl, "BlendPose_0")):
        if not a.find_output_pin(ap).try_create_connection(b.find_input_pin(bp)):
            raise Aborta("ABP: ligacao %s.%s -> %s.%s falhou" % (a.get_node_title(), ap, b.get_node_title(), bp))
    ge.add_comment_node("LUX vela (Tools/Player/vela_pega.py): pega de espada na haste da vela (aditiva sobre as animacoes da lanterna)",
                        unreal.Vector2D(pos.x - 40, pos.y + 100), unreal.Vector2D(700, 420))
    w("ABP: Apply Additive(AS_LuxVela_Pega) no ramo da lanterna")
    return True


def erros(bp):
    out = []
    for g in [str(x) for x in BEL.list_graph_names(bp)]:
        try:
            ge = BGE.get_graph_editor_by_name(bp, g)
        except Exception:
            continue
        out += ["%s: %s" % (g, str(n.get_node_title()).replace("\n", " ")) for n in ge.list_nodes_with_errors()]
    return out


def instalar():
    if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():
        raise Aborta("feche o PIE")
    P, centro_h, eixo_h, dedos, rel, alvo, giro, r, locais = calcula()
    relatorio(P, centro_h, eixo_h, dedos, rel, alvo, giro, r)
    seq = cria_aditiva(P, locais)
    sk = socket_vela(centro_h, eixo_h)
    abp_mudou = aditivo_no_abp(seq)
    abp = EAL.load_asset(ABP)
    BEL.compile_blueprint(abp)
    e = erros(abp)
    if e:
        raise Aborta("ABP com erros (nada salvo): %s" % e)
    for a in (seq, sk, abp):
        w("salvo", a.get_path_name(), EAL.save_loaded_asset(a, False))
    return abp_mudou


def verificar():
    falhas = []
    if not EAL.does_asset_exist(PEGA):
        falhas.append("sem AS_LuxVela_Pega")
    else:
        s = EAL.load_asset(PEGA)
        if AL.get_additive_animation_type(s) != unreal.AdditiveAnimationType.AAT_LOCAL_SPACE_BASE:
            falhas.append("AS_LuxVela_Pega nao e aditiva local")
    if not EAL.load_asset(SKM).find_socket(SOCKET):
        falhas.append("sem socket %s" % SOCKET)
    nos = BGE.get_graph_editor_by_name(EAL.load_asset(ABP), "AnimGraph").list_all_nodes()
    if not [n for n in nos if "AS_LuxVela_Pega" in str(n.get_node_title())]:
        falhas.append("ABP sem a aditiva da pega")
    falhas += erros(EAL.load_asset(ABP))
    w("verificar pega:", ("FAIL %s" % falhas) if falhas else "PASS")
    return falhas


def escalas(P):
    """para cada escala da vela: quanto cada dedo entra no castical (folga negativa) depois de fechar"""
    global ESCALA_VELA, HASTE_R, HASTE_MEIO
    salvo = (ESCALA_VELA, HASTE_R, HASTE_MEIO)
    try:
        for s in (0.30, 0.34, 0.38, 0.42, 0.44, 0.46, 0.48, 0.50):
            ESCALA_VELA, HASTE_R, HASTE_MEIO = s, 1.75 * s, 15.6 * s
            c, e, _ = haste_na_mao(P)
            _, rel = fecha_dedos(P, c, e)
            w("escala %.2f (vela %.1f cm, haste livre %.1f cm): %s" % (s, 41.7 * s, 17.8 * s, "; ".join(rel)))
    finally:
        ESCALA_VELA, HASTE_R, HASTE_MEIO = salvo


def main():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    open(LOG, "w", encoding="utf-8").close()
    modo = next((a for a in sys.argv[1:] if a in ("sondar", "escalas", "instalar", "verificar")), "sondar")
    w("modo:", modo)
    try:
        if modo == "escalas":
            escalas(Pose())
        elif modo == "sondar":
            relatorio(*calcula()[:8])
        elif modo == "instalar":
            instalar()
            verificar()
        else:
            verificar()
    except Aborta as ex:
        w("ABORTADO:", ex)
    except Exception:
        w("ERRO " + traceback.format_exc())


if __name__ == "__main__":
    main()
