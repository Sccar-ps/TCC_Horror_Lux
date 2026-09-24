# Iluminação, exposição e Lumen no TCC_Horror_Lux (UE 5.8.3)

Este guia cobre o aviso *"Cached lighting in Lumen and real-time sky capture lighting is going to be clipped"* e as otimizações de iluminação aplicadas no `Mapa_B`. Todos os números foram medidos no editor desta máquina (Ryzen 5 5500X3D · RTX 5060 8 GB · 16 GB), no dia 24/09/2026.

Os scripts ficam em `Tools/Lighting/`.

---

## 0. Resumo do que mudou

| Onde | Mudança | Estado |
|---|---|---|
| `Config/DefaultEngine.ini` → `[SystemSettings]` | `r.EyeAdaptation.CachedLightingPreExposure=1` (padrão da engine: 4) | **Gravado no disco**. Vale no próximo boot do editor; nesta sessão já foi aplicado pelo console |
| `Config/DefaultEngine.ini` → `[/Script/Engine.RendererSettings]` | Removida a linha duplicada `ExtendDefaultLuminanceRange=true` | Gravado |
| `Mapa_B` | Novo `PPV_Global` (Post Process Volume *Unbound*), com exposição limitada e distâncias do Lumen ajustadas à casa | **Mapa não salvo**: revise e salve com Ctrl+S |
| `Mapa_B` | 7 luzes Stationary → **Movable** | Mapa não salvo |
| `Mapa_B` | `DirectionalLight`: *Distance Field Shadows* desligado | Mapa não salvo |

> **Atenção ao salvar:** o `Mapa_B` já tinha alterações suas pendentes antes (o editor mostrava "3 Unsaved"). O Ctrl+S grava tudo junto. Para desfazer só as minhas mudanças, use Ctrl+Z: cada script abriu uma transação própria ("LUX: PPV_Global" e "LUX: luzes Stationary -> Movable").

---

## 1. O aviso: o que é e por que aparece em ambiente escuro

### 1.1 A causa

A 5.8 introduziu a cvar `r.EyeAdaptation.CachedLightingPreExposure`. A descrição oficial é *"Fixed pre-exposure offset in EV units for cached lighting. Adjust it per project to cover used exposure range."*

Em linguagem simples:

- **Pré-exposição** é multiplicar a luz pela exposição da câmera antes de gravá-la, para caber em formatos de pouca precisão (16 bits, R11G11B10). Na cena principal ela acompanha a exposição da câmera a cada frame.
- A **luz em cache** não pode fazer isso, porque vive vários frames. São três caches:
  - o *surface cache* do Lumen;
  - o *radiance cache* do Lumen;
  - o cubemap do SkyLight em *Real Time Capture*.

  Por isso, a luz em cache é gravada com uma pré-exposição **fixa**, dada pela cvar.
- Um valor fixo só representa bem uma faixa de exposições. Fora dela, a luz em cache perde precisão ou satura. Na prática aparecem GI manchada ou preta, *banding* e ruído em áreas escuras. É isso que o aviso chama de *clipped*.

### 1.2 A fórmula (medida no editor)

Testei a cvar em quatro valores no `Mapa_B`. O aviso sempre imprimiu a faixa segura:

| `CachedLightingPreExposure` | Faixa segura impressa |
|---|---|
| 4 (padrão) | [−8, 12] |
| 10 | [−2, 18] |
| 16 | [4, 24] |
| 30 | [4, 24] (a engine limita o valor a 16) |

**Faixa segura = [P − 12, P + 8]**, em que P é o valor da cvar.

O número *Exposure* do aviso **inclui o Exposure Compensation**. Com Min = Max EV100 = −6, o aviso mostrou −6,0 com compensação 0, e −8,0 com compensação +2. Então:

```
Exposure (do aviso) = EV100 da câmera − Exposure Compensation
```

### 1.3 Por que o Mapa_B disparou

