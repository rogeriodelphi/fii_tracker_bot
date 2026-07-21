from django.core.management.base import BaseCommand
from django.db import transaction
from bot.models import FundoImobiliario

DADOS_ACOES = [
    {"ticker": "VALE3", "qtd": 27, "pm": 76.43, "alvo": 72.30},
    {"ticker": "TAEE11", "qtd": 35, "pm": 40.46, "alvo": 40.00},
    {"ticker": "ITUB4", "qtd": 30, "pm": 40.17, "alvo": 38.71},
    {"ticker": "BBAS3", "qtd": 58, "pm": 19.98, "alvo": 19.43},
    {"ticker": "WEGE3", "qtd": 18, "pm": 44.40, "alvo": 43.61},
    {"ticker": "B3SA3", "qtd": 50, "pm": 15.46, "alvo": 14.30},
    {"ticker": "CMIG4", "qtd": 68, "pm": 11.17, "alvo": 10.70},
    {"ticker": "CPLE3", "qtd": 45, "pm": 14.82, "alvo": 14.29},
    {"ticker": "AXIA3", "qtd": 9, "pm": 50.77, "alvo": 49.62},
    {"ticker": "EGIE3", "qtd": 15, "pm": 31.36, "alvo": 29.85},
    {"ticker": "RANI3", "qtd": 45, "pm": 7.88, "alvo": 7.50},
    {"ticker": "SAPR4", "qtd": 31, "pm": 7.10, "alvo": 6.97},
    {"ticker": "SANB4", "qtd": 10, "pm": 13.73, "alvo": 13.03},
    {"ticker": "BBDC4", "qtd": 6, "pm": 17.57, "alvo": 17.50},
    {"ticker": "ITSA4", "qtd": 8, "pm": 12.76, "alvo": 12.73},
    {"ticker": "KLBN11", "qtd": 6, "pm": 16.71, "alvo": 16.68},
    {"ticker": "SUZB3", "qtd": 2, "pm": 39.64, "alvo": 39.62},
    {"ticker": "PETR4", "qtd": 2, "pm": 37.81, "alvo": 37.79},
    {"ticker": "POMO4", "qtd": 11, "pm": 5.26, "alvo": 5.26},
    {"ticker": "GOAU4", "qtd": 5, "pm": 9.47, "alvo": 9.47},
    {"ticker": "TASA4", "qtd": 10, "pm": 4.82, "alvo": 4.50},
    {"ticker": "BBSE3", "qtd": 1, "pm": 39.01, "alvo": 38.99},
]


class Command(BaseCommand):
    def handle(self, *args, **options):
        self.stdout.write("🔄 Atualizando Ações no banco de dados...")
        with transaction.atomic():
            for item in DADOS_ACOES:
                fundo, _ = FundoImobiliario.objects.get_or_create(ticker=item['ticker'])
                fundo.quantidade = item['qtd']
                fundo.tipo = "Ação"
                fundo.preco_medio = item['pm']
                fundo.preco_teto = item['alvo']
                fundo.save()
                self.stdout.write(
                    f"  └─ ✅ {item['ticker']} -> Qtd: {item['qtd']} | PM: R$ {item['pm']:.2f} | Alvo: R$ {item['alvo']:.2f}")

        self.stdout.write(self.style.SUCCESS("🎉 Sincronização de Ações concluída com sucesso!"))