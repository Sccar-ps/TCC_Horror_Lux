# MixamoFP: corpo em 1ª pessoa com o Cowboy sincronizado ao FPMovement (UE 5.8)

Este guia substitui a tentativa anterior (CowboyFP com a FreeAnimationLibrary). O `BP_Player` do FPMovement e os seus mapas **não foram alterados**. Todos os assets novos estão em `/Game/Characters/MixamoFP/`, e os scripts que geram tudo estão em `Tools/MixamoFP/`.

---

## 0. Arquitetura final

```
BP_Player (FPMovement)            ← intacto: input, crouch (Crouch_TL), headbob, lanterna, interação
 └─ BP_Player_Cowboy (filho)      /Game/Characters/MixamoFP/Blueprints/
     ├─ SpringArm → FirstPersonCamera → FirstPersonMesh (braços + lanterna)   ← herdados, sem mudança
     └─ Mesh (CharacterMesh0) = SKM_Cowboy_NoGun + ABP_CowboyFP   "MALHA-SOMBRA": locomoção fisicamente correta
          │  Render in Main Pass = off · Render in Depth Pass = off · Cast Shadow = on
          │  Visibility Based Anim Tick Option = Always Tick Pose and Refresh Bones
          └─ BodyVisible = SKM_Cowboy_NoGun + ABP_CowboyFP_Visible   "MALHA VISÍVEL": só o que a câmera vê
                Copy Pose From Mesh (Use Attached Parent) + camada 1P (BodyShift / LeanRot)
                Cast Shadow = off · Only Tick Pose When Rendered
                HideBoneByName: neck_01 (cabeça), upperarm_l, upperarm_r (braços)
BP_PlayerMode → Default Pawn Class = BP_Player_Cowboy   (o Mapa_A usa BP_PlayerMode como GameMode Override)
```

**Por que duas malhas.** Os requisitos se contradizem numa malha só.

- **Sombra:** precisa do corpo inteiro, com cabeça e braços.
- **Câmera:** não pode ver a cabeça (atravessaria a lente) nem os braços do corpo (brigariam com os braços FP que seguram a lanterna).

O `HideBoneByName` colapsa os vértices do osso em todos os passes, inclusive na sombra. Por isso ele só pode ser aplicado numa malha que não projeta sombra.

A documentação da Epic compara as três formas de reaproveitar uma pose:

- **Leader Pose:** é a mais barata, mas os seguidores "won't run any animations independently" (não rodam nenhuma animação própria). Assim, não dá para aplicar a camada 1P só na malha visível.
- **Copy Pose From Mesh:** permite um AnimGraph próprio. Custa mais que o Leader Pose, mas para um único personagem isso é irrelevante.
- **Skeletal Mesh Merge:** junta as malhas em uma só em runtime. Não serve aqui, pelo mesmo motivo: a malha resultante roda uma única animação.

---

## 1. Etapa 1: preparar o pacote Mixamo (Blender)

### 1.1 O que havia de errado com o pacote bruto (`Content/AnimationAdobe`)

| Problema | Consequência | Solução aplicada |
|---|---|---|
| FBX *Without Skin* (só esqueleto) | O UE não cria um `Skeleton` a partir de um FBX sem malha | Malha-proxy gerada no Blender: uma caixa por osso, 416 vértices (`SKM_Mixamo_Proxy`) |
| `Hips` é a raiz e carrega a translação (root motion) | O corpo sai andando da cápsula | *In place*: remoção linear (detrend) da translação horizontal do `Hips` |
| Nó `Armature` com rotação e escala | A primeira importação "deitou" o esqueleto (quadril em y = −104) | Unit scale 0.01, rotação e escala aplicadas antes do export, Primary Y / Secondary X, Forward −Z / Up Y, `Add Leaf Bones` = off |
| Pacote incompleto (sem idle em pé, walk com maleta, sem crouch lateral ou para trás, sem queda) | Faltariam amostras nos BlendSpaces | Substitutos gerados por IK analítica de duas juntas (tabela abaixo) |

### 1.2 Clipes gerados (velocidades medidas nos pés do Cowboy, após o retarget)

| Asset final | Fonte no pacote | Processamento | Vel. no chão (cm/s) |
|---|---|---|---|
| `A_CB_Idle` | Stop Walking (pose final) | Pose estática de 4 s + respiração em `Spine1`/`Spine2` | 0 |
| `A_CB_Walk_F` | Walk With Briefcase | Braço da maleta substituído pelo espelho do braço livre | 152,7 |
| `A_CB_Walk_B` | Walking Backward | Stride warp ×1,25, quadril −3 cm | 135,1 |
| `A_CB_Walk_L` / `_R` | Walk Strafe Left/Right | Stride warp ×1,25 | 70,5 |
| `A_CB_Run_L` / `_R` | run Left/Right Strafe | In place | 424 |
| `A_CB_Crouch_Idle` | Crouch Idle | Nenhum | 0 |
| `A_CB_Crouch_F` | Crouched Walking | "Crouchify" (quadril a 62 cm), stride ×0,6 | 77,3 |
| `A_CB_Crouch_B` | Crouched Walking **invertido** | Reverse | 77,3 |
| `A_CB_Crouch_L` / `_R` | Walk Strafe **agachado sintético** | Crouchify + delta de coluna, stride ×1,3, joelho à frente | 73 |
| `A_CB_Fall` | Crouched To Standing (50%) | Pose estática | — |

Todos os clipes estão a 30 fps e com os pés no chão: tornozelo a 10–12 cm e ponta do pé a 1–5 cm depois do retarget.

### 1.3 Como reproduzir e acrescentar clipes

```bat
:: Blender 4.2+ (validado com o bpy 5.0.1; ajuste o caminho do blender.exe). Lê os FBX de Content/AnimationAdobe (ou da pasta em MIXAMO_SRC)
"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe" -b --factory-startup -P "Tools\MixamoFP\blender\prep_all.py"
:: saída: Tools\MixamoFP\blender\prep\*.fbx + manifest.json  →  copie para SourceArt\MixamoFP_v2\
```

