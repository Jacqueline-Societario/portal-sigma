# Design System — Portal Societário Sigma Contabilidade

> **Referência obrigatória** para qualquer tela, componente, imagem, apresentação ou página futura do portal.
> Nenhuma alteração visual deve ser feita sem consultar este documento.

---

## 1. Princípios Visuais

O Portal Societário da Sigma Contabilidade não é um dashboard SaaS genérico. É uma ferramenta institucional de uma contabilidade com 15 anos de mercado, cujo valor está na confiança, na seriedade e no cuidado com o cliente.

### Premissas inegociáveis

- **Institucional** — A interface deve transmitir credibilidade. O usuário deve sentir que está usando uma ferramenta da Sigma, não um template anônimo de admin panel.
- **Elegante** — Composição visual refinada, proporções equilibradas, uso consciente do espaço. Nada deve parecer jogado ou automático.
- **Quente** — Paleta predominantemente vinho, rosé e bege. O portal não é frio nem clínico.
- **Limpo** — Sem poluição visual, sem excesso de bordas, sem cores desnecessárias. Limpeza não significa vazio — significa intenção.
- **Acolhedor** — Profissional, mas não intimidador. Adequado para a equipe interna que usa diariamente.

### O que este portal não é

- Não é um SaaS de startups.
- Não é um painel de monitoramento técnico.
- Não é uma ferramenta Bootstrap com tema padrão.
- Não é uma tela gerada automaticamente por IA sem curadoria visual.

---

## 2. Paleta de Cores

### Cores principais

| Nome | Hex | Uso |
|---|---|---|
| Vinho principal | `#8A1F2D` | Cor de marca. Ícones, destaques, links ativos, bordas de ênfase. |
| Carmim escuro | `#6E1824` | Hover de botões primários, estados ativos profundos. |
| Vinho suave | `#9B2C3A` | Textos em vinho, ícones secundários, rótulos. |

### Tons rosé (fundos de apoio e ícones)

| Nome | Hex | Uso |
|---|---|---|
| Rosé claro | `#F3DCDD` | Fundo de caixas de ícone, fundo de item ativo na sidebar, badges suaves. |
| Rosé médio | `#E8BFC2` | Bordas de destaque suave, separadores, fundo de blocos de anotação. |
| Rosé queimado claro | `#EBC9C9` | Variação de post-it, hover de itens de lista. |

### Fundo e superfícies

| Nome | Hex | Uso |
|---|---|---|
| Bege/off-white de fundo | `#F7F2EC` | Fundo geral da aplicação (body/main). |
| Branco dos cards | `#FFFDFC` | Superfície de cards, modais, painéis. |

### Textos e bordas

| Nome | Hex | Uso |
|---|---|---|
| Cinza texto principal | `#2F2F2F` | Títulos e textos de corpo. |
| Cinza texto secundário | `#6B7280` | Descrições, metadados, labels de formulário. |
| Cinza borda | `#E7DED8` | Bordas de cards, separadores horizontais, inputs. |

### Cores funcionais (uso restrito e com propósito)

Estas cores só devem aparecer quando há significado funcional claro e indispensável:

| Cor | Situação permitida |
|---|---|
| Verde `#16A34A` / `#DCFCE7` | Status de sucesso, aprovado, concluído. |
| Azul `#2563EB` / `#DBEAFE` | Links externos, informação neutra, link de processo. |
| Amarelo `#D97706` / `#FEF3C7` | Alerta, pendente, atenção. |
| Vermelho `#DC2626` / `#FEE2E2` | Erro, bloqueado, vencido. |

**Regra:** Nunca usar estas cores como elementos decorativos ou para variar a paleta. Apenas como indicadores funcionais.

---

## 3. Tipografia

O portal não exige uma fonte específica diferente da padrão do sistema, mas define regras claras de uso de tamanho, peso e cor.

### Hierarquia de textos

| Elemento | Tamanho | Peso | Cor |
|---|---|---|---|
| Título de página (H1) | `1.5rem` (24px) | `600` | `#2F2F2F` |
| Subtítulo de seção (H2) | `1.125rem` (18px) | `600` | `#2F2F2F` |
| Título de card | `0.9375rem` (15px) | `600` | `#2F2F2F` |
| Texto de corpo | `0.875rem` (14px) | `400` | `#2F2F2F` |
| Texto secundário / descrição | `0.8125rem` (13px) | `400` | `#6B7280` |
| Metadado / label | `0.75rem` (12px) | `500` | `#6B7280` |
| Número de indicador | `1.75rem` (28px) | `700` | `#8A1F2D` |
| Link | `0.875rem` (14px) | `500` | `#8A1F2D` |
| Botão primário | `0.875rem` (14px) | `600` | `#FFFFFF` |
| Botão secundário | `0.875rem` (14px) | `500` | `#8A1F2D` |

