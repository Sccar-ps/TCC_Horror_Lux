# LUX - calibracao OFFLINE dos eventos de loop (sem editor, sem RAM): copia fiel de simular() de add_loop_events.py.
#   "C:/Program Files/Epic Games/UNREAL/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe" Tools/Loop/sim_eventos_offline.py
# Serve para escolher caixas, ordem e parametros ANTES de rodar add_loop_events.py instalar. Nao importa unreal. Nao toca o projeto.
# Regras do hub replicadas: pos_troca 3 s, gap 3 s, MaxBarulhos 3, reserva de susto (0,5 s), JanelaS, DistMaxJogador,
#   CosOlhar + AparicaoDistMin (aparicao), CosCostas (de costas).
# Diferencas para o simular() real (mantenha em sincronia se ele mudar):
#   - linha de visao sempre livre (corredor reto); o verificar no editor usa raios de verdade
#   - sem marcas/bloqueios (distorcao do loop 3/5 e batida do 4) e sem AlvoGirar/bExigirVistoAntes
#   - atraso: segundos parado na chegada (fade, porta abrindo, camera voltando) com o relogio do hub ja correndo
#   - rota extra "chave": corredor -> banquinho lateral (-2536, -664) -> porta (a chave do loop 1)
# Geometria real (sondar, 30/09/2026): Chegada (-3275, 955); BP_BaseDoor7 y 870; GatilhoFechar y 595..645; meia-largura 126.
# Conferido em 30/09: para o pacote do loop 1 este script e o verificar do editor deram os mesmos instantes (vulto 3-4 s, macaneta 6-7 s,
#   passos 10,25 s). Ordem macaneta -> vulto reprovou (5 de 30 cenarios); vulto -> macaneta passou (0 de 30).
# v2 (30/09): vulto no vao do escritorio e passos saindo do vao: 0 de 30 com CosCostas -0,2, 0 e 0,2 (passos a 2,2-3,4 m do som).
# v3 (30/09, polimento): passos comecam em L1_PASSOS[0] = (-3250, -740) (add_loop_events.py); o vulto continua em L1_VAO[0].
# v4 (05/10, plano do Vulto fluido, passo 5): o pacote das duas figuras (PadraoPiscar, caminho, ponto de som) vem de vulto_cronograma.py
#   (fim da copia digitada) e, depois do FIRED, o jogador continua em passos de 1/30 s ate o fim do evento: distancia horizontal minima
#   figura-jogador com P > 0,05 (reprova < 60 cm), tempo com P >= 0,5 e dentro do cone de visao, P(t) com a deriva da cadeia de timers
#   (k x dt) para 30/60/113 FPS. A parte de DISPARO (relatorio) segue identica ao baseline.
#   Decisao do orquestrador (05/10): a protecao de camera do BP_LuxVultoFluido (P x FClamp((Dist2D - 60) / 40), no Vector_Distance2D,
#   sondado no commandlet: resolve e compila limpo) ENTRA; o criterio de distancia minima (60 cm) vale COM ela. O resultado SEM ela
#   (cenario de 21 cm, jogador parado no fim da reta) sai como informativo.
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vulto_cronograma as vc

ALTURA_OLHO = 166.0
HUB = {"gap": 3.0, "post": 3.0, "maxb": 3, "maxs": 99}
MOTIVOS_RESERVA = ["gap", "vista", "costas", "nao_visto", "pos_troca", "externo", "distorcao", "aguarda_marca"]
MW = 126.0
PERFIS = (("andando", 170.0, False), ("olhando_em_volta", 170.0, True))  # cm/s; varre = camera oscila +-60 graus, periodo 4 s
ROTAS = {
    "meio": [(-3275, 955), (-3275, -500), (-2750, -800), (-2600, -1350), (-2450, -1500), (-2294, -1827)],
    "oeste": [(-3275, 955), (-3275, -500), (-2850, -560), (-2820, -1350), (-2700, -1800), (-2294, -1850)],
    "leste": [(-3275, 955), (-3275, -500), (-2900, -480), (-2200, -480), (-2150, -1600), (-2294, -1827)],
    "escritorio": [(-3275, 955), (-3275, -500), (-3250, -700), (-3500, -1100), (-3250, -700), (-3275, -500), (-2750, -800),
                   (-2600, -1350), (-2450, -1500), (-2294, -1827)],
    "chave": [(-3275, 955), (-3275, -500), (-2700, -600), (-2536, -664), (-2600, -1350), (-2450, -1500), (-2294, -1827)]}


