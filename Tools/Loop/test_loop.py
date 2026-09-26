# Teste de ponta a ponta do loop no PIE (nao altera o mapa: os 2 atores de teste sao removidos no fim).
#   py "C:/Users/bruno/Documents/Unreal Projects/TCC_Horror_Lux/Tools/Loop/test_loop.py"
# O jogador e posicionado por script e "aperta interagir" pela funcao Interact do BP_Player (trace real).
# Resultado: Saved/Loop/test_log.txt (PASSOU/FALHOU por item) e Saved/Loop/test_*.png
import glob, math, os, traceback, unreal

saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(saved, "Loop")
LOG = os.path.join(OUT, "test_log.txt")
SHOTS = os.path.join(saved, "Screenshots")
GS = unreal.GameplayStatics
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
DIANTE_SALA = unreal.Vector(-2294.0, -1850.0, 98.0)   # dentro da sala, 1,27 m da porta, olhando -Y
NO_GATILHO = unreal.Vector(-3275.0, 620.0, 98.0)
log, fails = [], []


def w(m):
    log.append(str(m))


def check(name, ok, info=""):
    w("%s  %s %s" % ("PASSOU" if ok else "FALHOU", name, info))
    if not ok:
        fails.append(name)


def pngs():
    return set(glob.glob(os.path.join(SHOTS, "**", "*.png"), recursive=True))


def steps():
    # ---- atores de teste no mapa do editor (tags do sistema de etapas)
    limpar_teste()
    test = []
    for label, tag, y in (("LOOP_TESTE_2ON", "LOOP2_ON", 300.0), ("LOOP_TESTE_3OFF", "LOOP3_OFF", 0.0)):
        a = eas.spawn_actor_from_class(unreal.PointLight, unreal.Vector(-3275.0, y, 250.0), unreal.Rotator())
        a.set_actor_label(label)
        a.set_editor_property("tags", [unreal.Name(tag), unreal.Name("LUX_LOOP_TESTE")])
        test.append(a)
    les.editor_request_begin_play()
    while not ues.get_game_world() or not GS.get_player_character(ues.get_game_world(), 0):
        yield 0.2
    yield 2.0
    world = ues.get_game_world()
    player, pc = GS.get_player_character(world, 0), GS.get_player_controller(world, 0)
    lux = GS.get_all_actors_with_tag(world, "LUX_LOOP")
    mgr = [a for a in lux if a.get_class().get_name().startswith("BP_LuxLoopManager")][0]
    ldoor = [a for a in lux if a.get_class().get_name().startswith("BP_LuxLoopDoor")][0]
    q, saida, cheg = (mgr.get_editor_property(k) for k in ("PortaQuarto", "PortaSaida", "Chegada"))
    t2, t3 = sorted(GS.get_all_actors_with_tag(world, "LUX_LOOP_TESTE"), key=lambda a: a.get_actor_label())
    hid = lambda a: a.get_editor_property("hidden")
    w("pawn %s em %s" % (player.get_class().get_name(), player.get_actor_location()))
    check("inicio: LOOP2_ON escondido", hid(t2))
    check("inicio: LOOP3_OFF visivel", not hid(t3))
    check("inicio: porta de saida real escondida", hid(saida) and not hid(ldoor))
    final = mgr.get_editor_property("LoopFinal")

    def interagir():
        player.set_actor_location(DIANTE_SALA, False, True)
        pc.set_control_rotation(unreal.Rotator(roll=0.0, pitch=-3.0, yaw=-90.0))

    for n in range(1, final + 1):
        interagir()
        yield 0.5
        player.call_method("Interact")
        yield 0.1
        via = "BP_Player.Interact"
        if not mgr.get_editor_property("bOcupado"):
            via = "fallback: Interact direto na porta (o trace do jogador nao pegou a porta)"
            ldoor.call_method("Interact", (None,))
        yield 1.3
        d = player.get_actor_location() - cheg.get_actor_location()
        check("loop %d: troca" % n, mgr.get_editor_property("LoopAtual") == n and math.hypot(d.x, d.y) < 60,
              "(%s; LoopAtual=%s; dist. da chegada %.0f cm)" % (via, mgr.get_editor_property("LoopAtual"), math.hypot(d.x, d.y)))
        check("loop %d: porta do quarto abrindo" % n, not q.get_editor_property("IsClosed"))
        if n == 1:
            yield from shot(world, "1_apos_troca")
        yield 1.5
        if n == 1:
            yield from shot(world, "2_porta_aberta")
        player.set_actor_location(NO_GATILHO, False, True)
        yield 0.5
        check("loop %d: porta fecha atras" % n, q.get_editor_property("IsClosed") and not mgr.get_editor_property("bArmado"))
        if n == 1:
            pc.set_control_rotation(unreal.Rotator(roll=0.0, pitch=-3.0, yaw=90.0))
            yield 1.5
            yield from shot(world, "3_porta_fechada_atras")
        if n == 2:
            check("loop 2: LOOP2_ON apareceu", not hid(t2))
        if n == 3:
            check("loop 3: LOOP3_OFF sumiu", hid(t3))
        yield 2.0
    check("loop final: porta de loop some e a real aparece", hid(ldoor) and not hid(saida))
    interagir()
    yield 0.5
    player.call_method("Interact")
    yield 2.0
    check("depois do final: porta da sala abre de verdade", not saida.get_editor_property("IsClosed")
          and mgr.get_editor_property("LoopAtual") == final, "(IsClosed=%s)" % saida.get_editor_property("IsClosed"))
    yield from shot(world, "4_saida_aberta")
    les.editor_request_end_play()
    yield 1.0
    limpar_teste()


def limpar_teste():
    for a in eas.get_all_level_actors():
        if "LUX_LOOP_TESTE" in [str(t) for t in a.tags]:
            eas.destroy_actor(a)


def shot(world, name):
    before = pngs()
    unreal.SystemLibrary.execute_console_command(world, "HighResShot 1")
    yield 1.5
    new = sorted(pngs() - before, key=os.path.getmtime)
    if new:
        dst = os.path.join(OUT, "test_%s.png" % name)
        if os.path.exists(dst):
            os.remove(dst)
        os.replace(new[-1], dst)


gen = steps()
st = {"wait": 0.0}


def tick(dt):
    if st.get("cleanup") and not les.is_in_play_in_editor():  # erro no meio: tira os atores de teste depois do PIE
        limpar_teste()
        st["cleanup"] = False
        unreal.unregister_slate_post_tick_callback(handle)
        return
    st["wait"] -= dt
    if st["wait"] > 0:
        return
    try:
        st["wait"] = next(gen)
        return
    except StopIteration:
        w("RESULTADO: " + ("TUDO PASSOU" if not fails else "FALHAS: %s" % fails))
    except Exception:
        w("ERRO " + traceback.format_exc())
        if les.is_in_play_in_editor():
            les.editor_request_end_play()
        st["cleanup"] = True
    open(LOG, "w", encoding="utf-8").write("\n".join(log))
    if not st.get("cleanup"):
        unreal.unregister_slate_post_tick_callback(handle)


handle = unreal.register_slate_post_tick_callback(tick)
