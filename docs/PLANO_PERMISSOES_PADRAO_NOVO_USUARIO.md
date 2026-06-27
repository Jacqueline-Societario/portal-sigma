# Plano — Permissões Padrão para Novo Usuário

**Data:** 27/06/2026
**Status:** PENDENTE — não implementado
**Arquivo alvo:** `database.py` — função `criar_usuario()`

---

## Objetivo

Ao criar um novo usuário, ativar automaticamente 6 módulos por padrão.
Atualmente todos os módulos aparecem inativados para usuários recém-criados.

---

## Módulos a ativar por padrão

| Módulo | Chave em TOOLS | Observação |
|--------|---------------|------------|
| Empresas | `empresas` | presente em TOOLS |
| Movimentação | `movimentacao` | presente em TOOLS |
| Anotações | `anotacoes` | **NÃO está em TOOLS** — verificar |
| Procurações | `procuracoes` | presente em TOOLS |
| Newsletter | `newsletter` | presente em TOOLS |
| Manuais | `manuais` | presente em TOOLS |

**Atenção:** `anotacoes` não consta no dict `TOOLS` (database.py ~linha 654).
Antes de implementar, confirmar se permissão é verificada para esse módulo.
Se não for verificada, `anotacoes` é livremente acessível — não precisa inserir registro.

---

## Implementação proposta

### 1. Adicionar constante em `database.py` (antes de `criar_usuario`)

```python
# Módulos ativados por padrão para novos usuários
TOOLS_PADRAO = ['empresas', 'movimentacao', 'procuracoes', 'newsletter', 'manuais']
# 'anotacoes' excluído se não estiver em TOOLS
```

### 2. Modificar `criar_usuario()` — após o INSERT do usuário

Localizar o trecho após o `cursor.execute(INSERT ...)` e `conn.commit()`,
antes do `return novo_id`.

Adicionar:
```python
# Definir permissões padrão para o novo usuário
for tool in TOOLS_PADRAO:
    set_user_permission(novo_id, tool, True)
```

### 3. Verificar `set_user_permission()`

Confirmar que a função aceita `user_id, tool, enabled` e faz UPSERT correto.
Atualmente localizada em ~linha 681 do database.py.

---

## Riscos

- **Baixo** — afeta apenas usuários criados a partir da implementação
- Usuários existentes não são alterados
- Permissões podem ser modificadas manualmente pelo admin após criação

---

## Verificações antes de implementar

1. Confirmar chave de `anotacoes` — está em `TOOLS`? Se não, remover da lista
2. Confirmar que `set_user_permission` pode ser chamada dentro de `criar_usuario` (sem conflito de conexão DB)
3. Testar criação de usuário após implementação e verificar painel admin

---

## Arquivos a alterar

- `database.py` — adicionar `TOOLS_PADRAO` + loop em `criar_usuario()`

**Nenhum outro arquivo precisa ser alterado.**
