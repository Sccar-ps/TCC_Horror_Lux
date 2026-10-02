# LUX: compara dois resultados de pie_bs_stand_valida.py (antes x depois de mexer no BlendSpace). Python comum, fora do editor, nao grava nada:
#   python -B Tools/MixamoFP/anim_compara.py <rotulo_antes> <rotulo_depois>      (pastas de Saved/LuxSnapshots/anim_pie/)
import json, os, sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "Saved", "LuxSnapshots", "anim_pie")
CHAVES = ("speed_medio", "dir_medio", "foot_l_frente_alcance", "foot_r_frente_alcance", "foot_l_lado_alcance", "foot_r_lado_alcance", "foot_l_altura_alcance", "foot_r_altura_alcance",
          "passos_por_s_frente", "passos_por_s_lado")


def carrega(rotulo):
    return json.load(open(os.path.join(BASE, rotulo, "anim_result.json"), encoding="utf-8"))["fases"]


def main():
    antes, depois = carrega(sys.argv[1]), carrega(sys.argv[2])
    print("%-10s %-24s %10s %10s %9s" % ("fase", "medida", "antes", "depois", "delta"))
    maior = {}
    for fase in antes:
        if fase not in depois:
            continue
        for k in CHAVES:
            a, d = antes[fase].get(k), depois[fase].get(k)
            if a is None or d is None:
                continue
            delta = d - a
            rel = abs(delta) / max(abs(a), 1.0)
            if k != "dir_medio":
                maior[fase] = max(maior.get(fase, 0.0), rel)
            print("%-10s %-24s %10.2f %10.2f %+8.2f%s" % (fase, k, a, d, delta, "  <-" if rel > 0.05 and abs(delta) > 1.0 else ""))
    print("\nmaior diferenca relativa por fase (sem a direcao):")
    for fase, rel in maior.items():
        print("  %-10s %5.1f %%" % (fase, 100.0 * rel))


if __name__ == "__main__":
    main()
