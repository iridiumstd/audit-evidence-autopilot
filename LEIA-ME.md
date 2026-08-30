# Evidence Autopilot EUDR — pacote de documentos

**ATON · versão em markdown de tudo que está no doc mestre (Porta de Entrada).**

Os originais são artefatos com formatação, tabelas coloridas e semáforos. Esta é a versão em texto, para quem quiser ler offline, buscar por palavra ou colar em outro lugar. **Quando houver dúvida, o artefato original é a versão boa** — o link está no topo de cada arquivo.

---

## `pitch-e-produto/` — os 14 documentos do doc mestre

### Comece por aqui
| Arquivo | O que é | Quem lê |
|---|---|---|
| `01-mini-pitch.md` | Mini pitch interno nos oito blocos da estrutura real, com as notas de palco | A PM abre o dia com ele. Quem escrever a narrativa começa daqui |
| `02-plano-do-dia.md` | Estado das frentes, o que já está decidido, as decisões que faltam, as horas com dono | Todo mundo lê a seção "já decidido" |

### Para decidir e para contar
| Arquivo | O que é | Quem lê |
|---|---|---|
| `03-mvp.md` | A definição completa: tese, ICP, recorte, dossiê, cadência, laços, checagens, caso de negócio | Quem escreve a narrativa e a PM |
| `04-duas-pernas.md` | Por que metade da lei virou gratuita e a outra metade não tem dono. O precedente do EUTR | Narrativa e sabatina |
| `05-icp-claudia.md` | Quem compra, quem assina, quem se beneficia. Por que a dor é grave, urgente e cara | Quem for pitchar decora as seções 3 e 4 |

### Para construir
| Arquivo | O que é | Quem lê |
|---|---|---|
| `06-conferencia.md` | Os cinco outputs, as oito seções do dossiê, os seis testes. Toda linha tem "reprova se" | A PM antes do ensaio; cada trilha na sua parte |
| `07-correcoes-spec.md` | O que a taxonomia documental mudou no PRD e no spec | Quem escreve PRD e spec |
| `08-ordem-de-construcao.md` | As cinco trilhas, os pontos de junção, o teste de aceitação | Todos os vibecoders |
| `09-interface.md` | Conceitos de tela. **Este perde muito em markdown** — abra o artefato | O designer |

### Para validar
| Arquivo | O que é | Quem lê |
|---|---|---|
| `10-entrevista.md` | Roteiro completo e autossuficiente: contexto, convite, cola, as seis perguntas, o que fazer se sair do trilho | A PO, sozinha |
| `11-frentes-paralelas.md` | Os briefs prontos para rodar as frentes de pesquisa em sessões separadas | Quem for rodar frente nova |

### As pesquisas que embasam
| Arquivo | O que é |
|---|---|
| `12-dimensionamento.md` | TAM, SAM e SOM construídos de baixo para cima, com as premissas rastreáveis |
| `13-conta-que-exclui.md` | A pesquisa de mercado: custo de conformidade, concentração de compra, evidência de exclusão |
| `14-dossie-eudr-cacau.md` | O levantamento regulatório de base |

---

## `repositorio/` — o que vai junto com o código

Estes quatro já nasceram em markdown e vivem em `docs/` no repositório.

| Arquivo | Papel |
|---|---|
| `contrato.md` | **Decide.** O que construir, quem escreve onde, o esquema, as sete checagens, os invariantes, a ordem de corte. Em qualquer conflito, ele ganha |
| `entradas.md` | Detalha o que entra: o que o produtor entrega, o que **não** se pede, e as nove bases que o sistema cruza |
| `conferencia.md` | Detalha o que sai. Mesma coisa que `06-conferencia.md`, aqui na versão do repositório |
| `duas-pernas.md` | Enquadramento conceitual. **Desatualizado nas regras** — vale o contrato |

---

## Duas observações

**Falta um documento no doc mestre.** A **Taxonomia Documental EUDR** — 29 tipos documentais, matriz das oito categorias, conjunto mínimo em cinco camadas e as 50 regras R01–R50 — não está listada na Porta de Entrada, e é a fonte de boa parte do que está no `07-correcoes-spec.md` e no `entradas.md`. Vale adicionar o card.

**Os arquivos 12, 13 e 14 vieram de cópias locais.** Se esses artefatos foram republicados depois, a versão em markdown pode estar atrás do original. O link está no topo de cada um.
