# LUX - cronograma PURO (sem `import unreal`) do Vulto fluido do Loop 1 (BP_LuxVultoFluido, plano de 05/10/2026, passo 4).
#   "C:/Program Files/Epic Games/UNREAL/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe" -B Tools/Loop/vulto_cronograma.py
# Fonte unica dos numeros do desenho: a luz continua em DEGRAU (cadeia de timers do BP_LuxLoopEvent, nao editado) e a figura
# tem uma PRESENCA P (0 a 1, Custom Primitive Data 0 multiplicando a Opacity) derivada da intensidade REAL da luz-fundo:
#   ao ver a luz subir (f > 0,5 vindo de baixo) grava TSub e NSub++; Dur = JanAcesa[NSub-1];
#   P = FMin(FClamp((Now-TSub)/EntradaS), FClamp((TSub+Dur-MargemS-Now)/SaidaS)) x L,  L = FClamp((f-0,2)/0,6),
#   e P = 0 se NSub > Length(JanAcesa) ou |(TSub-T0) - TSubNom[NSub-1]| > TolS;
#   depois P x FClamp((Dist2D(figura, camera) - DIST_MIN_CAM) / (DIST_PLENA_CAM - DIST_MIN_CAM)) (protecao de camera; fora de executa(),
#   que nao conhece a camera: o simulador a aplica com prot=).
# Usado por: sim_eventos_offline.py (pacote do disparo + metricas depois do FIRED), add_vulto_corre.py (dados de instancia e regras do
# verificar_l1) e add_loop_events.py (regras de som do verificar). Nao importa unreal; nao toca o projeto. Rode com -B (nao regravar .pyc
# versionado).
# Modelo de tempo (HIPOTESE de engine, TimerManager.cpp:1212 / 714): cada elo da cadeia de timers relativos da luz atrasa U(0, dt);
#   o timer de 0,02 s da figura (loop) dispara no primeiro quadro >= seu vencimento; a figura segura o ultimo P ate a proxima amostra.
import bisect
import math
import os
import random

# ---------------------------------------------------------------- constantes (plano_final.txt, passo 4; brief de 05/10, secao 1)
PASSO_CM = 54.0          # deslocamento do som por passo (DeslocPorRep dos Passos): 0,65 s x 83 cm/s = 53,95
V = 83.0                 # cm/s do ator dos Passos (reta D)
V_NAT = 116.5            # cm/s da animacao A_LuxVultoAndar a taxa 1,0, x escala Y 0,95 da Figura (MEDIDO no commandlet, 05/10: regressao
                         # da raiz nos 28 quadros = 122,6 cm/s na malha 1:1; a estimativa antiga era 115,6)
TAXA = 0.718             # play rate da animacao (TAXA x V_NAT = 83,6; desvio de 0,8 % para V, dentro dos 3 % do C5)
CICLO_S = 0.9333         # ciclo do anim_Walk_Fwd_Loop_L a taxa 1,0 (MEDIDO no commandlet, 05/10)
FASE0 = 0.333            # fase (s) do contato do pe no inicio dos Passos (MEDIDO: contato D em 0,333 s com 56,7 cm)
# 0,17 s e nao 0,12/0,15: o timer de 0,02 s e quantizado por quadro e a figura segura o ultimo P ate a proxima amostra; com 0,12/0,15 o
# degrau de P entre amostras chegava a 0,278; com 0,17 fica <= 0,196 (30/60 FPS) e P >= 0,5 dura 0,58 s por janela
ENTRADA_S = 0.17
SAIDA_S = 0.17
MARGEM_S = 0.05
TOL_S = 0.35
F_ESCURO = 0.04          # IntensidadeApagada dos dois eventos
TIMER_S = 0.02           # periodo do timer em loop do BP_LuxVultoFluido (precedente BP_LuxVultoCorre); um so timer, sem Tick
DIST_MIN_CAM = 60.0      # protecao de camera: P x FClamp((Dist2D(figura, camera) - DIST_MIN_CAM) / (DIST_PLENA_CAM - DIST_MIN_CAM))
DIST_PLENA_CAM = 100.0   # (alternativa D do simulador: leva o pior cenario de 21 cm a 62,4 cm)
P0 = (-3250.0, -740.0)   # inicio da reta D (PontoSom dos Passos)
FIM = (-2800.0, -725.0)  # fim da reta D (constante do plano; NAO mudar sem a varredura de capsula no editor)
# Z do ATOR = 0 (chao; o chao() do verificar confere +-5 cm). Z_PASSOS e Z_VULTO valem SO para o ponto de som/olhar do evento
# (PontoSom); nunca como Z do ator (a figura flutuaria).
Z_ATOR = 0.0
Z_PASSOS = 60.0
# V0/V1 = L1_VAO de add_loop_events.py:441 (conferido no __main__ por leitura do arquivo; este modulo nao importa o outro)
V0 = (-3250.0, -700.0)
V1 = (-3275.0, -665.0)
Z_VULTO = 120.0
TMOV_I = 1.10            # reposicao do Vulto V0 -> V1 (43 cm) dentro do apagao do meio (invisivel: P = 0)
TMOV_F = 1.28
OFFSET_YAW_VULTO = -30.0  # yaw do Vulto = yaw para a camera do disparo + OFFSET, desfeito aos poucos ate DuracaoS (encara a camera)
YAW0_VULTO = 90.0        # yaw com que a instancia do vao nasce no mapa (so editor: o BP recalcula no Iniciar)
PARADO = "vulto"
PASSOS = "passos"

# PadraoPiscar NOVO do Vulto e o do Passos (sem mudanca). bApagarNoFim/RestaurarAposS como no pacote_loop1.
# figura/luz/anim: quem mostra o evento (BP_LuxVultoFluido) e de qual luz propria le a intensidade real.
EVENTOS = {
    "vulto": dict(nome="EV_L1_VultoParado", padrao=[0.25, 0.8, 0.25, 0.8, 0.3], apagar_no_fim=False, restaurar=0.0,
                  ap=F_ESCURO, duracao=2.25, n_janelas=2, intervalo_rep_s=1.05, figura="LUX_Vulto_L1_Porta",
                  luz="LUX_L1_LuzFundo", anim="idle"),
    "passos": dict(nome="EV_L1_PassosPesados", padrao=[0.5, 0.8] * 3, apagar_no_fim=True, restaurar=2.5,
                   ap=F_ESCURO, duracao=5.60, n_janelas=3, intervalo_rep_s=0.65, figura="LUX_Vulto_L1_Passos",
                   luz="LUX_L1_LuzPassos", anim="andar")}

# padroes das variaveis editaveis do BP_LuxVultoFluido (CDO); os dados reais vem de dados_instancia()
PADROES_BP = dict(DuracaoS=2.0, EntradaS=ENTRADA_S, SaidaS=SAIDA_S, MargemS=MARGEM_S, TolS=TOL_S, TMovI=0.0, TMovF=1.0, bEncarar=True,
                  YawFixo=0.0, OffsetYaw=0.0, FaseIni=-1.0, TaxaAnim=1.0, DistMinCam=DIST_MIN_CAM, DistPlenaCam=DIST_PLENA_CAM, bLog=False)


def _ev(evento, padrao=None):
    ev = dict(EVENTOS[evento] if isinstance(evento, str) else evento)
    if padrao is not None:
        ev["padrao"] = list(padrao)
    return ev


# ---------------------------------------------------------------- janelas (PORTADA de add_vulto_corre.py:887-902, sem import)
def janelas(padrao, bApagarNoFim, restaurar, ate=12.0):
    """(escuras, acesas, TSubNom, JanAcesa) em s depois do DisparoT, como o PassoPiscar/FimPiscar do evento: passos pares do
    PadraoPiscar apagados (no maximo 8, cada um com 0,25 s ou mais); no fim, com bApagarNoFim, apagado ate RestaurarAposS
    (0 = para sempre). `acesas` inclui a ultima (a que comeca na subida final do FimPiscar/RestaurarLuzes); TSubNom e JanAcesa
    so tem as janelas acesas DENTRO do padrao (a subida final nao e janela da figura)."""
    pp = [max(0.25, x) for x in list(padrao)[:8]]
    esc, ace, t = [], [], 0.0
    for i, d in enumerate(pp):
        (esc if i % 2 == 0 else ace).append((t, t + d))
        t += d
    n_dentro = len(ace)
    if bApagarNoFim:
        esc.append((t, t + restaurar if restaurar > 0 else 1e9))
        if restaurar > 0:
            ace.append((t + restaurar, ate))
    else:
        ace.append((t, ate))
    tsub_nom = [a for a, b in ace[:n_dentro]]
    jan_acesa = [round(b - a, 6) for a, b in ace[:n_dentro]]
    return esc, ace, tsub_nom, jan_acesa


