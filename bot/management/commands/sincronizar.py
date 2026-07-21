from django.core.management.base import BaseCommand
from django.db import transaction
from bot.models import FundoImobiliario

DADOS_TELA = [
    {"ticker": "GARE11", "qtd": 929, "segmento": "Híbrido", "pm": 8.29, "alvo": 8.10},
    {"ticker": "KNRI11", "qtd": 38, "segmento": "Híbrido", "pm": 157.20, "alvo": 150.00},
    {"ticker": "HGLG11", "qtd": 34, "segmento": "Logístico", "pm": 152.71, "alvo": 148.37},
    {"ticker": "XPML11", "qtd": 30, "segmento": "Shoppings", "pm": 107.19, "alvo": 105.00},
    {"ticker": "TRXF11", "qtd": 20, "segmento": "Híbrido", "pm": 91.20, "alvo": 90.76},
    {"ticker": "BTLG11", "qtd": 16, "segmento": "Logístico", "pm": 103.27, "alvo": 102.00},
    {"ticker": "VISC11", "qtd": 15, "segmento": "Shoppings", "pm": 106.24, "alvo": 103.99},
    {"ticker": "KNCR11", "qtd": 9, "segmento": "Títulos e Valores Mobiliários", "pm": 105.07, "alvo": 104.34},
    {"ticker": "MXRF11", "qtd": 79, "segmento": "Híbrido", "pm": 9.59, "alvo": 9.60},
    {"ticker": "BTCI11", "qtd": 70, "segmento": "Títulos e Valores Mobiliários", "pm": 9.26, "alvo": 9.00},
    {"ticker": "XPCI11", "qtd": 6, "segmento": "Títulos e Valores Mobiliários", "pm": 82.26, "alvo": 82.23},
    {"ticker": "CPTS11", "qtd": 65, "segmento": "Títulos e Valores Mobiliários", "pm": 7.59, "alvo": 7.33},
    {"ticker": "SNAG11", "qtd": 38, "segmento": "Fiagros", "pm": 9.99, "alvo": 9.89},
    {"ticker": "VGIR11", "qtd": 36, "segmento": "Títulos e Valores Mobiliários", "pm": 9.65, "alvo": 9.58},
    {"ticker": "GGRC11", "qtd": 30, "segmento": "Logístico", "pm": 9.71, "alvo": 9.66},
    {"ticker": "ZAGH11", "qtd": 15, "segmento": "Híbrido", "pm": 8.42, "alvo": 8.00},
    {"ticker": "SNEL11", "qtd": 15, "segmento": "Outros", "pm": 8.36, "alvo": 8.16},
    {"ticker": "VGIA11", "qtd": 12, "segmento": "Fiagros", "pm": 9.52, "alvo": 9.32},
    {"ticker": "RZTR11", "qtd": 1, "segmento": "Híbrido", "pm": 86.26, "alvo": 86.23},
]

class Command(BaseCommand):
    def handle(self, *args, **options):
        self.stdout.write("🔄 Atualizando banco de dados...")
        with transaction.atomic():
            for item in DADOS_TELA:
                fundo, _ = FundoImobiliario.objects.get_or_create(ticker=item['ticker'])
                fundo.quantidade = item['qtd']
                fundo.tipo = item['segmento']
                fundo.preco_medio = item['pm']
                fundo.preco_teto = item['alvo']
                fundo.save()
                self.stdout.write(f"  └─ ✅ {item['ticker']} atualizado!")
        self.stdout.write(self.style.SUCCESS("🎉 Todos os ativos foram sincronizados com sucesso!"))