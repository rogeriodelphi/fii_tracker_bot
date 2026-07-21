from django.core.management.base import BaseCommand
from django.db import transaction
from bot.models import FundoImobiliario

DADOS_BDRS = [
    {"ticker": "SPCX34", "qtd": 27, "pm": 50.14, "alvo": 42.75},
    {"ticker": "BURA39", "qtd": 24, "pm": 39.64, "alvo": 35.55},
    {"ticker": "AAPL34", "qtd": 4, "pm": 79.57, "alvo": 79.29},
    {"ticker": "MSFT34", "qtd": 3, "pm": 82.96, "alvo": 81.31},
    {"ticker": "AURA33", "qtd": 3, "pm": 96.01, "alvo": 93.19},
    {"ticker": "TSLA34", "qtd": 4, "pm": 55.05, "alvo": 55.05},
    {"ticker": "NVDC34", "qtd": 2, "pm": 21.01, "alvo": 21.00},
]


class Command(BaseCommand):
    def handle(self, *args, **options):
        self.stdout.write("🔄 Atualizando BDRs no banco de dados...")
        with transaction.atomic():
            for item in DADOS_BDRS:
                fundo, _ = FundoImobiliario.objects.get_or_create(ticker=item['ticker'])
                fundo.quantidade = item['qtd']
                fundo.tipo = "BDR"
                fundo.preco_medio = item['pm']
                fundo.preco_teto = item['alvo']
                fundo.save()
                self.stdout.write(
                    f"  └─ ✅ {item['ticker']} -> Qtd: {item['qtd']} | PM: R$ {item['pm']:.2f} | Alvo: R$ {item['alvo']:.2f}")

        self.stdout.write(self.style.SUCCESS("🎉 Sincronização de BDRs concluída com sucesso!"))