def _eventos_luz(ev):
    """[(t_ideal, fator)] das mudancas de luz do evento; o elo k (k=0 no Executar) usa o atraso acumulado de k timers."""
    pp = [max(0.25, x) for x in list(ev["padrao"])[:8]]
    n = len(pp)
    out, t = [(0.0, ev["ap"])], 0.0
    for i, d in enumerate(pp):
        t += d
        j = i + 1                                          # passo que executa agora
        if j < n:
            out.append((t, 1.0 if j % 2 == 1 else ev["ap"]))
        else:                                              # FimPiscar
            out.append((t, 0.0 if ev["apagar_no_fim"] else 1.0))
            if ev["apagar_no_fim"] and ev["restaurar"] > 0:
                out.append((t + ev["restaurar"], 1.0))     # RestaurarLuzes
    return out


def luz_nominal(t, evento="passos", padrao=None):
    """fator de luz IDEAL (sem deriva de timer) = Intensity / IntensOrig em t s depois do DisparoT."""
    ev = _ev(evento, padrao)
    f = 1.0
    for ti, fi in _eventos_luz(ev):
        if ti <= t + 1e-12:
            f = fi
    return f


# ---------------------------------------------------------------- geometria
def caminho_passos(fim=FIM, dobra=None):
    """polilinha (x, y) da figura dos Passos: P0 -> [dobra] -> fim."""
    pts = [P0] + ([tuple(dobra)] if dobra else []) + [tuple(fim)]
    return pts


def _comprimento(pts):
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def _ao_longo(pts, s):
    s = max(0.0, s)
    for a, b in zip(pts, pts[1:]):
        d = math.dist(a, b)
        if s <= d or (a, b) == (pts[-2], pts[-1]):
            f = min(1.0, s / d) if d > 0 else 0.0
            return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
        s -= d
    return pts[-1]


def pos(t, evento="passos", caminho=None):
    """posicao (x, y) da figura t s depois do DisparoT (tempo ABSOLUTO, como o VLerp do BP: independe de FPS)."""
    if evento == "vulto":
        if t <= TMOV_I:
            return V0
        f = min(1.0, (t - TMOV_I) / (TMOV_F - TMOV_I))
        return (V0[0] + (V1[0] - V0[0]) * f, V0[1] + (V1[1] - V0[1]) * f)
    return _ao_longo(caminho or caminho_passos(), V * t)


def tempo_fim_reta(caminho=None):
    return _comprimento(caminho or caminho_passos()) / V


def yaw(t, evento="passos", yaw_para_camera=0.0, caminho=None):
    """yaw (graus) da figura: Passos = direcao da reta D, fixo (bEncarar falso); Vulto = yaw para a camera do disparo (calculado UMA vez,
    no Iniciar) + OFFSET que se desfaz linearmente ate DuracaoS: a figura gira devagar ate encarar a camera."""
    if evento == "vulto":
        return yaw_para_camera + OFFSET_YAW_VULTO * (1.0 - _clamp(t / EVENTOS["vulto"]["duracao"]))
    pts = caminho or caminho_passos()
    return math.degrees(math.atan2(pts[-1][1] - pts[0][1], pts[-1][0] - pts[0][0]))


def dados_instancia(chave):
    """valores de INSTANCIA do BP_LuxVultoFluido da figura do evento `chave` ('vulto' | 'passos'), com os nomes exatos das variaveis do BP.
    Fonte unica para o ensure_l1_figuras e para o verificar_l1 (nenhum numero copiado a mao). Arrays em listas; vetores em tuplas (x, y, z)
    do ATOR (z = Z_ATOR, o chao). Evento e ActorLuz (referencias) ficam por conta de quem aplica: EVENTOS[chave]['nome'] e ['luz']."""
    ev = EVENTOS[chave]
    esc, ace, tsub, jan = janelas(ev["padrao"], ev["apagar_no_fim"], ev["restaurar"])
    if chave == "vulto":
        a, b, ti, tf = V0, V1, TMOV_I, TMOV_F
        extra = dict(bEncarar=True, YawFixo=0.0, OffsetYaw=OFFSET_YAW_VULTO, FaseIni=-1.0, TaxaAnim=1.0)
    else:
        a, b, ti, tf = P0, FIM, 0.0, tempo_fim_reta()
        extra = dict(bEncarar=False, YawFixo=yaw(0, "passos"), OffsetYaw=0.0, FaseIni=FASE0, TaxaAnim=TAXA)
    d = dict(PADROES_BP)
    d.update(DuracaoS=ev["duracao"], JanAcesa=list(jan), TSubNom=list(tsub), PontoA=(a[0], a[1], Z_ATOR), PontoB=(b[0], b[1], Z_ATOR),
             TMovI=ti, TMovF=tf, **extra)
    return d


def pontos_percurso(chave, passo=10.0):
    """pontos (x, y, Z_ATOR) a cada `passo` cm (no maximo) em TODO o trecho percorrido pela figura (a reta D dos Passos; a reposicao
    V0 -> V1 do Vulto), com os dois extremos. A varredura de capsula e de chao do verificar_l1 passa em cada um."""
    pts = caminho_passos() if chave == "passos" else [V0, V1]
    comp = _comprimento(pts)
    n = max(1, math.ceil(comp / passo - 1e-9))
    return [(x, y, Z_ATOR) for x, y in (_ao_longo(pts, comp * i / n) for i in range(n + 1))]


# ---------------------------------------------------------------- pacote para o simulador / add_loop_events
def pacote_loop1_dados():
    """valores de EVENTO dos dois eventos de figura (os mesmos que pacote_loop1() de add_loop_events.py grava; o __main__ confere por leitura
    do arquivo) + o caminho da figura, para sim_eventos_offline.py e para dados_novo(). PontoSom usa Z_VULTO/Z_PASSOS (som/olhar, nao o ator)."""
    return {
        "vulto": dict(PadraoPiscar=list(EVENTOS["vulto"]["padrao"]), bApagarNoFim=EVENTOS["vulto"]["apagar_no_fim"],
                      RestaurarAposS=EVENTOS["vulto"]["restaurar"], caminho=[V0, V1], PontoSom=(V0[0], V0[1], Z_VULTO),
                      Repeticoes=3, IntervaloRepS=EVENTOS["vulto"]["intervalo_rep_s"], DeslocPorRep=(-12.5, 17.5, 0.0)),
        "passos": dict(PadraoPiscar=list(EVENTOS["passos"]["padrao"]), bApagarNoFim=EVENTOS["passos"]["apagar_no_fim"],
                       RestaurarAposS=EVENTOS["passos"]["restaurar"], caminho=caminho_passos(), PontoSom=(P0[0], P0[1], Z_PASSOS),
                       Repeticoes=9, IntervaloRepS=EVENTOS["passos"]["intervalo_rep_s"], DeslocPorRep=(PASSO_CM, 1.8, 0.0))}


# ---------------------------------------------------------------- simulacao da luz (cadeia de timers) e da presenca
def _clamp(x, a=0.0, b=1.0):
    return a if x < a else (b if x > b else x)


class Execucao:
    """uma execucao: eventos reais da luz (lt, lf), amostras do timer da figura (S, PV) e a grade de quadros (theta, dt)."""
    __slots__ = ("ev", "fps", "dt", "theta", "phi", "lt", "lf", "S", "PV", "tsubs", "entrada", "saida", "margem", "tol")

    def f(self, t):
        i = bisect.bisect_right(self.lt, t) - 1
        return self.lf[i] if i >= 0 else 1.0

    def P(self, t):
        """P exibido em t (a figura segura o ultimo valor ate a proxima amostra do timer)."""
        i = bisect.bisect_right(self.S, t) - 1
        return self.PV[i] if i >= 0 else 0.0


