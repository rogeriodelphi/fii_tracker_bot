from django.shortcuts import render
from .models import FundoImobiliario

def home(request):
    fundos = FundoImobiliario.objects.all()
    fundos_ativos = fundos.filter(quantidade__gt=0)

    # Calculando Totais
    total_investido = sum(f.quantidade * float(f.preco_medio) for f in fundos if f.quantidade > 0)
    renda_estimada = sum(f.quantidade * float(f.ultimo_dividendo) for f in fundos if f.quantidade > 0)

    # Contador de Magic Numbers atingidos
    magic_atingidos = sum(1 for f in fundos if f.quantidade >= f.magic_number and f.magic_number > 0)
    total_ativos = fundos.filter(quantidade__gt=0).count()

    total_investido = sum(f.quantidade * float(f.preco_medio or 0) for f in fundos if f.quantidade > 0)
    renda_estimada = sum(f.quantidade * float(f.ultimo_dividendo or 0) for f in fundos if f.quantidade > 0)

    # Novo: Cálculo para o Gráfico de Diversificação
    distribuicao = {}
    for f in fundos:
        tipo = (f.tipo or "Tijolo").capitalize()
        valor_atual = f.quantidade * float(f.preco_atual or 0)
        distribuicao[tipo] = distribuicao.get(tipo, 0) + valor_atual


    context = {
        'fundos': fundos,
        'total_investido': total_investido,
        'renda_estimada': renda_estimada,
        'magic_atingidos': magic_atingidos,
        'total_ativos': total_ativos,
        'labels_grafico': list(distribuicao.keys()),
        'dados_grafico': list(distribuicao.values()),
        'labels_grafico': list(distribuicao.keys()),
        'dados_grafico': list(distribuicao.values()),
    }
    return render(request, 'index.html', context)