import streamlit as st
import pandas as pd
import boto3
from datetime import datetime
import pytz
from boto3.dynamodb.conditions import Attr

# --- 0. CONFIGURACIÓN ---
TABLA_STOCK = 'SaaS_Stock_Test'
TABLA_VENTAS = 'SaaS_Ventas_Test'

st.set_page_config(page_title="NEXUS BALLARTA SaaS", layout="wide", page_icon="🚀")
tz_peru = pytz.timezone('America/Lima')

def obtener_tiempo_peru():
    ahora = datetime.now(tz_peru)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%H:%M:%S"), ahora.strftime("%Y%m%d%H%M%S%f")

# --- 1. CONEXIÓN AWS ---
try:
    dynamodb = boto3.resource('dynamodb', 
                              region_name=st.secrets["aws"]["aws_region"],
                              aws_access_key_id=st.secrets["aws"]["aws_access_key_id"],
                              aws_secret_access_key=st.secrets["aws"]["aws_secret_access_key"])
    tabla_stock = dynamodb.Table(TABLA_STOCK)
    tabla_ventas = dynamodb.Table(TABLA_VENTAS)
except Exception as e:
    st.error(f"Error AWS: {e}")
    st.stop()

# --- 2. SESIÓN ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'tenant' not in st.session_state: st.session_state.tenant = None
if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'boleta' not in st.session_state: st.session_state.boleta = None

# --- LOGIN ---
if not st.session_state.auth:
    st.markdown("<h1 style='text-align: center;'>🚀 NEXUS BALLARTA SaaS</h1>", unsafe_allow_html=True)
    auth_multi = st.secrets.get("auth_multi", {"Demo": "tiotuinventario"})
    locales = list(auth_multi.keys())
    local_sel = st.selectbox("Seleccione Local:", locales)
    clave = st.text_input("Contraseña:", type="password")
    if st.button("🔓 Ingresar", use_container_width=True):
        if clave == "tiotuinventario":
            st.session_state.auth = True
            st.session_state.tenant = local_sel
            st.rerun()
        else: st.error("❌ Clave incorrecta")
    st.stop()
def obtener_datos():
    try:
        res = tabla_stock.scan(FilterExpression=Attr('TenantID').eq(st.session_state.tenant))
        items = res.get('Items', [])
        df = pd.DataFrame(items)
        if df.empty: return pd.DataFrame(columns=['Producto', 'Stock', 'Precio', 'Precio_Compra'])
        df['Stock'] = pd.to_numeric(df['Stock'], errors='coerce').fillna(0).astype(int)
        df['Precio'] = pd.to_numeric(df['Precio'], errors='coerce').fillna(0.0)
        df['Precio_Compra'] = pd.to_numeric(df['Precio_Compra'], errors='coerce').fillna(0.0)
        return df[['Producto', 'Stock', 'Precio', 'Precio_Compra']].sort_values('Producto')
    except: return pd.DataFrame(columns=['Producto', 'Stock', 'Precio', 'Precio_Compra'])

df_inv = obtener_datos()

tabs = st.tabs(["🛒 VENTA", "📦 STOCK", "📊 REPORTES", "📋 HISTORIAL", "📥 CARGAR", "🛠️ MANT."])

with tabs[0]:
    if st.session_state.boleta:
        st.success("✅ ¡Venta Realizada!")
        if st.button("⬅️ Nueva Venta"): st.session_state.boleta = None; st.rerun()
    else:
        bus = st.text_input("🔍 Buscar Producto:").upper()
        prod_lista = [p for p in df_inv['Producto'].tolist() if bus in str(p)]
        c1, c2 = st.columns([3, 1])
        with c1: p_sel = st.selectbox("Seleccionar:", prod_lista) if prod_lista else None
        with c2: cant = st.number_input("Cant:", min_value=1, value=1)
        
        if p_sel:
            info = df_inv[df_inv['Producto'] == p_sel].iloc[0]
            st.info(f"Precio: S/ {info['Precio']} | Stock: {info['Stock']}")
            if st.button("➕ Añadir al Carrito"):
                if cant <= info['Stock']:
                    st.session_state.carrito.append({'Producto': p_sel, 'Cantidad': int(cant), 'Precio': float(info['Precio']), 'Precio_Compra': float(info['Precio_Compra']), 'Subtotal': round(float(info['Precio']) * cant, 2)})
                    st.rerun()
                else: st.error("Stock insuficiente")

        if st.session_state.carrito:
            df_c = pd.DataFrame(st.session_state.carrito)
            st.table(df_c[['Producto', 'Cantidad', 'Precio', 'Subtotal']])
            total_b = df_c['Subtotal'].sum()
            st.markdown(f"<h1 style='color:#2ecc71;'>Total: S/ {total_b:.2f}</h1>", unsafe_allow_html=True)
            
            if st.button("🚀 FINALIZAR COMPRA", type="primary", use_container_width=True):
                f, h, uid = obtener_tiempo_peru()
                try:
                    for i, item in enumerate(st.session_state.carrito):
                        # USANDO VentaID (i mayúscula)
                        tabla_ventas.put_item(Item={
                            'TenantID': st.session_state.tenant,
                            'VentaID': f"V-{uid}-{i}", 
                            'Fecha': f, 'Hora': h,
                            'Producto': item['Producto'],
                            'Cantidad': int(item['Cantidad']),
                            'Total': str(item['Subtotal']),
                            'Precio_Compra': str(item['Precio_Compra'])
                        })
                        # Descontar Stock
                        n_s = int(df_inv[df_inv['Producto'] == item['Producto']]['Stock'].values[0]) - item['Cantidad']
                        tabla_stock.update_item(Key={'TenantID': st.session_state.tenant, 'Producto': item['Producto']}, UpdateExpression="SET Stock = :s", ExpressionAttributeValues={':s': n_s})
                    st.session_state.carrito = []; st.session_state.boleta = True; st.rerun()
                except Exception as e: st.error(f"Fallo AWS: {e}")
with tabs[1]:
    st.dataframe(df_inv, use_container_width=True)

with tabs[4]:
    st.subheader("📥 Cargar Producto")
    with st.form("carga"):
        p_n = st.text_input("Producto").upper()
        s_n = st.number_input("Stock", min_value=0)
        pr_n = st.number_input("Precio Venta", min_value=0.0)
        pc_n = st.number_input("Precio Compra", min_value=0.0)
        if st.form_submit_button("Guardar en Nube"):
            if p_n:
                tabla_stock.put_item(Item={'TenantID': st.session_state.tenant, 'Producto': p_n, 'Stock': int(s_n), 'Precio': str(pr_n), 'Precio_Compra': str(pc_n)})
                st.success("Guardado"); st.rerun()

with tabs[5]:
    st.subheader("🛠️ Mantenimiento")
    if not df_inv.empty:
        p_edit = st.selectbox("Editar Producto:", df_inv['Producto'].tolist())
        ns = st.number_input("Nuevo Stock", value=0)
        if st.button("Actualizar Stock"):
            tabla_stock.update_item(Key={'TenantID': st.session_state.tenant, 'Producto': p_edit}, UpdateExpression="SET Stock = :s", ExpressionAttributeValues={':s': int(ns)})
            st.success("Actualizado"); st.rerun()
        if st.button("🗑️ Eliminar Producto"):
            tabla_stock.delete_item(Key={'TenantID': st.session_state.tenant, 'Producto': p_edit})
            st.error("Eliminado"); st.rerun()
