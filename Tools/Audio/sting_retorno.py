# LUX - "Retorno": som ALTO que toca em TODA troca de loop (pedido do Bruno, 30/09): a "morte" de Santos a cada volta,
# no espirito do Retorno pela Morte do Subaru (Re:Zero), porem mais tenso. Som 100% ORIGINAL, sintetizado aqui
# (Python puro, stdlib; o Python do UE nao tem numpy). Nada do anime e copiado.
#   1) Fora do editor, gera o WAV + analise + espectrograma (nao precisa do editor aberto):
#      "C:/Program Files/Epic Games/UNREAL/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe" Tools/Audio/sting_retorno.py sintetizar
#   2) No editor (console ou execucao remota):
#      py ".../Tools/Audio/sting_retorno.py" sondar|instalar|verificar|desfazer
# Gancho: BP_LuxLoopManager.PedirTroca toca PlaySound2D(SomTroca) no INICIO da troca (setup_loop.py). Linha do tempo a
# partir desse t=0: camera desliza ate a macaneta (0,5 s) -> fade para preto (0,50-0,58) -> preto ate 0,62 (teleporte)
# -> fade de volta ate 0,82 -> porta do quarto abre (rangido 0,4) -> controle ~1,72 s. O IMPACTO cai no quadro preto.
# O instalar so muda a variavel de instancia LOOP_Manager.SomTroca (nenhum grafo e editado). desfazer: SomTroca = vazio.
# Condicoes do TCC: para desligar o som numa condicao, SomTroca = vazio no ator de condicao (futuro).
import math, os, random, struct, sys, wave, zlib
from array import array

AQUI = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(os.path.dirname(AQUI))
WAV = os.path.join(PROJ, "SourceArt", "Audio", "SW_LuxRetorno.wav")
ANALISE_DIR = os.path.join(PROJ, "Saved", "LuxSnapshots", "audio")
ASSET_DIR = "/Game/Masion/LUX/Loop/Audio"
ASSET = ASSET_DIR + "/SW_LuxRetorno"

SR = 48000
DUR = 4.8                 # s
T_IMP = 0.57              # s: impacto (ataque) -> com ~30 ms de latencia do mixer cai em ~0,60, no preto (0,58-0,62)
T_CORTE = T_IMP - 0.028   # a subida corta seco 28 ms antes: um instante de vacuo antes do golpe
PICO_DBFS = -1.0
SEMENTE = 1311

# niveis de PICO de cada camada em dB relativos ao golpe ("lub" = 0 dB): cada camada e normalizada no proprio pico antes
# (o ruido filtrado perde muita energia no filtro; sem isso a subida sumia: -40 dBFS no 1o teste). Botoes de ajuste aqui.
NIVEL = {"subida_ruido": -6.0, "subida_sub": -9.0, "cluster": -10.0, "tique": -12.0, "lub": 0.0, "estalo": -6.0,
         "sino": -8.0, "dub": -2.0, "vazio": -16.0, "zumbido": -22.0, "reverb": -10.0}


def db(x):
    return 10.0 ** (x / 20.0)


def clamp01(x):
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


def idx(t):
    return max(0, min(int(round(t * SR)), int(DUR * SR)))


class Biquad:
    """RBJ cookbook, forma direta transposta II."""

    def __init__(self, tipo, f, q):
        self.tipo, self.z1, self.z2 = tipo, 0.0, 0.0
        self.set(f, q)

    def set(self, f, q):
        f = min(max(f, 10.0), SR * 0.45)
        w0 = 2.0 * math.pi * f / SR
        cw, sw = math.cos(w0), math.sin(w0)
        al = sw / (2.0 * q)
        if self.tipo == "lp":
            b0, b1, b2 = (1 - cw) / 2, 1 - cw, (1 - cw) / 2
        elif self.tipo == "hp":
            b0, b1, b2 = (1 + cw) / 2, -(1 + cw), (1 + cw) / 2
        else:  # "bp", ganho 0 dB no pico
            b0, b1, b2 = al, 0.0, -al
        a0, a1, a2 = 1 + al, -2 * cw, 1 - al
        self.b0, self.b1, self.b2, self.a1, self.a2 = b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0

    def run(self, x):
        y = self.b0 * x + self.z1
        self.z1 = self.b1 * x - self.a1 * y + self.z2
        self.z2 = self.b2 * x - self.a2 * y
        return y


def novo(n=None):
    return [0.0] * (n if n is not None else int(DUR * SR))


