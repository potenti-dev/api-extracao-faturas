import os
import re
from flask import Flask, request, jsonify
from io import BytesIO
import requests
import pandas as pd
import numpy as np
import pdfplumber
from flask_cors import CORS, cross_origin
from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar

app = Flask(__name__)

cors = CORS(app, resources={r"/api/*": {"origins": "https://127.0.0.1:5000"}})

FATURA_DICT = {
    1: "Consumo Ponta TUSD",
    2: "Consumo Fora Ponta TUSD",
    3: "Consumo Reservado TUSD",
    4: "Consumo Reativo Ponta TUSD",
    5: "Consumo Reativo Fora Ponta TUSD",
    6: "Consumo Ponta TE",
    7: "Consumo Fora Ponta TE",
    8: "Consumo Reservado TE",
    9: "Consumo Reativo Ponta TE",
    10: "Consumo Reativo Fora Ponta TE",
    11: "Demanda Reativo Fora Ponta TUSD",
    12: "Demanda Fora Ponta TUSD",
    13: "Demanda Ponta TUSD Isenta ICMS",
    14: "Demanda Fora Ponta TUSD Isenta ICMS",
    15: "Demanda Reativa Ponta",
    16: "Demanda Reativa Fora Ponta",
    17: "Demanda Ultrapassada Ponta",
    18: "Demanda Ultrapassada Fora Ponta",
    19: "Demanda Complementar",
    20: "Energia Injetada Ponta TUSD",
    21: "Energia Injetada Fora Ponta TUSD",
    22: "Energia Injetada Ponta TE",
    23: "Energia Injetada Fora Ponta TE",
    24: "Energia ACL ICSM ST Ponta",
    25: "Energia ACL ICSM ST Fora Ponta",
    26: "Subsídio Demanda Isenta TUSD"
}

# TIPOS DE FATURA
TIPO_FATURA = [('COPEL', 'Copel Distribuição'), ('CPFL', 'Cia Piratininga'), ('ENERGISA', 'ENERGISA')]
TIPO_FATURA_CELESC = [('CELESC', 'Celesc'), ('CELESC', 'CELESC')]
TIPO_FATURA_COORDENADAS = (0, 570, 595, 841)

# CELESC
CELESC_COPEL_COORDENADAS_DADOS = (0, 120, 320, 235)
CELESC_COORDENADAS_BANDEIRA_TARIFA1 = (420, 275, 590, 330)
CELESC_COORDENADAS_BANDEIRA_TARIFA2 = (143, 560, 282, 665)
CELESC_COORDENADAS_VERIFICAR_MODELO = (27,580,59,600)

# CELESC MODELO 1
CELESC1_COORDENADAS_ITEM_FATURA = (27,400,105,582)
CELESC1_COORDENADAS_QUANTIDADE = (130,400,170,582)
CELESC1_COORDENADAS_VALOR = (200,400,241,582)

# CELESC MODELO 2 E 3
CELESC2_COORDENADAS_ITEM_FATURA = (10,245,144,402)
CELESC2_COORDENADAS_QUANTIDADE = (168,245,217,402)
CELESC2_COORDENADAS_VALOR = (260,245,300,402)

CELESC3_COORDENADAS_ITEM_FATURA = (10,90,144,730)
CELESC3_COORDENADAS_QUANTIDADE = (168,90,217,730)
CELESC3_COORDENADAS_VALOR = (260,90,300,730)

# COPEL
COPEL_COORDENADAS_BANDEIRA_TARIFA = (0, 50, 595, 165)
COPEL_COORDENADAS_DIAS = (430, 100, 500, 150)
COPEL_COORDENADAS_ITEM_FATURA = (40,280,144,470)
COPEL_COORDENADAS_QUANTIDADE = (168,280,210,470)
COPEL_COORDENADAS_VALOR = (240,280,285,470)