| Fator | Valor encontrado |
|---|---|
| PostProcessVolume no mapa | nenhum |
| Câmera do `BP_Player_Cowboy` | *Post Process* sem nenhum override. Valem os padrões do projeto: histograma, Min EV100 −10, Max EV100 20, Exposure Compensation 1,0 |
| Luzes | Todas muito fracas: RectLights de 0,6 a 1,3 cd, PointLight de 8 cd, sol a 10 lux |
| Resultado | O olho virtual adaptou até **Exposure −8,5**, fora da faixa [−8, 12] |

Com o padrão de fábrica, a exposição efetiva do projeto podia chegar a −10 − 1 = **−11**. Mesmo um ajuste só na cvar para 2 ([−10, 10]) não cobriria o pior caso.

---

## 2. A correção aplicada: duas camadas

### 2.1 Camada do projeto: mover a faixa segura para baixo

`Config/DefaultEngine.ini`:

```ini
[SystemSettings]
r.EyeAdaptation.CachedLightingPreExposure=1
```

- **Faixa resultante:** [−11, 9].
- **Por que em `[SystemSettings]` e não em `[/Script/Engine.RendererSettings]`:** essa seção a UI de Configurações do Projeto não reescreve, então o valor não some quando alguém mexer em Editar (*Edit*) → Configurações do Projeto (*Project Settings*) → Rendering.
- **Custo:** zero. É só a escala com que os caches são gravados.
- **Troca:** o teto cai de 12 para 9. Uma cena de dia claro (EV100 12–15) passaria a disparar o aviso para o lado claro. Se a abertura na floresta for de dia, veja a seção 5.6.

### 2.2 Camada do mapa: limitar o olho virtual (`PPV_Global`)

Criado pelo `apply_ppv_global.py`. Para conferir ou ajustar à mão: selecione `PPV_Global` no Organizador (*Outliner*) → Detalhes (*Details*).

| Seção nos Detalhes | Propriedade | Valor | Por quê |
|---|---|---|---|
| Post Process Volume Settings | `Infinite Extent (Unbound)` | ✔ | Vale para o mapa inteiro |
| Lens → Exposure | `Metering Mode` | Auto Exposure Histogram | Mantém a adaptação do olho, que é parte da fotofobia |
| Lens → Exposure | `Exposure Compensation` | 1,0 | Igual ao valor efetivo que o projeto já usava (`r.DefaultFeature.AutoExposure.Bias=1`), para o visual não mudar |
| Lens → Exposure | `Min EV100` | **−8** | O olho virtual não "enxerga" além disso: o escuro continua escuro |
| Lens → Exposure | `Max EV100` | **8** | Lâmpada ou lanterna na cara não leva a exposição para fora da faixa |
| Lens → Exposure → Avançado | `Histogram Min EV100` / `Max EV100` | −10 / 10 | Os 64 *buckets* do histograma passam a cobrir 20 EV em vez de 30: medição mais fina |
| Global Illumination → Lumen Global Illumination | `Lumen Scene View Distance` | **7000** cm (padrão 20000) | A casa mede 35 × 42 × 5 m (diagonal de 55 m, calculada pelo script). Não precisa de uma cena Lumen de 200 m |
| idem | `Max Trace Distance` | **7000** cm (padrão 20000) | Mesmo motivo. Abaixo da diagonal da casa, a luz "vazaria" em cômodos grandes |
| idem | `Skylight Leaking` | 0 | Não há SkyLight; fica explícito para ninguém ligar sem querer |

**Exposição efetiva resultante:** [−8 − 1, 8 − 1] = **[−9, 7]**, dentro de [−11, 9], com **2 EV de folga de cada lado**. Essa folga existe para os efeitos de fotofobia (seção 6).

**Visual:** no ponto em que o aviso aparecia (−8,5), a exposição é a mesma. Só os cantos mais escuros da casa, que antes o olho clareava até −10/−11, agora ficam até 2 EV mais escuros. Isso também reduz o ruído do Lumen, que antes era amplificado nesses cantos (o granulado visível na parede).

> **Ajuste artístico:** para um terror mais "físico", suba o `Min EV100` para −6 ou −5. Uma sala de verdade à luz da lua fica em torno de EV100 −4 a −7. O escuro vira preto de verdade e a lanterna passa a ser obrigatória. A faixa segura continua respeitada.

### 2.3 A regra para todo PPV e câmera daqui para frente