def somar(dst, src, i0, g=1.0):
    n = min(len(src), len(dst) - i0)
    for k in range(n):
        dst[i0 + k] += src[k] * g


def norm(x):
    """pico 1.0 (a camada entra no mix pelo NIVEL, em dB relativos ao golpe)."""
    p = max(abs(v) for v in x) or 1.0
    return [v / p for v in x]


# ------------------------------------------------------------------ camadas
def subida_ruido(rng):
    """0 -> T_CORTE: 'retrocesso' - ruido em banda que sobe (250 -> 2400 Hz) e cresce acelerando; corta seco."""
    n = idx(T_CORTE)
    out = novo(n)
    bp1, bp2, lp = Biquad("bp", 250, 1.6), Biquad("bp", 500, 2.5), Biquad("lp", 180, 0.7)
    for i in range(n):
        u = i / n
        if i % 32 == 0:
            fc = 250.0 * (2400.0 / 250.0) ** (u ** 1.3)
            bp1.set(fc, 1.6)
            bp2.set(fc * 1.52, 2.5)
        x = rng.uniform(-1.0, 1.0)
        y = bp1.run(x) + 0.55 * bp2.run(x) + 0.8 * lp.run(x)
        env = db(-46.0 + 38.0 * u ** 2.2)
        fim = clamp01((n - i) / (0.002 * SR))
        out[i] = y * env * fim
    return out


def subida_sub():
    """0 -> T_CORTE: sub subindo 30 -> 58 Hz, crescendo."""
    n = idx(T_CORTE)
    out, ph = novo(n), 0.0
    for i in range(n):
        u = i / n
        f = 30.0 + 28.0 * u ** 1.5
        ph += 2 * math.pi * f / SR
        env = db(-34.0 + 24.0 * u) * clamp01(i / (0.02 * SR)) * clamp01((n - i) / (0.003 * SR))
        out[i] = math.sin(ph) * env
    return out


def cluster():
    """0,04 -> T_CORTE: cluster dissonante (Re, Re#, Sol#, La: segundas menores + tritono) subindo 1 semitom, com tremolo
    acelerando (5 -> 16 Hz, pulso disparando) e passa-baixa abrindo 500 -> 2600 Hz."""
    i0, n = idx(0.04), idx(T_CORTE) - idx(0.04)
    out = novo(n)
    vozes = [146.83, 155.56, 207.65, 220.0]
    fases = [[0.0] * 6 for _ in vozes]
    ph_trem = 0.0
    lp = Biquad("lp", 500, 0.9)
    for i in range(n):
        u = i / n
        if i % 32 == 0:
            lp.set(500.0 + 2100.0 * u ** 1.4, 0.9)
        mult = 2.0 ** (u / 12.0)
        s = 0.0
        for v, f0 in enumerate(vozes):
            f = f0 * mult * (1.0 + (0.002 if v % 2 else -0.002))
            for h in range(6):
                fases[v][h] += 2 * math.pi * f * (h + 1) / SR
                s += math.sin(fases[v][h]) / (h + 1)
        ph_trem += 2 * math.pi * (5.0 + 11.0 * u * u) / SR
        trem = 1.0 - 0.65 * (0.5 + 0.5 * math.sin(ph_trem))
        env = db(-40.0 + 26.0 * u ** 1.6) * clamp01(i / (0.03 * SR)) * clamp01((n - i) / (0.002 * SR))
        out[i] = lp.run(s * 0.18) * trem * env
    return i0, out


def tiques(rng):
    """Relogio voltando: tique-taques INVERTIDOS (ataque crescente, fim seco) acelerando ate o corte. Estereo alternado."""
    L, R = novo(idx(T_CORTE)), novo(idx(T_CORTE))
    tempos = [T_CORTE - 0.52 * 0.62 ** k for k in range(9)]
    for k, t in enumerate(tempos):
        if t < 0.01:
            continue
        dur = 0.014
        f = 2400.0 if k % 2 == 0 else 1850.0
        bp = Biquad("bp", f, 7.0)
        g = db(-10.0 + 10.0 * k / len(tempos))
        n = int(dur * SR)
        i0 = idx(t) - n
        ph = 0.0
        for j in range(n):
            u = j / n                       # invertido: cresce ate o fim
            ph += 2 * math.pi * f * 1.37 / SR
            x = bp.run(rng.uniform(-1, 1)) * 2.2 + math.sin(ph) * 0.5
            y = x * (u ** 3) * g
            if 0 <= i0 + j < len(L):
                (L if k % 2 == 0 else R)[i0 + j] += y
                (R if k % 2 == 0 else L)[i0 + j] += y * 0.45
    return L, R


