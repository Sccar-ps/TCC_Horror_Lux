# TCC_Horror_Lux no Codex

Este é o projeto Unreal; a memória e os scripts oficiais estão no [vault CerebroUnreal-Horror](../../BRAIN_UNREAL_TCC/CerebroUnreal-Horror/AGENTS.md). Leia esse AGENTS.md, o roteador indicado por ele e a [skill de papéis](../../BRAIN_UNREAL_TCC/CerebroUnreal-Horror/.agents/skills/teammates-cerebro-unreal/SKILL.md) antes do trabalho. Descubra os caminhos de cada desenvolvedor em 01_Projeto/Stack_e_Ambiente.md do vault; não grave caminhos absolutos de máquina nos arquivos versionados.

## Papéis vigentes desde 26/10/2026

Somente sccar (Sccar, gpt-6.1-terra/xhigh), hunter (Hunter, gpt-6.1-sol/high), golden (Golden, gpt-6.1-sol/medium) e rattao (Rattão, gpt-6.1-sol/medium). A política aplica-se ao desenvolvimento Unreal e à infraestrutura/configuração/documentação/memória desse domínio.

Rattão é a sessão principal: coordena e audita contratos, diffs e logs, **sem criar, editar, mover, apagar ou salvar arquivo algum**, inclusive notas/memória e ações de editor/PIE com escrita. Implementação é delegada exclusivamente ao domínio: Sccar para Blueprint de conteúdo/UI/animação/materiais/VFX/ponte C++; Hunter para núcleo e sistemas, mesmo em Blueprint, testes e infraestrutura; Golden para ambientes/layout/luz. Especialistas mantêm as notas atribuídas do próprio domínio. Golden é consulta obrigatória antes da aprovação visual. Máximo de principal + três filhos, sem exigir todos por pedido.

Esta decisão substitui lead Opus/scout e exceções legadas que reservem escrita/editor/PIE à sessão principal; as demais regras técnicas e decisões do projeto continuam válidas. Em sessão com catálogo antigo, siga o fallback da skill de papéis: default com fork none e modelo/esforço explícitos, sem fingir recarga e sem implementação por Rattão.

## Confiabilidade

- Antes de alterar Unreal, reconhecer .uproject/Modules/Plugins e a estrutura do projeto. A D01 revista em 26/10/2026 autoriza C++ quando facilitar implementação; comparar alternativas e registrar toolchain/build e impacto na equipe antes de introduzir Source/Modules (ver CPP_vs_Blueprint no vault).
- Git somente de leitura; registrar status antes e preservar toda alteração prévia.
- Um dono por arquivo/asset/mapa; binários em série. Uma operação Unreal por vez, com vez liberada por Rattão após conferir processos e RAM; não encerrar processo de terceiro.
- Preservar D01–D03, bases protegidas, scripts seguros e idempotentes do vault e dependências D22/D24.
- Auditoria Rattão antes de contrato, após uma falha de compilação/teste, antes de concluir e antes de PR/merge; duas falhas do mesmo teste exigem causa raiz.
- Compilação, automação, cook quando aplicável e verificação própria do projeto precisam de evidência atual. O especialista entrega evidência; Rattão audita, sem se tornar escritor da nota.
