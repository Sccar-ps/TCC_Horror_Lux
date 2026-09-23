import sys, os, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fbx"))
from fk import Rig

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prep")
SKIP = ("Thumb", "Index", "Middle", "Ring", "Pinky", "_End")


def draw(ax, rig, pos, view):
    for mid, pid in rig.parent.items():
        n, pn = rig.name[mid], rig.name[pid]
        if pn == "Armature" or any(s in n for s in SKIP):
            continue
        a, b = pos[pn], pos[n]
        col = "#c0392b" if n.startswith("Left") else ("#2471a3" if n.startswith("Right") else "#333333")
        if view == "side":
            ax.plot([a[2], b[2]], [a[1], b[1]], color=col, lw=1.6)
        else:
            ax.plot([a[0], b[0]], [a[1], b[1]], color=col, lw=1.6)
    ax.axhline(0, color="#999999", lw=0.8)


def sheet(names, out, ncols=5):
    fig, axes = plt.subplots(len(names), ncols + 1, figsize=(2.1 * (ncols + 1), 2.3 * len(names)))
    for r, name in enumerate(names):
        rig = Rig(os.path.join(D, name + ".fbx"))
        ts = np.linspace(rig.t0, rig.t1, ncols + 1)[:-1] if rig.t1 > rig.t0 else [rig.t0] * ncols
        for c in range(ncols + 1):
            ax = axes[r][c]
            t = ts[c] if c < ncols else ts[len(ts) // 2]
            pos = rig.pose(t)
            draw(ax, rig, pos, "side" if c < ncols else "front")
            ax.set_xlim(-80, 80); ax.set_ylim(-5, 190); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
            if c == 0:
                ax.set_ylabel(name, fontsize=8)
            if r == 0:
                ax.set_title("frente" if c == ncols else "lado t=%.2f" % t, fontsize=7)
            lf, rf = pos["LeftFoot"][1], pos["RightFoot"][1]
            ax.text(-78, 180, "hips %.0f  pes %.0f/%.0f" % (pos["Hips"][1], lf, rf), fontsize=5.5)
    plt.tight_layout()
    plt.savefig(out, dpi=90)
    plt.close(fig)


if __name__ == "__main__":
    groups = [["MX_Idle", "MX_Walk_F", "MX_Walk_B", "MX_Walk_L", "MX_Walk_R", "MX_Run_L", "MX_Run_R"],
              ["MX_Crouch_Idle", "MX_Crouch_F", "MX_Crouch_B", "MX_Crouch_L", "MX_Crouch_R", "MX_Fall"]]
    for i, g in enumerate(groups):
        sheet(g, os.path.join(os.path.dirname(D), "sheet_%d.png" % i))
    print("ok")
