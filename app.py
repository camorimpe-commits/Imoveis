import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

# ==================
# Configuração da página
# ==================
st.set_page_config(page_title="Painel Executivo", page_icon="🏥", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .stApp { background-color: #F8FAFC; }
    .metric-card { background-color: #ffffff; border-radius: 12px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); border-left: 5px solid #2563EB; margin-bottom: 1rem; }
    .metric-card.warning { border-left-color: #F59E0B; }
    .metric-card.danger { border-left-color: #DC2626; }
    .metric-card.success { border-left-color: #10B981; }
    .metric-title { color: #64748B; font-size: 0.9rem; font-weight: 600; text-transform: uppercase; margin-bottom: 0.5rem; }
    .metric-value { color: #0F172A; font-size: 2rem; font-weight: 800; line-height: 1.2; }
</style>
""", unsafe_allow_html=True)

# ==================
# Lógica de Geocodificação (CEP para Lat/Lon)
# ==================
@st.cache_data(show_spinner=False)
def get_coordinates_from_cep(df):
    """Transforma CEPs em Latitude e Longitude usando Geopy"""
    # Se a planilha já tiver as colunas LATITUDE e LONGITUDE preenchidas, pula essa etapa
    if 'LATITUDE' in df.columns and 'LONGITUDE' in df.columns and not df['LATITUDE'].isna().all():
        return df
        
    if 'CEP' in df.columns:
        st.sidebar.info("🌐 Convertendo CEPs em coordenadas no mapa. Isso pode demorar alguns segundos na primeira vez...")
        
        # Inicia o serviço gratuito de mapas do OpenStreetMap
        geolocator = Nominatim(user_agent="painel_saude_recife_app")
        # Rate Limiter para não bloquear a API gratuita (1 pedido por segundo)
        geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
        
        # Cria uma coluna com a busca (Ex: "50000-000, Brasil")
        df['busca_geo'] = df['CEP'].astype(str) + ", Brasil"
        
        # Aplica a busca
        df['location'] = df['busca_geo'].apply(geocode)
        df['LATITUDE'] = df['location'].apply(lambda loc: loc.latitude if loc else np.nan)
        df['LONGITUDE'] = df['location'].apply(lambda loc: loc.longitude if loc else np.nan)
        
    return df

# ==================
# Leitura de Dados
# ==================
@st.cache_data(ttl=600)
def load_data(url_or_file):
    if not url_or_file: return None
    try:
        if isinstance(url_or_file, str) and "output=csv" in url_or_file:
            df = pd.read_csv(url_or_file)
        else:
            df = pd.read_excel(url_or_file)
            
        # Processar CEPs para gerar o mapa
        df = get_coordinates_from_cep(df)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar: {e}")
        return None

def generate_dummy_data():
    np.random.seed(42)
    n = 120
    dias_para_fim = np.random.randint(-150, 600, n)
    sinalizador, situacao = [], []
    for dias in dias_para_fim:
        if dias < 0: sinalizador.append('VENCIDO'); situacao.append('ENCERRADO')
        elif dias <= 90: sinalizador.append('ALERTA VENCIMENTO PRÓXIMO'); situacao.append('VIGENTE')
        else: sinalizador.append('VIGENTE - NO PRAZO'); situacao.append('VIGENTE')
    return pd.DataFrame({
        'NOME DO EQUIPAMENTO': [f'Equipamento {i:03d}' for i in range(1, n+1)],
        'DS': np.random.choice(['DS I', 'DS II', 'DS III', 'DS IV'], n),
        'INÍCIO DA VIGÊNCIA': pd.date_range(start='2020-01-01', periods=n, freq='15D').strftime('%d/%m/%Y'),
        'TÉRMINO DA VIGÊNCIA': pd.date_range(start='2024-01-01', periods=n, freq='15D').strftime('%d/%m/%Y'),
        'DIAS PARA O FIM DA VIGÊNCIA': dias_para_fim,
        'SINALIZADOR DE PRAZO PARA TA': sinalizador,
        'SITUAÇÃO DO CONTRATO/TA': situacao,
        'LATITUDE': np.random.uniform(-8.15, -7.95, n),
        'LONGITUDE': np.random.uniform(-34.95, -34.85, n)
    })

# ==================
# SIDEBAR
# ==================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/Bras%C3%A3o_do_Recife.svg/1200px-Bras%C3%A3o_do_Recife.svg.png", width=100)
st.sidebar.title("Configurações do Painel")
data_source = st.sidebar.radio("Fonte dos Dados:", ["Demonstração", "Google Sheets", "Upload"])
df = None

if data_source == "Google Sheets":
    gsheets_url = st.sidebar.text_input("Link CSV:")
    if gsheets_url: df = load_data(gsheets_url)
elif data_source == "Upload":
    uploaded_file = st.sidebar.file_uploader("Upload", type=["xlsx", "csv"])
    if uploaded_file: df = load_data(uploaded_file)
else:
    df = generate_dummy_data()

# ==================
# CORPO
# ==================
if df is not None:
    selected_ds, selected_sit = [], []
    if 'DS' in df.columns: selected_ds = st.sidebar.multiselect("Distrito Sanitário", options=df['DS'].dropna().unique())
    if 'SITUAÇÃO DO CONTRATO/TA' in df.columns: selected_sit = st.sidebar.multiselect("Situação", options=df['SITUAÇÃO DO CONTRATO/TA'].dropna().unique())

    df_filtered = df.copy()
    if selected_ds: df_filtered = df_filtered[df_filtered['DS'].isin(selected_ds)]
    if selected_sit: df_filtered = df_filtered[df_filtered['SITUAÇÃO DO CONTRATO/TA'].isin(selected_sit)]
        
    st.title("Painel Integrado de Equipamentos da Saúde")
    
    col1, col2, col3, col4 = st.columns(4)
    total_equip = len(df_filtered)
    vencidos, alerta = 0, 0
    if 'SINALIZADOR DE PRAZO PARA TA' in df_filtered.columns:
        vencidos = len(df_filtered[df_filtered['SINALIZADOR DE PRAZO PARA TA'].astype(str).str.contains('VENCIDO', case=False)])
        alerta = len(df_filtered[df_filtered['SINALIZADOR DE PRAZO PARA TA'].astype(str).str.contains('ALERTA', case=False)])
    
    with col1: st.markdown(f'<div class="metric-card"><div class="metric-title">Total de Equipamentos</div><div class="metric-value">{total_equip}</div></div>', unsafe_allow_html=True)
    with col2: st.markdown(f'<div class="metric-card success"><div class="metric-title">No Prazo</div><div class="metric-value">{total_equip - vencidos - alerta}</div></div>', unsafe_allow_html=True)
    with col3: st.markdown(f'<div class="metric-card warning"><div class="metric-title">Em Alerta (<= 90 Dias)</div><div class="metric-value">{alerta}</div></div>', unsafe_allow_html=True)
    with col4: st.markdown(f'<div class="metric-card danger"><div class="metric-title">Vencidos</div><div class="metric-value">{vencidos}</div></div>', unsafe_allow_html=True)

    col_map, col_chart = st.columns([6, 4])
    with col_map:
        st.subheader("📍 Localização")
        
        # Filtra apenas os que tem coordenadas válidas
        map_df = df_filtered.dropna(subset=['LATITUDE', 'LONGITUDE']) if 'LATITUDE' in df_filtered.columns else pd.DataFrame()
        
        map_center = [map_df['LATITUDE'].mean(), map_df['LONGITUDE'].mean()] if not map_df.empty else [-8.0476, -34.8770]
        
        # Alterado de 'CartoDB positron' para 'OpenStreetMap' para remover a marca d'agua de API REQUIRED
        m = folium.Map(location=map_center, zoom_start=11, tiles='OpenStreetMap')
        
        if not map_df.empty:
            for idx, row in map_df.iterrows():
                sinal = str(row.get('SINALIZADOR DE PRAZO PARA TA', ''))
                color = 'red' if 'VENCIDO' in sinal.upper() else 'orange' if 'ALERTA' in sinal.upper() else 'green'
                folium.CircleMarker(location=[row['LATITUDE'], row['LONGITUDE']], radius=7, popup=f"<b>{row.get('NOME DO EQUIPAMENTO', '')}</b>", color=color, fill=True).add_to(m)
        st_folium(m, width="100%", height=400, returned_objects=[])

    with col_chart:
        st.subheader("📊 Equipamentos por DS")
        if 'DS' in df_filtered.columns:
            ds_counts = df_filtered['DS'].value_counts().reset_index()
            ds_counts.columns = ['DS', 'Quantidade']
            fig = px.bar(ds_counts, x='Quantidade', y='DS', orientation='h', color='Quantidade', color_continuous_scale='Blues')
            fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 Detalhamento de Prazos")
    def style_sinal(val):
        val_str = str(val).upper()
        if 'VENCIDO' in val_str: return 'background-color: #FEE2E2; color: #DC2626;'
        if 'ALERTA' in val_str: return 'background-color: #FEF3C7; color: #D97706;'
        return 'background-color: #D1FAE5; color: #059669;'

    cols_to_show = [c for c in ['NOME DO EQUIPAMENTO', 'CEP', 'DS', 'DIAS PARA O FIM DA VIGÊNCIA', 'SITUAÇÃO DO CONTRATO/TA', 'SINALIZADOR DE PRAZO PARA TA'] if c in df_filtered.columns]
    if cols_to_show:
        styled_df = df_filtered[cols_to_show].style
        if 'SINALIZADOR DE PRAZO PARA TA' in cols_to_show:
            styled_df = styled_df.map(style_sinal, subset=['SINALIZADOR DE PRAZO PARA TA'])
        st.dataframe(styled_df, use_container_width=True, height=400)
else:
    st.info("Aguardando carregamento da base de dados...")
