import streamlit as st
import pandas as pd
import boto3
import time
from datetime import datetime, timedelta

# --- 1. CONEXIÓN CON AMAZON DYNAMODB ---
try:
    session = boto3.Session(
        aws_access_key_id=st.secrets["aws"]["aws_access_key_id"],
        aws_secret_access_key=st.secrets["aws"]["aws_secret_access_key"],
        region_name=st.secrets["aws"]["aws_region"]
    )
    dynamodb = session.resource('dynamodb')
    tabla = dynamodb.Table('Inventariodentaltio')
except Exception as e:
    st.error(f"Error de conexión con AWS: {e}")

# --- 2. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="Inventario Dental Pro", layout="wide")

st.markdown("""
    <style>
    .titulo-seccion { font-size:30px !important; font-weight: bold; color: #00acc1; margin-bottom: 20px; }
    [data-testid="stMetricValue"] { color: #00acc1 !important; font-size: 45px !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center; color: #00acc1;'>🦷 SISTEMA DENTAL - ALBERTO BALLARTA</h1>", unsafe_allow_html=True)

def obtener_tiempo_peru():
    ahora = datetime.utcnow() - timedelta(hours=5)
    fecha = ahora.strftime("%d/%m/%Y")
    hora = ahora.strftime("%H:%M:%S")
    return fecha, hora

def cargar_datos_aws():
    try:
        respuesta = tabla.scan()
        items = respuesta.get('Items', [])
        if not items: return pd.DataFrame()
        df = pd.DataFrame(items)
        df["Stock_Actual"] = pd.to_numeric(df["Stock_Actual"])
        df["Precio_Venta"] = pd.to_numeric(df["Precio_Venta"])
        return df.sort_values(by="ID_Producto").reset_index(drop=True)
    except: return pd.DataFrame()

# Inicializar estados de sesión
if 'df_memoria' not in st.session_state: st.session_state.df_memoria = cargar_datos_aws()
if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'ventas_dia' not in st.session_state: st.session_state.ventas_dia = []
if 'lista_vendidos' not in st.session_state: st.session_state.lista_vendidos = []
if 'admin_autenticado' not in st.session_state: st.session_state.admin_autenticado = False

# --- 3. TABLA DE STOCK ---
st.markdown("<p class='titulo-seccion'>📋 Inventario en Tiempo Real (AWS)</p>", unsafe_allow_html=True)
df_vis = st.session_state.df_memoria.copy()
if not df_vis.empty:
    columnas_ordenadas = ['ID_Producto', 'Producto', 'Stock_Actual', 'Precio_Venta']
    df_vis = df_vis[columnas_ordenadas]
    df_vis['Stock_Actual'] = df_vis['Stock_Actual'].astype(int)
    df_vis['Precio_Venta'] = df_vis['Precio_Venta'].map('S/ {:,.2f}'.format)
    st.table(df_vis)

# --- 4. REGISTRAR VENTA ---
st.divider()
st.markdown("<p class='titulo-seccion'>🛒 Armar Pedido</p>", unsafe_allow_html=True
