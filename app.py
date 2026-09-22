import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import folium
from streamlit_folium import st_folium
import random

# ==========================================
# Configuração da Página
# ==========================================
st.set_page_config(
    page_title="Painel Executivo - Equipamentos da Saúde", 
    page_icon="🏥", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Estilização CSS para Cartões de Indicadores e Layout
st.markdown("""
<style>
    .stApp { background-color: #F8FAFC; }
    .metric-card { 
        background-color: #ffffff; 
        border-radius: 10px; 
        padding: 16px 20px; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); 
        border-left: 4px solid #2563EB; 
        margin-bottom: 0.8rem; 
    }
    .metric-card.warning { border-left-color: #F59E0B; }
    .metric-card.danger { border-left-color: #DC2626; }
    .metric-card.value-card { border-left-color: #059669; }
    .metric-title { color: #64748B; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; margin-bottom: 0.3rem; }
    .metric-value { color: #0F172A; font-size: 1.6rem; font-weight: 800; line-height: 1.2; }
</style>
""", unsafe_allow_html=True)

# URL fixa da planilha pública do Google Sheets
GSHEETS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQky1KxFglGq0Iee6y3EjzqY9wdNCqNQ2I23hwcUdP6u9mO2tL45agP3UwhSJRuqCKN39gNkOl1hWos/pub?gid=1241429519&single=true&output=csv"

# ==========================================
# Coordenadas por Bairro do Recife (Geocodificação Rápida)
# ==========================================
COORDENADAS_BAIRROS = {
    'CASA AMARELA': (-8.0264, -34.9189),
    'CAXANGÁ': (-8.0431, -34.9382),
    'GUABIRABA': (-7.9942, -34.9315),
    'BOA VISTA': (-8.0581, -34.8892),
    'ENCRUZILHADA': (-8.0389, -34.8965),
    'IPSEP': (-8.1189, -34.9192),
    'PRADO': (-8.0622, -34.9081),
    'PEIXINHOS': (-8.0165, -34.8722),
    'SANTO AMARO': (-8.0489, -34.8825),
    'AFOGADOS': (-8.0731, -34.9056),
    'BOA VIAGEM': (-8.1250, -34.9015),
    'VARZEA': (-8.0355, -34.9652),
    'VÁRZEA': (-8.0355, -34.9652),
    'IBURA': (-8.1125, -34.9389),
    'IMBIRIBEIRA': (-8.1002, -34.9065),
    'CORDEIRO': (-8.0520, -34.9220),
    'TORRE': (-8.0425, -34.9088),
    'MADALENA': (-8.0551, -34.9072),
    'GRAÇAS': (-8.0438, -34.8972),
    'ESPINHEIRO': (-8.0385, -34.8912),
    'ARRUDA': (-8.0210, -34.8890),
    'ÁGUA FRIA': (-8.0205, -34.8955),
    'AGUA FRIA': (-8.0205, -34.8955),
    'SAN MARTIN': (-8.0705, -34.9250),
    'TEJIPIÓ': (-8.0850, -34.9520),
    'AREIAS': (-8.0889, -34.9275),
    'BARRO': (-8.0865, -34.9450),
    'COHAB': (-8.1280, -34.9480),
    'PINA': (-8.0880, -34.8850),
    'SANTO ANTÔNIO': (-8.0640, -34.8770),
    'RECIFE': (-8.0620, -34.8710),
    'SÃO JOSÉ': (-8.0680, -34.8800),
}

def mapear_coordenadas(row):
    """Atribui Latitude e Longitude válidas com dispersão para não empilhar os pontos"""
    lat = pd.to_numeric(row.get('LATITUDE'), errors='coerce')
    lon = pd.to_numeric(row.get('LONGITUDE'), errors='coerce')
    
    if pd.notna(lat) and pd.notna(lon) and lat != 0:
        return pd.Series([lat, lon])
        
    bairro = str(row.get('BAIRRO', '')).strip().upper()
    if bairro in COORDENADAS_BAIRROS:
        c_lat, c_lon = COORDENADAS_BAIRROS[bairro]
        return pd.Series([c_lat + random.uniform(-0.003, 0.003), c_lon + random.uniform(-0.003, 0.003)])
        
    return pd.Series([-8.0476 + random.uniform(-0.02, 0.02), -34.8770 + random.uniform(-0.02, 0.02)])

# ==========================================
# Funções Financeiras
# ==========================================
def formatar_moeda(valor):
    """Formata valores no padrão R$ 898,03 Mil / R$ 22,30 Mi"""
    if pd.isna(valor) or valor == 0:
        return "R$ 0,00"
    
    if valor >= 1_000_000:
        val_mi = valor / 1_000_000
        return f"R$ {val_mi:,.2f} Mi".replace(",", "X").replace(".", ",").replace("X", ".")
    elif valor >= 1_000:
        val_mil = valor / 1_000
        return f"R$ {val_mil:,.2f} Mil".replace(",", "X").replace(".", ",").replace("X", ".")
    else:
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ==========================================
# Leitura e Carga dos Dados
# ==========================================
@st.cache_data(ttl=300)
def load_data(url):
    try:
        df = pd.read_csv(url, skiprows=3)
        df.columns = df.columns.str.strip()
        
        # Ajustar coluna do Responsável
        if 'RESPONSÁVEL' not in df.columns and 'RESPONSAVEL' in df.columns:
            df.rename(columns={'RESPONSAVEL': 'RESPONSÁVEL'}, inplace=True)
            
        # Tratar Valor Mensal
        col_valor_mensal = [c for c in df.columns if 'VALOR MENSAL' in c.upper()]
        if col_valor_mensal:
            df['VALOR_MENSAL_NUM'] = df[col_valor_mensal[0]].astype(str)
            df['VALOR_MENSAL_NUM'] = df['VALOR_MENSAL_NUM'].str.replace('R$', '', regex=False)
            df['VALOR_MENSAL_NUM'] = df['VALOR_MENSAL_NUM'].str.replace('.', '', regex=False)
            df['VALOR_MENSAL_NUM'] = df['VALOR_MENSAL_NUM'].str.replace(',', '.', regex=False)
            df['VALOR_MENSAL_NUM'] = pd.to_numeric(df['VALOR_MENSAL_NUM'], errors='coerce').fillna(0)
        else:
            df['VALOR_MENSAL_NUM'] = 0.0

        # Classificação por Faixas de Vencimento
        if 'DIAS PARA O FIM DA VIGÊNCIA' in df.columns:
            df['DIAS_NUMERICO'] = pd.to_numeric(df['DIAS PARA O FIM DA VIGÊNCIA'], errors='coerce')
            
            def classificar_faixa(dias):
                if pd.isna(dias): return "Não se aplica / Sem Info"
                elif dias < 0: return "0. Vencido"
                elif dias <= 30: return "1. Crítico (<= 30 dias)"
                elif dias <= 60: return "2. Alerta (31 a 60 dias)"
                elif dias <= 90: return "3. Alerta (61 a 90 dias)"
                elif dias <= 120: return "4. Planejamento (91 a 120 dias)"
                elif dias <= 150: return "5. Planejamento (121 a 150 dias)"
                elif dias <= 180: return "6. Monitoramento (151 a 180 dias)"
                else: return "7. Regular (> 180 dias)"
            
            df['FAIXA_ALERTA'] = df['DIAS_NUMERICO'].apply(classificar_faixa)

        # Mapeamento Geográfico
        df[['LATITUDE', 'LONGITUDE']] = df.apply(mapear_coordenadas, axis=1)
            
        return df
    except Exception as e:
        st.error(f"Erro ao carregar os dados: {e}")
        return pd.DataFrame()

df = load_data(GSHEETS_URL)

# ==========================================
# SIDEBAR / PAINEL APENAS DE FILTROS
# ==========================================
st.sidebar.markdown("<h2 style='text-align: center; letter-spacing: 2px;'>FILTROS</h2>", unsafe_allow_html=True)
st.sidebar.markdown("---")

df_filtered = df.copy()

if not df.empty:
    # 1. Filtro de Responsável
    if 'RESPONSÁVEL' in df.columns:
        opcoes_resp = sorted([str(r) for r in df['RESPONSÁVEL'].dropna().unique() if str(r).strip() != ''])
        selected_resp = st.sidebar.multiselect("RESPONSÁVEL", options=opcoes_resp)
        if selected_resp:
            df_filtered = df_filtered[df_filtered['RESPONSÁVEL'].astype(str).isin(selected_resp)]

    # 2. Filtro de Distrito Sanitário (DS)
    if 'DS' in df.columns:
        opcoes_ds = sorted([str(d) for d in df['DS'].dropna().unique() if str(d).strip() != ''])
        selected_ds = st.sidebar.multiselect("DISTRITO SANITÁRIO (DS)", options=opcoes_ds)
        if selected_ds:
            df_filtered = df_filtered[df_filtered['DS'].astype(str).isin(selected_ds)]

    # 3. Filtro de Regime de Ocupação
    if 'REGIME DE OCUPAÇÃO' in df.columns:
        opcoes_regime = sorted([str(r) for r in df['REGIME DE OCUPAÇÃO'].dropna().unique() if str(r).strip() != ''])
        selected_regime = st.sidebar.multiselect("REGIME DE OCUPAÇÃO", options=opcoes_regime)
        if selected_regime:
            df_filtered = df_filtered[df_filtered['REGIME DE OCUPAÇÃO'].astype(str).isin(selected_regime)]

    # 4. Filtro por Faixa de Vencimento
    if 'FAIXA_ALERTA' in df.columns:
        opcoes_faixa = sorted(df['FAIXA_ALERTA'].dropna().unique())
        selected_faixa = st.sidebar.multiselect("FAIXA DE VENCIMENTO", options=opcoes_faixa)
        if selected_faixa:
            df_filtered = df_filtered[df_filtered['FAIXA_ALERTA'].isin(selected_faixa)]

# ==========================================
# CORPO DA APLICAÇÃO
# ==========================================
st.title("🏥 Painel dos Equipamentos da Saúde")

if df_filtered is not None and not df_filtered.empty:
    
    # Cálculos de Métricas
    total_equip = len(df_filtered)
    vencidos = len(df_filtered[df_filtered['FAIXA_ALERTA'] == '0. Vencido']) if 'FAIXA_ALERTA' in df_filtered.columns else 0
    criticos = len(df_filtered[df_filtered['FAIXA_ALERTA'] == '1. Crítico (<= 30 dias)']) if 'FAIXA_ALERTA' in df_filtered.columns else 0
    
    valor_mensal_total = df_filtered['VALOR_MENSAL_NUM'].sum()
    valor_anual_total = valor_mensal_total * 12
    
    # ------------------------------------------
    # Cartões de Indicadores
    # ------------------------------------------
    c1, c2, c3, c4, c5 = st.columns(5)
    
    with c1:
        st.markdown(f'''
            <div class="metric-card value-card">
                <div class="metric-title">Valor Mensal</div>
                <div class="metric-value">{formatar_moeda(valor_mensal_total)}</div>
            </div>
        ''', unsafe_allow_html=True)

    with c2:
        st.markdown(f'''
            <div class="metric-card value-card">
                <div class="metric-title">Valor Anual</div>
                <div class="metric-value">{formatar_moeda(valor_anual_total)}</div>
            </div>
        ''', unsafe_allow_html=True)

    with c3:
        st.markdown(f'''
            <div class="metric-card">
                <div class="metric-title">Total Imóveis</div>
                <div class="metric-value">{total_equip}</div>
            </div>
        ''', unsafe_allow_html=True)

    with c4:
        st.markdown(f'''
            <div class="metric-card warning">
                <div class="metric-title"><= 30 Dias</div>
                <div class="metric-value">{criticos}</div>
            </div>
        ''', unsafe_allow_html=True)

    with c5:
        st.markdown(f'''
            <div class="metric-card danger">
                <div class="metric-title">Vencidos</div>
                <div class="metric-value">{vencidos}</div>
            </div>
        ''', unsafe_allow_html=True)

    st.markdown("---")

    # ------------------------------------------
    # Visualizações (Mapa + Gráfico)
    # ------------------------------------------
    col_map, col_chart = st.columns([6, 4])
    
    with col_map:
        st.subheader("📍 Mapa por Unidade e Bairro")
        map_df = df_filtered.dropna(subset=['LATITUDE', 'LONGITUDE'])
        map_center = [map_df['LATITUDE'].mean(), map_df['LONGITUDE'].mean()] if not map_df.empty else [-8.0476, -34.8770]
        
        m = folium.Map(location=map_center, zoom_start=11, tiles='OpenStreetMap')
        
        for idx, row in map_df.iterrows():
            faixa = str(row.get('FAIXA_ALERTA', ''))
            color = 'red' if 'Vencido' in faixa or 'Crítico' in faixa else 'orange' if 'Alerta' in faixa else 'green'
            
            nome = row.get('NOME DO EQUIPAMENTO', 'Equipamento')
            bairro = row.get('BAIRRO', '')
            val_m = formatar_moeda(row.get('VALOR_MENSAL_NUM', 0))
            
            folium.CircleMarker(
                location=[row['LATITUDE'], row['LONGITUDE']],
                radius=6,
                popup=f"<b>{nome}</b><br>Bairro: {bairro}<br>Valor Mensal: {val_m}",
                color=color,
                fill=True,
                fill_opacity=0.7
            ).add_to(m)
                
        st_folium(m, width="100%", height=380, returned_objects=[])

    with col_chart:
        st.subheader("📊 Distribuição por Faixa de Vencimento")
        if 'FAIXA_ALERTA' in df_filtered.columns:
            faixa_counts = df_filtered['FAIXA_ALERTA'].value_counts().reset_index()
            faixa_counts.columns = ['Faixa', 'Quantidade']
            faixa_counts = faixa_counts.sort_values(by='Faixa')
            
            fig = px.bar(
                faixa_counts, 
                x='Quantidade', 
                y='Faixa', 
                orientation='h', 
                color='Faixa',
                color_discrete_sequence=px.colors.qualitative.Set1
            )
            fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=0), height=380)
            st.plotly_chart(fig, use_container_width=True)

    # ------------------------------------------
    # Tabela Detalhada
    # ------------------------------------------
    st.subheader("📋 Tabela de Monitoramento")
    cols_exibir = [c for c in ['RESPONSÁVEL', 'NOME DO EQUIPAMENTO', 'DS', 'REGIME DE OCUPAÇÃO', 'BAIRRO', 'VALOR_MENSAL_NUM', 'DIAS PARA O FIM DA VIGÊNCIA', 'FAIXA_ALERTA'] if c in df_filtered.columns]
    
    if cols_exibir:
        st.dataframe(df_filtered[cols_exibir], use_container_width=True, height=350)
else:
    st.info("Nenhum dado encontrado para os filtros selecionados.")
