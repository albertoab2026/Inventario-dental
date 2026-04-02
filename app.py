import streamlit as st
import pandas as pd

# Configuración de la página
st.set_page_config(page_title="Inventario Dental Pro", layout="wide")

# Estilo de la Portada
st.markdown("<h1 style='text-align: center; color: #00acc1;'>🦷 SISTEMA DENTAL PRO</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #666;'>Gestión Profesional - Alberto Ballarta</p>", unsafe_allow_html=True)

# La Planilla de Stock (Tal como en tu foto)
st.subheader("📋 Control de Stock Actual")
data = {
    "Producto": ["Resina Z350", "Guantes Nitrilo", "Adhesivo Dental", "Algodón en rollo"],
    "Stock_Actual": [10, 40, 5, 30],
    "Precio_Venta": [85.0, 25.0, 120.0, 10.0]
}
df = pd.DataFrame(data)
st.table(df) # Usamos st.table para que se vea fija y ordenada

st.divider()

# Sección para Armar Pedido
st.subheader("🛒 Armar Pedido")
col1, col2 = st.columns(2)
with col1:
    prod = st.selectbox("Selecciona producto:", df["Producto"])
with col2:
    cant = st.number_input("Cantidad:", min_value=1, value=1)

if st.button("➕ Agregar al Carrito", type="primary"):
    st.success(f"Añadido al carrito: {cant} unidades de {prod}")

# Firma Final
st.markdown("---")
st.markdown("<p style='text-align: center; color: #00796b;'>Desarrollado con esfuerzo por Alberto Ballarta | 2026</p>", unsafe_allow_html=True)
