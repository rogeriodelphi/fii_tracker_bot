import logging
import os
import asyncio
import datetime
import yfinance as yf
from dotenv import load_dotenv
from django.core.management.base import BaseCommand
from asgiref.sync import sync_to_async
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from bot.models import FundoImobiliario
from django.db import transaction, close_old_connections

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- 1. CONFIGURAÇÕES ---

_raw_ids = os.environ.get('TELEGRAM_CHAT_IDS', '')
CHAT_IDS_AUTORIZADOS = {int(cid) for cid in _raw_ids.split(',') if cid.strip()}
# Pega o primeiro ID como padrão para jobs de fundo caso /start não seja enviado
CHAT_ID_PADRAO = list(CHAT_IDS_AUTORIZADOS)[0] if CHAT_IDS_AUTORIZADOS else None

ALVOS_COMPRA_INICIAIS = {
    # Ações na carteira
    'AXIA3': 49.62,
    'B3SA3': 14.30,
    'BBAS3': 19.43,
    'BBDC4': 17.50,
    'BBSE3': 38.99,
    'CMIG4': 10.70,
    'CPLE3': 14.29,
    'EGIE3': 29.85,
    'GOAU4': 9.47,
    'ITSA4': 12.73,
    'ITUB4': 38.71,
    'KLBN11': 16.68,
    'PETR4': 37.79,
    'POMO4': 5.16,
    'RANI3': 7.50,
    'SANB4': 13.03,
    'SAPR4': 6.97,
    'SUZB3': 39.62,
    'TAEE11': 40.00,
    'TASA4': 4.50,
    'VALE3': 71.91,
    'WEGE3': 43.10,

    # FIIs na carteira
    'BTCI11': 9.00,
    'BTLG11': 102.00,
    'CPTS11': 7.33,
    'GARE11': 8.10,
    'GGRC11': 9.66,
    'HGLG11': 148.37,
    'KNCR11': 104.34,
    'KNRI11': 150.00,
    'MXRF11': 9.60,
    'RZTR11': 86.23,
    'SNAG11': 9.89,
    'SNEL11': 8.16,
    'TRXF11': 90.76,
    'VGIA11': 9.32,
    'VGIR11': 9.58,
    'VISC11': 103.99,
    'XPCI11': 82.23,
    'XPML11': 105.00,
    'ZAGH11': 8.00,
}

INTERVALO_SINAIS = 180  # 3 minutos em segundos


# --- 2. HELPERS ---