# CPFL
CPFL_COORDENADAS_DATA = (0, 240, 595, 285)
CPFL_COORDENADAS_BANDEIRA_TARIFA = (300, 130, 420, 180)
CPFL_COORDENADAS_CONSUMO_TOTAL_IN = (300, 285, 350, 300)
CPFL_COORDENADAS_CONSUMO_TOTAL_OUT = (490, 285, 530, 300)
CPFL_COORDENADAS_ITEM_FATURA = (60,310,150,470)
CPFL_COORDENADAS_QUANTIDADE = (190,310,220,470)
CPFL_COORDENADAS_VALOR = (310,310,350,470)

# ENERGISA
ENERGISA_COORDENADAS_DATA = (0, 120, 340, 485)
ENERGISA_COORDENADAS_ITEM_FATURA = (20,370,160,550)
ENERGISA_COORDENADAS_QUANTIDADE = (190,370,225,550)
ENERGISA_COORDENADAS_VALOR = (260,370,295,550)

def converter_para_float(_value):
    if _value is None:
        return 0.0
    
    if isinstance(_value, str):
        _value = _value.replace('.', '').replace(',', '.')
    
    try:
        return float(_value)
    except (ValueError, TypeError):
        return 0.0


class APILeitorFaturas:
    def __init__(self, pdf):
        self._pdf = pdf

    @property
    def pdf(self):
        return self._pdf

    def extrair_documento(self):
        somar_itens_fatura = False
        tipo_fatura = None
        with pdfplumber.open(self._pdf) as pdf:
            pagina = pdf.pages[0]
            text = pagina.within_bbox(TIPO_FATURA_COORDENADAS).extract_text()
            if not text:
                return {'status': 400, 'message': 'Não foi possível extrair o tipo de fatura.'}
            for tipo in TIPO_FATURA:
                if tipo[1] in text:
                    tipo_fatura = tipo[0]
                    break
            for tipo in TIPO_FATURA_CELESC:
                if tipo[1] in text:
                    tipo_fatura = tipo[0]
                    break
            if not tipo_fatura:
                return {'status': 400, 'message': 'Tipo de fatura não reconhecido.'}
                
        if tipo_fatura == 'COPEL':
            result_itens_fatura = self.busca_itens_fatura('COPEL')
        if tipo_fatura == 'CPFL':
            result_itens_fatura = self.busca_itens_fatura('CPFL')
        if tipo_fatura == 'ENERGISA':
            result_itens_fatura = self.busca_itens_fatura('ENERGISA')
        if tipo_fatura == 'CELESC':
            modelo = self.busca_valor_pela_coordenada(CELESC_COORDENADAS_VERIFICAR_MODELO, 0)
            if 'LEGENDA' in modelo:
                result_itens_fatura = self.busca_itens_fatura('CELESC1')
            else:
                if len(pdf.pages) > 2:
                    somar_itens_fatura = True
                    result_itens_fatura = self.busca_itens_fatura('CELESC2_3', somar_itens_fatura)
                result_itens_fatura = self.busca_itens_fatura('CELESC2_3')

        data_values = {}
        data_values = {
            **self.get_pattern_value(tipo_fatura),
            **data_values,
            'lancamentos': result_itens_fatura['itens_fatura'],
            'encargos': result_itens_fatura['encargos'],
            'soma_total_quantidade': result_itens_fatura['soma_total_quantidade'],
            # 'soma_total_valor': result_itens_fatura['soma_total_valor']
        }

        data_values['consumo_total'] = result_itens_fatura['soma_total_valor'] if result_itens_fatura['soma_total_valor'] else data_values['consumo_total']

        print(data_values)
        return {'status': 200,
                'message': 'Dados extraídos com sucesso.',
                'data': data_values}

    def busca_valor_pela_coordenada(self, coordinates, page: int = 0, split=False):
        with pdfplumber.open(self._pdf) as pdf:
            first_page = pdf.pages[page]
            text = first_page.within_bbox(coordinates).extract_text()
            if not text:
                return None
            if split:
                text = text.split('\n')
            return text

    def busca_itens_fatura(self, tipo_fatura, somar_itens_fatura=False):
        page = 0
        if tipo_fatura == 'COPEL':
            cords_item_fatura = COPEL_COORDENADAS_ITEM_FATURA
            cords_quantidade = COPEL_COORDENADAS_QUANTIDADE
            cords_valor = COPEL_COORDENADAS_VALOR
        if tipo_fatura == 'CPFL':
            cords_item_fatura = CPFL_COORDENADAS_ITEM_FATURA
            cords_quantidade = CPFL_COORDENADAS_QUANTIDADE
            cords_valor = CPFL_COORDENADAS_VALOR
        if tipo_fatura == 'ENERGISA':
            cords_item_fatura = ENERGISA_COORDENADAS_ITEM_FATURA
            cords_quantidade = ENERGISA_COORDENADAS_QUANTIDADE
            cords_valor = ENERGISA_COORDENADAS_VALOR
        if tipo_fatura == 'CELESC1':
            cords_item_fatura = CELESC1_COORDENADAS_ITEM_FATURA
            cords_quantidade = CELESC1_COORDENADAS_QUANTIDADE
            cords_valor = CELESC1_COORDENADAS_VALOR
        if tipo_fatura == 'CELESC2_3':
            cords_item_fatura = CELESC2_COORDENADAS_ITEM_FATURA
            cords_quantidade = CELESC2_COORDENADAS_QUANTIDADE
            cords_valor = CELESC2_COORDENADAS_VALOR
        
        lista_item_fatura = self.busca_valor_pela_coordenada(cords_item_fatura, page, split=True)
        lista_quantidade = self.busca_valor_pela_coordenada(cords_quantidade, page, split=True)
        lista_valor = self.busca_valor_pela_coordenada(cords_valor, page, split=True)

        if somar_itens_fatura:
            page = 1
            somar_item_fatura = self.busca_valor_pela_coordenada(CELESC3_COORDENADAS_ITEM_FATURA, page, split=True)
            somar_quantidade = self.busca_valor_pela_coordenada(CELESC3_COORDENADAS_QUANTIDADE, page, split=True)
            somar_valor = self.busca_valor_pela_coordenada(CELESC3_COORDENADAS_VALOR, page, split=True)
            lista_item_fatura = lista_item_fatura + somar_item_fatura
            lista_quantidade = lista_quantidade + somar_quantidade
            lista_valor = lista_valor + somar_valor


        if tipo_fatura == 'CELESC1' or tipo_fatura == 'CELESC2_3':
            lista_item_fatura = [item[5:] if item.startswith('(') else item for item in lista_item_fatura]
            lista_item_fatura = self.renomear_lista_celesc(lista_item_fatura)

        if tipo_fatura == 'COPEL':
            lista_item_fatura = self.renomear_lista_copel(lista_item_fatura)
        
        if tipo_fatura == 'CPFL':
            lista_item_fatura = self.renomear_lista_cpfl(lista_item_fatura)

        if tipo_fatura == 'ENERGISA':
            lista_item_fatura = self.renomear_lista_energisa(lista_item_fatura)

        max_length = max(len(lista_item_fatura), len(lista_quantidade), len(lista_valor))
        lista_item_fatura += [None] * (max_length - len(lista_item_fatura))
        lista_quantidade += [None] * (max_length - len(lista_quantidade))
        lista_valor += [None] * (max_length - len(lista_valor))

        df = pd.DataFrame({
            'item_fatura': lista_item_fatura,
            'quantidade': lista_quantidade,
            'valor': lista_valor
        })

        df['quantidade'] = df['quantidade'].apply(converter_para_float)
        df['valor'] = df['valor'].apply(converter_para_float)
        df = df[~((df['quantidade'].isna()) & (df['valor'].isna()))]
        df['quantidade'] = df['quantidade'].replace('.', '', regex=True).replace(',', '.', regex=True)
        df = df.groupby('item_fatura').agg({
            'quantidade': 'sum',
            'valor': 'sum'
        }).reset_index()
        soma_total_quantidade = df['quantidade'].sum()
        total_keywords = ['TOTAL', 'Total a Pagar', 'Total']
        soma_total_valor = df.loc[
            (df['item_fatura'].isin(total_keywords)) | (df['quantidade'].isin(total_keywords)),
            'valor'
        ]
        soma_total_valor = soma_total_valor.values[0] if not soma_total_valor.empty else None

        result_json = self.transforma_em_json(df)

        return {
            'itens_fatura' : result_json['itens_fatura'],
            'encargos' : result_json['encargos'],
            'soma_total_quantidade': soma_total_quantidade,
            'soma_total_valor': soma_total_valor
        }

    def get_pattern_value(self, tipo_fatura):
        dados_dicionario = {}
        dados_texto = ''
        consumo_total = None
        tipo_bandeira = None
        dias_bandeira = None
        padrao_bandeira_celesc = re.compile(r'(Bandeira)\s+(.*?)\s+(\d{1,2})')
        padrao_bandeira_copel = re.compile(r'TARIFA HORARIA\s+(\S+)')
        padrao_bandeira_cpfl = re.compile(r'(\S+)')
        padrao_dias_bandeira_cpfl = re.compile(r'(\d+)\s+Dias')

        try:
            if tipo_fatura == 'CELESC' or tipo_fatura == 'COPEL':
                dados_texto = self.busca_valor_pela_coordenada(CELESC_COPEL_COORDENADAS_DADOS, 0)

            if tipo_fatura == 'CPFL':
                dados_texto = self.busca_valor_pela_coordenada(CPFL_COORDENADAS_DATA, 0)
                consumo_total_in = self.busca_valor_pela_coordenada(CPFL_COORDENADAS_CONSUMO_TOTAL_IN, 1)
                consumo_total_out = self.busca_valor_pela_coordenada(CPFL_COORDENADAS_CONSUMO_TOTAL_OUT, 1)
                if consumo_total_in and consumo_total_out:
                    consumo_total = float(consumo_total_in.replace('.', '').replace(',', '.')) + float(consumo_total_out.replace('.', '').replace(',', '.')) 
                text_bandeira = self.busca_valor_pela_coordenada(CPFL_COORDENADAS_BANDEIRA_TARIFA, 1)
                bandeira = padrao_bandeira_cpfl.findall(text_bandeira)
                dias_bandeira = padrao_dias_bandeira_cpfl.findall(text_bandeira)
                if bandeira:
                    tipo_bandeira = bandeira[0]
                else:
                    tipo_bandeira = None
                if dias_bandeira:
                    dias_bandeira = dias_bandeira[0]
                else:
                    dias_bandeira = None

            if tipo_fatura == 'COPEL':
                dias_bandeira = self.busca_valor_pela_coordenada(COPEL_COORDENADAS_DIAS, 0)
                text_with_bandeira = self.busca_valor_pela_coordenada(COPEL_COORDENADAS_BANDEIRA_TARIFA, 2)
                bandeira = padrao_bandeira_copel.findall(text_with_bandeira)
                dados_texto += text_with_bandeira
                if bandeira:
                    tipo_bandeira = bandeira[0]
                else:
                    tipo_bandeira = None

            if tipo_fatura == 'CELESC':
                text_bandeira = self.busca_valor_pela_coordenada(CELESC_COORDENADAS_BANDEIRA_TARIFA1, 0)
                bandeira = padrao_bandeira_celesc.findall(text_bandeira)
                if not bandeira:
                    text_bandeira = self.busca_valor_pela_coordenada(CELESC_COORDENADAS_BANDEIRA_TARIFA2, 0)
                    bandeira = padrao_bandeira_celesc.findall(text_bandeira)
                dias_bandeira = None
                if len(bandeira) == 1 and len(bandeira[0]) == 3:
                    _, tipo_bandeira, dias_bandeira = bandeira[0]
                else:
                    try:
                        tipo_bandeira = bandeira[0][1]
                    except:
                        tipo_bandeira = None

            if tipo_fatura == 'ENERGISA':
                dados_texto = self.busca_valor_pela_coordenada(ENERGISA_COORDENADAS_DATA, 0)
                padrao_bandeira_energisa = re.compile(r'TARIF[ÁA]RIA\s+(\w+)')
                bandeira = padrao_bandeira_energisa.findall(dados_texto)
                if bandeira == 1:
                    tipo_bandeira = bandeira[0]
                else:
                    try:
                        tipo_bandeira = bandeira[0]
                    except:
                        tipo_bandeira = None

        except:
            dados_texto = ''

        if(tipo_fatura == "ENERGISA"):
            padrao_numero_unidade = re.compile(r'\b[A-Za-z]\d{10}\b')
            padrao_consumo_total = re.compile(r'\bKWH\s([\d,.]+)\b')

        else:
            padrao_numero_unidade = re.compile(r'\b\d{8,9}\b')
            padrao_consumo_total = re.compile(r'\b(\d+\s?kWh)\b')

        padrao_referencia = re.compile(r'\b(\d{2}/\d{4})\b')
        padrao_vencimento = re.compile(r'\b(\d{2}/\d{2}/\d{4})\b')
        padrao_valor_vencimento = re.compile(r'(?:R\$ ?)?([\d.]+,\d{2})')

        if(tipo_fatura == "ENERGISA" or tipo_fatura == "CPFL"):
            date = padrao_referencia.findall(dados_texto)
            date_format = "%m/%Y"
            date_obj = datetime.strptime(date[0], date_format)
            new_date_obj = date_obj - relativedelta(months=1)
            new_date_str = new_date_obj.strftime(date_format)
            matches_referencia = [new_date_str]

            if dias_bandeira == None:
                year = new_date_obj.year
                month = new_date_obj.month
                num_days = calendar.monthrange(year, month)[1]
                dias_bandeira = num_days

        else:
            matches_referencia = padrao_referencia.findall(dados_texto)

        matches_numero_unidade = padrao_numero_unidade.findall(dados_texto)
        matches_vencimento = padrao_vencimento.findall(dados_texto)
        matches_consumo_total = padrao_consumo_total.findall(dados_texto)
        matches_valor_vencimento = padrao_valor_vencimento.findall(dados_texto)

        if(tipo_fatura == "ENERGISA"):
            try:
                def converter_para_float(s):
                    s = s.replace('.', '').replace(',', '.')
                    return float(s)
                soma_total = sum(converter_para_float(numero) for numero in matches_consumo_total)
                matches_consumo_total = [soma_total]
            except ValueError as e:
                matches_consumo_total = []

        dados_dicionario["referencia"] = matches_referencia[0] if matches_referencia else None
        dados_dicionario["unidade_consumidora"] = matches_numero_unidade[0] if matches_numero_unidade else None
        dados_dicionario["vencimento"] = matches_vencimento[1] if len(matches_vencimento) >= 2 else matches_vencimento[
            0] if matches_vencimento else None
        dados_dicionario["consumo_total"] = matches_consumo_total[0] if matches_consumo_total else consumo_total
        dados_dicionario["valor_fatura"] = float(matches_valor_vencimento[0].replace('.', '').replace(',', '.')) if matches_valor_vencimento else None
        dados_dicionario["bandeira"] = tipo_bandeira
        dados_dicionario["dias_bandeira"] = dias_bandeira
        return dados_dicionario

    def renomear_lista_copel(self, list):
        lista_renomeada = [
            FATURA_DICT[6] if item == 'TE CDE COVID PONTA' else
            FATURA_DICT[7] if item == 'TE CDE COVID FORA PONTA' else
            FATURA_DICT[9] if item == 'ENERGIA REAT EXCED TE PONTA' else
            FATURA_DICT[10] if item == 'ENERGIA REAT EXCED TE F PONTA' else
            FATURA_DICT[12] if item == 'DEMANDA DE DISTRIBUICAO TUSD' else
            FATURA_DICT[11] if item == 'DEMANDA REATIVA EXCED USD' else
            FATURA_DICT[24] if item == 'ENERGIA ELETRICA ACL-COM ICMS ST' else
            FATURA_DICT[25] if item == 'ENERGIA ELETRICA ACL-COM ICMS ST' else
            item
            for item in list
        ]
        return lista_renomeada

    def renomear_lista_cpfl(self, list):
        lista_renomeada = [
            FATURA_DICT[9] if item == 'Consumo Reativo Exc Ponta' else
            FATURA_DICT[10] if item == 'Consumo Reativo Exc Fora Ponta' else
            FATURA_DICT[12] if item == 'Demanda' else
            FATURA_DICT[14] if item == 'Demanda' else
            item
            for item in list
        ]
        return lista_renomeada
    
    def renomear_lista_energisa(self, list):
        lista_renomeada = [
            FATURA_DICT[6] if item == 'Consumo em kWh - Ponta' else
            FATURA_DICT[7] if item == 'Consumo em kWh - Fora Ponta' else
            FATURA_DICT[23] if item == 'Energia Atv Injetada - Fora Ponta' else
            FATURA_DICT[10] if item == 'Energia Reativa Exced em KWh - Fponta' else
            FATURA_DICT[12] if item == 'Demanda de Potência Medida - Fora Ponta' else
            FATURA_DICT[18] if item == 'Demanda de Potência Ativa - Ultrap - F Ponta' else
            item
            for item in list
        ]
        return lista_renomeada

    def renomear_lista_celesc(self, list):
        lista_renomeada = [
            FATURA_DICT[1] if item == 'Consumo Ponta TUSD' else
            FATURA_DICT[2] if item == 'Consumo Fora Ponta TUSD' else
            FATURA_DICT[6] if item == 'Consumo Ponta TE' else
            FATURA_DICT[7] if item == 'Consumo Fora Ponta TE' else
            FATURA_DICT[10] if item == 'Energia Reativa Excedente' else
            FATURA_DICT[12] if item == 'Demanda' else
            FATURA_DICT[16] if item == 'Demanda Reativa' else
            item
            for item in list
        ]
        return lista_renomeada
        
    def transforma_em_json(self, df):
        df['categoria'] = df['item_fatura'].apply(lambda x: 'itens de fatura' if x in FATURA_DICT.values() else 'encargos')
        df['encargo_valido'] = df.apply(
            lambda row: (
                row['categoria'] == 'encargos' and 
                pd.notnull(row['quantidade']) and 
                pd.notnull(row['valor']) and 
                row['item_fatura'] not in ['SUBTOTAL', 'TOTAL']
            ), axis=1
        )
        itens_fatura = df[df['categoria'] == 'itens de fatura'][['item_fatura', 'quantidade', 'valor']]
        encargos = df[df['encargo_valido'] == True][['item_fatura', 'quantidade', 'valor']]
        itens_fatura_list = itens_fatura.to_dict(orient='records')
        encargos_list = encargos.to_dict(orient='records')
        
        return {
            'itens_fatura': itens_fatura_list,
            'encargos': encargos_list
        }



@app.route('/api/extract', methods=['GET'])
@cross_origin(origin='*', methods=['GET', 'POST'], allow_headers=['Content-Type'])
def extrair_pdf():
    if request.method == 'GET':
        pdf_url = request.args.get('url')
        if not pdf_url:
            return jsonify({'status': 400, 'message': 'Nenhum arquivo foi seledcionado'})
        result = examina_pdf(pdf_url)
        return jsonify(result)


def examina_pdf(pdf_url):
    conteudo_pdf = requests.get(pdf_url)
    conteudo_pdf.raise_for_status()
    conteudo_pdf = BytesIO(conteudo_pdf.content)
    result_api = APILeitorFaturas(conteudo_pdf).extrair_documento()
    if result_api['status'] == 400:
        return result_api
    return result_api


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)

# caminho_faturas = os.path.join(os.getcwd(), 'jupyter', 'Faturas')
# os.listdir(caminho_faturas)
# lista_caminhos_pdfs = [os.path.join(caminho_faturas,arq) for arq in os.listdir(caminho_faturas) if arq.endswith('.pdf')]
# for index, item in enumerate(lista_caminhos_pdfs):
#     print(f'{index} - {item}') 
#     result_api = APILeitorFaturas(item).extract_document()
