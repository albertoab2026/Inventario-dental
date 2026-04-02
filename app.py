import streamlit as st
import pandas as pd
from datetime import datetime

# 1. Configuración de la página
st.set_page_config(page_title="Inventario Dental Pro", layout="wide")

st.markdown("<h1 style='text-align: center; color: #00acc1;'>🦷 SISTEMA DENTAL - ALBERTO BALLARTA</h1>", unsafe_allow_html=True)

# 2. Inicializar Memorias
if 'df_memoria' not in st.session_state:
    st.session_state.df_memoria = pd.DataFrame({
        "Producto": ["Resina Z350", "Guantes Nitrilo", "Adhesivo Dental", "Algodón en rollo"],
        "Stock_Actual": [10, 40, 5, 30],
        "Precio_Venta": [85.0, 25.0, 120.0, 10.0]
    })

if 'carrito' not in st.session_state:
    st.session_state.carrito = []

if 'ventas_dia' not in st.session_state:
    st.session_state.ventas_dia = []

# 3. Mostrar Inventario
st.subheader("📋 Stock Disponible")
st.dataframe(st.session_state.df_memoria, use_container_width=True, hide_index=True)

st.divider()

# 4. Sección de Ventas (CON RESET SEGURO)
st.subheader("🛒 Armar Pedido")
col1, col2 = st.columns(2)

with col1:
    prod_sel = st.selectbox("Selecciona producto:", st.session_state.df_memoria["Producto"])

with col2:
    # Definimos el valor inicial de la cantidad
    if 'cant_input' not in st.session_state:
        st.session_state.cant_input = 1
    
    cant_sel = st.number_input("Cantidad:", min_value=1, value=st.session_state.cant_input, key="v_cantidad")

if st.button("➕ Agregar al Carrito", type="primary"):
    idx = st.session_state.df_memoria[st.session_state.df_memoria['Producto'] == prod_sel].index[0]
    stock_real = st.session_state.df_memoria.at[idx, 'Stock_Actual']
    
    if cant_sel > stock_real:
        st.error(f"⚠️ ¡Error! No hay stock suficiente. Solo quedan {stock_real} unidades.")
    else:
        precio = st.session_state.df_memoria.at[idx, 'Precio_Venta']
        st.session_state.carrito.append({
            "Producto": prod_sel, 
            "Cant": cant_sel, 
            "Subtotal": cant_sel * precio
        })
        st.success(f"✅ {prod_sel} añadido al carrito.")
        # Aquí reseteamos la cantidad de forma segura
        st.session_state.cant_input = 1
        st.rerun()

# 5. Carrito y Métodos de Pago
if st.session_state.carrito:
    st.divider()
    st.subheader("📝 Artículos en el Carrito")
    df_car = pd.DataFrame(st.session_state.carrito)
    st.table(df_car)
    
    total = df_car['Subtotal'].sum()
    st.write(f"## Total: S/ {total}")
    
    metodo = st.selectbox("Método de Pago:", ["Efectivo", "Yape", "Plin", "Transferencia"])
    
    if st.button("🚀 REGISTRAR VENTA FINAL"):
        for item in st.session_state.carrito:
            idx = st.session_state.df_memoria[st.session_state.df_memoria['Producto'] == item['Producto']].index[0]
            st.session_state.df_memoria.at[idx, 'Stock_Actual'] -= item['Cant']
        
        st.session_state.ventas_dia.append({"Total": total, "Metodo": metodo})
        st.session_state.carrito = [] 
        st.balloons()
        st.rerun()

# 6. Recaudación y Firma 💪
st.divider()
if st.session_state.ventas_dia:
    st.subheader("💰 Recaudación del Día")
    df_v = pd.DataFrame(st.session_state.ventas_dia)
    st.metric("GANANCIA TOTAL", f"S/ {df_v['Total'].sum()}")
    st.dataframe(df_v, use_container_width=True)

st.markdown("<p style='text-align: center; color: #00796b;'>💪 Desarrollado por Alberto Ballarta | Cloud 2026</p>", unsafe_allow_html=True)
