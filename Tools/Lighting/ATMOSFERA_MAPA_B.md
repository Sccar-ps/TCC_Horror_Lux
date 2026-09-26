# Atmosfera densa no Mapa_B: diagnóstico e caminhos (UE 5.8.3)

Levantamento feito em 26/09/2026 no editor, com o `Mapa_B` como estava salvo. Script de leitura: `Tools/Lighting/audit_atmosphere.py` (saída em `Saved/AtmosphereAudit.txt`). Nada no mapa foi alterado.

## 1. Estado atual

### Luzes (22 componentes)

| Grupo | Situação |
|---|---|
| Velas, candelabros, abajures e arandela (15, na pasta `LUX/Luzes`) | 2200–2700 K, 0,02–0,35 cd. É a iluminação real da casa |
| RectLights de teto | `RectLight2/3/5/7` com intensidade **0**. A `RectLight6` foi apagada. Só a `RectLight` do escritório está acesa (0,64 cd, 4500 K) |
| `DirectionalLight` | 10 lux, pitch +2,9°: o sol fica abaixo do horizonte. Pinta o pôr do sol nas janelas. Sombra VSM e *volumetric shadow* ligadas |
| `PointLight` | 1830 lm, com sombra, a 12,8 m de altura e fora da casa, com raio de 10 m. Não alcança o interior: sobra do template |
| Lanterna (`BP_Player_Cowboy`) | Spot 4000 (unitless), 15 m, cone 30°, light function `Flashlightpattern_Mat`, sombra, *Volumetric Scattering* 0,25, *Indirect* 0 |

- **Luzes ativas:** 16. Outras 6 estão zeradas: as 4 RectLights e as `VelasPiano` 1 e 2. Luz com intensidade 0 não é renderizada.
- **Luzes ativas com sombra (7):**
  - `PointLight` externa;
  - `RectLight` (escritório);
  - `DirectionalLight`;
  - `Sala_Candelabro`;
  - `Sala_VelaJantar`;
  - `Escritorio_Vela`;
  - `Sala_Abajur2`.
- **Raios fora de escala** (a diagonal da casa é de 55 m):

  | Luz | Attenuation Radius | Source Radius | Sombra |
  |---|---|---|---|
  | `Quarto_VelaComoda` | 52,7 m | 3 cm | não |
  | `Sala_Abajur2` (fica no quarto) | 39,9 m | 10 m | sim |
  | `Sala_Candelabro` 1–3 | 8,2 m | 1,68 m | só o 1 |

### Névoa, céu e pós-processo

- **`ExponentialHeightFog`:** na prática, invisível dentro da casa.
  - Densidade 0,0436, que é valor de paisagem: dá cerca de 1,6% de névoa em 10 m.
  - O ator está a Z = −6850.
  - *Inscattering* preto: a cor vem do céu.
  - **Volumetric Fog desligado** no componente (a cvar `r.VolumetricFog` está em 1).
  - Um A/B com `show fog` não mostra diferença visível.
- **Não há** SkyLight, Local Fog Volume nem Reflection Capture.
- **`PPV_Global`:** só mexe em exposição (histograma, Min EV100 −8, Max 8, bias 1) e nas distâncias do Lumen (7000). Nenhum override de cor, vinheta, grain ou aberração cromática. A câmera do jogador não tem override.
- **Consequência:** com Min EV100 −8, o olho virtual clareia o escuro em 1–2 s.

### Custo (`stat gpu`, viewport do editor, 1263×768 a 89%)

| GPU | Lights | LumenScreenProbeGather | Postprocessing | Shadow Depths | Shadow Projection | Fog | VRAM |
|---|---|---|---|---|---|---|---|
| 5,70 ms | 1,63 | 1,25 | 1,02 + 0,42 (compute) | 0,49 | 0,18 | 0,03 | 3,59 / 6,96 GB |

Em 24/09 o passo *Lights* media 0,92 ms. A câmera era outra, então não é A/B exato. Os raios de 40–53 m são o suspeito principal.

## 2. Abordagens avaliadas