```
Min EV100 − Exposure Compensation  ≥  −11      (P − 12)
Max EV100 − Exposure Compensation  ≤    9      (P + 8)
```

Vale também para a câmera, se um dia você ligar *overrides* de exposição no `FirstPersonCamera`. O *post process* da câmera é aplicado depois dos volumes e ganha deles.

### 2.4 Como medir a exposição em qualquer ponto (truque de diagnóstico)

O aviso imprime a exposição atual. Para lê-lo em qualquer situação, force-o de propósito:

1. No console do PIE, rode `r.EyeAdaptation.CachedLightingPreExposure 16`. A faixa vira [4, 24] e o aviso aparece em todo lugar escuro, com `Exposure: X`.
2. Ande pela casa, ligue e desligue a lanterna e anote os valores.
3. Volte com `r.EyeAdaptation.CachedLightingPreExposure 1`.

Medido depois da correção: **−6,3** olhando para a janela, **sem aviso** em nenhum dos pontos testados.

---

## 3. Otimizações aplicadas no Mapa_B e o ganho medido

### 3.1 O que foi feito

| Mudança | Script | Motivo |
|---|---|---|
| 7 luzes Stationary → Movable | `apply_lights_movable.py` | Projeto 100% Lumen, sem lightmap construído. A doc de VSM diz que Stationary com VSM já é avaliada "the same as Movable lights". Stationary só acrescentava a dependência de build (o aviso "LIGHTING NEEDS TO BE REBUILT") e o limite de 4 Stationary sobrepostas. As luzes que piscam (fotofobia) continuam podendo mudar intensidade e cor em runtime |
| `DirectionalLight` → Distance Field Shadows desligado | idem | Com VSM ligado, os *clipmaps* já cobrem a distância. A doc diz que DF Shadows "can be used in tandem" com VSM, mas numa casa não há sombra distante a ganhar. Além disso, o SDF é justamente o que vaza em parede fina |
| `PPV_Global` (seção 2.2) | `apply_ppv_global.py` | Exposição e distâncias do Lumen |

### 3.2 `stat gpu` antes e depois

Mesma câmera do viewport do editor, 1263×768 a 89% de resolução:

| Passo | Antes (ms) | Depois (ms) |
|---|---|---|
| **GPU Time (`stat unit`)** | **4,77** | **4,59** |
| Graphics Queue Total | 4,37 | 4,21 |
| Lights | 1,13 | 0,92 |
| Shadow Projection | 0,45 | 0,27 |
| DistanceField Shadows | 0,24 | **0** |
| LumenScreenProbeGather (compute) | 1,10 | 1,17 (ruído) |

**PIE depois das mudanças:** GPU 4,19 ms a 1235×750, VRAM 4,45 GB de 6,96 GB disponíveis, sem o aviso de clipping, sem o "LIGHTING NEEDS TO BE REBUILT".

**Leitura honesta dos números:**

- O ganho de GPU é pequeno (~4%) porque a cena é pequena: 36 StaticMeshComponents, 24 malhas únicas e 2 com Nanite. A GPU não é o gargalo aqui.
- **Projeção para tela cheia:** a 1080p (2,1 MP, 87% de resolução) a GPU fica na faixa de ~7 ms, e a 1440p na faixa de ~11 ms. Os dois cabem em 60 fps na RTX 5060.
- **O gargalo aparente no editor é a CPU:** Game ≈ 10–13 ms e Draw ≈ 8–9 ms, com o overlay "PROFILING WITH AI LOGGING ON!". No editor isso inclui o Slate e o próprio editor. Para saber o custo real, meça em **Standalone** ou num build empacotado (seção 4).

---

## 4. Metodologia de profiling: o roteiro

A regra é medir, mudar uma coisa só e medir de novo, sempre na mesma câmera.

### 4.1 Onde medir

| Onde | Como | Serve para |
|---|---|---|
| Viewport do editor | Console: `stat unit`, `stat gpu` | Comparação rápida A/B da GPU (câmera parada) |
| **Standalone** | Seta ao lado do Play → *Standalone Game*. Em Editar (*Edit*) → Preferências do Editor (*Editor Preferences*) → Level Editor → Play → *Additional Launch Parameters*: `-NoAILogging` | Números de CPU sem o overhead do editor |
| Build Development | Plataformas (*Platforms*) → Windows → *Package Project* | O número que vale para o TCC |

