import streamlit as st
import pandas as pd

# Configuración Pro
st.set_page_config(page_title="Inventario Dental Pro", layout="wide")

# Título Principal
st.markdown("<h1 style='color: #00acc1; text-align: center;'>🦷 Sistema Dental - Alberto Ballarta</h1>", unsafe_allow_html=True)

# Base de datos temporal
if 'inventario' not in st.session_state:
    st.session_state.inventario = pd.DataFrame({
        "Producto": ["Resina Z350", "Guantes Nitrilo", "Adhesivo Dental", "Algodón en rollo"],
        "Stock_Actual": [10, 40, 5, 30],
        "Precio_Venta": [85.0, 25.0, 120.0, 10.0]
    })

# Mostrar la Tabla de Stock
st.subheader("📋 Stock Disponible")
st.dataframe(st.session_state.inventario, use_container_width=True, hide_index=True)

st.divider()

# Sección de Pedido
st.subheader("🛒 Armar Pedido")
col1, col2 = st.columns(2)

with col1:
    prod_sel = st.selectbox("Selecciona producto:", st.session_state.inventario["Producto"])
with col2:
    cant_sel = st.number_input("Cantidad:", min_value=1, value=1)

if st.button("➕ Agregar al Carrito", type="primary"):
    st.success(f"Añadido: {cant_sel} de {prod_sel}")

st.divider()
st.markdown("<p style='text-align: center; color: gray;'>Desarrollado por Alberto Ballarta | Soluciones Cloud 2026</p>", unsafe_allow_html=True)
