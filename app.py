import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# 1. Configuración Pro y Hora de Perú
st.set_page_config(page_title="Inventario Dental Pro", layout="wide")
st.markdown("<h1 style='text-align: center; color: #00acc1;'>🦷 SISTEMA DENTAL - CONTROL DE VENTAS</h1>", unsafe_allow_html=True)

# Función para obtener hora de Perú (UTC-5)
def obtener_hora_peru():
    return (datetime.utcnow() - timedelta(hours=5)).strftime("%H:%M:%S")

# 2. Memorias del Sistema
if 'df_memoria' not in st.session_state:
    st.session_state.df_memoria = pd.DataFrame({
        "Producto": ["Resina Z350", "Guantes Nitrilo", "Adhesivo Dental", "Algodón en rollo"],
        "Stock_Actual": [10, 40, 5, 30],
        "Precio_Venta": [85.0, 25.0, 120.0, 10.0]
    })
if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'ventas_dia' not in st.session_state: st.session_state.ventas_dia = []

# 3. Stock Disponible
st.subheader("📋 Stock Disponible")
df_mostrar = st.session_state.df_memoria.copy()
df_mostrar['Precio_Venta'] = df_mostrar['Precio_Venta'].map('S/ {:,.2f}'.format)
st.dataframe(df_mostrar, use_container_width=True, hide_index=True)

st.divider()

# 4. Armar Pedido
st.subheader("🛒 Armar Pedido")
col1, col2 = st.columns(2)
with col1:
    prod_sel = st.selectbox("Selecciona producto:", st.session_state.df_memoria["Producto"])
with col2:
    if 'c_reset' not in st.session_state: st.session_state.c_reset = 1
    cant_sel = st.number_input("Cantidad:", min_value=1, value=st.session_state.c_reset, key="input_c")

if st.button("➕ Agregar al Carrito", type="primary"):
    idx = st.session_state.df_memoria[st.session_state.df_memoria['Producto'] == prod_sel].index[0]
    stock_dispo = st.session_state.df_memoria.at[idx, 'Stock_Actual']
    
    if cant_sel > stock_dispo:
        st.error(f"⚠️ ¡No hay stock suficiente! Solo quedan {stock_dispo} unidades de {prod_sel}.")
    else:
        precio = st.session_state.df_memoria.at[idx, 'Precio_Venta']
        st.session_state.carrito.append({"Producto": prod_sel, "Cant": cant_sel, "Subtotal": cant_sel * precio})
        st.success(f"✅ Añadido: {prod_sel}")
        st.session_state.c_reset = 1
        st.rerun()

# 5. Gestión de Carrito
if st.session_state.carrito:
    st.divider()
    st.subheader("📝 Pedido Actual")
    df_car = pd.DataFrame(st.session_state.carrito)
    st.table(df_car.style.format({"Subtotal": "S/ {:.2f}"}))
    
    total = df_car['Subtotal'].sum()
    st.write(f"### Total a Cobrar: S/ {total:,.2f}")

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🗑️ Borrar Último", use_container_width=True):
            st.session_state.carrito.pop()
            st.rerun()
    with c2:
        if st.button("❌ Vaciar Carrito", use_container_width=True):
            st.session_state.carrito = []
            st.rerun()
    with c3:
        metodo = st.selectbox("Pago:", ["Efectivo", "Yape", "Plin"])

    if st.button("🚀 REGISTRAR VENTA FINAL", type="primary", use_container_width=True):
        for item in st.session_state.carrito:
            idx = st.session_state.df_memoria[st.session_state.df_memoria['Producto'] == item['Producto']].index[0]
            st.session_state.df_memoria.at[idx, 'Stock_Actual'] -= item['Cant']
        
        # Guardamos la venta con número y hora de Perú
        n_venta = len(st.session_state.ventas_dia) + 1
        st.session_state.ventas_dia.append({
            "N°": n_venta,
            "Hora": obtener_hora_peru(),
            "Total": total,
            "Metodo": metodo
        })
        st.session_state.carrito = []
        st.balloons()
        st.rerun()

# 6. Recaudación Enumerada
st.divider()
if st.session_state.ventas_dia:
    st.subheader(f"💰 Recaudación del Día ({obtener_hora_peru()})")
    df_v = pd.DataFrame(st.session_state.ventas_dia)
    st.metric("GANANCIA TOTAL", f"S/ {df_v['Total'].sum():,.2f}")
    # Mostramos la tabla enumerada
    st.dataframe(df_v, use_container_width=True, hide_index=True)

st.markdown("<p style='text-align: center; color: #00796b;'>💪 Desarrollado por Alberto Ballarta | Carabayllo - Cloud 2026</p>", unsafe_allow_html=True)
