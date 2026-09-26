# Loop estilo P.T. no Mapa_B

Montado por script em 26/09/2026 (UE 5.8.3), só com Blueprint. A primeira versão passou em 22 de 22 checagens no PIE e o mapa foi salvo.

**Versão 2 (26/09, 14h50): troca fluida.** A câmera desliza até a maçaneta, pisca por ~0,1 s e volta aos olhos enquanto a porta abre. O som de abrir agora é tocado pelo manager. Aplicar com `setup_loop.py rebuild` e depois Ctrl+S. Ainda não foi testada no PIE.

Scripts em `Tools/Loop/`. Logs e prints em `Saved/Loop/`.

---

## 0. O que foi criado

| Peça | Onde | Função |
|---|---|---|
| `BP_LuxLoopManager` | `/Game/Masion/LUX/Loop/` | Faz a troca, conta os loops, aplica as mudanças de cada loop e fecha a porta do quarto atrás do jogador |
| `BP_LuxLoopDoor` | `/Game/Masion/LUX/Loop/` | Filho da `BP_BaseDoor`. Ao interagir, não abre: pede a troca ao manager |
| `LOOP_Manager` | Organizador (*Outliner*) → `LUX/Loop`, no corredor, 2,5 m à frente da porta do quarto | Instância do manager. A caixa `GatilhoFechar` cobre a largura do corredor |
| `LOOP_PortaSala` | Em cima da `BP_BaseDoor5` (porta da sala) | Porta de loop, com o mesmo transform da porta real |
| `LOOP_Chegada` | Target Point no quarto, 85 cm da porta, virado para o corredor | Onde o jogador reaparece |
| `LOOP_CamSala` e `LOOP_CamQuarto` | Câmeras a 35 cm da maçaneta de cada porta, do lado de quem abre, FOV 45 | O close da maçaneta. Como a pose relativa à maçaneta é a mesma, o quadro quase não muda na piscada |
| `LOOP_PlayerStart` | Corredor, de costas para o quarto | O mapa não tinha PlayerStart |

Todos os atores levam a tag `LUX_LOOP`.

Mudanças em atores que já existiam:
- `BP_BaseDoor5`: textos do prompt trocados de "Close Door"/"Open Door" para "Abrir Porta"/"Fechar Porta", iguais aos da porta do quarto.
- `BP_BaseDoor7`: nenhuma. A folha foi conferida e está fechada.

---

## 1. Como funciona

| Passo | O jogador vê | O que acontece |
|---|---|---|
| 1 | Interage com a porta da sala | `BP_LuxLoopDoor` chama `PedirTroca`. Movimento e câmera travam |
| 2 | A câmera desliza até a maçaneta (0,5 s, *ease in-out*; o FOV vai do da câmera do jogador para 45) | `SetViewTargetWithBlend` para a `LOOP_CamSala` |
| 3 | Piscada: 0,08 s escurecendo e 0,04 s no preto | Na tela preta: teleporte para a `LOOP_Chegada`, vista trocada para a `LOOP_CamQuarto` (o mesmo close, na porta do quarto), *camera cut*, `LoopAtual + 1` e tags do loop |
| 4 | Clareia em 0,2 s. A maçaneta se afasta e a porta abre para o corredor | A porta do quarto abre pelo próprio `Interact`. O som de abrir é tocado pelo manager nesse instante |
| 5 | A câmera volta aos olhos (0,9 s) enquanto a porta termina de abrir | `SetViewTargetWithBlend` de volta para o jogador. Depois, o input é liberado |
| 6 | Anda ~2 m pelo corredor | A caixa `GatilhoFechar` fecha a porta do quarto atrás dele |
| 7 | Volta e abre essa porta | É a porta real do quarto, então ela dá no quarto |
| Final | Depois da troca de número `LoopFinal` | A porta de loop some e a `BP_BaseDoor5` real aparece. Na próxima interação, a porta da sala abre de verdade |

**Por que o som falhava na v1.** A `BP_BaseDoor` só toca o som de abrir quando a folha passa entre 0° e 4°, uma janela de 1 ou 2 frames. No frame da troca, o Lumen e as sombras recalculam o lugar novo, e esse frame costuma demorar. Com isso a folha pula a janela e o som não toca.

Na v2, o manager deixa o `OpenSound` da porta do quarto vazio durante essa abertura e toca o som em 2D. Ser 2D evita que o som "salte" de posição na troca. O `OpenSound` é devolvido ao fim da sequência, então aberturas manuais continuam com som.

---

## 2. Por que foi feito assim