| | 1. Só pós-processo | 2. Pós + névoa volumétrica | 3. Iluminação por cômodo |
|---|---|---|---|
| Atores | 0 novos, 1 editado (`PPV_Global`) | 0 novos, 2 editados + lanterna | Vários novos: Local Fog Volumes, PPVs locais, flicker |
| Custo GPU | ≈ 0 (gradação vira LUT por frame; vinheta, grain e aberração ficam no tonemapper) | Estimado em 0,3–0,8 ms na RTX 5060 (grid High 16 px × 64 fatias ≈ 396 mil voxels a 1080p/87%). Estimado em ~20–35 MB de VRAM | O da 2, mais Local Fog Volumes (custo de luz dinâmica por área de tela, até 32 por vista) e a lua com sombra volumétrica |
| Ganho | Escuro de verdade, contraste frio × quente, vinheta e grain | + ar, halos nas velas, fundo do corredor engolido | + identidade por cômodo, fachos de lua, flicker |
| Riscos | Sem "ar"; *banding* ao escurecer só pela cor | Lanterna deixa rastro na névoa (reprojeção temporal, documentado pela Epic). *Source Radius* e IES são ignorados na névoa | Muitos parâmetros; mistura variáveis no experimento |

**Limpeza que vale para qualquer caminho:**
- raios: `VelaComoda` → ~3 m; `Abajur2` → ~5 m, com *Source Radius* ~10 cm; candelabros → ~3 m;
- apagar a `PointLight` externa.

## 3. Decisões do grupo (26/09)

| Pergunta | Resposta |
|---|---|
| Céu | Noite com lua |
| Paleta | Frio × quente: sombras e névoa frias, velas quentes |
| Condições do experimento | Alternar no mesmo mapa, em runtime |
| Hardware dos testes | Máquinas variadas |

## 4. Recomendação ajustada às respostas

Abordagem 2, com três complementos.

1. **Lua = a `DirectionalLight` existente.**
   - Colocar acima do horizonte, com poucos lux e tom frio.
   - Com o SkyAtmosphere, um "sol" fraco resulta num céu noturno azul-escuro.
   - A *volumetric shadow* já está ligada, então a lua forma fachos pelas janelas na névoa.
2. **Troca de condição no mesmo mapa.**
   - **Não apagar as RectLights zeradas:** elas são a luz "relativamente clara" da condição A (controle).
   - **Estrutura:**
     - `PPV_Controle`, neutro;
     - `PPV_Atmosfera`, com exposição baixa, gradação frio × quente, vinheta e grain;
     - a névoa;
     - a lista de luzes da condição.
   - **Controle:** tudo comandado por um ator Blueprint com um enum de condição e uma função `AplicarCondicao`, chamada no BeginPlay e numa tecla de debug. O custo aparece só no evento; por frame é zero. C++ não se justifica.
3. **Máquinas variadas: validade do experimento.**
   - **O problema:** no `BaseScalability` padrão, Shadows Low e Medium desligam `r.VolumetricFog`. O High usa 16 px/64 fatias, os mesmos valores lidos no editor; o Epic usa 8/128. Em 5.8, GI Low desliga o Lumen. Com preset diferente por máquina, a condição B muda de participante para participante.
   - **Propostas:**
     - build de teste com escalabilidade travada, reduzindo só a resolução (Screen Percentage/TSR) nas máquinas fracas;
     - `Config/DefaultScalability.ini` mantendo uma névoa volumétrica barata no Medium em vez de desligá-la;
     - height fog comum como base de densidade em todos os níveis.

**Ordem proposta:**
1. Limpeza dos raios, com medição antes e depois.
2. `PPV_Atmosfera` + exposição.
3. Névoa volumétrica + lua.
4. Blueprint de condição + `PPV_Controle`.
5. Escalabilidade + medição em Low, Medium e High.

## 5. Fontes