class V:
    def __init__(s, x, y, z=0.0): s.x, s.y, s.z = x, y, z
    def __sub__(s, o): return V(s.x - o.x, s.y - o.y, s.z - o.z)
    def length(s): return math.sqrt(s.x ** 2 + s.y ** 2 + s.z ** 2)
    def normal(s):
        l = s.length() or 1.0
        return V(s.x / l, s.y / l, s.z / l)


def box(y_norte, y_sul, x=-3275.0, mw=MW):
    """caixa de corredor: y_norte > y_sul (o jogador anda para y decrescente)."""
    return V(x, (y_norte + y_sul) / 2), V(mw, (y_norte - y_sul) / 2)


def ev(label, cat, loops, caixa, som, **k):
    """mesmos nomes de add_loop_events.ev(); caixa = (centro V, meia-extensao V); som = PontoSom V."""
    c, x = caixa
    e = dict(label=label, Categoria=cat, Loops=loops, c=c, x=x, som=som, JanelaS=6.0, DistMaxJogador=0.0, bSoQuandoDeCostas=False,
             CosCostas=-0.2, bSoQuandoOlhando=False, CosOlhar=0.8, bAparicao=False, AparicaoDistMin=500.0, bExigirDentro=False, alvo_olhar=som)
    e.update(k)
    return e


def dentro(e, x, y): return abs(x - e["c"].x) <= e["x"].x and abs(y - e["c"].y) <= e["x"].y


def olhando(e, pos, ang):
    cam = V(pos[0], pos[1], ALTURA_OLHO)
    d = e["alvo_olhar"] - cam
    n = d.normal()
    if math.cos(ang) * n.x + math.sin(ang) * n.y < e["CosOlhar"]: return False
    if e["bAparicao"] and d.length() < e["AparicaoDistMin"]: return False
    return True  # linha de visao livre


