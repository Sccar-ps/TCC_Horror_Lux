"""nucleo offline: malha do braco (glTF exportado pela Unreal) + pose (pose.json) + skinning em espaco UE (cm, Z pra cima)"""
import json, struct, os
import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
# dados exportados pelo Tools/Player/vela_mao_dump.py (Saved/LuxSnapshots/mao_dump); LUX_DUMP muda o lugar
D = os.environ.get("LUX_DUMP") or next((p for p in (os.path.join(AQUI, "dump"),
                                                     os.path.join(AQUI, "..", "..", "..", "Saved", "LuxSnapshots", "mao_dump"))
                                        if os.path.isdir(p)), os.path.join(AQUI, "dump"))


# ---------------------------------------------------------------- quaternions (x, y, z, w), convencao UE: qmul(a, b) = a depois de b
def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return np.array((aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
                     aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz))


def qinv(q): return np.array((-q[0], -q[1], -q[2], q[3]))


def qaxis(axis, graus):
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    s = np.sin(np.radians(graus) / 2)
    return np.array((a[0] * s, a[1] * s, a[2] * s, np.cos(np.radians(graus) / 2)))


def qmat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def qrot(q, v): return qmat(q) @ np.asarray(v, float)


def qang(a, b):
    return np.degrees(2 * np.arccos(min(1.0, abs(float(np.dot(a, b))))))


def mat4(p, q):
    M = np.eye(4)
    M[:3, :3] = qmat(q)
    M[:3, 3] = p
    return M


# ---------------------------------------------------------------- dados
class Dados:
    def __init__(self):
        self.P = json.load(open(os.path.join(D, "pose.json")))
        g = json.load(open(os.path.join(D, "arms.gltf")))
        buf = open(os.path.join(D, "arms.bin"), "rb").read()

        def acc(i):
            a = g["accessors"][i]
            bv = g["bufferViews"][a["bufferView"]]
            n = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}[a["type"]]
            dt = {5126: np.float32, 5123: np.uint16, 5121: np.uint8, 5125: np.uint32}[a["componentType"]]
            off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
            stride = bv.get("byteStride", 0)
            isz = np.dtype(dt).itemsize * n
            if stride and stride != isz:
                raw = np.frombuffer(buf, np.uint8, count=stride * a["count"], offset=off).reshape(a["count"], stride)[:, :isz]
                arr = np.frombuffer(raw.tobytes(), dt).reshape(a["count"], n)
            else:
                arr = np.frombuffer(buf, dt, count=n * a["count"], offset=off).reshape(a["count"], n)
            if a.get("normalized"):
                arr = arr.astype(np.float64) / np.iinfo(dt).max
            return arr

        pr = g["meshes"][0]["primitives"]
        V, J, W, T, N = [], [], [], [], []
        base = 0
        for p in pr:
            at = p["attributes"]
            v = acc(at["POSITION"]).astype(np.float64)
            V.append(v)
            N.append(acc(at["NORMAL"]).astype(np.float64))
            J.append(np.hstack([acc(at["JOINTS_0"]), acc(at["JOINTS_1"])]).astype(int) if "JOINTS_1" in at else acc(at["JOINTS_0"]).astype(int))
            W.append(np.hstack([acc(at["WEIGHTS_0"]), acc(at["WEIGHTS_1"])]).astype(np.float64) if "WEIGHTS_1" in at else acc(at["WEIGHTS_0"]).astype(np.float64))
            T.append(acc(p["indices"]).reshape(-1, 3).astype(int) + base)
            base += len(v)
        gl = np.vstack(V)
        # glTF (x, y, z) = UE (x, z, y) / 100   (conferido: bind das juntas = pose de referencia do pose.json)
        self.v = np.stack([gl[:, 0], gl[:, 2], gl[:, 1]], 1) * 100.0
        gn = np.vstack(N)
        self.n = np.stack([gn[:, 0], gn[:, 2], gn[:, 1]], 1)
        self.j = np.vstack(J)
        self.w = np.vstack(W)
        self.w /= self.w.sum(1, keepdims=True)
        self.t = np.vstack(T)
        sk = g["skins"][0]
        self.juntas = [g["nodes"][i]["name"] for i in sk["joints"]]
        ibm = acc(sk["inverseBindMatrices"]).reshape(-1, 4, 4).transpose(0, 2, 1).astype(np.float64)  # column-major
        C = np.zeros((4, 4))
        C[0, 0] = C[1, 2] = C[2, 1] = 0.01
        C[3, 3] = 1       # UE -> glTF
        Ci = np.linalg.inv(C)
        self.bind = np.array([Ci @ np.linalg.inv(m) @ C for m in ibm])        # junta -> componente (UE), pose de bind
        # hierarquia
        self.pai = {}
        for i, nd in enumerate(g["nodes"]):
            for c in nd.get("children", []):
                if g["nodes"][c].get("name") and nd.get("name"):
                    self.pai[g["nodes"][c]["name"]] = nd["name"]
        self.ordem = [b for b in self.P["nomes"]]

    # pose local (dict osso -> (p, q)) -> componente
    def cs(self, local):
        out = {}
        for b in self.ordem:
            if b not in local:
                continue
            p, q = np.asarray(local[b][0], float), np.asarray(local[b][1], float)
            pa = self.pai.get(b)
            if pa in out:
                pp, pq = out[pa]
                out[b] = (pp + qrot(pq, p), qmul(pq, q))
            else:
                out[b] = (p, q)
        return out

    def pele(self, cs, idx=None):
        """vertices na pose (componente)"""
        S = np.array([mat4(*cs[b]) @ np.linalg.inv(self.bind[i]) if b in cs else np.eye(4) for i, b in enumerate(self.juntas)])
        v = self.v if idx is None else self.v[idx]
        j = self.j if idx is None else self.j[idx]
        w = self.w if idx is None else self.w[idx]
        vh = np.hstack([v, np.ones((len(v), 1))])
        out = np.zeros((len(v), 3))
        for k in range(j.shape[1]):
            M = S[j[:, k]]
            out += w[:, k:k + 1] * np.einsum("nij,nj->ni", M, vh)[:, :3]
        return out

    def local(self, fonte="idle0"):
        return {b: (np.array(t[0]), np.array(t[1])) for b, t in self.P[fonte]["LOCAL"].items()}