def executa(evento, fps, seed=0, deriva=None, lag=0.0, extra=(), entrada=None, saida=None, margem=None, tol=None, padrao=None):
    """simula UM disparo. deriva None = cada elo atrasa U(0, dt); 'max' = todo elo atrasa dt; 'zero' = sem atraso.
    lag = quanto a figura enxerga a luz atrasada (0 = ve a luz do mesmo instante; pior caso = dt).
    extra = [(t, fator)] mudancas de luz EXTRAS (ex.: RestaurarLuzes por troca de loop) em t exato."""
    entrada = ENTRADA_S if entrada is None else entrada
    saida = SAIDA_S if saida is None else saida
    margem = MARGEM_S if margem is None else margem
    tol = TOL_S if tol is None else tol
    ev = _ev(evento, padrao)
    dt = 1.0 / fps
    rng = random.Random(seed)
    # --- luz real: elo k atrasa a soma de k atrasos
    lt, lf = [0.0], [ev["ap"]]
    ideal = _eventos_luz(ev)
    t, prev = 0.0, 0.0
    for ti, fi in ideal[1:]:
        e = rng.uniform(0.0, dt) if deriva is None else (dt if deriva == "max" else 0.0)
        t += (ti - prev) + e
        prev = ti
        lt.append(t)
        lf.append(fi)
    if extra:
        par = sorted(list(zip(lt, lf)) + [(float(a), float(b)) for a, b in extra], key=lambda x: x[0])
        lt, lf = [a for a, b in par], [b for a, b in par]
    # --- grade de quadros e timer da figura (loop 0,02 s, vencimentos fixos; dispara no 1o quadro >= vencimento)
    theta = rng.uniform(0.0, dt) if deriva is None else 0.0
    phi = rng.uniform(0.0, TIMER_S) if deriva is None else 0.0
    _, _, tsub_nom, jan = janelas(ev["padrao"], ev["apagar_no_fim"], ev["restaurar"])
    nj = len(jan)
    dur = ev["duracao"]
    S, PV, tsubs = [], [], []
    nsub, tsub, ant, iniciou, n, ultimo = 0, 0.0, False, False, 0, -1.0
    while True:
        exp = phi + n * TIMER_S
        n += 1
        m = math.ceil((exp - theta) / dt - 1e-9)
        s = theta + m * dt
        if s <= ultimo + 1e-12:
            continue
        ultimo = s
        if s >= dur:                                       # Encerrar: P = 0, esconde
            S.append(s)
            PV.append(0.0)
            break
        i = bisect.bisect_right(lt, s - lag) - 1
        fv = lf[i] if i >= 0 else 1.0
        if not iniciou:                                    # Iniciar: reseta NSub/TSub, bLuzAnt := f > 0,5 do instante
            iniciou, ant = True, fv > 0.5
            S.append(s)
            PV.append(0.0)
            continue
        claro = fv > 0.5
        if claro and not ant:
            nsub += 1
            tsub = s
            tsubs.append(s)
        ant = claro
        p = 0.0
        if 0 < nsub <= nj and abs(tsub - tsub_nom[nsub - 1]) <= tol:
            L = _clamp((fv - 0.2) / 0.6)
            p = min(_clamp((s - tsub) / entrada), _clamp((tsub + jan[nsub - 1] - margem - s) / saida)) * L
        S.append(s)
        PV.append(p)
    r = Execucao()
    r.ev, r.fps, r.dt, r.theta, r.phi, r.lt, r.lf, r.S, r.PV, r.tsubs = ev, fps, dt, theta, phi, lt, lf, S, PV, tsubs
    r.entrada, r.saida, r.margem, r.tol = entrada, saida, margem, tol
    return r


_CACHE = {}


def P_nominal(t, fps, seed=0, evento="passos", **kw):
    """P(t) exibido, com a deriva k x dt da cadeia de timers (k = numero de elos ate a subida) e a amostragem do timer."""
    chave = (evento if isinstance(evento, str) else id(evento), fps, seed, tuple(sorted((a, str(b)) for a, b in kw.items())))
    r = _CACHE.get(chave)
    if r is None:
        r = _CACHE[chave] = executa(evento, fps, seed, **kw)
    return r.P(t)


def P_continuo(t, evento="passos", entrada=None, saida=None, margem=None):
    """P IDEAL (sem deriva e sem amostragem): rampa de entrada/saida em cada janela nominal."""
    entrada = ENTRADA_S if entrada is None else entrada
    saida = SAIDA_S if saida is None else saida
    margem = MARGEM_S if margem is None else margem
    ev = _ev(evento)
    _, _, tsub, jan = janelas(ev["padrao"], ev["apagar_no_fim"], ev["restaurar"])
    p = 0.0
    for ts, d in zip(tsub, jan):
        p = max(p, min(_clamp((t - ts) / entrada), _clamp((ts + d - margem - t) / saida)))
    return p


def monte_carlo(evento, fps, n=10000, lag=0.0, seed0=1000, **kw):
    """n execucoes: conta violacoes de (a) P > 0 em quadro com f < 0,2 e (c) P > 0 durante a reposicao do Vulto;
    mede o maior degrau de P entre amostras consecutivas do timer da figura (degrau por quadro exibido)."""
    ev = _ev(evento)
    dur = ev["duracao"]
    res = dict(evento=evento, fps=fps, n=n, lag=lag, runs_viol=0, quadros_viol=0, quadros_escuros=0, p_max_escuro=0.0,
               repos_viol=0, repos_quadros=0, dp_max=0.0, tsub_atraso_max=0.0)
    _, _, tsub_nom, _ = janelas(ev["padrao"], ev["apagar_no_fim"], ev["restaurar"])
    for i in range(n):
        r = executa(evento, fps, seed0 + i, lag=lag, **kw)
        dt, th, S, PV, lt, lf = r.dt, r.theta, r.S, r.PV, r.lt, r.lf
        viol = 0
        for j in range(len(lt)):
            if lf[j] >= 0.2:
                continue
            a = lt[j]
            b = lt[j + 1] if j + 1 < len(lt) else 1e9
            b = min(b, dur)
            m = math.ceil((a - th) / dt - 1e-9)
            g = th + m * dt
            while g < b:                                   # quadros exibidos com a luz real escura
                k = bisect.bisect_right(S, g) - 1
                p = PV[k] if k >= 0 else 0.0
                res["quadros_escuros"] += 1
                if p > 1e-12:
                    viol += 1
                    res["p_max_escuro"] = max(res["p_max_escuro"], p)
                m += 1
                g = th + m * dt
        res["quadros_viol"] += viol
        res["runs_viol"] += 1 if viol else 0
        if evento == "vulto":                              # (c) reposicao so com P = 0
            m = math.ceil((TMOV_I - th) / dt - 1e-9)
            g = th + m * dt
            while g <= TMOV_F + 1e-12:
                k = bisect.bisect_right(S, g) - 1
                res["repos_quadros"] += 1
                if k >= 0 and PV[k] > 1e-12:
                    res["repos_viol"] += 1
                m += 1
                g = th + m * dt
        for k in range(1, len(PV)):
            res["dp_max"] = max(res["dp_max"], abs(PV[k] - PV[k - 1]))
        for ts, tn in zip(r.tsubs, tsub_nom):
            res["tsub_atraso_max"] = max(res["tsub_atraso_max"], ts - tn)
    return res


def dp_continuo_max(evento="passos", passo=0.02, **kw):
    """max |P(t+passo) - P(t)| do P ideal (plano C1: rampa de 0,12 s = 0,17 por 0,02 s)."""
    t, m = 0.0, 0.0
    fim = _ev(evento)["duracao"]
    while t < fim:
        m = max(m, abs(P_continuo(t + passo, evento, **kw) - P_continuo(t, evento, **kw)))
        t += 0.001
    return m


# ---------------------------------------------------------------- verifica (R-LUZ / R-VIS / R-POS / R-ANIM / R-SOM)
VEL_GIRO_MAX = 30.0      # graus/s: o Vulto "gira devagar ate encarar a camera" (OffsetYaw / DuracaoS); acima disso e um giro brusco


