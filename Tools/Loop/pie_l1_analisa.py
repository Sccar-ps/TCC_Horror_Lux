# LUX - analisa o JSON de pie_l1.py contra o modelo de vulto_cronograma.py: `python -B pie_l1_analisa.py <Saved/LuxSnapshots/l1_fluido/pie_l1_<evento>_<cenario>.json>`
import json, sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
import vulto_cronograma as vc
arq = sys.argv[1]
chave = "passos" if "Passos" in arq else "vulto"
luz_chave = "LUX_L1_LuzPassos" if chave == "passos" else "LUX_L1_LuzFundo"
d = json.load(open(arq, encoding="utf-8"))
fr = d["frames"]
dT = next((f["dT"] for f in fr if f["dT"] != d["disparo0"]), None)
F = [f for f in fr if f["dT"] == dT]            # quadros depois do disparo
for f in F:
    f["t"] = f["tg"] - dT
dts = [f["dt"] for f in F if f["dt"] > 0]
print("== %s | cenario %s | quadros apos o disparo: %d | FPS medio %.1f (pior quadro %.1f ms) | jogador %s" % (chave, d["cenario"], len(F), len(dts)/sum(dts), 1000*max(dts), [round(x) for x in d["jogador"]]))
# luz real: instantes das mudancas
lt = []
ant = None
for f in F:
    v = f["luz"][luz_chave]
    q = "escuro" if v < 0.2 else "aceso"
    if q != ant:
        lt.append((round(f["t"], 3), q, round(v, 3)))
        ant = q
print("luz real (%s): %s" % (luz_chave, lt))
print("luz nominal   :", vc.luz_nominal(0.0, chave), [(round(t, 3), f) for t, f in vc._eventos_luz(vc._ev(chave))])
# P
P = [f["P"] for f in F]
dP = [abs(P[i] - P[i-1]) for i in range(1, len(P))]
print("max |dP| por quadro: %.3f | P maximo: %.3f" % (max(dP) if dP else 0, max(P)))
# janelas com P>=0.5
jan, ini = [], None
for f in F:
    if f["P"] >= 0.5 and ini is None:
        ini = f["t"]
    if f["P"] < 0.5 and ini is not None:
        jan.append((round(ini, 3), round(f["t"], 3), round(f["t"] - ini, 3)))
        ini = None
print("janelas com P>=0,5 (ini, fim, duracao):", jan, "| total %.2f s" % sum(j[2] for j in jan))
# P>0 so com luz acesa?
viol = [(round(f["t"], 3), round(f["P"], 3), round(f["luz"][luz_chave], 3)) for f in F if f["P"] > 0.01 and f["luz"][luz_chave] < 0.2]
print("quadros com P>0,01 e luz < 0,2 (deve ser 0):", len(viol), viol[:5])
# atraso do inicio de P em relacao a subida real da luz e P=0 antes da queda
subidas = [t for t, q, v in lt if q == "aceso"]
quedas = [t for t, q, v in lt if q == "escuro"][1:]
for k, ts in enumerate(subidas[:len(vc.janelas(vc.EVENTOS[chave]["padrao"], vc.EVENTOS[chave]["apagar_no_fim"], vc.EVENTOS[chave]["restaurar"])[2])]):
    p0 = next((f["t"] for f in F if f["t"] >= ts and f["P"] > 0.01), None)
    p1 = next((f["t"] for f in F if f["t"] >= ts and f["P"] >= 0.99), None)
    queda = next((q for q in quedas if q > ts), None)
    pz = next((f["t"] for f in F if queda and f["t"] >= ts and f["P"] <= 0.001 and f["t"] > (p1 or ts)), None)
    print("  janela %d: luz sobe %.3f | P>0 em %s (atraso %s ms) | P=1 em %s | queda da luz %s | P voltou a 0 em %s (%s ms antes da queda)" % (
        k+1, ts, p0 and round(p0, 3), p0 and round((p0-ts)*1000), p1 and round(p1, 3), queda, pz and round(pz, 3), queda and pz and round((queda-pz)*1000)))
# toggles de oculto
prev = None
for f in F:
    if prev is not None and f["oculto"] != prev:
        print("  oculto %s -> %s em t=%.3f com P=%.3f (ativo=%s)" % (prev, f["oculto"], f["t"], f["P"], f["ativo"]))
    prev = f["oculto"]
# posicao x modelo
erro = max(abs(f["x"] - vc.pos(f["t"], chave)[0]) for f in F if f["ativo"])
erroy = max(abs(f["y"] - vc.pos(f["t"], chave)[1]) for f in F if f["ativo"])
passo = [abs(F[i]["x"] - F[i-1]["x"]) + abs(F[i]["y"] - F[i-1]["y"]) for i in range(1, len(F)) if F[i]["ativo"] and F[i-1]["ativo"]]
print("posicao: erro max vs modelo |dx|=%.2f cm |dy|=%.2f cm | passo max por quadro %.2f cm (V*dt = %.2f)" % (erro, erroy, max(passo), 83.0 * max(dts)))
print("NSub final:", F[-1]["NSub"], "| ativo no fim:", F[-1]["ativo"], "| oculto no fim:", F[-1]["oculto"], "| dcam min/max: %.0f / %.0f" % (min(f["dcam"] for f in F), max(f["dcam"] for f in F)))
# primeiro quadro ativo
a0 = next((f for f in F if f["ativo"]), None)
print("1o quadro ativo em t=%.3f (P=%.3f oculto=%s)" % (a0["t"], a0["P"], a0["oculto"]))