- **`mxlib.py`:** funções reutilizáveis.
  - `load`, `in_place`, `reverse`
  - `stride_warp` e `crouchify` (IK de perna exata)
  - `static_pose_clip`, `mirror_arm_from_left`
  - `build_proxy_mesh` (a malha-proxy)
  - `to_ue_space` e `export_fbx`
- **`prep_all.py`:** a "receita" de cada clipe. Para um clipe novo, copie um bloco existente. Por exemplo, um walk sem maleta seria `load("Walking")` → `in_place` → `done("MX_Walk_F", …)`.

> Não importe FBX bruto do Mixamo direto no `SKM_Mixamo_Proxy_Skeleton`. O nó `Armature` do arquivo bruto traz outra orientação, e a animação entra girada. O pipeline do Blender existe exatamente para padronizar isso.

---

## 2. Etapa 2: importar no UE (`import_mixamo2.py`)

A 5.8 importa FBX pelo **Interchange** por padrão. O script liga o importador legado com a cvar `Interchange.FeatureFlags.Import.FBX 0` e depois a restaura para `1`.

O script faz o equivalente a estes passos manuais:

1. Abra o Navegador de Conteúdo (*Content Browser*), clique em **Importar** (*Import*) e escolha `SKM_Mixamo_Proxy.fbx`.
2. Marque `Import Mesh` e `Update Skeleton Reference Pose`. O resultado é `/Game/Characters/MixamoFP/Source/SKM_Mixamo_Proxy` e o `_Skeleton`.
3. Importe os `MX_*.fbx` com:
   - `Skeleton` = `SKM_Mixamo_Proxy_Skeleton`
   - `Import Animations` ligado
   - `Animation Length` = *Exported Time*
   - `Use Default Sample Rate` = off e `Custom Sample Rate` = 30

Destino: `/Game/Characters/MixamoFP/Source/Anims/MX_*`. O UE remove o namespace `mixamorig:`, e os ossos ficam `Hips`, `Spine`…

---

## 3. Etapa 3: retarget Mixamo → Cowboy (`setup_retarget.py`)

| Asset | O que tem |
|---|---|
| `Rig/IK_Mixamo`, `Rig/IK_Cowboy` | Caracterização automática: cadeias de retarget + FBIK gerados automaticamente |
| `Rig/RTG_Mixamo_to_Cowboy` | Op stack: Pelvis Motion, FK Chains, Run IK Rig, **Root Motion desligado** (os clipes já estão in place) e Remap Curves. Cadeias mapeadas por nome (fuzzy), `Auto Align All Bones` no alvo e `Snap to Ground` pelo `foot_l` |
| `Anims/A_CB_*` (13) | Exportados em lote (*batch*), trocando o prefixo `MX_` por `A_CB_` |

Caminhos na UI:

- **Criar IK Rig ou Retargeter:** clique direito no Navegador de Conteúdo → Animação (*Animation*) → Retargeting → *IK Rig* / *IK Retargeter*.
- **Exportar em lote:** no editor do Retargeter, selecione os clipes na aba *Asset Browser* e use `Export Selected Animations`.

O script também mede a velocidade real dos pés de cada clipe retargetado e grava em `Saved/MixamoFP_speeds.json`. Essa velocidade alimenta o *rate scale* dos BlendSpaces, que é o que evita o pé "patinando" (*foot sliding*).

---

## 4. Etapa 4: BlendSpaces (`create_assets.py`, linha de corrida por `run_apply.py`)

**`BlendSpaces/BS_CB_Stand`**

- Eixo X `Direction`: −180..180, 8 divisões, `Wrap Input` ligado.
- Eixo Y `Speed`: 0..**360** (era 450; ver 4.1).

| Amostra (Direction, Speed) | Clipe | Rate scale |
|---|---|---|
| (−180, −90, 0, 90, 180; 0) | Idle | 1,00 |
| (0; 150) | Walk_F | 0,98 |
| (±180; 150) | Walk_B | 1,11 |
| (−90 / 90; 150) | Walk_L / Walk_R | 2,13 |
| (0; 360) | **Run_F** (corrida real) | 0,75 |
| (±180; 360) | Walk_B **(placeholder de corrida para trás)** | 2,66 |
| (−90 / 90; 360) | Run_L / Run_R | 0,85 |

### 4.1 Corrida mais lenta e com animação de corrida de verdade

**Antes:** o sprint do FPMovement era 450 cm/s e, para frente, usava o walk acelerado 2,95× (um "passo de vídeo acelerado"). Para trás era o walk de costas a 3,33×.

**Agora:**

- **Velocidade:** `BP_Player_Cowboy` → Padrões de Classe (*Class Defaults*) → `Max Sprint Speed` = **360 cm/s** (−20%). É uma sobrescrita no filho; o `BP_Player` continua com 450. A lógica de sprint é a do próprio FPMovement (`Set MaxWalkSpeed = MaxSprintSpeed`), então nada no input mudou.
- **Corrida para frente:** `A_CB_Run_F`, cópia do `MM_Run_Fwd` que vem no demo do pacote do Cowboy (mesmo esqueleto, sem retarget). O original do demo não mudou. Velocidade natural medida no contato do pé: 479,8 cm/s, 3 ciclos em 1,9 s. A 360 ela toca a 0,75×, e as corridas laterais a 0,85×.
- **Por que 360 e não menos:** abaixo de ~0,7× a corrida parece câmera lenta ("flutuando"). A 300, a Run_F tocaria a 0,63×. Para testar outro valor, rode `py ".../Tools/MixamoFP/run_apply.py" 330`: ele recalcula os rate scales e ajusta o `MaxSprintSpeed` de uma vez.
- **Sync markers de passo:** walk, idle e corrida têm número de ciclos diferente (a Run_F tem 3 ciclos, o Walk_F tem 1). Por isso o `run_prepare.py` pôs *sync markers* `L`/`R` no meio do apoio de cada pé, numa trilha "Passos", em **todos** os clipes do `BS_CB_Stand`. O BlendSpace só sincroniza por markers se **todos** os clipes tiverem os mesmos nomes; no idle os markers são artificiais, em 1/4 e 3/4. Resultado: na transição andar ↔ correr os pés não se cruzam.

