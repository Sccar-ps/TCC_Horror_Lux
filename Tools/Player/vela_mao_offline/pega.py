"""LUX: pega da haste do castical calculada na MALHA REAL da mao (fora da Unreal).
Uso (python3 com numpy, scipy e matplotlib):
    1) na Unreal, sem PIE:  py "<projeto>/Tools/Player/vela_mao_dump.py"   (exporta pele + ossos para Saved/LuxSnapshots/mao_dump)
    2) aqui:                python pega.py [partida.json] [saida.json]
       partida = resultado anterior (padrao pega_final.json); sai a tabela HASTE_CENTRO/HASTE_EIXO/PEGA_DEDOS para colar
       no Tools/Player/vela_pega.py, e as vistas em PNG (z-buffer) + a vista do olho do jogador.
    3) na Unreal:           py "<projeto>/Tools/Player/vela_pega.py" instalar
Custo (solver.py): nada entra no castical (perfil real), partes da mao nao se atravessam, falanges proximal/media
encostam na haste, dedos vizinhos encostados, pontas na haste ou na palma, palma encostada, polegar abraca a haste
e apoia a ponta no dorso do indicador/medio, e naturalidade (DIP ~0,7 PIP, cascata entre dedos, pouca abertura).
Como foi obtido em 28/09: partidas em 0.42/0.50/0.55 (0.42 nao cabe: palma 1,6 cm no colar/copinho) -> 0.50;
L-BFGS-B + Powell nos 29 parametros; busca global (evolucao diferencial) so no polegar; de novo com "vizinhos"."""
import json, sys, time
import numpy as np
from scipy.optimize import differential_evolution
from solver import *
from mao import qang

ini = sys.argv[1] if len(sys.argv) > 1 else "pega_final.json"
out = sys.argv[2] if len(sys.argv) > 2 else "pega_nova.json"
R = json.load(open(ini)); escala(R["escala"])
m = Mao()
C = Custo(m, np.array(R["c"]), np.array(R["a"]))
t = time.time()
x = otimiza(C, np.array(R["x"])).x
ks = [NOMES.index(n) for n in ("th1_x", "th1_y", "th1_z", "th2_f", "th2_a", "th3_f")]
b = limites()
def so_polegar(y):
    z = x.copy(); z[ks] = y
    return C(z)
d = differential_evolution(so_polegar, [b[k] for k in ks], seed=1, popsize=12, maxiter=50, tol=1e-4, polish=True, x0=x[ks])
if d.fun < C(x):
    x[ks] = d.x
tot, E, rel, piores, (V, N, c, a, fo) = C(x, True)
print("custo %.3f (%.0f s) | penetracao max %.2f cm" % (tot, time.time() - t, -fo.min()))
print("termos", {k: round(float(v), 3) for k, v in E.items()})
print("folgas (cm)", {k: round(float(v), 2) for k, v in rel.items()})
# tabela para o vela_pega.py (arredondada; a haste absorve hx..tb)
x = np.round(x, 1)
v = dict(zip(NOMES, x))
rv = np.array([v["th1_x"], v["th1_y"], v["th1_z"]]); ang = float(np.linalg.norm(rv)); ax = rv / max(ang, 1e-9)
a = a / np.linalg.norm(a)
print("\nHASTE_CENTRO = (%.2f, %.2f, %.2f)\nHASTE_EIXO = (%.4f, %.4f, %.4f)\nPEGA_DEDOS = {" % (tuple(c) + tuple(a)))
for f in DEDOS:
    print('    "%s_01_r": (("Z", %.1f), ("Y", %.1f)), "%s_02_r": (("Z", %.1f),), "%s_03_r": (("Z", %.1f),),' % (
        f, v[f + "_mcp"], v[f + "_abd"], f, v[f + "_pip"], f, v[f + "_dip"]))
print('    "ring_metacarpal_r": (("Z", %.1f),), "pinky_metacarpal_r": (("Z", %.1f),),' % (v["ring_meta"], v["pinky_meta"]))
print('    "thumb_01_r": (((%.3f, %.3f, %.3f), %.1f),),' % (ax[0], ax[1], ax[2], ang))
print('    "thumb_02_r": (("Z", %.1f), ("Y", %.1f)), "thumb_03_r": (("Z", %.1f),),\n}' % (v["th2_f"], v["th2_a"], v["th3_f"]))
for n in ("hx", "hy", "hz", "ta", "tb"):
    x[NOMES.index(n)] = 0
json.dump({"escala": R["escala"], "x": list(map(float, x)), "c": list(map(float, np.round(c, 2))), "a": list(map(float, np.round(a, 4)))},
          open(out, "w"))
print("salvo", out)