def dados_de_instancia(chave, fig, evt):
    """descricao de UMA figura no formato que verifica() le, a partir dos valores de instancia da figura (`fig`: variaveis do BP +
    saved_playing e saved_play_rate da animation_data) e do evento (`evt`: PadraoPiscar, bApagarNoFim, RestaurarAposS, Repeticoes,
    IntervaloRepS, DeslocPorRep e PontoSom em mundo). No editor, o verificar_l1 monta fig/evt dos atores do mapa; dados_novo() monta
    do proprio cronograma. Os dois caminhos usam a MESMA verifica()."""
    ev = EVENTOS[chave]
    pa, pb = fig["PontoA"], fig["PontoB"]
    ent, sai, mar = fig["EntradaS"], fig["SaidaS"], fig["MargemS"]
    comp = math.hypot(pb[0] - pa[0], pb[1] - pa[1])
    dmov = fig["TMovF"] - fig["TMovI"]
    ds = evt["DeslocPorRep"]
    n, dt = int(evt["Repeticoes"]), evt["IntervaloRepS"]
    if chave == "vulto":
        yaw_ok = bool(fig["bEncarar"]) and abs(fig["OffsetYaw"]) / max(1e-9, fig["DuracaoS"]) <= VEL_GIRO_MAX
        yaw_msg = "Vulto: bEncarar e giro lento (|OffsetYaw|/DuracaoS <= %.0f graus/s)" % VEL_GIRO_MAX
    else:
        dir_graus = math.degrees(math.atan2(pb[1] - pa[1], pb[0] - pa[0]))
        yaw_ok = (not fig["bEncarar"]) and abs(fig["YawFixo"] - dir_graus) <= 0.5
        yaw_msg = "Passos: bEncarar falso e YawFixo = direcao do percurso (%.2f graus) +-0,5" % dir_graus
    c = dict(evento=chave, nome=ev["nome"], modo="fluido", padrao=list(evt["PadraoPiscar"]), apagar_no_fim=bool(evt["bApagarNoFim"]),
             restaurar=evt["RestaurarAposS"], duracao=fig["DuracaoS"], tsub_nom=list(fig["TSubNom"]), jan_acesa=list(fig["JanAcesa"]),
             entrada_s=ent, saida_s=sai, margem_s=mar, tol_s=fig["TolS"], dp_max_02=min(1.0, TIMER_S / max(1e-9, min(ent, sai))),
             saltos=[], repos=[], show_hide=[(0.04, "show", 0.0, 0.0), (fig["DuracaoS"], "hide", 0.0, 0.0)],
             anim_tocando=bool(fig["saved_playing"]), play_rate=fig["saved_play_rate"], fase0=fig["FaseIni"], yaw_fixo=yaw_ok, yaw_msg=yaw_msg,
             n_janelas_esperadas=ev["n_janelas"], vis_por_janela=None, taxa_anim=fig["TaxaAnim"], intervalo_rep_s=dt,
             desloc_rep_cm=math.hypot(ds[0], ds[1]), sons=[k * dt for k in range(n)], evt=evt, v_cm_s=None)
    if chave == "vulto":
        c["repos"] = [(fig["TMovI"], fig["TMovF"], comp)]
    else:
        c.update(comprimento_cm=comp, velocidade_cm_s=comp / max(1e-9, dmov), v_cm_s=comp / max(1e-9, dmov))
    return c


def dados_novo(evento, entrada=None, saida=None, margem=None, tol=None, padrao=None, caminho=None):
    """descricao do desenho NOVO (BP_LuxVultoFluido) no formato que verifica() le, montada do proprio cronograma. Os argumentos
    entrada/saida/margem/tol/padrao trocam UM numero do desenho (testes negativos); caminho troca o percurso dos Passos."""
    fig = dados_instancia(evento)
    fig.update(saved_playing=True, saved_play_rate=fig["TaxaAnim"])
    evt = dict(pacote_loop1_dados()[evento])
    if entrada is not None: fig["EntradaS"] = entrada
    if saida is not None: fig["SaidaS"] = saida
    if margem is not None: fig["MargemS"] = margem
    if tol is not None: fig["TolS"] = tol
    if padrao is not None:
        evt["PadraoPiscar"] = list(padrao)
        esc, ace, tsub, jan = janelas(evt["PadraoPiscar"], evt["bApagarNoFim"], evt["RestaurarAposS"])
        fig.update(TSubNom=tsub, JanAcesa=jan)      # os dados da figura acompanham o padrao (so o n de janelas e o resto reprovam)
    if caminho is not None:
        fig["PontoA"], fig["PontoB"] = (caminho[0][0], caminho[0][1], Z_ATOR), (caminho[-1][0], caminho[-1][1], Z_ATOR)
        fig["TMovF"] = _comprimento(caminho) / V
    return dados_de_instancia(evento, fig, evt)


def dados_v3(evento):
    """descricao do desenho v3 (BP_LuxVultoQuadros, commit 55dcf08): quadros com teleporte, pose congelada, tranco no claro,
    opacidade 0 -> 0,65 em 1 quadro, 3 sons / 4 bordas no Vulto e padrao antigo [0,25; 1,6; 0,3]."""
    if evento == "vulto":
        pad = [0.25, 1.6, 0.3]
        esc, ace, tsub, jan = janelas(pad, False, 0.0)
        return dict(evento="vulto", nome="EV_L1_VultoParado(v3)", modo="quadros", padrao=pad, apagar_no_fim=False, restaurar=0.0,
                    duracao=1.97, tsub_nom=tsub, jan_acesa=jan, entrada_s=0.0, saida_s=0.0, margem_s=0.08, tol_s=0.0,
                    dp_max_02=0.65, saltos=[(0.925, math.dist(V0, V1))], repos=[], show_hide=[(0.0, "show", 0.0, 0.65), (1.97, "hide", 0.65, 0.0)],
                    anim_tocando=False, fase0=None, yaw_fixo=True, n_janelas_esperadas=1, vis_por_janela=[1.6 - 0.14],
                    v_cm_s=None, taxa_anim=None, intervalo_rep_s=0.925, desloc_rep_cm=None, sons=[0.0, 0.925, 1.85])
    pad = [0.5, 0.8] * 3
    esc, ace, tsub, jan = janelas(pad, True, 2.5)
    return dict(evento="passos", nome="EV_L1_PassosPesados(v3)", modo="quadros", padrao=pad, apagar_no_fim=True, restaurar=2.5,
                duracao=4.1, tsub_nom=tsub, jan_acesa=jan, entrada_s=0.0, saida_s=0.0, margem_s=0.08, tol_s=0.0, dp_max_02=0.65,
                saltos=[(0.0, 55.0), (1.3, 55.0), (2.6, 55.0), (3.9, 55.0)],
                repos=[], show_hide=[(0.0, "show", 0.0, 0.65), (4.1, "hide", 0.65, 0.0)], anim_tocando=False, fase0=None,
                yaw_fixo=True, n_janelas_esperadas=3, vis_por_janela=[0.8 - 0.14] * 3, v_cm_s=55.0 / 1.3, taxa_anim=None,
                intervalo_rep_s=1.3, desloc_rep_cm=55.0, sons=[k * 1.3 for k in range(4)], velocidade_cm_s=55.0 / 1.3)


def verifica_som(chave, evt):
    """regras R-SOM do plano sobre os valores de um EVENTO EV_L1_* (`evt` como em dados_de_instancia; PontoSom e DeslocPorRep em
    coordenadas de mundo, o ator do evento sem rotacao): o som cai onde o pe/figura esta. Usada pelo verificar do add_loop_events.py
    (so tem o evento) e, via verifica(), pelo verificar_l1. Devolve [(regra, msg)]; vazia = PASS."""
    f = []
    pp = list(evt["PadraoPiscar"])
    esc, ace, tsub, jan = janelas(pp, bool(evt["bApagarNoFim"]), evt["RestaurarAposS"])
    quedas = [a for a, b in esc]
    n, dt = int(evt["Repeticoes"]), evt["IntervaloRepS"]
    ps, ds = evt["PontoSom"], evt["DeslocPorRep"]
    ref0 = P0 if chave == "passos" else V0
    tol_cm = 1.0 if chave == "passos" else 25.0
    if math.hypot(ps[0] - ref0[0], ps[1] - ref0[1]) > 1.0 + 1e-9:
        f.append(("R-SOM-1", "PontoSom (%.1f, %.1f) a mais de 1 cm de (%.1f, %.1f), o inicio da figura" % (ps[0], ps[1], ref0[0], ref0[1])))
    for k in range(n):
        som = (ps[0] + k * ds[0], ps[1] + k * ds[1])
        fx = pos(k * dt, chave)
        d = math.hypot(som[0] - fx[0], som[1] - fx[1])
        if d > tol_cm + 1e-9:
            f.append(("R-SOM-2", "som %d em t=%.3f s a %.1f cm da figura (> %.0f cm)" % (k, k * dt, d, tol_cm)))
    if chave == "passos":
        if abs(dt - 0.4665 / TAXA) > 0.005 + 1e-12:
            f.append(("R-SOM-3", "IntervaloRepS %.3f != 0,4665/TAXA = %.3f (+-5 ms)" % (dt, 0.4665 / TAXA)))
        (ax, ay), (bx, by) = caminho_passos()[0], caminho_passos()[-1]
        comp = math.hypot(bx - ax, by - ay)
        ex, ey = V * dt * (bx - ax) / comp, V * dt * (by - ay) / comp
        if math.hypot(ds[0] - ex, ds[1] - ey) > 1.0 + 1e-9:
            f.append(("R-SOM-4", "DeslocPorRep (%.1f, %.1f) != V x IntervaloRepS na direcao do percurso (%.1f, %.1f) (+-1 cm)" % (ds[0], ds[1], ex, ey)))
        if (n - 1) * dt > tempo_fim_reta() + 0.05:
            f.append(("R-SOM-7", "o ultimo passo (%.2f s) cai depois do fim da reta (%.2f s)" % ((n - 1) * dt, tempo_fim_reta())))
        for k in range(n):
            t = k * dt
            if k % 2 == 0 and t <= quedas[-1] + 1e-9 and min(abs(t - q) for q in quedas) > 0.02:
                f.append(("R-SOM-6", "contato %d em %.3f s nao coincide com o inicio de um apagao (quedas %s)" % (k, t, [round(q, 3) for q in quedas])))
    else:
        if len(pp) >= 3 and abs(dt - (pp[1] + pp[2])) > 1e-3:
            f.append(("R-SOM-5", "IntervaloRepS do Vulto %.3f != PadraoPiscar[1]+[2] = %.3f" % (dt, pp[1] + pp[2] if len(pp) >= 3 else -1)))
        for k in range(n):
            t = k * dt
            if min(abs(t - q) for q in quedas) > 0.02:
                f.append(("R-SOM-6", "estalo %d em %.3f s nao cai numa queda nominal da luz (quedas %s)" % (k, t, [round(q, 3) for q in quedas])))
    return f


