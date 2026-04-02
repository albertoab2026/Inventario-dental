import streamlit as st
import pandas as pd

# 1. Configuración de la página
st.set_page_config(page_title="Inventario Dental Pro - Alberto Ballarta", layout="wide")

# Estilo y Título
st.markdown("<h2 style='color: #00acc1; text-align: center;'>🦷 Sistema Dental - Control de Ventas</h2>", unsafe_allow_html=True)

# 2. Datos de prueba (Esto luego vendrá de AWS)
if 'df_memoria' not in st.session_state:
    data = {
        "Producto": ["Resina Z350", "Guantes Nitrilo", "Adhesivo Dental", "Algodon en rollo"],
        "Stock_Actual": [0, 40, 0, 30],
        "Precio_Venta": [85, 25, 120, 10]
    }
    st.session_state.df_memoria = pd.DataFrame(data)

# 3. Mostrar Inventario
st.subheader("📋 Stock Disponible")
st.dataframe(st.session_state.df_memoria, use_container_width=True, hide_index=True)

st.divider()

# 4. Sección Armar Pedido
st.subheader("🛒 Armar Pedido")
col1, col2 = st.columns(2)

with col1:
    prod_sel = st.selectbox("Selecciona producto:", st.session_state.df_memoria["Producto"])
with col2:
    cant_sel = st.number_input("Cantidad:", min_value=1, value=1)

if st.button("➕ Agregar al Carrito", type="primary"):
    # Lógica de validación
    idx = st.session_state.df_memoria[st.session_state.df_memoria['Producto'] == prod_sel].index[0]
    stock_real = st.session_state.df_memoria.at[idx, 'Stock_Actual']
    
    if cant_sel > stock_real:
        st.error(f"❌ Error: Solo quedan {stock_real} unidades de {prod_sel}")
    else:
        st.success(f"✅ Añadido: {cant_sel} de {prod_sel}")

st.divider()

# 5. Tu Firma Final
st.markdown("""
    <div style='text-align: center; color: #00796b; padding: 20px;'>
        <p>💪 Desarrollado con esfuerzo por</p>
        <h3>Alberto Ballarta</h3>
        <p>Soluciones Cloud para Negocios Locales | 2026</p>
    </div>
""", unsafe_allow_html=True)
