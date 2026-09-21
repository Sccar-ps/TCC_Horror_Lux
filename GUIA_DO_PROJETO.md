# Guia do projeto — TCC_Horror_Lux

Jogo de horror em primeira pessoa feito em **Unreal Engine 5.8**, sem código C++ — tudo em Blueprint.

> Este guia descreve o projeto como ele está. Números de peso e resolução foram medidos direto nos arquivos, não estimados.

---

## 1. Como abrir

| | |
|---|---|
| Engine | `C:\Program Files\Epic Games\UNREAL\UE_5.8` (versão 5.8.2) |
| Arquivo de projeto | `TCCHorrorLux.uproject` |
| Mapa que abre no editor | `Content/FPMovement/Demo/Maps/L_Default_DevMap.umap` |
| **Mapa da cena de verdade** | `Content/Scene_Saloon/Maps/Historic_Saloon.umap` |

**Atenção:** `EditorStartupMap` e `GameDefaultMap` (em `Config/DefaultEngine.ini`) apontam para o `L_Default_DevMap`, que é o mapa de demonstração que veio com o template de movimentação. O saloon é o nível de verdade e precisa ser aberto na mão. Se a intenção for que o jogo comece nele, é só trocar as duas chaves.

### Renderização

Configurado em `Config/DefaultEngine.ini`, seção `[/Script/Engine.RendererSettings]`:

- **Lumen** para GI e reflexos (`r.DynamicGlobalIlluminationMethod=1`, `r.ReflectionMethod=1`)
- **Virtual Shadow Maps** (`r.Shadow.Virtual.Enable=1`)
- **Local Exposure** com contraste reduzido em sombra e realce (`0.8` nos dois) — importante num jogo escuro
- Mesh Distance Fields ligado
- **DirectX 12 / Shader Model 6**, alvo Desktop, qualidade Máxima

---

## 2. Estrutura de pastas

### Conteúdo autoral

| Pasta | Peso | O que é |
|---|---|---|
| `Content/Scene_Saloon/` | 4,23 GB | O nível jogável. Ambiente, materiais e os assets Megascans/Quixel |
| `Content/FPMovement/` | 414 MB | Player, input, interação, HUD, áudio. Base do gameplay |
| `Content/FogArea/` | 27 MB | `BP_FogArea` — volume de névoa local |
| `Content/MR_PSX_Shader/` | 1 MB | Shader de estética PlayStation 1 |
| `Content/Procedural_Hearbeat/` | <1 MB | Batimento cardíaco procedural |
| `Content/__ExternalActors__/` | 4 MB | Atores One File Per Actor (World Partition) |

### Packs de loja fora do versionamento

Nenhum destes é referenciado por `Scene_Saloon` nem por `FPMovement` — verificado varrendo os 1.735 arquivos restantes do projeto. Estão no `.gitignore`, continuam no disco local e podem ser rebaixados do Fab/Quixel quando forem usados.

| Pasta | Peso |
|---|---|
| `Content/OldWest/` | 3,09 GB |
| `Content/SICKA_MouldingSet/` | 672 MB |
| `Content/Backrooms_Ambience/` | 271 MB |
| `Content/FreeAnimationLibrary/` | 189 MB |

**Se você começar a usar assets de algum deles, tire a pasta do `.gitignore` no mesmo commit** — senão o projeto quebra pra quem clonar.

---

## 3. Gameplay

### Ponto de entrada

```
BP_PlayerMode  (GameMode, definido em GlobalDefaultGameMode)
  |-- BP_Player            Character em primeira pessoa
  |-- BP_PlayerController
```

Todos em `Content/FPMovement/Player/Blueprints/`.

### Input — Enhanced Input

Mapping context `IMC_Default`, com 9 ações em `Content/FPMovement/Player/Input/Actions/`:

`IA_Move`, `IA_Look`, `IA_Jump`, `IA_Sprint`, `IA_Crouch`, `IA_Interact`, `IA_Inspect`, `IA_Zoom`, `IA_Flashlight`

### Interação

A interface **`BP_Interact`** (`Player/Blueprints/Interface/`) é o contrato: qualquer ator que a implemente vira interagível. Quem implementa hoje:

