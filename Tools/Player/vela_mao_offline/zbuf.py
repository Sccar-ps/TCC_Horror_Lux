"""render com z-buffer (sem erro de ordem do pintor)"""
import numpy as np


def raster(tris2d, z3, cores, W=360, H=360):
    img = np.ones((H, W, 3))
    zb = np.full((H, W), np.inf)
    for (p, z, c) in zip(tris2d, z3, cores):
        xs = (p[:, 0] + 1) * 0.5 * (W - 1)
        ys = (1 - (p[:, 1] + 1) * 0.5) * (H - 1)
        x0, x1 = int(max(0, np.floor(xs.min()))), int(min(W - 1, np.ceil(xs.max())))
        y0, y1 = int(max(0, np.floor(ys.min()))), int(min(H - 1, np.ceil(ys.max())))
        if x1 < x0 or y1 < y0:
            continue
        X, Y = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
        (ax, ay), (bx, by), (cx, cy) = zip(xs, ys)
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-12:
            continue
        l1 = ((by - cy) * (X - cx) + (cx - bx) * (Y - cy)) / den
        l2 = ((cy - ay) * (X - cx) + (ax - cx) * (Y - cy)) / den
        l3 = 1 - l1 - l2
        m = (l1 >= 0) & (l2 >= 0) & (l3 >= 0)
        if not m.any():
            continue
        zz = l1 * z[0] + l2 * z[1] + l3 * z[2]
        sub = zb[y0:y1 + 1, x0:x1 + 1]
        upd = m & (zz < sub)
        sub[upd] = zz[upd]
        img[y0:y1 + 1, x0:x1 + 1][upd] = c
    return img


def vista(V_list, olho, alvo, cima, fov=45, W=360, H=360):
    f = np.asarray(alvo, float) - olho; f /= np.linalg.norm(f)
    r = np.cross(f, cima); r /= np.linalg.norm(r)
    u = np.cross(r, f)
    luz = -f * 0.6 + u * 0.5 + r * 0.3; luz /= np.linalg.norm(luz)
    esc = 1 / np.tan(np.radians(fov) / 2)
    P, Z, C = [], [], []
    for V, T, cor in V_list:
        rel = V - olho
        x, y, z = rel @ r, rel @ u, rel @ f
        ok = z > 0.5
        px, py = esc * x / np.maximum(z, 1e-3), esc * y / np.maximum(z, 1e-3)
        a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
        nn = np.cross(b - a, c - a); nn /= np.linalg.norm(nn, axis=1, keepdims=True) + 1e-12
        sh = 0.35 + 0.65 * np.abs(nn @ luz)
        for k, t in enumerate(T):
            if not ok[t].all():
                continue
            P.append(np.stack([px[t], py[t]], 1)); Z.append(z[t])
            base = cor if np.ndim(cor) == 1 else cor[t].mean(0)
            C.append(np.clip(np.asarray(base) * sh[k], 0, 1))
    return raster(P, Z, C, W, H)