### Regras de tipografia

- **Negrito com parcimônia.** Usar `font-weight: 600` para títulos e destaques importantes. Nunca usar `700` ou `800` em texto corrido.
- **Números de indicadores** devem ter peso `700` e cor vinho, mas tamanho controlado — não devem parecer pesados ou agressivos.
- **Textos secundários** sempre em `#6B7280`. Nunca usar cinza mais escuro que o texto principal para descrições.
- **Evitar text-transform: uppercase** em blocos longos. Pode ser usado com moderação em labels de categoria (ex: `font-size: 11px`, `letter-spacing: 0.05em`).
- **Line-height:** `1.5` para texto de corpo, `1.3` para títulos.

---

## 4. Espaçamento e Composição

### Espaçamentos base

| Contexto | Valor |
|---|---|
| Margem lateral da área de conteúdo | `32px` |
| Espaçamento entre seções principais | `32px` |
| Espaçamento interno de card | `24px` |
| Gap entre cards em grid | `20px` |
| Espaçamento entre ícone e texto | `12px` |
| Espaçamento entre rótulo e valor | `4px` |

### Grid de indicadores (KPIs)

- Desktop (≥1280px): 4 colunas.
- Desktop médio (≥1024px): 3 ou 4 colunas conforme o contexto.
- Tablet (≥768px): 2 colunas.
- Mobile: 1 coluna.
- Gap entre cards de indicador: `16px` a `20px`.

### Grid de acessos rápidos

- Desktop: 3 ou 4 colunas.
- Cards de acesso rápido com largura mínima de `180px`.
- Nunca deixar colunas muito estreitas que pareçam lista vertical em desktop.

### Seções de duas colunas

- Proporção recomendada: `2/3` + `1/3` ou `1/2` + `1/2`.
- Gap entre colunas: `24px`.
- Nunca colocar duas colunas muito desproporcionais (ex: `90%` + `10%`).

### Respiro e equilíbrio

- O layout deve ter respiro suficiente para parecer elegante, mas não vazio.
- Evitar áreas em branco sem propósito — cada espaço deve ter intenção.
- Em desktop, os componentes devem ocupar bem o espaço disponível. Evitar componentes estreitos que pareçam mobile esticado.

---

## 5. Cards

Os cards são o componente central do portal. Devem parecer refinados, consistentes e institucionais.

### Especificações do card padrão

```css
background: #FFFDFC;
border-radius: 16px;
border: 1px solid #E7DED8;
box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 4px 12px rgba(0,0,0,0.04);
padding: 24px;
```

### Card de indicador (KPI)

```css
/* Caixa do ícone */
background: #F3DCDD;
border-radius: 10px;
padding: 10px;
width: 42px;
height: 42px;
display: flex;
align-items: center;
justify-content: center;

/* Ícone dentro da caixa */
color: #8A1F2D;
width: 20px;
height: 20px;

/* Número de destaque */
font-size: 1.75rem;
font-weight: 700;
color: #8A1F2D;

/* Rótulo */
font-size: 0.8125rem;
color: #6B7280;
```

### Card de acesso rápido

- Ícone no topo, dentro de caixa rosé.
- Título do módulo em `#2F2F2F`, peso `600`.
- Descrição curta em `#6B7280`, peso `400`.
- Link "Acessar →" em vinho, alinhado ao rodapé do card.
- Hover: leve elevação de sombra + deslocamento sutil de `translateY(-2px)`.

### Regras gerais de cards

- Nunca usar `border-radius` menor que `12px` ou maior que `20px`.
- Sombra sempre suave — nunca sombra pesada ou escura demais.
- Ícones dentro de cards sempre em caixa rosé (`#F3DCDD`) com ícone vinho.
- Links dentro de cards sempre em vinho (`#8A1F2D`), com underline apenas no hover.

---

## 6. Sidebar

A sidebar é o elemento de navegação principal e deve transmitir identidade institucional.

### Especificações

```css
/* Fundo da sidebar */
background: #FFFDFC;
border-right: 1px solid #E7DED8;
width: 240px; /* desktop */
```

### Estrutura

1. **Topo:** Logo da Sigma centralizado ou alinhado à esquerda, com espaçamento generoso.
2. **Menu:** Itens agrupados por categorias com label de seção em cinza claro (`font-size: 11px`, `text-transform: uppercase`, `letter-spacing: 0.05em`, `color: #6B7280`).
3. **Item de menu padrão:**
   - Ícone + texto em `#2F2F2F`.
   - Padding: `10px 16px`.
   - Border-radius: `8px`.
4. **Item ativo:**
   - Fundo: `#F3DCDD`.
   - Cor do texto e ícone: `#8A1F2D`, peso `600`.
