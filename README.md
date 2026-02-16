# 📊 FII Tracker & Monitor B3

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-4.2-green.svg)](https://www.djangoproject.com/)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue.svg)](https://core.telegram.org/bots)

Um ecossistema completo para monitoramento de Fundos Imobiliários em tempo real. O projeto combina um **Bot de Telegram** para operações rápidas e alertas, e um **Dashboard Web** robusto para análise visual de métricas avançadas como P/VP, Preço Teto e a estratégia "Bola de Neve" (Magic Number).

---

## ✨ Funcionalidades

### 🤖 Bot de Telegram (O Operacional)
* **Gestão de Ativos:** Comando `/comprar` para cadastrar compras com preço médio automático.
* **Status em Tempo Real:** Comando `/status` com emojis dinâmicos e cálculo de lucro/prejuízo.
* **Categorização:** Identificação automática por tipos (🏢 Tijolo, 📄 Papel, 📦 FoF, etc).
* **Relatórios Automáticos:** Envio diário de fechamento de mercado às 18:10.
* **Inteligência de Dados:** Limpeza de atualizações pendentes para evitar conflitos de processos.

### 🖥️ Dashboard Web (O Estratégico)
* **Interface Dark Mode:** Design moderno inspirado no estilo GitHub (Primer).
* **Monitor B3:** Tabela dinâmica com indicadores de P/VP (Sinal verde/vermelho).
* **Estratégia Magic Number:** Barras de progresso que mostram quão perto você está de atingir o rendimento que compra uma nova cota (Bola de Neve).
* **Gráficos Dinâmicos:** Gráfico de Rosca (Chart.js) mostrando a diversificação por setor da carteira.
* **Sinal de Compra:** Alertas visuais quando um ativo está abaixo do Preço Teto configurado.

---

## 🛠️ Tecnologias Utilizadas

* **Backend:** Python / Django (ORM, Management Commands).
* **Frontend:** Bootstrap 5, Chart.js, CSS Customizado.
* **Banco de Dados:** SQLite (padrão Django).
* **Integrações:** API do Telegram (python-telegram-bot).
* **Finanças:** Lógica de Preço Médio, Dividend Yield e Projeção Patrimonial.

---

## 🚀 Como Executar o Projeto

1. **Clone o repositório:**
   ```bash
   git clone [https://github.com/seu-usuario/fii-tracker.git](https://github.com/seu-usuario/fii-tracker.git)
   
2. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
3. Configure as Migrations (Banco de Dados):
   ```bash
   python manage.py makemigrations

   python manage.py migrate   
4. Inicie o Dashboard Web:<br>O painel ficará disponível em http://127.0.0.1:8000   
   ```bash
   python manage.py runserver

5. Inicie o Bot do Telegram:
   ```bash
   python manage.py runbot