**Conferido no PIE:**

- Sprint a 360 nas 4 direções (`Direction` 0 / −90 / 90 / −180).
- Transição a 232 cm/s sem pés cruzados.
- Corrida para frente e laterais naturais.
- Para trás, a pose ainda é o walk de costas acelerado: é o próximo clipe a baixar ("Running Backward").

**Som dos passos:** o `BP_Player` acelera o `Footsteps_TL` com `Set Play Rate` = **2,2** no sprint. Esse valor está fixo no grafo do pai e não dá para sobrescrever no filho. Na cadência nova da corrida (≈2,4 passos/s), o valor equivalente seria **≈1,25**. Se o som dos passos soar rápido demais, ajuste esse nó no `BP_Player`: EventGraph → `EnhancedInputAction IA_Sprint` (*Started*) → `Set Play Rate` → `New Rate`. É o único ajuste que mexe no FPMovement, e não o fiz por isso.

**`BlendSpaces/BS_CB_Crouch`**

- `Speed`: 0..80.

| Amostra (Direction, Speed) | Clipe | Rate scale |
|---|---|---|
| (vários; 0) | Crouch_Idle | 1,00 |
| (0; 80) | Crouch_F | 1,03 |
| (±180; 80) | Crouch_B | 1,03 |
| (−90 / 90; 80) | Crouch_L / Crouch_R | 1,10 |

A regra do rate scale é `velocidade no jogo ÷ velocidade medida do clipe`. Por exemplo, 150 ÷ 70,5 = 2,13 para o strafe.

> **Armadilha conhecida:** amostras criadas via Python nascem com `bIsValid = false` (campo *transient*), e o BlendSpace devolve a *ref pose* até o editor dele ser aberto. O script abre e salva os dois BlendSpaces alguns frames depois de terminar. Se editar amostras por script de novo, abra o BlendSpace (duplo clique) e salve com **Ctrl+S**.

---

## 5. Etapa 5: `ABP_CowboyFP` (malha-sombra = a "verdade física")

**EventGraph** (`Blueprint Update Animation`, atrás de `IsValid(Player)`):

| Variável | Cálculo | Por quê |
|---|---|---|
| `Speed` | `VSizeXY(GetVelocity)` | Eixo Y dos BlendSpaces |
| `Direction` | `CalculateDirection(Velocity, ActorRotation)` | Eixo X |
| `CrouchAlpha` | `clamp((StandingHalfHeight − HalfHeight atual) / (96 − 40))` | O crouch do FPMovement é **customizado**: usa `Crouch_TL`, `SetCapsuleHalfHeight` e `CameraOffset`, e não `ACharacter::Crouch()`. Por isso a leitura vem da cápsula, e o resultado é um alpha contínuo que acompanha o timeline |
| `InAirAlpha` | `FInterpTo(InAirAlpha, IsFalling ? 1 : 0, dt, 10)` | Entrada e saída suaves da pose de queda |
| `RootOffset` | `(0, −Lerp(BackOffsetStand, BackOffsetCrouch, CrouchAlpha), 96 − HalfHeight)` | **Z:** a cápsula encolhe de 96 para 40, o centro desce 56 cm e o `Mesh` (em Z −96) iria para dentro do chão; o +56 compensa. **Y:** empurra o corpo para trás da câmera. No espaço de componente do Cowboy, +Y é a frente |

**AnimGraph:**

1. `BS_CB_Stand` / `BS_CB_Crouch` → `Blend` (`CrouchAlpha`)
2. → `Blend` (`InAirAlpha`, `A_CB_Fall`)
3. → `Save Cached Pose`
4. → `Slot 'DefaultSlot'` + `Layered blend per bone` (a partir do `spine_01`), preparado para montages de interação
5. → `Local To Component` → `Transform (Modify) Bone` (`root`, translação aditiva em *Component Space* = `RootOffset`)
6. → `Component To Local` → **Output Pose**

Padrões de Classe (*Class Defaults*): `StandingHalfHeight` 96, `CrouchedHalfHeight` 40, `BackOffsetStand` 4, `BackOffsetCrouch` 30.

---

## 6. Etapa 6: `ABP_CowboyFP_Visible` (camada de apresentação 1P)

Tudo o que é "truque de câmera" fica **só** aqui. A sombra continua fisicamente correta.

**Initialize:** `HideBoneByName` em `neck_01`, `upperarm_l` e `upperarm_r`, e um `Cast To BP_Player` feito uma única vez, com o resultado guardado em `Player`.

**Update** (a cada frame, na malha visível):

```
NeckRel   = neck_01 da malha-sombra − posição da FirstPersonCamera        (mundo)
StandW    = MapRangeClamped(NeckRel.Z, 0, −10, 0, 1)      → 1 em pé (câmera ≥10 cm acima do pescoço), 0 agachado
LookA     = MapRangeClamped(Pitch da câmera, LeanStartPitch, LeanFullPitch, 0, 1) · StandW
BodyShift = FInterpTo(BodyShift, clamp(NeckFwd + NeckMinBehind, 0, MaxBodyShift)·StandW + LookDownShift·LookA, dt, 8)
RootShift = (0, −BodyShift, 0)                       → ModifyBone(root, translação aditiva, Component Space)
LeanRot   = (Roll = −LeanMax · LookA)                → ModifyBone(spine_01, rotação aditiva, Component Space)
```

**Os dois problemas que isso resolve (medidos no PIE):**

1. **Animações inclinadas põem o pescoço na frente da câmera.** Em relação à câmera, o pescoço fica:
   - parado: 11 cm **atrás**;
   - andando: 1–2 cm atrás;
   - no sprint: **8 cm à frente**, e a câmera veria o buraco do pescoço escondido.

   O `BodyShift` mantém o pescoço sempre pelo menos `NeckMinBehind` cm atrás. O valor fica em 8–9 cm andando e em cerca de 18 cm no sprint.
2. **Olhando para baixo em pé, o colete cobre os pés.** Equivale a um "modelo de pescoço": ao flexionar a cabeça, os olhos avançam. O corpo visível recua 12 cm e o tronco inclina 14°. A −75° aparecem o peito e as **pontas das botas**, em vez de só a gola.