def verifica(c, fps_folga=30.0):
    """lista de (regra, mensagem) das violacoes; vazia = PASS. Regras R-LUZ/R-VIS/R-POS/R-ANIM do plano (passos 4 e 10) + R-SOM
    (verifica_som, so no desenho 'fluido'; o 'quadros' da v3 usa o R-LUZ-2/R-ANIM-2 escalar). R-POS-2 (varredura de capsula, chao e
    folga a CutPart14) so existe no editor e NAO e conferida aqui."""
    f = []
    pp, dt30 = c["padrao"], 1.0 / fps_folga
    esc, ace, tsub, jan = janelas(pp, c["apagar_no_fim"], c["restaurar"])
    quedas = [a for a, b in esc]
    # R-LUZ-1: regra do piscar (ALE:2166-2177)
    if sum(pp) > 4.0 + 1e-9:
        f.append(("R-LUZ-1", "soma do PadraoPiscar %.2f s > 4 s" % sum(pp)))
    if min(pp) < 0.25 - 1e-9:
        f.append(("R-LUZ-1", "passo %.2f s < 0,25 s" % min(pp)))
    if len(pp) > 8:
        f.append(("R-LUZ-1", "%d passos > 8" % len(pp)))
    # R-LUZ-2 (desenho 'quadros'): cada estalo / contato par do pe coincide com uma queda nominal da luz; no 'fluido' e o R-SOM-6
    if c["modo"] != "fluido":
        if c["evento"] == "vulto":
            for t in c["sons"]:
                if min(abs(t - q) for q in quedas) > 0.02:
                    f.append(("R-LUZ-2", "estalo em %.3f s nao coincide com queda de luz (quedas %s)" % (t, [round(q, 3) for q in quedas])))
        else:
            for k, t in enumerate(c["sons"]):
                if k % 2 == 0 and t <= quedas[-1] + 1e-9 and min(abs(t - q) for q in quedas) > 0.02:
                    f.append(("R-LUZ-2", "contato %d em %.3f s nao coincide com o inicio de um apagao" % (k, t)))
    # R-VIS-1: sem degrau de opacidade
    if c["dp_max_02"] > 0.2 + 1e-9:
        f.append(("R-VIS-1", "degrau de P por 0,02 s = %.2f > 0,2 (v3: 0 a 0,65 em 1 quadro)" % c["dp_max_02"]))
    for t, tipo, pa, pd in c["show_hide"]:
        if pa > 0.01 or pd > 0.01:
            f.append(("R-VIS-1", "%s em %.2f s com P %.2f -> %.2f (so com P = 0 nos dois lados)" % (tipo, t, pa, pd)))
    # R-VIS-3: janelas e tempo visivel
    if len(jan) != c["n_janelas_esperadas"]:
        f.append(("R-VIS-3", "%d janelas, esperado %d" % (len(jan), c["n_janelas_esperadas"])))
    if c["modo"] == "fluido":
        e, s, m = c["entrada_s"], c["saida_s"], c["margem_s"]
        if e + s + m > min(jan) + 1e-9:
            f.append(("R-VIS-3", "EntradaS+SaidaS+MargemS = %.2f > menor janela acesa %.2f" % (e + s + m, min(jan))))
        vis = [d - m - (e + s) / 2 for d in jan]
        # R-JAN: JanAcesa e TSubNom do BP == as janelas acesas calculadas do PadraoPiscar do evento (<= 0,01 s)
        for nome, tem, quer in (("TSubNom", c["tsub_nom"], tsub), ("JanAcesa", c["jan_acesa"], jan)):
            if len(tem) != len(quer) or any(abs(a - b) > 0.01 + 1e-9 for a, b in zip(tem, quer)):
                f.append(("R-JAN", "%s %s != janelas() do PadraoPiscar %s" % (nome, [round(x, 3) for x in tem], [round(x, 3) for x in quer])))
        # R-DUR: DuracaoS cai dentro do ultimo apagao, >= 0,10 s depois da ultima queda nominal e >= 0,10 s antes da subida final
        a_ult, b_ult = esc[-1]
        if not (a_ult + 0.10 - 1e-9 <= c["duracao"] <= b_ult - 0.10 + 1e-9):
            f.append(("R-DUR", "DuracaoS %.2f s fora de [%.2f, %.2f] (ultimo apagao %.2f-%.2f s, folga 0,10 s)" % (c["duracao"], a_ult + 0.10,
                                                                                                                  b_ult - 0.10, a_ult, b_ult)))
    else:
        vis = c["vis_por_janela"] or [0.0]
    for i, v in enumerate(vis):
        if v < 0.5 - 1e-9:
            f.append(("R-VIS-3", "janela %d: tempo com P >= 0,5 = %.2f s < 0,5 s" % (i + 1, v)))
    # R-POS-1: nenhum salto visivel; reposicao so com P = 0; velocidade de caminhada plausivel
    for t, cm in c["saltos"]:
        f.append(("R-POS-1", "salto de %.0f cm em %.2f s com a figura visivel (teleporte)" % (cm, t)))
    if c["modo"] == "fluido":
        janelas_p = []
        for i, (ts, d) in enumerate(zip(tsub, jan)):
            k_elo = 2 * i + 1
            janelas_p.append((ts, ts + d - c["margem_s"] + (k_elo + 1) * dt30 + TIMER_S))   # fim com deriva k x dt30 + deteccao
        for t0, t1, cm in c["repos"]:
            for a, b in janelas_p:
                if t0 < b and t1 > a:
                    f.append(("R-POS-1", "reposicao %.2f-%.2f s (%.0f cm) cai numa janela com P > 0 [%.2f, %.2f]" % (t0, t1, cm, a, b)))
        if c["evento"] == "passos" and c.get("velocidade_cm_s", 0) > 90.0:
            f.append(("R-POS-1", "velocidade %.1f cm/s > 90" % c["velocidade_cm_s"]))
    else:
        for t0, t1, cm in c["repos"]:
            f.append(("R-POS-1", "reposicao no claro %.2f-%.2f s" % (t0, t1)))
    if not c["yaw_fixo"]:
        f.append(("R-POS-1", "yaw fora da regra (%s)" % c.get("yaw_msg", "yaw nao fixo")))
    # R-ANIM-1 / R-ANIM-2
    if not c["anim_tocando"]:
        f.append(("R-ANIM-1", "animacao nao esta tocando (pose congelada)"))
    elif c["modo"] == "fluido" and c.get("play_rate") is not None and abs(c["play_rate"] - c["taxa_anim"]) > 1e-6:
        f.append(("R-ANIM-1", "saved_play_rate %.4f != TaxaAnim %.4f" % (c["play_rate"], c["taxa_anim"])))
    if c["evento"] == "passos":
        if c["taxa_anim"] is None or not c["anim_tocando"]:
            f.append(("R-ANIM-1", "sem taxa de animacao (pe nao casa com a velocidade)"))
        else:
            v = c["v_cm_s"]
            if abs(v - c["taxa_anim"] * V_NAT) / v > 0.03 + 1e-12:
                f.append(("R-ANIM-1", "|V - TAXA x V_NAT|/V = %.1f por cento > 3" % (100 * abs(v - c["taxa_anim"] * V_NAT) / v)))
            if c["modo"] != "fluido":
                if abs(c["intervalo_rep_s"] - 0.4665 / c["taxa_anim"]) > 0.005 + 1e-12:
                    f.append(("R-ANIM-2", "IntervaloRepS %.3f != 0,4665/TAXA = %.3f (+-5 ms)" % (c["intervalo_rep_s"], 0.4665 / c["taxa_anim"])))
                if abs(c["desloc_rep_cm"] - v * c["intervalo_rep_s"]) > 1.0 + 1e-12:
                    f.append(("R-ANIM-2", "DeslocPorRep %.1f != V x IntervaloRepS = %.1f (+-1 cm)" % (c["desloc_rep_cm"], v * c["intervalo_rep_s"])))
            if c["fase0"] is None or abs(c["fase0"] - FASE0) > 1e-6:
                f.append(("R-ANIM-2", "FaseIni %s != %.3f" % (c["fase0"], FASE0)))
    elif c["modo"] != "fluido":
        if c["intervalo_rep_s"] is not None and abs(c["intervalo_rep_s"] - (pp[1] + pp[2])) > 0.01:
            f.append(("R-ANIM-2", "IntervaloRepS do Vulto %.3f != PadraoPiscar[1]+[2] = %.3f" % (c["intervalo_rep_s"], pp[1] + pp[2])))
    if c["modo"] == "fluido":
        f += verifica_som(c["evento"], c["evt"])
    return f


