import streamlit as st
import pandas as pd
import boto3
from datetime import datetime
import pytz
from boto3.dynamodb.conditions import Attr

# 1. CONFIGURACIÓN DE MARCA
MARCA_SaaS = "NEXUS BALLARTA SaaS"
st.set_page_config(page_title=MARCA_SaaS, layout="wide", page_icon="🚀")

TABLA_VENTAS_NAME = 'SaaS_Ventas_Test'
TABLA_STOCK_NAME = 'SaaS_Stock_Test'
tz_peru = pytz.timezone('America/Lima')

def obtener_tiempo_peru():
    ahora = datetime.now(tz_peru)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%H:%M:%S"), ahora, ahora.strftime("%Y%m%d%H%M%S%f")

# 2. CONEXIÓN AWS
try:
    aws_id = st.secrets["aws"]["aws_access_key_id"].strip()
    aws_key = st.secrets["aws"]["aws_secret_access_key"].strip()
    aws_region = st.secrets["aws"]["aws_region"].strip()
    aws_token = st.secrets["aws"].get("aws_session_token", None)
    
    dynamodb = boto3.resource('dynamodb', region_name=aws_region,
                              aws_access_key_id=aws_id,
                              aws_secret_access_key=aws_key,
                              aws_session_token=aws_token)
    
    tabla_ventas = dynamodb.Table(TABLA_VENTAS_NAME)
    tabla_stock = dynamodb.Table(TABLA_STOCK_NAME)
except Exception as e:
    st.error(f"Error AWS: {e}")
    st.stop()
if 'sesion_iniciada' not in st.session_state: st.session_state.sesion_iniciada = False
if 'tenant_id' not in st.session_state: st.session_state.tenant_id = None
if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'boleta' not in st.session_state: st.session_state.boleta = None
if 'reset_v' not in st.session_state: st.session_state.reset_v = 0
if 'df_stock_local' not in st.session_state: st.session_state.df_stock_local = pd.DataFrame()

def actualizar_stock_local():
    try:
        response = tabla_stock.scan(FilterExpression=Attr('TenantID').eq(st.session_state.tenant_id))
        items = response.get('Items', [])
        if items:
            df = pd.DataFrame(items)
            for col in ['Stock', 'Precio', 'P_Compra_U']:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            df['Stock'] = df['Stock'].astype(int)
            df['Producto'] = df['Producto'].astype(str).str.upper().str.strip()
            st.session_state.df_stock_local = df.sort_values(by='Producto')
        else:
            st.session_state.df_stock_local = pd.DataFrame(columns=['Producto', 'Stock', 'Precio', 'P_Compra_U'])
    except:
        st.session_state.df_stock_local = pd.DataFrame(columns=['Producto', 'Stock', 'Precio', 'P_Compra_U'])

if not st.session_state.sesion_iniciada:
    st.markdown(f"<h1 style='text-align: center;'>{MARCA_SaaS}</h1>", unsafe_allow_html=True)
    auth_multi = st.secrets.get("auth_multi", {})
    local_sel = st.selectbox("Empresa:", list(auth_multi.keys()))
    clave = st.text_input("Contraseña:", type="password")
    if st.button("🔓 Entrar", use_container_width=True):
        if local_sel in auth_multi and clave == auth_multi[local_sel].strip():
            st.session_state.sesion_iniciada = True
            st.session_state.tenant_id = local_sel
            actualizar_stock_local()
            st.rerun()
        else: st.error("Clave incorrecta")
    st.stop()
if 'sesion_iniciada' not in st.session_state: st.session_state.sesion_iniciada = False
if 'tenant_id' not in st.session_state: st.session_state.tenant_id = None
if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'boleta' not in st.session_state: st.session_state.boleta = None
if 'reset_v' not in st.session_state: st.session_state.reset_v = 0
if 'df_stock_local' not in st.session_state: st.session_state.df_stock_local = pd.DataFrame()

def actualizar_stock_local():
    try:
        response = tabla_stock.scan(FilterExpression=Attr('TenantID').eq(st.session_state.tenant_id))
        items = response.get('Items', [])
        if items:
            df = pd.DataFrame(items)
            for col in ['Stock', 'Precio', 'P_Compra_U']:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            df['Stock'] = df['Stock'].astype(int)
            df['Producto'] = df['Producto'].astype(str).str.upper().str.strip()
            st.session_state.df_stock_local = df.sort_values(by='Producto')
        else:
            st.session_state.df_stock_local = pd.DataFrame(columns=['Producto', 'Stock', 'Precio', 'P_Compra_U'])
    except:
        st.session_state.df_stock_local = pd.DataFrame(columns=['Producto', 'Stock', 'Precio', 'P_Compra_U'])

if not st.session_state.sesion_iniciada:
    st.markdown(f"<h1 style='text-align: center;'>{MARCA_SaaS}</h1>", unsafe_allow_html=True)
    auth_multi = st.secrets.get("auth_multi", {})
    local_sel = st.selectbox("Empresa:", list(auth_multi.keys()))
    clave = st.text_input("Contraseña:", type="password")
    if st.button("🔓 Entrar", use_container_width=True):
        if local_sel in auth_multi and clave == auth_multi[local_sel].strip():
            st.session_state.sesion_iniciada = True
            st.session_state.tenant_id = local_sel
            actualizar_stock_local()
            st.rerun()
        else: st.error("Clave incorrecta")
    st.stop()
