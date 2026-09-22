import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import folium
from streamlit_folium import st_folium

# ==========================================
# Configuração da página
# ==========================================
st.set_page_config(
    page_title="Painel Executivo de Equipamentos da Saúde", 
    page_icon="🏥", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #F8FAFC; }
    .metric-card { background-color: #ffffff; border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); border-left: 5px solid #2563EB; margin-bottom: 1rem; }
    .metric-card.warning { border-left-color: #F59E0B; }
    .metric-card.danger { border-left-color: #DC2626; }
    .metric-card.success { border-left-color: #10B981; }
    .metric-title { color: #64748B; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; margin-bottom: 0.4rem; }
    .metric-value { color: #0F172A; font-size: 1.8rem; font-weight: 800; line-height: 1.2; }
</style>
""", unsafe_allow_html=True)

# Coordenadas aproximadas dos CEPs/Bairros do Recife (Evita bloqueio da API Geopy)
@st.cache_data
def geocode_cep_fast(df):
    """Mapeamento rápido de coordenadas no Recife caso as colunas LATITUDE/LONGITUDE não venham preenchidas"""
    if 'LATITUDE' in df.columns and 'LONGITUDE' in df.columns and not df['LATITUDE'].isna().all():
        return df
    
    # Se não houver lat/lon, insere coordenadas centrais da cidade
    df['LATITUDE'] = -8.0476
    df['LONGITUDE'] = -34.8770
    return df

# ==========================================
# Leitura e Tratamento dos Dados
# ==========================================
@st.cache_data(ttl=300)
def load_data(url_or_file):
    if not url_or_file: return None
    try:
        if isinstance(url_or_file, str):
            df = pd.read_csv(url_or_file, skiprows=3) # Considera os cabeçalhos das primeiras linhas
        else:
            df = pd.read_excel(url_or_file, header=3)
            
        # Limpar espaços extras do nome das colunas
        df.columns = df.columns.str.strip()
        
        # Criar Faixas de Alerta
        if 'DIAS PARA O FIM DA VIGÊNCIA' in df.columns:
            df['DIAS_NUMERICO'] = pd.to_numeric(df['DIAS PARA O FIM DA VIGÊNCIA'], errors='coerce')
            
            def classificar_faixa(dias):
                if pd.isna(dias): return "Não se aplica / Sem Informação"
                elif dias < 0: return "0. Vencido"
                elif dias <= 30: return "1. Crítico (<= 30 dias)"
                elif dias <= 60: return "2. Alerta Alto (31 a 60 dias)"
                elif dias <= 90: return "3. Alerta Médio (61 a 90 dias)"
                elif dias <= 120: return "4. Planejamento (91 a 120 dias)"
                elif dias <= 150: return "5. Planejamento (121 a 150 dias)"
                elif dias <= 180: return "6. Monitoramento (151 a 180 dias)"
                else: return "7. Regular (> 180 dias)"
            
            df['FAIXA_ALERTA'] = df['DIAS_NUMERICO'].apply(classificar_faixa)

        df = geocode_cep_fast(df)
        return df
    except Exception as e:
        # Tenta leitura direta se falhar o skiprows
        try:
            df = pd.read_csv(url_or_file) if isinstance(url_or_file, str) else pd.read_excel(url_or_file)
            df.columns = df.columns.str.strip()
            return geocode_cep_fast(df)
        except Exception as ex:
            st.error(f"Erro ao carregar a planilha: {ex}")
            return None

def generate_dummy_data():
    np.random.seed(42)
    n = 80
    dias_para_fim = np.random.randint(-50, 250, n)
    return pd.DataFrame({
        'NOME DO EQUIPAMENTO': [f'Equipamento Exemplo {i:03d}' for i in range(1, n+1)],
        'DS': np.random.choice([1, 2, 3, 4, 5, 6, 7, 8], n),
        'REGIME DE OCUPAÇÃO': np.random.choice(['LOCAÇÃO', 'PRÓPRIO', 'CESSÃO'], n),
        'DIAS PARA O FIM DA VIGÊNCIA': dias_para_fim,
        'FAIXA_ALERTA': ['0. Vencido' if d < 0 else '1. Crítico (<= 30 dias)' if d <= 30 else '7. Regular (> 180 dias)' for d in dias_para_fim],
        'LATITUDE': np.random.uniform(-8.12, -8.01, n),
        'LONGITUDE': np.random.uniform(-34.95, -34.88, n)
    })

# ==========================================
# SIDEBAR / FILTROS
# ==========================================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/Bras%C3%A3o_do_Recife.svg/1200px-Bras%C3%A3o_do_Recife.svg.png", width=90)
st.sidebar.title("Painel de Controle")

data_source = st.sidebar.radio("Fonte dos Dados:", ["Google Sheets", "Upload File", "Demonstração"])
df = None

DEFAULT_GSHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQky1KxFglGq0Iee6y3EjzqY9wdNCqNQ2I23hwcUdP6u9mO2tL45agP3UwhSJRuqCKN39gNkOl1hWos/pub?gid=1241429519&single=true&output=csv"

if data_source == "Google Sheets":
    gsheets_url = st.sidebar.text_input("URL da Planilha (CSV Publicado):", value=DEFAULT_GSHEET_URL)
    if gsheets_url: 
        df = load_data(gsheets_url)
elif data_source == "Upload File":
    uploaded_file = st.sidebar.file_uploader("Selecione o arquivo Excel ou CSV", type=["xlsx", "csv"])
    if uploaded_file: 
        df = load_data(uploaded_file)
else:
    df = generate_dummy_data()

# ==========================================
# CORPO DA APLICAÇÃO
# ==========================================
if df is not None and not df.empty:
    
    # Filtros Dinâmicos
    st.sidebar.subheader("Filtros")
    
    selected_ds = []
    if 'DS' in df.columns:
        options_ds = sorted(df['DS'].dropna().unique().astype(str))
        selected_ds = st.sidebar.multiselect("Distrito Sanitário (DS):", options=options_ds)
        
    selected_regime = []
    if 'REGIME DE OCUPAÇÃO' in df.columns:
        options_regime = sorted(df['REGIME DE OCUPAÇÃO'].dropna().unique())
        selected_regime = st.sidebar.multiselect("Regime de Ocupação:", options=options_regime)

    selected_faixa = []
    if 'FAIXA_ALERTA' in df.columns:
        options_faixa = sorted(df['FAIXA_ALERTA'].dropna().unique())
        selected_faixa = st.sidebar.multiselect("Faixa de Vencimento:", options=options_faixa)

    # Aplicação dos Filtros
    df_filtered = df.copy()
    if selected_ds and 'DS' in df_filtered.columns: 
        df_filtered = df_filtered[df_filtered['DS'].astype(str).isin(selected_ds)]
    if selected_regime and 'REGIME DE OCUPAÇÃO' in df_filtered.columns: 
        df_filtered = df_filtered[df_filtered['REGIME DE OCUPAÇÃO'].isin(selected_regime)]
    if selected_faixa and 'FAIXA_ALERTA' in df_filtered.columns: 
        df_filtered = df_filtered[df_filtered['FAIXA_ALERTA'].isin(selected_faixa)]
        
    st.title("🏥 Painel Integrado de Equipamentos da Saúde")
    st.markdown("Monitoramento de Contratos, Prazos de Vigência e Geolocalização das Unidades.")
    
    # Kpis / Métricas
    total_equip = len(df_filtered)
    vencidos, criticos, alerta = 0, 0, 0
    
    if 'FAIXA_ALERTA' in df_filtered.columns:
        vencidos = len(df_filtered[df_filtered['FAIXA_ALERTA'] == '0. Vencido'])
        criticos = len(df_filtered[df_filtered['FAIXA_ALERTA'] == '1. Crítico (<= 30 dias)'])
        alerta = len(df_filtered[df_filtered['FAIXA_ALERTA'].str.contains('Alerta', na=False)])

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="metric-card"><div class="metric-title">Total Exibido</div><div class="metric-value">{total_equip}</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-card danger"><div class="metric-title">Vencidos</div><div class="metric-value">{vencidos}</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-card warning"><div class="metric-title">Críticos (<= 30 Dias)</div><div class="metric-value">{criticos}</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="metric-card"><div class="metric-title">Em Alerta (31 a 90 Dias)</div><div class="metric-value">{alerta}</div></div>', unsafe_allow_html=True)

    # Visualizações (Mapa + Gráfico)
    col_map, col_chart = st.columns([6, 4])
    
    with col_map:
        st.subheader("📍 Mapa de Distribuição")
        
        map_df = df_filtered.dropna(subset=['LATITUDE', 'LONGITUDE']) if 'LATITUDE' in df_filtered.columns else pd.DataFrame()
        map_center = [map_df['LATITUDE'].mean(), map_df['LONGITUDE'].mean()] if not map_df.empty else [-8.0476, -34.8770]
        
        m = folium.Map(location=map_center, zoom_start=11, tiles='OpenStreetMap')
        
        if not map_df.empty:
            for idx, row in map_df.iterrows():
                faixa = str(row.get('FAIXA_ALERTA', ''))
                color = 'red' if 'Vencido' in faixa or 'Crítico' in faixa else 'orange' if 'Alerta' in faixa else 'green'
                
                nome = row.get('NOME DO EQUIPAMENTO', 'Equipamento')
                bairro = row.get('BAIRRO', '')
                
                folium.CircleMarker(
                    location=[row['LATITUDE'], row['LONGITUDE']],
                    radius=6,
                    popup=f"<b>{nome}</b><br>Bairro: {bairro}<br>Status: {faixa}",
                    color=color,
                    fill=True,
                    fill_opacity=0.7
                ).add_to(m)
                
        st_folium(m, width="100%", height=380, returned_objects=[])

    with col_chart:
        st.subheader("📊 Equipamentos por Faixa de Vencimento")
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

    # Tabela Detalhada
    st.subheader("📋 Tabela de Monitoramento")
    cols_exibir = [c for c in ['NOME DO EQUIPAMENTO', 'DS', 'REGIME DE OCUPAÇÃO', 'BAIRRO', 'CEP', 'DIAS PARA O FIM DA VIGÊNCIA', 'FAIXA_ALERTA'] if c in df_filtered.columns]
    
    if cols_exibir:
        st.dataframe(df_filtered[cols_exibir], use_container_width=True, height=350)
else:
    st.info("Aguardando carregamento da base de dados do Google Sheets...")
