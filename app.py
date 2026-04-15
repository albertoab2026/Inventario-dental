import streamlit as st
import pandas as pd
import boto3
from datetime import datetime
import pytz
from boto3.dynamodb.conditions import Attr

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="NEXUS BALLARTA SaaS", layout="wide", page_icon="🚀")
tz_peru = pytz.timezone('America/Lima')

def obtener_info_tiempo():
    ahora = datetime.now(tz_peru)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%H:%M:%S"), ahora.strftime("%Y%m%d%H%M%S%f")

# --- 2. CONEXIÓN AWS ---
try:
    dynamodb = boto3.resource(
        'dynamodb',
        region_name=st.secrets["aws"]["aws_region"],
        aws_access_key_id=st.secrets["aws"]["aws_access_key_id"],
        aws_secret_access_key=st.secrets["aws"]["aws_secret_access_key"]
    )
    t_stock = dynamodb.Table('SaaS_Stock_Test')
    t_ventas = dynamodb.Table('SaaS_Ventas_Test')
except Exception as e:
    st.error(f"Error de conexión AWS: {e}")
    st.stop()

# --- 3. GESTIÓN DE SESIÓN ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'tenant' not in st.session_state: st.session_state.tenant = None
if 'carrito' not in st.session_state: st.session_state.carrito = []

# --- 4. LOGIN (Multi-Usuario) ---
if not st.session_state.auth:
    st.markdown("<h1 style='text-align: center;'>🚀 NEXUS BALLARTA SaaS</h1>", unsafe_allow_html=True)
    locales = list(st.secrets.get("auth_multi", {"Demo": ""}).keys())
    local_sel = st.selectbox("Seleccione su Empresa/Local:", locales)
    clave = st.text_input("Contraseña de acceso:", type="password")
    
    if st.button("🔓 Iniciar Sesión", use_container_width=True):
        # Clave maestra definida por el usuario
        if clave == "tiotuinventario":
            st.session_state.auth = True
            st.session_state.tenant = local_sel
            st.rerun()
        else:
            st.error("❌ Contraseña incorrecta")
    st.stop()

# --- 5. INTERFAZ PRINCIPAL ---
st.sidebar.title(f"🏢 {st.session_state.tenant}")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.auth = False
    st.rerun()

# Recuperamos las pestañas que mencionaste
tabs = st.tabs(["🛒 VENTA", "📦 STOCK", "📊 REPORTES", "📋 HISTORIAL", "📥 CARGA"])

# --- PESTAÑA: CARGA (Para alimentar el sistema) ---
with tabs[4]:
    st.subheader("📥 Registro de Productos")
    with st.form("form_registro"):
        col1, col2 = st.columns(2)
        with col1:
            nom = st.text_input("Nombre del Producto:").upper().strip()
            stk = st.number_input("Stock Inicial:", min_value=0, step=1)
        with col2:
            p_v = st.number_input("Precio Venta (S/):", min_value=0.0)
            p_c = st.number_input("Precio Compra (S/):", min_value=0.0)
        
        if st.form_submit_button("Guardar en Inventario"):
            if nom:
                t_stock.put_item(Item={
                    'TenantID': st.session_state.tenant,
                    'Producto': nom,
                    'Stock': int(stk),
                    'Precio': str(p_v),
                    'Precio_Compra': str(p_c)
                })
                st.success(f"✅ {nom} registrado correctamente.")
                st.rerun()

# --- CONSULTA GLOBAL DE DATOS (Solo para este Tenant) ---
res_stock = t_stock.scan(FilterExpression=Attr('TenantID').eq(st.session_state.tenant))
df_stock = pd.DataFrame(res_stock.get('Items', []))

# --- PESTAÑA: STOCK ---
with tabs[1]:
    st.subheader("📦 Inventario Actual")
    if not df_stock.empty:
        st.dataframe(df_stock[['Producto', 'Stock', 'Precio']], use_container_width=True, hide_index=True)
    else:
        st.info("No hay productos en stock. Ve a la pestaña 'CARGA'.")

# --- PESTAÑA: VENTA ---
with tabs[0]:
    st.subheader("🛒 Punto de Venta")
    if not df_stock.empty:
        p_sel = st.selectbox("Seleccione Producto:", df_stock['Producto'].tolist())
        datos_p = df_stock[df_stock['Producto'] == p_sel].iloc[0]
        st.write(f"Precio: S/ {datos_p['Precio']} | Disponible: {datos_p['Stock']}")
        
        cant = st.number_input("Cantidad:", min_value=1, max_value=int(datos_p['Stock']), value=1)
        
        if st.button("➕ Añadir al Carrito"):
            st.session_state.carrito.append({
                'Producto': p_sel, 
                'Cantidad': int(cant), 
                'Precio': float(datos_p['Precio']),
                'Subtotal': round(float(datos_p['Precio']) * cant, 2)
            })
            st.rerun()

        if st.session_state.carrito:
            df_car = pd.DataFrame(st.session_state.carrito)
            st.table(df_car)
            if st.button("🚀 FINALIZAR VENTA"):
                f, h, uid = obtener_info_tiempo()
                total = df_car['Subtotal'].sum()
                
                # 1. Guardar Venta
                t_ventas.put_item(Item={
                    'TenantID': st.session_state.tenant,
                    'VentaID': f"V-{uid}",
                    'Fecha': f,
                    'Hora': h,
                    'Total': str(total),
                    'Detalle': df_car.to_dict('records')
                })
                
                # 2. Descontar Stock
                for item in st.session_state.carrito:
                    t_stock.update_item(
                        Key={'TenantID': st.session_state.tenant, 'Producto': item['Producto']},
                        UpdateExpression="SET Stock = Stock - :val",
                        ExpressionAttributeValues={':val': item['Cantidad']}
                    )
                
                st.session_state.carrito = []
                st.success("Venta procesada con éxito")
                st.rerun()

# --- PESTAÑA: REPORTES Y HISTORIAL (Resumen rápido) ---
res_ventas = t_ventas.scan(FilterExpression=Attr('TenantID').eq(st.session_state.tenant))
df_ventas = pd.DataFrame(res_ventas.get('Items', []))

with tabs[2]:
    st.subheader("📊 Resumen de Caja")
    if not df_ventas.empty:
        total_dia = pd.to_numeric(df_ventas['Total']).sum()
        st.metric("Total Ventas (S/)", f"{total_dia:.2f}")
        st.line_chart(df_ventas.set_index('Hora')['Total'])

with tabs[3]:
    st.subheader("📋 Historial de Movimientos")
    if not df_ventas.empty:
        st.dataframe(df_ventas[['VentaID', 'Fecha', 'Hora', 'Total']], use_container_width=True)
