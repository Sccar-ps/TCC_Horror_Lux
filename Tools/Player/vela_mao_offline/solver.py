"""pega da haste do castical com a malha real: dedos/polegar/haste otimizados juntos (espaco do hand_r)"""
import numpy as np
from scipy.optimize import minimize
from scipy.spatial import cKDTree
from mao import *
from render import PERFIL

DEDOS = ("index", "middle", "ring", "pinky")
G = {}


def escala(s):
    """escala da vela: perfil (cm) e meio da haste livre"""
    G["s"] = s
    G["PH"] = np.array([p[0] for p in PERFIL]) * s
    G["PR"] = np.array([p[1] for p in PERFIL]) * s
    G["meio"] = 15.6 * s


escala(0.42)


def raio(h):
    return np.interp(h, G["PH"], G["PR"], left=0.0, right=0.0)


class Mao:
    """ossos e pele da mao no espaco do hand_r (hand_r = identidade), pose base = idle quadro 0"""

    def __init__(self, d=None, base="idle0"):
        self.d = d = d or Dados()
        self.base = d.local(base)
        cs = d.cs(self.base)
        hp, hq = cs["hand_r"]
        self.hinv = (hp, hq)
        # ossos da mao (subarvore do hand_r) em ordem
        self.sub = [b for b in d.ordem if b != "hand_r" and self._desce(b)]
        # pele: so vertices com peso relevante na mao / dedos / pulso
        dom = d.j[np.arange(len(d.j)), d.w.argmax(1)]
        nomes = np.array(d.juntas)
        self.dom = nomes[dom]
        peso_mao = np.zeros(len(d.v))
        for i, b in enumerate(d.juntas):
            if b == "hand_r" or b in self.sub:
                peso_mao += (d.w * (d.j == i)).sum(1)
        self.idx = np.where(peso_mao > 0.5)[0]
        self.dom = self.dom[self.idx]
        # matrizes de skinning fixas (fora da mao): no espaco da mao
        H = np.linalg.inv(mat4(hp, hq))
        self.S_fixo = {}
        for i, b in enumerate(d.juntas):
            if b != "hand_r" and b not in self.sub:
                self.S_fixo[i] = H @ mat4(*cs[b]) @ np.linalg.inv(d.bind[i]) if b in cs else np.eye(4)
        self.bind_inv = np.array([np.linalg.inv(m) for m in d.bind])
        self.j = d.j[self.idx]
        self.w = d.w[self.idx]
        self.vh = np.hstack([d.v[self.idx], np.ones((len(self.idx), 1))])
        self.nv = d.n[self.idx]
        # partes
        def parte(n):
            for f in DEDOS + ("thumb",):
                if n.startswith(f) and "metacarpal" not in n:
                    return f + n[len(f):len(f) + 3]         # ex.: index_02
            return "palma"
        self.parte = np.array([parte(n) for n in self.dom])

    def _desce(self, b):
        while b in self.d.pai:
            b = self.d.pai[b]
            if b == "hand_r":
                return True
        return False

    def cs(self, local):
        out = {"hand_r": (np.zeros(3), np.array((0, 0, 0, 1.0)))}
        for b in self.sub:
            p, q = local.get(b, self.base[b])
            pp, pq = out[self.d.pai[b]]
            out[b] = (pp + qrot(pq, p), qmul(pq, q))
        return out

    def pele(self, cs):
        S = np.empty((len(self.d.juntas), 4, 4))
        for i, b in enumerate(self.d.juntas):
            S[i] = self.S_fixo[i] if i in self.S_fixo else mat4(*cs[b]) @ self.bind_inv[i]
        M = np.einsum("nk,nkij->nij", self.w, S[self.j])
        v = np.einsum("nij,nj->ni", M, self.vh)[:, :3]
        n = np.einsum("nij,nj->ni", M[:, :3, :3], self.nv)
        n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-9
        return v, n