def simular(evs, pts, v=170.0, varre=False, atraso=0.0, L=1, snaps=None):
    evs = sorted(evs, key=lambda e: e["Categoria"])  # barulhos antes dos sustos (pior caso para a reserva), como o real
    t, dt = 0.0, 0.25
    seg, pos = 0, list(pts[0])
    ang_passo = math.atan2(pts[1][1] - pos[1], pts[1][0] - pos[0])
    ultimo, cont, reserva_ate = -1000.0, {0: 0, 1: 0}, -1.0
    st = {e["label"]: {"tent": None, "feito": False} for e in evs}
    out = []
    while seg < len(pts) - 1 and t < 120:
        if t >= atraso:
            ax, ay = pts[seg + 1]
            dx, dy = ax - pos[0], ay - pos[1]
            dd = math.hypot(dx, dy)
            passo = v * dt
            if dd <= passo: pos, seg = [ax, ay], seg + 1
            else: pos = [pos[0] + dx / dd * passo, pos[1] + dy / dd * passo]
            ang_passo = math.atan2(dy, dx) if dd > 1e-6 else ang_passo
        ang = ang_passo + (math.radians(60.0) * math.sin(2 * math.pi * t / 4.0) if varre else 0.0)
        t += dt
        for e in evs:
            s = st[e["label"]]
            if s["feito"] or L not in e["Loops"]: continue
            den = dentro(e, pos[0], pos[1])
            if den and s["tent"] is None: s["tent"] = t
            if s["tent"] is None: continue
            d = math.hypot(pos[0] - e["som"].x, pos[1] - e["som"].y)
            m = None
            if e["DistMaxJogador"] > 0 and d > e["DistMaxJogador"]: m = "dist"
            elif t < HUB["post"]: m = "pos_troca"
            elif e["Categoria"] == 0 and t < reserva_ate: m = "reserva"
            elif t - ultimo < HUB["gap"]: m = "gap"
            elif cont[e["Categoria"]] >= (HUB["maxb"] if e["Categoria"] == 0 else HUB["maxs"]): m = "cota"
            elif e["bSoQuandoOlhando"] and not olhando(e, pos, ang): m = "vista"
            elif e["bSoQuandoDeCostas"]:
                fx, fy = math.cos(ang), math.sin(ang)
                nx, ny = e["som"].x - pos[0], e["som"].y - pos[1]
                if (fx * nx + fy * ny) / (math.hypot(nx, ny) or 1) > e["CosCostas"]: m = "costas"
            if m is None:
                a = e["alvo_olhar"]
                out.append((e["label"], "FIRED", round(t, 2), "y=%.0f d=%.0f" % (pos[1], math.hypot(pos[0] - a.x, pos[1] - a.y))))
                ultimo = t; cont[e["Categoria"]] += 1; s["feito"] = True
                if snaps is not None: snaps[e["label"]] = dict(t=t, seg=seg, pos=list(pos), ang_passo=ang_passo, ang=ang)
            else:
                s["ultimo_m"] = m
                if e["Categoria"] == 1 and m in MOTIVOS_RESERVA: reserva_ate = t + 0.5
                if m in ("pos_troca", "reserva"): s["tent"] = t
                if e["bExigirDentro"] and not den:
                    out.append((e["label"], "SKIP", round(t, 2), "fora:" + m)); s["feito"] = True; continue
                if t - s["tent"] > e["JanelaS"]:
                    out.append((e["label"], "SKIP", round(t, 2), m)); s["feito"] = True
    for e in evs:
        s = st[e["label"]]
        if L in e["Loops"] and not s["feito"]:
            out.append((e["label"], "PENDENTE_NA_PORTA" if s["tent"] is not None else "NAO_ALCANCADO", round(t, 2), s.get("ultimo_m", "")))
    return out


def relatorio(evs, atrasos=(0.0, 1.5, 2.5), quieto=False, L=1):
    """roda todas as rotas x perfis x atrasos; cenario com qualquer resultado diferente de FIRED conta como falha."""
    ruins = 0
    for atraso in atrasos:
        for nome, v, varre in PERFIS:
            for rota, pts in ROTAS.items():
                r = simular(evs, pts, v, varre, atraso, L)
                falha = [x for x in r if x[1] != "FIRED"]
                ruins += bool(falha)
                if not quieto or falha:
                    print("atraso %.1f | %-16s | %-10s | %s%s" % (atraso, nome, rota, "  ".join("%s@%.2f(%s)" % (a.replace("EV_L1_", ""), t, x)
                          for a, ac, t, x in sorted(r, key=lambda k: k[2]) if ac == "FIRED"), ("   << FALHA: %s" % falha) if falha else ""))
    print("cenarios com falha: %d de %d" % (ruins, len(atrasos) * len(PERFIS) * len(ROTAS)))
    return ruins


def sobrepoem(evs):
    """o verificar reprova caixas sobrepostas no mesmo loop."""
    for i, a in enumerate(evs):
        for b in evs[i + 1:]:
            if set(a["Loops"]) & set(b["Loops"]) and abs(a["c"].x - b["c"].x) < a["x"].x + b["x"].x and abs(a["c"].y - b["c"].y) < a["x"].y + b["x"].y:
                print("SOBREPOEM:", a["label"], b["label"])


