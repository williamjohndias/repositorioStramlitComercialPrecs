import streamlit as st
import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv
from datetime import datetime
from streamlit_autorefresh import st_autorefresh 
from io import BytesIO
import base64
from PIL import Image
import plotly.express as px
import streamlit.components.v1 as components
from datetime import datetime
st.session_state.page_height = 900  # ou use st.window_height, futuramente
import locale
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except locale.Error:
    pass

# ---- Tela cheia + tema escuro da PRECS ----
st.set_page_config(page_title="Precs Propostas", layout="wide")

# Estilo personalizado com identidade visual PRECS (preto e dourado)
st.markdown("""
    <style>
    header{
            visibility: hidden;
        }
    body {
        background-color: #0d0d0d;
        color: white;
    }
    .main {
        background-color: #0d0d0d;
    }
    h1, h2, h3, h4 {
        color: #FFD700;
    }
    .stApp {
        background-color: #0d0d0d;
        padding: 2rem;
        max-width: 100%;
    }
    .stButton>button {
        background-color: #FFD700;
        color: black;
        border-radius: 10px;
        border: none;
    }
    .stButton>button:hover {
        background-color: #e6c200;
        color: black;
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .css-1v0mbdj {
        background-color: #1a1a1a !important;
        color: white;
    }
    .css-1d391kg {
        background-color: #1a1a1a !important;
    }
    .stDataFrame {
        background-color: #1a1a1a;
        color: white;
    }

    /* Responsividade */
    @media screen and (max-width: 768px) {
        html, body, [class*="css"] {
            font-size: 12px !important;
        }
        h1, h2, h3, h4 {
            font-size: 14px !important;
        }
        table {
            font-size: 10px !important;
        }
        .stButton>button {
            font-size: 10px !important;
        }
        img {
            max-width: 80% !important;
        }
        .tabela-container {
            max-height: 60vh !important;
        }
        .stColumns {
            flex-direction: column !important;
        }
    }
    @media screen and (min-width: 769px) {
        .stColumns {
            display: flex !important;
            gap: 1rem !important;
        }
    }
    </style>
""", unsafe_allow_html=True)



# ---- Autoatualização (a cada 10 segundos) ----
st_autorefresh(interval=70 * 1000, key="atualizacao")

print(f"Página atualizada em: {datetime.now().strftime('%H:%M:%S')}")

def image_to_base64(image_path):
    img = Image.open(image_path)
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_b64 = base64.b64encode(buffered.getvalue()).decode()
    return img_b64

# ---- Carrega variáveis do .env ----
load_dotenv()
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# ---- Conectar ao PostgreSQL ----
def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        sslmode="require"
    )

# ---- Carregar dados ----
@st.cache_data(ttl=10)
def carregar_dados_propostas():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM dashmetas", conn)
    df["data"] = pd.to_datetime(df["data"])
    conn.close()
    return df

@st.cache_data(ttl=10)
def carregar_dados_campanhas():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM campanhas", conn)
    conn.close()
    return df

def atualizar_status_campanhas(campanhas_selecionadas):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE campanhas SET status_campanha = FALSE")
        for campanha in campanhas_selecionadas:
            cur.execute(
                "UPDATE campanhas SET status_campanha = TRUE WHERE nome_campanha = %s",
                (campanha,)
            )
        conn.commit()
    except Exception as e:
        st.error(f"Erro ao atualizar status das campanhas: {e}")
    finally:
        cur.close()
        conn.close()

def contar_propostas(df, df_original):
    # Garante que a coluna 'data' é datetime
    df['data'] = pd.to_datetime(df['data'])

    # Ordena pela data (da mais recente primeiro)
    df_sorted = df.sort_values(by='data', ascending=False)

    # Mantém a última vez que cada negócio passou por cada etapa
    df_ultimos = df_sorted.drop_duplicates(subset=['id_negocio', 'id_etapa'], keep='first')


    # Lista de todos os proprietários (caso queira usar depois)
    all_proprietarios = df_original['proprietario'].unique()

    # Contagem de negócios que passaram pela etapa 'Cálculo' (última vez de cada um)
    df_adquiridas = df_ultimos[df_ultimos['id_etapa'] == 'Cálculo'] \
        .groupby('proprietario').agg(quantidade_adquiridas=('id_negocio', 'nunique')).reset_index()

    # Contagem de negócios que passaram pela etapa 'Negociações iniciadas' (última vez de cada um)
    df_apresentadas = df_ultimos[df_ultimos['id_etapa'] == 'Negociações iniciadas'] \
        .groupby('proprietario').agg(quantidade_apresentadas=('id_negocio', 'nunique')).reset_index()

    # Garante todos os proprietários no resultado final
    df_adquiridas_full = pd.DataFrame({'proprietario': all_proprietarios}) \
        .merge(df_adquiridas, on='proprietario', how='left').fillna(0)
    
    df_apresentadas_full = pd.DataFrame({'proprietario': all_proprietarios}) \
        .merge(df_apresentadas, on='proprietario', how='left').fillna(0)

    # Junta os resultados
    return pd.merge(df_adquiridas_full, df_apresentadas_full, on='proprietario', how='outer').fillna(0)

