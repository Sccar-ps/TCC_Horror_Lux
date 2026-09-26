# Mobília e ambientação do Mapa_B

Tudo foi feito por script, no editor aberto, em 25/09/2026 (UE 5.8.3). Os scripts ficam em `Tools/Furnish/`.

> **O mapa não foi salvo.** Revise e grave com Ctrl+S. Se não gostar, rode o modo `clear` (seção 1) ou use Ctrl+Z: cada execução do `furnish.py` é uma única transação ("LUX: mobiliar Mapa_B").

Comparação antes/depois: `Tools/Furnish/Mapa_B_antes_depois.jpg`.

---

## 0. Resumo

| O quê | Quantidade | Onde fica |
|---|---|---|
| Móveis e objetos | ~90 móveis, quadros e objetos soltos + 368 livros e potes nas estantes | Organizador (*Outliner*) → pastas `LUX/Sala`, `LUX/Corredor`, `LUX/Quarto`, `LUX/Escritorio` |
| Luzes práticas (abajur, arandela, vela) | 12 PointLights | `LUX/Luzes` |
| Sujeira (decals) | 7 no chão + 7 infiltrações nas paredes | `LUX/Decals` |
| Som ambiente | 1 drone global + 3 ventos nas janelas | `LUX/Som` |
| Colisão invisível | 21 cubos | `LUX/Colisao` |
| Paredes e tetos | 38 slots de material trocados, por override no ator | Detalhes (*Details*) → Materiais dos atores `CubeGridToolOutput*` |
| RectLights do teto que já existiam | 6 luzes, de 6500 K para 4500 K | as mesmas luzes (`RectLight`, `RectLight2`...) |

Todos os atores criados levam a tag `LUX_FURNISH`. Nenhum asset `_GENERATED` de vocês foi alterado.

**Assets novos** (em `/Game/Masion/LUX/`, que é versionado):

| Asset | Tamanho | Para quê |
|---|---|---|
| `Materials/M_LUX_Surface` | 33 KB | Material mestre das paredes: UV projetado no mundo, dessaturação, tint |
| `Materials/MI_LUX_Wallpaper_Old` | 11 KB | Papel de parede com lambri (em uso) |
| `Materials/MI_LUX_WoodPlanks_Old`, `MI_LUX_Wallpaper_Plain` | 13 KB cada | Alternativas prontas para testar |
| `Materials/MI_LUX_Plaster_Ceiling` | 11 KB | Gesso escuro dos tetos (filho do `MI_PlasterCream` do SICKA) |
| `Audio/SW_LUX_Amb_Memorias` | **19,6 MB** | Cópia do `5_LOOP_Backrooms_Memories` com *Looping* ligado. Vai para o LFS |

---

## 1. Como rodar

Console do editor (a caixa **Cmd** no rodapé):

```
py "C:/Users/bruno/Documents/Unreal Projects/TCC_Horror_Lux/Tools/Furnish/make_materials.py"
py "C:/Users/bruno/Documents/Unreal Projects/TCC_Horror_Lux/Tools/Furnish/furnish.py"
```

| Comando | O que faz |
|---|---|
| `make_materials.py` | Cria ou atualiza o mestre e as MIs. Reconstrói o grafo do mestre a cada execução |
| `furnish.py` | Apaga tudo que tem a tag `LUX_FURNISH`, restaura materiais e luzes originais e aplica tudo de novo. Log em `Saved/Furnish/furnish_log.txt` |
| `furnish.py clear` | Remove tudo e devolve paredes, tetos e RectLights ao estado original |
| `furnish.py apply MI_LUX_WoodPlanks_Old` | Igual ao padrão, mas com outra MI nas paredes |

Os materiais e luzes originais ficam em `Saved/Furnish/furnish_backup.json`, gravado só na primeira execução. **Não apague esse arquivo** enquanto quiser poder usar o `clear`.

Para mudar a posição de um móvel, edite a linha dele nas funções `sala()`, `corredor()`, `quarto()` e `escritorio()` e rode de novo. Os comentários do script explicam o formato: `put(malha, x, y, frente_em_graus, z, ...)`.

---

## 2. O que entrou em cada cômodo

Faces internas medidas na malha (cm): Sala x[−3000, −2052] y[−1940, −350] · Corredor x[−3402, −3149] y[−700, 850] · Quarto x[−3614, −2510] y[900, 1740] · Escritório x[−3855, −3107] y[−1500, −729].

