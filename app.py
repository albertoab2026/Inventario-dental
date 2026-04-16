import streamlit as st
import pandas as pd
import boto3
from datetime import datetime
import pytz
import time
from boto3.dynamodb.conditions import Attr

# 0. CONFIGURACIÓN SaaS (DINÁMICA)
# Los nombres de las tablas ahora son los de tu nueva consola SaaS
TABLA_STOCK = 'SaaS_Stock_Test'
TABLA_VENTAS = 'SaaS_Ventas_Test'

# 1. CONFIGURACIÓN E INTERFAZ
st.set_page_config(page_title="NEXUS BALLARTA SaaS", layout="wide", page_icon="🚀")
tz_peru = pytz.timezone('America/Lima')

def obtener_tiempo_peru():
    ahora = datetime.now(tz_peru)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%H:%M:%S"), ahora, ahora.strftime("%Y%m%d%H%M%S%f")

# 2. CONEXIÓN SEGURA AWS
try:
    aws_id = st.secrets["aws"]["aws_access_key_id"]
    aws_key = st.secrets["aws"]["aws_secret_access_key"]
    aws_region = st.secrets["aws"]["aws_region"]
    
    dynamodb = boto3.resource('dynamodb', region_name=aws_region,
                              aws_access_key_id=aws_id,
                              aws_secret_access_key=aws_key)
    
    tabla_stock = dynamodb.Table(TABLA_STOCK)
    tabla_ventas = dynamodb.Table(TABLA_VENTAS)
except Exception as e:
    st.error("Error de conexión con la Nube AWS.")
    st.stop()

# 3. CONTROL DE SESIÓN SaaS
if 'auth' not in st.session_state: st.session_state.auth = False
if 'tenant' not in st.session_state: st.session_state.tenant = None
if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'boleta' not in st.session_state: st.session_state.boleta = None
if 'reset_v' not in st.session_state: st.session_state.reset_v = 0

# --- LOGIN MULTIUSUARIO ---
if not st.session_state.auth:
    st.markdown("<h1 style='text-align: center;'>🚀 NEXUS BALLARTA SaaS</h1>", unsafe_allow_html=True)
    locales = list(st.secrets.get("auth_multi", {"Demo": ""}).keys())
    local_sel = st.selectbox("Seleccione su Empresa/Local:", locales)
    clave = st.text_input("Clave de acceso:", type="password")
    
    if st.button("🔓 Ingresar", use_container_width=True):
        if clave == "tiotuinventario":
            st.session_state.auth = True
            st.session_state.tenant = local_sel
            st.rerun()
        else: 
            time.sleep(2)
            st.error("❌ Clave incorrecta")
    st.stop()

# 4. CARGA DE DATOS FILTRADOS (Solo lo que pertenece al Tenant actual)
def obtener_stock_db():
    try:
        # IMPORTANTE: Solo escaneamos los productos que pertenecen al Tenant logueado
        res = tabla_stock.scan(FilterExpression=Attr('TenantID').eq(st.session_state.tenant))
        items = res.get('Items', [])
        if items:
            df = pd.DataFrame(items)
            df['Stock'] = pd.to_numeric(df['Stock'], errors='coerce').fillna(0).astype(int)
            df['Precio'] = pd.to_numeric(df['Precio'], errors='coerce').fillna(0.0)
            df['Precio_Compra'] = pd.to_numeric(df.get('Precio_Compra', 0), errors='coerce').fillna(0.0)
            return df[['Producto', 'Stock', 'Precio', 'Precio_Compra']].sort_values(by='Producto')
        return pd.DataFrame(columns=['Producto', 'Stock', 'Precio', 'Precio_Compra'])
    except:
        return pd.DataFrame(columns=['Producto', 'Stock', 'Precio', 'Precio_Compra'])

df_stock = obtener_stock_db()

with st.sidebar:
    st.title(f"🏢 {st.session_state.tenant}")
    if st.button("🔴 CERRAR SESIÓN", use_container_width=True):
        st.session_state.auth = False
        st.rerun()

tabs = st.tabs(["🛒 VENTA", "📦 STOCK", "📊 REPORTES", "📋 HISTORIAL", "📥 CARGAR", "🛠️ MANT."])

