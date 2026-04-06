# Revisão da base de código: problemas encontrados e tarefas sugeridas

## 1) Tarefa para corrigir erro de digitação
**Problema encontrado:** há comentário com grafia incorreta em `bot_fii.py` (`as vezes` em vez de `às vezes`).

**Tarefa sugerida:**
- Ajustar o comentário para português correto e revisar rapidamente outros comentários/mensagens para evitar erros semelhantes.
- Exemplo pontual: trocar `Yahoo Finance as vezes retorna dados incompletos...` por `Yahoo Finance às vezes retorna dados incompletos...`.

---

## 2) Tarefa para corrigir um bug
**Problema encontrado:** tokens de bot do Telegram estão hardcoded em código-fonte (`bot/management/commands/runbot.py` e `bot_fii.py`). Isso é falha de segurança e operação (segredo versionado no repositório).

**Tarefa sugerida:**
- Remover tokens hardcoded e carregar via variável de ambiente (`TELEGRAM_BOT_TOKEN`).
- Falhar com mensagem clara quando a variável não estiver configurada.
- Invalidar/rotacionar imediatamente os tokens já expostos.

---

## 3) Tarefa para ajustar comentário de código ou discrepância de documentação
**Problema encontrado:** o README promete `Relatórios Automáticos` com envio diário às 18:10, mas o código atual não agenda job diário (`run_daily`), apenas job repetitivo de vigilância de preço e comando manual `/hoje`.

**Tarefa sugerida:**
- Escolher uma direção e alinhar documentação + implementação:
  1. **Implementar** agendamento diário real no bot (ex.: `job_queue.run_daily(...)`), **ou**
  2. **Atualizar README** para refletir o comportamento atual, removendo a promessa de envio diário automático.
- Incluir no README como configurar timezone e chat de destino para relatórios automáticos.

---

## 4) Tarefa para melhorar um teste
**Problema encontrado:** suíte de testes praticamente inexistente (`bot/tests.py` contém apenas o stub padrão).

**Tarefa sugerida:**
- Criar testes unitários para propriedades críticas de `FundoImobiliario` (`dividend_yield`, `lucro_total`, `p_vp`, `magic_number`, `progresso_magic`).
- Criar teste de integração simples da `home` view validando:
  - cálculo de `total_investido` e `renda_estimada`;
  - presença de chaves de contexto para o gráfico (`labels_grafico`, `dados_grafico`);
  - comportamento com carteira vazia e com ativos.
- Rodar `python manage.py test` no CI para prevenir regressões.