def guarda_camera(dist):
    """fator da protecao de camera do BP: FClamp((dist - DIST_MIN_CAM) / (DIST_PLENA_CAM - DIST_MIN_CAM)), dist = Dist2D(figura, camera)."""
    return _clamp((dist - DIST_MIN_CAM) / (DIST_PLENA_CAM - DIST_MIN_CAM))


def _le_ale():
    """le add_loop_events.py por AST (sem importar, sem unreal): L1_VAO, L1_PASSOS e os argumentos literais dos ev(...) de
    pacote_loop1(). Serve para o __main__ conferir que os numeros do arquivo batem com este modulo (fonte unica dos numeros)."""
    import ast
    txt = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "add_loop_events.py"), encoding="utf-8").read()
    arv = ast.parse(txt)
    out = dict(L1_VAO=None, L1_PASSOS=None, eventos={})
    for no in arv.body:
        if isinstance(no, ast.Assign) and len(no.targets) == 1 and isinstance(no.targets[0], ast.Name) and no.targets[0].id in ("L1_VAO", "L1_PASSOS"):
            out[no.targets[0].id] = [tuple(p) for p in ast.literal_eval(no.value)]
        if isinstance(no, ast.FunctionDef) and no.name == "pacote_loop1":
            for c in ast.walk(no):
                if isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == "ev" and isinstance(c.args[0], ast.Constant):
                    kw = {}
                    for k in c.keywords:
                        try:
                            kw[k.arg] = ast.literal_eval(k.value)
                        except (ValueError, TypeError):
                            kw[k.arg] = "<expr>"
                    out["eventos"][c.args[0].value] = dict(kw, _ponto_som=ast.unparse(c.args[5]))
    return out