def batida(f_ini, f_fim, tau_pitch, tau_amp, drive, dur):
    """Batida de coracao/impacto: seno com queda rapida de pitch, saturado."""
    n = int(dur * SR)
    out, ph = novo(n), 0.0
    k = math.tanh(drive)
    for i in range(n):
        t = i / SR
        f = f_fim + (f_ini - f_fim) * math.exp(-t / tau_pitch)
        ph += 2 * math.pi * f / SR
        env = min(1.0, t / 0.002) * math.exp(-t / tau_amp)
        x = (math.sin(ph) + 0.25 * math.sin(2 * ph)) * env
        out[i] = math.tanh(drive * x) / k
    return out


def estalo(rng):
    n = int(0.045 * SR)
    out = novo(n)
    hp, bp = Biquad("hp", 700, 0.7), Biquad("bp", 2500, 0.7)
    for i in range(n):
        t = i / SR
        x = rng.uniform(-1, 1) * math.exp(-t / 0.006)
        out[i] = bp.run(hp.run(x)) * 2.0 + (1.0 if i == 0 else 0.0)
    return out


def sino():
    """Parciais inarmonicas de sino/gongo (Do#2), cada uma em par desafinado (batimento), decaimento por parcial."""
    f0 = 69.3
    razoes = [1.0, 2.0, 2.76, 4.07, 5.40, 6.94, 8.93]
    amps = [1.0, 0.40, 0.65, 0.30, 0.38, 0.20, 0.14]
    n = int((DUR - T_IMP) * SR)
    out = novo(n)
    for k, (r, a) in enumerate(zip(razoes, amps)):
        tau = 2.6 / (1.0 + 0.35 * k)
        for det in (-0.25, 0.25):
            ph = 0.0
            f = f0 * r + det
            for i in range(n):
                t = i / SR
                ph += 2 * math.pi * f * (1.0 - 0.03 * math.exp(-t / 0.08)) / SR
                out[i] += math.sin(ph) * a * 0.5 * math.exp(-t / tau) * min(1.0, t / 0.004)
    return out


def vazio():
    """O que fica depois do golpe: grave (36 + 54 Hz) sumindo."""
    n = int((DUR - T_IMP) * SR)
    out = novo(n)
    p1 = p2 = 0.0
    for i in range(n):
        t = i / SR
        p1 += 2 * math.pi * 36.0 / SR
        p2 += 2 * math.pi * 54.0 / SR
        out[i] = (math.sin(p1) + 0.5 * math.sin(p2)) * math.exp(-t / 1.4) * min(1.0, t / 0.02)
    return out


def zumbido():
    """Zumbido (tinnitus do TCE): 3740 + 3747 Hz (batimento de 7 Hz), sobe em 0,35 s, segura, some ate o fim."""
    t0 = T_IMP + 0.08
    n = int((DUR - t0) * SR)
    out = novo(n)
    p1 = p2 = 0.0
    for i in range(n):
        t = i / SR
        vib = 1.0 + 0.0012 * math.sin(2 * math.pi * 0.25 * t)
        p1 += 2 * math.pi * 3740.0 * vib / SR
        p2 += 2 * math.pi * 3747.0 * vib / SR
        if t < 0.35:
            env = t / 0.35
        elif t < 1.4:
            env = 1.0
        else:
            env = math.exp(-(t - 1.4) / 0.9)
        out[i] = (math.sin(p1) + math.sin(p2)) * 0.5 * env
    return t0, out