5. **Hover (não ativo):**
   - Fundo: `#F7F2EC`.
   - Cor: `#9B2C3A`.
6. **Rodapé:** Informações do usuário logado — avatar/inicial, nome e cargo. Fundo ligeiramente diferenciado ou separador superior.

### Regras da sidebar

- Nunca usar fundo escuro ou colorido na sidebar.
- Nunca usar ícones coloridos aleatórios — sempre vinho ou cinza neutro.
- A sidebar deve parecer parte de uma aplicação corporativa, não de um template gratuito de Bootstrap.

---

## 7. Topbar

A topbar é o cabeçalho fixo da área de conteúdo.

### Especificações

```css
background: #FFFDFC;
border-bottom: 1px solid #E7DED8;
height: 60px;
padding: 0 32px;
display: flex;
align-items: center;
justify-content: space-between;
```

### Estrutura

- **Esquerda:** Breadcrumb indicando a localização atual. Separador `/` em cinza claro. Último item em `#2F2F2F`, peso `600`. Itens anteriores em `#6B7280`, com link vinho no hover.
- **Direita:** Sino de notificações (ícone vinho) + Avatar do usuário (inicial em círculo vinho) + Nome do usuário em `#2F2F2F`.

### Regras da topbar

- Nunca usar topbar com fundo escuro ou colorido.
- O sino deve indicar notificações com badge numérico em vinho.
- O avatar deve ser simples — inicial do nome em fundo vinho e texto branco.

---

## 8. Botões e Links

### Botão primário

```css
background: #8A1F2D;
color: #FFFFFF;
border: none;
border-radius: 8px;
padding: 10px 20px;
font-size: 0.875rem;
font-weight: 600;
cursor: pointer;
transition: background 0.15s ease;

/* Hover */
background: #6E1824;
```

### Botão secundário (fundo claro)

```css
background: #F3DCDD;
color: #8A1F2D;
border: none;
border-radius: 8px;
padding: 10px 20px;
font-size: 0.875rem;
font-weight: 500;

/* Hover */
background: #E8BFC2;
```

### Botão com borda (outline)

```css
background: transparent;
color: #8A1F2D;
border: 1.5px solid #8A1F2D;
border-radius: 8px;
padding: 9px 20px;
font-size: 0.875rem;
font-weight: 500;

/* Hover */
background: #F3DCDD;
```

### Botão destrutivo (ação irreversível)

```css
background: #DC2626;
color: #FFFFFF;

/* Hover */
background: #B91C1C;
```

### Link com seta

```css
color: #8A1F2D;
font-weight: 500;
text-decoration: none;
display: inline-flex;
align-items: center;
gap: 4px;

/* Hover */
text-decoration: underline;
```

Formato padrão: `Acessar →` ou `Ver todos →`.

### Regras de botões

- Nunca usar `border-radius` maior que `10px` em botões.
- Sempre definir estado de hover.
- Nunca usar botões com gradientes ou sombras pesadas.
- Botões de ação destrutiva devem ser vermelhos e estar isolados visualmente das ações principais.

---

## 9. Blocos de Anotações / Post-its

Os blocos de anotação devem ter aparência de post-it elegante — não de textarea padrão HTML e não de cards comuns.

### Cores disponíveis para post-its

| Nome | Hex fundo | Hex borda |
|---|---|---|
| Rosé | `#FDF0F0` | `#EBC9C9` |
| Branco quente | `#FFFDFC` | `#E7DED8` |
| Amarelo claro | `#FEFCE8` | `#FDE68A` |
| Verde muito claro | `#F0FDF4` | `#BBF7D0` |
| Azul muito claro | `#EFF6FF` | `#BFDBFE` |

### Especificações do bloco

```css
border-radius: 14px;
padding: 16px;
box-shadow: 0 2px 8px rgba(0,0,0,0.06);
border: 1px solid [cor-borda];
background: [cor-fundo];

/* Área de texto */
border: none;
background: transparent;
resize: none;
font-size: 0.875rem;
line-height: 1.6;
color: #2F2F2F;
width: 100%;
outline: none;
```

### Barra de formatação (se houver)

- Discreta, alinhada ao topo ou rodapé do bloco.
- Ícones pequenos em cinza (`#6B7280`), hover em vinho.
- Sem fundo próprio — integrada ao bloco.
- Nunca usar barra de formatação chamativa ou com cores saturadas.

### Regras de post-its

- Nunca usar fundo branco puro em post-its — usar sempre um dos tons suaves listados.
- Nunca usar cabeçalho com cor forte no topo do post-it.
- A sombra deve ser muito suave — apenas para dar profundidade, não para chamar atenção.
- O conjunto de post-its em tela deve parecer uma coleção elegante, não uma bagunça colorida.

---

## 10. Regras Anti-Genérico

