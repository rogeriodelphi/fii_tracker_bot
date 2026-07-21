import io
import re
import pdfplumber
from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404
from .forms import ImportarPDFForm
from .models import FundoImobiliario
from .forms import FundoImobiliarioForm

def home(request):
    fundos = FundoImobiliario.objects.all().order_by('tipo', 'ticker')

    total_investido = sum(float(f.quantidade or 0) * float(f.preco_medio or 0) for f in fundos if f.quantidade > 0)
    renda_estimada  = sum(float(f.quantidade or 0) * float(f.ultimo_dividendo or 0) for f in fundos if f.quantidade > 0)
    magic_atingidos = sum(1 for f in fundos if f.quantidade >= f.magic_number and f.magic_number > 0)
    total_ativos    = fundos.filter(quantidade__gt=0).count()

    # Mapeamento para juntar todos os segmentos de FIIs em um único grupo
    SEGMENTOS_FII = {
        'Fiagros', 'Híbrido', 'Logístico', 'Não Definido', 'Outros',
        'Papel', 'Shoppings', 'Tijolo', 'Tijolos', 'Títulos e Valores Mobiliários',
        'FII', 'FIIs'
    }

    categorias = {}
    distribuicao = {}

    for f in fundos:
        # Se o tipo do ativo for um dos segmentos imobiliários, força para "FIIs"
        tipo_original = f.tipo or 'Não Definido'
        if tipo_original in SEGMENTOS_FII:
            tipo = 'FIIs'
        else:
            tipo = tipo_original

        qtd = float(f.quantidade or 0)
        p_medio = float(f.preco_medio or 0)
        p_atual = float(f.preco_atual or p_medio)

        # Cálculo do valor investido e valor atual do ativo
        valor_investido_ativo = (1 * p_medio) if tipo == 'Renda Fixa' else (qtd * p_medio)
        valor_atual_ativo = (1 * p_atual) if tipo == 'Renda Fixa' else (qtd * p_atual)

        # Somatório para o gráfico de pizza
        distribuicao[tipo] = distribuicao.get(tipo, 0) + valor_atual_ativo

        # Agrupamento dentro das categorias (sanfona)
        if tipo not in categorias:
            categorias[tipo] = {
                'itens': [],
                'total_valor': 0,
                'total_investido': 0,
                'qtd_ativos': 0,
            }

        categorias[tipo]['itens'].append(f)
        categorias[tipo]['total_valor'] += valor_atual_ativo
        categorias[tipo]['total_investido'] += valor_investido_ativo
        categorias[tipo]['qtd_ativos'] += 1

    patrimonio_total = sum(distribuicao.values()) or 1

    # Cálculo do % na carteira e rentabilidade de cada categoria
    for tipo, dados in categorias.items():
        lucro_cat = dados['total_valor'] - dados['total_investido']
        dados['rentabilidade'] = (lucro_cat / dados['total_investido'] * 100) if dados['total_investido'] > 0 else 0
        dados['percentual_carteira'] = round((dados['total_valor'] / patrimonio_total) * 100, 1)

    percentuais = {tipo: round(valor / patrimonio_total * 100, 1) for tipo, valor in distribuicao.items()}

    # Cores personalizadas dos gráficos por tipo
    CORES_TIPO = {
        'FIIs':           '#90caf9',
        'FII':            '#90caf9',
        'Ações':          '#81c784',
        'BDR':            '#ce93d8',
        'ETF':            '#ffcc80',
        'Cripto':         '#80cbc4',
        'Tesouro Direto': '#fff176',
        'Renda Fixa':     '#ef9a9a',
        'Não Definido':   '#aaaaaa',
    }
    cores_grafico = [CORES_TIPO.get(t, '#aaaaaa') for t in distribuicao.keys()]

    context = {
        'fundos':                fundos,
        'categorias':            categorias,
        'patrimonio_total':      patrimonio_total,
        'total_investido':       total_investido,
        'renda_estimada':        renda_estimada,
        'magic_atingidos':       magic_atingidos,
        'total_ativos':          total_ativos,
        'labels_grafico':        list(distribuicao.keys()),
        'dados_grafico':         list(distribuicao.values()),
        'percentuais_grafico':   list(percentuais.values()),
        'cores_grafico':         cores_grafico,
    }
    return render(request, 'index.html', context)


def limpar_valor_monetario(texto):
    """Converte valores no formato 'R$ 1.234,56' para float (1234.56)."""
    if not texto:
        return 0.0
    limpo = (
        str(texto)
        .replace('R$', '')
        .replace('%', '')
        .replace(' ', '')
        .replace('.', '')
        .replace(',', '.')
        .strip()
    )
    try:
        return float(limpo)
    except ValueError:
        return 0.0


