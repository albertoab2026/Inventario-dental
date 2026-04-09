import streamlit as st
import pandas as pd
import boto3
from botocore.exceptions import NoCredentialsError

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Inventario Dental", layout="wide")

# 2. CARGA DE SECRETOS (AWS Y AUTH)
try:
    aws_id = st.secrets["aws"]["aws_access_key_id"]
    aws_key = st.secrets["aws"]["aws_secret_access_key"]
    aws_region = st.secrets["aws"]["aws_region"]
    admin_pass = st.secrets["auth"]["admin_password"]
except KeyError as e:
    st.error(f"Falta una configuración en los Secretos: {e}")
    st.stop()

# 3. FUNCIÓN PARA CARGAR DATOS
@st.cache_data
def cargar_datos():
    # Asegúrate de que este archivo exista en tu GitHub
    df = pd.read_csv("inventario.csv")
    # Limpieza: quitar espacios vacíos en los nombres de columnas
    df.columns = df.columns.str.strip()
    return df

df = cargar_datos()

# 4. INTERFAZ PÚBLICA (LO QUE VE EL CLIENTE)
st.title("🦷 Sistema de Inventario Dental")

with st.expander("🔐 PANEL DE ADMINISTRADOR"):
    password = st.text_input("Introduce la contraseña para gestionar:", type="password")
    
    if password == admin_pass:
        st.success("Acceso concedido")
        
        # --- SECCIÓN DE GESTIÓN ---
        st.subheader("Gestión de Stock")
        
        # Buscamos la columna 'Producto' sin importar mayúsculas/minúsculas
        columnas = {c.lower(): c for c in df.columns}
        
        if 'producto' in columnas:
            nombre_col_real = columnas['producto']
            lista_productos = df[nombre_col_real].tolist()
            
            producto_sel = st.selectbox("Elegir producto para abastecer:", lista_productos)
            cantidad = st.number_input("Cantidad a añadir:", min_value=1, value=10)
            
            if st.button("Actualizar Inventario"):
                # Aquí iría tu lógica para subir a S3 o DynamoDB
                st.info(f"Actualizando {producto_sel} con +{cantidad} unidades...")
        else:
            st.error(f"Error: No se encuentra la columna 'Producto'. Columnas actuales: {list(df.columns)}")

        if st.button("CERRAR SESIÓN ADMIN"):
            st.rerun()
            
    elif password != "":
        st.error("Contraseña incorrecta")

# 5. MOSTRAR TABLA DE PRODUCTOS (VISTA GENERAL)
st.subheader("Stock Actual")
st.dataframe(df, use_container_width=True)
