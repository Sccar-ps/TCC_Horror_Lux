"""quanto da volta da haste a mao cobre (raios radiais a partir do eixo, colisao com a pele)"""
import json, sys
import numpy as np
from solver import *

def raios_tri(O, D, V, T, tmax=4.0):
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    e1, e2 = b - a, c - a
    hits = []
    for o, d in zip(O, D):
        p = np.cross(d, e2)
        det = np.einsum("ij,ij->i", e1, p)
        ok = np.abs(det) > 1e-9
        inv = np.where(ok, 1 / np.where(ok, det, 1), 0)
        s = o - a
        u = np.einsum("ij,ij->i", s, p) * inv
        q = np.cross(s, e1)
        v = (q @ d) * inv
        t = np.einsum("ij,ij->i", e2, q) * inv
        m = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 0) & (t < tmax)
        hits.append(t[m].min() if m.any() else np.inf)
    return np.array(hits)

R = json.load(open(sys.argv[1])); escala(R["escala"])
m = Mao()
L = locais(m, np.array(R["x"]))
V, N = m.pele(m.cs(L))
# triangulos so da mao
sel = set(range(len(m.idx)))
remap = -np.ones(len(m.d.v), int); remap[m.idx] = np.arange(len(m.idx))
T = remap[m.d.t]; T = T[(T >= 0).all(1)]
c, a = np.array(R["c"]), np.array(R["a"])
e1 = np.cross(a, (1, 0, 0)); e1 /= np.linalg.norm(e1); e2 = np.cross(a, e1)
fr = np.array((-1.0, 0, 0)); fr -= a * (fr @ a); fr /= np.linalg.norm(fr)
lado = np.cross(a, fr)
print("direcoes: X socket (frente) = %s, Y socket = %s" % (np.round(fr, 2), np.round(lado, 2)))
for h in (-3.0, -1.5, 0.0, 1.5, 3.0):
    angs = np.radians(np.arange(0, 360, 15))
    D = np.array([np.cos(t) * fr + np.sin(t) * lado for t in angs])
    O = np.array([c + a * h + d * 0.1 for d in D])
    t = raios_tri(O, D, V, T)
    linha = "".join("#" if x < 1.2 else ("+" if x < 2.5 else ".") for x in t)
    print("h %+.1f cm: %s  (0 graus = +X do socket, sentido +Y)  coberto %.0f%%" % (h, linha, 100 * np.mean(t < 2.5)))
