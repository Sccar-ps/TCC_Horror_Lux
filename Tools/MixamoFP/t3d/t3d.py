"""Gerador minimo de texto T3D (clipboard de grafos do Unreal 5.8)."""
import uuid

COMPACT = True

PT_TAIL = ("PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,"
           "PinType.bIsReference={ref},PinType.bIsConst={const},PinType.bIsWeakPointer=False,"
           "PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,")


def guid():
    return uuid.uuid4().hex.upper()


def cls_ref(path):  # /Script/Engine.Actor -> "/Script/CoreUObject.Class'/Script/Engine.Actor'"
    return "\"/Script/CoreUObject.Class'%s'\"" % path


def bpc_ref(path):  # BlueprintGeneratedClass
    return "\"/Script/Engine.BlueprintGeneratedClass'%s'\"" % path


def abpc_ref(path):
    return "\"/Script/Engine.AnimBlueprintGeneratedClass'%s'\"" % path


def struct_ref(path):
    return "\"/Script/CoreUObject.ScriptStruct'%s'\"" % path


VEC = struct_ref("/Script/CoreUObject.Vector")
ROT = struct_ref("/Script/CoreUObject.Rotator")
POSE = struct_ref("/Script/Engine.PoseLink")
CPOSE = struct_ref("/Script/Engine.ComponentSpacePoseLink")


class Pin:
    def __init__(self, node, name, cat, sub="", subobj="None", out=False, default=None, hidden=False,
                 friendly=None, ref=False, const=False, default_object=None, member_ref=None):
        self.node, self.name, self.cat, self.sub, self.subobj = node, name, cat, sub, subobj
        self.out, self.default, self.hidden, self.friendly = out, default, hidden, friendly
        self.ref, self.const, self.default_object, self.member_ref = ref, const, default_object, member_ref
        self.id = guid()
        self.links = []

    def keep(self):
        return bool(self.links) or self.default is not None or self.default_object is not None

    def text(self):
        s = 'CustomProperties Pin (PinId=%s,PinName="%s",' % (self.id, self.name)
        if COMPACT:
            if self.out:
                s += 'Direction="EGPD_Output",'
            s += 'PinType.PinCategory="%s",' % self.cat
            if self.sub:
                s += 'PinType.PinSubCategory="%s",' % self.sub
            if self.subobj != "None":
                s += 'PinType.PinSubCategoryObject=%s,' % self.subobj
            if self.default is not None:
                s += 'DefaultValue="%s",' % self.default
            if self.default_object is not None:
                s += 'DefaultObject="%s",' % self.default_object
            if self.links:
                s += "LinkedTo=(" + "".join("%s %s," % (p.node.name, p.id) for p in self.links) + "),"
            return s + ")"
        if self.friendly:
            s += 'PinFriendlyName=%s,' % self.friendly
        if self.out:
            s += 'Direction="EGPD_Output",'
        s += 'PinType.PinCategory="%s",PinType.PinSubCategory="%s",PinType.PinSubCategoryObject=%s,' % (
            self.cat, self.sub, self.subobj)
        tail = PT_TAIL.format(ref="True" if self.ref else "False", const="True" if self.const else "False")
        if self.member_ref:
            tail = tail.replace("PinType.PinSubCategoryMemberReference=()", "PinType.PinSubCategoryMemberReference=" + self.member_ref)
        s += tail
        if self.default is not None:
            s += 'DefaultValue="%s",' % self.default
        if self.default_object is not None:
            s += 'DefaultObject="%s",' % self.default_object
        if self.links:
            s += "LinkedTo=(" + "".join("%s %s," % (p.node.name, p.id) for p in self.links) + "),"
        s += ("PersistentGuid=00000000000000000000000000000000,bHidden=%s,bNotConnectable=False,"
              "bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)"
              % ("True" if self.hidden else "False"))
        return s


class Node:
    anim = False

    def __init__(self, graph, cls, name, x, y, props=()):
        self.graph, self.cls, self.name, self.x, self.y = graph, cls, name, x, y
        self.props = list(props)
        self.pins = {}
        graph.nodes.append(self)

    def pin(self, name, *a, **k):
        p = Pin(self, name, *a, **k)
        self.pins[name] = p
        return p

    def __getitem__(self, name):
        return self.pins[name]

    def text(self):
        lines = ['Begin Object Class=%s Name="%s"' % (self.cls, self.name)]
        if self.anim:
            lines += ['   Begin Object Class=/Script/AnimGraph.AnimGraphNodeBinding_Base Name="AnimGraphNodeBinding_Base_0"',
                      '   End Object',
                      '   Begin Object Name="AnimGraphNodeBinding_Base_0"',
                      '   End Object']
        lines += ["   " + p for p in self.props]
        if self.anim:
            lines.append("   Binding=\"/Script/AnimGraph.AnimGraphNodeBinding_Base'AnimGraphNodeBinding_Base_0'\"")
        lines += ["   NodePosX=%d" % self.x, "   NodePosY=%d" % self.y, "   NodeGuid=%s" % guid()]
        lines += ["   " + p.text() for p in self.pins.values() if (not COMPACT) or p.keep()]
        lines.append("End Object")
        return "\r\n".join(lines)


class AnimNode(Node):
    anim = True


class Graph:
    def __init__(self, bp_path, graph_name, self_class_ref):
        self.bp_path, self.graph_name, self.self_ref = bp_path, graph_name, self_class_ref
        self.nodes = []
        self._n = 0

    def uname(self, base):
        self._n += 1
        return "%s_CB%02d" % (base, self._n)

    def text(self):
        return "\r\n".join(n.text() for n in self.nodes) + "\r\n"


