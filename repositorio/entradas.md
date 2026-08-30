# Entradas do sistema

**Evidence Autopilot EUDR · ATON**

O que entra: o que o **produtor entrega** e as **bases que o sistema cruza**. O par deste arquivo é o `conferencia.md`, que trata do que sai.

> Não compete com o `contrato.md`: o contrato diz **o que construir**, este arquivo detalha **o que alimenta**. Em caso de conflito, o contrato ganha.

---

## Parte 1 · O que o produtor entrega

### O conjunto mínimo — quatro tipos, não quarenta

| Camada | O que ele entrega | Alternativas aceitas, **em ordem de força** |
|---|---|---|
| **1 · Parcela geolocalizada** | **CAR** — recibo de inscrição e demonstrativo | **Nenhuma.** É a única exigência sem substituto: o CAR é o único vetor geoespacial que a base inteira possui. Precisa estar **não-cancelado** — Ativo e Pendente passam |
| **2 · Direito de uso da área** | **Um** documento de posse ou propriedade | **Matrícula** → **título** (TD, CDRU, CCU) → **contrato ou declaração de posse + CCIR ou recibo do ITR em nome próprio** |
| **3 · Identidade e vínculo** | **CPF + extrato do CAF** | Na falta do CAF: ficha de cooperado + inscrição estadual de produtor |
| **4 · Transação, quantidade e data** | **Notas fiscais da safra** | Se ele não emite: a **contranota** da cooperativa resolve — e ela é da cooperativa, não dele |

O número de arquivos varia pelas notas da safra. Os tipos são quatro.

### A camada 5 ele não entrega

Sem embargo do IBAMA ou da LDI · sem desmatamento no PRODES depois de 31/12/2020 · CPF fora da Lista Suja · sem sobreposição com terra indígena, unidade de conservação de proteção integral ou território quilombola.

**Tudo isso o sistema gera contra a coordenada dele e data.** É o que fecha as categorias que não têm documento — direitos humanos (f), consulta às comunidades (g) e parte dos direitos de terceiros (d).

> É evidência que o sistema gera, não que o produtor entrega.

### O que NÃO se pede — e este pedaço é o mais importante

| Documento | Por quê |
|---|---|
| **Licença ambiental** | Cacauicultura familiar é tipicamente dispensada. **Não ter é a situação regular** |
| **SIGEF** | Só obrigatório em 21/10/2029; abaixo de 25 ha não se aplica agora |
| **ASV / AUTEF** | SAF em área consolidada não exige e cabruca não suprime. A presença é que é rara |
| **Certificações** (RA, orgânico, Fairtrade) | Complemento da avaliação de risco (Art. 10(2)(n)), nunca substituto |
| **CND-ITR** | Débito de ITR não torna a produção ilegal — vira flag, não bloqueio |

**Pedir qualquer um desses é criar a barreira que o produto existe para remover.**

### O que vence — é aqui que a vigilância mora

CCIR: anual · extrato do CAF: 5 anos no Norte, 3 nos demais · CND-ITR: 180 dias · certidão de matrícula: 30 dias para atos · certidão de embargo: **retrato do dia** · nota fiscal: nasce a cada entrega.

---

## Parte 2 · As bases que o sistema cruza

### Geoespaciais e em lote — cruzamento automático

Gratuitas, públicas e legíveis por máquina. Sustentam a camada 5 e produzem a evidência que o produtor não entrega. Vivem em `dados/bases/`.

| Base | Órgão | O que prova | Formato | Cadência |
|---|---|---|---|---|
| **SiCAR** (+ SICAR+/SEMAS-PA, CEFIR/SEIA-BA) | SFB e estados | Polígono do imóvel e **condição do CAR** (Ativo, Pendente, Suspenso, Cancelado) | Shapefile na consulta pública | Muda de condição, não vence |
| **PRODES / TerraBrasilis** | INPE | Desmatamento consolidado — **o cruzamento decisivo do corte de 31/12/2020** | Shapefile anual | Anual |
| **MapBiomas Alerta** | MapBiomas | Alerta **validado** com imagem de alta resolução; laudo por cruzamento alerta × imóvel | API / shapefile | Contínua |
| **Embargos IBAMA** | IBAMA | Área embargada — categorias (b) e (d) | **CSV e SHP em dados abertos, sem autenticação** | Diária |
| **LDI** | SEMAS-PA (Dec. 838/2013) | Lista estadual de desmatamento ilegal, com nº do CAR e polígonos | Consulta pública | Contínua |
| **Terras Indígenas** | FUNAI | Sobreposição — **categorias (d), (f) e (g)** | Shapefile | Eventual |
| **Unidades de conservação** | CNUC/MMA e ICMBio | Sobreposição com proteção integral | Shapefile | Eventual |
| **Territórios quilombolas** | INCRA | Sobreposição com área titulada ou certificada | Shapefile | Eventual |
| **Lista Suja do trabalho escravo** | MTE (Portaria 4/2016) | **Categorias (e) e (f)** — a única prova automatizável delas | Planilha/PDF, **sem API** | Semestral; permanência de 2 anos |

### Três armadilhas que custam caro

1. **IBAMA e LDI não conversam.** Embargo estadual não aparece na base federal e vice-versa. Checar as duas — e as municipais, quando existirem.
2. **Cruzar por polígono, não só por CPF.** Embargos aparecem com frequência em CPF divergente do fornecedor: posseiro, herdeiro, meeiro. O CPF pega uma parte; a geometria pega o resto. Na Lista Suja só existe CPF — e o match é **por CPF, nunca por nome**.
3. **DETER não vale como veredito.** Tem falso positivo por nuvem e por degradação. O veredito sai do PRODES mais a validação do MapBiomas; o DETER serve como gatilho de vigilância, não como prova.

### Consultas individuais — documento a documento

Não são cruzamento: são verificação de um documento por vez, e várias exigem login ou captcha. Confirmam o que o produtor entregou; **não geram evidência**.

| Base | Confirma | Camada |
|---|---|---|
| **SNCR / INCRA** | CCIR emitido e **quitado** no exercício | 2 |
| **Receita Federal** | Recibo da DITR (NIRF/CIB) e CND do imóvel, por código de controle | 2 e 8 |
| **ONR / registradores** | Certidão de matrícula e averbações | 2 |
| **SIGEF / INCRA** | Planta e memorial certificados, por código único | 1 e 2 |
| **Rede CAF** ("Meu Imóvel Rural") | Extrato do CAF e vigência | 3 |
| **SEFA-PA / SEFAZ-BA** | Autorização da chave de acesso da NF-e e situação da inscrição estadual | 4 |
| **Rainforest, FLOCERT, MAPA orgânicos** | Se o certificado declarado está mesmo vigente | complementar |

---

## Ordem de valor para o MVP

As três que já rodam sobre dado real e sem autenticação — **embargos do IBAMA**, **PRODES** e o trio **TI / UC / quilombola** — fecham juntas as categorias que não têm documento, que é a tese inteira. A **Lista Suja** é a quarta e a mais barata: baixar uma planilha por semestre e casar CPF.

## Aberto, e vale confirmar hoje

**Pode haver mascaramento de CPF nos dados abertos do IBAMA.** Não foi inspecionado. Se houver, o fallback é o polígono — que de todo jeito é o cruzamento mais robusto. Muda o desenho da checagem 02.