- **Blueprint, não C++.**
  - O projeto não tem `Source/`. O `LuxLoopManager` em C++ da conversa anterior obrigaria os 5 integrantes a compilar o projeto.
  - A troca roda uma vez por loop, então não há ganho de performance em C++.
  - O UE 5.8 tem API Python de grafos (`BlueprintGraphEditor`). Com ela, os Blueprints são gerados por script e podem ser refeitos.
- **Deslize até a maçaneta + piscada curta, em vez de apagão.**
  - Na v1, a tela ficava preta por 0,45 s e voltava com a vista em outro lugar e noutra direção. Isso denunciava o teleporte.
  - Na v2, a troca acontece entre dois closes quase iguais, com a câmera em movimento antes e depois. É o "corte na ação" do cinema: o movimento contínuo e o som que atravessa o corte escondem o salto.
  - As portas não são idênticas (largura 1,1 contra 1,3, vidro, luz de cada cômodo). Por isso ainda há uma piscada de ~0,1 s; sem ela, a diferença de luz no vidro "pula".
  - Para testar a troca seca, zere `TempoEscurecer` e `TempoApagado`.
  - Para esconder mais o salto, deixe as duas portas com a mesma escala (hoje `BP_BaseDoor5` usa 1,1 e `BP_BaseDoor7` usa 1,3).
- **Ponto de chegada fixo em vez de pose relativa.**
  - O jogador sempre reaparece no mesmo lugar, olhando para a porta, e nunca cai dentro de um móvel. A volta da câmera aos olhos acontece com a porta abrindo, então o salto não aparece.
- **Porta real escondida embaixo da porta de loop.**
  - A API de script não cria o nó *Call to Parent Function*, então a porta de loop não consegue "abrir como porta normal" no final.
  - Trocar a visibilidade das duas no último loop resolve sem mexer na `BP_BaseDoor`, que é compartilhada com o resto do projeto.

---

## 3. Mudanças por loop (sem abrir Blueprint)

Cada mudança é uma tag no ator: selecione o ator e vá em **Detalhes → Ator → Tags → +**.

| Tag | Efeito |
|---|---|
| `LOOP3_ON` | Começa escondido e aparece a partir do loop 3 |
| `LOOP3_OFF` | Some no loop 3 |

- **O que esconder significa:** render, colisão e som. Um *Ambient Sound* toca ao aparecer e sai em fade de 1 s ao sumir.
- **Tipos de ator:** vale para malhas, luzes, decals, Local Fog Volumes e sons.
- **Várias tags:** um ator pode ter mais de uma, por exemplo `LOOP2_ON` e `LOOP4_OFF`.
- **Limite:** tags `_ON` acima de `LoopFinal` são ignoradas.
- **Loop 1:** é a primeira volta, depois da primeira troca.

Roteiro sugerido (cada loop isola um recurso do TCC):

| Loop | Mudança (exemplo) | Recurso |
|---|---|---|
| 1 | Nada. O jogador precisa reconhecer o corredor | Linha de base |
| 2 | Duplicar uma moldura vazia do corredor com a foto da Lia → `LOOP2_ON` | Storytelling ambiental |
| 3 | `LUX_Luz_Corredor_Arandela3` e `LUX_Luz_Corredor_Arandela5` → `LOOP3_OFF`; uma vela nova → `LOOP3_ON` | Luz pontual |
| 4 | *Ambient Sound* de batidas, com Auto Activate → `LOOP4_ON` | Som de antecipação |
| 5 | Cadeira duplicada e virada para a porta → `LOOP5_ON`; a original → `LOOP5_OFF` | Clímax |

Para lógica que tag não resolve (trocar material, mexer na névoa), abra o `BP_LuxLoopManager` e continue o fluxo do evento `PedirTroca` depois dos dois `AplicarTag`. Nesse ponto a tela ainda está preta.

---

## 4. Parâmetros

Ficam no `LOOP_Manager`, em **Detalhes → Loop**.

| Parâmetro | Padrão | Uso |
|---|---|---|
| `LoopFinal` | 5 | Número de trocas antes de a porta da sala abrir de verdade |
| `TempoAproximar` | 0,5 s | Deslize da câmera até a maçaneta |
| `TempoEscurecer` | 0,08 s | Piscada: fade para preto |
| `TempoApagado` | 0,04 s | Piscada: tempo no preto. A troca acontece aqui |
| `TempoClarear` | 0,2 s | Piscada: fade de volta |
| `TempoAfastar` | 0,9 s | Volta da câmera aos olhos, com a porta abrindo |
| `SomTroca` | vazio | Som 2D opcional no momento da interação. Sugestão: o bipe do monitor hospitalar do roteiro |
| `PortaQuarto`, `PortaSaida`, `PortaLoop`, `Chegada`, `CamSala`, `CamQuarto` | já apontados | Só mude se trocar as portas |

