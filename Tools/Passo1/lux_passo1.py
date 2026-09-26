# -*- coding: utf-8 -*-
"""
LUX - Passo 1: estabilizacao do Mapa_B (UE 5.8, Python do editor).

Coloque este arquivo em  <projeto>/Tools/Passo1/lux_passo1.py  e rode no console do editor
(caixa "Cmd" no rodape), com o Mapa_B aberto e SEM PIE rodando:

    py "<projeto>/Tools/Passo1/lux_passo1.py"            -> so verifica; nao muda nada
    py "<projeto>/Tools/Passo1/lux_passo1.py" aplicar    -> corrige e salva (ver abaixo)

Modo "aplicar":
  - So faz alguma coisa se a atmosfera (PPV_Atmosfera, nevoa, lua, raio da VelaComoda) estiver no mapa aberto.
    Se faltar, NAO muda nada e diz o que rodar antes.
  - Desliga o Auto Possess Player dos pawns ThirdPersonCharacter (Ctrl+Z desfaz: "LUX: Passo 1").
  - Salva SO os pacotes do Mapa_B (.umap, _BuiltData e atores externos) e os Blueprints sujos de /Game/Masion/LUX/Loop/.
  - Qualquer outro asset sujo e so listado, nunca salvo.

Log completo em Saved/Passo1/passo1_log.txt.
"""

import os
import sys
import traceback

import unreal

MODO_APLICAR = any(str(a).lower() == "aplicar" for a in getattr(sys, "argv", [])[1:])
NOME_MAPA = "Mapa_B"
PASTA_LOOP = "/Game/Masion/LUX/Loop/"
TRANSACAO = "LUX: Passo 1"
SECAO_MAPAS = "/Script/EngineSettings.GameMapsSettings"
LOOP_ESPERADOS = {"LOOP_Manager", "LOOP_PortaSala", "LOOP_Chegada", "LOOP_CamSala", "LOOP_CamQuarto", "LOOP_PlayerStart"}

_linhas = []


def log(msg=""):
    _linhas.append(msg)
    unreal.log(msg)


def aviso(msg):
    _linhas.append(msg)
    unreal.log_warning(msg)


def ler(obj, *nomes):
    """Le a primeira propriedade que existir entre os nomes dados. Devolve (valor, nome) ou (None, None)."""
    for nome in nomes:
        try:
            return obj.get_editor_property(nome), nome
        except Exception:
            continue
    return None, None


def perto(valor, alvo, tol):
    try:
        return abs(float(valor) - float(alvo)) <= tol
    except Exception:
        return False


def rotulo(ator):
    try:
        return ator.get_actor_label()
    except Exception:
        return ator.get_name()


def tags_de(ator):
    valor, _ = ler(ator, "tags")
    return [str(t) for t in (valor or [])]


def projeto():
    return unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()).replace("\\", "/").rstrip("/")


def pacotes_sujos():
    """Pacotes sujos (mapa + conteudo), sem repetir."""
    U = unreal.EditorLoadingAndSavingUtils
    vistos, saida = set(), []
    for p in list(U.get_dirty_map_packages()) + list(U.get_dirty_content_packages()):
        n = p.get_name()
        if n not in vistos:
            vistos.add(n)
            saida.append(p)
    return saida


def dono_mapa(world, atores):
    """Devolve uma funcao nome_pacote -> True se o pacote for do mapa aberto
    (.umap, _BuiltData, subniveis carregados e atores/objetos externos do One File Per Actor)."""
    nomes, prefixos = set(), []
    try:
        niveis = list(unreal.EditorLevelUtils.get_levels(world))
    except Exception:
        niveis = []
    raizes = [n.get_outermost().get_name() for n in niveis] or [world.get_outermost().get_name()]
    for pk in raizes:
        nomes.add(pk)
        nomes.add(pk + "_BuiltData")
        partes = pk.split("/")  # ['', 'Game', 'Pasta', 'Mapa_B']
        if len(partes) >= 3:
            raiz, resto = "/" + partes[1], "/".join(partes[2:])
            prefixos += ["%s/__ExternalActors__/%s/" % (raiz, resto), "%s/__ExternalObjects__/%s/" % (raiz, resto)]
    for a in atores:
        try:
            nomes.add(a.get_package().get_name())
        except Exception:
            pass
    return lambda n: n in nomes or any(n.startswith(p) for p in prefixos)