def link(a, b):
    """a: output Pin, b: input Pin (links sao bidirecionais no T3D)."""
    a.links.append(b)
    b.links.append(a)


# ---------------------------------------------------------------- fabricas de nos K2
def ev(g, member, x, y, extra_out=()):
    n = Node(g, "/Script/BlueprintGraph.K2Node_Event", g.uname("K2Node_Event"), x, y, [
        'EventReference=(MemberParent=%s,MemberName="%s")' % (cls_ref("/Script/Engine.AnimInstance"), member),
        "bOverrideFunction=True"])
    n.pin("OutputDelegate", "delegate", out=True,
          member_ref='(MemberParent=%s,MemberName="%s")' % (cls_ref("/Script/Engine.AnimInstance"), member))
    n.pin("then", "exec", out=True)
    for name, cat, sub in extra_out:
        n.pin(name, cat, sub, out=True, default="0.0")
    return n


def call(g, owner_path, func, x, y, pure=True, self_ctx=False, lib=None, ret=None, inputs=(), exec_pins=None, self_ref=None):
    """ret=(cat, sub, subobj); inputs=[(name, cat, sub, subobj, default, ref, const)]"""
    props = []
    if pure:
        props.append("bDefaultsToPureFunc=True")
    if self_ctx:
        props.append('FunctionReference=(MemberName="%s",bSelfContext=True)' % func)
    else:
        props.append('FunctionReference=(MemberParent=%s,MemberName="%s")' % (cls_ref(owner_path), func))
    n = Node(g, "/Script/BlueprintGraph.K2Node_CallFunction", g.uname("K2Node_CallFunction"), x, y, props)
    if not pure:
        n.pin("execute", "exec")
        n.pin("then", "exec", out=True)
    if lib:
        n.pin("self", "object", subobj=cls_ref(owner_path), hidden=True,
              friendly='NSLOCTEXT("K2Node", "Target", "Target")', default_object=lib)
    else:
        n.pin("self", "object", subobj=self_ref or cls_ref(owner_path),
              friendly='NSLOCTEXT("K2Node", "Target", "Target")', hidden=self_ctx)
    for (name, cat, sub, subobj, default, ref, const) in inputs:
        n.pin(name, cat, sub, subobj, default=default, ref=ref, const=const)
    if ret:
        n.pin("ReturnValue", ret[0], ret[1], ret[2], out=True)
    return n


def var_get(g, name, cat, sub="", subobj="None", owner=None, x=0, y=0):
    if owner:  # variavel de outra classe (NotSelfContext)
        props = ['VariableReference=(MemberParent=%s,MemberName="%s")' % (owner, name), "SelfContextInfo=NotSelfContext"]
    else:
        props = ['VariableReference=(MemberName="%s",bSelfContext=True)' % name]
    n = Node(g, "/Script/BlueprintGraph.K2Node_VariableGet", g.uname("K2Node_VariableGet"), x, y, props)
    n.pin(name, cat, sub, subobj, out=True)
    n.pin("self", "object", subobj=owner or g.self_ref, friendly='NSLOCTEXT("K2Node", "Target", "Target")',
          hidden=owner is None)
    return n


def var_set(g, name, cat, sub="", subobj="None", x=0, y=0):
    n = Node(g, "/Script/BlueprintGraph.K2Node_VariableSet", g.uname("K2Node_VariableSet"), x, y,
             ['VariableReference=(MemberName="%s",bSelfContext=True)' % name])
    n.pin("execute", "exec")
    n.pin("then", "exec", out=True)
    n.pin(name, cat, sub, subobj)
    n.pin("Output_Get", cat, sub, subobj, out=True)
    n.pin("self", "object", subobj=g.self_ref, friendly='NSLOCTEXT("K2Node", "Target", "Target")', hidden=True)
    return n


def is_valid(g, x, y):
    n = Node(g, "/Script/BlueprintGraph.K2Node_MacroInstance", g.uname("K2Node_MacroInstance"), x, y, [
        "MacroGraphReference=(MacroGraph=\"/Script/Engine.EdGraph'/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:IsValid'\","
        "GraphBlueprint=\"/Script/Engine.Blueprint'/Engine/EditorBlueprintResources/StandardMacros.StandardMacros'\","
        "GraphGuid=64422BCD430703FF5CAEA8B79A32AA65)"])
    n.pin("exec", "exec")
    n.pin("InputObject", "object", subobj=cls_ref("/Script/CoreUObject.Object"))
    n.pin("Is Valid", "exec", out=True)
    n.pin("Is Not Valid", "exec", out=True)
    return n


def cast(g, target_bpc_path, out_name, x, y):
    n = Node(g, "/Script/BlueprintGraph.K2Node_DynamicCast", g.uname("K2Node_DynamicCast"), x, y, [
        "TargetType=%s" % bpc_ref(target_bpc_path), "PureState=Impure"])
    n.pin("execute", "exec")
    n.pin("then", "exec", out=True)
    n.pin("CastFailed", "exec", out=True)
    n.pin("Object", "object", subobj=cls_ref("/Script/CoreUObject.Object"))
    n.pin(out_name, "object", subobj=bpc_ref(target_bpc_path), out=True)
    n.pin("bSuccess", "bool", out=True, hidden=True)
    return n


def branch(g, x, y):
    n = Node(g, "/Script/BlueprintGraph.K2Node_IfThenElse", g.uname("K2Node_IfThenElse"), x, y)
    n.pin("execute", "exec")
    n.pin("Condition", "bool", default="true")
    n.pin("then", "exec", out=True, friendly='NSLOCTEXT("K2Node", "true", "true")')
    n.pin("else", "exec", out=True, friendly='NSLOCTEXT("K2Node", "false", "false")')
    return n
