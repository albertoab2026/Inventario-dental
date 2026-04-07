import streamlit as st
import pandas as pd
import boto3
import time
import io
from datetime import datetime, timedelta
from decimal import Decimal

# --- 1. CONEXIÓN AWS (Configurada en st.secrets) ---
try:
    session = boto3.Session(
        aws_access_key_id=st.secrets["aws"]["aws_access_key_id"],
        aws_secret_access_key=st.secrets["aws"]["aws_secret_access_key"],
        region_name=st.secrets["aws"]["aws_region"]
    )
    dynamodb = session.resource('dynamodb')
    tabla_inventario = dynamodb.Table('Inventariodentaltio')
    tabla_ventas = dynamodb.Table('VentasDentaltio')
except Exception as e:
    st.error(f"Error de conexión AWS: {e}")

# --- 2. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="Inventario Dental Pro", layout="wide")

st.markdown("""
    <style>
    .titulo-seccion { font-size:28px !important; font-weight: bold; color: #00acc1; margin-top: 20px; }
    [data-testid="stMetricValue"] { color: #00acc1 !important; font-size: 40px !important; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center; color: #00acc1;'>🦷 SISTEMA DENTAL - ALBERTO BALLARTA</h1>", unsafe_allow_html=True)

# --- 3. FUNCIONES ---
def obtener_tiempo_peru():
    ahora = datetime.utcnow() - timedelta(hours=5)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%H:%M:%S")

def cargar_datos():
    try:
        data = tabla_inventario.scan()["Items"]
        df = pd.DataFrame(data)
        if not df.empty:
            df["Stock_Actual"] = pd.to_numeric(df["Stock_Actual"])
            df["Precio_Venta"] = pd.to_numeric(df["Precio_Venta"])
            return df.sort_values(by="ID_Producto").reset_index(drop=True)
        return pd.DataFrame()
    except:
        return pd.DataFrame()

# --- 4. ESTADO DE SESIÓN ---
if "df" not in st.session_state:
    st.session_state.df = cargar_datos()

if "carrito" not in st.session_state:
    st.session_state.carrito = []

if "admin_autenticado" not in st.session_state:
    st.session_state.admin_autenticado = False

# --- 5. TABLA DE INVENTARIO ---
st.markdown("<p class='titulo-seccion'>📋 Inventario en la Nube</p>", unsafe_allow_html=True)
df = st.session_state.df

if not df.empty:
    df_view = df.copy()
    df_view["Precio_Venta"] = df_view["Precio_Venta"].map("S/ {:.2f}".format)
    st.table(df_view[['ID_Producto', 'Producto', 'Stock_Actual', 'Precio_Venta']])
else:
    st.info("Cargando datos o inventario vacío...")

# --- 6. REGISTRO DE VENTA (ESTA SECCIÓN YA NO SE ESCONDE) ---
st.divider()
st.markdown("<p class='titulo-seccion'>🛒 Registrar Nueva Venta</p>", unsafe_allow_html=True)

if not df.empty:
    col_sel, col_cant = st.columns(
