"""a pega (aditiva local, base = idle quadro 0) somada a cada quadro das animacoes da lanterna: penetracao e folgas"""
import json, sys
from solver import *

DEDO_OSSOS = [b for f in DEDOS for b in ("%s_metacarpal_r" % f, "%s_01_r" % f, "%s_02_r" % f, "%s_03_r" % f)] + \
             ["thumb_01_r", "thumb_02_r", "thumb_03_r"]


def avalia(arq):
    R = json.load(open(arq))
    escala(R["escala"])
    m = Mao()
    C = Custo(m, np.zeros(3), np.array((0, 0, 1.0)))
    x = np.array(R["x"])
    T = locais(m, x)
    c, a = np.array(R["c"]), np.array(R["a"])
    B0 = m.base
    piores = []
    for an, dados in m.d.P["anims"].items():
        pior_pen, pior_gap, onde = 0.0, 0.0, ""
        for f, loc in dados["quadros"].items():
            L = {}
            for b in DEDO_OSSOS:
                A = np.array(loc[b][1])
                q = qmul(qmul(T[b][1], qinv(B0[b][1])), A) if b in T else A
                L[b] = (np.array(loc[b][0]), q)
            cs = m.cs(L)
            V, N = m.pele(cs)
            fo, h = folga_haste(V, c, a)
            if -fo.min() > pior_pen:
                pior_pen, onde = -fo.min(), "%s q%s" % (m.parte[fo.argmin()], f)
            for d in DEDOS:
                for k in ("01", "02"):
                    g = fo[C.sel["%s_%s" % (d, k)]].min()
                    if g > pior_gap:
                        pior_gap = g
                        gq = "%s_%s q%s" % (d, k, f)
        piores.append((an, pior_pen, onde, pior_gap, gq if pior_gap > 0 else ""))
        print("%-30s penetracao max %.2f cm (%s) | maior folga prox/media %.2f cm (%s)" % piores[-1])
    return piores


if __name__ == "__main__":
    avalia(sys.argv[1])