def autorizado(func):
    """Rejeita comandos de chat_ids não cadastrados em TELEGRAM_CHAT_IDS."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if CHAT_IDS_AUTORIZADOS and update.effective_chat.id not in CHAT_IDS_AUTORIZADOS:
            await update.message.reply_text("⛔ Acesso não autorizado.")
            return
        return await func(update, context)
    wrapper.__name__ = func.__name__
    return wrapper


def buscar_preco_na_b3(ticker):
    try:
        simbolo = f"{ticker.upper()}.SA"
        fii = yf.Ticker(simbolo)
        preco = fii.fast_info.get('last_price')
        if not preco:
            hist = fii.history(period="1d")
            preco = hist['Close'].iloc[-1] if not hist.empty else None
        return float(preco) if preco else None
    except Exception:
        logger.exception("Erro ao buscar preço de %s", ticker)
        return None


def _seed_alvos():
    """Força a atualização de todos os preco_teto no banco com base em ALVOS_COMPRA_INICIAIS."""
    close_old_connections()
    for ticker, preco_alvo in ALVOS_COMPRA_INICIAIS.items():
        fundo, _ = FundoImobiliario.objects.get_or_create(ticker=ticker.upper())
        # Atualiza SEMPRE o preco_teto para o valor atual do dicionario
        fundo.preco_teto = preco_alvo
        fundo.save(update_fields=['preco_teto'])


# --- 3. TAREFAS AUTOMÁTICAS (JOBS) ---
ULTIMO_AVISO_PRECO = {}


async def vigia_precos(context: ContextTypes.DEFAULT_TYPE):
    # Garante a obtenção de um Chat ID válido
    chat_id = getattr(context.job, 'chat_id', CHAT_ID_PADRAO)
    if not chat_id:
        logger.warning("Vigia de preços rodou, mas nenhum Chat ID foi configurado/autorizado.")
        return

    # 1. Atualiza FORÇADAMENTE o preco_teto de todos os ativos da lista e busca apenas eles
    def sincronizar_alvos_iniciais():
        close_old_connections()

        tickers_desejados = [t.upper() for t in ALVOS_COMPRA_INICIAIS.keys()]

        for ticker, alvo in ALVOS_COMPRA_INICIAIS.items():
            fundo, _ = FundoImobiliario.objects.get_or_create(ticker=ticker.upper())
            # Força a sobrescrita no banco caso o valor da lista tenha mudado
            if float(fundo.preco_teto or 0) != float(alvo):
                fundo.preco_teto = alvo
                fundo.save(update_fields=['preco_teto'])

        # Traz do banco EXCLUSIVAMENTE os ativos que pertencem à sua lista
        return list(
            FundoImobiliario.objects.filter(ticker__in=tickers_desejados)
            .values('ticker', 'preco_teto')
        )

    lista_ativos = await sync_to_async(sincronizar_alvos_iniciais)()
    logger.info(f"🔄 Executando verificação de {len(lista_ativos)} ativos atualizados...")

    # 2. Varre apenas a lista oficial
    for item in lista_ativos:
        ticker = item['ticker']
        preco_alvo = float(item['preco_teto'])

        preco_atual = await asyncio.to_thread(buscar_preco_na_b3, ticker)

        if preco_atual:
            def update_db():
                close_old_connections()
                fundo = FundoImobiliario.objects.get(ticker=ticker)
                preco_anterior = float(
                    fundo.preco_atual) if fundo.preco_atual and fundo.preco_atual > 0 else preco_atual
                variacao = ((preco_atual / preco_anterior) - 1) * 100

                fundo.preco_atual = preco_atual
                fundo.variacao = variacao
                fundo.save()
                return variacao

            var = await sync_to_async(update_db)()

            # Verificação de Oportunidade com o alvo real (R$ 8,10 para GARE11)
            if preco_atual <= preco_alvo:
                margem = ((preco_alvo - preco_atual) / preco_alvo) * 100
                ultimo_p = ULTIMO_AVISO_PRECO.get(ticker)

                # Só avisa se for a 1ª vez ou se o preço caiu ainda mais
                if ultimo_p is None or preco_atual < ultimo_p:
                    ULTIMO_AVISO_PRECO[ticker] = preco_atual

                    tendencia = "📉" if var < 0 else "📈" if var > 0 else "↔️"

                    msg = (
                        f"🚨 **OPORTUNIDADE!**\n\n"
                        f"🏢 **{ticker}**\n"
                        f"💰 Preço: R$ {preco_atual:.2f} {tendencia}\n"
                        f"📉 Alvo: R$ {preco_alvo:.2f}\n"
                        f"🎯 **Margem: {margem:.2f}% abaixo do alvo**\n"
                        f"⏱️ _Próxima checagem em 3 min..._"
                    )

                    await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')


# --- 4. HANDLERS ---

@autorizado
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHAT_ID_PADRAO
    CHAT_ID_PADRAO = update.effective_chat.id

    # Remove agendamentos antigos para o mesmo chat e reinicia
    for job in context.job_queue.get_jobs_by_name(f"vigia_{CHAT_ID_PADRAO}"):
        job.schedule_removal()

    context.job_queue.run_repeating(
        vigia_precos,
        interval=INTERVALO_SINAIS,
        first=5,
        chat_id=CHAT_ID_PADRAO,
        name=f"vigia_{CHAT_ID_PADRAO}"
    )

    await update.message.reply_text("🚀 **Sistemas Ativados!**\nVigiando ativos a cada 3 minutos.")


@autorizado
async def setalvo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Define ou atualiza o preço-alvo de compra de um ativo."""
    try:
        ticker = context.args[0].upper()
        preco = float(context.args[1].replace(',', '.'))

        def save_alvo():
            close_old_connections()
            fundo, _ = FundoImobiliario.objects.get_or_create(ticker=ticker)
            fundo.preco_teto = preco
            fundo.save(update_fields=['preco_teto'])

        await sync_to_async(save_alvo)()
        await update.message.reply_text(f"🎯 Preço-alvo de **{ticker}** atualizado para **R$ {preco:.2f}**!", parse_mode='Markdown')
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Use: `/setalvo TICKER PRECO`\nEx: `/setalvo BBAS3 19.50`", parse_mode='Markdown')
    except Exception:
        logger.exception("Erro no /setalvo")
        await update.message.reply_text("❌ Erro ao definir alvo.")


@autorizado
async def relatorio_fechamento(update: Update = None, context: ContextTypes.DEFAULT_TYPE = None):
    chat_id = update.effective_chat.id if update else getattr(context.job, 'chat_id', CHAT_ID_PADRAO)
    if not chat_id:
        return

    if update:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    def get_data():
        close_old_connections()
        fundos = FundoImobiliario.objects.filter(quantidade__gt=0)
        resumo = {'total_inv': 0, 'total_atu': 0, 'total_div': 0, 'detalhes': []}

        for f in fundos:
            v_inv = float(f.quantidade) * float(f.preco_medio)
            v_atu = float(f.quantidade) * float(f.preco_atual or 0)
            div = float(f.quantidade) * float(f.ultimo_dividendo or 0)

            resumo['total_inv'] += v_inv
            resumo['total_atu'] += v_atu
            resumo['total_div'] += div

            tipo = (f.tipo or "Tijolo").capitalize()
            resumo['detalhes'].append(f"🔹 {f.ticker} ({tipo})")

        return resumo

    dados = await sync_to_async(get_data)()

    if dados['total_atu'] == 0 and dados['total_inv'] == 0:
        if update:
            await update.message.reply_text("📭 Carteira vazia.")
        return

    lucro = dados['total_atu'] - dados['total_inv']
    perc = (lucro / dados['total_inv'] * 100) if dados['total_inv'] > 0 else 0

    msg = "🏁 **RELATÓRIO PATRIMONIAL** 🏁\n"
    msg += f"📅 {datetime.datetime.now().strftime('%d/%m/%Y')}\n\n"
    msg += "\n".join(dados['detalhes']) + "\n\n"
    msg += f"💵 Patrimônio Atual: *R$ {dados['total_atu']:.2f}*\n"
    msg += f"📈 Resultado Total: *R$ {lucro:+.2f}* ({perc:+.2f}%)\n"
    msg += f"💸 Proventos Est.: *R$ {dados['total_div']:.2f}*"

    await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')