**Parâmetros ajustáveis** (em `ABP_CowboyFP_Visible` → Padrões de Classe / *Class Defaults*):

| Variável | Padrão | Efeito |
|---|---|---|
| `NeckMinBehind` | 10 cm | Distância mínima do pescoço atrás da câmera. Aumente se ainda aparecer gola ou buraco do pescoço |
| `MaxBodyShift` | 25 cm | Limite do alinhamento, para animações muito inclinadas |
| `LookDownShift` | 12 cm | Recuo extra ao olhar para baixo. **0** desliga, e os pés visíveis deixam de deslizar ao inclinar a câmera |
| `LeanStartPitch` / `LeanFullPitch` | −20° / −75° | Faixa de pitch em que o recuo e a inclinação entram |
| `LeanMax` | 14° | Inclinação do tronco para trás em `spine_01` |

**Compromisso consciente.** Com `LookDownShift` > 0, os pés visíveis deslizam até 12 cm no chão enquanto você inclina a câmera. A sombra não se move, porque ela vem da outra malha. Se preferir pés 100% plantados, use 0: você perde as pontas das botas, mas continua vendo o peito.

Os dois grafos têm comentários explicando cada bloco.

---

## 7. Etapa 7: personagem e GameMode

| Onde | Configuração |
|---|---|
| `BP_Player_Cowboy` → componente `Mesh` (herdado) → Detalhes (*Details*) | Malha (*Mesh*) → Skeletal Mesh Asset = `SKM_Cowboy_NoGun` (ver 7.1); Animação (*Animation*) → `Anim Class` = `ABP_CowboyFP`; Transform: Location (0, 0, −96), Rotation Z = −90 |
| idem | Renderização (*Rendering*) → Avançado (*Advanced*) → `Render in Main Pass` = off, `Render in Depth Pass` = off; Iluminação (*Lighting*) → `Cast Shadow` = on; Otimização (*Optimization*) → `Visibility Based Anim Tick Option` = `Always Tick Pose and Refresh Bones` |
| `BodyVisible` (filho do `Mesh`) | Mesma malha; `Anim Class` = `ABP_CowboyFP_Visible`; `Cast Shadow` = off; `Visibility Based Anim Tick Option` = `Only Tick Pose When Rendered`; transform zerado |
| `BP_PlayerMode` → Padrões de Classe (*Class Defaults*) | Classes → `Default Pawn Class` = `BP_Player_Cowboy` |
| `Mapa_A` → Janela (*Window*) → Configurações do Mundo (*World Settings*) | `GameMode Override` = `BP_PlayerMode` (já estava assim) |

### 7.1 Coldre e revólver removidos (`/Game/Characters/MixamoFP/Mesh/SKM_Cowboy_NoGun`)

O Cowboy original do pacote (`SM_SkeletalMesh_cowboy_character`) **não foi alterado**. Ele continua sendo usado pelo demo do pacote. O personagem usa uma cópia sem o cinturão/coldre (slot 7, `mat_cowboy_holster`) e sem o Colt (slot 8, `mat_cowboy_colt`).

Script: `Tools/MixamoFP/nogun_apply.py`, rodando o Geometry Script em cada LOD. Para cada LOD ele:

1. Lê o *source model* do LOD original (`CopyMeshFromSkeletalMesh`).
2. Seleciona os triângulos por ID de material (`SelectMeshElementsByMaterialID` com 7 e 8).
3. Apaga esses triângulos (`DeleteSelectedTrianglesFromMesh`) e compacta a malha.
4. Grava o resultado no duplicado (`CopyMeshToSkeletalMesh`), preservando pesos de skin, UVs e as configurações de build.

Por fim, os slots 7 e 8 ficam vazios. Assim o personagem deixa de referenciar os materiais e as texturas do coldre e do revólver.

| LOD | Triângulos | Vértices (render) | Seções |
|---|---|---|---|
| 0 | 26.459 → **14.631** (−45%) | 16.323 → **8.715** | 9 → 7 |
| 1 | 5.291 → 3.479 | 3.882 → 2.456 | 9 → 7 |
| 2 | 1.321 → 961 | 1.193 → 903 | 7 → 5 |

O ganho vale em dobro, porque são duas malhas: a sombra e a visível. Por frame, o skinning processa metade dos vértices, e caem 2 seções (*draw calls*) por malha em cada passe. O cinturão de balas era a peça mais densa do modelo.

**Conferido no PIE (Mapa_B, com sol):**

- Frente, lado, costas e close da cintura dos dois lados: sem buracos, com a calça e o cinto fino da calça intactos.
- Em 1ª pessoa não aparece mais a coronha na lateral do colete.
- A sombra do corpo inteiro aparece no chão, sem revólver.

**Para reverter ou trocar:**

- Aponte `Mesh` e `BodyVisible` de volta para `SM_SkeletalMesh_cowboy_character`.
- Alternativa sem mexer em asset nenhum: no *Initialize* dos dois ABPs, use `Show Material Section` (Material ID 7 e 8, `Show` = false, LOD 0..2) no componente dono. Esconde só na instância, mas mantém os vértices e as texturas carregadas.

**Preview:** a malha de preview dos dois ABPs não é exposta ao Python. No editor do ABP, troque em *Preview Scene Settings* → *Preview Mesh* = `SKM_Cowboy_NoGun`, só para visualizar.

**Por que `Always Tick` na malha-sombra.** Ela não é desenhada no *main pass*, então a engine a consideraria "não renderizada" e pararia de atualizar os ossos. Isso congelaria a sombra e também a fonte do *Copy Pose*. A malha visível pode usar `Only Tick…`, porque sai de cena junto com a câmera.

---

## 8. Validação no PIE (números reais)

