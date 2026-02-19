import yfinance as yf
import asyncio
import datetime
import pytz
from django.core.management.base import BaseCommand
from asgiref.sync import sync_to_async
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from bot.models import FundoImobiliario
from django.db import transaction, connection, close_old_connections

# --- 1. CONFIGURAÇÕES ---
ALVOS_COMPRA = {
    'KNCR11': 106.00, 'KNRI11': 166.00, 'GARE11': 8.50,
    'MXRF11': 9.70, 'HGLG11': 157.30, 'XPML11': 110.90,
    'XPLG11': 102.20, 'KNIP11': 91.00, 'KNHY11': 99.90,
    'HGBS11': 19.97,
}
INTERVALO_SINAIS = 300  # Aumentado para 5 min para evitar travar o banco


# --- 2. FUNÇÕES DE BUSCA ---
def buscar_preco_na_b3(ticker):
    try:
        simbolo = f"{ticker.upper()}.SA"
        fii = yf.Ticker(simbolo)
        # Tenta pegar o preço de forma rápida
        preco = fii.fast_info.get('last_price')
        if not preco:
            hist = fii.history(period="1d")
            preco = hist['Close'].iloc[-1] if not hist.empty else None
        return float(preco) if preco else None
    except:
        return None


# --- 3. TAREFAS AUTOMÁTICAS (JOBS) ---

# Criamos um dicionário simples fora da função para lembrar o último preço avisado
# Isso evita que o bot repita o alerta se o preço não mudar significativamente
ULTIMO_AVISO_PRECO = {}