### 4.2 Comandos de console

| Comando | O que mostra |
|---|---|
| `stat unit` / `stat unitgraph` | Frame, Game (CPU lógica), Draw (render thread), GPU, VRAM. O maior valor é o gargalo |
| `stat gpu` | Tempo por *pass*: Lumen, Lights, Shadow Depths, Postprocessing, TSR |
| `ProfileGPU` (ou Ctrl+Shift+,) | Árvore completa de um frame, com cada draw e cada *dispatch* |
| `stat scenerendering` | Draw calls e primitivas |
| `stat streaming` | Pool de texturas: *Wanted* × *Pool size*. Se passar do pool, as texturas borram |
| `stat rhi` | Memória de render targets e texturas na VRAM |
| `r.ScreenPercentage 50` | Se a GPU cair quase pela metade, o custo é por pixel (Lumen, luzes, *post*). Se não cair, é geometria ou sombra |

### 4.3 Modos de visualização

No viewport → menu **Lit** → **Visualizar** (*Optimization Viewmodes* / *Lumen*):

- **Light Complexity:** quantas luzes afetam cada pixel. As 7 luzes do `Mapa_B` usam `Attenuation Radius` = 1000 (o padrão). Reduzir o raio ao tamanho do cômodo é a otimização de luz mais barata que existe. Não mexi porque muda o visual; ajuste olhando esse modo.
- **Lumen → Lumen Scene:** o que o Lumen "enxerga". Áreas rosa não têm *surface cache*. A doc manda subir `Max Lumen Mesh Cards` na malha ou dividir a malha.
- **Lumen → Surface Cache:** a cobertura dos cards.
- **Shader Complexity & Quads:** o custo de material por pixel.
- **Virtual Shadow Map → Cached Page:** as invalidações de cache das sombras. Luz ou malha que se move invalida o cache.

### 4.4 Unreal Insights (CPU, GPU e memória num mesmo trace)

1. Na barra de status, abra **Trace** (canto inferior) → *Channels* e ligue `cpu`, `gpu`, `frame`, `bookmark` e `memory`. Alternativa: em Standalone, `-trace=default,gpu,memory -statnamedevents -NoAILogging`.
2. Jogue 30–60 s pelo trecho que quer medir e pare o trace.
3. Abra `Engine/Binaries/Win64/UnrealInsights.exe` e escolha a sessão.
   - **Timing Insights:** clique no frame mais lento e veja o que domina na *Game Thread* (Tick de Blueprint? AnimGraph?) e na GPU.
   - **Memory Insights:** use o *LLM* (`-llm`) e confira *Textures*, *Meshes*, *Lumen* e *RenderTargets* contra os 16 GB de RAM.

### 4.5 Orçamento de VRAM (RTX 5060, 8 GB)

- **Medido no PIE:** 4,45 GB usados de 6,96 GB disponíveis, com o editor aberto (a UI do editor come uma parte).
- **Maiores consumidores neste projeto:**
  - pool de texturas (`r.Streaming.PoolSize` = 800 MB);
  - *surface cache* do Lumen (atlas 3584²);
  - páginas de VSM (`r.Shadow.Virtual.MaxPhysicalPages` = 2048);
  - streaming do Nanite;
  - render targets + histórico do TSR.
- **O que controla cada um:**
  - Texturas: o teto de 2048 do `optimize_textures.py` (já aplicado).
  - Lumen: a `Lumen Scene View Distance` (aplicada, seção 2.2).
  - VSM: sombra só em luzes que precisam (seção 5.4).

---

## 5. Recomendações que NÃO apliquei (dependem de decisão sua ou de reiniciar o editor)

### 5.1 Desligar `Allow Static Lighting` (recomendado)

