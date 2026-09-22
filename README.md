# 🏥 Painel Executivo de Equipamentos da Saúde

Um painel interativo (Dashboard) desenvolvido em **Python** e **Streamlit** para o acompanhamento gerencial e georreferenciado dos contratos e equipamentos da Secretaria de Saúde (SESAU).

## 🎯 Objetivo do Projeto
O objetivo desta aplicação é fornecer ao corpo executivo e diretores uma visão clara, dinâmica e atualizada sobre a situação dos contratos vigentes, alertando sobre prazos de vencimento e distribuição geográfica por Distrito Sanitário (DS).

## ✨ Principais Funcionalidades
- **Integração Online:** Capacidade de carregar dados dinamicamente diretamente de uma planilha do Google Sheets.
- **Métricas de Impacto (KPIs):** Visualização rápida de contratos no prazo, em alerta (vencimento <= 90 dias) e vencidos.
- **Mapa Georreferenciado:** Distribuição de equipamentos no mapa utilizando a biblioteca `folium`, com marcações coloridas baseadas na situação do prazo.
- **Filtros Dinâmicos:** Filtre facilmente os resultados por Distrito Sanitário (DS) ou Situação do Contrato.
- **Alertas Visuais:** Tabela de dados com formatação condicional inteligente para destacar onde a atenção é necessária.

## 🛠️ Tecnologias Utilizadas
- **[Python 3](https://www.python.org/):** Linguagem base.
- **[Streamlit](https://streamlit.io/):** Framework para a criação da interface web e dashboard.
- **[Pandas](https://pandas.pydata.org/):** Tratamento e manipulação dos dados.
- **[Plotly](https://plotly.com/):** Geração de gráficos interativos (barras/donut).
- **[Folium](https://python-visualization.github.io/folium/):** Renderização de mapas dinâmicos.

## 🚀 Como acessar a aplicação
A aplicação está hospedada e pode ser acessada de qualquer navegador.
👉 **[INSERIR O LINK DA APLICAÇÃO AQUI APÓS O DEPLOY]**

### Como integrar sua própria planilha do Google Sheets:
Para que o painel leia seus dados atualizados automaticamente, a planilha precisa seguir os cabeçalhos padrão (ex: `NOME DO EQUIPAMENTO`, `DS`, `SINALIZADOR DE PRAZO PARA TA`, etc) e estar publicada para a web:
1. Abra sua planilha no Google Sheets.
2. Vá em `Arquivo` > `Compartilhar` > `Publicar na Web`.
3. Selecione a aba correspondente e escolha o formato **Valores separados por vírgula (.csv)**.
4. Clique em Publicar, copie o link gerado e cole diretamente no menu lateral do aplicativo!

## 💻 Como executar o projeto localmente

Se você deseja rodar este projeto no seu próprio computador, siga os passos abaixo:

1. Clone este repositório:
   ```bash
   git clone https://github.com/SEU-USUARIO/SEU-REPOSITORIO.git
