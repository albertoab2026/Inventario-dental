import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Inventario Dental Pro", layout="wide")
st.title("🦷 Demo Inventario de Mi Tío")

# Inicializar la memoria de ventas si no existe
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
    # Guardar en la memoria temporal
    precio_unitario = df.loc[df['Producto'] == prod_seleccionado, 'Precio_Venta'].values[0]
    venta = {
        "Hora": datetime.now().strftime("%H:%M:%S"),
        "Producto": prod_seleccionado,
        "Cant": cantidad,
        "Subtotal": cantidad * precio_unitario
    }
    st.session_state.historial_ventas.append(venta)
    st.success(f"Venta registrada: {cantidad} de {prod_seleccionado}")

st.divider()
if st.button("🔴 CERRAR CAJA Y VER RESUMEN"):
    if st.session_state.historial_ventas:
        st.header(f"💰 Resumen de Ventas")
        # Convertir la memoria en una tablita para mostrar
        df_ventas = pd.DataFrame(st.session_state.historial_ventas)
        st.table(df_ventas)
        
        total_plata = df_ventas['Subtotal'].sum()
        st.metric("GANANCIA TOTAL", f"S/ {total_plata:,.2f}")
        st.balloons()
    else:
        st.warning("Aún no has registrado ninguna venta hoy.")