- **Onde:** Editar (*Edit*) → Configurações do Projeto (*Project Settings*) → Engine → Rendering → busque **Allow Static Lighting** → desmarque.
- **Por quê:** a doc do Lumen recomenda desligar para projetos só com Lumen. Remove as permutações de shader de lightmap (menos memória de shader e compilações mais rápidas no futuro) e acaba de vez com o "LIGHTING NEEDS TO BE REBUILT", que ainda aparecia com "1 unbuilt object" mesmo com `DumpUnbuiltLightInteractions` = 0.
- **É também pré-requisito do First Person Rendering nativo** (ver `claude/MixamoFP_setup.md`, seção 9).
- **Custo:** reinicia o editor e **recompila todos os materiais**. Com os Megascans do `Scene_Saloon`, espere dezenas de minutos na primeira vez. Faça com o projeto salvo e commitado.

### 5.2 Lumen com Hardware Ray Tracing

- **Estado atual:**
  - `r.Lumen.HardwareRayTracing = 1`, mas `r.RayTracing = 0`. O suporte a HWRT do projeto está desligado, então o Lumen roda em **Software**.
  - Na qualidade High, `r.Lumen.TraceMeshSDFs = 0`: modo *Global Tracing*, que traça só o SDF global, grosso.
- **Risco:**
  - A doc pede **paredes com pelo menos 10 cm** no Software Ray Tracing.
  - As paredes do `Mapa_B` são CubeGrid. Confira em Lit → Lumen → Lumen Scene se há luz vazando nas quinas e entre cômodos.
- **Opção:** Configurações do Projeto → Engine → Rendering → busque **Support Hardware Ray Tracing** e marque. Reinicia e recompila shaders.
  - A doc diz que o HWRT "intersects against the actual triangles": melhor em interiores e em parede fina.
  - Custa mais GPU e um pouco de VRAM (BVH), mas numa casa com poucas dezenas de malhas isso é barato.
  - Se o TCC for avaliado numa GPU sem RT, o Lumen cai automaticamente para Software.

### 5.3 Escalabilidade padrão do jogo: High (ou Lumen Lite)

- **Qualidade High:** mira 60 fps. A Epic mira 30 fps de console.
- **Lumen Lite:** novo na 5.8, com `sg.GlobalIlluminationQuality 1` e `sg.ReflectionQuality 1`. É cerca de 2× mais rápido que o High e é uma boa opção "Médio" para máquinas fracas.
- **No primeiro boot do jogo:** *Event BeginPlay* do GameInstance → `Get Game User Settings` → `Run Hardware Benchmark` → `Apply Hardware Benchmark Results` → `Apply Settings`.

  Blueprint serve: roda uma vez só.

### 5.4 Sombras das luzes locais

Toda luz local com `Cast Shadows` gera páginas de VSM e raios de SMRT.

- **Luzes de preenchimento:** nas que só dão ambiência, desligue em Detalhes → Luz (*Light*) → `Cast Shadows`.
- **`RectLight5`:** tem 416 cm de largura. Uma área de luz grande dá sombra macia e cara.
- **A lanterna:** mantenha a sombra, porque ela é a estrela do terror. Já está com `Indirect Lighting Intensity` = 0, o que a tira do *surface cache* do Lumen: ótimo, porque ela se move o tempo todo.

### 5.5 MegaLights

Está *Production Ready* na 5.8. Só compensa com dezenas de luzes com sombra. Com 7 luzes, não ligue.

### 5.6 Cenas claras (a trilha na floresta)

- **Floresta à noite ou ao entardecer:** a faixa [−11, 9] serve.
- **Floresta de dia, com sol (EV100 12–15):** o teto de 9 dispara o aviso para o lado claro. Há duas saídas:
  - suba a cvar para 4–5 (faixa [−8, 12] ou [−7, 13]) e reaperte os `Min EV100` dos mapas escuros para respeitar o novo piso;
  - ou mantenha a floresta ao entardecer, que combina com o terror.

  A cvar é global. Trocar em runtime por mapa não é recomendado, porque os caches foram gravados com a escala antiga.

---

## 6. Efeitos de fotofobia sem estourar a faixa (Blueprint × C++)

Luz "estourando" feita com `Exposure Compensation` **positivo** empurra a exposição efetiva para **baixo**, na direção de −11. Escurecimento feito com compensação **negativa** empurra para **cima**, na direção de 9.