# 1. PESTAÑA DE VENTAS
with tabs[0]:
    if st.session_state.boleta:
        st.balloons(); st.success("✅ ¡VENTA REALIZADA!")
        b = st.session_state.boleta
        ticket = f"""
        <div style="background-color: white; color: #000; padding: 20px; border: 2px solid #000; border-radius: 10px; max-width: 350px; margin: auto; font-family: monospace;">
            <center><b>{st.session_state.tenant}</b><br>{b['fecha']} {b['hora']}</center>
            <hr style="border-top: 1px dashed black;">
            <table style="width: 100%;">
        """
        for i in b['items']:
            ticket += f"<tr><td>{i['Cantidad']}</td><td>{i['Producto']}</td><td style='text-align: right;'>S/ {i['Subtotal']:.2f}</td></tr>"
        ticket += f"""
            </table>
            <hr style="border-top: 1px dashed black;">
            <div style="text-align: right; font-size: 17px;"><b>TOTAL: S/ {b['total_neto']:.2f}</b></div>
            <center><br>¡Gracias!</center>
        </div>
        """
        st.markdown(ticket, unsafe_allow_html=True)
        if st.button("⬅️ NUEVA VENTA"):
            st.session_state.boleta = None; st.rerun()
    else:
        bus_v = st.text_input("🔍 Buscar producto:").strip().upper()
        prod_filt = [p for p in df_stock['Producto'].tolist() if bus_v in str(p)]
        
        c1, c2 = st.columns([3, 1])
        with c1:
            p_sel = st.selectbox("Producto:", prod_filt) if prod_filt else None
        with c2: 
            cant = st.number_input("Cant:", min_value=1, value=1)
        
        if st.button("➕ AÑADIR") and p_sel:
            info = df_stock[df_stock['Producto'] == p_sel].iloc[0]
            if cant <= info['Stock']:
                st.session_state.carrito.append({
                    'Producto': p_sel, 'Cantidad': int(cant), 
                    'Precio': float(info['Precio']), 'Precio_Compra': float(info['Precio_Compra']),
                    'Subtotal': round(float(info['Precio']) * cant, 2)
                })
                st.rerun()
            else: st.error("Sin stock suficiente")

        if st.session_state.carrito:
            df_c = pd.DataFrame(st.session_state.carrito)
            st.table(df_c[['Producto', 'Cantidad', 'Precio', 'Subtotal']])
            total = df_c['Subtotal'].sum()
            if st.button("🚀 FINALIZAR VENTA"):
                f, h, _, uid = obtener_tiempo_peru()
                st.session_state.boleta = {'fecha': f, 'hora': h, 'items': list(st.session_state.carrito), 'total_neto': total}
                for idx, item in enumerate(st.session_state.carrito):
                    # Actualizar Stock con TenantID
                    nuevo_s = int(df_stock[df_stock['Producto'] == item['Producto']]['Stock'].values[0]) - item['Cantidad']
                    tabla_stock.update_item(
                        Key={'TenantID': st.session_state.tenant, 'Producto': item['Producto']},
                        UpdateExpression="set Stock = :s", ExpressionAttributeValues={':s': nuevo_s}
                    )
                    # Registrar Venta con TenantID
                    tabla_ventas.put_item(Item={
                        'TenantID': st.session_state.tenant, 'VentaID': f"V-{uid}-{idx}",
                        'Fecha': f, 'Hora': h, 'Producto': item['Producto'], 
                        'Cantidad': int(item['Cantidad']), 'Total': str(item['Subtotal']),
                        'Precio_Compra': str(item['Precio_Compra'])
                    })
                st.session_state.carrito = []; st.rerun()

# 2. STOCK
with tabs[1]:
    st.subheader("📦 Inventario")
    st.dataframe(df_stock, use_container_width=True, hide_index=True)

# 3. REPORTES (GANANCIA REAL)
with tabs[2]:
    st.subheader("📊 Ganancias")
    v_data = tabla_ventas.scan(FilterExpression=Attr('TenantID').eq(st.session_state.tenant)).get('Items', [])
    if v_data:
        df_v = pd.DataFrame(v_data)
        df_v['Total'] = pd.to_numeric(df_v['Total'])
        df_v['Precio_Compra'] = pd.to_numeric(df_v['Precio_Compra'])
        df_v['Ganancia'] = df_v['Total'] - (df_v['Precio_Compra'] * pd.to_numeric(df_v['Cantidad']))
        st.metric("GANANCIA TOTAL", f"S/ {df_v['Ganancia'].sum():.2f}")
        st.dataframe(df_v[['Fecha', 'Producto', 'Total', 'Ganancia']], use_container_width=True)

# 4. CARGA MASIVA / INDIVIDUAL
with tabs[4]:
    st.subheader("📥 Cargar Mercadería")
    opcion = st.radio("Método:", ["Individual", "Masiva (Excel)"], horizontal=True)
    if opcion == "Individual":
        with st.form("f_car"):
            p_n = st.text_input("Nombre Producto:").upper()
            s_n = st.number_input("Stock:", min_value=0)
            pv_n = st.number_input("Precio Venta:", min_value=0.0)
            pc_n = st.number_input("Precio Compra:", min_value=0.0)
            if st.form_submit_button("Guardar"):
                tabla_stock.put_item(Item={
                    'TenantID': st.session_state.tenant, 'Producto': p_n,
                    'Stock': int(s_n), 'Precio': str(pv_n), 'Precio_Compra': str(pc_n)
                })
                st.success("Guardado"); st.rerun()
    else:
        file = st.file_uploader("Excel", type=['xlsx'])
        if file and st.button("Subir Masivo"):
            df_m = pd.read_excel(file)
            for _, r in df_m.iterrows():
                tabla_stock.put_item(Item={
                    'TenantID': st.session_state.tenant, 'Producto': str(r['Producto']).upper(),
                    'Stock': int(r['Stock']), 'Precio': str(r['Precio']), 'Precio_Compra': str(r['Precio_Compra'])
                })
            st.success("Carga exitosa"); st.rerun()

# 5. MANTENIMIENTO
with tabs[5]:
    st.subheader("🛠️ Editar")
    if not df_stock.empty:
        p_ed = st.selectbox("Producto a editar:", df_stock['Producto'].tolist())
        item_ed = df_stock[df_stock['Producto'] == p_ed].iloc[0]
        with st.form("f_ed"):
            new_s = st.number_input("Stock:", value=int(item_ed['Stock']))
            new_p = st.number_input("Precio:", value=float(item_ed['Precio']))
            if st.form_submit_button("Actualizar"):
                tabla_stock.update_item(
                    Key={'TenantID': st.session_state.tenant, 'Producto': p_ed},
                    UpdateExpression="set Stock = :s, Precio = :p",
                    ExpressionAttributeValues={':s': int(new_s), ':p': str(new_p)}
                )
                st.rerun()