@autorizado
async def comprar_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        ticker = context.args[0].upper().strip()
        qtd = int(context.args[1])
        preco = float(context.args[2].replace(',', '.'))
        tipo = context.args[3].capitalize() if len(context.args) > 3 else "Tijolo"

        def db_work():
            close_old_connections()
            with transaction.atomic():
                fundo, _ = FundoImobiliario.objects.get_or_create(ticker=ticker)
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
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Use: /comprar TICKER QTD PRECO TIPO")
    except Exception:
        logger.exception("Erro no /comprar")
        await update.message.reply_text("❌ Erro ao registrar compra.")


@autorizado
async def vender_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        ticker = context.args[0].upper()
        qtd_venda = int(context.args[1])

        def db_venda():
            close_old_connections()
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
    except Exception:
        logger.exception("Erro no /vender")
        await update.message.reply_text("💥 Erro ao registrar venda.")


@autorizado
async def dividendo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        ticker = context.args[0].upper()
        valor = float(context.args[1].replace(',', '.'))

        def save_div():
            close_old_connections()
            fundo = FundoImobiliario.objects.get(ticker=ticker)
            fundo.ultimo_dividendo = valor
            fundo.save()

        await sync_to_async(save_div)()
        await update.message.reply_text(f"✅ Provento de {ticker} atualizado: R$ {valor:.2f}")
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Use: /div TICKER VALOR")
    except Exception:
        logger.exception("Erro no /div")
        await update.message.reply_text("❌ Ticker não encontrado ou erro ao salvar.")


@autorizado
async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    def buscar_dados():
        close_old_connections()
        fundos = FundoImobiliario.objects.filter(quantidade__gt=0).order_by('-quantidade')

        if not fundos.exists():
            return None

        EMOJI_TIPOS = {
            'Tijolo': '🏢',
            'Papel': '📄',
            'Fof': '📦',
            'Híbrido': '🔄',
            'Desenvolvimento': '🏗️',
        }

        total_investido, total_atual, renda_mensal, linhas = 0, 0, 0, []

        for f in fundos:
            qtd = f.quantidade
            v_inv = float(qtd) * float(f.preco_medio)
            v_atu = float(qtd) * float(f.preco_atual or 0)
            lucro = v_atu - v_inv
            perc_lucro = (lucro / v_inv * 100) if v_inv > 0 else 0
            renda = float(qtd) * float(f.ultimo_dividendo or 0)

            total_investido += v_inv
            total_atual += v_atu
            renda_mensal += renda

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
            'lucro_total': total_atual - total_investido,
        }

    try:
        dados = await sync_to_async(buscar_dados)()
    except Exception:
        logger.exception("Erro no /status")
        await update.message.reply_text("❌ Erro ao acessar o banco de dados.")
        return

    if dados is None:
        await update.message.reply_text("📭 Sua carteira está vazia no momento.")
        return

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
        token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if not token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN não definido. Configure o arquivo .env.")

        self.stdout.write("Populando preços-alvo no banco de dados...")
        _seed_alvos()

        app = (
            ApplicationBuilder()
            .token(token)
            .connect_timeout(30)
            .read_timeout(30)
            .write_timeout(30)
            .build()
        )

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("comprar", comprar_handler))
        app.add_handler(CommandHandler("vender", vender_handler))
        app.add_handler(CommandHandler("div", dividendo_handler))
        app.add_handler(CommandHandler("setalvo", setalvo_handler))
        app.add_handler(CommandHandler("hoje", relatorio_fechamento))
        app.add_handler(CommandHandler("status", status_handler))
        app.add_handler(CommandHandler("carteira", status_handler))

        # Inicializa o job automático imediatamente ao subir o bot
        if CHAT_ID_PADRAO:
            app.job_queue.run_repeating(
                vigia_precos,
                interval=INTERVALO_SINAIS,
                first=10,
                chat_id=CHAT_ID_PADRAO,
                name="vigia_global"
            )

        self.stdout.write("🚀 Bot iniciado com sucesso! Pressione Ctrl+C para parar.")
        app.run_polling(drop_pending_updates=True)