from django.core.management.base import BaseCommand
from django.db import transaction
from bot.models import FundoImobiliario

DADOS_RENDA_FIXA = [
    {
        "ticker": "LCI - Caixa Econômica - Pré-Fixado - 11.7%",
        "aplicado": 11073.74,
        "saldo": 11494.83,
        "vencimento": "17/09/2026"
    },
    {
        "ticker": "RDB - NUBANK - TURBO - Pós-Fixado - 120% CDI",
        "aplicado": 9455.91,
        "saldo": 10282.66,
        "vencimento": "Liquidez Diária"
    },
    {
        "ticker": "RDB - Caixa 10.000 - NUBANK - Pós-Fixado - 102.5% CDI",
        "aplicado": 2136.32,
        "saldo": 2473.02,
        "vencimento": "Liquidez Diária"
    },
    {
        "ticker": "RDB - Banco do Brasil - Pós-Fixado - 90% CDI",
        "aplicado": 1788.76,
        "saldo": 1955.02,
        "vencimento": "Liquidez Diária"
    },
    {
        "ticker": "RDB - NUBANK - Bets - Pós-Fixado - 100% CDI",
        "aplicado": 1716.09,
        "saldo": 1850.62,
        "vencimento": "Liquidez Diária"
    },
    {
        "ticker": "RDB - Mercado Pago - Pós-Fixado - 120% CDI",
        "aplicado": 1084.17,
        "saldo": 1095.15,
        "vencimento": "Liquidez Diária"
    },
    {
        "ticker": "CDB - Banco PAN - Pré-Fixado - 15.02%",
        "aplicado": 847.58,
        "saldo": 905.98,
        "vencimento": "21/07/2026"
    },
    {
        "ticker": "CDB - Banco BV - Pré-Fixado - 14.95%",
        "aplicado": 398.74,
        "saldo": 426.09,
        "vencimento": "20/08/2026"
    },
    {
        "ticker": "CDB - Banco Original - Pós-Fixado - 101% CDI",
        "aplicado": 253.00,
        "saldo": 270.70,
        "vencimento": "19/07/2027"
    },
    {
        "ticker": "CDB - Banco Original - Pós-Fixado - 105% CDI",
        "aplicado": 240.00,
        "saldo": 257.45,
        "vencimento": "20/01/2028"
    },
    {
        "ticker": "CDB - NUBANK - Pós-Fixado - 103.5% CDI",
        "aplicado": 200.00,
        "saldo": 215.19,
        "vencimento": "02/07/2027"
    },
    {
        "ticker": "RDB - Itaú - Pós-Fixado - 100% CDI",
        "aplicado": 0.86,
        "saldo": 0.93,
        "vencimento": "Liquidez Diária"
    },
]

class Command(BaseCommand):
    def handle(self, *args, **options):
        self.stdout.write("🔄 Atualizando Renda Fixa no banco de dados...")
        with transaction.atomic():
            for item in DADOS_RENDA_FIXA:
                fundo, _ = FundoImobiliario.objects.get_or_create(ticker=item['ticker'])
                fundo.quantidade = 1
                fundo.tipo = "Renda Fixa"
                fundo.preco_medio = item['aplicado']
                fundo.preco_atual = item['saldo']
                fundo.preco_teto = item['saldo']
                fundo.save()
                self.stdout.write(f"  └─ ✅ {item['ticker']} -> Aplicado: R$ {item['aplicado']:.2f} | Saldo: R$ {item['saldo']:.2f}")

        self.stdout.write(self.style.SUCCESS("🎉 Sincronização de Renda Fixa concluída com sucesso!"))