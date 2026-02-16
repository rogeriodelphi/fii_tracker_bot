import logging
import yfinance as yf
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

# Configuração de logs para ver erros no terminal
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


# Função para pegar dados do FII
def get_fii_data(ticker):
    # Adiciona .SA se o usuário esqueceu (padrão B3 no Yahoo Finance)
    if not ticker.endswith('.SA'):
        ticker_search = f"{ticker}.SA"
    else:
        ticker_search = ticker

    try:
        fii = yf.Ticker(ticker_search)
        info = fii.info

        # Yahoo Finance as vezes retorna dados incompletos para FIIs,
        # mas 'currentPrice' ou 'regularMarketPrice' costumam funcionar.
        preco = info.get('currentPrice') or info.get('regularMarketPrice')

        if preco is None:
            return None

        return {
            'nome': info.get('longName', ticker),
            'preco': preco,
            'moeda': info.get('currency', 'BRL')
        }
    except Exception as e:
        print(f"Erro ao buscar {ticker}: {e}")
        return None


# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Olá! Sou seu Robô de FIIs. 🏢\n"
        "Use o comando: /fii HGLG11 (ou qualquer outro ticker) para ver o preço."
    )


# Comando /fii [TICKER]
async def consultar_fii(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Por favor, informe o ticker. Ex: /fii MXRF11")
        return

    ticker = context.args[0].upper()
    await update.message.reply_text(f"🔍 Buscando dados de {ticker}...")

    dados = get_fii_data(ticker)

    if dados:
        msg = (
            f"🏢 **Fundo:** {dados['nome']}\n"
            f"💰 **Preço Atual:** R$ {dados['preco']:.2f}\n"
        )
    else:
        msg = f"❌ Não encontrei dados para o fundo **{ticker}**. Verifique se o código está correto."

    await update.message.reply_text(msg, parse_mode='Markdown')


if __name__ == '__main__':
    # COLOQUE SEU TOKEN AQUI
    TOKEN = '7982038153:AAFlhv6V2h24J6-PXi4PmCe4TWfjP9ay6Uo'

    application = ApplicationBuilder().token(TOKEN).build()

    # Adicionando os manipuladores de comando
    start_handler = CommandHandler('start', start)
    fii_handler = CommandHandler('fii', consultar_fii)

    application.add_handler(start_handler)
    application.add_handler(fii_handler)

    print("🤖 Robô iniciado...")
    application.run_polling()