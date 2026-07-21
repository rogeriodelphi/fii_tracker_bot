from django import forms
from .models import FundoImobiliario

TIPO_CHOICES = [
    ('',                 '— Selecione o tipo —'),
    ('FII',              'Fundos Imobiliários (FII)'),
    ('Ações',            'Ações'),
    ('BDR',              'BDRs'),
    ('ETF',              'ETFs'),
    ('Cripto',           'Criptomoedas'),
    ('Tesouro Direto',   'Tesouro Direto'),
    ('Renda Fixa',       'Renda Fixa (LCI/LCA/CDB/...)'),
]

_input  = {'class': 'form-control'}
_select = {'class': 'form-select'}
_input_pct = {'class': 'form-control', 'step': '0.01'}
_input_dec = {'class': 'form-control', 'step': '0.01', 'min': '0'}
_input_int = {'class': 'form-control', 'min': '0'}


class ImportarPDFForm(forms.Form):
    arquivo_pdf = forms.FileField(
        label='Selecione o arquivo PDF da Carteira:',
        widget=forms.FileInput(
            attrs={'class': 'form-control', 'accept': '.pdf'}
        ),
    )

class FundoImobiliarioForm(forms.ModelForm):
    tipo = forms.ChoiceField(
        choices=TIPO_CHOICES,
        widget=forms.Select(attrs=_select),
    )

    class Meta:
        model = FundoImobiliario
        fields = [
            'ticker', 'tipo', 'quantidade',
            'preco_atual', 'preco_medio', 'preco_teto', 'variacao',
            'valor_patrimonial', 'ultimo_dividendo',
        ]
        labels = {
            'ticker':            'Ticker',
            'tipo':              'Tipo',
            'quantidade':        'Quantidade de Cotas',
            'preco_atual':       'Preço Atual (R$)',
            'preco_medio':       'Preço Médio (R$)',
            'preco_teto':        'Preço Teto (R$)',
            'variacao':          'Variação do Dia (%)',
            'valor_patrimonial': 'Valor Patrimonial (R$)',
            'ultimo_dividendo':  'Último Dividendo (R$)',
        }
        help_texts = {
            'ticker':            'Ex: MXRF11, HGLG11, KNRI11',
            'preco_teto':        'Preço máximo que você considera compra vantajosa.',
            'valor_patrimonial': 'Valor patrimonial por cota (VP). Usado para calcular o P/VP.',
            'ultimo_dividendo':  'Último provento pago por cota. Usado para calcular o Magic Number.',
            'variacao':          'Variação percentual do dia. Preenchida automaticamente pelo bot.',
        }
        widgets = {
            'ticker':            forms.TextInput(attrs={**_input, 'placeholder': 'Ex: MXRF11', 'style': 'text-transform:uppercase'}),
            'quantidade':        forms.NumberInput(attrs=_input_int),
            'preco_atual':       forms.NumberInput(attrs=_input_dec),
            'preco_medio':       forms.NumberInput(attrs=_input_dec),
            'preco_teto':        forms.NumberInput(attrs=_input_dec),
            'variacao':          forms.NumberInput(attrs=_input_pct),
            'valor_patrimonial': forms.NumberInput(attrs=_input_dec),
            'ultimo_dividendo':  forms.NumberInput(attrs=_input_dec),
        }

    def clean_ticker(self):
        ticker = self.cleaned_data['ticker'].upper().strip()
        qs = FundoImobiliario.objects.filter(ticker=ticker)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Já existe um ativo cadastrado com este ticker.")
        return ticker