Com o `PPV_Global` atual (Min −8, Max 8), a compensação segura, com 0,5 EV de margem, fica entre **−0,5 e +2,5**.

- **Para flashes de claridade:** use a compensação. Há até +2,5 disponível.
- **Para escurecer:** prefira `Color Grading → Global → Gain`, `Scene Color Tint` ou `Vignette`. Não mexem na exposição.

**Blueprint é suficiente.** O cálculo roda uma vez por evento (ou num *Timeline*), não é lógica pesada por frame:

```
Get Console Variable Float Value ("r.EyeAdaptation.CachedLightingPreExposure") → P
SafeMin = P − 12        SafeMax = P + 8
BiasMax = MinEV100 − SafeMin − 0.5
BiasMin = MaxEV100 − SafeMax + 0.5
Bias    = Clamp(BiasDesejado, BiasMin, BiasMax)
→ Set Members in PostProcessSettings (Auto Exposure Bias, bOverride ligado) → Set Settings no PPV do efeito
```

**C++ só se** esse clamp virar utilitário usado por muitos sistemas. Neste caso, uma *Function Library* (o projeto hoje é só Blueprint; criar a classe em Ferramentas (*Tools*) → Nova Classe C++ transforma o projeto em C++):

```cpp
// LuxExposureLibrary.h
#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "LuxExposureLibrary.generated.h"

UCLASS()
class TCCHORRORLUX_API ULuxExposureLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    /** Faixa segura (EV) da luz em cache na 5.8: [P-12, P+8], P = r.EyeAdaptation.CachedLightingPreExposure. */
    UFUNCTION(BlueprintPure, Category = "Lux|Exposure")
    static void GetCachedLightingSafeRange(float& OutMinEV, float& OutMaxEV);

    /** Limita o Exposure Compensation para que [MinEV100 - Bias, MaxEV100 - Bias] fique dentro da faixa segura. */
    UFUNCTION(BlueprintPure, Category = "Lux|Exposure")
    static float ClampExposureCompensation(float DesiredBias, float MinEV100, float MaxEV100, float MarginEV = 0.5f);
};
```

```cpp
// LuxExposureLibrary.cpp
#include "LuxExposureLibrary.h"
#include "HAL/IConsoleManager.h"

void ULuxExposureLibrary::GetCachedLightingSafeRange(float& OutMinEV, float& OutMaxEV)
{
    // Sem estado de UObject: nada para o GC rastrear. O ponteiro da cvar é estável durante o processo.
    static IConsoleVariable* CVar = IConsoleManager::Get().FindConsoleVariable(TEXT("r.EyeAdaptation.CachedLightingPreExposure"));
    const float P = CVar ? FMath::Min(CVar->GetFloat(), 16.f) : 4.f;   // a engine limita o valor a 16 (medido)
    OutMinEV = P - 12.f;
    OutMaxEV = P + 8.f;
}

float ULuxExposureLibrary::ClampExposureCompensation(float DesiredBias, float MinEV100, float MaxEV100, float MarginEV)
{
    float SafeMin = 0.f, SafeMax = 0.f;
    GetCachedLightingSafeRange(SafeMin, SafeMax);
    // Exposure efetiva = EV100 - Bias  ->  (MinEV100 - Bias >= SafeMin) e (MaxEV100 - Bias <= SafeMax)
    const float BiasHi = MinEV100 - (SafeMin + MarginEV);
    const float BiasLo = MaxEV100 - (SafeMax - MarginEV);
    return (BiasLo <= BiasHi) ? FMath::Clamp(DesiredBias, BiasLo, BiasHi) : 0.5f * (BiasLo + BiasHi);
}
```

---

## 7. Scripts (`Tools/Lighting/`)

Todos rodam pelo console do editor com `py "C:/Users/bruno/Documents/Unreal Projects/TCC_Horror_Lux/Tools/Lighting/<script>.py"`.