async def vigia_precos(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    for ticker, preco_alvo in ALVOS_COMPRA.items():
        preco_atual = await asyncio.to_thread(buscar_preco_na_b3, ticker)

        if preco_atual:
            def update_db():
                connection.close()
                fundo, _ = FundoImobiliario.objects.get_or_create(ticker=ticker.upper())
                preco_anterior = float(fundo.preco_atual) if fundo.preco_atual > 0 else preco_atual
                variacao = ((preco_atual / preco_anterior) - 1) * 100
                fundo.preco_atual = preco_atual
                fundo.preco_teto = preco_alvo
                fundo.variacao = variacao
                fundo.save()
                return variacao

            var = await sync_to_async(update_db)()

            # Verificação de Oportunidade
            if preco_atual <= preco_alvo:
                margem = ((preco_alvo - preco_atual) / preco_alvo) * 100

                # --- Lógica da Trava de Silêncio ---
                # Só envia se:
                # 1. For a primeira vez que atinge o alvo
                # 2. OU se o preço caiu mais de 1% desde o último alerta enviado
                ultimo_p = ULTIMO_AVISO_PRECO.get(ticker, 999999)
                mudanca_desde_alerta = ((preco_atual / ultimo_p) - 1) * 100

                if mudanca_desde_alerta <= -1.0 or ticker not in ULTIMO_AVISO_PRECO:
                    ULTIMO_AVISO_PRECO[ticker] = preco_atual  # Atualiza o último preço avisado

                    tendencia = "📉" if var < 0 else "📈" if var > 0 else "↔️"

                    msg = (
                        f"🚨 **OPORTUNIDADE!**\n\n"
                        f"🏢 **{ticker}**\n"
                        f"💰 Preço: R$ {preco_atual:.2f} {tendencia}\n"
                        f"📉 Alvo: R$ {preco_alvo:.2f}\n"
                        f"🎯 **Margem: {margem:.2f}% abaixo do alvo**\n"
                        f"⚠️ _Aviso: Próximo alerta apenas se cair +1%_"
                    )

                    await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')


async def relatorio_fechamento(update: Update = None, context: ContextTypes.DEFAULT_TYPE = None):
    if update:
        chat_id = update.effective_chat.id
    elif context.job:
        chat_id = context.job.chat_id
    else:
        return

    if update:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    def get_data():
        connection.close()
        fundos = FundoImobiliario.objects.filter(quantidade__gt=0)

        # Criamos o dicionário de dados aqui para evitar o NameError
        resumo = {
            'total_inv': 0,
            'total_atu': 0,
            'total_div': 0,
            'detalhes': []
        }

        for f in fundos:
            v_inv = float(f.quantidade) * float(f.preco_medio)
            v_atu = float(f.quantidade) * float(f.preco_atual)
            div = float(f.quantidade) * float(f.ultimo_dividendo or 0)

            resumo['total_inv'] += v_inv
            resumo['total_atu'] += v_atu
            resumo['total_div'] += div

            # Adiciona uma linha simples para cada fundo
            tipo = (f.tipo or "Tijolo").capitalize()
            resumo['detalhes'].append(f"🔹 {f.ticker} ({tipo})")

        return resumo

    # Aqui definimos a variável 'dados' que estava faltando!
    dados = await sync_to_async(get_data)()

    if dados['total_atu'] == 0 and dados['total_inv'] == 0:
        if update:
            await update.message.reply_text("📭 Carteira vazia.")
        return

    lucro = dados['total_atu'] - dados['total_inv']
    perc = (lucro / dados['total_inv'] * 100) if dados['total_inv'] > 0 else 0

    msg = "🏁 **RELATÓRIO PATRIMONIAL** 🏁\n"
    msg += f"📅 {datetime.datetime.now().strftime('%d/%m/%Y')}\n\n"

    # Lista os ativos incluídos no fechamento
    msg += "\n".join(dados['detalhes']) + "\n\n"

    msg += f"💵 Patrimônio Atual: *R$ {dados['total_atu']:.2f}*\n"
    msg += f"📈 Resultado Total: *R$ {lucro:+.2f}* ({perc:+.2f}%)\n"
    msg += f"💸 Proventos Est.: *R$ {dados['total_div']:.2f}*"

    await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')

# --- 4. HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    # Remove jobs antigos para não duplicar
    current_jobs = context.job_queue.get_jobs_by_name(f"vigia_{chat_id}")
    for job in current_jobs: job.schedule_removal()

    context.job_queue.run_repeating(vigia_precos, interval=INTERVALO_SINAIS, first=10, chat_id=chat_id,
                                    name=f"vigia_{chat_id}")

    await update.message.reply_text("🚀 **Sistemas Ativados!**\nVigiando ativos e pronto para ordens.")


async def comprar_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        ticker = context.args[0].upper().strip()
        qtd = int(context.args[1])
        preco = float(context.args[2].replace(',', '.'))
        # Pega o tipo se o usuário digitar, senão fica "Tijolo" por padrão
        tipo = context.args[3].capitalize() if len(context.args) > 3 else "Tijolo"

        def db_work():
            connection.close()
            with transaction.atomic():
                fundo, _ = FundoImobiliario.objects.get_or_create(ticker=ticker)

                # Atualiza o tipo (mesmo que o fundo já exista)
                fundo.tipo = tipo

                qtd_ant = fundo.quantidade or 0
                pm_ant = float(fundo.preco_medio or 0)
                nova_qtd = qtd_ant + qtd
                novo_pm = ((qtd_ant * pm_ant) + (qtd * preco)) / nova_qtd

                fundo.quantidade = nova_qtd
                fundo.preco_medio = novo_pm
                fundo.save()
                return nova_qtd, tipo

        res_qtd, res_tipo = await sync_to_async(db_work)()
        await update.message.reply_text(f"✅ {ticker} ({res_tipo}) atualizado para {res_qtd} cotas.")
    except Exception as e:
        await update.message.reply_text(
            f"❌ Erro! Use: /comprar TICKER QTD PRECO TIPO\nEx: /comprar MXRF11 10 9.74 Papel")


from asgiref.sync import sync_to_async
from django.db import connection


async def vender_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        ticker = context.args[0].upper()
        qtd_venda = int(context.args[1])
        print(f"DEBUG: Tentando vender {qtd_venda} de {ticker}...")  # Veja isso no terminal!

        def db_venda():
            from django.db import connection
            connection.close()  # Libera o banco para evitar 'Database is locked'

            fundo = FundoImobiliario.objects.filter(ticker=ticker).first()
            if not fundo:
                return f"❌ {ticker} não encontrado."

            if fundo.quantidade < qtd_venda:
                return f"❌ Você só tem {fundo.quantidade} cotas."

            fundo.quantidade -= qtd_venda
            fundo.save()
            return f"✅ Vendido! {ticker} agora tem {fundo.quantidade} cotas."

        msg = await sync_to_async(db_venda)()
        await update.message.reply_text(msg)

    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Use: /vender TICKER QTD")
    except Exception as e:
        print(f"ERRO NO VENDER: {e}")
        await update.message.reply_text(f"💥 Erro: {e}")


async def dividendo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        ticker = context.args[0].upper()
        valor = float(context.args[1].replace(',', '.'))

        def save_div():
            connection.close()
            fundo = FundoImobiliario.objects.get(ticker=ticker)
            fundo.ultimo_dividendo = valor
            fundo.save()

        await sync_to_async(save_div)()
        await update.message.reply_text(f"✅ Provento de {ticker} atualizado: R$ {valor:.2f}")
    except:
        await update.message.reply_text("❌ Use: /div TICKER VALOR")


async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    def buscar_dados():
        connection.close()
        fundos = FundoImobiliario.objects.filter(quantidade__gt=0).order_by('-quantidade')

        if not fundos.exists():
            return None

        EMOJI_TIPOS = {
            'Tijolo': '🏢',
            'Papel': '📄',
            'Fof': '📦',
            'Híbrido': '🔄',
            'Desenvolvimento': '🏗️'
        }

        total_investido = 0
        total_atual = 0
        renda_mensal = 0
        linhas = []

        for f in fundos:
            qtd = f.quantidade
            v_inv = float(qtd) * float(f.preco_medio)
            v_atu = float(qtd) * float(f.preco_atual)
            lucro = v_atu - v_inv
            perc_lucro = (lucro / v_inv * 100) if v_inv > 0 else 0
            renda = float(qtd) * float(f.ultimo_dividendo or 0)

            total_investido += v_inv
            total_atual += v_atu
            renda_mensal += renda

            # Pega o tipo do banco. Se estiver vazio no banco, usa "Tijolo"
            tipo_fii = (f.tipo or "Tijolo").capitalize()
            emoji_tipo = EMOJI_TIPOS.get(tipo_fii, '💰')

            emoji_rent = "🟢" if lucro >= 0 else "🔴"

            linhas.append(
                f"{emoji_rent} *{f.ticker}* ({emoji_tipo} {tipo_fii})\n"
                f"      {qtd} cotas | Lucro: R$ {lucro:.2f} ({perc_lucro:.1f}%)"
            )

        return {
            'linhas': linhas,
            'investido': total_investido,
            'atual': total_atual,
            'renda': renda_mensal,
            'lucro_total': total_atual - total_investido
        }

    # A variável 'dados' DEVE ser definida aqui, fora da subfunção
    try:
        dados = await sync_to_async(buscar_dados)()
    except Exception as e:
        print(f"Erro ao buscar dados: {e}")
        await update.message.reply_text("❌ Erro ao acessar o banco de dados.")
        return

    # Verificação se a carteira está vazia
    if dados is None:
        await update.message.reply_text("📭 Sua carteira está vazia no momento.")
        return

    # Montando a mensagem final
    msg = "📊 **RESUMO DA CARTEIRA**\n\n"
    msg += "\n".join(dados['linhas'])
    msg += "\n\n" + "─" * 15 + "\n"
    msg += f"💰 **Total Investido:** R$ {dados['investido']:.2f}\n"
    msg += f"📈 **Patrimônio Atual:** R$ {dados['atual']:.2f}\n"
    msg += f"💵 **Resultado:** R$ {dados['lucro_total']:+.2f}\n"
    msg += f"💸 **Renda Mensal Est.:** R$ {dados['renda']:.2f}"

    await update.message.reply_text(msg, parse_mode='Markdown')


# --- 5. CLASSE PRINCIPAL ---
class Command(BaseCommand):
    def handle(self, *args, **options):
        TOKEN = '7982038153:AAF9iP9-XVgVN3wFSSRyhkwj943_K3-NeJY'

        app = (ApplicationBuilder().token(TOKEN)
               .connect_timeout(30).read_timeout(30).write_timeout(30).build())

        # REGISTRO DE TODOS OS COMANDOS
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("comprar", comprar_handler))
        app.add_handler(CommandHandler("vender", vender_handler))
        app.add_handler(CommandHandler("div", dividendo_handler))
        app.add_handler(CommandHandler("hoje", relatorio_fechamento))
        app.add_handler(CommandHandler("status", status_handler))
        app.add_handler(CommandHandler("carteira", status_handler))  # Dois nomes para o mesmo comando

        # print("--- BOT RODANDO (WAL MODE) ---")
        # if __name__ == '__main__':
        #     # drop_pending_updates=True limpa o "cache" de mensagens ao iniciar
        #     app.run_polling(drop_pending_updates=True)

        # ... (todo o seu código anterior de funções e comandos) ...

        print("🚀 Bot iniciado com sucesso! Pressione Ctrl+C para parar.")

        # Inicia o monitoramento e mantém o script rodando infinitamente
        app.run_polling(drop_pending_updates=True)

    # Esta parte garante que o Django execute o loop corretamente
    if __name__ == "__main__":
        try:
            # Chame aqui a sua função principal que configura o 'app'
            # ou certifique-se que o código acima não está dentro de uma função solta
            pass
        except KeyboardInterrupt:
            pass