| Cômodo | Móveis e objetos |
|---|---|
| **Sala** | Mesa de centro com livros, copo e garrafa. Abajur de chão ao lado do sofá. Banquinho com vela. Piano com banco, duas velas e cabeça de cervo na parede oeste. Canto de leitura (cadeira e candelabro). Baú e estante com livros junto à porta de saída. Prateleira de parede. 4 quadros |
| **Corredor** | Aparador com livros e vela. Cadeira solitária encostada na parede. 2 arandelas. 5 molduras, **4 delas vazias de propósito**: é a amnésia do Santos, as memórias que faltam. Uma porta de loop pode ir trocando o que aparece nelas |
| **Quarto** | Criado-mudo com vela, livro e copo, e banquinho do outro lado. Armário-cristaleira com livros. Cômoda com vela. Baú ao pé da cama. Cadeira. Abajur de chão. 2 quadros |
| **Escritório** (era o cômodo vazio) | Escrivaninha com papéis espalhados, livros, vela, garrafa, copo e um osso. Cadeira. Quadro de investigação com 6 papéis pregados. Armário e estante cheios de livros. Baú. Candelabro. Papéis no chão. Cortinas nas 3 janelas |

Os livros das estantes foram distribuídos por *line trace*: o script acha a altura de cada prateleira na própria malha. Por isso eles assentam certo, com tamanhos variados.

---

## 3. Paredes e tetos

**Problema encontrado:**
- As paredes usavam o `Wood_Dark` do rack de TV (textura de madeira de 4K esticada).
- O teto do quarto estava com o `WorldGridMaterial`, o xadrez padrão da engine.

**UV das CubeGrid:** o UV varia entre as paredes. A maioria usa 1 UV = 100 cm, mas a parede sul da sala está girada, com 123 cm por UV. Por isso o `M_LUX_Surface` **projeta a textura pelas coordenadas de mundo**: (y, −z) nas paredes voltadas para X e (x, −z) nas voltadas para Y. O lambri fica na mesma altura em todas as paredes.

Parâmetros do `MI_LUX_Wallpaper_Old` para ajuste fino (abra a MI no Navegador de Conteúdo, *Content Browser*):

| Parâmetro | Valor | Efeito |
|---|---|---|
| `Tiling` | 0,4 | Uma repetição a cada 2,5 m. O lambri fica embaixo e aparece uma faixa de madeira perto do teto |
| `OffsetV` | 0 | Desloca o padrão na vertical |
| `Desaturation` | 0,65 | Tira o vermelho de saloon do tecido |
| `Tint` | (0,26, 0,25, 0,23) | Escurece. Paredes mais claras = mais GI do Lumen = casa mais iluminada |

A troca foi feita com override de material **no componente do ator**. Os assets `_GENERATED` continuam com os materiais originais.

---

## 4. Luzes

As RectLights de teto de vocês têm entre 0,6 e 1,3 cd. As luzes novas seguem essa escala: uma vela fica em torno de 1/30 de uma luz de teto. Com valores "reais" (vela = 1 cd), o olho virtual escurecia o resto da casa e as velas estouravam em laranja.

| Luz | cd | Raio | Temperatura | Sombra |
|---|---|---|---|---|
| Abajur da sala | 1,0 | 480 | 2700 K | sim |
| Abajur do quarto | 0,9 | 480 | 2700 K | sim |
| Arandelas do corredor (2) | 0,35 | 360 | 2700 K | só a 1ª |
| Vela da escrivaninha | 0,1 | 380 | 2200 K | sim |
| Demais velas e candelabros (7) | 0,04 a 0,05 | 200 a 240 | 2200 K | não |

- **Luzes com sombra:** 4, pela recomendação da seção 5.4 do guia de iluminação (sombra só onde conta).
- **Arandelas:** a malha tem `Cast Shadow` desligado, porque a luz fica dentro da lanterna.
- **RectLights existentes:** passaram para 4500 K. Com 3300 K a casa virou um saloon laranja.

---

## 5. Sujeira e som

- **Decals:**
  - `MI_Decal_Debris_Dirt_02_A` no chão.
  - `MI_Decal_Leak_Dirt_02` nas paredes, entre 1,3 e 3,9 m de altura.
  - O `_B` (poeira clara) foi descartado, porque saía branco sob a exposição do mapa.
- **Drone global:** `SW_LUX_Amb_Memorias`, não espacializado, volume 0,22.
  - Os *cues* `LOOP` do Backrooms **não fazem loop**: duram 102 s e acabam. Por isso a cópia tem *Looping* ligado.