def pacote_loop1():
    """mesmos valores de pacote_loop1() em add_loop_events.py (so os que influem no disparo); PadraoPiscar/caminho/PontoSom das figuras
    vem de vulto_cronograma.pacote_loop1_dados() (fonte unica)."""
    yl = 620.0 - 25.0 - 25.0     # gatilho: centro 620, meia-extensao 25 -> y_gat_min 595; caixa comeca 25 cm depois
    yv = yl - 270.0
    yb = yv - 10.0 - 690.0
    d = vc.pacote_loop1_dados()
    return [  # v2 (30/09): vulto no vao do escritorio (sem aparicao estatica); passos saindo do vao
        ev("EV_L1_VultoParado", 1, [1], box(yl, yv), V(*d["vulto"]["PontoSom"]), JanelaS=30.0, bSoQuandoOlhando=True, CosOlhar=0.90,
           bAparicao=False, PadraoPiscar=d["vulto"]["PadraoPiscar"], caminho=d["vulto"]["caminho"]),
        ev("EV_L1_Macaneta", 0, [1], box(yv - 10.0, yb), V(-3275.0, 910.0, 105.0), JanelaS=25.0, DistMaxJogador=1300.0,
           bSoQuandoDeCostas=True, CosCostas=0.0),
        ev("EV_L1_PassosPesados", 1, [1], (V(-3000.0, -550.0), V(60.0, 210.0)), V(*d["passos"]["PontoSom"]), JanelaS=25.0,
           DistMaxJogador=1100.0, bSoQuandoDeCostas=True, CosCostas=-0.2, PadraoPiscar=d["passos"]["PadraoPiscar"],
           caminho=d["passos"]["caminho"])]


# ------------------------------------------------------------------ v4: o que acontece DEPOIS do FIRED
DT_POS = 1.0 / 30.0             # passo do jogador/figura depois do FIRED (plano)
DT_FINO = 1.0 / 120.0           # conferencia do minimo (jogador 170 cm/s + figura 83 cm/s = ate 8 cm por passo de 1/30 s)
DIST_MIN = 60.0                 # cm: reprova o cenario se a figura (P > 0,05) chegar mais perto que isso
P_VISIVEL, P_PLENA = 0.05, 0.5
COS_CONE = math.cos(math.radians(45.0))   # cone de visao: +-45 graus (FOV horizontal 90, HIPOTESE)
FIGURAS = (("EV_L1_VultoParado", "vulto"), ("EV_L1_PassosPesados", "passos"))
_RUNS = {}


def _runs(evento, fps_list=(30, 60, 113), aleatorias=4):
    """execucoes da luz/presenca por FPS: deriva zero, deriva maxima (todo elo atrasa dt) e algumas aleatorias."""
    if evento not in _RUNS:
        r = []
        for fps in fps_list:
            r.append((fps, "zero", vc.executa(evento, fps, 0, deriva="zero")))
            r.append((fps, "max", vc.executa(evento, fps, 0, deriva="max")))
            for sd in range(1, aleatorias + 1):
                r.append((fps, "s%d" % sd, vc.executa(evento, fps, sd)))
        _RUNS[evento] = r
    return _RUNS[evento]


def continua(pts, v, varre, atraso, snap, dur, dt):
    """jogador depois do FIRED, com a MESMA regra de simular() (passo v x dt, corta no ponto, camera varrendo), em passos dt:
    [(tau, (x, y), ang)] com tau = 0 no instante do FIRED (= DisparoT)."""
    t, seg, pos, ang_passo = snap["t"], snap["seg"], list(snap["pos"]), snap["ang_passo"]
    out = [(0.0, (pos[0], pos[1]), snap["ang"])]
    for i in range(1, int(round(dur / dt)) + 1):
        if seg < len(pts) - 1 and t >= atraso:
            ax, ay = pts[seg + 1]
            dx, dy = ax - pos[0], ay - pos[1]
            dd = math.hypot(dx, dy)
            passo = v * dt
            if dd <= passo: pos, seg = [ax, ay], seg + 1
            else: pos = [pos[0] + dx / dd * passo, pos[1] + dy / dd * passo]
            ang_passo = math.atan2(dy, dx) if dd > 1e-6 else ang_passo
        ang = ang_passo + (math.radians(60.0) * math.sin(2 * math.pi * t / 4.0) if varre else 0.0)
        t += dt
        out.append((i * dt, (pos[0], pos[1]), ang))
    return out