Lista de proibições absolutas para o Portal Societário da Sigma:

### Visual

- **Proibido** usar o visual padrão de dashboard SaaS (fundo cinza, sidebar escura, ícones coloridos, KPIs com gradientes de cor).
- **Proibido** usar ícones multicoloridos aleatórios (vermelho, verde, azul, amarelo juntos sem propósito).
- **Proibido** usar cards frios e sem identidade — sem sombra, sem borda, com espaçamento padrão de Bootstrap.
- **Proibido** usar excesso de branco puro `#FFFFFF` sem elementos quentes ao redor.
- **Proibido** usar cores vivas (ex: gradiente roxo, laranja, ciano) como parte da identidade visual.
- **Proibido** deixar telas com cara de protótipo rápido ou de componente gerado sem curadoria.

### Componentes

- **Proibido** usar botões com `border-radius: 4px` (aparência padrão de Bootstrap/Material sem personalização).
- **Proibido** usar inputs com borda azul de foco padrão do navegador sem sobrescrever com cor vinho.
- **Proibido** usar tabelas sem estilização — zebra sem cor, bordas escuras, headers azuis ou cinzas.
- **Proibido** usar modais com header azul ou cinza escuro — manter paleta vinho/branco.

### Layout

- **Proibido** usar layout com componentes muito estreitos em desktop, parecendo versão mobile esticada.
- **Proibido** usar espaçamento excessivo que deixe a tela parecendo vazia e sem conteúdo.
- **Proibido** usar grids irregulares sem intenção visual clara.

### Tipografia

- **Proibido** usar `font-weight: 900` ou textos agressivamente grandes em indicadores.
- **Proibido** usar `text-transform: uppercase` em títulos de seção principais.
- **Proibido** misturar mais de dois tamanhos de fonte em um mesmo card.

---

## 11. Checklist Obrigatório Antes de Finalizar Qualquer Tela

Antes de considerar uma tela pronta, responder honestamente a todas as perguntas abaixo:

### Identidade visual

- [ ] A tela parece institucional e alinhada à Sigma Contabilidade?
- [ ] A paleta vinho / rosé / bege está dominante?
- [ ] A tela poderia ser confundida com um template genérico de SaaS? (Resposta esperada: **NÃO**)
- [ ] As cores funcionais (verde, azul, vermelho, amarelo) aparecem apenas onde há significado claro?

### Componentes

- [ ] Os ícones estão consistentes em estilo e cor?
- [ ] Os ícones dentro de cards estão dentro de caixas rosé (`#F3DCDD`) com cor vinho?
- [ ] Os cards têm sombra suave, borda clara e border-radius entre 14px e 20px?
- [ ] Os botões primários estão em vinho escuro `#8A1F2D`?
- [ ] Os inputs têm foco em vinho, não em azul padrão?

### Tipografia e hierarquia

- [ ] A hierarquia tipográfica está elegante e legível?
- [ ] Não há uso excessivo de negrito?
- [ ] Os textos secundários estão em cinza médio `#6B7280`?
- [ ] Os números de indicadores se destacam sem parecerem pesados?

### Layout e composição

- [ ] O layout tem respiro, mas não parece vazio?
- [ ] Em desktop, os componentes ocupam bem o espaço disponível?
- [ ] O espaçamento entre seções está entre 28px e 36px?
- [ ] O grid de cards está equilibrado (sem colunas muito estreitas ou muito largas)?

### Resultado final

- [ ] O resultado parece feito por um designer com curadoria, não gerado automaticamente?
- [ ] A tela está visualmente consistente com as outras telas do portal?
- [ ] Um usuário que vê pela primeira vez identifica que é uma ferramenta da Sigma Contabilidade?

---

## Referência rápida — variáveis CSS recomendadas

```css
:root {
  /* Marca */
  --sigma-vinho:         #8A1F2D;
  --sigma-carmim:        #6E1824;
  --sigma-vinho-suave:   #9B2C3A;

  /* Rosé */
  --sigma-rose-claro:    #F3DCDD;
  --sigma-rose-medio:    #E8BFC2;
  --sigma-rose-queimado: #EBC9C9;

  /* Fundo e superfícies */
  --sigma-fundo:         #F7F2EC;
  --sigma-card:          #FFFDFC;

  /* Texto */
  --sigma-texto:         #2F2F2F;
  --sigma-texto-sec:     #6B7280;
  --sigma-borda:         #E7DED8;

  /* Funcionais */
  --sigma-sucesso:       #16A34A;
  --sigma-alerta:        #D97706;
  --sigma-erro:          #DC2626;
  --sigma-info:          #2563EB;
}
```

---

*Documento criado em 30/04/2026. Qualquer alteração visual no portal deve consultar este arquivo antes de ser implementada.*
