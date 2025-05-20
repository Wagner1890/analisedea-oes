from flask import Flask, render_template, request
import yfinance as yf

app = Flask(__name__)

# Função para formatar valores monetários em R$
def formatar_real(valor):
    return f'R$ {valor:,.2f}'.replace(",", "X").replace(".", ",").replace("X", ".")

# Função para calcular a rentabilidade anual
def calcular_rentabilidade_anual(codigo, anos=10):
    try:
        acao = yf.Ticker(codigo)
        dados_historicos = acao.history(period=f"{anos}y")

        if dados_historicos.empty:
            raise ValueError("Não foi possível obter os dados históricos.")

        preco_inicial = dados_historicos['Close'].iloc[0]
        preco_final = dados_historicos['Close'].iloc[-1]

        rentabilidade_anual = ((preco_final / preco_inicial) ** (1 / anos) - 1) * 100
        return round(rentabilidade_anual, 2)

    except Exception as e:
        print(f"Erro ao calcular rentabilidade anual: {e}")
        return None

# Função para analisar os dados da ação
def analisar_acao(codigo):
    try:
        acao = yf.Ticker(codigo)
        info = acao.info

        nome = info.get('longName', 'Não encontrado')
        preco = round(info.get('regularMarketPrice', 0), 2)
        lucro_por_acao = info.get('trailingEps', 0)
        dividendo = info.get('dividendYield', 0)
        moeda = info.get('currency', 'USD')
        roe = info.get('returnOnEquity')
        margem = info.get('profitMargins')
        div_patrimonio = info.get('debtToEquity')

        pl = preco / lucro_por_acao if lucro_por_acao and lucro_por_acao > 0 else None
        dy = dividendo if dividendo else 0

        # Cálculo do Score aprimorado
        score = 0
        if pl is not None:
            score += max(0, min(100, (100 - pl) * 0.4))
        score += dy * 600 if dy else 0
        if roe: score += roe * 100 * 0.1
        if margem: score += margem * 100 * 0.1
        if div_patrimonio: score -= div_patrimonio * 0.05

        score = max(0, min(100, score))

        return {
            'nome': nome,
            'preco': f'{moeda} {preco:.2f}',
            'moeda': moeda,
            'pl': f'{pl:.2f}' if pl is not None else 'N/A',
            'dy': f'{dy:.2f}%' if dy else 'N/A',
            'score': f'{score:.2f}',
            'pl_float': pl or 0,
            'dy_float': dy or 0,
            'score_float': score,
            'roe': f'{roe * 100:.2f}%' if roe else 'N/A',
            'margem': f'{margem * 100:.2f}%' if margem else 'N/A',
            'divida': f'{div_patrimonio:.2f}' if div_patrimonio else 'N/A',
        }
    except Exception as e:
        print("Erro na análise:", e)
        return None

# Função para simular o investimento
def simular_investimento(aporte, anos, codigo, rentabilidade_anual=None):
    if rentabilidade_anual is None:
        rentabilidade_anual = calcular_rentabilidade_anual(codigo, anos)

    if rentabilidade_anual is None:
        return None

    meses = anos * 12
    rent_mensal = (1 + rentabilidade_anual / 100) ** (1 / 12) - 1
    valor_final = 0
    valores = []
    labels = []

    for mes in range(1, meses + 1):
        valor_final = (valor_final + aporte) * (1 + rent_mensal)
        valores.append(round(valor_final, 2))
        labels.append(f'Mês {mes}')

    return {
        'valor_final': formatar_real(valor_final),
        'valores': valores,
        'meses': labels,
        'rentabilidade': f'{rentabilidade_anual}%'
    }

@app.route('/', methods=['GET', 'POST'])
def index():
    resultado = None
    erro = None

    if request.method == 'POST':
        try:
            codigo = request.form['codigo'].strip().upper()
            if not codigo.endswith('.SA'):
                codigo += '.SA'
            aporte = float(request.form['aporte'])
            anos = int(request.form['anos'])

            if not codigo or aporte <= 0 or anos <= 0:
                erro = "Preencha todos os campos corretamente."
                return render_template('index.html', erro=erro)

            dados_analise = analisar_acao(codigo)
            if not dados_analise:
                erro = "Não foi possível obter os dados da ação. Verifique o código e tente novamente."
                return render_template('index.html', erro=erro)

            rentabilidade = calcular_rentabilidade_anual(codigo, anos)
            if rentabilidade is None:
                erro = "Erro ao calcular rentabilidade histórica."
                return render_template('index.html', erro=erro)

            dados_simulacao = simular_investimento(aporte, anos, codigo, rentabilidade)
            if not dados_simulacao:
                erro = "Erro ao simular o investimento."
                return render_template('index.html', erro=erro)

            resultado = {
                **dados_analise,
                'aporte': formatar_real(aporte),
                'anos': anos,
                'rentabilidade': dados_simulacao['rentabilidade'],
                'valor_final': dados_simulacao['valor_final'],
                'valores': dados_simulacao['valores'],
                'meses': dados_simulacao['meses'],
            }

        except Exception as e:
            erro = f"Erro inesperado: {e}"

    return render_template('index.html', resultado=resultado, erro=erro)

import os

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