# ------------------------------------------------------------------ reverb (Freeverb)
def freeverb(x, sala=0.9, amort=0.3, largura=1.0):
    esc = SR / 44100.0
    combs = [1116, 1188, 1277, 1356, 1422, 1491, 1557, 1617]
    aps = [556, 441, 341, 225]
    fb, d1 = sala * 0.28 + 0.7, amort * 0.4
    d2 = 1.0 - d1
    saidas = []
    for spread in (0, 23):
        cb = [[0.0] * int((c + spread) * esc) for c in combs]
        ci = [0] * len(combs)
        fs = [0.0] * len(combs)
        ab = [[0.0] * int((a + spread) * esc) for a in aps]
        ai = [0] * len(aps)
        y = novo(len(x))
        for i in range(len(x)):
            inp = x[i] * 0.015
            acc = 0.0
            for c in range(8):
                buf, j = cb[c], ci[c]
                o = buf[j]
                fs[c] = o * d2 + fs[c] * d1
                buf[j] = inp + fs[c] * fb
                ci[c] = j + 1 if j + 1 < len(buf) else 0
                acc += o
            for a in range(4):
                buf, j = ab[a], ai[a]
                bo = buf[j]
                buf[j] = acc + bo * 0.5
                acc = bo - acc
                ai[a] = j + 1 if j + 1 < len(buf) else 0
            y[i] = acc
        saidas.append(y)
    wl, wr = saidas
    g1, g2 = (largura / 2 + 0.5), (1 - largura) / 2
    return [wl[i] * g1 + wr[i] * g2 for i in range(len(x))], [wr[i] * g1 + wl[i] * g2 for i in range(len(x))]


# ------------------------------------------------------------------ mix
def sintetizar():
    rng = random.Random(SEMENTE)
    N = int(DUR * SR)
    L, R, envio = novo(N), novo(N), novo(N)
    s = norm(subida_ruido(rng))
    atraso = int(0.0004 * SR)  # 0,4 ms no canal direito: largura sem mudar o timbre
    somar(L, s, 0, db(NIVEL["subida_ruido"]))
    somar(R, s, atraso, db(NIVEL["subida_ruido"]))
    sub = norm(subida_sub())
    somar(L, sub, 0, db(NIVEL["subida_sub"]))
    somar(R, sub, 0, db(NIVEL["subida_sub"]))
    i0, cl = cluster()
    cl = norm(cl)
    somar(L, cl, i0, db(NIVEL["cluster"]))
    somar(R, cl, i0 + atraso * 2, db(NIVEL["cluster"]))
    tl, tr = tiques(rng)
    pt = max(max(abs(v) for v in tl), max(abs(v) for v in tr)) or 1.0
    somar(L, tl, 0, db(NIVEL["tique"]) / pt)
    somar(R, tr, 0, db(NIVEL["tique"]) / pt)
    ii = idx(T_IMP)
    lub = norm(batida(130.0, 36.0, 0.05, 0.32, 2.6, 1.8))
    dub = norm(batida(110.0, 34.0, 0.045, 0.26, 2.2, 1.6))
    est, sin_, vaz = norm(estalo(rng)), norm(sino()), norm(vazio())
    for dst in (L, R, envio):
        somar(dst, lub, ii, db(NIVEL["lub"]))
        somar(dst, dub, idx(T_IMP + 0.30), db(NIVEL["dub"]))
        somar(dst, est, ii, db(NIVEL["estalo"]))
        somar(dst, sin_, ii, db(NIVEL["sino"]))
    somar(L, vaz, ii, db(NIVEL["vazio"]))
    somar(R, vaz, ii, db(NIVEL["vazio"]))
    tz, zb = zumbido()
    zb = norm(zb)
    somar(L, zb, idx(tz), db(NIVEL["zumbido"]))
    somar(R, zb, idx(tz) + atraso, db(NIVEL["zumbido"]))
    print("reverb...")
    wl, wr = freeverb(envio)
    pw = max(max(abs(v) for v in wl), max(abs(v) for v in wr)) or 1.0
    g = db(NIVEL["reverb"]) / pw
    for i in range(N):
        L[i] += wl[i] * g
        R[i] += wr[i] * g
    # master: passa-alta 22 Hz, saturacao suave, normaliza, fade final
    for ch in (L, R):
        hp = Biquad("hp", 22.0, 0.707)
        for i in range(N):
            ch[i] = hp.run(ch[i])
    pico = max(max(abs(v) for v in L), max(abs(v) for v in R)) or 1.0
    k = math.tanh(1.3)
    for ch in (L, R):
        for i in range(N):
            ch[i] = math.tanh(1.3 * ch[i] / pico) / k
    alvo = db(PICO_DBFS)
    pico = max(max(abs(v) for v in L), max(abs(v) for v in R)) or 1.0
    nf = int(0.35 * SR)
    for ch in (L, R):
        for i in range(N):
            ch[i] *= alvo / pico
            if i >= N - nf:
                ch[i] *= (N - i) / nf
    return L, R