def metricas_figura(evento, snap, pts, v, varre, atraso, caminho=None, dt=DT_POS, prot=None):
    """pior caso sobre fps (30/60/113) x deriva da cadeia (zero, maxima, aleatorias): distancia horizontal minima figura-jogador com
    P > 0,05, tempo com P >= 0,5 e tempo com P >= 0,5 dentro do cone de visao. v = 0 e o jogador PARADO no DisparoT (pior caso de
    proximidade). prot = (d0, d1) simula a protecao de camera: P x FClamp((dist - d0) / (d1 - d0)) (Vector_Distance2D no BP)."""
    dur = vc.EVENTOS[evento]["duracao"]
    traj = continua(pts, v, varre, atraso, snap, dur, dt)
    fpos = [vc.pos(tau, evento, caminho) for tau, _, _ in traj]
    r = dict(dmin=1e9, tau=None, pj=None, pf=None, rodada=None, t05_min=1e9, t05_max=0.0, cone_min=1e9)
    for fps, rot, run in _runs(evento):
        t05 = tc = 0.0
        for (tau, pj, ang), pf in zip(traj, fpos):
            p = run.P(tau)
            d = math.hypot(pf[0] - pj[0], pf[1] - pj[1])
            if prot: p *= min(1.0, max(0.0, (d - prot[0]) / (prot[1] - prot[0])))
            if p > P_VISIVEL:
                if d < r["dmin"]: r.update(dmin=d, tau=tau, pj=pj, pf=pf, rodada="%d FPS %s" % (fps, rot))
            if p >= P_PLENA:
                t05 += dt
                bx, by = pf[0] - pj[0], pf[1] - pj[1]
                if (math.cos(ang) * bx + math.sin(ang) * by) / (math.hypot(bx, by) or 1.0) >= COS_CONE: tc += dt
        r["t05_min"], r["t05_max"], r["cone_min"] = min(r["t05_min"], t05), max(r["t05_max"], t05), min(r["cone_min"], tc)
    return r


def relatorio_figuras(evs, atrasos=(0.0, 1.5, 2.5), caminho_passos=None, quieto=False, rotulo="", prot=None):
    """depois do FIRED: roda os 30 cenarios com DOIS modelos de jogador (segue a rota; para no DisparoT = pior caso de proximidade)
    e reprova os cenarios cuja distancia minima (dos dois, passo fino de 1/120 s) for < DIST_MIN.
    Devolve (n_falhas, lista de resultados)."""
    falhas, res = 0, []
    for atraso in atrasos:
        for nome, v, varre in PERFIS:
            for rota, pts in ROTAS.items():
                snaps = {}
                simular(evs, pts, v, varre, atraso, 1, snaps=snaps)
                linha, ruim, item = [], False, dict(cenario="%.1f|%s|%s" % (atraso, nome, rota), figs={})
                for label, evento in FIGURAS:
                    if label not in snaps:
                        continue
                    cam = caminho_passos if evento == "passos" else None
                    m = {}
                    for modelo, vv in (("segue", v), ("para", 0.0)):
                        g = metricas_figura(evento, snaps[label], pts, vv, varre, atraso, cam, prot=prot)
                        f = metricas_figura(evento, snaps[label], pts, vv, varre, atraso, cam, DT_FINO, prot=prot)
                        g["dmin_fino"] = min(g["dmin"], f["dmin"])
                        m[modelo] = g
                    item["figs"][evento] = m
                    dmin = min(m["segue"]["dmin_fino"], m["para"]["dmin_fino"])
                    ok = dmin >= DIST_MIN
                    ruim = ruim or not ok
                    linha.append("%s dmin segue=%4.0f para=%4.0f cm%s P>=0,5 %.2f-%.2fs cone>=%.2fs" % (
                        evento, m["segue"]["dmin_fino"], m["para"]["dmin_fino"], "" if ok else " <<REPROVA", m["segue"]["t05_min"],
                        m["segue"]["t05_max"], min(m["segue"]["cone_min"], m["para"]["cone_min"])))
                falhas += ruim
                item["ruim"] = ruim
                res.append(item)
                if not quieto or ruim:
                    print("atraso %.1f | %-16s | %-10s | %s" % (atraso, nome, rota, "  ||  ".join(linha)))
    print("%scenarios com distancia minima < %.0f cm (P > %.2f; jogador que segue a rota ou que para): %d de %d" % (
        rotulo, DIST_MIN, P_VISIVEL, falhas, len(res)))
    return falhas, res


