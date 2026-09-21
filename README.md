# TCC_Horror_Lux

# X

Um jogo de exploração narrativa e terror psicológico em primeira pessoa, desenvolvido na **Unreal Engine**. O projeto foca em mecânicas de loop espacial (*estilo P.T.*) e design sensorial imersivo para simular a desorientação e os sintomas de um trauma cerebral grave.

## Sinopse

A história tem início com o protagonista, Santos, realizando uma trilha em uma densa floresta. O percurso é subitamente interrompido quando ele sofre uma grave queda em um buraco. A visão escurece e a realidade é substituída pelo som agudo e contínuo de um monitor multiparamétrico de hospital.

Quando Santos finalmente "desperta", ele se vê no corredor da própria casa. Sem memórias claras de como chegou ali, ele caminha até a sala de estar. Porém, ao cruzar a porta de saída, o impossível acontece: ele é jogado de volta ao ponto exato onde acordou. O ciclo recomeça.

## Contexto Clínico e Psicológico

Na realidade, a queda resultou em um **Traumatismo Cranioencefálico (TCE)**. O cenário da casa é uma projeção de sua mente lutando para processar o trauma enquanto está internado. Toda a experiência de jogo é baseada nos efeitos colaterais reais da sua lesão:

*   **Perda de Consciência e Amnésia:** Justifica os "apagões" e a falta de entendimento do ambiente.
*   **Confusão Mental:** O layout da casa que não faz sentido lógico e o loop infinito.
*   ### *Fotofobia (Sensibilidade à luz): Luzes do cenário que estouram, piscam agressivamente ou causam distorções visuais quando o jogador olha diretamente.*
*   ### *Fonofobia (Sensibilidade ao som): Efeitos sonoros normais (como o tique-taque de um relógio, passos ou o bipe do monitor) que se tornam ensurdecedores e opressivos durante os ciclos.*

## Mecânicas Principais (O Loop)

O jogo ocorre quase inteiramente no mesmo cenário (o corredor e a sala), mas a progressão é impulsionada pela repetição:

*   **Evolução do Cenário:** A cada ciclo concluído, o corredor sofre alterações sutis ou drásticas. Objetos mudam de lugar, a iluminação decai, texturas se corrompem e elementos de um hospital começam a invadir a casa.
*   **Passagem do Tempo e Desorientação:** O ambiente reflete a percepção distorcida de tempo de Santos. Portas que antes abriam podem desaparecer, e o corredor pode parecer infinitamente mais longo ou esmagadoramente estreito dependendo do nível de confusão mental naquele ciclo.
*   **Gatilhos Narrativos:** A transição entre os loops é ativada ao cruzar o batente da porta final, forçando o jogador a sempre seguir em frente na tentativa de quebrar o ciclo e acordar na vida real.

## 🛠️ Tecnologias e Ferramentas

*   **Motor Gráfico:** Unreal Engine 5
*   **Programação:** Blueprints / C++
*   **Áudio:** Implementação de áudio dinâmico e espacialização para simular a fonofobia e os bipes do monitor hospitalar.
*   **Iluminação e Pós-Processamento:** Uso intenso de *Post-Process Volumes* para simular a fotofobia e a degradação visual do TCE.
