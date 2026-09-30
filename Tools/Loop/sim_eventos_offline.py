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
import math

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


def simular(evs, pts, v=170.0, varre=False, atraso=0.0, L=1):
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
    """mesmos valores de pacote_loop1() em add_loop_events.py (so os que influem no disparo)."""
    yl = 620.0 - 25.0 - 25.0     # gatilho: centro 620, meia-extensao 25 -> y_gat_min 595; caixa comeca 25 cm depois
    yv = yl - 270.0
    yb = yv - 10.0 - 690.0
    return [  # v2 (30/09): vulto no vao do escritorio (sem aparicao estatica); passos saindo do vao
        ev("EV_L1_VultoParado", 1, [1], box(yl, yv), V(-3250.0, -700.0, 120.0), JanelaS=30.0, bSoQuandoOlhando=True, CosOlhar=0.90,
           bAparicao=False),
        ev("EV_L1_Macaneta", 0, [1], box(yv - 10.0, yb), V(-3275.0, 910.0, 105.0), JanelaS=25.0, DistMaxJogador=1300.0,
           bSoQuandoDeCostas=True, CosCostas=0.0),
        ev("EV_L1_PassosPesados", 1, [1], (V(-3000.0, -550.0), V(60.0, 210.0)), V(-3250.0, -720.0, 60.0), JanelaS=25.0,
           DistMaxJogador=1100.0, bSoQuandoDeCostas=True, CosCostas=-0.2)]


if __name__ == "__main__":
    pk = pacote_loop1()
    sobrepoem(pk)
    relatorio(pk)