def grava_wav(L, R, caminho):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    a = array("h")
    for l, r in zip(L, R):
        a.append(int(max(-1.0, min(1.0, l)) * 32767))
        a.append(int(max(-1.0, min(1.0, r)) * 32767))
    with wave.open(caminho, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(a.tobytes())


# ------------------------------------------------------------------ analise (evidencia, sem ouvir)
def fft(x):
    n = len(x)
    j = 0
    a = [complex(v, 0.0) for v in x]
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j |= bit
        if i < j:
            a[i], a[j] = a[j], a[i]
    m = 2
    while m <= n:
        wm = complex(math.cos(-2 * math.pi / m), math.sin(-2 * math.pi / m))
        for k in range(0, n, m):
            w = 1.0 + 0j
            for q in range(m // 2):
                t = w * a[k + q + m // 2]
                u = a[k + q]
                a[k + q] = u + t
                a[k + q + m // 2] = u - t
                w *= wm
        m <<= 1
    return a


def png(caminho, largura, altura, pix):
    raw = b"".join(b"\x00" + bytes(pix[y * largura * 3:(y + 1) * largura * 3]) for y in range(altura))
    def chunk(tag, dados):
        c = struct.pack(">I", len(dados)) + tag + dados
        return c + struct.pack(">I", zlib.crc32(tag + dados) & 0xFFFFFFFF)
    with open(caminho, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", largura, altura, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def cor(v):
    """0..1 -> preto, roxo, laranja, amarelo."""
    pts = [(0.0, (0, 0, 0)), (0.35, (70, 10, 110)), (0.65, (220, 70, 30)), (0.85, (250, 170, 30)), (1.0, (255, 255, 200))]
    for (a, ca), (b, cb) in zip(pts, pts[1:]):
        if v <= b:
            u = (v - a) / (b - a) if b > a else 0
            return tuple(int(ca[i] + (cb[i] - ca[i]) * u) for i in range(3))
    return pts[-1][1]


def analisar(L, R, pasta):
    os.makedirs(pasta, exist_ok=True)
    N = len(L)
    mono = [(l + r) * 0.5 for l, r in zip(L, R)]
    pico = max(max(abs(v) for v in L), max(abs(v) for v in R))
    dc = sum(mono) / N
    jan = int(0.05 * SR)
    rms = []
    for i in range(0, N - jan + 1, jan):
        e = sum(v * v for v in mono[i:i + jan]) / jan
        rms.append(10 * math.log10(e + 1e-12))
    ataque = None
    for k in range(1, len(rms)):
        if k * 0.05 > 0.3 and rms[k] - rms[k - 1] > 6.0 and ataque is None:
            ataque = k * 0.05
    linhas = ["pico dBFS: %.2f" % (20 * math.log10(pico)), "DC: %.6f" % dc, "duracao: %.2f s, %d Hz, estereo 16 bit" % (N / SR, SR),
              "ataque detectado (janela de 50 ms com salto > 6 dB): %s s (alvo T_IMP=%.2f)" % (ataque, T_IMP),
              "RMS por 50 ms (dBFS):"]
    for k in range(0, len(rms), 2):
        linhas.append("  %4.2f s  %6.1f  %s" % (k * 0.05, rms[k], "#" * max(0, int((rms[k] + 60) / 2))))
    # espectrograma: N=512 (Hann), salto 10 ms, 220 linhas em escala log 25 Hz..16 kHz
    nfft, salto = 512, int(0.01 * SR)
    han = [0.5 - 0.5 * math.cos(2 * math.pi * i / (nfft - 1)) for i in range(nfft)]
    cols = []
    for i in range(0, N - nfft, salto):
        esp = fft([mono[i + j] * han[j] for j in range(nfft)])
        cols.append([abs(esp[b]) for b in range(nfft // 2)])
    H = 220
    fmin, fmax = 25.0, 16000.0
    W = len(cols)
    mat = []
    for y in range(H):
        f = fmin * (fmax / fmin) ** (1 - y / (H - 1))
        b = min(nfft // 2 - 1, max(1, int(round(f * nfft / SR))))
        mat.append([20 * math.log10(c[b] + 1e-9) for c in cols])
    top = max(max(r) for r in mat)
    pix = bytearray()
    x_imp, x_p1, x_p2 = int(T_IMP / 0.01), int(0.58 / 0.01), int(0.62 / 0.01)
    for y in range(H):
        for x in range(W):
            if x in (x_p1, x_p2):
                pix += bytes((60, 160, 255))
            elif x == x_imp:
                pix += bytes((255, 255, 255))
            else:
                pix += bytes(cor(clamp01((mat[y][x] - (top - 80.0)) / 80.0)))
    png(os.path.join(pasta, "SW_LuxRetorno_espectrograma.png"), W, H, pix)
    txt = os.path.join(pasta, "SW_LuxRetorno_analise.txt")
    with open(txt, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\nespectrograma: eixo x = 10 ms/pixel; y = 16 kHz (topo) .. 25 Hz (base), log; linha branca = impacto; "
                "linhas azuis = quadro preto 0,58-0,62 s\n")
    print("\n".join(linhas[:4]))
    return txt


# ------------------------------------------------------------------ editor
def _editor():
    import unreal
    EAL = unreal.EditorAssetLibrary
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

    def w(*a):
        unreal.log("[LUX retorno] " + " ".join(str(x) for x in a))

    def mgr():
        m = [a for a in eas.get_all_level_actors() if a.get_actor_label() == "LOOP_Manager"]
        if len(m) != 1:
            raise RuntimeError("esperava 1 LOOP_Manager (%d)" % len(m))
        return m[0]

    def verificar():
        f = []
        if not EAL.does_asset_exist(ASSET):
            return ["asset %s ausente" % ASSET]
        s = EAL.load_asset(ASSET)
        if abs(s.get_editor_property("duration") - DUR) > 0.05:
            f.append("duracao %.2f != %.2f" % (s.get_editor_property("duration"), DUR))
        if s.get_editor_property("looping"):
            f.append("som em loop")
        if mgr().get_editor_property("SomTroca") != s:
            f.append("LOOP_Manager.SomTroca nao aponta para %s" % ASSET)
        w("verificar:", ("FAIL %s" % f) if f else "PASS", "| dur %.2f s, SomTroca=%s" % (s.get_editor_property("duration"), mgr().get_editor_property("SomTroca")))
        return f

    def instalar():
        if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():
            raise RuntimeError("feche o PIE")
        U = unreal.EditorLoadingAndSavingUtils
        sujos = [p.get_name() for p in U.get_dirty_map_packages()] + [p.get_name() for p in U.get_dirty_content_packages()]
        if sujos:
            raise RuntimeError("ha pacotes nao salvos antes de comecar: %s" % sujos)
        if not os.path.exists(WAV):
            raise RuntimeError("rode 'sintetizar' antes (falta %s)" % WAV)
        t = unreal.AssetImportTask()
        for k, v in (("filename", WAV), ("destination_path", ASSET_DIR), ("destination_name", "SW_LuxRetorno"), ("replace_existing", True),
                     ("automated", True), ("save", True)):
            t.set_editor_property(k, v)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
        s = EAL.load_asset(ASSET)
        if not s:
            raise RuntimeError("importacao falhou")
        s.set_editor_property("looping", False)
        EAL.save_loaded_asset(s, False)
        m = mgr()
        m.set_editor_property("SomTroca", s)
        mapa = [p for p in U.get_dirty_map_packages() if p.get_name() == "/Game/Masion/Mapa_B"]
        f = verificar()
        if f:
            raise RuntimeError("verificar FAIL (mapa nao salvo): %s" % f)
        if mapa:
            w("salvo Mapa_B", U.save_packages(mapa, True))

    def desfazer():
        m = mgr()
        m.set_editor_property("SomTroca", None)
        U = unreal.EditorLoadingAndSavingUtils
        U.save_packages([p for p in U.get_dirty_map_packages() if p.get_name() == "/Game/Masion/Mapa_B"], True)
        w("SomTroca vazio; o asset %s continua (apague no Content Browser se quiser)" % ASSET)

    def sondar():
        m = mgr()
        w("SomTroca atual:", m.get_editor_property("SomTroca"), "| WAV:", WAV, os.path.exists(WAV), "| asset existe:", EAL.does_asset_exist(ASSET))

    return {"sondar": sondar, "instalar": instalar, "verificar": verificar, "desfazer": desfazer}


def main():
    modo = next((a for a in sys.argv[1:] if a in ("sintetizar", "sondar", "instalar", "verificar", "desfazer")), "sondar")
    if modo == "sintetizar":
        L, R = sintetizar()
        grava_wav(L, R, WAV)
        print("WAV:", WAV)
        print("analise:", analisar(L, R, ANALISE_DIR))
        return
    try:
        _editor()[modo]()
    except Exception as ex:
        import unreal
        unreal.log_error("[LUX retorno] ABORTADO: %s" % ex)


if __name__ == "__main__":
    main()
