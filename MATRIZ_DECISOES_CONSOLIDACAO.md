# Matriz de Decisoes -- Consolidacao Portal Societario

**Criado em:** 02/06/2026
**Fase:** Consolidacao VPS (concluida)
**Repositorio:** /home/jacqueline-benedito/projetos/portal-sigma/
**Status:** VPS LIMPA -- 7 itens analisados, 5 commits criados

---

## 1. Contexto

Durante a fase de consolidacao, a VPS foi tratada como a versao operacional
consolidada do Portal Societario, porque e o ambiente que serve a equipe na
internet atraves do societario.gsigma.com.br.

O WSL (ambiente local) nao foi declarado como fonte de verdade geral. Ambos os
ambientes evoluiram de forma independente ao longo do tempo e nao sao espelhos.

A consolidacao foi feita arquivo por arquivo, em ordem de risco crescente, para
evitar efeito cascata: cada decisao foi diagnosticada, justificada e aplicada
antes de passar para o proximo item.

Objetivo: garantir que o repositorio Git da VPS refletisse o estado real de
producao, com todos os arquivos criticos rastreados e nenhum dado sensivel
exposto.

---

## 2. Estado final da VPS

- Repositorio portal-sigma: **LIMPO** (git status vazio em 02/06/2026)
- Branch: main
- Commits criados nesta fase: 5
- Deploy realizado: **nao**
- Servicos reiniciados: **nao**
- Scripts executados: **nao**
- .env alterado: **nao**
- portal.db alterado: **nao**
- credentials/ alterado: **nao**
- logs/, backups/, uploads/ alterados: **nao**
- static/data/ continuou ignorado pelo .gitignore (regra linha 79)

---

## 3. Matriz de decisoes

| # | Arquivo | Decisao | Motivo | Acao aplicada | Commit | Observacao |
|---|---|---|---|---|---|---|
| 1 | portal.py | VPS prevalece | VPS tem filtro Jinja2 `preview` usado em templates/newsletter/index.html. WSL nao tem esse filtro -- sobrescrever quebraria o modulo newsletter silenciosamente. | Nenhuma acao (VPS ja era a correta) | -- | Arquivo nao alterado |
| 2 | blueprints/cnae.py | VPS prevalece | VPS tem: captcha solver, consulta CNAE em 2 etapas (scraping + busca local), correcoes de parsing e fechamento correto de sessao. WSL estava desatualizado e quebraria consultas CNAE Objetiva. | Nenhuma acao (VPS ja era a correta) | 8d0d4e1 (checkpoint) | WSL nao pode sobrescrever |
| 3 | templates/esqueceu_senha.html | WSL prevaleceu (excecao) | VPS tinha o arquivo com 0 bytes -- regressao acidental. O template vazio quebrava silenciosamente a recuperacao de senha para todos os usuarios. | Template do WSL copiado para VPS e commitado | 48585c2 | Excecao pontual. Nao torna WSL fonte de verdade geral. |
| 4 | security.py | VPS prevalece | Diferenca minima: WSL usava `user.get('is_admin')`, VPS usava `user['is_admin']`. VPS estava em producao sem erros. Sem nova funcionalidade, sem regressao. | Nenhuma acao (VPS ja era a correta) | -- | Arquivo nao alterado |
| 5 | templates/index.html | WSL prevaleceu (excecao) | VPS tinha 3 regressoes no upload handler: (1) `r.json()` sem check de `r.ok` -- crash em erro 500 com HTML; (2) `data.tamanho` sem null safety -- TypeError se tamanho vier null; (3) `catch` sem `err.message` -- perde contexto de erro. WSL tinha tratamento mais robusto. | Arquivo do WSL copiado para VPS e commitado | 7ab9b29 | Excecao pontual. Nao torna WSL fonte de verdade geral. |
| 6 | requirements.txt | Criado e versionado na VPS | O projeto nao tinha requirements.txt. Dependencias externas identificadas por leitura estatica de 27 arquivos Python. Versoes confirmadas no .venv de producao. | Arquivo criado com 14 dependencias e commitado | ca0fdba | Novo arquivo. Nao existia em nenhum dos dois ambientes. |
| 7 | scripts/atualizar_base_cnae_concla.py | Versionado na VPS | Script legitimo de manutencao CNAE: baixa XLSX oficial do CONCLA/IBGE e salva static/data/cnae_subclasses.json. Referenciado em blueprints/cnae.py. Sem dados sensiveis (0 ocorrencias de password/token/secret/key). static/data/ ja estava ignorado pelo .gitignore. | Script adicionado ao Git e commitado | 681dfdb | static/data/cnae_subclasses.json continua fora do Git |

