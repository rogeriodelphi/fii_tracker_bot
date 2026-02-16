from django.db import models


class FundoImobiliario(models.Model):
    ticker = models.CharField(max_length=10, unique=True)
    tipo = models.CharField(max_length=30, default="Não Definido")
    preco_atual = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    preco_teto = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    ultimo_dividendo = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    valor_patrimonial = models.DecimalField(max_digits=10, decimal_places=2, default=1.00)
    variacao = models.FloatField(default=0.00)

    # ADICIONE ESTES DOIS CAMPOS ABAIXO:
    quantidade = models.IntegerField(default=0)
    preco_medio = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    atualizado_em = models.DateTimeField(auto_now=True)

    @property
    def dividend_yield(self):
        if self.preco_atual > 0:
            return (float(self.ultimo_dividendo) / float(self.preco_atual)) * 100
        return 0

    @property
    def falta_quanto(self):
        if self.preco_atual > self.preco_teto:
            return float(self.preco_atual - self.preco_teto)
        return 0

    @property
    def lucro_total(self):
        if self.quantidade > 0:
            # (Preço Atual - Preço Médio) * Quantidade
            return float(self.preco_atual - self.preco_medio) * self.quantidade
        return 0

    @property
    def p_vp(self):
        if self.valor_patrimonial > 0:
            return float(self.preco_atual) / float(self.valor_patrimonial)
        return 0

    @property
    def magic_number(self):
        if self.ultimo_dividendo > 0 and self.preco_atual > 0:
            # Quantas cotas para o dividendo comprar uma nova cota
            import math
            return math.ceil(float(self.preco_atual) / float(self.ultimo_dividendo))
        return 0

    @property
    def faltam_para_magic(self):
        # Calcula a diferença entre o objetivo e o que você já tem
        total_necessario = self.magic_number
        if total_necessario > self.quantidade:
            return total_necessario - self.quantidade
        return 0

    @property
    def progresso_magic(self):
        target = self.magic_number
        if target > 0:
            percent = (self.quantidade / target) * 100
            return min(percent, 100)
        return 0