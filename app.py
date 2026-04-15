import streamlit as st
import pandas as pd
import boto3
from datetime import datetime
import pytz
import time
from boto3.dynamodb.conditions import Attr

# ==========================================
# 1. CONFIGURACIÓN DE MARCA Y PÁGINA
# ==========================================
MARCA_SaaS = "NEXUS BALLARTA SaaS"
st.set_page_config(page_title=MARCA_SaaS, layout="wide", page_icon="🚀")

# --- AJUSTE GLOBAL DE TIEMPO PERÚ ---
tz_peru = pytz.timezone('America/Lima')

def obtener_tiempo_peru():
    ahora = datetime.now(tz_peru)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%H:%M:%S"), ahora, ahora.strftime("%Y%m%d%H%M%S%f")

# ==========================================
# 2. CONEXIÓN SEGURA AWS
# ==========================================
try:
    if "aws" not in st.secrets:
        st.error("⚠️ Error: Credenciales AWS no encontradas.")
        st.stop()
        
    aws_id = st.secrets["aws"]["aws_access_key_id"].strip()
    aws_key = st.secrets["aws"]["aws_secret_access_key"].strip()
    aws_region = st.secrets["aws"]["aws_region"].strip()
    
    dynamodb = boto3.resource('dynamodb', region_name=aws_region,
                              aws_access_key_id=aws_id,
                              aws_secret_access_key=aws_key)
    
    tabla_ventas = dynamodb.Table('SaaS_Ventas_Test')
    tabla_stock = dynamodb.Table('SaaS_Stock_Test')
    tabla_auditoria = dynamodb.Table('SaaS_Audit_Test')
except Exception as e:
    st.error(f"❌ Error de conexión AWS: {e}")
    st.stop()

# ==========================================
# 3. CONTROL DE ESTADOS
# ==========================================
if 'sesion_iniciada' not in st.session_state: st.session_state.sesion_iniciada = False
if 'tenant_id' not in st.session_state: st.session_state.tenant_id = None
if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'boleta' not in st.session_state: st.session_state.boleta = None
if 'reset_v' not in st.session_state: st.session_state.reset_v = 0
if 'df_stock_local' not in st.session_state: st.session_state.df_stock_local = None

def actualizar_stock_local():
    try:
        response = tabla_stock.scan(FilterExpression=Attr('TenantID').eq(st.session_state.tenant_id))
        items = response.get('Items', [])
        if items:
            df = pd.DataFrame(items)
            for col in ['Stock', 'Precio', 'P_Compra_U']:
                if col not in df.columns: df[col] = 0
            df['Stock'] = pd.to_numeric(df['Stock'], errors='coerce').fillna(0).astype(int)
            df['Precio'] = pd.to_numeric(df['Precio'], errors='coerce').fillna(0.0)
            df['Producto'] = df['Producto'].astype(str).str.upper().strip()
            st.session_state.df_stock_local = df.groupby('Producto').agg({'Stock': 'sum', 'Precio': 'max', 'P_Compra_U': 'max'}).reset_index()
        else:
            st.session_state.df_stock_local = pd.DataFrame(columns=['Producto', 'Stock', 'Precio', 'P_Compra_U'])
    except:
        st.session_state.df_stock_local = pd.DataFrame(columns=['Producto', 'Stock', 'Precio', 'P_Compra_U'])

# ==========================================
# 4. PANTALLA DE LOGIN (CORRECCIÓN MODO OSCURO)
# ==========================================
if not st.session_state.sesion_iniciada:
    # Título principal con color adaptable
    st.markdown(f"""
        <div style='text-align: center; padding: 10px;'>
            <h1 style='color: #3498DB; font-family: sans-serif; margin-bottom: 0;'>{MARCA_SaaS}</h1>
            <p style='color: #7FB3D5;'>Cloud Inventory Management</p>
        </div>
    """, unsafe_allow_html=True)
    
    if "auth_multi" in st.secrets:
        locales_disponibles = list(st.secrets["auth_multi"].keys())
    else:
        st.error("Configure [auth_multi] en sus Secrets.")
        st.stop()

    col_l, col_r = st.columns([1, 1])
    with col_l:
        st.subheader("🔑 Acceso Seguro")
        local_sel = st.selectbox("Seleccione su Empresa:", locales_disponibles)
        clave = st.text_input("Contraseña de Acceso:", type="password")
        
        if st.button("🔓 Entrar al Sistema", use_container_width=True):
            pass_correcta = st.secrets["auth_multi"][local_sel].strip()
            if clave == pass_correcta:
                st.session_state.sesion_iniciada = True
                st.session_state.tenant_id = local_sel
                actualizar_stock_local()
                st.rerun()
            else:
                with st.spinner("Verificando..."): time.sleep(1)
                st.error("❌ Credenciales inválidas.")
    
    with col_r:
        # Recuadro informativo con colores que funcionan en Light y Dark Mode
        st.markdown(f"""
            <div style='background-color: rgba(52, 152, 219, 0.1); padding: 25px; border-radius: 10px; border: 1px solid #3498DB;'>
                <h4 style='color: #3498DB; margin-top: 0;'>Bienvenido a Nexus Ballarta</h4>
                <p style='font-size: 0.95em;'>Usted está accediendo a un entorno <b>SaaS Multi-inquilino</b>.</p>
                <ul style='font-size: 0.85em;'>
                    <li>Seguridad por aislamiento de datos.</li>
                    <li>Respaldo automático en AWS Cloud.</li>
                    <li>Soporte técnico 24/7 activado.</li>
                </ul>
                <p style='font-size: 0.8em; color: #7FB3D5;'>ID de Sesión: {local_sel if local_sel else "Esperando..."}</p>
            </div>
        """, unsafe_allow_html=True)
    st.stop()