| Script | O que faz | Salva algo? |
|---|---|---|
| `audit_lighting.py` | Auditoria só de leitura: luzes, céu, névoa, PPVs, câmera e lanterna do PIE, geometria e cvars. Saída em `Saved/LightingAudit.txt` | Não |
| `apply_ppv_global.py` | Cria ou atualiza o `PPV_Global` (idempotente, pela tag `LUX_PPV_GLOBAL`). Calcula a distância do Lumen pela diagonal do mapa. Com 3 argumentos (`<min> <max> <bias>`), troca só a exposição, para testes. Log em `Saved/LightingApplyPPV.txt` | Não; você salva o mapa |
| `apply_lights_movable.py` | Stationary → Movable e DF Shadows off na directional. Log em `Saved/LightingApplyMovable.txt` | Não |
| `pie_exposure_probe.py`, `pie_ppv_probe.py` | Diagnósticos descartáveis desta sessão. O segundo nem funciona, porque a API de *deferred spawn* não é exposta ao Python. **Pode apagar os dois** | — |

**Para outro mapa escuro:** abra o mapa e rode `apply_ppv_global.py`. Depois, se fizer sentido, rode `apply_lights_movable.py`.

**Para desfazer:**

- Ctrl+Z antes de salvar;
- ou apague o `PPV_Global`;
- no `.ini`, remova a seção `[SystemSettings]` (ou rode `git checkout Config/DefaultEngine.ini`).

---

## 8. Fontes

- Epic / cvar:
  - [r.EyeAdaptation.CachedLightingPreExposure (Unreal Directive)](https://unrealdirective.com/resources/console-variables/r-eyeadaptation-cachedlightingpreexposure/): descrição oficial da cvar, padrão 4.0, introduzida na 5.8.
  - [Cinematographer: FAQ do mesmo aviso](https://lumines-labs.com/Cinematographer-Documentation.html): exemplo do texto completo do aviso e a correção pelo `.ini` (para cena clara, subindo a cvar).
- Epic, exposição:
  - [Auto Exposure in Unreal Engine](https://dev.epicgames.com/documentation/en-us/unreal-engine/auto-exposure-in-unreal-engine): Min/Max EV100, Exposure Compensation, Local Exposure ("should always be set up when using Lumen GI") e o conceito de pré-exposição.
- Epic, Lumen:
  - [Lumen Global Illumination and Reflections (5.8)](https://dev.epicgames.com/documentation/unreal-engine/lumen-global-illumination-and-reflections-in-unreal-engine?lang=en-US): Allow Static Lighting, Detail × Global Tracing, Scene View Distance e Max Trace Distance.
  - [Lumen Technical Details (5.8)](https://dev.epicgames.com/documentation/en-us/unreal-engine/lumen-technical-details-in-unreal-engine): paredes ≥ 10 cm, Max Lumen Mesh Cards, vantagens do HWRT.
  - [Lumen Performance Guide (5.8)](https://dev.epicgames.com/documentation/unreal-engine/lumen-performance-guide-for-unreal-engine): Epic × High × Medium (Lumen Lite), cvars de custo, `stat gpu` / `ProfileGPU`.
- Epic, sombras:
  - [Virtual Shadow Maps](https://dev.epicgames.com/documentation/en-us/unreal-engine/virtual-shadow-maps-in-unreal-engine): Stationary avaliada como Movable com VSM, DF Shadows "in tandem", cache e cvars de resolução.
  - [Sky Lights (5.8)](https://dev.epicgames.com/documentation/unreal-engine/sky-lights-in-unreal-engine): Real Time Capture e time slicing.
- 5.8:
  - [Unreal Engine 5.8 Release Notes](https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-8-release-notes?lang=en-US): MegaLights Production Ready, Lumen Lite.
  - [UE 5.8 Performance Highlights (Tom Looman)](https://tomlooman.com/unreal-engine-5-8-performance-highlights/): Lumen Lite ~2× mais rápido, `r.Lumen.HeightFog`.
- Fórum:
  - ["PROFILING WITH AI LOGGING ON"](https://forums.unrealengine.com/t/how-to-remove-profiling-debug-text/292761): `-NoAILogging`.
  - [Lumen radiance cache × skylight HDR](https://forums.unrealengine.com/t/lumen-radiance-cache-lighting-varies-greatly-w-r-t-probe-resolution-given-high-dynamic-range-skylight-cubemap/2697119): comportamento do radiance cache com céu de alto alcance dinâmico.
