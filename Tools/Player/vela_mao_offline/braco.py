"""braco (IK do vela_pega.py) fora da Unreal: mesma matematica, pose lida do pose.json"""
import json, os, sys
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "fake"))            # modulo unreal falso (so para importar a matematica)
sys.path.insert(1, os.path.dirname(AQUI))                 # Tools/Player: vela_pega.py
import vela_pega as vp

from mao import D


class PoseJ:
    def __init__(self):
        P = json.load(open(os.path.join(D, "pose.json")))
        self.nomes = P["nomes"]
        self.loc = {b: (tuple(t[0]), tuple(t[1])) for b, t in P["idle0"]["LOCAL"].items()}
        self.cs = {b: (tuple(t[0]), tuple(t[1])) for b, t in P["idle0"]["WORLD"].items()}
        self.ref_hand = tuple(P["ref"]["LOCAL"]["hand_r"][1])


def escala(s):
    vp.ESCALA_VELA, vp.HASTE_R, vp.HASTE_MEIO = s, 1.75 * s, 15.6 * s


def braco(P, centro, eixo, alvo=None):
    """alvo = ((x,y,z), giro) ou None para a busca do vela_pega"""
    if alvo:
        r = vp.solve(P, tuple(centro), tuple(eixo), *alvo)
    else:
        nota, a, giro, r = vp.escolhe(P, tuple(centro), tuple(eixo))
        alvo = (a, giro)
    cl = P.cs["clavicle_r"][1]
    L = {"upperarm_r": vp.qmul(vp.qinv(cl), r["qu"]), "lowerarm_r": vp.qmul(vp.qinv(r["qu"]), r["ql"]),
         "hand_r": vp.qmul(vp.qinv(r["ql"]), r["qh"])}
    return alvo, r, L
