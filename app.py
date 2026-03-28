import streamlit as st
import pandas as pd
from datetime import datetime
import pytz

# 1. Configuración de Hora de Lima
zona_horaria = pytz.timezone('America/Lima')

st.set_page_config(page_title="Inventario Dental Pro", layout="wide")
st.title("🦷 Demo Inventario de Mi Tío")

# 2. TRUCO: Cargar el inventario a la MEMORIA para que se pueda restar
if 'df_memoria' not in st.session_state:
    st.session_state.df_memoria = pd.read_csv('inventario.csv')
    # Creamos la columna de Stock Actual si no existe
    st.session_state.df_memoria['Stock_Actual'] = st.session_state.df_memoria['Stock_Inicial']

# Inicializar historial de ventas
if 'historial_ventas' not in st.session_state:
    st.session_state.historial_ventas = []

# 3. MOSTRAR LA TABLA (Se actualizará sola cuando restemos)
st.subheader("📋 Inventario en Tiempo Real")
st.table(st.session_state.df_memoria[['Producto', 'Stock_Actual', 'Precio_Venta']])

st.divider()

# 4. REGISTRAR VENTA Y RESTAR STOCK
st.subheader("🛒 Registrar Venta")
col1, col2 = st.columns(2)
with col1:
    prod_seleccionado = st.selectbox("Producto:", st.session_state.df_memoria['Producto'])
with col2:
    cantidad = st.number_input("Cantidad:", min_value=1, value=1)

if st.button("✅ Confirmar Venta"):
    # Buscar el stock actual del producto
    idx = st.session_state.df_memoria[st.session_state.df_memoria['Producto'] == prod_seleccionado].index[0]
    stock_ahora = st.session_state.df_memoria.at[idx, 'Stock_Actual']

    if stock_ahora >= cantidad:
        # ¡AQUÍ ESTÁ LA MAGIA! Restamos el stock en la memoria
        st.session_state.df_memoria.at[idx, 'Stock_Actual'] = stock_ahora - cantidad
        
        # Guardar en el historial para el cierre de caja
        precio_v = st.session_state.df_memoria.at[idx, 'Precio_Venta']
        nueva_venta = {
            "Hora": datetime.now(zona_horaria).strftime("%H:%M:%S"),
            "Producto": prod_seleccionado,
            "Cant": cantidad,
            "Total": cantidad * precio_v
        }
        st.session_state.historial_ventas.append(nueva_venta)
        st.success(f"Venta realizada. ¡Stock actualizado!")
        st.rerun() # Esto hace que la tabla de arriba se refresque al instante
    else:
        st.error(f"¡No hay suficiente stock! Solo quedan {stock_ahora} unidades.")

st.divider()
if st.button("🔴 CERRAR CAJA"):
    if st.session_state.historial_ventas:
        st.header(f"💰 Resumen del Día")
        df_resumen = pd.DataFrame(st.session_state.historial_ventas)
        st.table(df_resumen)
        st.metric("GANANCIA TOTAL", f"S/ {df_resumen['Total'].sum():,.2f}")
        st.balloons()
    else:
        st.warning("No hay ventas para resumir.")