def get_cor_barra(valor, maximo=6):
    if valor >= maximo:
        return "background-color: #FFD700; box-shadow: 0 0 5px #FFD700, 0 0 10px #FFD700, 0 0 15px #FFD700;"
    return "background-color: #c3a43e;"



df_original = carregar_dados_propostas()
df = df_original.copy()
df_campanhas = carregar_dados_campanhas()

# ---- Sidebar ----
with st.sidebar:
    st.header("Filtros")
    mostrar_gestao = st.checkbox("Mostrar proprietário 'Gestão'", value=False)
    
    proprietarios_disponiveis = df["proprietario"].unique().tolist()
    if not mostrar_gestao:
        proprietarios_disponiveis = [p for p in proprietarios_disponiveis if p != "Gestão"]
    
    proprietarios = st.multiselect("Proprietário", options=proprietarios_disponiveis, default=proprietarios_disponiveis)
    etapas = st.multiselect("Etapa", df["id_etapa"].unique(), default=df["id_etapa"].unique())
    data_ini = st.date_input("Data inicial", df["data"].max().date())
    data_fim = st.date_input("Data final", df["data"].max().date())
    
    campanhas_disponiveis = df_campanhas["nome_campanha"].tolist()
    campanhas_selecionadas = st.multiselect(
        "Campanhas",
        options=campanhas_disponiveis,
        default=df_campanhas[df_campanhas["status_campanha"] == True]["nome_campanha"].tolist(),
        key="campanhas_filtro"
    )

atualizar_status_campanhas(campanhas_selecionadas)

if not mostrar_gestao:
    df = df[df["proprietario"] != "Gestão"]
    df_original = df_original[df_original["proprietario"] != "Gestão"]

df_filtrado = df.copy()
if proprietarios:
    df_filtrado = df_filtrado[df_filtrado["proprietario"].isin(proprietarios)]
if etapas:
    df_filtrado = df_filtrado[df_filtrado["id_etapa"].isin(etapas)]
df_filtrado = df_filtrado[
    (df_filtrado["data"].dt.date >= data_ini) &
    (df_filtrado["data"].dt.date <= data_fim)
]

df_propostas = contar_propostas(df_filtrado, df_original)
total_adquiridas = df_propostas['quantidade_adquiridas'].sum()
total_apresentadas = df_propostas['quantidade_apresentadas'].sum()

# ---- Total de propostas ----
#st.markdown(f"<p style='text-align:center; font-size:16px; color:#C5A45A; font-weight: bold;'>{int(total_adquiridas)} adquiridas | {int(total_apresentadas)} apresentadas</p>", unsafe_allow_html=True)

# ---- Visualizações principais ----
col2, col1 = st.columns([1,3])

