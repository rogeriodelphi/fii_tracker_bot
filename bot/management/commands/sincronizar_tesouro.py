from django.core.management.base import BaseCommand
from django.db import transaction
from bot.models import FundoImobiliario

DADOS_TESOURO = [
    {
        "ticker": "Tesouro Prefixado 2029",
        "qtd": 0.94,
        "preco_atual": 720.06,
        "saldo": 676.86
    },
]

class Command(BaseCommand):
    def handle(self, *args, **options):
        self.stdout.write("🔄 Atualizando Tesouro Direto no banco de dados...")
        with transaction.atomic():
            for item in DADOS_TESOURO:
                fundo, _ = FundoImobiliario.objects.get_or_create(ticker=item['ticker'])
                fundo.quantidade = item['qtd']
                fundo.tipo = "Tesouro Direto"
                fundo.preco_medio = item['preco_atual']
                fundo.preco_atual = item['preco_atual']
                fundo.preco_teto = item['preco_atual']
                fundo.save()
                self.stdout.write(f"  └─ ✅ {item['ticker']} -> Qtd: {item['qtd']} | Valor/Cota: R$ {item['preco_atual']:.2f}")

        self.stdout.write(self.style.SUCCESS("🎉 Sincronização de Tesouro Direto concluída com sucesso!"))