| Situação | Resultado medido |
|---|---|
| Em pé, parado | Tornozelos a 10–11 cm, ponta do pé a 3 cm, pelve a 96 cm, cabeça a 164 cm. Câmera a 166 cm, pescoço 11 cm abaixo e 11 cm atrás |
| Andando (150 cm/s) | `Speed` 150, `BodyShift` 8,5–8,8 → pescoço a cerca de 10 cm atrás da câmera |
| Sprint (medido a 450 cm/s, antes da 4.1; hoje 360) | `BodyShift` ≈ 18. Os braços FP (`SKM_Metahuman_Arms`) aparecem balançando, o que é comportamento do FPMovement |
| Sprint a 360 cm/s (4.1) | Frente com `A_CB_Run_F` a 0,75×, laterais com Run_L/R a 0,85×, transição a 232 cm/s sem pés cruzados. Para trás ainda é o walk de costas acelerado |
| Agachado | `CrouchAlpha` 1, `RootOffset` (0, −30, 56), câmera a 80 cm, `StandW` 0 (camada 1P desligada). Olhando para baixo aparecem as coxas e os joelhos |
| Olhando para baixo, −75° | `BodyShift` 12, `Lean` −14° → peito e pontas das botas visíveis |
| Pulo | `InAirAlpha` ≈ 0,95 no ar |
| Sombra no chão (Mapa_B, sol direto) | A malha-sombra projeta o corpo inteiro, com cabeça e braços, visível tanto em 1P quanto em 3P |
| Visual 3ª pessoa (câmera de teste) | Idle, walk, strafe, back, sprint, crouch e crouch walk corretos, com os pés no chão |

Scripts de teste, todos só no PIE, sem salvar nada:

- `pie_mx2.py`: locomoção completa com câmera 3P e 1P.
- `pie_fpvis.py`: camada 1P.
- `pie_shadow.py`: liga e desliga a sombra da malha-sombra.

As capturas ficam em `Saved/Screenshots/WindowsEditor/` (`HighresScreenshot00042`–`00122`).

---

## 9. Performance e memória (Ryzen 5 5500X3D · RTX 5060 8 GB · 16 GB RAM)

**Custo novo:**

- Duas instâncias do `SKM_Cowboy_NoGun` (3 LODs; LOD0 com 8.715 vértices, 14.631 triângulos e 7 seções). Sem o cinturão/coldre e o revólver, o modelo caiu quase pela metade (seção 7.1).
- A malha-sombra entra **só** nos *shadow depth passes*; a visível entra só no *main pass*.
- CPU de animação:
  - um AnimGraph completo (2 BlendSpaces + blends);
  - uma cópia de pose;
  - dois `ModifyBone`.

  Para um único pawn, é pouco.

**Como medir** (no console do PIE):

- `stat unit` e `stat unitgraph`: Game, Draw e GPU.
- `stat anim`: custo de update e evaluate.
- `stat gpu` / `ProfileGPU`: passes de sombra e *base pass*.
- `stat streaming`: pool de texturas.
- **Unreal Insights** (`UnrealInsights.exe`): na barra de status, abra **Trace** → *Channels* e ligue `Animation`, ou inicie o editor com `-trace=default,animation`. Compare `UpdateAnimation` (Game Thread) com `EvaluateAnimation` (worker threads).
- **Animation Insights:** ative os plugins *Animation Insights*, *Insights Data Source Filters* e *Trace Data Filtering* em Editar (*Edit*) → Plugins, e depois abra Ferramentas (*Tools*) → Profile → *Animation Insights*. O **Rewind Debugger** mostra frame a frame qual nó do AnimGraph estava ativo.

**Memória, seu gargalo real:**

- As texturas do `Cowboy_character` são 4K/8K. No editor de cada textura, use uma destas opções (para 1ª pessoa, 2K sobra):
  - Detalhes → Compressão (*Compression*) → Avançado → `Maximum Texture Size` = 2048;
  - ou Nível de Detalhe (*Level Of Detail*) → `LOD Bias` = 1.
- Acompanhe `stat streaming` e ajuste `r.Streaming.PoolSize` para não estourar os 8 GB de VRAM junto com Lumen e Virtual Shadow Maps.
- **LOD da malha-sombra (opcional):** em Otimização → `Forced LOD Model` = 2 ou 3, na malha-sombra (0 = automático, 2 = LOD1, 3 = LOD2), reduz o skinning da sombra. **Teste antes:** se o LOD1/LOD2 do Cowboy remover ossos, o *Copy Pose* entrega esses ossos sem atualização para a malha visível.
- **Não copie esta configuração para NPCs.** Neles, use `Only Tick Pose When Rendered` + *Update Rate Optimizations* (URO) ou o *Animation Budget Allocator*.

**Alternativa nativa (5.5+): First Person Rendering.** O componente ganha `First Person Primitive Type`:

- *World Space Representation:* invisível para a câmera 1P, mas projeta sombra.
- *First Person:* FOV e escala próprios, sem sombra.

O equivalente da sua malha-sombra seria *World Space Representation*. As limitações:

- exige `Allow Static Lighting` desligado nas Configurações do Projeto;
- o auto-sombreamento é feito em *screen space*;
- há relatos no fórum de sombra ausente com VSM/CSM, contornados com `Lighting → Advanced → Hidden Shadow`.

A solução atual (`Render in Main Pass` off + `Cast Shadow`) não depende desses requisitos. O caso que justifica migrar é usar FOV separado nos braços FP.

---

## 10. C++ ou Blueprint?

| Lógica | Onde deixar | Motivo |
|---|---|---|
| EventGraph dos dois ABPs (um único personagem) | **Blueprint** | Poucos nós por frame. A agilidade de iterar compensa, e o ganho em C++ seria marginal |
| Mesmo ABP reaproveitado em NPCs, ou o Insights mostrando `BlueprintUpdateAnimation` pesado | **C++** (`UAnimInstance`) | Tira a VM de Blueprint do Game Thread. As contas vão para `NativeThreadSafeUpdateAnimation`, em worker thread |
| `GetSocketLocation` / câmera (camada 1P) | Game Thread (`NativeUpdateAnimation`) | Leitura de componentes não é *thread-safe* |

Versão C++ equivalente. Crie as classes por Ferramentas (*Tools*) → Nova Classe C++ (*New C++ Class*) → pai `AnimInstance`, e troque `YOURPROJECT_API` pela macro do seu módulo. No `Build.cs`, adicione `"AnimGraphRuntime"`.

