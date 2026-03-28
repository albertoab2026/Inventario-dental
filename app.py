import streamlit as st
import pandas as pd

st.set_page_config(page_title="Inventario Dental Pro", layout="wide")
st.title("🦷 Demo Inventario de Mi Tío")

# Leer los datos del archivo csv que creaste antes
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
    st.success(f"Venta registrada: {cantidad} de {prod_seleccionado}")
    st.info("Nota: En este demo, el stock vuelve a su estado original al recargar.")

st.divider()
if st.button("🔴 CERRAR CAJA Y VER GANANCIAS"):
    st.header(f"💰 Resumen de Hoy")
    st.metric("Total Vendido Hoy", "S/ 350.00")
    st.write("¡Felicidades por las ventas de hoy!")
    st.balloons()