def folga_parede(caminho, x_ref=-3125.0, y_parede=-775.0, raio=28.0):
    """folga (cm) da capsula (raio) a face sul da CutPart14 (y_parede) no ponto x_ref do caminho. HIPOTESE: so o editor confirma."""
    d = 0.0
    for a, b in zip(caminho, caminho[1:]):
        if min(a[0], b[0]) <= x_ref <= max(a[0], b[0]):
            f = (x_ref - a[0]) / (b[0] - a[0])
            return a[1] + (b[1] - a[1]) * f - raio - y_parede
    return None


def alternativas_fim(evs):
    """compara o FIM do plano com ajustes minimos; so informa (nao muda a constante FIM de vulto_cronograma.py)."""
    cands = [("A  plano: FIM (-2800,-725), reta unica", vc.caminho_passos(), None),
             ("B  FIM y=-745, reta unica", vc.caminho_passos(fim=(-2800.0, -745.0)), None),
             ("C  y=-745 so no trecho final: dobra (-3000,-731) -> (-2800,-745)", vc.caminho_passos(fim=(-2800.0, -745.0), dobra=(-3000.0, -731.0)), None),
             ("D  plano + protecao de camera P x clamp((dist-60)/40)", vc.caminho_passos(), (vc.DIST_MIN_CAM, vc.DIST_PLENA_CAM))]
    print("ALTERNATIVAS DO FIM (informativo; o editor confirma a folga fisica):")
    for nome, cam, prot in cands:
        n, res = relatorio_figuras(evs, caminho_passos=cam, quieto=True, prot=prot, rotulo="    ")
        pior = min(((min(r["figs"]["passos"]["segue"]["dmin_fino"], r["figs"]["passos"]["para"]["dmin_fino"]), r["cenario"]) for r in res))
        t05 = min(r["figs"]["passos"]["segue"]["t05_min"] for r in res)
        fp = folga_parede(cam)
        print("  %-66s pior dmin=%5.1f cm (%s) | falhas %d/30 | t(P>=0,5) minimo %.2f s | folga a CutPart14 em x=-3125: %.1f cm | ultimo ponto %s" % (
            nome, pior[0], pior[1], n, t05, fp, cam[-1]))


def relatorio_P():
    """P(t) com a deriva da cadeia de timers (k x dt): janelas com P >= 0,5 (deriva zero e maxima) e x da figura dos Passos."""
    print("P(t) nominal por FPS (janelas com P >= %.1f; deriva zero | deriva maxima k x dt):" % P_PLENA)
    for evento in ("vulto", "passos"):
        for fps in (30, 60, 113):
            for rot in ("zero", "max"):
                run = vc.executa(evento, fps, 0, deriva=rot)
                jan, t0 = [], None
                for s_, p in zip(run.S, run.PV):
                    if p >= P_PLENA and t0 is None: t0 = s_
                    if p < P_PLENA and t0 is not None: jan.append((t0, s_)); t0 = None
                x = "" if evento == "vulto" else "  x=%s" % ["%.0f..%.0f" % (vc.pos(a)[0], vc.pos(b)[0]) for a, b in jan]
                print("  %-6s %3d FPS %-4s: %s total %.2f s%s" % (evento, fps, rot, ["%.2f-%.2f" % ab for ab in jan], sum(b - a for a, b in jan), x))


if __name__ == "__main__":
    pk = pacote_loop1()
    sobrepoem(pk)
    ruins = relatorio(pk)
    print("--- v4: depois do FIRED (passos de 1/30 s; figuras do vulto_cronograma.py; deriva k x dt a 30/60/113 FPS)")
    relatorio_P()
    prot = (vc.DIST_MIN_CAM, vc.DIST_PLENA_CAM)
    falhas_dist, _ = relatorio_figuras(pk, prot=prot, rotulo="COM a protecao de camera do BP (%.0f-%.0f cm): " % prot)
    relatorio_figuras(pk, quieto=True, rotulo="SEM a protecao (informativo; o jogador parado no fim da reta): ")
    alternativas_fim(pk)
    sys.exit(1 if (ruins or falhas_dist) else 0)