```cpp
// CowboyFPAnimInstance.h  — substitui o EventGraph do ABP_CowboyFP
#pragma once
#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "CowboyFPAnimInstance.generated.h"

class ACharacter;

UCLASS()
class YOURPROJECT_API UCowboyFPAnimInstance : public UAnimInstance
{
    GENERATED_BODY()
public:
    UPROPERTY(EditDefaultsOnly, Category = "CowboyFP") float CrouchedHalfHeight = 40.f;
    UPROPERTY(EditDefaultsOnly, Category = "CowboyFP") float BackOffsetStand = 4.f;
    UPROPERTY(EditDefaultsOnly, Category = "CowboyFP") float BackOffsetCrouch = 30.f;

    UPROPERTY(BlueprintReadOnly, Category = "CowboyFP") float Speed = 0.f;
    UPROPERTY(BlueprintReadOnly, Category = "CowboyFP") float Direction = 0.f;
    UPROPERTY(BlueprintReadOnly, Category = "CowboyFP") float CrouchAlpha = 0.f;
    UPROPERTY(BlueprintReadOnly, Category = "CowboyFP") float InAirAlpha = 0.f;
    UPROPERTY(BlueprintReadOnly, Category = "CowboyFP") FVector RootOffset = FVector::ZeroVector;

protected:
    virtual void NativeInitializeAnimation() override;
    virtual void NativeUpdateAnimation(float DeltaSeconds) override;             // Game Thread: só copia estado
    virtual void NativeThreadSafeUpdateAnimation(float DeltaSeconds) override;   // Worker Thread: contas

private:
    UPROPERTY(Transient) TObjectPtr<ACharacter> OwnerCharacter = nullptr;        // UPROPERTY → o GC enxerga
    FVector CachedVelocity = FVector::ZeroVector;
    FRotator CachedRotation = FRotator::ZeroRotator;
    float StandingHalfHeight = 96.f;
    float CurrentHalfHeight = 96.f;
    bool bFalling = false;
};
```

```cpp
// CowboyFPAnimInstance.cpp
#include "CowboyFPAnimInstance.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Components/CapsuleComponent.h"
#include "KismetAnimationLibrary.h"

void UCowboyFPAnimInstance::NativeInitializeAnimation()
{
    Super::NativeInitializeAnimation();
    OwnerCharacter = Cast<ACharacter>(TryGetPawnOwner());
    if (OwnerCharacter)
    {
        StandingHalfHeight = OwnerCharacter->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    }
}

void UCowboyFPAnimInstance::NativeUpdateAnimation(float DeltaSeconds)
{
    Super::NativeUpdateAnimation(DeltaSeconds);
    if (!OwnerCharacter) { return; }
    CachedVelocity    = OwnerCharacter->GetVelocity();
    CachedRotation    = OwnerCharacter->GetActorRotation();
    CurrentHalfHeight = OwnerCharacter->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    bFalling          = OwnerCharacter->GetCharacterMovement()->IsFalling();
}

void UCowboyFPAnimInstance::NativeThreadSafeUpdateAnimation(float DeltaSeconds)
{
    Super::NativeThreadSafeUpdateAnimation(DeltaSeconds);
    Speed       = float(CachedVelocity.Size2D());
    Direction   = UKismetAnimationLibrary::CalculateDirection(CachedVelocity, CachedRotation);
    CrouchAlpha = FMath::Clamp((StandingHalfHeight - CurrentHalfHeight) / FMath::Max(StandingHalfHeight - CrouchedHalfHeight, 1.f), 0.f, 1.f);
    InAirAlpha  = FMath::FInterpTo(InAirAlpha, bFalling ? 1.f : 0.f, DeltaSeconds, 10.f);
    const float Back = FMath::Lerp(BackOffsetStand, BackOffsetCrouch, CrouchAlpha);
    RootOffset  = FVector(0.f, -Back, StandingHalfHeight - CurrentHalfHeight);   // +Y = frente do Cowboy
}
```

```cpp
// CowboyFPVisibleAnimInstance.h  — substitui o EventGraph do ABP_CowboyFP_Visible
#pragma once
#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "CowboyFPVisibleAnimInstance.generated.h"

class ACharacter;
class UCameraComponent;

UCLASS()
class YOURPROJECT_API UCowboyFPVisibleAnimInstance : public UAnimInstance
{
    GENERATED_BODY()
public:
    UPROPERTY(EditDefaultsOnly, Category = "FP") float NeckMinBehind = 10.f;
    UPROPERTY(EditDefaultsOnly, Category = "FP") float MaxBodyShift = 25.f;
    UPROPERTY(EditDefaultsOnly, Category = "FP") float LookDownShift = 12.f;
    UPROPERTY(EditDefaultsOnly, Category = "FP") float LeanStartPitch = -20.f;
    UPROPERTY(EditDefaultsOnly, Category = "FP") float LeanFullPitch = -75.f;
    UPROPERTY(EditDefaultsOnly, Category = "FP") float LeanMax = 14.f;

    UPROPERTY(BlueprintReadOnly, Category = "FP") FVector RootShift = FVector::ZeroVector;
    UPROPERTY(BlueprintReadOnly, Category = "FP") FRotator LeanRot = FRotator::ZeroRotator;

protected:
    virtual void NativeInitializeAnimation() override;
    virtual void NativeUpdateAnimation(float DeltaSeconds) override;   // Game Thread: lê socket e câmera

private:
    UPROPERTY(Transient) TObjectPtr<ACharacter> OwnerCharacter = nullptr;
    UPROPERTY(Transient) TObjectPtr<UCameraComponent> Camera = nullptr;
    float BodyShift = 0.f;
};
```