- **Vento:** `SW_Wind_calm` (já em loop, do FPMovement) em 3 pontos. Janelas do corredor, do escritório e da sala, com atenuação de 120 cm de raio e *falloff* de 650 cm.

---

## 6. Colisão

Todas as malhas do `Scene_Saloon` usadas aqui estão **sem colisão simples**: cadeiras, mesa, estantes, baú, abajur e cômoda. Nelas o jogador atravessaria o móvel. Medido pelo `check_collision.py`:

- `box_elems`, `convex_elems` etc. = 0 nessas malhas;
- as do OldWest têm convex.

**Solução sem tocar nos assets:** cada móvel ganhou um cubo invisível (`LUX/Colisao`) com o perfil `InvisibleWall`.
- Esse perfil bloqueia o Pawn e ignora o canal Visibility, então não atrapalha a interação.
- Cama, sofá e rack que já estavam no mapa também ganharam o cubo.
- **Por que não re-salvar os assets com colisão:** cada `.uasset` desses tem mais de 100 MB no LFS (seção 6 do `GUIA_DO_PROJETO.md`).

---

## 7. Custo medido

`stat unit` no viewport do editor, depois de tudo:

| Métrica | Valor |
|---|---|
| GPU Time | 5,19 ms |
| Draws | 586 |
| Prims | 70,8 K |
| VRAM | 3,65 GB |

- **Comparação com o guia de iluminação:** lá eram 4,59 ms, mas com outra câmera, então não é um A/B exato. A ordem de grandeza é +0,6 ms de GPU.
- **CPU:** a medida que vale continua sendo Standalone ou build, seção 4 do `GUIA_ILUMINACAO_EXPOSICAO.md`.
- **Se pesar:** os ~370 livros são atores separados. O próximo passo seria juntá-los em Instanced Static Mesh por estante.

---

## 8. Coisas que encontrei no mapa e não mexi

1. **76 atores sem malha:**
   - São 70 `SM_FramePattern_UV_*` e 6 `SM_FullColumn_UV_*` (SICKA), com `StaticMesh = None`. Provavelmente o mapa foi salvo numa máquina sem o SICKA.
   - Os do corredor estão em x = −3450 e −3098, **dentro** das paredes atuais. Só restaurar a malha não resolve.
2. **`BP_BaseDoor3`** em (−2404, −652), entre o sofá e a TV, sem malha.
3. **Não há PlayerStart** no `Mapa_B`.
4. **Céu nas janelas:** pôr do sol claro. Para uma noite de terror, escureça o céu ou a DirectionalLight.
5. **Exposição:** o `Min EV100 = −8` do `PPV_Global` deixa o olho clarear bastante os cantos escuros. O guia de iluminação já sugere −6 ou −5 para um escuro "físico". É o ajuste que mais muda o clima, e não mexi por ser decisão artística.
6. **Dependência de packs:** o mapa agora usa OldWest (piano, cristaleira, quadro de avisos, cervo, velas, arandelas) e SICKA (o gesso do teto). Os dois continuam no `.gitignore`. Vocês disseram que todos os devs já têm os packs. Mesmo assim, quem clonar sem eles vê esses objetos sumirem.

---

## 9. Incidente durante o trabalho

- **O que aconteceu:** o primeiro script de análise de malhas (`analyze_sections.py`) derrubou o editor com um *access violation* dentro do Python da engine.
- **Recuperação:** o `Mapa_B` e mais 4 assets não salvos voltaram pelo *Restore Packages*, a partir do autosave das 19:14. Conferi depois do restart: 151 atores, dump idêntico ao de antes do crash.
- **O que ficou:** o script foi desativado e substituído pelo `export_sections.py`, que só usa chamadas já testadas.

## 10. Scripts

| Script | Função | Altera algo? |
|---|---|---|
| `furnish.py` | Aplica e remove tudo | Sim (1 transação) |
| `make_materials.py` | Material mestre e MIs | Cria e salva assets em `/Game/Masion/LUX/Materials` |
| `dump_scene.py`, `export_geometry.py`, `export_sections.py`, `inspect_assets.py`, `check_collision.py` | Levantamento (planta, UVs, pivôs, colisão). Saída em `Saved/Furnish/` | Não |
| `cam.py x y z pitch yaw` | Posiciona a câmera do viewport | Não |
| `lineup.py` | Enfileira as malhas para descobrir a "frente" de cada uma (`lineup.py clear` remove) | Temporário |
| `analyze_sections.py` | Desativado (causou o crash) | — |
