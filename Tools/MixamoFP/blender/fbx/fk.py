import sys, os, collections
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from fbxparse import parse, props70
KT = 46186158000.0


def rx(a):
    c, s = np.cos(a), np.sin(a); return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def ry(a):
    c, s = np.cos(a), np.sin(a); return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rz(a):
    c, s = np.cos(a), np.sin(a); return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def euler_xyz(deg):
    x, y, z = np.radians(deg)
    return rz(z) @ ry(y) @ rx(x)


class Rig:
    def __init__(self, path):
        ver, root = parse(path)
        objs = root.find("Objects")
        self.models = {o.props[0]: o for o in objs.children if o.name == "Model"}
        self.by_id = {o.props[0]: o for o in objs.children}
        self.name = {k: v.props[1].split("\x00\x01")[0].replace("mixamorig:", "") for k, v in self.models.items()}
        self.id_of = {v: k for k, v in self.name.items()}
        self.parent = {}
        children_of = collections.defaultdict(list)
        for c in root.find("Connections").children:
            a, b = c.props[1], c.props[2]
            prop = c.props[3] if len(c.props) > 3 else None
            children_of[b].append((a, prop))
            if a in self.models and b in self.models:
                self.parent[a] = b
        self.rest = {}
        for k, m in self.models.items():
            p = props70(m)
            self.rest[k] = dict(T=np.array(p.get("Lcl Translation", [0, 0, 0]), float),
                                R=np.array(p.get("Lcl Rotation", [0, 0, 0]), float),
                                pre=np.array(p.get("PreRotation", [0, 0, 0]), float))
        # curvas
        self.curves = {}
        for mid in self.models:
            for cn_id, prop in children_of[mid]:
                cn = self.by_id.get(cn_id)
                if cn is None or cn.name != "AnimationCurveNode" or prop not in ("Lcl Translation", "Lcl Rotation"):
                    continue
                axes = {}
                for cv_id, cprop in children_of[cn_id]:
                    cv = self.by_id.get(cv_id)
                    if cv is not None and cv.name == "AnimationCurve":
                        axes[cprop] = (cv.find("KeyTime").props[0] / KT, cv.find("KeyValueFloat").props[0].astype(float))
                self.curves[(mid, prop)] = axes
        ts = [a[0] for ax in self.curves.values() for a in ax.values()]
        self.t0 = min(t[0] for t in ts); self.t1 = max(t[-1] for t in ts)
        self.order = []
        seen = set()
        def visit(k):
            if k in seen: return
            if k in self.parent: visit(self.parent[k])
            seen.add(k); self.order.append(k)
        for k in self.models: visit(k)

    def sample(self, mid, prop, t, default):
        axes = self.curves.get((mid, prop))
        if not axes: return default
        out = default.copy()
        for i, ax in enumerate(("d|X", "d|Y", "d|Z")):
            if ax in axes:
                tt, vv = axes[ax]
                out[i] = np.interp(t, tt, vv)
        return out

    def pose(self, t=None):
        """posicoes globais (cm, Y-up) de todos os ossos no tempo t (None = rest)"""
        G = {}
        for k in self.order:
            r = self.rest[k]
            T = r["T"] if t is None else self.sample(k, "Lcl Translation", t, r["T"])
            R = r["R"] if t is None else self.sample(k, "Lcl Rotation", t, r["R"])
            M = np.eye(4)
            M[:3, :3] = euler_xyz(r["pre"]) @ euler_xyz(R)
            M[:3, 3] = T
            G[k] = G[self.parent[k]] @ M if k in self.parent else M
        return {self.name[k]: G[k][:3, 3] for k in G}