- [Volumetric Fog (5.8)](https://dev.epicgames.com/documentation/en-us/unreal-engine/volumetric-fog-in-unreal-engine): custos, luzes com sombra ~3×, rastro de lanternas, limitações.
- [Exponential Height Fog (5.8)](https://dev.epicgames.com/documentation/en-us/unreal-engine/exponential-height-fog-in-unreal-engine).
- [Local Fog Volumes (5.8)](https://dev.epicgames.com/documentation/unreal-engine/local-fog-volumes-in-unreal-engine): renderização analítica, custo por área de tela, limite de 32.
- [Using Light Functions (5.8)](https://dev.epicgames.com/documentation/en-us/unreal-engine/using-light-functions-in-unreal-engine): Light Function Atlas com suporte à névoa volumétrica.
- [Color Grading and the Filmic Tonemapper](https://dev.epicgames.com/documentation/en-us/unreal-engine/color-grading-and-the-filmic-tonemapper-in-unreal-engine).
- [UE 5.8 Release Notes](https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-8-release-notes?lang=en-US) e [UE 5.8 Performance Highlights (Tom Looman)](https://tomlooman.com/unreal-engine-5-8-performance-highlights/).
- [BaseScalability.ini (cópia pública, estrutura da UE4)](https://github.com/GameTechDev/UnrealCapabilityDetect/blob/master/Saved/Temp/Win64/Engine/Config/BaseScalability.ini): `r.VolumetricFog` por nível de Shadows.
- [Fórum: luz com intensidade 0](https://forums.unrealengine.com/t/does-a-light-with-intensity-set-to-0-spends-resourches/644559).

## 6. Aplicado em 26/09 (etapas 1 a 3)

Script: `Tools/Lighting/apply_atmosphere.py`. É idempotente: os valores ficam no topo do arquivo, então basta editar e rodar de novo. Desfazer: Ctrl+Z ("LUX: atmosfera"). **O mapa não foi salvo.** Os valores originais estão em `Saved/AtmosphereAudit.txt`.

Para comparar, use `Tools/Lighting/shots.py <rótulo>`: ele tira 4 vistas fixas na altura do olho e salva em `Saved/Atmos/`. O antes e depois está em `Tools/Lighting/Mapa_B_atmosfera_antes_depois.jpg`.

| Camada | O que mudou |
|---|---|
| Limpeza | `VelaComoda` 52,7 → 3 m · `Abajur2` 39,9 → 5 m, *Source Radius* 10 m → 10 cm, **sombra off** (a cúpula bloqueava a luz) · Candelabros 1–3: 8,2 → 3 m, *Source Radius* 5 cm · Arandelas 3 e 5: 11,2 → 6 m · `PointLight` externa apagada |
| `PPV_Atmosfera` (novo, Unbound, prioridade 1) | Min/Max EV100 −7/4 · Speed Down 0,5 · Local Exposure Shadow Contrast 0,9 · White Temp 5800 · Contrast 1,08 · Sombras: saturação 0,7, gain (0,85; 0,95; 1,15) · Vinheta 0,7 · Grain 0,3 · Aberração cromática 0,25 |
| `ExponentialHeightFog` | Z −6850 → 0 · densidade 0,0436 → 0,15 · Inscattering (0,0005; 0,001; 0,002) · contribuição do céu 0 · **Volumetric Fog on** · Albedo (200, 205, 215) · Scattering Distribution 0,3 · View Distance 30 m · Emissive (0,0001; 0,0002; 0,0004) |
| Lua (`DirectionalLight`) | pitch +2,9° → −25° · 10 → 0,06 lux · cor (170, 195, 255) · Volumetric Scattering 0,4 |
| Céu | `SkyAtmosphere` Sky Luminance Factor 0,1 |
| Velas, abajures e arandelas (`LUX_Luz_*`) | Volumetric Scattering 3,0: halo na névoa sem mudar a luz na superfície |

**Custo medido** (`stat gpu`, câmera da sala, viewport 1263×768 a 89%)

| | GPU | Lights | VolumetricFog | Fog | Shadow Depths | VRAM |
|---|---|---|---|---|---|---|
| Antes | 5,66 ms | 1,56 | — | 0,03 | 0,50 | 3,75 GB |
| Depois | **4,86 ms** | **0,53** | 0,13 | 0,04 | 0,46 | 3,76 GB |

A névoa volumétrica custa 0,13 ms. A correção dos raios devolveu ~1 ms no passo *Lights*.

**O que ficou para depois**

- **Lanterna × névoa (rastro):** não foi testada. No PIE a lanterna não ligou com `F`: no FPMovement ela depende do item `BP_Flashlight`. Se aparecer rastro, baixe o *Volumetric Scattering* da lanterna (hoje 0,25).
- **Janelas do escritório:** continuam sendo o ponto mais claro. É o exterior iluminado pela lua. Para escurecer, baixe `MOON["intensity"]`.
- **Etapas 4 e 5** (Blueprint de condição e escalabilidade): ainda não feitas. A condição A (controle) hoje é desligar o `PPV_Atmosfera` (*Enabled*) e o *Volumetric Fog* da névoa.
