"""vistas de um resultado (JSON do pega.py): 4 lados com z-buffer e o olho do jogador (braco pelo IK do vela_pega.py)
    python vistas.py pega_final.json   -> pega_final_vistas.png"""
import json, sys
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.spatial.transform import Rotation
from braco import PoseJ, escala as esc_vp, braco, vp
from solver import *
from render import Cena, MESH_NA_CAMERA
from zbuf import vista

arq = sys.argv[1]
R = json.load(open(arq)); s = R["escala"]
escala(s); esc_vp(s)
c, a = np.array(R["c"]), np.array(R["a"])
m = Mao()
L = dict(m.base); L.update(locais(m, np.array(R["x"])))
alvo, r, Lb = braco(PoseJ(), c, a, vp.ALVO_FIXO)
for b, q in Lb.items():
    L[b] = (m.base[b][0], np.array(q))
fr = np.array((-1.0, 0, 0)); fr -= a * (fr @ a); fr /= np.linalg.norm(fr)
q = Rotation.from_matrix(np.stack([fr, np.cross(a, fr), a], 1)).as_quat()
cena = Cena(m.d, escala=s)
cs, pv, cv, (sp, sq) = cena.monta(L, (c, q))
X, Y, Z = qrot(sq, (1, 0, 0)), qrot(sq, (0, 1, 0)), qrot(sq, (0, 0, 1))
(tx, ty, tz), yaw = MESH_NA_CAMERA
qc = qaxis((0, 0, 1), yaw)
olho = qrot(qinv(qc), -np.array((tx, ty, tz)))
obj = [(pv, cena.tri_l, cena.cor), (cv, cena.cT, np.array((0.55, 0.55, 0.6)))]
fig, axs = plt.subplots(1, 5, figsize=(25, 5.5))
axs[0].imshow(vista(obj, olho, sp, qrot(qinv(qc), (0, 0, 1)), fov=16)); axs[0].set_title("olho do jogador (zoom)")
for ax, (nome, v) in zip(axs[1:], (("frente (+X do socket)", X), ("tras (-X)", -X), ("dorso (+Y)", Y), ("palma (-Y)", -Y))):
    ax.imshow(vista(obj, sp + v * 20, sp, Z, fov=45)); ax.set_title(nome)
for ax in axs:
    ax.axis("off")
fig.suptitle("%s | pulso: flexao %.0f desvio %.0f torcao %.0f | cotovelo %.0f" % (arq, r["flexao"], r["desvio"], r["torcao"], r["cotovelo"]))
plt.tight_layout(); plt.savefig(arq.replace(".json", "_vistas.png"), dpi=70)
