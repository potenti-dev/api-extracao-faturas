# API de Extração de Dados de Faturas

Este projeto consiste em uma API desenvolvida em Python usando Flask para extrair dados de faturas em PDF de diversas empresas de fornecimento de energia. A API utiliza a biblioteca `pdfplumber` para a extração de texto a partir de PDFs e está configurada para reconhecer e processar faturas de diferentes modelos, incluindo COPEL, CPFL, ENERGISA e CELESC.

## Funcionalidades

- **Extração de dados estruturados** de faturas de PDF, incluindo itens, quantidades e valores.
- **Compatibilidade com múltiplos fornecedores**: COPEL, CPFL, ENERGISA e CELESC.
- **Transformação dos dados extraídos** em um formato JSON para fácil manipulação.
- **Identificação e extração de informações adicionais**, como referência de vencimento, consumo total, bandeiras tarifárias e encargos.

## Tecnologias Utilizadas

- **Flask**: Framework web para construção da API.
- **pdfplumber**: Biblioteca para extração de texto e dados de arquivos PDF.
- **Pandas**: Manipulação e análise de dados.
- **NumPy**: Operações numéricas de suporte.
- **Flask-CORS**: Gerenciamento de políticas de CORS para permitir o acesso da API por outras origens.

## Estrutura do Projeto

- **`app.py`**: Arquivo principal que define a API e a lógica de extração.
- **Classes e Métodos**:
  - `APILeitorFaturas`: Classe principal para a manipulação e extração de dados dos PDFs.
  - `extrair_documento()`: Método para extração de dados a partir do PDF.
  - `busca_valor_pela_coordenada()`, `busca_itens_fatura()`: Métodos auxiliares para localizar e processar seções específicas do PDF.
  - `get_pattern_value()`: Extração de padrões como datas e valores.
  - `transforma_em_json()`: Conversão dos dados extraídos para JSON.

## Como Executar o Projeto

### Pré-requisitos

- Python 3.8 ou superior.
- Bibliotecas listadas em `requirements.txt`.

### Instalação

1. **Clone o repositório**:
   ```bash
   git clone https://github.com/dev-potenti/api-leitor-faturas.git
   cd api-leitor-faturas
   pip install -r requirements.txt
   python app.py
   ```

2. **Exemplo de requisição**:
GET http://127.0.0.1:8080/api/extract?url=https://exemplo.com/fatura.pdf

3. **Exemplo de resposta**:
   ```json
   {
  "status": 200,
  "message": "Dados extraídos com sucesso.",
  "data": {
    "referencia": "08/2023",
    "unidade_consumidora": "123456789",
    "vencimento": "15/09/2023",
    "consumo_total": 450.75,
    "valor_fatura": 1234.56,
    "bandeira": "Amarela",
    "dias_bandeira": 30,
    "lancamentos": [
      {
        "item_fatura": "Consumo Ponta TUSD",
        "quantidade": 100.0,
        "valor": 300.0
      },
      ...
    ],
    "encargos": [
      {
        "item_fatura": "Encargo X",
        "quantidade": 1.0,
        "valor": 50.0
      }
    ]
  }
}
```






