"""Patch da camada 1P (ABP_CowboyFP_Visible):
   - EventGraph: LookDownA = MapRangeClamped(Pitch, LeanStartPitch, LeanFullPitch, 0, 1) * StandW
                 alvo do BodyShift += LookDownShift * LookDownA   (o 'pescoco' avanca ao olhar para baixo)
   - Comentarios explicativos nos dois grafos
"""
from t3d import *
import json

VIS = "/Game/Characters/MixamoFP/Blueprints/ABP_CowboyFP_Visible.ABP_CowboyFP_Visible"
VIS_C = "/Game/Characters/MixamoFP/Blueprints/ABP_CowboyFP_Visible.ABP_CowboyFP_Visible_C"
KML = "/Script/Engine.KismetMathLibrary"
KML_D = "/Script/Engine.Default__KismetMathLibrary"
D = ("real", "double", "None")


class G(Graph):
    def __init__(self, *a, tag="FX"):
        super().__init__(*a)
        self.tag = tag

    def uname(self, base):
        self._n += 1
        return "%s_%s%02d" % (base, self.tag, self._n)


def dbl(name, default="0.0"):
    return (name, "real", "double", "None", default, False, False)


def kml(g, func, x, y, ret=D, inputs=()):
    return call(g, KML, func, x, y, lib=KML_D, ret=ret, inputs=inputs)


def math2(g, func, x, y, a="0.0", b="0.0"):
    return kml(g, func, x, y, inputs=[dbl("A", a), dbl("B", b)])


def comment(g, text, x, y, wdt, hgt, color="(R=0.10,G=0.35,B=0.60,A=1.0)"):
    n = Node(g, "/Script/UnrealEd.EdGraphNode_Comment", g.uname("EdGraphNode_Comment"), x, y, [
        "CommentColor=%s" % color, "NodeWidth=%d" % wdt, "NodeHeight=%d" % hgt, 'NodeComment="%s"' % text])
    return n


X, Y = -600, 500
v = G(VIS, "EventGraph", abpc_ref(VIS_C), tag="FX")
g_lds = var_get(v, "LookDownShift", "real", "double", x=X + 1380, y=Y + 1100)
f_la = kml(v, "MapRangeClamped", X + 1120, Y + 960,
           inputs=[dbl("Value"), dbl("InRangeA", "-20.0"), dbl("InRangeB", "-75.0"), dbl("OutRangeA", "0.0"), dbl("OutRangeB", "1.0")])
f_law = math2(v, "Multiply_DoubleDouble", X + 1380, Y + 960)
f_lds = math2(v, "Multiply_DoubleDouble", X + 1620, Y + 1000)
f_sum = math2(v, "Add_DoubleDouble", X + 2000, Y + 560)
link(f_la["ReturnValue"], f_law["A"])
link(f_law["ReturnValue"], f_lds["A"]); link(g_lds["LookDownShift"], f_lds["B"])
link(f_lds["ReturnValue"], f_sum["B"])
c1 = comment(v, "1) Initialize: esconde cabeca e bracos da malha visivel e guarda a referencia do Player (cast uma unica vez)",
             -1260, -380, 1800, 330)
c2 = comment(v, "2) Update (so a malha visivel, a sombra nao muda): BodyShift mantem o pescoco NeckMinBehind cm atras da camera "
                "(corrige a inclinacao das animacoes) + LookDownShift ao olhar para baixo; LeanRot inclina o tronco para tras. "
                "StandW desliga tudo agachado.", -1260, 20, 3200, 1300)
open("mx_vis3_event.t3d", "w", newline="").write(v.text())
names = {"fx_map": f_la.name, "fx_mulw": f_law.name, "fx_sum": f_sum.name, "fx_c1": c1.name, "fx_c2": c2.name}

a = G(VIS, "AnimGraph", abpc_ref(VIS_C), tag="FY")
c3 = comment(a, "Camada 1P: copia a pose da malha-sombra (Mesh) e aplica BodyShift na raiz + LeanRot em spine_01, "
                "so para o que a camera ve", -940, -120, 1660, 420)
open("mx_vis3_anim.t3d", "w", newline="").write(a.text())
names["fy_c3"] = c3.name
json.dump(names, open("mx_vis3_names.json", "w"), indent=1)
print(names)