---

## 4. Arquivos em que VPS prevaleceu

Os seguintes arquivos estavam mais atualizados e/ou corretos na VPS e nao foram
alterados durante a consolidacao:

- **portal.py** -- filtro Jinja2 `preview` ausente no WSL
- **blueprints/cnae.py** -- captcha solver + consulta 2 etapas ausentes no WSL
- **security.py** -- versao de producao sem erros, diferenca minima sem impacto

Esses arquivos nao devem ser sobrescritos pelo WSL sem revisao cuidadosa.

---

## 5. Arquivos em que WSL prevaleceu como excecao

Dois arquivos foram restaurados a partir do WSL porque a VPS tinha regressoes:

- **templates/esqueceu_senha.html** -- VPS com 0 bytes (commit 48585c2)
- **templates/index.html** -- VPS com 3 regressoes no upload handler (commit 7ab9b29)

Importante: o fato de o WSL ter prevalecido nesses dois casos nao significa que
o WSL e a fonte de verdade geral do projeto. Foram excecoes pontuais justificadas
por regressoes especificas na VPS. Para todos os demais arquivos, a VPS continuou
sendo a referencia.

---

## 6. Novos arquivos versionados na VPS

Dois arquivos foram criados e versionados durante esta fase. Nao existiam em
nenhum dos dois ambientes antes:

- **requirements.txt** -- 14 dependencias externas, versoes do .venv de producao (commit ca0fdba)
- **scripts/atualizar_base_cnae_concla.py** -- script de manutencao CNAE, sem dados sensiveis (commit 681dfdb)

---

## 7. Commits da fase de consolidacao

Em ordem cronologica reversa (mais recente primeiro):

```
681dfdb  chore: versionar script de atualizacao da base CNAE
ca0fdba  chore: adicionar requirements.txt com dependencias do portal
7ab9b29  fix: restaurar tratamento robusto de upload e alert de rerratificacao
48585c2  fix: restaurar template de recuperacao de senha
8d0d4e1  chore: checkpoint estado atual de producao do portal-sigma
```

---

## 8. Itens que nao foram alterados

Durante toda a fase de consolidacao, os seguintes itens foram preservados
integralmente e nunca abertos nem modificados:

- .env (credenciais de producao)
- portal.db (banco de dados com dados reais de clientes)
- credentials/ (tokens OAuth e chaves)
- logs/ e *.log (logs de producao ativos)
- backups/ e *.bak_* (backups de producao)
- uploads/ (arquivos enviados por usuarios)
- static/data/cnae_subclasses.json (arquivo gerado, ignorado pelo .gitignore)
- Configuracoes systemd e service files
- Pastas de outros usuarios da VPS

---

## 9. Proxima fase recomendada

A proxima fase e consolidar o WSL com base nas decisoes finais da VPS,
alinhando o ambiente local ao estado correto de producao.

Ordem sugerida:

1. Diagnosticar estado atual do WSL (alteracao-contratual/).
   Verificar quais arquivos diferem em relacao ao estado atual da VPS.

2. Verificar se ha Git proprio no WSL para o projeto.
   O WSL usa o workspace principal ~/claude como repositorio -- avaliar se
   convem criar git proprio para alteracao-contratual/ ou manter no workspace.

3. Criar ou ajustar .gitignore no WSL.
   Garantir que .env, portal.db, credentials/, logs/, backups/, uploads/ e
   static/data/ estejam protegidos tambem no WSL.

4. Copiar da VPS para o WSL os arquivos que prevaleceram na VPS.
   Arquivos criticos: portal.py, blueprints/cnae.py, security.py,
   requirements.txt, scripts/atualizar_base_cnae_concla.py.

5. Garantir que as correcoes aplicadas na VPS tambem estejam no WSL.
   templates/esqueceu_senha.html (commit 48585c2) e
   templates/index.html (commit 7ab9b29) devem estar alinhados.

6. Criar commit local no WSL documentando o alinhamento.

7. So depois avaliar criacao de remote GitHub privado por projeto.
   Nunca fazer deploy direto WSL -> VPS por copia ampla.

---

*Documento gerado ao final da fase de consolidacao VPS -- 02/06/2026*
*Proxima revisao: apos conclusao da fase de alinhamento WSL*
