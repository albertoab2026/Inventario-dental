import streamlit as st
import pandas as pd
from datetime import datetime
import pytz

# 1. Configurar la hora de Perú (Esto es lo que faltaba arriba)
zona_horaria = pytz.timezone('America/Lima')

st.set_page_config(page_title="Inventario Dental Pro", layout="wide")
st.title("🦷 Demo Inventario de Mi Tío")

# Inicializar la memoria de ventas
if 'historial_ventas' not in st.session_state:
    st.session_state.historial_ventas = []

df = pd.read_csv('inventario.csv')

st.subheader("📋 Inventario General")
df['Stock_Actual'] = df['Stock_Inicial'] - df['Vendido']
st.table(df) 

st.divider()
st.subheader("🛒 Registrar Venta Rápida")
col1, col2 = st.columns(2)
with col1:
    prod_seleccionado = st.selectbox("Producto vendido:", df['Producto'])
with col2:
    cantidad = st.number_input("Cantidad:", min_value=1, value=1)

if st.button("✅ Registrar Venta"):
    # Buscar el precio del producto elegido
    precio_unitario = df.loc[df['Producto'] == prod_seleccionado, 'Precio_Venta'].values[0]
    
    # Guardar la venta con la hora de LIMA
    nueva_venta = {
        "Hora": datetime.now(zona_horaria).strftime("%H:%M:%S"),
        "Producto": prod_seleccionado,
        "Cant": cantidad,
        "Total": cantidad * precio_unitario
    }
    st.session_state.historial_ventas.append(nueva_venta)
    st.success(f"¡Venta registrada con éxito a las {nueva_venta['Hora']}!")

st.divider()
if st.button("🔴 CERRAR CAJA Y VER RESUMEN"):
    if st.session_state.historial_ventas:
        st.header(f"💰 Resumen de Ventas Hoy")
        df_ventas = pd.DataFrame(st.session_state.historial_ventas)
        st.table(df_ventas)
        
        suma_total = df_ventas['Total'].sum()
        st.metric("GANANCIA TOTAL", f"S/ {suma_total:,.2f}")
        st.balloons()
    else:
        st.warning("Todavía no hay ventas registradas.")
