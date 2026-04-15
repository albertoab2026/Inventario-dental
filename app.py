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

# --- 4. LOGIN ---
if not st.session_state.auth:
    st.markdown("<h1 style='text-align: center;'>🚀 NEXUS BALLARTA SaaS</h1>", unsafe_allow_html=True)
    locales = list(st.secrets.get("auth_multi", {"Demo": ""}).keys())
    local_sel = st.selectbox("Seleccione su Empresa/Local:", locales)
    clave = st.text_input("Contraseña de acceso:", type="password")
    
    if st.button("🔓 Iniciar Sesión", use_container_width=True):
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

# Pestañas solicitadas
tabs = st.tabs(["🛒 VENTA", "📦 STOCK", "📊 REPORTES", "📋 HISTORIAL", "📥 CARGA", "🛠️ MANTENIMIENTO"])

# --- CONSULTA DE DATOS (Tenant Isolation) ---
# Esto extrae solo los productos que pertenecen al local logueado
res_stock = t_stock.scan(FilterExpression=Attr('TenantID').eq(st.session_state.tenant))
df_stock = pd.DataFrame(res_stock.get('Items', []))

# --- PESTAÑA: CARGA ---
with tabs[4]:
    st.subheader("📥 Registro de Productos Nuevos")
    st.info("Usa esta pestaña para subir tus productos por primera vez.")
    with st.form("form_registro"):
        col1, col2 = st.columns(2)
        with col1:
            nom = st.text_input("Nombre del Producto:").upper().strip()
            stk = st.number_input("Stock Inicial:", min_value=0, step=1)
        with col2:
            p_v = st.number_input("Precio Venta (S/):", min_value=0.0)
            p_c = st.number_input("Precio Compra (S/):", min_value=0.0)
        
        if st.form_submit_button("🚀 Guardar Producto"):
            if nom:
                t_stock.put_item(Item={
                    'TenantID': st.session_state.tenant,
                    'Producto': nom,
                    'Stock': int(stk),
                    'Precio': str(p_v),
                    'Precio_Compra': str(p_c)
                })
                st.success(f"✅ {nom} guardado. Ya aparecerá en Ventas y Stock.")
                st.rerun()

# --- PESTAÑA: STOCK ---
with tabs[1]:
    st.subheader("📦 Inventario")
    if not df_stock.empty:
        st.dataframe(df_stock[['Producto', 'Stock', 'Precio']], use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ El inventario está vacío. Por favor, ve a la pestaña 'CARGA' para añadir productos.")

# --- PESTAÑA: VENTA ---
with tabs[0]:
    st.subheader("🛒 Punto de Venta")
    if not df_stock.empty:
        # Solo mostrar productos con stock mayor a 0
        df_con_stock = df_stock[df_stock['Stock'].astype(int) > 0]
        
        if not df_con_stock.empty:
            p_sel = st.selectbox("Seleccione Producto:", df_con_stock['Producto'].tolist())
            datos_p = df_con_stock[df_con_stock['Producto'] == p_sel].iloc[0]
            
            c1, c2 = st.columns(2)
            c1.metric("Precio", f"S/ {datos_p['Precio']}")
            c2.metric("Disponible", datos_p['Stock'])
            
            cant = st.number_input("Cantidad a vender:", min_value=1, max_value=int(datos_p['Stock']), value=1)
            
            if st.button("➕ Añadir al Carrito"):
                st.session_state.carrito.append({
                    'Producto': p_sel, 
                    'Cantidad': int(cant), 
                    'Precio': float(datos_p['Precio']),
                    'Subtotal': round(float(datos_p['Precio']) * cant, 2)
                })
                st.rerun()
        else:
            st.error("No hay productos con stock disponible para vender.")

        if st.session_state.carrito:
            st.markdown("---")
            st.write("### Carrito de Compras")
            df_car = pd.DataFrame(st.session_state.carrito)
            st.table(df_car)
            
            col_f1, col_f2 = st.columns(2)
            if col_f1.button("🗑️ Vaciar Carrito"):
                st.session_state.carrito = []
                st.rerun()
                
            if col_f2.button("🚀 FINALIZAR VENTA", type="primary"):
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
                        ExpressionAttributeValues={':val': int(item['Cantidad'])}
                    )
                
                st.session_state.carrito = []
                st.success("✅ Venta realizada!")
                st.rerun()
    else:
        st.info("No hay productos registrados. Por favor, ve a la pestaña 'CARGA'.")

# --- PESTAÑA: MANTENIMIENTO ---
with tabs[5]:
    st.subheader("🛠️ Gestión de Productos")
    if not df_stock.empty:
        p_mant = st.selectbox("Seleccione producto para gestionar:", df_stock['Producto'].tolist())
        
        c_m1, c_m2 = st.columns(2)
        if c_m1.button("❌ ELIMINAR PRODUCTO", use_container_width=True):
            t_stock.delete_item(Key={'TenantID': st.session_state.tenant, 'Producto': p_mant})
            st.warning(f"Producto {p_mant} eliminado.")
            st.rerun()
        
        st.info("Para editar el precio o stock, simplemente vuelve a cargarlo con el mismo nombre en la pestaña CARGA y se sobrescribirá.")
    else:
        st.write("No hay productos para gestionar.")

# --- PESTAÑAS: REPORTES E HISTORIAL ---
res_ventas = t_ventas.scan(FilterExpression=Attr('TenantID').eq(st.session_state.tenant))
df_ventas = pd.DataFrame(res_ventas.get('Items', []))

with tabs[2]:
    st.subheader("📊 Reportes")
    if not df_ventas.empty:
        total_acumulado = pd.to_numeric(df_ventas['Total']).sum()
        st.metric("Ventas Totales del Local", f"S/ {total_acumulado:.2f}")
    else:
        st.write("Aún no hay ventas registradas.")

with tabs[3]:
    st.subheader("📋 Historial")
    if not df_ventas.empty:
        st.dataframe(df_ventas[['VentaID', 'Fecha', 'Hora', 'Total']], use_container_width=True)