def importar_carteira(request):
    if request.method == 'POST':
        form = ImportarPDFForm(request.POST, request.FILES)
        if form.is_valid():
            arquivo = request.FILES['arquivo_pdf']

            atualizados = 0
            criados = 0

            try:
                # Carrega o PDF diretamente da memória
                with pdfplumber.open(io.BytesIO(arquivo.read())) as pdf:
                    for pagina in pdf.pages:
                        # 1. Tenta extrair estruturado como tabela
                        tabelas = pagina.extract_tables()

                        for tabela in tabelas:
                            for linha in tabela:
                                if not linha:
                                    continue

                                # Limpa valores nulos dentro da linha
                                colunas = [
                                    str(c).strip() for c in linha if c is not None
                                ]

                                if len(colunas) >= 3:
                                    ticker = colunas[0].upper().strip()

                                    # Expressão regular para identificar Tickers da B3 (Ex: MXRF11, PETR4, IVVB11, etc.)
                                    if re.match(r'^[A-Z0-9]{4,8}$', ticker):
                                        qtd = limpar_valor_monetario(colunas[1])
                                        p_medio = (
                                            limpar_valor_monetario(colunas[2])
                                            if len(colunas) > 2
                                            else 0.0
                                        )
                                        p_atual = (
                                            limpar_valor_monetario(colunas[3])
                                            if len(colunas) > 3
                                            else p_medio
                                        )

                                        if qtd > 0 or p_medio > 0 or p_atual > 0:
                                            (
                                                obj,
                                                created,
                                            ) = FundoImobiliario.objects.update_or_create(
                                                ticker=ticker,
                                                defaults={
                                                    'quantidade': qtd,
                                                    'preco_medio': p_medio,
                                                    'preco_atual': p_atual,
                                                },
                                            )
                                            if created:
                                                criados += 1
                                            else:
                                                atualizados += 1

                        # 2. Fallback: Se não detectou tabelas nativas, varre o texto linha por linha
                        if not tabelas:
                            texto_pagina = pagina.extract_text() or ''
                            for linha in texto_pagina.splitlines():
                                partes = [
                                    p.strip()
                                    for p in re.split(r'\s{2,}', linha)
                                    if p.strip()
                                ]
                                if len(partes) >= 3:
                                    ticker = partes[0].upper().strip()
                                    if re.match(r'^[A-Z0-9]{4,8}$', ticker):
                                        qtd = limpar_valor_monetario(partes[1])
                                        p_medio = (
                                            limpar_valor_monetario(partes[2])
                                            if len(partes) > 2
                                            else 0.0
                                        )
                                        p_atual = (
                                            limpar_valor_monetario(partes[3])
                                            if len(partes) > 3
                                            else p_medio
                                        )

                                        (
                                            obj,
                                            created,
                                        ) = FundoImobiliario.objects.update_or_create(
                                            ticker=ticker,
                                            defaults={
                                                'quantidade': qtd,
                                                'preco_medio': p_medio,
                                                'preco_atual': p_atual,
                                            },
                                        )
                                        if created:
                                            criados += 1
                                        else:
                                            atualizados += 1

                if atualizados > 0 or criados > 0:
                    messages.success(
                        request,
                        f'PDF processado com sucesso! {atualizados} ativos atualizados e {criados} novos criados.',
                    )
                else:
                    messages.warning(
                        request,
                        'Nenhum ativo reconhecido no PDF. Certifique-se de enviar o relatório da carteira.',
                    )

                return redirect('home')

            except Exception as e:
                messages.error(
                    request, f'Erro ao ler o arquivo PDF: {str(e)}'
                )
    else:
        form = ImportarPDFForm()

    return render(request, 'importar_carteira.html', {'form': form})


def cadastrar_ativo(request):
    if request.method == 'POST':
        form = FundoImobiliarioForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f"Ativo {form.cleaned_data['ticker']} cadastrado com sucesso!")
            return redirect('home')
    else:
        form = FundoImobiliarioForm()

    return render(request, 'cadastrar_ativo.html', {'form': form, 'acao': 'Cadastrar'})


def editar_ativo(request, pk):
    fundo = get_object_or_404(FundoImobiliario, pk=pk)
    if request.method == 'POST':
        form = FundoImobiliarioForm(request.POST, instance=fundo)
        if form.is_valid():
            form.save()
            messages.success(request, f"Ativo {fundo.ticker} atualizado com sucesso!")
            return redirect('home')
    else:
        form = FundoImobiliarioForm(instance=fundo)

    return render(request, 'cadastrar_ativo.html', {'form': form, 'acao': 'Editar', 'fundo': fundo})


def excluir_ativo(request, pk):
    fundo = get_object_or_404(FundoImobiliario, pk=pk)
    if request.method == 'POST':
        ticker = fundo.ticker
        fundo.delete()
        messages.success(request, f"Ativo {ticker} removido com sucesso!")
        return redirect('home')
    return render(request, 'confirmar_exclusao.html', {'fundo': fundo})