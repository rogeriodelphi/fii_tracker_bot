from django.core.management.base import BaseCommand
from django.db import transaction
from bot.models import FundoImobiliario

DADOS_CRIPTO = [
    {"ticker": "USDC", "qtd": 109.06047300, "pm": 5.20, "alvo": 5.00},
    {"ticker": "ETH", "qtd": 0.03048309, "pm": 8720.24, "alvo": 8153.24},
    {"ticker": "BTC", "qtd": 0.00040529, "pm": 319252.88, "alvo": 303951.36},
    {"ticker": "SOL", "qtd": 0.12770876, "pm": 391.51, "alvo": 390.98},
]

class Command(BaseCommand):
    def handle(self, *args, **options):
        self.stdout.write("🔄 Atualizando Criptomoedas no banco de dados...")
        with transaction.atomic():
            for item in DADOS_CRIPTO:
                fundo, _ = FundoImobiliario.objects.get_or_create(ticker=item['ticker'])
                fundo.quantidade = item['qtd']
                fundo.tipo = "Cripto"
                fundo.preco_medio = item['pm']
                fundo.preco_teto = item['alvo']
                fundo.save()
                self.stdout.write(f"  └─ ✅ {item['ticker']} -> Qtd: {item['qtd']} | PM: R$ {item['pm']:.2f} | Alvo: R$ {item['alvo']:.2f}")

        self.stdout.write(self.style.SUCCESS("🎉 Sincronização de Criptomoedas concluída com sucesso!"))