with col1:
    medalha_b64 = image_to_base64("medalha.png")
    if not df_propostas.empty:
        tabela_html = f"""
        <div style=" border: 2px solid #C5A45A ">
            <h3 style='color: #D4AF37 !important; text-align: center; font-size: 40px; margin-top: 5px; margin-bottom: 5px;'>
                Propostas Diárias
            </h3>
            <table style="width: 100%; border-collapse: collapse; font-size: 10px;">
            <thead>
                <tr style="border-bottom: 2px solid #C5A45A;">
                    <th style="font-size: 25px; text-align: left; background-color: #000000; color: #C5A45A; padding: 10px;">Nome</th>
                    <th style="font-size: 25px; text-align: center; background-color: #1A1A1A; color: #C5A45A; padding: 10px;">Adquiridas: {int(total_adquiridas)}/90</th>
                    <th style="font-size: 25px; text-align: center; background-color: #333333; color: #C5A45A; padding: 10px;">Apresentadas: {int(total_apresentadas)}/90</th>
                </tr>
            </thead>
            <tbody>
        """

        maximo = 6
        for _, row in df_propostas.iterrows():
            nome = row['proprietario']
            valor1 = int(row['quantidade_adquiridas'])
            valor2 = int(row['quantidade_apresentadas'])
            medalha_html = f"""<img src="data:image/png;base64,{medalha_b64}" width="25" style="margin-left: 10px; vertical-align: middle;">""" \
                if valor1 >= 6 or valor2 >= 6 else ""
            
            proporcao1 = min(valor1 / maximo, 1.0)
            proporcao2 = min(valor2 / maximo, 1.0)
            cor_barra1 = get_cor_barra(valor1)
            cor_barra2 = get_cor_barra(valor2)

            barra1 = f"""
            <div style='background-color: #2C2C2C; width: 100%; height: 15px; border-radius: 6px; border: 2px solid #D4AF37;'>
                <div style='width: {proporcao1*100:.1f}%; {cor_barra1} height: 100%; border-radius: 4px;'></div>
            </div>
            <span style='font-size: 12px; color: #ccc;'>{valor1}/{maximo}</span>
            """

            barra2 = f"""
            <div style='background-color: #2C2C2C; width: 100%; height: 15px; border-radius: 6px; border: 2px solid #D4AF37;'>
                <div style='width: {proporcao2*100:.1f}%; {cor_barra2} height: 100%; border-radius: 4px;'></div>
            </div>
            <span style='font-size: 12px; color: #ccc;'>{valor2}/{maximo}</span>
            """

            tabela_html += f"""
            <tr style="border-bottom: 1px solid #FFD700;"> <!-- dourado -->
                <td style="font-size: 25px; background-color: #000000; padding: 10px 12px; color: #FFF; vertical-align: middle; text-align: left;">
                    {nome} {medalha_html}
                </td>
                <td style="padding: 10px 12px; background-color: #1A1A1A; color: #FFD700; vertical-align: middle; text-align: center;">
                    {barra1}
                </td>
                <td style="padding: 10px 12px; background-color: #333333; color: #FFD700; vertical-align: middle; text-align: center;">
                    {barra2}
                </td>
            </tr>
            """

        tabela_html += "</tbody></table></div>"
        components.html(tabela_html, height=2000, scrolling=False)


with col2:
    logo_b64 = image_to_base64("precs2.png")
    sino_b64 = image_to_base64("sino.png")  # Seu arquivo de sino
    
    st.markdown(f"""
        <div style="display: flex; justify-content: center; align-items: center; text-align: center;"> 
            <img src="data:image/png;base64,{logo_b64}" width="300" style="border-radius: 12px;">
        </div> 
    """, unsafe_allow_html=True)
    
    # Cabeçalho com logo e título
    st.markdown(f"""
        <div style="display: flex; justify-content: center; align-items: center; text-align: center;">
            <h1 style="font-size: 45px; color: #D4AF37; margin: 0;">Precs Propostas</h1> 
        </div>
        <h3 style='font-size: 25px; color: #C5A45A; font-weight: bold; text-align: center;'>
            Segunda-feira - 28/07/2025
        </h3>
    """, unsafe_allow_html=True)

    # Título das campanhas + sino
    st.markdown("""
        <h2 style='text-align: center; color: #D4AF37; margin-bottom: 10px;'>Campanhas Ativas</h2>
    """, unsafe_allow_html=True)

    st.markdown(f"""
        <div style='text-align: center; margin-bottom: 80px;'>
            <img src="data:image/png;base64,{sino_b64}" width="150px;">
        </div>
    """, unsafe_allow_html=True)

    # Lista de campanhas
    campanhas_ativas = df_campanhas[df_campanhas["status_campanha"] == True]
    for _, campanha in campanhas_ativas.iterrows():
        st.markdown(f"""
            <div style="display: flex; justify-content: center; align-items: center; text-align: center; margin-bottom: 10px;">
                <span style="font-size: 40px; color: #FFF;">{campanha['nome_campanha']}</span>
            </div>
        """, unsafe_allow_html=True)