| Blueprint | Função |
|---|---|
| `BP_BaseDoor` | Porta, com variante trancada |
| `BP_BaseKey` | Chave que destranca uma porta |
| `BP_BaseItem` | Item coletável genérico |
| `BP_Flashlight` | Lanterna |
| `BP_BaseNote` | Bilhete legível |
| `BP_FlashlightFlicker` | TriggerBox que faz a lanterna piscar ao ser atravessado |

O retículo reage via `BP_InteractDot` + `WB_InteractDot`.

### Sistema de bilhetes

Data-driven, em `FPMovement/Blueprints/Notes/`:

- `PDA_Note` — Primary Data Asset, o molde de um bilhete
- `S_Readable` — struct do conteúdo legível
- `DA_ExampleNoteSingle` / `DA_ExampleNoteMultiple` — exemplos de página única e múltipla
- `WB_Note` — o widget que mostra na tela

**Para criar um bilhete novo não se mexe em Blueprint**: duplica um `DA_` e edita o texto.

### HUD

`WB_PlayerHud` é o container. Dentro dele: `WB_InteractDot`, `WB_Note`, `WB_Notification`. Fonte `F_Handwritten`.

### Headbob

Quatro Blueprints de curva em `Player/Effects/Headbob/`: `BP_Idle`, `BP_Walk`, `BP_Sprint`, `BP_Jump` (+ `BP_JumpEnd`). Tem também um efeito de sujeira na lente em `Player/Effects/Dirtlens/`.

### Passos por superfície

`Config/DefaultEngine.ini` declara **13 Physical Surfaces** (`Footsteps_Concrete`, `Footsteps_Wood`, `Footsteps_Gravel`, ...). Cada uma tem um Sound Cue correspondente em `FPMovement/Assets/Audio/Character/Footsteps/SoundCues/`, alimentado por 6 a 32 variações de wave.

**Ao criar um material de chão novo, atribua o Physical Material certo** — sem isso o passo sai mudo ou com o som errado.

### Animação

`ABP_Player` (`FPMovement/Demo/Character/`) com os braços em `Demo/Character/Arms/` — há uma versão MetaHuman e uma Mannequin.

---

## 4. Convenções de nomenclatura

Seguidas de forma consistente no projeto:

| Prefixo | Tipo | Prefixo | Tipo |
|---|---|---|---|
| `BP_` | Blueprint | `T_` / `TX_` | Textura |
| `WB_` / `WP_` | Widget | `SM_` | Static Mesh |
| `ABP_` | Animation Blueprint | `M_` | Material |
| `IA_` | Input Action | `MI_` | Material Instance |
| `IMC_` | Input Mapping Context | `MF_` | Material Function |
| `DA_` / `PDA_` | Data Asset | `SW_` | Sound Wave |
| `S_` | Struct | `L_` / `MAP_` | Nível |

Os assets Megascans em `Scene_Saloon/Assets/MS/` usam o padrão da Quixel (`His_Sal_`, `Res_Fur_`, `Urb_Set_`...) com sufixo de canal: `_D` difuso, `_N` normal, `_DpR` displacement/roughness. **Não renomeie** — quebra o vínculo com o Bridge.

---

## 5. Orçamento de arte

### Regra de textura: teto de 2048 px

Toda textura do projeto tem `Maximum Texture Size = 2048`. Aplicado em **166 texturas** que estavam acima disso (6 de 8K e 160 de 4K).

| | Antes | Depois |
|---|---|---|
| VRAM de textura | ~3.487 MB | ~1.487 MB |
| Redução | — | **−57%** |

**Para assets novos:** rode o script abaixo depois de importar. Ele só toca no que passa de 2048 e ignora texturas de UI.

```bash
"C:/Program Files/Epic Games/UNREAL/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" "C:/Users/bruno/Documents/Unreal Projects/TCC_Horror_Lux/TCCHorrorLux.uproject" -run=pythonscript -script="C:/Users/bruno/Documents/Unreal Projects/TCC_Horror_Lux/Tools/optimize_textures.py" -unattended -nopause -nosplash -stdout
```