```cpp
// CowboyFPVisibleAnimInstance.cpp
#include "CowboyFPVisibleAnimInstance.h"
#include "GameFramework/Character.h"
#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"

void UCowboyFPVisibleAnimInstance::NativeInitializeAnimation()
{
    Super::NativeInitializeAnimation();
    OwnerCharacter = Cast<ACharacter>(TryGetPawnOwner());
    Camera = OwnerCharacter ? OwnerCharacter->FindComponentByClass<UCameraComponent>() : nullptr;
    if (USkeletalMeshComponent* Self = GetSkelMeshComponent())
    {
        for (const TCHAR* Bone : { TEXT("neck_01"), TEXT("upperarm_l"), TEXT("upperarm_r") })
        {
            Self->HideBoneByName(FName(Bone), PBO_None);
        }
    }
}

void UCowboyFPVisibleAnimInstance::NativeUpdateAnimation(float DeltaSeconds)
{
    Super::NativeUpdateAnimation(DeltaSeconds);
    if (!OwnerCharacter || !Camera) { return; }
    const FVector NeckRel = OwnerCharacter->GetMesh()->GetSocketLocation(TEXT("neck_01")) - Camera->GetComponentLocation();
    const float StandW  = FMath::GetMappedRangeValueClamped(FVector2f(0.f, -10.f), FVector2f(0.f, 1.f), float(NeckRel.Z));
    const float Pitch   = float(Camera->GetComponentRotation().Pitch);
    const float LookA   = FMath::GetMappedRangeValueClamped(FVector2f(LeanStartPitch, LeanFullPitch), FVector2f(0.f, 1.f), Pitch) * StandW;
    const float NeckFwd = float(FVector::DotProduct(NeckRel, OwnerCharacter->GetActorForwardVector()));
    const float Target  = FMath::Clamp(NeckFwd + NeckMinBehind, 0.f, MaxBodyShift) * StandW + LookDownShift * LookA;
    BodyShift = FMath::FInterpTo(BodyShift, Target, DeltaSeconds, 8.f);
    RootShift = FVector(0.f, -BodyShift, 0.f);          // espaço de componente do Cowboy: +Y = frente
    LeanRot   = FRotator(0.f, 0.f, -LeanMax * LookA);   // FRotator(Pitch, Yaw, Roll): roll negativo = tronco para trás
}
```

**Como migrar:**

1. Em cada ABP, apague as variáveis que têm o mesmo nome das `UPROPERTY` e os nós do EventGraph.
2. Em Configurações de Classe (*Class Settings*), troque `Parent Class` para a classe C++ correspondente.
3. Os pinos do AnimGraph passam a ler as `UPROPERTY` de mesmo nome. É *fast path*, sem VM de Blueprint.

---

## 11. Completar o pacote no Mixamo

**Configuração de download:**

- `Format`: FBX Binary (.fbx)
- `Skin`: **Without Skin**
- `Frames per Second`: **30**
- `Keyframe Reduction`: none
- `In Place`: marque quando a opção existir. É opcional, porque o pipeline remove a translação de qualquer forma.

Coloque os arquivos em `Content/AnimationAdobe`, ou na pasta definida em `MIXAMO_SRC`.

Por prioridade (os nomes variam no site, então busque pelo termo):

| # | Buscar no Mixamo | Substitui hoje | Ganho |
|---|---|---|---|
| 1 | Idle em pé ("Breathing Idle" / "Idle") | `A_CB_Idle` (pose estática do *Stop Walking*) | Idle vivo |
| 2 | "Walking" (sem maleta) | `A_CB_Walk_F` (maleta corrigida por espelho) | Braços naturais na sombra |
| 3 | "Running Backward" (e, se quiser o mesmo estilo Mixamo na frente, "Running" / "Jogging") | Sprint para trás (Walk_B ×2,66). Para frente já existe `A_CB_Run_F` (4.1) | Corrida de costas real, o maior ganho visual que falta |
| 4 | Crouch andando para trás e para os lados ("Crouched Walking" back, "Crouched Sneaking Left/Right") | `Crouch_B` (reverso) e `Crouch_L/R` (sintéticos) | Crouch lateral autêntico |
| 5 | "Falling Idle", "Jump" / "Jumping Up", "Falling To Landing" | `A_CB_Fall` (pose estática) | Pulo e aterrissagem |
| 6 | Opcional: "Standing To Crouched" / "Crouched To Standing", "Left/Right Turn 90" | — | Transições e *turn in place* |

**Para integrar:**

1. Acrescente o bloco correspondente no `prep_all.py`.
2. Rode o Blender e copie a saída para `SourceArt/MixamoFP_v2/`.
3. Rode `import_mixamo2.py` e depois `setup_retarget.py` (o `setup_retarget.py` mede a velocidade nova).
4. Ajuste as listas `stand` e `crouch` do `create_assets.py`.
5. Rode o `create_assets.py`.
6. Abra os BlendSpaces e salve.

Todos os scripts rodam pelo console do editor com `py "C:/…/Tools/MixamoFP/<script>.py"`.

---

## 12. Limpeza sugerida (você decide; eu não apaguei nada)

- `/Game/FreeAnimationLibrary/_Retarget_CowboyFP/`: sobra da tentativa anterior.
- `SourceArt/MixamoFP/` (v1, esqueleto deitado). A versão válida é a `SourceArt/MixamoFP_v2/`.
- `Content/AnimationAdobe/`: são FBX brutos dentro de `Content`. Mova para `SourceArt/MixamoRaw/`, definindo `MIXAMO_SRC` para o Blender achar, e assim não mistura arquivo-fonte com `.uasset`.
- `Saved/Screenshots/WindowsEditor/HighresScreenshot00042`–`00122` e `Saved/MixamoFP_*.txt`: capturas e logs de teste.
- `Tools/MixamoFP/`: os `pie_*`, `inspect_*`, `probe_*`, `dump_*`, `check_*` e `*_check.py` são diagnósticos.
  - **Pipeline reutilizável:** `blender/*` → `import_mixamo2.py` → `setup_retarget.py` → `create_assets.py` → `run_prepare.py` (sync markers + `A_CB_Run_F`) → `run_apply.py <velocidade>`.
  - **Atenção ao rodar o `create_assets.py` de novo:** ele recria a linha de corrida antiga (450 e walk acelerado). Rode `run_prepare.py` e `run_apply.py 360` depois dele.
  - **Histórico de construção, não precisa rodar de novo:** `wire_mixamo.py`, `vis_vars.py`, `wire_vis2.py`, `fix_update*.py`, `vis_patch.py`, `wire_vis3.py`, `wire_vis4.py` e `t3d/*`. Os grafos foram gerados como texto T3D, colados no editor e ligados por esses scripts.

