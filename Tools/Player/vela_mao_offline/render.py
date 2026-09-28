"""render simples (pintor) da mao + castical, para conferir a pega fora da Unreal"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from mao import *

ESCALA = 0.42
PERFIL = ((0.0, 10.2), (3.0, 10.2), (3.4, 4.3), (6.0, 4.3), (6.7, 1.8), (24.5, 1.8), (25.5, 4.6), (33.0, 4.9), (33.5, 2.5), (41.7, 2.5))
HASTE_MEIO = 15.6 * ESCALA
MESH_NA_CAMERA = ((-13.765, 0.0, -163.173), -90.0)

COR = {"index": (0.85, 0.35, 0.35), "middle": (0.35, 0.75, 0.35), "ring": (0.35, 0.45, 0.9), "pinky": (0.9, 0.8, 0.3),
       "thumb": (0.8, 0.4, 0.85)}


def raio_em(h):
    h = h / ESCALA
    if h <= PERFIL[0][0] or h >= PERFIL[-1][0]:
        return 0.0
    for (h0, r0), (h1, r1) in zip(PERFIL, PERFIL[1:]):
        if h0 <= h <= h1:
            return (r0 + (r1 - r0) * (h - h0) / ((h1 - h0) or 1)) * ESCALA
    return 0.0


def euler_ue(roll, pitch, yaw):
    """FRotator -> quat (UE)"""
    cr, sr = np.cos(np.radians(roll) / 2), np.sin(np.radians(roll) / 2)
    cp, sp = np.cos(np.radians(pitch) / 2), np.sin(np.radians(pitch) / 2)
    cy, sy = np.cos(np.radians(yaw) / 2), np.sin(np.radians(yaw) / 2)
    return np.array((cr * sp * sy - sr * cp * cy, -cr * sp * cy - sr * cp * sy, cr * cp * sy - sr * sp * cy, cr * cp * cy + sr * sp * sy))


def castical(n=28, ESCALA=ESCALA):
    """malha de revolucao no espaco do socket (Z = haste; origem = meio da haste)"""
    HASTE_MEIO = 15.6 * ESCALA
    hs = []
    for (h0, r0), (h1, r1) in zip(PERFIL, PERFIL[1:]):
        for t in np.linspace(0, 1, max(2, int((h1 - h0) / 1.0) + 1))[:-1]:
            hs.append((h0 + (h1 - h0) * t, r0 + (r1 - r0) * t))
    hs.append(PERFIL[-1])
    hs = [(0.0, 0.0)] + hs + [(PERFIL[-1][0], 0.0)]
    ang = np.linspace(0, 2 * np.pi, n, endpoint=False)
    V = []
    for h, r in hs:
        for a in ang:
            V.append((r * ESCALA * np.cos(a), r * ESCALA * np.sin(a), h * ESCALA - HASTE_MEIO))
    V = np.array(V)
    T = []
    for i in range(len(hs) - 1):
        for k in range(n):
            a, b = i * n + k, i * n + (k + 1) % n
            c, e = a + n, b + n
            T += [(a, b, e), (a, e, c)]
    return V, np.array(T)


class Cena:
    def __init__(self, d=None, escala=ESCALA):
        self.d = d or Dados()
        d = self.d
        # vertices da mao direita (peso nos ossos da mao/dedos)
        self.osso_dom = np.array([d.juntas[j] for j in d.j[np.arange(len(d.j)), d.w.argmax(1)]])
        mao = np.zeros(len(d.v), bool)
        for i, b in enumerate(d.juntas):
            if b == "hand_r" or (b.endswith("_r") and any(k in b for k in COR)) or b.startswith("lowerarm"):
                if b.startswith("lowerarm") and not b.endswith("_r"):
                    continue
                mao |= (d.w * (d.j == i)).sum(1) > 0.05
        self.idx = np.where(mao)[0]
        sel = set(self.idx.tolist())
        self.tri = np.array([t for t in d.t if t[0] in sel and t[1] in sel and t[2] in sel])
        remap = -np.ones(len(d.v), int)
        remap[self.idx] = np.arange(len(self.idx))
        self.tri_l = remap[self.tri]
        self.cor = np.array([next((COR[k] for k in COR if k in b and b.endswith("_r")), (0.93, 0.72, 0.6)) for b in self.osso_dom[self.idx]])
        self.cV, self.cT = castical(ESCALA=escala)

    def monta(self, local, sock):
        """sock = (loc em hand_r, quat em hand_r)"""
        cs = self.d.cs(local)
        pv = self.d.pele(cs, self.idx)
        hp, hq = cs["hand_r"]
        sp = hp + qrot(hq, sock[0])
        sq = qmul(hq, sock[1])
        cv = (qmat(sq) @ self.cV.T).T + sp
        return cs, pv, cv, (sp, sq)

    def desenha(self, ax, pv, cv, olho, alvo, cima=(0, 0, 1), fov=40, marca=None, titulo=""):
        f = np.asarray(alvo, float) - olho
        f /= np.linalg.norm(f)
        r = np.cross(f, cima)
        r /= np.linalg.norm(r)
        u = np.cross(r, f)
        polys, cols, zs = [], [], []
        luz = -f * 0.6 + u * 0.5 + r * 0.3
        luz /= np.linalg.norm(luz)
        esc = 1 / np.tan(np.radians(fov) / 2)
        for V, T, C in ((pv, self.tri_l, self.cor), (cv, self.cT, None)):
            rel = V - olho
            x, y, z = rel @ r, rel @ u, rel @ f
            z = np.maximum(z, 1e-3)
            px, py = esc * x / z, esc * y / z
            a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
            nn = np.cross(b - a, c - a)
            nn /= np.linalg.norm(nn, axis=1, keepdims=True) + 1e-12
            vis = (np.einsum("ij,ij->i", nn, (a + b + c) / 3 - olho) < 0) | (C is None)
            sh = 0.35 + 0.65 * np.abs(nn @ luz)
            for k in np.where(vis & (z[T].min(1) > 1))[0]:
                t = T[k]
                polys.append(np.stack([px[t], py[t]], 1))
                base = np.array((0.55, 0.55, 0.6)) if C is None else C[t].mean(0)
                cols.append(np.clip(base * sh[k], 0, 1))
                zs.append(z[t].mean())
        o = np.argsort(zs)[::-1]
        ax.add_collection(PolyCollection([polys[i] for i in o], facecolors=[cols[i] for i in o], edgecolors="none"))
        if marca is not None:
            rel = marca - olho
            ax.scatter(esc * (rel @ r) / (rel @ f), esc * (rel @ u) / (rel @ f), c="k", s=4, zorder=5)
        ax.set_xlim(-1, 1)
        ax.set_ylim(-1, 1)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(titulo, fontsize=9)


def vistas(cena, local, sock, arq, d_cam=18, marca=None, titulo=""):
    cs, pv, cv, (sp, sq) = cena.monta(local, sock)
    Z = qrot(sq, (0, 0, 1))
    X = qrot(sq, (1, 0, 0))
    Y = qrot(sq, (0, 1, 0))
    # camera do jogador
    (tx, ty, tz), yaw = MESH_NA_CAMERA
    qc = qaxis((0, 0, 1), yaw)
    # olho no espaco do componente: cam = qc*p + t -> p = qc^-1 (0 - t)
    olho = qrot(qinv(qc), -np.array((tx, ty, tz)))
    frente = qrot(qinv(qc), (1, 0, 0))
    cima_c = qrot(qinv(qc), (0, 0, 1))
    fig, axs = plt.subplots(2, 3, figsize=(15, 10))
    cena.desenha(axs[0, 0], pv, cv, olho, sp, cima_c, fov=30, titulo="olho do jogador", marca=marca)
    for ax, (nome, v) in zip(axs.flat[1:], (("frente +X", X), ("tras -X", -X), ("+Y", Y), ("-Y", -Y), ("cima", Z * 1 + X * 0.35))):
        cena.desenha(ax, pv, cv, sp + v / np.linalg.norm(v) * d_cam, sp, Z if "cima" not in nome else X, fov=45, titulo=nome, marca=marca)
    fig.suptitle(titulo)
    plt.tight_layout()
    plt.savefig(arq, dpi=80)
    plt.close(fig)
    return cs, pv, cv, (sp, sq)
