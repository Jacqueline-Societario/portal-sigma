# Lessons — portal-sigma

- ERRO: Assumir modo do git index (100644) sem verificar arquivos específicos — output de `git ls-files -s` pode estar truncado e não incluir o arquivo em questão.
  REGRA: Sempre rodar `git ls-files -s [arquivo_suspeito]` antes de qualquer chmod ou update-index. Nunca deduzir o modo pelo comportamento do `git status` geral.

- ERRO: Concluir que `git status` vazio significa que disco e index estão alinhados quanto a filemode — WSL git e git Windows do GitHub Desktop podem ter `core.filemode` diferente e ver estados diferentes.
  REGRA: Para diagnóstico de filemode com GitHub Desktop, sempre checar `git ls-files -s` no arquivo suspeito e comparar com `ls -la` no disco antes de agir.
