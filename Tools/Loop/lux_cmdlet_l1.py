# LUX - driver do COMMANDLET do Loop 1 v4 (BP_LuxVultoFluido): gera, verifica e salva os 4 assets novos SEM o editor grafico.
#   UnrealEditor-Cmd.exe <TCCHorrorLux.uproject> -run=pythonscript "-script=<este arquivo> <modo>" -unattended -nosplash -nullrhi -nop4
#   modos:
#     assets            cria o que falta de BP_LuxVultoFluido, M_LuxVultoSombra_P, M_LuxVultoAura_L1 e MI_LuxVultoSombra_L1P, roda o
#                       verificar_assets e salva SO esses 4 (nunca "todos os sujos": o commandlet deixa um pacote alheio sujo)
#     verificar_assets  so leitura (rode num processo NOVO depois do 'assets': prova o que foi para o disco)
#     ensaio            tudo em memoria com outros nomes (BP em /Temp/LuxProbe, materiais ZZ_*), nada e salvo: prova o gerador antes do 'assets'
# Por que commandlet: criar nos de BP no editor grafico, depois de um compile com o mesmo operador, derruba o editor (P21); aqui, se cair,
# so o processo cai e nada foi salvo. Pre-condicoes: nenhum UnrealEditor vivo, >= 2,5 GB de RAM livre, uma execucao por vez, barras
# NORMAIS no -script (barra invertida seguida de digitos vira escape octal). O caminho do projeto tem ESPACO e o -script nao aceita aspas
# aninhadas: lance por um arquivo curto SEM espaco que faca os.environ["LUX_CMDLET"] = "1" e runpy.run_path(<este arquivo>, run_name="__main__")
# com sys.argv = [<este arquivo>, <modo>] (Skill_Scripts_Blueprint_Seguros, "Dois processos, commandlet..."). Depois: etapa 'mapa' no editor
# grafico (add_vulto_corre.py instalar_l1 mapa). O log proprio (flush + fsync por etapa; a ultima linha aponta a etapa de uma queda):
# Saved/LuxSnapshots/vulto_fluido_log.txt. O exit code 1 do commandlet vem do redirecionador circular conhecido (P04), nao do script.
import os
import sys
import time
import traceback

sys.dont_write_bytecode = True        # nao regravar os .pyc versionados de Tools/Loop/__pycache__
os.environ["LUX_CMDLET"] = "1"        # sem editor grafico: o LevelEditorSubsystem derruba o commandlet
import unreal

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
LOG = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "LuxSnapshots", "vulto_fluido_log.txt")
T0 = time.time()


def L(*a):
    """linha no log proprio, com flush + fsync ANTES da etapa seguinte"""
    linha = "%7.2f %s" % (time.time() - T0, " ".join(str(x) for x in a))
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(linha + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    unreal.log("[LUX fluido] " + linha)


def main():
    modo = sys.argv[1] if len(sys.argv) > 1 else "verificar_assets"
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    open(LOG, "w", encoding="utf-8").close()
    L("modo", modo, "| python", sys.version.split()[0], "| LUX_CMDLET", os.environ.get("LUX_CMDLET"))
    try:
        import add_vulto_corre as avc      # importa add_loop_events e vulto_cronograma
        avc.w = L                          # as mensagens do add_vulto_corre tambem vao para o log com fsync
        L("add_vulto_corre importado")
        if modo == "assets":
            avc.instalar_l1_assets()
        elif modo == "verificar_assets":
            falhas = avc.verificar_assets()
            L("RESULTADO verificar_assets:", ("FAIL %s" % falhas) if falhas else "PASS")
        elif modo == "ensaio":
            falhas = avc.ensaio_l1_assets()
            L("RESULTADO ensaio:", ("FAIL %s" % falhas) if falhas else "PASS")
        else:
            L("modo desconhecido (assets | verificar_assets | ensaio)")
    except Exception as ex:
        if type(ex).__name__ == "Aborta":
            L("ABORTADO:", ex)
        else:
            L("ERRO " + traceback.format_exc())
    L("FIM", modo)


if __name__ == "__main__":
    main()