# ------------------------------------------------------------------ parametros
# por dedo: flexao MCP, abducao MCP, flexao PIP, flexao DIP (graus somados na pose do idle; flexao = -Z local)
# anelar/minimo: flexao do metacarpo (arco da palma). Polegar: base (3 eixos), MCP flexao/abducao, IP flexao.
# haste: deslocamento do centro (3, cm) e inclinacao (2, graus)
NOMES = []
for f in DEDOS:
    NOMES += ["%s_mcp" % f, "%s_abd" % f, "%s_pip" % f, "%s_dip" % f]
NOMES += ["ring_meta", "pinky_meta", "th1_x", "th1_y", "th1_z", "th2_f", "th2_a", "th3_f", "hx", "hy", "hz", "ta", "tb"]
LIM = {"mcp": (-95, 15), "abd": (-18, 18), "pip": (-100, 15), "dip": (-70, 15), "meta": (-15, 3), "th1": (-55, 55),
       "th2_f": (-55, 20), "th2_a": (-20, 20), "th3_f": (-75, 20), "h": (-2.0, 2.0), "t": (-25, 25)}


def limites():
    out = []
    for n in NOMES:
        k = n.split("_")[-1] if n.split("_")[0] in DEDOS else None
        if k in ("mcp", "abd", "pip", "dip"):
            out.append(LIM[k])
        elif n.endswith("meta"):
            out.append(LIM["meta"])
        elif n.startswith("th1"):
            out.append(LIM["th1"])
        elif n in ("th2_f", "th2_a", "th3_f"):
            out.append(LIM[n])
        elif n in ("hx", "hy", "hz"):
            out.append(LIM["h"])
        else:
            out.append(LIM["t"])
    return out


def locais(m, x):
    """vetor -> rotacoes locais (sobre a pose base)"""
    v = dict(zip(NOMES, x))
    L = {}
    Z, Y, X = (0, 0, 1), (0, 1, 0), (1, 0, 0)

    def ap(b, *rots):
        q = m.base[b][1]
        for ax, g in rots:
            q = qmul(q, qaxis(ax, g))
        L[b] = (m.base[b][0], q)

    for f in DEDOS:
        ap("%s_01_r" % f, (Z, v["%s_mcp" % f]), (Y, v["%s_abd" % f]))
        ap("%s_02_r" % f, (Z, v["%s_pip" % f]))
        ap("%s_03_r" % f, (Z, v["%s_dip" % f]))
    ap("ring_metacarpal_r", (Z, v["ring_meta"]))
    ap("pinky_metacarpal_r", (Z, v["pinky_meta"]))
    rv = np.array((v["th1_x"], v["th1_y"], v["th1_z"]))
    ang = np.linalg.norm(rv)
    ap("thumb_01_r", (rv if ang > 1e-6 else X, ang))
    ap("thumb_02_r", (Z, v["th2_f"]), (Y, v["th2_a"]))
    ap("thumb_03_r", (Z, v["th3_f"]))
    return L


def haste(c0, a0, x):
    v = dict(zip(NOMES, x))
    c = c0 + np.array((v["hx"], v["hy"], v["hz"]))
    # inclinacao em dois eixos perpendiculares ao eixo inicial
    e1 = np.cross(a0, (1, 0, 0))
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(a0, e1)
    a = qrot(qmul(qaxis(e1, v["ta"]), qaxis(e2, v["tb"])), a0)
    return c, a / np.linalg.norm(a)


def folga_haste(p, c, a):
    r = p - c
    h = r @ a
    rad = np.linalg.norm(r - np.outer(h, a), axis=1)
    return rad - raio(h + G["meio"]), h


def sd(pts, arv, V, N, k=3, lim=1.5):
    """distancia com sinal aproximada dos pontos ate a pele (V, N) de outra parte: + fora, - dentro.
    Pontos a mais de lim cm da outra parte contam como fora (+lim)."""
    dd, ii = arv.query(pts, k=k, distance_upper_bound=lim)
    ok = np.isfinite(dd)
    ii = np.where(ok, ii, 0)
    s = np.einsum("nkj,nkj->nk", pts[:, None, :] - V[ii], N[ii])
    wgt = np.where(ok, 1.0 / (dd + 1e-3), 0.0)
    ws = wgt.sum(1)
    out = np.where(ws > 0, (s * wgt).sum(1) / np.maximum(ws, 1e-9), lim)
    return out, np.where(ok[:, 0], dd[:, 0], lim)