def eh_blueprint(pacote):
    n = pacote.get_name()
    try:
        return isinstance(unreal.find_object(None, "%s.%s" % (n, n.rsplit("/", 1)[-1])), unreal.Blueprint)
    except Exception:
        return False


def salvar_log():
    try:
        pasta = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "Passo1")
        os.makedirs(pasta, exist_ok=True)
        caminho = os.path.join(pasta, "passo1_log.txt")
        with open(caminho, "w", encoding="utf-8") as f:
            f.write("\n".join(_linhas) + "\n")
        unreal.log("Log gravado em: " + caminho)
    except Exception as e:
        unreal.log_warning("Nao consegui gravar o log: %s" % e)


def main():
    log("=" * 70)
    log("LUX Passo 1 - modo: %s" % ("APLICAR" if MODO_APLICAR else "SO VERIFICAR (nao muda nada)"))
    log("=" * 70)

    # ------------------------------------------------------------------ 0. pre-condicoes
    try:
        if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():
            aviso("[PARE] O PIE esta rodando. Feche o PIE (Esc) e rode de novo.")
            return
    except Exception:
        pass

    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world is None:
        aviso("[PARE] Nenhum mundo de editor aberto (o PIE esta rodando?).")
        return
    caminho_mapa = world.get_path_name()  # /Game/Pasta/Mapa_B.Mapa_B
    log("Mapa aberto: " + caminho_mapa)
    if world.get_name() != NOME_MAPA:
        aviso("[PARE] O mapa aberto nao e o %s. Abra o %s (Content Browser, duplo clique) e rode de novo." % (NOME_MAPA, NOME_MAPA))
        return

    try:
        ar = unreal.AssetRegistryHelpers.get_asset_registry()
        mundos = ar.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "World"))
        iguais = sorted(str(d.package_name) for d in mundos if str(d.asset_name) == NOME_MAPA)
        if len(iguais) > 1:
            aviso("  [ATENCAO] Ha %d mapas chamados %s: %s. Confira se o aberto e o certo." % (len(iguais), NOME_MAPA, ", ".join(iguais)))
    except Exception:
        pass

    atores = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    log("Atores carregados no nivel: %d" % len(atores))

    try:
        res = unreal.WorldPartitionBlueprintLibrary.get_actor_descs()
        descs = next((r for r in res if not isinstance(r, bool)), []) if isinstance(res, tuple) else (res or [])
        if len(descs) > len(atores):
            aviso("  [ATENCAO] World Partition: o mapa tem %d atores e so %d estao carregados. "
                  "Carregue tudo (janela World Partition > selecionar tudo > Load Region) e rode de novo." % (len(descs), len(atores)))
    except Exception:
        pass

    eh_do_mapa = dono_mapa(world, atores)
    sujos_antes = pacotes_sujos()  # retrato ANTES de qualquer mudanca
    nomes_mapa_antes = sorted(p.get_name() for p in sujos_antes if eh_do_mapa(p.get_name()))

    # ------------------------------------------------------------------ 1. Auto Possess, GameMode, PlayerStart
    log("")
    log("--- 1. Jogador ---")
    alvo_desligar = []
    for a in atores:
        if not isinstance(a, unreal.Pawn):
            continue
        valor, _ = ler(a, "auto_possess_player")
        classe = a.get_class().get_name()
        if "ThirdPersonCharacter" in rotulo(a) or "ThirdPersonCharacter" in classe:
            log("  %s (classe %s): Auto Possess Player = %s" % (rotulo(a), classe, valor))
            if valor is not None and valor != unreal.AutoReceiveInput.DISABLED:
                alvo_desligar.append(a)
        elif valor is not None and valor != unreal.AutoReceiveInput.DISABLED:
            aviso("  [ATENCAO] %s (classe %s) tambem tem Auto Possess = %s. Nao mexi; ele tambem toma o jogador."
                  % (rotulo(a), classe, valor))
    if alvo_desligar:
        log("  [A FAZER] %d ator(es) com Auto Possess ligado. %s" % (
            len(alvo_desligar),
            "Serao desligados no bloco 4, junto com o save, se a atmosfera estiver OK." if MODO_APLICAR else "Rode com 'aplicar'."))
    else:
        log("  Nenhum ThirdPersonCharacter com Auto Possess ligado.")

    starts = [a for a in atores if isinstance(a, unreal.PlayerStart)]
    nomes_ps = [rotulo(a) for a in starts]
    log("  PlayerStart no mapa: %s" % (", ".join(nomes_ps) or "NENHUM"))
    if "LOOP_PlayerStart" not in nomes_ps:
        aviso("  [ATENCAO] LOOP_PlayerStart nao encontrado (a nota do loop diz que ele foi criado).")
    elif len(starts) > 1:
        aviso("  [ATENCAO] %d PlayerStarts: o jogador pode nascer fora do LOOP_PlayerStart." % len(starts))

    gm, _ = ler(world.get_world_settings(), "default_game_mode")
    if gm:
        log("  World Settings > GameMode Override: %s" % gm.get_name())
        try:
            pc = unreal.get_default_object(gm).get_editor_property("default_pawn_class")
            log("  Default Pawn do override: %s" % (pc.get_name() if pc else "nenhum"))
            if not pc or "BP_Player_Cowboy" not in pc.get_name():
                aviso("  [ATENCAO] O GameMode Override nao usa BP_Player_Cowboy. Limpe o override (World Settings > GameMode Override = None).")
        except Exception as e:
            aviso("  Nao consegui ler o Default Pawn do override: %s" % e)
    else:
        log("  World Settings > GameMode Override: nenhum (usa o do projeto, BP_PlayerMode)")

    # ------------------------------------------------------------------ 2. Atmosfera
    # Criterio: saiu dos valores ORIGINAIS da auditoria (a nota permite ajustar os alvos no apply_atmosphere.py).
    log("")
    log("--- 2. Atmosfera ---")
    checks = []  # (nome, ok, detalhe)

    ppv = [a for a in atores if isinstance(a, unreal.PostProcessVolume) and rotulo(a) == "PPV_Atmosfera"]
    ena = None
    if ppv:
        unb, _ = ler(ppv[0], "unbound")
        pri, _ = ler(ppv[0], "priority")
        ena, _ = ler(ppv[0], "enabled")
        checks.append(("PPV_Atmosfera existe, ligado e Unbound", bool(ena) and bool(unb),
                       "unbound=%s prioridade=%s enabled=%s" % (unb, pri, ena)))
    else:
        checks.append(("PPV_Atmosfera existe", False, "nao encontrado"))

    fogs = [a for a in atores if isinstance(a, unreal.ExponentialHeightFog)]
    vol = None
    if fogs:
        f = fogs[0]
        if len(fogs) > 1:
            aviso("  [ATENCAO] Ha %d ExponentialHeightFog; conferi so %s." % (len(fogs), rotulo(f)))
        comps = f.get_components_by_class(unreal.ExponentialHeightFogComponent)
        z = f.get_actor_location().z
        dens, _ = ler(comps[0], "fog_density") if comps else (None, None)
        vol, _ = ler(comps[0], "enable_volumetric_fog") if comps else (None, None)
        checks.append(("Nevoa: Z saiu de -6850 (alvo 0)", z > -1000.0, "Z=%.1f" % z))
        checks.append(("Nevoa: densidade acima de 0,0436 (alvo 0,15)", dens is not None and dens > 0.06, "densidade=%s" % dens))
        checks.append(("Nevoa: Volumetric Fog ligado", vol is True, "volumetric=%s" % vol))
    else:
        checks.append(("ExponentialHeightFog existe", False, "nao encontrado"))

    dls = [a for a in atores if isinstance(a, unreal.DirectionalLight)]
    if dls:
        dls.sort(key=lambda a: 0 if rotulo(a) == "DirectionalLight" else 1)
        d = dls[0]
        if len(dls) > 1:
            aviso("  [ATENCAO] Ha %d DirectionalLights; conferi so %s." % (len(dls), rotulo(d)))
        comps = d.get_components_by_class(unreal.DirectionalLightComponent)
        inten, _ = ler(comps[0], "intensity") if comps else (None, None)
        pitch = d.get_actor_rotation().pitch
        checks.append(("Lua: intensidade abaixo de 1 lux (era 10; alvo 0,06)", inten is not None and 0.0 < inten < 1.0, "intensidade=%s" % inten))
        checks.append(("Lua: acima do horizonte (pitch era +2,9; alvo -25)", pitch < -5.0, "pitch=%.1f" % pitch))
    else:
        checks.append(("DirectionalLight existe", False, "nao encontrada"))

    velas = [a for a in atores if "VelaComoda" in rotulo(a) and a.get_components_by_class(unreal.LocalLightComponent)]
    if velas:
        if len(velas) > 1:
            aviso("  [ATENCAO] %d luzes 'VelaComoda': %s; conferi a primeira." % (len(velas), ", ".join(rotulo(v) for v in velas)))
        raio, _ = ler(velas[0].get_components_by_class(unreal.LocalLightComponent)[0], "attenuation_radius")
        checks.append(("VelaComoda: raio abaixo de 10 m (era 52,7 m; alvo 3 m)", raio is not None and raio < 1000.0,
                       "raio=%s cm (%s)" % (raio, rotulo(velas[0]))))
    else:
        checks.append(("Luz VelaComoda existe", False, "nao encontrada"))

    atmosfera_ok = all(ok for _, ok, _ in checks)
    for nome, ok, det in checks:
        log("  [%s] %s  (%s)" % ("OK" if ok else "FALTA", nome, det))
    if ppv and fogs and ena is False and vol is False:
        aviso("  [INFO] Parece a condicao A (controle) ligada: PPV_Atmosfera e Volumetric Fog desligados. "
              "Religue os dois (ou rode apply_atmosphere.py) antes de salvar.")

    ppv_global = [a for a in atores if "LUX_PPV_GLOBAL" in tags_de(a)]
    log("  PPV_Global (tag LUX_PPV_GLOBAL, de 24/09): %s" % ("presente" if ppv_global else "NAO encontrado"))

    # ------------------------------------------------------------------ 3. Loop (so leitura)
    log("")
    log("--- 3. Loop (so leitura) ---")
    loop_atores = [a for a in atores if "LUX_LOOP" in tags_de(a)]
    log("  Atores com tag LUX_LOOP: %s" % (", ".join(sorted(rotulo(a) for a in loop_atores)) or "NENHUM"))
    faltam = LOOP_ESPERADOS - set(rotulo(a) for a in loop_atores)
    if faltam:
        aviso("  [ATENCAO] Atores LUX_LOOP da nota que nao estao no mapa: " + ", ".join(sorted(faltam)))
    v2_ok = False
    mgr = [a for a in atores if rotulo(a) == "LOOP_Manager"]
    if mgr:
        v2, nome = ler(mgr[0], "TempoAproximar")
        lf, _ = ler(mgr[0], "LoopFinal")
        log("  LoopFinal = %s" % lf)
        if nome:
            v2_ok = True
            log("  TempoAproximar = %s -> a v2 (troca fluida) esta no mapa." % v2)
        else:
            aviso('  [ATENCAO] LOOP_Manager sem TempoAproximar -> a v2 NAO foi aplicada. '
                  'Rode py "%s/Tools/Loop/setup_loop.py" rebuild, depois este script com aplicar.' % projeto())
    else:
        aviso("  [ATENCAO] LOOP_Manager nao encontrado no mapa.")

    # ------------------------------------------------------------------ 4. Pacotes sujos + aplicar
    log("")
    log("--- 4. Mudancas pendentes e save ---")
    loop_sujos = [p for p in sujos_antes if p.get_name() not in nomes_mapa_antes
                  and p.get_name().startswith(PASTA_LOOP) and eh_blueprint(p)]
    nomes_loop = sorted(p.get_name() for p in loop_sujos)
    outros = sorted(p.get_name() for p in sujos_antes if p.get_name() not in nomes_mapa_antes and p.get_name() not in nomes_loop)
    log("  Pacotes do %s com mudancas NAO salvas: %s" % (NOME_MAPA, ", ".join(nomes_mapa_antes) or "nenhum"))
    log("  Blueprints do loop nao salvos: %s" % (", ".join(nomes_loop) or "nenhum"))
    if outros:
        aviso("  [NAO VOU SALVAR] Outros assets nao salvos (decida voce): " + ", ".join(outros))

    if not atmosfera_ok:
        if nomes_mapa_antes:
            aviso("  Interpretacao: a atmosfera NAO esta no mapa. Ha mudancas pendentes no mapa, mas nao sao a atmosfera.")
        else:
            aviso("  Interpretacao: a atmosfera nao esta no mapa e nao ha nada pendente -> ela se perdeu antes do save (provavelmente num dos crashes).")
        aviso('  Rode py "%s/Tools/Lighting/apply_atmosphere.py" (idempotente, nao salva) e depois este script com aplicar.' % projeto())
    elif nomes_mapa_antes:
        log("  Interpretacao: a atmosfera esta no mapa, mas NAO esta salva. O modo aplicar salva.")
    else:
        log("  Interpretacao: a atmosfera esta no mapa e ja estava salva.")

    salvou = False
    if MODO_APLICAR:
        if not atmosfera_ok:
            aviso("  [NAO MUDEI NADA] Atmosfera incompleta (bloco 2): nao desliguei o Auto Possess e nao salvei.")
        else:
            if alvo_desligar:
                with unreal.ScopedEditorTransaction(TRANSACAO):
                    for a in alvo_desligar:
                        a.set_editor_property("auto_possess_player", unreal.AutoReceiveInput.DISABLED)
                        novo, _ = ler(a, "auto_possess_player")
                        log("  [FEITO] %s: Auto Possess Player -> %s" % (rotulo(a), novo))
            para_salvar = [p for p in pacotes_sujos() if eh_do_mapa(p.get_name())]
            ok_mapa = True
            if para_salvar:
                ok_mapa = unreal.EditorLoadingAndSavingUtils.save_packages(para_salvar, True)
                log("  Salvar %s (%d pacote(s)): %s" % (NOME_MAPA, len(para_salvar), "OK" if ok_mapa else "FALHOU"))
            else:
                log("  Nada do %s para salvar." % NOME_MAPA)
            ok_loop = True
            if loop_sujos:
                ok_loop = unreal.EditorLoadingAndSavingUtils.save_packages(loop_sujos, True)
                log("  Salvar Blueprints do loop: %s" % ("OK" if ok_loop else "FALHOU"))
            restantes = [p.get_name() for p in pacotes_sujos() if eh_do_mapa(p.get_name()) or p.get_name() in nomes_loop]
            if restantes:
                aviso("  [FALHOU?] Ainda nao salvos: " + ", ".join(restantes))
            else:
                log("  Conferido: nada do %s nem do loop ficou pendente." % NOME_MAPA)
            salvou = ok_mapa and ok_loop and not restantes

    # ------------------------------------------------------------------ 5. DefaultEngine.ini (so leitura)
    log("")
    log("--- 5. DefaultEngine.ini (so leitura) ---")
    log("  Valor certo para as duas chaves: " + caminho_mapa)
    try:
        ini = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_config_dir()), "DefaultEngine.ini")
        valores, secao = {}, None
        with open(ini, "r", encoding="utf-8", errors="replace") as f:
            for linha in f:
                s = linha.strip()
                if s.startswith("[") and s.endswith("]"):
                    secao = s[1:-1].strip()
                elif secao == SECAO_MAPAS and "=" in s and not s.startswith(";"):
                    k, v = s.split("=", 1)
                    valores[k.strip()] = v.strip().strip('"')  # a ultima ocorrencia vale
        aceitos = (caminho_mapa, caminho_mapa.split(".")[0])
        for chave in ("GameDefaultMap", "EditorStartupMap", "GlobalDefaultGameMode"):
            atual = valores.get(chave, "(ausente)")
            if chave == "GlobalDefaultGameMode":
                log("  [%s] %s=%s" % ("OK" if "BP_PlayerMode" in atual else "CONFERIR", chave, atual))
            else:
                log("  [%s] %s=%s" % ("OK" if atual in aceitos else "TROCAR", chave, atual))
    except Exception as e:
        aviso("  Nao consegui ler o DefaultEngine.ini: %s" % e)

    # ------------------------------------------------------------------ 6. Proximo comando
    log("")
    log("--- 6. Teste do loop ---")
    teste = projeto() + "/Tools/Loop/test_loop.py"
    if not os.path.isfile(teste):
        aviso("  [ATENCAO] test_loop.py nao encontrado em " + teste)
    elif not v2_ok:
        aviso("  Ainda nao rode o teste: aplique a v2 primeiro (bloco 3).")
    elif MODO_APLICAR and salvou:
        log('  Pronto para o teste. Rode: py "%s"' % teste)
    else:
        log('  Depois do modo aplicar dar certo, rode: py "%s"' % teste)
    log("=" * 70)


try:
    main()
except Exception:
    aviso("[ERRO] O script parou:\n" + traceback.format_exc())
    raise
finally:
    salvar_log()