with st.sidebar:
    st.title(MARCA_SaaS)
    st.write(f"🏢 {st.session_state.tenant_id}")
    if st.button("🔴 CERRAR SESIÓN"):
        st.session_state.sesion_iniciada = False
        st.rerun()

tabs = st.tabs(["🛒 VENTA", "📦 STOCK", "📊 REPORTES", "📋 HISTORIAL", "📥 CARGAR", "🛠️ MANT."])
df_stock = st.session_state.df_stock_local

with tabs[0]:
    if st.session_state.boleta:
        b = st.session_state.boleta
        st.success("✅ VENTA REALIZADA")
        if st.button("⬅️ NUEVA VENTA"): st.session_state.boleta = None; st.rerun()
    else:
        st.subheader("Ventas")
        bus_v = st.text_input("🔍 Buscar:").upper()
        prod_filt = [p for p in df_stock['Producto'].tolist() if bus_v in p]
        if prod_filt:
            p_sel = st.selectbox("Producto:", prod_filt, key=f"v_{st.session_state.reset_v}")
            info = df_stock[df_stock['Producto'] == p_sel].iloc[0]
            cant = st.number_input("Cantidad:", min_value=1, value=1)
            if st.button("➕ AÑADIR"):
                if cant <= info['Stock']:
                    st.session_state.carrito.append({'Producto': p_sel, 'Cantidad': int(cant), 'Precio': float(info['Precio']), 'Subtotal': round(float(info['Precio']) * cant, 2), 'TenantID': st.session_state.tenant_id})
                    st.session_state.reset_v += 1; st.rerun()
                else: st.error("Sin stock")
        if st.session_state.carrito:
            st.table(pd.DataFrame(st.session_state.carrito)[['Producto', 'Cantidad', 'Subtotal']])
            if st.button("🚀 FINALIZAR"):
                f, h, dt, idv = obtener_tiempo_peru()
                total = sum(i['Subtotal'] for i in st.session_state.carrito)
                # Guardar venta
                tabla_ventas.put_item(Item={'VentaID': idv, 'TenantID': st.session_state.tenant_id, 'Fecha': f, 'Total': str(total), 'Items': str(st.session_state.carrito)})
                # Descontar stock
                for item in st.session_state.carrito:
                    tabla_stock.update_item(Key={'Producto': item['Producto'], 'TenantID': st.session_state.tenant_id}, UpdateExpression="SET Stock = Stock - :v", ExpressionAttributeValues={':v': item['Cantidad']})
                st.session_state.boleta = {'fecha': f, 'total_neto': total}; st.session_state.carrito = []; actualizar_stock_local(); st.rerun()
with tabs[4]:
    st.subheader("📥 Cargar Productos")
    c1, c2 = st.columns(2)
    with c1:
        with st.form("f_manual"):
            n = st.text_input("Nombre:").upper().strip()
            s = st.number_input("Stock:", min_value=0)
            pv = st.number_input("Precio Venta:", min_value=0.0)
            pc = st.number_input("Precio Compra:", min_value=0.0)
            if st.form_submit_button("Guardar"):
                if n:
                    tabla_stock.put_item(Item={'Producto': n, 'TenantID': st.session_state.tenant_id, 'Stock': int(s), 'Precio': str(pv), 'P_Compra_U': str(pc)})
                    st.success("Guardado"); actualizar_stock_local(); st.rerun()
    with c2:
        archivo = st.file_uploader("Subir CSV/Excel:", type=['csv', 'xlsx'])
        if archivo:
            df_m = pd.read_csv(archivo) if archivo.name.endswith('.csv') else pd.read_excel(archivo)
            df_m['Producto'] = df_m['Producto'].astype(str).str.upper().str.strip()
            df_m = df_m.drop_duplicates(subset=['Producto']) # EVITA EL ERROR DE DUPLICADOS
            if st.button("🚀 SUBIR MASIVO"):
                with tabla_stock.batch_writer() as batch:
                    for _, r in df_m.iterrows():
                        batch.put_item(Item={'Producto': r['Producto'], 'TenantID': st.session_state.tenant_id, 'Stock': int(r.get('Stock', 0)), 'Precio': str(r.get('Precio', 0)), 'P_Compra_U': str(r.get('P_Compra_U', 0))})
                st.success("Carga lista"); actualizar_stock_local(); st.rerun()
with tabs[1]: st.dataframe(df_stock, use_container_width=True)
with tabs[2]: st.info("📊 Reportes próximamente.")
with tabs[3]: st.info("📋 Historial próximamente.")

with tabs[5]:
    st.subheader("🛠️ Gestión")
    if not df_stock.empty:
        pm = st.selectbox("Elegir:", df_stock['Producto'].tolist())
        im = df_stock[df_stock['Producto'] == pm].iloc[0]
        if st.button("🔄 ACTUALIZAR PRECIOS"):
            tabla_stock.update_item(Key={'Producto': pm, 'TenantID': st.session_state.tenant_id}, UpdateExpression="SET Precio = :v", ExpressionAttributeValues={':v': str(im['Precio'])})
            st.success("Actualizado"); actualizar_stock_local(); st.rerun()
        if st.button("❌ ELIMINAR"):
            tabla_stock.delete_item(Key={'Producto': pm, 'TenantID': st.session_state.tenant_id})
            st.error("Eliminado"); actualizar_stock_local(); st.rerun()