if __name__ == "__main__":
    import sys
    sys.dont_write_bytecode = True
    ok = 0

    def conf(cond, msg):
        global ok
        assert cond, "FALHOU: " + msg
        ok += 1
        print("  OK  " + msg)

    print("== constantes e geometria (CODIGO/DOC)")
    ale = _le_ale()
    conf(ale["L1_VAO"] == [V0, V1], "V0/V1 == L1_VAO de add_loop_events.py: %s" % ale["L1_VAO"])
    conf(ale["L1_PASSOS"] == [P0, FIM], "P0/FIM == L1_PASSOS de add_loop_events.py: %s" % ale["L1_PASSOS"])
    conf(abs(math.dist(V0, V1) - 43.0) < 0.05, "reposicao do Vulto V0 -> V1 = %.2f cm" % math.dist(V0, V1))
    L = _comprimento(caminho_passos())
    conf(abs(L - 450.25) < 0.05, "reta D = %.2f cm" % L)
    conf(abs(tempo_fim_reta() - 5.425) < 0.005, "TMovF dos Passos = %.3f s (plano 5,425)" % tempo_fim_reta())
    conf(abs(yaw(0) - 1.9) < 0.05, "yaw fixo dos Passos = %.2f graus (plano +1,9)" % yaw(0))
    conf(abs(pos(0.5)[0] - (-3208)) < 1.0 and abs(pos(1.3)[0] - (-3142)) < 1.0 and abs(pos(3.1)[0] - (-2993)) < 1.5,
         "x em 0,5/1,3/3,1 s = %.0f/%.0f/%.0f (plano -3208/-3142/-2993)" % (pos(0.5)[0], pos(1.3)[0], pos(3.1)[0]))
    tc = next(k * 0.001 for k in range(0, 6000) if pos(k * 0.001)[0] >= -3000.0)
    conf(abs(tc - 3.01) < 0.03, "cruza x=-3000 em %.3f s (plano 3,01 +-0,05)" % tc)
    # janelas(): tabelas esperadas (a copia antiga de add_vulto_corre.py foi movida para ca; o texto antigo e o do git HEAD)
    esc, ace, tsub, jan = janelas(EVENTOS["vulto"]["padrao"], False, 0.0)
    conf(esc == [(0.0, 0.25), (1.05, 1.3), (2.1, 2.4)] and ace[:2] == [(0.25, 1.05), (1.3, 2.1)] and ace[2][0] == 2.4,
         "Vulto: apagoes 0 / 1,05 / 2,10 s (0,25; 0,25; 0,30 s) e acesas 0,25-1,05 e 1,30-2,10: %s" % esc)
    conf(tsub == [0.25, 1.3] and jan == [0.8, 0.8], "Vulto: TSubNom [0,25; 1,30], JanAcesa [0,8; 0,8]")
    esc, ace, tsub, jan = janelas(EVENTOS["passos"]["padrao"], True, 2.5)
    conf(tsub == [0.5, 1.8, 3.1] and jan == [0.8, 0.8, 0.8] and abs(esc[-1][0] - 3.9) < 1e-9 and abs(esc[-1][1] - 6.4) < 1e-9,
         "Passos: TSubNom [0,5; 1,8; 3,1], JanAcesa [0,8 x3], apagao final 3,9-6,4 s")
    conf(luz_nominal(0.1, "passos") == 0.04 and luz_nominal(0.6, "passos") == 1.0 and luz_nominal(4.0, "passos") == 0.0 and luz_nominal(6.5, "passos") == 1.0,
         "luz_nominal: 0,04 / 1,0 / 0,0 (apagao final) / 1,0 (restaura)")

    print("== add_loop_events.py: pacote_loop1() bate com este modulo (leitura por AST)")
    d = pacote_loop1_dados()
    for chave, rot in (("vulto", "EV_L1_VultoParado"), ("passos", "EV_L1_PassosPesados")):
        kw, ds = ale["eventos"].get(rot), d[chave]
        conf(kw is not None and kw["PadraoPiscar"] == ds["PadraoPiscar"] and kw["Repeticoes"] == ds["Repeticoes"]
             and abs(kw["IntervaloRepS"] - ds["IntervaloRepS"]) < 1e-9 and tuple(kw["DeslocPorRep"]) == tuple(ds["DeslocPorRep"]),
             "%s: PadraoPiscar %s, Repeticoes %s, IntervaloRepS %s, DeslocPorRep %s == vulto_cronograma" % (
                 rot, kw and kw["PadraoPiscar"], kw and kw["Repeticoes"], kw and kw["IntervaloRepS"], kw and kw["DeslocPorRep"]))
        conf(bool(kw["bApagarNoFim"]) == ds["bApagarNoFim"] and abs(kw.get("RestaurarAposS", 0.0) - ds["RestaurarAposS"]) < 1e-9
             and abs(kw["IntensidadeApagada"] - F_ESCURO) < 1e-9, "%s: bApagarNoFim, RestaurarAposS e IntensidadeApagada %s == vulto_cronograma" % (rot, F_ESCURO))
    conf(ale["eventos"]["EV_L1_PassosPesados"]["_ponto_som"] == "(p0x, p0y, 60.0)" and ale["eventos"]["EV_L1_VultoParado"]["_ponto_som"] == "(vx, vy, 120.0)",
         "PontoSom dos Passos = (P0, z %.0f) e o do Vulto = (V0, z %.0f): z so do som/olhar, o ator fica em z = %.0f" % (Z_PASSOS, Z_VULTO, Z_ATOR))

    print("== dados de instancia (fonte unica para ensure_l1_figuras / verificar_l1)")
    for chave in ("vulto", "passos"):
        di = dados_instancia(chave)
        ev = EVENTOS[chave]
        esc, ace, tsub, jan = janelas(ev["padrao"], ev["apagar_no_fim"], ev["restaurar"])
        conf(di["JanAcesa"] == jan and di["TSubNom"] == tsub and di["PontoA"][2] == Z_ATOR == 0.0 and di["PontoB"][2] == 0.0
             and di["DuracaoS"] == ev["duracao"], "%s: JanAcesa/TSubNom == janelas(), PontoA/PontoB em z = 0, DuracaoS %.2f" % (chave, di["DuracaoS"]))
        conf(di["EntradaS"] == ENTRADA_S == 0.17 and di["SaidaS"] == SAIDA_S == 0.17 and di["MargemS"] == 0.05 and di["TolS"] == 0.35
             and di["DistMinCam"] == 60.0 and di["DistPlenaCam"] == 100.0 and di["bLog"] is False, "%s: EntradaS = SaidaS = 0,17, MargemS 0,05, TolS 0,35, camera 60/100, bLog falso" % chave)
    dv, dp = dados_instancia("vulto"), dados_instancia("passos")
    conf(dv["PontoA"] == (-3250.0, -700.0, 0.0) and dv["PontoB"] == (-3275.0, -665.0, 0.0) and dv["TMovI"] == 1.10 and dv["TMovF"] == 1.28
         and dv["bEncarar"] and dv["OffsetYaw"] == -30.0 and dv["FaseIni"] == -1.0 and dv["TaxaAnim"] == 1.0 and dv["DuracaoS"] == 2.25,
         "Vulto: V0 -> V1 (z 0) em 1,10-1,28 s, bEncarar, OffsetYaw -30, FaseIni -1, TaxaAnim 1,0, DuracaoS 2,25")
    conf(dp["PontoA"] == (-3250.0, -740.0, 0.0) and dp["PontoB"] == (-2800.0, -725.0, 0.0) and dp["TMovI"] == 0.0 and abs(dp["TMovF"] - 5.4247) < 1e-3
         and not dp["bEncarar"] and abs(dp["YawFixo"] - 1.909) < 0.01 and dp["FaseIni"] == 0.333 and dp["TaxaAnim"] == 0.718 and dp["DuracaoS"] == 5.6,
         "Passos: P0 -> FIM (z 0) em 0 - %.3f s, bEncarar falso, YawFixo %.2f, FaseIni 0,333, TaxaAnim 0,718, DuracaoS 5,60" % (dp["TMovF"], dp["YawFixo"]))
    for chave, n_esperado in (("passos", 47), ("vulto", 6)):
        pp_ = pontos_percurso(chave)
        passos = [math.dist(a[:2], b[:2]) for a, b in zip(pp_, pp_[1:])]
        conf(len(pp_) == n_esperado and max(passos) <= 10.0 + 1e-9 and pp_[0][2] == 0.0 and
             math.dist(pp_[0][:2], (P0 if chave == "passos" else V0)) < 1e-6 and math.dist(pp_[-1][:2], (FIM if chave == "passos" else V1)) < 1e-6,
             "pontos_percurso(%s): %d pontos, passo maximo %.2f cm, extremos %s -> %s" % (chave, len(pp_), max(passos), pp_[0][:2], pp_[-1][:2]))
    conf(guarda_camera(21.0) == 0.0 and guarda_camera(60.0) == 0.0 and abs(guarda_camera(80.0) - 0.5) < 1e-9 and guarda_camera(100.0) == 1.0 and guarda_camera(500.0) == 1.0,
         "protecao de camera: 21 cm -> 0, 60 -> 0, 80 -> 0,5, >= 100 -> 1")

    print("== (d) pe sem deslizar")
    conf(V == 83.0, "V = 83,0 cm/s")
    conf(abs(V - TAXA * V_NAT) / V <= 0.03, "|V - TAXA x V_NAT|/V = %.3f por cento (<= 3; V_NAT %.1f medido, TAXA x V_NAT = %.2f)" % (100 * abs(V - TAXA * V_NAT) / V, V_NAT, TAXA * V_NAT))
    conf(abs(PASSO_CM / V - 0.65) < 0.002 and abs(0.4665 / TAXA - 0.65) < 0.005, "intervalo do passo %.4f s ~ 0,65 (0,4665/TAXA = %.4f)" % (PASSO_CM / V, 0.4665 / TAXA))

    print("== (e) PadraoPiscar novo do Vulto")
    pv = EVENTOS["vulto"]["padrao"]
    conf(pv == [0.25, 0.8, 0.25, 0.8, 0.3] and sum(pv) <= 4.0 and min(pv) >= 0.25 and len(pv) <= 8, "soma %.2f s <= 4, passos >= 0,25, %d passos <= 8" % (sum(pv), len(pv)))

    print("== desenho NOVO passa em verifica(); (f) NEGATIVOS devem REPROVAR")
    for ev in ("vulto", "passos"):
        r = verifica(dados_novo(ev))
        conf(not r, "verifica(dados_novo(%s)) PASS %s" % (ev, r))
    for ev in ("vulto", "passos"):
        r = verifica(dados_v3(ev))
        conf(len(r) >= 4, "NEGATIVO v3 %s reprovou de proposito com %d violacoes: %s" % (ev, len(r), sorted(set(a for a, b in r))))
        for a, b in r:
            print("        [reprova v3/%s] %s: %s" % (ev, a, b))
    v3_regras = set(a for ev in ("vulto", "passos") for a, b in verifica(dados_v3(ev)))
    conf({"R-VIS-1", "R-POS-1", "R-ANIM-1", "R-LUZ-2"} <= v3_regras, "v3 reprova R-VIS-1 (degrau), R-POS-1 (teleporte/tranco), R-ANIM-1 (pose congelada) e R-LUZ-2 (estalo fora de queda): %s" % sorted(v3_regras))
    r = verifica(dados_novo("passos", saida=0.6))
    conf(any(a == "R-VIS-3" for a, b in r), "NEGATIVO SaidaS=0,6 reprovou de proposito: %s" % r)
    r = verifica(dados_novo("vulto", saida=0.6))
    conf(any(a == "R-VIS-3" for a, b in r), "NEGATIVO SaidaS=0,6 (Vulto) reprovou de proposito: %s" % r)
    r = verifica(dados_novo("vulto", padrao=[0.25, 1.6, 0.3]))
    conf({"R-VIS-3", "R-SOM-5", "R-SOM-6"} <= set(a for a, b in r), "NEGATIVO padrao antigo [0,25; 1,6; 0,3] no desenho novo reprovou de proposito: %s" % [a for a, b in r])
    # negativos novos das regras da secao 2 do brief: cada um muda UM numero e a regra certa tem de acusar
    def muda(chave, campo, valor, onde="fig"):
        fig = dados_instancia(chave)
        fig.update(saved_playing=True, saved_play_rate=fig["TaxaAnim"])
        evt = dict(pacote_loop1_dados()[chave])
        (fig if onde == "fig" else evt)[campo] = valor
        return verifica(dados_de_instancia(chave, fig, evt))

    def acusa(r, regra):
        return any(a == regra for a, b in r)

    conf(acusa(muda("passos", "DuracaoS", 3.95), "R-DUR") and acusa(muda("vulto", "DuracaoS", 2.0), "R-DUR") and acusa(muda("vulto", "DuracaoS", 2.35), "R-DUR"),
         "NEGATIVO DuracaoS fora do ultimo apagao (Passos 3,95 s; Vulto 2,0 e 2,35 s) reprovou de proposito")
    conf(acusa(muda("passos", "JanAcesa", [0.8, 0.8, 0.6]), "R-JAN") and acusa(muda("vulto", "TSubNom", [0.25, 1.4]), "R-JAN"),
         "NEGATIVO JanAcesa/TSubNom fora de janelas() reprovou de proposito")
    conf(acusa(muda("passos", "bEncarar", True), "R-POS-1") and acusa(muda("passos", "YawFixo", 5.0), "R-POS-1") and acusa(muda("vulto", "OffsetYaw", -90.0), "R-POS-1"),
         "NEGATIVO yaw (Passos encarando; YawFixo 5 graus; Vulto girando 40 graus/s) reprovou de proposito")
    conf(acusa(muda("passos", "saved_playing", False), "R-ANIM-1") and acusa(muda("passos", "saved_play_rate", 1.0), "R-ANIM-1") and acusa(muda("passos", "TaxaAnim", 1.0), "R-ANIM-1")
         and acusa(muda("passos", "FaseIni", -1.0), "R-ANIM-2"), "NEGATIVO animacao (parada; play_rate != TaxaAnim; TaxaAnim 1,0 patina; FaseIni -1) reprovou de proposito")
    conf(acusa(muda("passos", "TMovF", 5.0), "R-POS-1") and acusa(muda("passos", "TMovF", 4.0), "R-ANIM-1") and acusa(muda("vulto", "TMovI", 0.9), "R-POS-1")
         and acusa(muda("vulto", "TMovF", 1.35), "R-POS-1"), "NEGATIVO velocidade > 90 cm/s / pe patinando / reposicao do Vulto dentro de janela com P > 0 reprovou de proposito")
    conf(acusa(muda("passos", "PontoSom", (-3250.0, -738.0, 60.0), "evt"), "R-SOM-1") and acusa(muda("passos", "IntervaloRepS", 1.3, "evt"), "R-SOM-3")
         and acusa(muda("passos", "DeslocPorRep", (55.0, 33.3, 0.0), "evt"), "R-SOM-4") and acusa(muda("passos", "DeslocPorRep", (50.0, 1.7, 0.0), "evt"), "R-SOM-2")
         and acusa(muda("passos", "Repeticoes", 12, "evt"), "R-SOM-7") and acusa(muda("vulto", "IntervaloRepS", 0.925, "evt"), "R-SOM-5")
         and acusa(muda("vulto", "DeslocPorRep", (-40.0, 17.5, 0.0), "evt"), "R-SOM-2"),
         "NEGATIVO som (PontoSom a 2 cm; IntervaloRepS 1,3; DeslocPorRep errado; passo 50 cm; 12 passos; Vulto 0,925 s e estalo a 40 cm) reprovou de proposito")
    conf(not verifica_som("passos", pacote_loop1_dados()["passos"]) and not verifica_som("vulto", pacote_loop1_dados()["vulto"]),
         "verifica_som() dos dois eventos do pacote: PASS")

    print("== rise falso (RestaurarLuzes fora de TSubNom) => P = 0")
    for fps in (30, 60, 113):
        for seed in range(200):
            r = executa("passos", fps, seed, extra=[(1.40, 1.0)])     # sobe no 2o apagao (depois da queda real), 0,40 s antes da subida nominal (1,8) > TolS
            assert max(p for s, p in zip(r.S, r.PV) if 1.40 <= s <= 2.7) == 0.0, "rise falso gerou P > 0 (fps %d seed %d)" % (fps, seed)
            r = executa("passos", fps, seed, extra=[(4.5, 1.0)])      # depois da ultima janela (NSub > Length)
            assert max(p for s, p in zip(r.S, r.PV) if s >= 4.5) == 0.0
            r = executa("vulto", fps, seed, extra=[(2.2, 0.04), (2.3, 1.0)])   # Vulto: sobe depois da 2a janela (NSub = 3 > 2)
            assert max(p for s, p in zip(r.S, r.PV) if s >= 2.2) == 0.0
        ok += 1
        print("  OK  rise falso (Passos 1,40 s e 4,5 s; Vulto 2,3 s): P = 0 nas 200 execucoes a %d FPS" % fps)

    print("== (a)/(c) 10000 execucoes por FPS: P = 0 em todo quadro com a luz real < 0,2; reposicao so com P = 0")
    N = 10000
    pior = {}
    for fps in (20, 30, 60, 113):
        for ev in ("vulto", "passos"):
            m = monte_carlo(ev, fps, N)
            pior[(ev, fps)] = m
            print("  fps %3d %-6s: execucoes com P>0 no escuro %d/%d, quadros violados %d/%d, P max no escuro %.3f, "
                  "reposicao violada %d/%d, atraso max da deteccao %.3f s, degrau max entre amostras %.3f"
                  % (fps, ev, m["runs_viol"], N, m["quadros_viol"], m["quadros_escuros"], m["p_max_escuro"], m["repos_viol"],
                     m["repos_quadros"], m["tsub_atraso_max"], m["dp_max"]))
    for fps in (30, 60, 113):
        for ev in ("vulto", "passos"):
            m = pior[(ev, fps)]
            conf(m["runs_viol"] == 0, "(a) %s a %d FPS: 0 violacoes de P=0 com f<0,2 em %d execucoes" % (ev, fps, N))
        conf(pior[("vulto", fps)]["repos_viol"] == 0, "(c) reposicao do Vulto (V0 a V1) so com P=0 a %d FPS (%d quadros)" % (fps, pior[("vulto", fps)]["repos_quadros"]))
    print("  (a 20 FPS so relata: violacoes Vulto %d/%d, Passos %d/%d)" % (pior[("vulto", 20)]["runs_viol"], N, pior[("passos", 20)]["runs_viol"], N))

    for fps in (30, 60, 113):   # pior caso informativo: a figura enxerga a luz com 1 quadro de atraso
        pes = [monte_carlo(e, fps, 2000, lag=1.0 / fps) for e in ("vulto", "passos")]
        print("  informativo, figura enxerga a luz 1 quadro atrasada, %3d FPS: execucoes com P>0 no escuro Vulto %d/2000, Passos %d/2000" % (fps, pes[0]["runs_viol"], pes[1]["runs_viol"]))

    print("== (b) degrau de P por amostra de 0,02 s (com os numeros do desenho: EntradaS = SaidaS = 0,17)")
    d_cont = max(dp_continuo_max(e) for e in ("vulto", "passos"))
    conf(d_cont <= 0.2, "P ideal (tempo continuo): max |dP| por 0,02 s = %.3f <= 0,2 (rampa 0,17 s = %.3f)" % (d_cont, TIMER_S / ENTRADA_S))
    for fps in (30, 60, 113):
        d = max(pior[("vulto", fps)]["dp_max"], pior[("passos", fps)]["dp_max"])
        conf(d <= 0.2 + 1e-9, "degrau MAXIMO entre amostras consecutivas do timer da figura a %d FPS = %.3f <= 0,2 (%d execucoes por evento)" % (fps, d, N))
    print("  (a 20 FPS so relata: degrau maximo %.3f)" % max(pior[("vulto", 20)]["dp_max"], pior[("passos", 20)]["dp_max"]))
    conf(all(not verifica(dados_novo(e)) for e in ("vulto", "passos")), "verifica() aceita os numeros finais (tempo com P>=0,5 por janela = %.2f s)" % (0.8 - MARGEM_S - ENTRADA_S))
    conf(max(monte_carlo(e, 60, 300, entrada=0.12, saida=0.15)["dp_max"] for e in ("vulto", "passos")) > 0.2,
         "NEGATIVO EntradaS=0,12 / SaidaS=0,15 (numeros antigos) dao degrau > 0,2 por amostra a 60 FPS: reprovou de proposito")

    print("== tabela de tempos (P nominal sem deriva e com deriva maxima k x dt)")
    for ev in ("vulto", "passos"):
        for fps in (30, 60, 113):
            for rotulo, dv in (("zero", "zero"), ("max", "max")):
                r = executa(ev, fps, 0, deriva=dv)
                acima = []
                t0 = None
                for s, p in zip(r.S, r.PV):
                    if p >= 0.5 and t0 is None:
                        t0 = s
                    if p < 0.5 and t0 is not None:
                        acima.append((round(t0, 3), round(s, 3)))
                        t0 = None
                print("  %-6s %3d FPS deriva %-4s: TSub %s ; P>=0,5 em %s (soma %.2f s)" % (ev, fps, rotulo, [round(x, 3) for x in r.tsubs], acima, sum(b - a for a, b in acima)))
    print("\nTODOS OS %d ASSERTS OK (os testes NEGATIVOS acima reprovaram de proposito)" % ok)
