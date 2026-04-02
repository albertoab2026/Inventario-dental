import streamlit as st
import pandas as pd

# Configuración de estilo Oscuro
st.set_page_config(page_title="Inventario Dental Pro", layout="wide")

# Título e información
st.markdown("<h2 style='color: #00acc1; text-align: center;'>🦷 Inventario Dental Pro - Alberto Ballarta</h2>", unsafe_allow_html=True)

# 1. LA TABLA DE STOCK ACTUAL (Igual a tu captura)
st.subheader("📋 Estado del Inventario")
data = {
    "Producto": ["Resina Z350", "Guantes Nitrilo", "Adhesivo Dental", "Algodon en rollo"],
    "Stock_Actual": [0, 40, 0, 30],
    "Precio_Venta": [85, 25, 120, 10]
}
df = pd.DataFrame(data)
st.table(df)

st.divider()

# 2. SECCIÓN ARMAR PEDIDO
st.subheader("🛒 Armar Pedido")
col1, col2 = st.columns([2, 1])

with col1:
    producto_sel = st.selectbox("Selecciona producto:", df["Producto"])
with col2:
    cantidad_sel = st.number_input("Cantidad:", min_value=0, value=20)

if st.button("➕ Agregar al Carrito", type="primary"):
    # Buscamos el stock actual del producto seleccionado
    stock_disponible = df.loc[df['Producto'] == producto_sel, 'Stock_Actual'].values[0]
    
    if cantidad_sel > stock_disponible:
        st.error(f"❌ No puedes añadir {cantidad_sel}. Solo quedan {stock_disponible} en total.")
    else:
        st.success(f"✅ Añadido al carrito: {producto_sel}")

st.divider()

# 3. ARTÍCULOS EN EL CARRITO
st.subheader("📝 Artículos en el Carrito:")
# Aquí crearemos la tabla del carrito más adelante con AWS
