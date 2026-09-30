# LUX - Passo 2: conteudo dos loops por tags (LOOPn_ON aparece no loop n, LOOPn_OFF some no loop n).
# So muda tags e cria duplicados de atores que ja existem (tag extra LUX_LOOP_CONTEUDO, pasta LUX/Loop/Conteudo).
# Idempotente: apaga os duplicados antigos, tira as tags LOOPn_* dos alvos e aplica tudo de novo. Nao salva.
#   py "<projeto>/Tools/Loop/apply_loop_tags.py"
#
# Loop 1: sem tags (30/09: os sinais do loop 1 sao eventos EV_L1_* de add_loop_events.py; o loop 0, 1a passagem, e o normal).
# Loop 2: aparece um quadro novo no corredor (a "foto da Lia"). PLACEHOLDER: a tela usa o material da pintura
#         que ja existe no corredor, porque nao ha imagem da Lia no projeto.
# Loop 3: as luzes das arandelas 3 e 5 do corredor apagam; aparece uma vela acesa no chao do corredor.
# Loop 4: a cadeira de leitura da sala some do canto e aparece no meio da sala, virada para a porta;
#         o quadro vazio O5 do corredor fica torto (sinal visual das batidas; o som fica para o Passo 3).
import re
import unreal

CONTEUDO = "LUX_LOOP_CONTEUDO"
SISTEMA = "LUX_LOOP"
FOLDER = "LUX/Loop/Conteudo"
TRANSACAO = "LUX: tags dos loops"
RX_LOOP = re.compile(r"^LOOP\d+_(ON|OFF)$")
V, R = unreal.Vector, unreal.Rotator

# tags em atores existentes
TAGS = {
    "LUX_Luz_Corredor_Arandela3": "LOOP3_OFF",
    "LUX_Luz_Corredor_Arandela5": "LOOP3_OFF",
    "Sala_Cadeira_Leitura": "LOOP4_OFF",
    "COL_Sala_Cadeira_Leitura": "LOOP4_OFF",
    "Corredor_Quadro_O5": "LOOP4_OFF",
}

# duplicados: (label novo, original, tag, funcao(orig) -> (loc, rot))
def mover(dx=0.0, dy=0.0, dz=0.0):
    return lambda a: (a.get_actor_location() + V(dx, dy, dz), a.get_actor_rotation())


def em(x, y, z, yaw):
    return lambda a: (V(x, y, z), R(roll=0.0, pitch=0.0, yaw=yaw))


def torto(graus):
    # gira em torno da normal da parede (eixo X do mundo: a parede leste do corredor fica em x = -3100)
    return lambda a: (a.get_actor_location(),
                      unreal.MathLibrary.compose_rotators(a.get_actor_rotation(),
                                                          unreal.MathLibrary.rotator_from_axis_and_angle(V(1, 0, 0), graus)))


CADEIRA = (-2600.0, -1600.0)
YAW_CADEIRA = -52.3  # frente da cadeira (+X local) apontando para a LOOP_PortaSala (macaneta em ~(-2336, -1942))
VELA = (-3140.0, -50.0)

DUPLICADOS = [
    # loop 2: quadro da Lia na parede leste, perto da chegada (mesmo par moldura+tela do Corredor_Quadro_O4, 260 cm adiante)
    ("LOOPC_L2_QuadroLia", "Corredor_Quadro_O4", "LOOP2_ON", mover(dy=260.0)),
    ("LOOPC_L2_QuadroLia_Tela", "Corredor_Quadro_O3_Tela2", "LOOP2_ON", mover(dy=260.0)),
    # loop 3: vela acesa no chao do corredor (copia da vela do banquinho da sala e da luz dela)
    ("LOOPC_L3_VelaChao", "Sala_Vela_Banquinho", "LOOP3_ON", em(VELA[0], VELA[1], 0.0, 0.0)),
    ("LOOPC_L3_VelaChao_Luz", "LUX_Luz_Sala_Vela", "LOOP3_ON", em(VELA[0], VELA[1], 103.9 - 58.2, 0.0)),
    # loop 4: cadeira de leitura no meio da sala, virada para a porta (+ a colisao dela)
    ("LOOPC_L4_Cadeira", "Sala_Cadeira_Leitura", "LOOP4_ON", em(CADEIRA[0], CADEIRA[1], 0.167, YAW_CADEIRA)),
    ("LOOPC_L4_Cadeira_COL", "COL_Sala_Cadeira_Leitura", "LOOP4_ON", em(CADEIRA[0], CADEIRA[1], 43.28479, YAW_CADEIRA)),
    # loop 4: quadro O5 torto
    ("LOOPC_L4_QuadroTorto", "Corredor_Quadro_O5", "LOOP4_ON", torto(12.0)),
]


def tags_de(a):
    return [str(t) for t in a.get_editor_property("tags")]


def main():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world.get_name() != "Mapa_B":
        raise RuntimeError("abra o Mapa_B (aberto: %s)" % world.get_path_name())
    with unreal.ScopedEditorTransaction(TRANSACAO):
        antigos = [a for a in eas.get_all_level_actors() if CONTEUDO in tags_de(a)]
        for a in antigos:
            eas.destroy_actor(a)
        print("duplicados antigos apagados: %d" % len(antigos))
        by = {a.get_actor_label(): a for a in eas.get_all_level_actors()}
        faltam = [n for n in list(TAGS) + [d[1] for d in DUPLICADOS] if n not in by]
        if faltam:
            raise RuntimeError("atores nao encontrados: %s" % ", ".join(faltam))
        # limpa tags LOOPn_* de qualquer ator que nao seja do sistema (idempotencia)
        for a in by.values():
            t = tags_de(a)
            if SISTEMA in t:
                continue
            limpo = [x for x in t if not RX_LOOP.match(x)]
            if len(limpo) != len(t):
                a.set_editor_property("tags", [unreal.Name(x) for x in limpo])
        for label, tag in TAGS.items():
            a = by[label]
            a.set_editor_property("tags", [unreal.Name(x) for x in tags_de(a) + [tag]])
            print("%-28s + %s" % (label, tag))
        for label, orig, tag, pose in DUPLICADOS:
            o = by[orig]
            loc, rot = pose(o)
            d = eas.duplicate_actor(o, world, V(0, 0, 0))
            d.set_actor_location_and_rotation(loc, rot, False, False)
            d.set_actor_label(label)
            d.set_folder_path(FOLDER)
            # sem LUX_FURNISH: o furnish.py nao deve apagar nem recriar estes atores
            base = [x for x in tags_de(o) if x != "LUX_FURNISH" and not RX_LOOP.match(x)]
            d.set_editor_property("tags", [unreal.Name(x) for x in base + [tag, CONTEUDO]])
            print("%-28s = copia de %s em %s rot %s + %s" % (label, orig, loc, rot, tag))


main()