O volume do som de abrir (0,4) fica no nó `PlaySound2D` depois do `Interact`, no evento `PedirTroca`.

- **Ponto de chegada:** pode mover a `LOOP_Chegada` à vontade. A seta indica para onde o jogador olha.
- **Gatilho:** pode mover o `LOOP_Manager` à vontade. Ele deve ficar fora do arco da porta do quarto, que invade cerca de 1,3 m do corredor.

---

## 5. Scripts

Os comandos vão no console do editor (a caixa **Cmd** no rodapé), com o `Mapa_B` aberto.

```
py "C:/Users/bruno/Documents/Unreal Projects/TCC_Horror_Lux/Tools/Loop/setup_loop.py"
py "C:/Users/bruno/Documents/Unreal Projects/TCC_Horror_Lux/Tools/Loop/test_loop.py"
```

| Script | O que faz |
|---|---|
| `setup_loop.py` | Refaz os atores `LUX_LOOP` do mapa e o grafo da `BP_LuxLoopDoor`. O `BP_LuxLoopManager` existente é mantido, com as edições feitas à mão. Desfazer: Ctrl+Z ("LUX: loop"). Não salva o mapa. Log em `Saved/Loop/setup_log.txt` |
| `setup_loop.py rebuild` | Refaz o EventGraph do `BP_LuxLoopManager` (edições à mão nele se perdem) e acrescenta as variáveis que faltarem. Fecha antes as janelas dos dois Blueprints e nunca remove grafos de função (veja a seção 7) |
| `test_loop.py` | Roda o PIE, faz as 5 trocas pela função `Interact` do `BP_Player` (o trace real), confere tudo e sai. Cria e remove dois atores de teste. Resultado em `Saved/Loop/test_log.txt` e prints `test_*.png` |
| `probe_loop*.py` | Levantamento, só leitura |

---

## 6. Teste e custo

Teste de 26/09 (`test_log.txt`), 22 de 22 checagens:

- **Início:** `LOOP2_ON` escondido, `LOOP3_OFF` visível, porta real escondida.
- **Loops 1 a 5:** troca (0 cm do ponto de chegada), porta do quarto abrindo, porta fechando atrás.
- **Tags:** `LOOP2_ON` aparece no loop 2 e `LOOP3_OFF` some no loop 3.
- **Final:** a porta de loop some, a real aparece e abre.

Custo:
- **Por frame:** zero. O manager não tem Tick, só a caixa de overlap.
- **Por troca:** um teleporte e duas buscas por tag (`GetAllActorsWithTag` em cerca de 620 atores), uma vez por loop.
- **Memória:** ator escondido continua carregado. Se um loop precisar de conteúdo pesado (mais de ~50 MB no Size Map), coloque num subnível e carregue com *Load Stream Level* um loop antes.

---

## 7. Observações

1. **O conteúdo dos loops ainda não existe.** Nenhum ator do mapa tem tag `LOOPn` ainda. A seção 3 mostra como marcar.
2. **O final abre para o vazio.** No teste, a porta real da sala mostrou o exterior azul-escuro. Falta um destino, por exemplo um gatilho atrás da porta que carrega a cena do hospital.
3. **Corredor claro demais no PIE.** Nos prints do teste o corredor aparece claro e enevoado, bem diferente da vista do editor. O mais provável é a lanterna do `BP_Player_Cowboy` na névoa volumétrica: é o item "Lanterna × névoa" que ficou pendente no `ATMOSFERA_MAPA_B.md`.
4. **Incidente.**
   - O que aconteceu: um `rebuild` com o `BP_LuxLoopManager` aberto no editor derrubou o editor às 14:20. O script estava removendo funções de um Blueprint carregado.
   - O que se perdeu: só as mudanças deste trabalho, que ainda não estavam salvas, e elas foram refeitas.
   - O que mudou: o script fecha as janelas dos Blueprints antes de editar e nunca remove grafos de função.
   - **Segundo crash, às 15:01, no `rebuild` da v2.**
     - Causa provável: com o `BP_LuxLoopManager` carregado do disco, o script não achou a caixa `GatilhoFechar` e criou outra com o mesmo nome. O editor caiu ao continuar editando o Blueprint.
     - O que mudou: a caixa só é criada quando o Blueprint é novo, e os atores `LUX_LOOP` saem do mapa antes de o Blueprint ser editado.
     - Diagnóstico: o log `Saved/Loop/setup_log.txt` agora é gravado a cada passo, então mostra onde o script parou, mesmo se o editor cair.
     - O que se perdeu: nada. O script só salva no fim.
   - Onde está o crash report: `Saved/Crashes/UECC-Windows-360537984B209AD8E6836583511BFEE8_0002`.
