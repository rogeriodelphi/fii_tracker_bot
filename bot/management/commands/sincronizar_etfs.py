from django.core.management.base import BaseCommand
from django.db import transaction
from bot.models import FundoImobiliario

DADOS_ETFS = [
    {"ticker": "GOLD11", "qtd": 9, "pm": 22.62, "alvo": 22.01},
    {"ticker": "BOVA11", "qtd": 1, "pm": 168.26, "alvo": 168.26},
]

class Command(BaseCommand):
    def handle(self, *args, **options):
        self.stdout.write("🔄 Atualizando ETFs no banco de dados...")
        with transaction.atomic():
            for item in DADOS_ETFS:
                fundo, _ = FundoImobiliario.objects.get_or_create(ticker=item['ticker'])
                fundo.quantidade = item['qtd']
                fundo.tipo = "ETF"
                fundo.preco_medio = item['pm']
                fundo.preco_teto = item['alvo']
                fundo.save()
                self.stdout.write(f"  └─ ✅ {item['ticker']} -> Qtd: {item['qtd']} | PM: R$ {item['pm']:.2f} | Alvo: R$ {item['alvo']:.2f}")

        self.stdout.write(self.style.SUCCESS("🎉 Sincronização de ETFs concluída com sucesso!"))