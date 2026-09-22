import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import folium
from streamlit_folium import st_folium

# ==================
# Configuração da página
# ==================
st.set_page_config(
    page_title="Painel Executivo de Equipamentos", 
    page_icon="🏥", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================
# Estilização CSS Moderna
# ==================
st.markdown("""
<style>
    .stApp { background-color: #F8FAFC; }
    .metric-card {
        background-color: #ffffff; border-radius: 12px; padding: 24px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border-left: 5px solid #2563EB; margin-bottom: 1rem;
    }
    .metric-card.warning { border-left-color: #F59E0B; }
    .metric-card.danger { border-left-color: #DC2626; }
    .metric-card.success { border-left-color: #10B981; }
    .metric-title {
        color: #64748B; font-size: 0.9rem; font-weight: 600;
        text-transform: uppercase; margin-bottom: 0.5rem;
    }
    .metric-value { color: #0F172A; font-size: 2rem; font-weight: 800; line-height: 1.2; }
</style>
""", unsafe_allow_html=True)

# ==================
# Funções de Leitura de Dados
# ==================
@st.cache_data(ttl=600)  # Atualiza os dados de 10 em 10 minutos automaticamente
def load_data(url_or_file):
    if not url_or_file: return None
    try:
        if isinstance(url_or_file, str) and "output=csv" in url_or_file:
            df = pd.read_csv(url_or_file)
        else:
            df = pd.read_excel(url_or_file)
            
        if 'LATITUDE' not in df.columns or 'LONGITUDE' not in df.columns:
            df['LATITUDE'] = np.random.uniform(-8.15, -7.95, len(df))
            df['LONGITUDE'] = np.random.uniform(-34.95, -34.85, len(df))
        return df
    except Exception as e:
        st.error(f"Erro ao carregar os dados: {e}")
        return None

def generate_dummy_data():
    """Gera dados de exemplo com a mesma estrutura para visualizar o layout"""
    np.random.seed(42)
    n = 120
    dias_para_fim = np.random.randint(-150, 600, n)
    sinalizador, situacao = [], []
    for dias in dias_para_fim:
        if dias < 0:
            sinalizador.append('VENCIDO'); situacao.append('ENCERRADO')
        elif dias <= 90:
            sinalizador.append('ALERTA VENCIMENTO PRÓXIMO'); situacao.append('VIGENTE')
        else:
            sinalizador.append('VIGENTE - NO PRAZO'); situacao.append('VIGENTE')
    return pd.DataFrame({
        'NOME DO EQUIPAMENTO': [f'Equipamento Saúde {i:03d}' for i in range(1, n+1)],
        'DS': np.random.choice(['DS I', 'DS II', 'DS III', 'DS IV', 'DS V', 'DS VI', 'DS VII'], n),
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

data_source = st.sidebar.radio("Fonte dos Dados:", ["Demonstração (Fictício)", "Planilha Online (Google Sheets)", "Upload de Arquivo"])
df = None

if data_source == "Planilha Online (Google Sheets)":
    st.sidebar.info("Cole o link CSV publicado do Google Sheets abaixo:")
    gsheets_url = st.sidebar.text_input("Link CSV (output=csv):")
    if gsheets_url: df = load_data(gsheets_url)
elif data_source == "Upload de Arquivo":
    uploaded_file = st.sidebar.file_uploader("Faça upload da Planilha", type=["xlsx", "csv"])
    if uploaded_file: df = load_data(uploaded_file)
else:
    df = generate_dummy_data()

# ==================
# CORPO DO PAINEL
# ==================
if df is not None:
    st.sidebar.markdown("---")
    st.sidebar.subheader("Filtros Dinâmicos")
    
    selected_ds, selected_sit = [], []
    if 'DS' in df.columns:
        selected_ds = st.sidebar.multiselect("Distrito Sanitário (DS)", options=df['DS'].dropna().unique(), default=[])
    if 'SITUAÇÃO DO CONTRATO/TA' in df.columns:
        selected_sit = st.sidebar.multiselect("Situação do Contrato", options=df['SITUAÇÃO DO CONTRATO/TA'].dropna().unique(), default=[])

    df_filtered = df.copy()
    if 'DS' in df.columns and selected_ds: df_filtered = df_filtered[df_filtered['DS'].isin(selected_ds)]
    if 'SITUAÇÃO DO CONTRATO/TA' in df.columns and selected_sit: df_filtered = df_filtered[df_filtered['SITUAÇÃO DO CONTRATO/TA'].isin(selected_sit)]
        
    st.title("Painel Integrado de Equipamentos da Saúde")
    st.markdown("Acompanhamento de contratos, vigências e distribuição geográfica.")
    
    col1, col2, col3, col4 = st.columns(4)
    total_equip = len(df_filtered)
    vencidos, alerta = 0, 0
    if 'SINALIZADOR DE PRAZO PARA TA' in df_filtered.columns:
        vencidos = len(df_filtered[df_filtered['SINALIZADOR DE PRAZO PARA TA'].astype(str).str.contains('VENCIDO', case=False)])
        alerta = len(df_filtered[df_filtered['SINALIZADOR DE PRAZO PARA TA'].astype(str).str.contains('ALERTA', case=False)])
    
    with col1: st.markdown(f'<div class="metric-card"><div class="metric-title">Total de Equipamentos</div><div class="metric-value">{total_equip}</div></div>', unsafe_allow_html=True)
    with col2: st.markdown(f'<div class="metric-card success"><div class="metric-title">Contratos no Prazo</div><div class="metric-value">{total_equip - vencidos - alerta}</div></div>', unsafe_allow_html=True)
    with col3: st.markdown(f'<div class="metric-card warning"><div class="metric-title">Em Alerta (<= 90 Dias)</div><div class="metric-value">{alerta}</div></div>', unsafe_allow_html=True)
    with col4: st.markdown(f'<div class="metric-card danger"><div class="metric-title">Contratos Vencidos</div><div class="metric-value">{vencidos}</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    col_map, col_chart = st.columns([6, 4])
    with col_map:
        st.subheader("📍 Localização (Status dos Prazos)")
        map_center = [df_filtered['LATITUDE'].mean(), df_filtered['LONGITUDE'].mean()] if not df_filtered.empty and 'LATITUDE' in df_filtered.columns else [-8.0476, -34.8770]
        m = folium.Map(location=map_center, zoom_start=12, tiles='CartoDB positron')
        
        if 'LATITUDE' in df_filtered.columns and 'LONGITUDE' in df_filtered.columns:
            for idx, row in df_filtered.iterrows():
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
        if 'VENCIDO' in val_str: return 'background-color: #FEE2E2; color: #DC2626; font-weight: bold;'
        if 'ALERTA' in val_str: return 'background-color: #FEF3C7; color: #D97706; font-weight: bold;'
        return 'background-color: #D1FAE5; color: #059669; font-weight: bold;'

    cols_to_show = [c for c in ['NOME DO EQUIPAMENTO', 'DS', 'INÍCIO DA VIGÊNCIA', 'TÉRMINO DA VIGÊNCIA', 'DIAS PARA O FIM DA VIGÊNCIA', 'SITUAÇÃO DO CONTRATO/TA', 'SINALIZADOR DE PRAZO PARA TA'] if c in df_filtered.columns]
    if cols_to_show:
        styled_df = df_filtered[cols_to_show].style
        if 'SINALIZADOR DE PRAZO PARA TA' in cols_to_show:
            styled_df = styled_df.map(style_sinal, subset=['SINALIZADOR DE PRAZO PARA TA'])
        st.dataframe(styled_df, use_container_width=True, height=400)
else:
    st.info("Aguardando carregamento da base de dados...")