---

## 13. Limitações conhecidas e próximos passos

- **Sprint:** para frente já usa uma corrida real (`A_CB_Run_F`, 4.1). **Para trás** continua com o walk de costas a 2,66×, até baixar o "Running Backward" (item 3 da lista). O som dos passos no sprint depende do `Set Play Rate` = 2,2 fixo no `BP_Player` (4.1).
- **Turn in place:** o corpo gira junto com a cápsula (o FPMovement usa o *yaw* do controller). Ao girar parado, os pés rodam no lugar. Uma evolução possível é um *root yaw offset* com animações de giro.
- **Escadas e rampas:** ainda não há *Foot Placement* nem *Leg IK*, então em degraus os pés podem flutuar ou atravessar.
- **Reflexos e espelhos:** mostram a malha visível, sem cabeça e com a inclinação 1P. Para um espelho, habilite a malha-sombra no *Scene Capture*.
- **Multiplayer:** seria necessário `Only Owner See` na `BodyVisible` e `Owner No See` + main pass ligado na malha-sombra para os outros jogadores.
- **Sombra dos braços FP:** se o `FirstPersonMesh` tiver `Cast Shadow` ligado, aparecem dois pares de braços na sombra. Para desligar sem tocar no `BP_Player`: `BP_Player_Cowboy` → componente herdado `FirstPersonMesh` → Iluminação → `Cast Shadow` = off.
- **Mapa_B:** se ainda tiver um `BP_ThirdPersonCharacter1` com `Auto Possess Player` = Player 0, ele toma o controle e o pawn do GameMode não é usado. Corrija em Detalhes → Peão (*Pawn*) → `Auto Possess Player` = *Disabled*.

---

## 14. Fontes

- Epic, retargeting:
  - [IK Rig Animation Retargeting (5.8)](https://dev.epicgames.com/documentation/en-us/unreal-engine/ik-rig-animation-retargeting-in-unreal-engine)
  - [Auto Retargeting (5.8)](https://dev.epicgames.com/documentation/unreal-engine/auto-retargeting-in-unreal-engine?lang=en-US)
  - [Animation Retargeting (5.8)](https://dev.epicgames.com/documentation/en-us/unreal-engine/animation-retargeting-in-unreal-engine)
- Epic, pose entre malhas:
  - [Copy a Pose (5.8)](https://dev.epicgames.com/documentation/en-us/unreal-engine/copy-a-pose-in-unreal-engine)
  - [Working with Modular Characters (5.8)](https://dev.epicgames.com/documentation/en-us/unreal-engine/working-with-modular-characters-in-unreal-engine): Leader Pose × Copy Pose × Merge
- Epic, 1ª pessoa:
  - [First Person Rendering (5.8)](https://dev.epicgames.com/documentation/en-us/unreal-engine/first-person-rendering)
  - [EFirstPersonPrimitiveType](https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Runtime/Engine/EFirstPersonPrimitiveType)
  - Fórum: [No Shadows From World Space Representation](https://forums.unrealengine.com/t/no-shadows-from-world-space-representation-first-person-rendering/2701045)
- Epic, performance de animação:
  - [Animation Optimization (5.8)](https://dev.epicgames.com/documentation/unreal-engine/animation-optimization-in-unreal-engine?lang=en-US)
  - [Property Access (5.8)](https://dev.epicgames.com/documentation/unreal-engine/property-access-in-unreal-engine)
  - [Graphing in Animation Blueprints (5.8)](https://dev.epicgames.com/documentation/en-us/unreal-engine/graphing-in-animation-blueprints-in-unreal-engine)
  - [EVisibilityBasedAnimTickOption](https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/Engine/EVisibilityBasedAnimTickOption)
  - Fórum: [VisibilityBasedAnimTickOption not working as expected](https://forums.unrealengine.com/t/visibilitybasedanimtickoption-not-working-as-expected/450700)
- Epic, profiling:
  - [Animation Insights (5.7)](https://dev.epicgames.com/documentation/en-us/unreal-engine/animation-insights-in-unreal-engine)
  - [Unreal Insights Reference (5.8)](https://dev.epicgames.com/documentation/unreal-engine/unreal-insights-reference-in-unreal-engine-5?lang=en-US)
  - [Trace (5.8)](https://dev.epicgames.com/documentation/en-us/unreal-engine/trace-in-unreal-engine-5)
- Comunidade, câmera 1P:
  - [True First Person Camera (Froyok)](https://www.froyok.fr/blog/2018-06-true-first-person-camera-in-unreal-engine-4/)
  - [Community Tutorial: True First Person Camera no UE5](https://forums.unrealengine.com/t/community-tutorial-how-to-create-a-true-first-person-camera-in-unreal-engine-5-full-tutorial/2528062)
- Epic, esconder partes da malha:
  - [Show Material Section (Blueprint API)](https://dev.epicgames.com/documentation/en-us/unreal-engine/BlueprintAPI/Components/SkinnedMesh/ShowMaterialSection?application_version=5.2)
- Comunidade, remover seções de um Skeletal Mesh dentro do UE:
  - [Delete Skeletal Mesh Sections sem Blender (Skeletal Mesh Editing Tools)](https://www.reactkeyblog.com/en/posts/[ue5]-no-blender-needed!-how-to-delete-skeletal-mesh-sections-and-bones-inside-unreal-engine/3cbc1065-c3e3-4fff-9c00-4446681329b2)
- Comunidade, Mixamo:
  - [UNAmedia: importar animação Mixamo no UE5](https://www.unamedia.com/ue5-mixamo/docs/import-mixamo-animation-in-ue5/)
  - [UNAmedia: root motion Mixamo](https://www.unamedia.com/ue5-mixamo/docs/mixamo-root-motion-animations/)
  - [mixamo2unreal (IK rigs Mixamo para UE 5.2+)](https://github.com/arbitrarygames/mixamo2unreal)