class Custo:
    def __init__(self, m, c0, a0, pesos=None):
        self.m, self.c0, self.a0 = m, c0, a0
        self.p = dict(pen=400.0, auto=200.0, contato=30.0, ponta=8.0, palma=20.0, polegar=20.0, nat=0.004, haste=0.2)
        self.p.update(pesos or {})
        pt = m.parte
        self.sel = {k: np.where(pt == k)[0] for k in set(pt)}
        # pares que nao podem se atravessar: (pontos de, contra pele de)
        self.pares = []
        for i, f in enumerate(DEDOS):
            for g in DEDOS[i + 1:]:
                self.pares.append(((f + "_02", f + "_03"), (g + "_01", g + "_02", g + "_03")))
                self.pares.append(((g + "_02", g + "_03"), (f + "_01", f + "_02", f + "_03")))
            self.pares.append(((f + "_02", f + "_03"), ("palma", "thumb_01")))
            self.pares.append((("thumb_02", "thumb_03"), (f + "_01", f + "_02", f + "_03")))
            self.pares.append(((f + "_02", f + "_03"), ("thumb_02", "thumb_03")))
        self.pares.append((("thumb_02", "thumb_03"), ("palma",)))
        # ponta do polegar: vertices do thumb_03 no terco final da falange (pose de referencia)
        d = m.d
        cs0 = d.cs(d.local("ref"))
        p3, q3 = cs0["thumb_03_r"]
        ids3 = self.sel["thumb_03"]
        ax = qrot(q3, (-1, 0, 0))
        t = (d.v[m.idx[ids3]] - p3) @ ax
        self.ponta_pol = ids3[t > np.percentile(t, 65)]
        self.log = None

    def junta(self, ks):
        return np.concatenate([self.sel.get(k, np.zeros(0, int)) for k in ks])

    def __call__(self, x, detalhe=False):
        m, P = self.m, self.p
        cs = m.cs(locais(m, x))
        V, N = m.pele(cs)
        c, a = haste(self.c0, self.a0, x)
        fo, h = folga_haste(V, c, a)
        E = {}
        # 1) nada entra no castical (tolerancia 0,05 cm de pele apertada)
        E["pen"] = P["pen"] * np.sum(np.minimum(fo + 0.05, 0) ** 2)
        # 2) partes da mao nao se atravessam
        auto = 0.0
        arvs = {}
        piores = {}
        for src, dst in self.pares:
            ids, idd = self.junta(src), self.junta(dst)
            if not len(ids) or not len(idd):
                continue
            key = dst
            if key not in arvs:
                arvs[key] = cKDTree(V[idd])
            s, dmin = sd(V[ids], arvs[key], V[idd], N[idd])
            s = np.where(dmin < 1.5, s, 1.0)          # longe = nao conta
            auto += np.sum(np.minimum(s + 0.08, 0) ** 2)
            piores["%s>%s" % (src[0][:-3], dst[0][:-3])] = float(s.min())
        E["auto"] = P["auto"] * auto
        # 3) contato: falange proximal e media de cada dedo encostam na haste
        cont, rel = 0.0, {}
        for f in DEDOS:
            for k in ("01", "02"):
                ids = self.sel["%s_%s" % (f, k)]
                mn = fo[ids].min()
                rel["%s_%s" % (f, k)] = mn
                cont += max(mn, 0) ** 2
            # ponta: encosta na haste ou na palma/base do polegar (a que estiver mais perto)
            ids = self.sel["%s_03" % f]
            mn = fo[ids].min()
            rel["%s_03" % f] = mn
        # dedos vizinhos encostados (punho fechado): falanges media/proximal de um tocam as do vizinho
        viz = 0.0
        for f, g in zip(DEDOS, DEDOS[1:]):
            ia, ib = self.junta((f + "_02",)), self.junta((g + "_02",))
            s_, _ = sd(V[ia], cKDTree(V[ib]), V[ib], N[ib])
            rel["%s-%s" % (f, g)] = float(s_.min())
            viz += max(s_.min(), 0) ** 2
        E["vizinhos"] = P.get("vizinhos", 30.0) * viz
        E["contato"] = P["contato"] * cont
        # pontas: fecham ate a palma/polegar (distancia do toque)
        pontas = 0.0
        idp = self.junta(("palma", "thumb_01", "thumb_02"))
        arvp = cKDTree(V[idp])
        for f in DEDOS:
            ids = self.sel["%s_03" % f]
            s, dmin = sd(V[ids], arvp, V[idp], N[idp])
            alvo = min(s.min(), rel["%s_03" % f])
            rel["%s_03_palma" % f] = float(s.min())
            pontas += max(alvo, 0) ** 2
        E["ponta"] = P["ponta"] * pontas
        # 4) palma encosta na haste
        mp = fo[self.sel["palma"]].min()
        rel["palma"] = mp
        E["palma"] = P["palma"] * max(mp - 0.4, 0) ** 2
        # 5) polegar: a polpa apoia na haste ou no dorso do indicador/medio
        idt = self.junta(("thumb_03",))
        ido = self.junta(("index_02", "index_03", "middle_02"))
        s, _ = sd(V[idt], cKDTree(V[ido]), V[ido], N[ido])
        # pega fechada (espada/martelo): a falange proximal do polegar abraca a haste do outro lado e a polpa
        # (falange distal) apoia no dorso da falange media do indicador/medio
        th2 = fo[self.sel["thumb_02"]].min()
        rel["polegar_haste"], rel["polegar_indicador"], rel["polegar02_haste"] = float(fo[idt].min()), float(s.min()), float(th2)
        # a ponta (nao o meio) do polegar e que apoia: o polegar dobra por cima do indicador em vez de sobrar para fora
        sp, _ = sd(V[self.ponta_pol], cKDTree(V[ido]), V[ido], N[ido])
        rel["ponta_polegar"] = float(sp.min())
        E["polegar"] = P["polegar"] * (max(s.min(), 0) ** 2 + max(th2, 0) ** 2 + max(sp.min(), 0) ** 2)
        # 6) naturalidade: DIP acompanha PIP (~0,7), abducao pequena, dedos vizinhos parecidos
        v = dict(zip(NOMES, x))
        nat = 0.0
        for f in DEDOS:
            nat += (v["%s_dip" % f] - 0.7 * v["%s_pip" % f]) ** 2 + 0.5 * v["%s_abd" % f] ** 2
        for f, g in zip(DEDOS, DEDOS[1:]):
            nat += 0.3 * ((v["%s_mcp" % f] - v["%s_mcp" % g]) ** 2 + (v["%s_pip" % f] - v["%s_pip" % g]) ** 2)
        nat += 0.2 * (v["th1_x"] ** 2 + v["th1_y"] ** 2 + v["th1_z"] ** 2) + 0.5 * v["th2_a"] ** 2 + 0.3 * (v["th3_f"] - v["th2_f"]) ** 2
        E["nat"] = P["nat"] * nat
        E["haste"] = P["haste"] * (v["hx"] ** 2 + v["hy"] ** 2 + v["hz"] ** 2 + 0.01 * (v["ta"] ** 2 + v["tb"] ** 2))
        tot = sum(E.values())
        if detalhe:
            return tot, E, rel, piores, (V, N, c, a, fo)
        return tot


def otimiza(custo, x0, iters=400):
    b = limites()
    r = minimize(custo, x0, method="L-BFGS-B", bounds=b, options=dict(maxiter=iters, eps=0.05))
    r2 = minimize(custo, r.x, method="Powell", bounds=b, options=dict(maxiter=6000, xtol=0.05, ftol=1e-6))
    return r2 if r2.fun < r.fun else r