# ==========================================
# 5. INTERFAZ PRINCIPAL
# ==========================================
with st.sidebar:
    st.markdown(f"<h2 style='color: #3498DB;'>{MARCA_SaaS}</h2>", unsafe_allow_html=True)
    st.write(f"🏢 **Local:** {st.session_state.tenant_id}")
    st.divider()
    if st.button("🔴 CERRAR SESIÓN", use_container_width=True):
        st.session_state.sesion_iniciada = False
        st.rerun()

tabs = st.tabs(["🛒 VENTAS", "📦 STOCK", "📊 REPORTES", "📋 HISTORIAL"])
df_stock = st.session_state.df_stock_local

with tabs[0]:
    if st.session_state.boleta:
        st.balloons()
        b = st.session_state.boleta
        st.markdown(f"""
            <div style="background-color: white; color: black; padding: 20px; border: 2px solid #333; font-family: monospace; max-width: 320px; margin: auto;">
                <center><h3>{st.session_state.tenant_id}</h3><p>{b['fecha']}</p></center><hr>
                {"".join([f"<p>{i['Cantidad']} x {i['Producto']} - S/ {i['Subtotal']:.2f}</p>" for i in b['items']])}
                <hr><h3>TOTAL: S/ {b['total_neto']:.2f}</h3>
            </div>
        """, unsafe_allow_html=True)
        if st.button("NUEVA VENTA", use_container_width=True):
            st.session_state.boleta = None
            st.rerun()
    else:
        st.subheader("🛒 Punto de Venta")
        bus_v = st.text_input("🔍 Buscar Producto:", key="bus_v").upper()
        prod_filt = [p for p in df_stock['Producto'].tolist() if bus_v in p]
        
        c1, c2 = st.columns(2)
        with c1:
            if prod_filt:
                p_sel = st.selectbox("Seleccione:", prod_filt, key=f"sel_{st.session_state.reset_v}")
                info = df_stock[df_stock['Producto'] == p_sel].iloc[0]
                st.write(f"Stock: **{info['Stock']}** | Precio: **S/ {info['Precio']:.2f}**")
            else: st.warning("Sin resultados.")
        with c2:
            cant = st.number_input("Cantidad:", min_value=1, value=1)

        if st.button("➕ AÑADIR", use_container_width=True) and prod_filt:
            if cant <= info['Stock']:
                st.session_state.carrito.append({
                    'Producto': p_sel, 'Cantidad': int(cant), 'Precio': float(info['Precio']),
                    'P_Compra_U': float(info['P_Compra_U']), 'Subtotal': round(float(info['Precio']) * cant, 2),
                    'TenantID': st.session_state.tenant_id
                })
                st.session_state.reset_v += 1
                st.rerun()
            else: st.error("No hay stock suficiente.")

        if st.session_state.carrito:
            df_c = pd.DataFrame(st.session_state.carrito)
            st.table(df_c[['Producto', 'Cantidad', 'Subtotal']])
            if st.button("🚀 FINALIZAR VENTA", use_container_width=True):
                f, h, dt, idv = obtener_tiempo_peru()
                total = df_c['Subtotal'].sum()
                try:
                    tabla_ventas.put_item(Item={'VentaID': idv, 'TenantID': st.session_state.tenant_id, 'Fecha': f, 'Total': str(total), 'Items': st.session_state.carrito})
                    for item in st.session_state.carrito:
                        tabla_stock.update_item(Key={'Producto': item['Producto']}, UpdateExpression="SET Stock = Stock - :v", ExpressionAttributeValues={':v': item['Cantidad']})
                    st.session_state.boleta = {'fecha': f, 'items': st.session_state.carrito, 'total_neto': total}
                    st.session_state.carrito = []; actualizar_stock_local(); st.rerun()
                except Exception as e: st.error(f"Error AWS: {e}")

with tabs[1]:
    st.subheader("📦 Inventario")
    with st.expander("➕ Nuevo Producto"):
        with st.form("f_stock"):
            np = st.text_input("Nombre:").upper().strip()
            ns = st.number_input("Stock:", min_value=0)
            nv = st.number_input("Precio Venta:", min_value=0.0)
            nc = st.number_input("Precio Compra:", min_value=0.0)
            if st.form_submit_button("Guardar"):
                if np:
                    tabla_stock.put_item(Item={'Producto': np, 'TenantID': st.session_state.tenant_id, 'Stock': int(ns), 'Precio': str(nv), 'P_Compra_U': str(nc)})
                    st.success("Guardado"); actualizar_stock_local(); st.rerun()
    st.dataframe(df_stock, use_container_width=True)

with tabs[2]: st.info("📊 Reportes Nexus disponibles próximamente.")
with tabs[3]: st.info("📋 Historial de transacciones por local.")