**Feche o editor antes de rodar** — o commandlet não consegue salvar com os pacotes travados. O relatório sai em `Saved/texture_optimization_report.csv`.

O script depende de dois plugins, já habilitados no `.uproject`: `PythonScriptPlugin` e `EditorScriptingUtilities`.

### O que `MaxTextureSize` faz e o que não faz

**Faz:** corta a memória de vídeo e o tamanho do build empacotado.

**Não faz:** encolher o `.uasset` em disco. O *source art* continua serializado dentro do arquivo — é por isso que `T_Res_Rur_Storage_Bucket_Metal_Worn_03_D.uasset` continua com 257 MB mesmo carregando em 2048 no jogo. A engine não expõe nenhuma API de resize de source a script; a única forma de encolher o arquivo seria exportar, reduzir fora da engine e reimportar, o que reseta sRGB, compressão e flag de normal map.

---

## 6. Git

### Git LFS é obrigatório

Todo binário de Unreal vai por LFS (regras em `.gitattributes`): `.uasset`, `.umap`, `.wav`, `.fbx`, `.png`, `.jpg`, `.ttf`.

**Ao clonar:**

```bash
git lfs install
```

```bash
git clone https://github.com/Sccar-ps/TCC_Horror_Lux.git
```

Sem o `git lfs install` antes, você recebe arquivos de ponteiro de texto no lugar dos assets e o projeto não abre.

### Por que LFS não era opcional

Seis arquivos passam de 100 MB, que é o limite rígido de blob do GitHub — sem LFS o push é rejeitado:

| Arquivo | Peso |
|---|---|
| `Scene_Saloon/.../T_Res_Rur_Storage_Bucket_Metal_Worn_03_D.uasset` | 257,3 MB |
| `Scene_Saloon/.../SM_His_Wil_Equipment_Saddle_Leather_Worn_01.uasset` | 132,5 MB |
| `Scene_Saloon/.../SM_His_Wil_Storage_BarrelStand_Wood_Worn_01.uasset` | 129,7 MB |
| `Scene_Saloon/.../SM_His_Wil_Furniture_Table_Wood_Worn_01.uasset` | 128,3 MB |
| `Scene_Saloon/.../SM_Res_Sto_Chest_Wood_Worn_08.uasset` | 127,7 MB |
| `Scene_Saloon/.../SM_His_Med_Storage_Barrel_Wood_Worn_02.uasset` | 126,9 MB |

Os cinco `SM_` são meshes Nanite do Megascans. Otimização de textura não os afeta.

### Cota de LFS

O repositório versionado tem **~4,56 GB**. A cota gratuita do GitHub é **1 GB de storage + 1 GB/mês de banda** — para dar push é preciso comprar data pack, ou enxugar mais o projeto.

### Não versionado

Pelo `.gitignore`: `Saved/`, `Intermediate/`, `DerivedDataCache/`, `Binaries/`, `*_BuiltData.uasset` (dados de iluminação assada, regeneráveis) e os quatro packs de loja da seção 2.

---

## 7. Armadilhas conhecidas

1. **`ProjectName=FPMovement`** — `Config/DefaultGame.ini` ainda carrega o nome do template, enquanto o `.uproject` é `TCCHorrorLux` e `[URL] GameName=TCCHorrorLux`. Inofensivo hoje, mas confunde no empacotamento.

2. **Mapa de startup errado** — ver seção 1.

3. **`__ExternalActors__` órfão** — quatro pastas (`FFPMovement`, `FirstPerson`, `LocomotionAnimPack`, `ThirdPerson`, 553 arquivos) apontam para mapas que não existem mais. Não quebram nada, mas sujam o Content Browser. Limpar só com o editor aberto, pelo Content Browser, nunca apagando arquivo na mão.

4. **Blueprints duplicados** — `WB_Note` e `WB_Notification` existem em duas pastas (`UserCreated/` e `UserCreated/Note/`, `UserCreated/Notification/`). Confira qual está realmente referenciado antes de editar.

5. **Assets Megascans são pesados por natureza** — um prop pode trazer 5 texturas 4K e um mesh Nanite de 130 MB. Antes de arrastar um asset novo do Bridge, pense se ele aparece na cena.
