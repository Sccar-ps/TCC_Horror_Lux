# LUX - cliente curto de Python Remote Execution (plugin PythonScriptPlugin, bRemoteExecution=True no DefaultEngine.ini) para o editor grafico ABERTO.
# Rode com o Python da engine (nao ha python no PATH): <UE_5.8>/Engine/Binaries/ThirdParty/Python3/Win64/python.exe -B ue_cli.py ...
# Recusa rodar com mais de um editor aberto (a execucao remota liga no 1o que responde: Skill_Scripts_Blueprint_Seguros). UE_RX = pasta do remote_execution.py.
#   python -B ue_cli.py nodes
#   python -B ue_cli.py file  "<caminho.py>" [args...]     (ExecuteFile: como o `py` do console)
#   python -B ue_cli.py code  "<codigo python, varias linhas ok>"   (ExecuteFile com o texto literal)
#   python -B ue_cli.py eval  "<expressao>"                 (EvaluateStatement)
# Variaveis: UE_ESPERA (s para descobrir o editor, padrao 30), UE_OUT (arquivo JSON com a resposta inteira).
import json
import os
import sys
import time

RX = os.environ.get("UE_RX", "C:/Program Files/Epic Games/UNREAL/UE_5.8/Engine/Plugins/Experimental/PythonScriptPlugin/Content/Python")
sys.path.insert(0, RX)
sys.dont_write_bytecode = True
import remote_execution as rx


def main():
    modo = sys.argv[1] if len(sys.argv) > 1 else "nodes"
    espera = float(os.environ.get("UE_ESPERA", "30"))
    ex = rx.RemoteExecution()
    ex.start()
    t0, nodes = time.time(), []
    while time.time() - t0 < espera:
        nodes = ex.remote_nodes
        if nodes:
            break
        time.sleep(0.5)
    time.sleep(1.5)
    nodes = ex.remote_nodes
    if modo == "nodes":
        print(json.dumps(nodes, indent=1, default=str))
        ex.stop()
        return 0 if nodes else 2
    if not nodes:
        print("NENHUM EDITOR RESPONDEU em %.0f s" % espera)
        ex.stop()
        return 2
    if len(nodes) > 1:
        print("VARIOS EDITORES (%d): recuse; feche os outros" % len(nodes))
        print(json.dumps(nodes, indent=1, default=str))
        ex.stop()
        return 3
    ex.open_command_connection(nodes[0]["node_id"])
    try:
        if modo == "file":
            cmd = '"%s"' % sys.argv[2].replace("\\", "/") + ("" if len(sys.argv) < 4 else " " + " ".join(sys.argv[3:]))
            r = ex.run_command(cmd, unattended=True, exec_mode=rx.MODE_EXEC_FILE)
        elif modo == "code":
            r = ex.run_command(sys.argv[2], unattended=True, exec_mode=rx.MODE_EXEC_FILE)
        elif modo == "eval":
            r = ex.run_command(sys.argv[2], unattended=True, exec_mode=rx.MODE_EVAL_STATEMENT)
        else:
            print("modo desconhecido:", modo)
            return 4
    finally:
        ex.stop()
    saida = os.environ.get("UE_OUT")
    if saida:
        with open(saida, "w", encoding="utf-8") as fh:
            json.dump(r, fh, indent=1, default=str, ensure_ascii=False)
    print("success:", r.get("success"))
    print("result:", str(r.get("result"))[:4000])
    for o in r.get("output", []):
        print("[%s] %s" % (o.get("type"), str(o.get("output")).rstrip()[:1500]))
    return 0 if r.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
