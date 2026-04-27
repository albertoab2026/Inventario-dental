import streamlit as st
import pandas as pd
import boto3
from datetime import datetime, timedelta
import pytz
from boto3.dynamodb.conditions import Attr, Key
from fpdf import FPDF
import time
import re
import urllib.parse
from decimal import Decimal, ROUND_HALF_UP
import io
import uuid

# === CONFIG ===
TABLA_STOCK = st.secrets["tablas"]["stock"]
TABLA_VENTAS = st.secrets["tablas"]["ventas"]
TABLA_MOVS = st.secrets["tablas"]["movs"]
TABLA_TENANTS = st.secrets["tablas"]["tenants"]
TABLA_CIERRES = st.secrets["tablas"]["cierres"]
TABLA_PAGOS = st.secrets["tablas"]["pagos"]
NUMERO_SOPORTE = "51914282688"
YAPE_SOPORTE = "Alberto Ballarta"
DESARROLLADOR = "Alberto Ballarta - Software Engineer"

st.set_page_config(
    page_title="NEXUS BALLARTA - Sistema POS",
    layout="wide",
    page_icon="💎",
    initial_sidebar_state="collapsed",
    menu_items={'About': "NEXUS BALLARTA v3.0 - Sistema de Punto de Venta Empresarial"}
)
tz_peru = pytz.timezone('America/Lima')

# === CSS ENTERPRISE ===
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
        * {font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;}
        html, body, [class*="stApp"], [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            color-scheme: light only!important;
            forced-color-adjust: none!important;
            -webkit-forced-color-adjust: none!important;
        }
     .main {background: linear-gradient(135deg, #667eea 0%, #764ba2 100%)!important;}
     .block-container {
            background: #ffffff!important;
            color: #0f172a!important;
            border-radius: 24px;
            padding: 3rem;
            box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1), 0 10px 10px -5px rgba(0,0,0,0.04);
            border: 1px solid rgba(255,255,255,0.3);
            margin-top: 2rem;
            backdrop-filter: blur(10px);
        }
     .block-container p,.block-container h1,.block-container h2,.block-container h3,
     .block-container h4,.block-container label,.block-container span,
     .stMarkdown,.stText,.stCaption {color: #0f172a!important;}
        h1 {font-weight: 900!important; letter-spacing: -0.03em; font-size: 3rem!important;}
        h2 {font-weight: 800!important; letter-spacing: -0.02em; font-size: 2rem!important;}
        h3 {font-weight: 700!important; letter-spacing: -0.02em; font-size: 1.5rem!important;}
     .hero-login {
            text-align: center;
            padding: 60px 20px 40px 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 20px;
            margin: -3rem -3rem 2rem -3rem;
            color: white;
        }
     .hero-login h1 {
            font-size: 4rem!important;
            font-weight: 900!important;
            margin: 0;
            color: white!important;
            text-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
     .hero-login p {
            font-size: 1.25rem;
            opacity: 0.95;
            margin: 10px 0 0 0;
            color: white!important;
            font-weight: 500;
        }
     .hero-badge {
            display: inline-block;
            background: rgba(255,255,255,0.2);
            backdrop-filter: blur(10px);
            padding: 8px 20px;
            border-radius: 50px;
            font-size: 0.9rem;
            font-weight: 600;
            margin-top: 15px;
            border: 1px solid rgba(255,255,255,0.3);
        }
        div[data-testid="stMetric"] {
            background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)!important;
            padding: 28px;
            border-radius: 16px;
            box-shadow: 0 10px 15px -3px rgba(59,130,246,0.3);
            border: none;
        }
        div[data-testid="stMetric"] label {
            color: rgba(255,255,255,0.9)!important;
            font-weight: 600;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            color: white!important;
            font-size: 42px;
            font-weight: 800;
            letter-spacing: -0.03em;
        }
        div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
            color: #86efac!important;
            font-size: 15px;
            font-weight: 700;
        }
     .stButton>button {
            border-radius: 10px;
            font-weight: 700;
            border: none;
            background: #3b82f6!important;
            color: white!important;
            box-shadow: 0 1px 3px 0 rgba(0,0,0,0.1), 0 1px 2px 0 rgba(0,0,0,0.06);
            height: 52px!important;
            font-size: 16px!important;
            letter-spacing: -0.01em;
            transition: all 0.15s ease;
        }
     .stButton>button:hover {
            background: #2563eb!important;
            box-shadow: 0 10px 15px -3px rgba(59,130,246,0.4);
            transform: translateY(-2px);
        }
     .stButton>button:active {transform: translateY(0px);}
        button[kind="primary"] {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%)!important;
            box-shadow: 0 4px 6px -1px rgba(16,185,129,0.3)!important;
        }
        button[kind="primary"]:hover {
            background: linear-gradient(135deg, #059669 0%, #047857 100%)!important;
            box-shadow: 0 10px 15px -3px rgba(16,185,129,0.4)!important;
        }
     .stTabs [data-baseweb="tab-list"] {
            gap: 6px;
            background: #f1f5f9!important;
            padding: 8px;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
        }
     .stTabs [data-baseweb="tab"] {
            border-radius: 8px;
            padding: 12px 24px;
            font-weight: 600;
            color: #64748b!important;
            font-size: 15px;
            transition: all 0.15s;
        }
     .stTabs [data-baseweb="tab"]:hover {
            color: #334155!important;
            background: rgba(255,255,255,0.5);
        }
     .stTabs [aria-selected="true"] {
            background: white!important;
            color: #0f172a!important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        button[key="btn_yape"] {
            background: linear-gradient(135deg, #720e9e 0%, #5a0b7a 100%)!important;
            color: white!important;
            font-size: 24px!important;
            font-weight: 800!important;
            height: 100px!important;
            border: none!important;
            border-radius: 16px!important;
            box-shadow: 0 10px 15px -3px rgba(114,14,158,0.4)!important;
        }
        button[key="btn_plin"] {
            background: linear-gradient(135deg, #00b9e5 0%, #0094b8 100%)!important;
            color: white!important;
            font-size: 24px!important;
            font-weight: 800!important;
            height: 100px!important;
            border: none!important;
            border-radius: 16px!important;
            box-shadow: 0 10px 15px -3px rgba(0,185,229,0.4)!important;
        }
        button[key="btn_efectivo"] {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%)!important;
            color: white!important;
            font-size: 24px!important;
            font-weight: 800!important;
            height: 100px!important;
            border: none!important;
            border-radius: 16px!important;
            box-shadow: 0 10px 15px -3px rgba(16,185,129,0.4)!important;
        }
        button[key="btn_yape"]:hover, button[key="btn_plin"]:hover, button[key="btn_efectivo"]:hover {
            transform: translateY(-3px);
            box-shadow: 0 20px 25px -5px rgba(0,0,0,0.3)!important;
        }
     .stSelectbox>div {
            background: white!important;
            border: 1px solid #cbd5e1!important;
            border-radius: 10px!important;
            font-weight: 500;
            transition: all 0.15s;
        }
     .stSelectbox>div:hover {border-color: #94a3b8!important;}
     .stSelectbox>div:focus-within {
            border-color: #3b82f6!important;
            box-shadow: 0 0 0 3px rgba(59,130,246,0.1);
        }
     .stSelectbox>div>div>div {color: #0f172a!important; font-weight: 500;}
     .stSelectbox svg {fill: #64748b!important;}
        [data-baseweb="select"] {background-color: white!important;}
        [data-baseweb="select"] > div {background-color: white!important; color: #0f172a!important;}
        [data-baseweb="popover"] {
            background-color: white!important;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1), 0 10px 10px -5px rgba(0,0,0,0.04);
        }
        [data-baseweb="menu"] {background-color: white!important; padding: 8px;}
        [data-baseweb="menu"] li {
            background-color: white!important;
            color: #0f172a!important;
            font-weight: 500;
            border-radius: 8px;
            margin: 2px 0;
        }
        [data-baseweb="menu"] li:hover {background-color: #f1f5f9!important;}
     .stTextInput>div>input,.stNumberInput>div>div>input,.stDateInput input {
            border-radius: 10px;
            border: 1px solid #cbd5e1!important;
            padding: 14px 18px;
            background: white!important;
            color: #0f172a!important;
            font-weight: 500;
            font-size: 15px;
            transition: all 0.15s;
        }
     .stTextInput>div>input:hover,.stNumberInput>div>div>input:hover,.stDateInput input:hover {border-color: #94a3b8!important;}
     .stTextInput>div>input:focus,.stNumberInput>div>div>input:focus,.stDateInput input:focus {
            border-color: #3b82f6!important;
            box-shadow: 0 0 0 3px rgba(59,130,246,0.1);
            outline: none;
        }
        [data-testid="stNumberInput"] {background: white!important;}
        [data-testid="stNumberInput"] input {background-color: white!important; color: #0f172a!important; font-weight: 500;}
        [data-testid="stNumberInput"] button {
            background-color: #f8fafc!important;
            color: #64748b!important;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
        }
        [data-testid="stNumberInput"] button:hover {background-color: #f1f5f9!important; border-color: #cbd5e1;}
     .stSelectbox label,.stTextInput label,.stNumberInput label,.stDateInput label,.stRadio label {
            color: #334155!important;
            font-weight: 600;
            font-size: 14px;
            margin-bottom: 8px;
            display: block;
        }
        [data-testid="stSidebar"] {background: #0f172a!important; border-right: 1px solid #1e293b;}
        [data-testid="stSidebar"] * {color: white!important;}
        [data-testid="stSidebar"].stButton>button {
            background: #3b82f6!important;
            color: white!important;
            font-weight: 600;
            border: none;
            box-shadow: 0 4px 6px -1px rgba(59,130,246,0.3);
        }
        [data-testid="stSidebar"].stButton>button:hover {
            background: #2563eb!important;
            box-shadow: 0 10px 15px -3px rgba(59,130,246,0.4);
        }
        [data-testid="stExpander"] {
            background-color: white!important;
            border: 1px solid #e2e8f0!important;
            border-radius: 14px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        [data-testid="stExpander"] summary {
            background: #f8fafc!important;
            color: #0f172a!important;
            font-weight: 600;
            border-radius: 14px;
            padding: 16px 20px;
            border: none;
            transition: all 0.15s;
        }
        [data-testid="stExpander"] summary:hover {background: #f1f5f9!important;}
        [data-testid="stExpander"] > div {background-color: white!important; padding: 8px 20px 20px 20px;}
     .streamlit-expanderHeader {
            background: #f8fafc!important;
            border-radius: 14px;
            font-weight: 600;
            color: #0f172a!important;
            border: 1px solid #e2e8f0;
        }
     .stAlert {border-radius: 12px; border-left: 4px solid; font-weight: 500; padding: 18px 20px;}
        div[data-testid="stAlert"][data-baseweb="notification"] {background-color: #eff6ff; border-left-color: #3b82f6; color: #1e40af;}
     .stDataFrame {
            border: 1px solid #e2e8f0!important;
            border-radius: 14px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
     .stDataFrame [data-testid="stTable"] {font-size: 14px; font-weight: 500;}
     .stCheckbox {font-weight: 500; color: #334155;}
     .stSuccess {background-color: #f0fdf4; border-left: 4px solid #10b981; color: #065f46; border-radius: 12px; padding: 16px 20px; font-weight: 500;}
     .stError {background-color: #fef2f2; border-left: 4px solid #ef4444; color: #991b1b; border-radius: 12px; padding: 16px 20px; font-weight: 500;}
     .stWarning {background-color: #fffbeb; border-left: 4px solid #f59e0b; color: #92400e; border-radius: 12px; padding: 16px 20px; font-weight: 500;}
     .stInfo {background-color: #eff6ff; border-left: 4px solid #3b82f6; color: #1e40af; border-radius: 12px; padding: 16px 20px; font-weight: 500;}
    </style>
""", unsafe_allow_html=True)

# === CONEXIÓN BD ===
dynamodb = boto3.resource('dynamodb', region_name=st.secrets["aws"]["region_name"])
tabla_stock = dynamodb.Table(TABLA_STOCK)
tabla_ventas = dynamodb.Table(TABLA_VENTAS)
tabla_movs = dynamodb.Table(TABLA_MOVS)
tabla_tenants = dynamodb.Table(TABLA_TENANTS)
tabla_cierres = dynamodb.Table(TABLA_CIERRES)
tabla_pagos = dynamodb.Table(TABLA_PAGOS)

# === FUNCIONES ===
@st.cache_data(ttl=300)
def contarProductosEnBD():
    try:
        return tabla_stock.scan(Select='COUNT')['Count']
    except:
        return 0

def to_decimal(v):
    if v is None or v == '': return Decimal('0.00')
    try:
        return Decimal(str(v)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except:
        return Decimal('0.00')

def obtener_tiempo_peru():
    ahora = datetime.now(tz_peru)
    return ahora.strftime('%d/%m/%Y'), ahora.strftime('%H:%M:%S'), ahora.isoformat()

@st.cache_data(ttl=30)
def cargarDatos():
    res = tabla_stock.scan()
    items = res.get('Items', [])
    for i in items:
        i['Precio_Compra'] = to_decimal(i.get('Precio_Compra', 0))
        i['Precio'] = to_decimal(i.get('Precio', 0))
        i['Stock'] = int(i.get('Stock', 0))
    return pd.DataFrame(items)

def registrar_kardex(producto, cantidad, tipo, total, precio_compra, detalle):
    fecha, hora, uid = obtener_tiempo_peru()
    item = {
        'TenantID': st.session_state.tenant, 'MovID': f"K-{uid}", 'Fecha': fecha, 'FechaISO': datetime.now(tz_peru).strftime('%Y-%m-%d'),
        'Hora': hora, 'Producto': producto, 'Tipo': tipo, 'Cantidad': int(cantidad), 'Total': to_decimal(total),
        'Precio_Compra': to_decimal(precio_compra), 'Metodo': detalle, 'Usuario': st.session_state.usuario
    }
    tabla_movs.put_item(Item=item)

def registrar_cierre(total_ventas, responsable, tipo, detalle, fecha_cierre):
    _, hora, uid = obtener_tiempo_peru()
    item = {
        'TenantID': st.session_state.tenant, 'CierreID': f"C-{uid}", 'Fecha': fecha_cierre, 'Hora': hora,
        'Total_Ventas': to_decimal(total_ventas), 'Responsable': responsable, 'Tipo': tipo, 'Detalle': detalle, 'UsuarioTurno': st.session_state.usuario
    }
    tabla_cierres.put_item(Item=item)

@st.cache_data(ttl=300)
def verificar_estado_pago(tenant_id):
    try:
        res = tabla_pagos.query(KeyConditionExpression=Key('TenantID').eq(tenant_id), ScanIndexForward=False, Limit=1)
        if not res.get('Items'):
            return True, "PRUEBA", datetime.now(tz_peru) + timedelta(days=7), None
        ultimo = res['Items'][0]
        estado = ultimo.get('Estado', 'PENDIENTE')
        plan = ultimo.get('Plan', 'BASICO')
        fecha_fin_str = ultimo.get('Fecha_Fin')
        fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').replace(tzinfo=tz_peru) if fecha_fin_str else None
        if estado == 'PAGADO' and fecha_fin:
            dias = (fecha_fin - datetime.now(tz_peru)).days
            return True, plan, fecha_fin, dias
        return False, plan, fecha_fin, 0
    except:
        return True, "PRUEBA", None, None

def tiene_whatsapp_habilitado():
    _, plan, _, _ = verificar_estado_pago(st.session_state.tenant)
    return plan in ['PRO', 'PREMIUM']

# === ESTADO ===
for k, v in [('usuario', None), ('rol', None), ('tenant', None), ('modo_lectura', False), ('carrito', []), ('confirmar', False), ('boleta', None), ('metodo_pago', '💵 EFECTIVO')]:
    if k not in st.session_state: st.session_state[k] = v

# === LOGIN ===
if not st.session_state.usuario:
    st.markdown("""
        <div class="hero-login">
            <h1>💎 NEXUS</h1>
            <p>Sistema de Punto de Venta Empresarial</p>
            <div class="hero-badge">⚡ Potenciado por AWS Cloud</div>
        </div>
    """, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login"):
            st.subheader("🔐 Iniciar Sesión")
            tid = st.text_input("ID Negocio:", placeholder="Ej: BODEGA_EL_SOL")
            usu = st.text_input("Usuario:", placeholder="DUEÑO o nombre empleado")
            cla = st.text_input("Contraseña:", type="password", placeholder="••••••••")
            if st.form_submit_button("🚀 INGRESAR", use_container_width=True, type="primary"):
                try:
                    res = tabla_tenants.get_item(Key={'TenantID': tid})
                    if 'Item' in res:
                        tenant = res['Item']
                        acceso_valido = False
                        if usu == "DUEÑO" and cla == tenant.get('PasswordDueño'):
                            st.session_state.rol = "DUEÑO"
                            acceso_valido = True
                        else:
                            empleados = tenant.get('Empleados', {})
                            if usu in empleados and cla == empleados[usu]:
                                st.session_state.rol = "EMPLEADO"
                                acceso_valido = True
                        if acceso_valido:
                            st.session_state.usuario = usu
                            st.session_state.tenant = tid
                            st.success(f"✅ Bienvenido {usu}")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Credenciales incorrectas")
                    else:
                        st.error("❌ Negocio no encontrado")
                except:
                    st.error("❌ Error de conexión")
    st.markdown("<div style='text-align:center;color:#64748b;margin-top:50px;padding:20px;'><p style='font-size:14px;font-weight:600;margin:0;'>" + DESARROLLADOR + "</p><p style='font-size:12px;margin:5px 0;'>Sistema POS Empresarial</p></div>", unsafe_allow_html=True)
    st.stop()
# FIN PARTE 1/8
# === VALIDACIÓN DE PAGO ===
tiene_acceso, plan, fecha_fin, dias_restantes = verificar_estado_pago(st.session_state.tenant)
PLAN_ACTUAL = plan
PRECIO_ACTUAL = {'BASICO': 30, 'PRO': 50, 'PREMIUM': 70}.get(plan, 0)

if not tiene_acceso:
    st.error("🚫 SUSCRIPCIÓN VENCIDA")
    st.warning(f"Tu plan {plan} expiró el {fecha_fin.strftime('%d/%m/%Y')}")
    st.info("💳 Realiza tu pago para reactivar el sistema")
    col1, col2 = st.columns(2)
    col1.metric("Plan", plan)
    col2.metric("Precio Mensual", f"S/ {PRECIO_ACTUAL}")
    texto_pago = f"Hola Alberto, soy {st.session_state.usuario} de {st.session_state.tenant}. Quiero renovar mi plan {plan} por S/ {PRECIO_ACTUAL}."
    st.link_button("💬 RENOVAR POR WHATSAPP", f"https://wa.me/{NUMERO_SOPORTE}?text={urllib.parse.quote(texto_pago)}", use_container_width=True, type="primary")
    if st.button("🚪 CERRAR SESIÓN", use_container_width=True):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()
    st.stop()

if dias_restantes is not None and dias_restantes <= 3 and dias_restantes > 0:
    st.warning(f"⚠️ Tu plan {plan} vence en {dias_restantes} días. Renueva pronto para evitar interrupciones.")

df_inv = cargarDatos()

# === HEADER ===
col1, col2, col3 = st.columns([2,1,1])
col1.markdown(f"### 💎 NEXUS - {st.session_state.tenant}")
col2.markdown(f"**Usuario:** {st.session_state.usuario}")
col3.markdown(f"**Plan:** {plan} | **Días:** {dias_restantes if dias_restantes else '∞'}")

MAX_PRODUCTOS_TOTALES = 5000
MAX_STOCK_POR_PRODUCTO = 10000
# FIN PARTE 2/8
tabs_list = ["🛒 VENTA", "📦 STOCK", "📊 REPORTES", "📋 HISTORIAL"]
if st.session_state.rol == "DUEÑO" and not st.session_state.get('modo_lectura', False):
    tabs_list += ["📥 CARGAR", "🛠️ MANT."]
tabs = st.tabs(tabs_list)
# FIN PARTE 3/8

# === TAB VENTA ===
with tabs[0]:
    f_hoy, h_hoy, _ = obtener_tiempo_peru()
    res_cierre = tabla_cierres.query(KeyConditionExpression=Key('TenantID').eq(st.session_state.tenant), FilterExpression=Attr('Fecha').eq(f_hoy) & Attr('UsuarioTurno').eq(st.session_state.usuario))
    ya_cerro = len(res_cierre.get('Items', [])) > 0
    hora_cierre = max([c['Hora'] for c in res_cierre.get('Items', [])]) if ya_cerro else None

    if ya_cerro:
        st.warning(f"⚠️ YA CERRASTE CAJA HOY A LAS {hora_cierre}")
        st.info("Las ventas que hagas ahora son POST-CIERRE. Se sumarán al reporte de mañana.")
        if st.button("🔓 REABRIR CAJA - SOLO DUEÑO", use_container_width=True, key="btn_reabrir_caja") and st.session_state.rol == "DUEÑO":
            for c in res_cierre.get('Items', []):
                tabla_cierres.delete_item(Key={'TenantID': st.session_state.tenant, 'CierreID': c['CierreID']})
            st.success("✅ Caja reabierta"); time.sleep(1); st.rerun()

    if st.session_state.boleta:
        b = st.session_state.boleta
        st.success("✅ VENTA REALIZADA")
        st.markdown(f"""<div style="background:white;color:black;padding:20px;border:2px solid #3b82f6;max-width:350px;margin:auto;font-family:monospace;border-radius:16px;box-shadow:0 10px 15px -3px rgba(59,130,246,0.3);">
            <h3 style="text-align:center;margin:0;color:#3b82f6;">{st.session_state.tenant}</h3>
            <p style="text-align:center;margin:0;">{b['fecha']} {b['hora']}</p><hr style="border-color:#3b82f6;">
            {''.join([f'<div style="display:flex;justify-content:space-between;"><span>{i["Cantidad"]}x {i["Producto"]}</span><span>S/{float(i["Subtotal"]):.2f}</span></div>' for i in b['items']])}
            <hr style="border-color:#3b82f6;"><div style="display:flex;justify-content:space-between;"><span>MÉTODO:</span><span>{b['metodo']}</span></div>
            <div style="display:flex;justify-content:space-between;color:#ef4444;"><span>DESC:</span><span>- S/{float(b['rebaja']):.2f}</span></div>
            <div style="display:flex;justify-content:space-between;font-size:18px;color:#3b82f6;"><b>NETO:</b><b>S/{float(b['t_neto']):.2f}</b></div>""", unsafe_allow_html=True)
        pdf = FPDF(orientation='P', unit='mm', format=(80, 200))
        pdf.add_page()
        pdf.set_font('Courier', 'B', 12)
        pdf.cell(0, 5, st.session_state.tenant, 0, 1, 'C')
        pdf.set_font('Courier', '', 8)
        pdf.cell(0, 4, f"{b['fecha']} {b['hora']}", 0, 1, 'C')
        pdf.cell(0, 2, '-'*40, 0, 1, 'C')
        for i in b['items']:
            nombre = str(i['Producto'])[:15]
            pdf.cell(40, 4, f"{i['Cantidad']}x {nombre}", 0, 0)
            pdf.cell(0, 4, f"S/{float(i['Subtotal']):.2f}", 0, 1, 'R')
        pdf.cell(0, 2, '-'*40, 0, 1, 'C')
        metodo_pdf = str(b['metodo']).replace('🟣 ', '').replace('🔵 ', '').replace('💵 ', '')
        pdf.cell(40, 4, f"METODO:", 0, 0)
        pdf.cell(0, 4, metodo_pdf, 0, 1, 'R')
        pdf.cell(40, 4, f"DESC:", 0, 0)
        pdf.cell(0, 4, f"- S/{float(b['rebaja']):.2f}", 0, 1, 'R')
        pdf.set_font('Courier', 'B', 10)
        pdf.cell(40, 5, f"NETO:", 0, 0)
        pdf.cell(0, 5, f"S/{float(b['t_neto']):.2f}", 0, 1, 'R')
        pdf_output = pdf.output(dest='S').encode('latin-1')

        df_boleta = pd.DataFrame(b['items'])
        df_boleta['Fecha'] = b['fecha']
        df_boleta['Hora'] = b['hora']
        df_boleta['Metodo'] = b['metodo']
        df_boleta['Descuento'] = float(b['rebaja'])
        df_boleta['Total_Neto'] = float(b['t_neto'])
        buf_excel = io.BytesIO()
        with pd.ExcelWriter(buf_excel, engine='openpyxl') as w:
            df_boleta[['Fecha', 'Hora', 'Producto', 'Cantidad', 'Precio', 'Subtotal', 'Metodo', 'Descuento', 'Total_Neto']].to_excel(w, index=False, sheet_name='Ticket')

        col1, col2 = st.columns(2)
        col1.download_button("📄 PDF 80mm", pdf_output, f"Ticket_{b['fecha'].replace('/','')}.pdf", "application/pdf", use_container_width=True, key="btn_pdf_boleta")
        col2.download_button("📊 EXCEL", buf_excel.getvalue(), f"Ticket_{b['fecha'].replace('/','')}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="btn_excel_boleta")

        if tiene_whatsapp_habilitado():
            texto = f"*TICKET - {st.session_state.tenant}*\n{b['fecha']} {b['hora']}\n---\n" + "\n".join([f"{i['Cantidad']}x {i['Producto']} - S/{float(i['Subtotal']):.2f}" for i in b['items']]) + f"\n---\n*TOTAL: S/{float(b['t_neto']):.2f}*\nMetodo: {b['metodo']}"
            st.link_button("📲 WhatsApp", f"https://wa.me/?text={urllib.parse.quote(texto)}", use_container_width=True)
        if st.button("⬅️ NUEVA VENTA", use_container_width=True, key="btn_nueva_venta"): st.session_state.boleta = None; st.rerun()
    else:
        tab_vender, tab_ingreso_emp = st.tabs(["🛒 VENDER", "📦 INGRESAR MERCADERÍA"])

        with tab_vender:
            st.subheader("🛍️ Nueva Venta")
            busq = st.text_input("🔍 Buscar:", key="bv", placeholder="Escribe nombre del producto...").upper()
            ops = []
            for _, f in df_inv.iterrows():
                if busq in str(f['Producto']):
                    est = f"STOCK: {f['Stock']}" if f['Stock'] > 0 else "🚫 AGOTADO"
                    ops.append(f"{f['Producto']} | S/ {f['Precio']:.2f} | {est}")
            col1, col2 = st.columns([3, 1])
            if ops:
                sel = col1.selectbox("Producto:", ops, key="sel_v", placeholder="Busca y selecciona producto")
                p_sel = sel.split(" | ")[0] if sel else None
            else:
                st.info("👆 Escribe arriba para buscar productos")
                sel = None
                p_sel = None
            cant = col2.number_input("Cant:", min_value=1, value=1, key="cant_v")
            if p_sel:
                dp = df_inv[df_inv['Producto'] == p_sel].iloc[0]
                en_carro = sum(i['Cantidad'] for i in st.session_state.carrito if i['Producto'] == p_sel)
                disp = dp.Stock - en_carro
                st.info(f"Disponible: {disp}")
                if st.button("➕ Añadir", use_container_width=True, key="btn_add_carrito"):
                    if cant <= disp:
                        st.session_state.carrito.append({'Producto': p_sel, 'Cantidad': int(cant), 'Precio': to_decimal(dp.Precio), 'Precio_Compra': to_decimal(dp.Precio_Compra), 'Subtotal': to_decimal(dp.Precio) * int(cant)})
                        st.rerun()
                    else: st.error("❌ Sin stock")
            if st.session_state.carrito:
                for idx, item in enumerate(st.session_state.carrito):
                    c1, c2 = st.columns([3,1])
                    c1.write(f"{item['Producto']} x{item['Cantidad']}")
                    c2.write(f"S/{float(item['Subtotal']):.2f}")
                if st.button("🗑️ VACIAR", key="btn_vaciar_carrito"): st.session_state.carrito = []; st.rerun()

                st.write("**Método de Pago:**")
                col_ef, col_yape, col_plin = st.columns(3)

                with col_ef:
                    st.markdown("<div style='text-align:center;font-size:40px;'>💵</div>", unsafe_allow_html=True)
                    if st.button("EFECTIVO", use_container_width=True, type="primary" if st.session_state.metodo_pago=="💵 EFECTIVO" else "secondary", key="btn_efectivo"):
                        st.session_state.metodo_pago = "💵 EFECTIVO"
                        st.rerun()

                with col_yape:
                    st.markdown("<div style='text-align:center;font-size:40px;'>🟣</div>", unsafe_allow_html=True)
                    if st.button("YAPE", use_container_width=True, type="primary" if st.session_state.metodo_pago=="🟣 YAPE" else "secondary", key="btn_yape"):
                        st.session_state.metodo_pago = "🟣 YAPE"
                        st.rerun()

                with col_plin:
                    st.markdown("<div style='text-align:center;font-size:40px;'>🔵</div>", unsafe_allow_html=True)
                    if st.button("PLIN", use_container_width=True, type="primary" if st.session_state.metodo_pago=="🔵 PLIN" else "secondary", key="btn_plin"):
                        st.session_state.metodo_pago = "🔵 PLIN"
                        st.rerun()

                metodo = st.session_state.metodo_pago
                st.markdown(f"<h3 style='text-align:center;color:#3b82f6;'>Seleccionado: {metodo}</h3>", unsafe_allow_html=True)

                rebaja = st.number_input("💸 Descuento:", min_value=0.0, value=0.0, key="num_rebaja")
                total = max(Decimal('0.00'), sum(i['Subtotal'] for i in st.session_state.carrito) - to_decimal(rebaja))
                st.markdown(f"<h1 style='text-align:center;color:#3b82f6;font-size:3rem;'>S/ {float(total):.2f}</h1>", unsafe_allow_html=True)
                if st.button("🚀 FINALIZAR", use_container_width=True, type="primary", key="btn_finalizar"): st.session_state.confirmar = True
                if st.session_state.confirmar:
                    if st.button(f"✅ CONFIRMAR S/ {float(total):.2f}", use_container_width=True, key="btn_confirmar_venta"):
                        f, h, uid = obtener_tiempo_peru()
                        for item in st.session_state.carrito:
                            tabla_stock.update_item(Key={'TenantID': st.session_state.tenant, 'Producto': item['Producto']}, UpdateExpression="SET Stock = Stock - :s", ConditionExpression="Stock >= :s", ExpressionAttributeValues={':s': item['Cantidad']})
                            tabla_ventas.put_item(Item={'TenantID': st.session_state.tenant, 'VentaID': f"V-{uid}", 'Fecha': f, 'Hora': h, 'Producto': item['Producto'], 'Cantidad': int(item['Cantidad']), 'Total': item['Subtotal'], 'Precio_Compra': item['Precio_Compra'], 'Metodo': metodo, 'Rebaja': to_decimal(rebaja), 'Usuario': st.session_state.usuario})
                            registrar_kardex(item['Producto'], item['Cantidad'], "VENTA", item['Subtotal'], item['Precio_Compra'], metodo)
                        st.session_state.boleta = {'items': st.session_state.carrito, 't_neto': total, 'rebaja': to_decimal(rebaja), 'metodo': metodo, 'fecha': f, 'hora': h}
                        st.session_state.carrito = []; st.session_state.confirmar = False; st.rerun()

        with tab_ingreso_emp:
            st.subheader("📦 Registrar Ingreso de Mercadería")
            st.caption("Registra lo que llegó de tu proveedor")

            if not df_inv.empty:
                prod_ingreso = st.selectbox("Producto que llegó:", df_inv['Producto'].tolist(), key="sel_ingreso_emp")

                if prod_ingreso:
                    df_prod = df_inv[df_inv['Producto'] == prod_ingreso].iloc[0]
                    ultimo_pc = float(df_prod['Precio_Compra'])
                    st.info(f"Stock actual: {int(df_prod['Stock'])} unidades | Último costo: S/{ultimo_pc:.2f} | Venta: S/{df_prod['Precio']:.2f}")

                    st.markdown("**📦 DATOS DE LA COMPRA:**")
                    col1, col2 = st.columns(2)
                    unidad_medida = col1.selectbox("Unidad:", ["Unidades", "Docenas", "Cajas", "Paquetes", "Millares"], key="unidad_medida_emp")
                    cantidad = col2.number_input(f"Cantidad:", min_value=1, value=1, key="cant_lote_emp")

                    multiplicador = {"Unidades": 1, "Docenas": 12, "Cajas": 1, "Paquetes": 1, "Millares": 1000}[unidad_medida]

                    if unidad_medida in ["Cajas", "Paquetes"]:
                        unid_x_bulto = st.number_input(f"¿Cuántas unidades trae cada {unidad_medida[:-1]}?", min_value=1, value=50, key="unid_bulto_emp")
                        multiplicador = unid_x_bulto

                    cant_ingreso = cantidad * multiplicador
                    costo_sugerido = ultimo_pc * cant_ingreso

                    usar_ultimo = st.checkbox(f"✓ Usar último costo: S/{ultimo_pc:.2f} c/u → Total: S/{costo_sugerido:.2f}", value=False, key="check_ultimo_emp")

                    if usar_ultimo:
                        precio_total_lote = costo_sugerido
                        st.success(f"✅ Usando último precio: S/{precio_total_lote:.2f}")
                    else:
                        precio_total_lote = st.number_input(f"Costo total S/:", min_value=0.0, value=0.0, key="precio_lote_emp", help="Lo que pagaste por todo según tu factura")

                    nuevo_pc = precio_total_lote / cant_ingreso if cant_ingreso > 0 else 0

                    st.success(f"✅ Total: {cant_ingreso} unidades | Costo unitario: S/{nuevo_pc:.2f}")
                    stock_final = int(df_prod['Stock']) + cant_ingreso
                    st.metric("Stock nuevo", f"{stock_final} unidades")

                    if st.button("📥 REGISTRAR", use_container_width=True, type="primary", key="btn_ingreso_stock_emp"):
                        if stock_final > MAX_STOCK_POR_PRODUCTO:
                            st.error(f"❌ Stock máximo: {MAX_STOCK_POR_PRODUCTO}")
                        else:
                            stock_viejo = int(df_prod['Stock'])
                            pc_viejo = float(df_prod['Precio_Compra'])
                            pc_promedio = ((stock_viejo * pc_viejo) + (cant_ingreso * nuevo_pc)) / stock_final if stock_viejo > 0 else nuevo_pc

                            tabla_stock.update_item(
                                Key={'TenantID': st.session_state.tenant, 'Producto': prod_ingreso},
                                UpdateExpression="SET Stock = :s, Precio_Compra = :pc",
                                ExpressionAttributeValues={':s': stock_final, ':pc': to_decimal(pc_promedio)}
                            )
                            registrar_kardex(prod_ingreso, cant_ingreso, "INGRESO_STOCK", precio_total_lote, nuevo_pc, f"INGRESO_{st.session_state.usuario}")
                            st.success(f"✅ {st.session_state.usuario} ingresó {cant_ingreso} {prod_ingreso} | Nuevo costo: S/{pc_promedio:.2f}")
                            time.sleep(1)
                            st.rerun()
            else:
                st.warning("⚠️ No hay productos")
# FIN PARTE 4/8
# === TAB STOCK - SIN SCROLL + COSTO SOLO DUEÑO ===
with tabs[1]:
    st.subheader("📦 Inventario")

    busq = st.text_input("🔍 Buscar producto por nombre:", key="bs", placeholder="Ej: CUADERNO, LAPIZ, BORRADOR...").upper()

    col1, col2, col3 = st.columns([2,1,1])
    mostrar_todos = col1.checkbox("📋 Ver lista completa", value=False, help="Solo activa si tienes <200 productos")
    filtro_stock = col2.selectbox("Filtrar:", ["Todos", "Stock bajo <5", "Agotados", "Con stock"], key="filtro_stock")

    df_mostrar = df_inv.copy()

    if busq:
        df_mostrar = df_mostrar[df_mostrar['Producto'].str.contains(busq, na=False)]

    if filtro_stock == "Stock bajo <5":
        df_mostrar = df_mostrar[df_mostrar['Stock'] < 5]
    elif filtro_stock == "Agotados":
        df_mostrar = df_mostrar[df_mostrar['Stock'] == 0]
    elif filtro_stock == "Con stock":
        df_mostrar = df_mostrar[df_mostrar['Stock'] > 0]

    if busq or mostrar_todos:
        if not df_mostrar.empty:
            st.caption(f"Mostrando {len(df_mostrar)} de {len(df_inv)} productos totales")

            if len(df_mostrar) > 50:
                page_size = 50
                total_pages = (len(df_mostrar) - 1) // page_size + 1
                page = st.number_input("Página:", min_value=1, max_value=total_pages, value=1, key="page_stock") - 1
                start_idx = page * page_size
                end_idx = start_idx + page_size
                df_pagina = df_mostrar.iloc[start_idx:end_idx]
                st.caption(f"Página {page+1} de {total_pages}")
            else:
                df_pagina = df_mostrar

            if st.session_state.rol == "DUEÑO":
                df_tabla = df_pagina[['Producto', 'Stock', 'Precio_Compra', 'Precio']].copy()
                df_tabla.columns = ['PROD', 'STOCK', 'COSTO', 'VENTA']
                df_tabla['STOCK'] = df_tabla['STOCK'].astype(int)
                column_config = {
                    "PROD": st.column_config.TextColumn("PROD", width="medium"),
                    "STOCK": st.column_config.NumberColumn("STOCK", width="small", format="%d"),
                    "COSTO": st.column_config.NumberColumn("COSTO", width="small", format="S/ %.2f"),
                    "VENTA": st.column_config.NumberColumn("VENTA", width="small", format="S/ %.2f")
                }
                col_order = ["PROD", "STOCK", "COSTO", "VENTA"]
            else:
                df_tabla = df_pagina[['Producto', 'Stock', 'Precio']].copy()
                df_tabla.columns = ['PROD', 'STOCK', 'VENTA']
                df_tabla['STOCK'] = df_tabla['STOCK'].astype(int)
                column_config = {
                    "PROD": st.column_config.TextColumn("PROD", width="large"),
                    "STOCK": st.column_config.NumberColumn("STOCK", width="small", format="%d"),
                    "VENTA": st.column_config.NumberColumn("VENTA", width="medium", format="S/ %.2f")
                }
                col_order = ["PROD", "STOCK", "VENTA"]

            st.dataframe(
                df_tabla,
                use_container_width=True,
                hide_index=True,
                height=400,
                column_config=column_config,
                column_order=col_order
            )

            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as w:
                df_mostrar.to_excel(w, index=False, sheet_name='Inventario')
            st.download_button(
                "📥 DESCARGAR EXCEL FILTRADO",
                buf.getvalue(),
                f"Inventario_{st.session_state.tenant}_{datetime.now(tz_peru).strftime('%Y%m%d')}.xlsx",
                use_container_width=True,
                key="btn_desc_inv"
            )

            bajo = df_mostrar[df_mostrar['Stock'] < 5]
            if not bajo.empty:
                st.warning(f"⚠️ Stock crítico: {len(bajo)} productos con menos de 5 unidades")
                with st.expander("Ver productos con stock bajo"):
                    for idx, row in bajo.iterrows():
                        st.write(f"**{row['Producto']}** - Stock: {int(row['Stock'])}")
        else:
            if busq:
                st.info(f"❌ No se encontró '{busq}'. Prueba con parte del nombre.")
            else:
                st.info("📭 No hay productos con ese filtro")
    else:
        st.info("👆 Escribe arriba para buscar o activa 'Ver lista completa'")
        st.caption(f"Total en BD: {contarProductosEnBD()} productos")

        if not df_inv.empty:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total productos", len(df_inv))
            col2.metric("Agotados", len(df_inv[df_inv['Stock'] == 0]))
            col3.metric("Stock bajo <5", len(df_inv[df_inv['Stock'] < 5]))
            col4.metric("Valor inventario", f"S/ {(df_inv['Stock'] * df_inv['Precio_Compra']).sum():.2f}")

# === TAB REPORTES - GANANCIA SOLO DUEÑO ===
with tabs[2]:
    st.subheader("📊 Reportes del Día")

    col_f1, col_f2 = st.columns([3,1])
    fecha = col_f1.date_input("Selecciona día:", value=datetime.now(tz_peru).date(), key="date_reportes_fix")
    if col_f2.button("🔄 ACTUALIZAR", use_container_width=True, key="btn_actualizar_reportes"):
        st.cache_data.clear()
        st.rerun()

    fecha_iso = fecha.strftime('%Y-%m-%d')
    fecha_sem_pasada = (fecha - timedelta(days=7)).strftime('%Y-%m-%d')

    if st.session_state.rol == "EMPLEADO":
        res_hoy = tabla_movs.query(
            IndexName='TenantID-FechaISO-index',
            KeyConditionExpression=Key('TenantID').eq(st.session_state.tenant) & Key('FechaISO').eq(fecha_iso),
            FilterExpression=Attr('Usuario').eq(st.session_state.usuario) & Attr('Tipo').eq('VENTA')
        )
        res_sem = tabla_movs.query(
            IndexName='TenantID-FechaISO-index',
            KeyConditionExpression=Key('TenantID').eq(st.session_state.tenant) & Key('FechaISO').eq(fecha_sem_pasada),
            FilterExpression=Attr('Usuario').eq(st.session_state.usuario) & Attr('Tipo').eq('VENTA')
        )
        st.info(f"📊 Viendo solo TUS ventas - {st.session_state.usuario}")
    else:
        res_hoy = tabla_movs.query(IndexName='TenantID-FechaISO-index', KeyConditionExpression=Key('TenantID').eq(st.session_state.tenant) & Key('FechaISO').eq(fecha_iso))
        res_sem = tabla_movs.query(IndexName='TenantID-FechaISO-index', KeyConditionExpression=Key('TenantID').eq(st.session_state.tenant) & Key('FechaISO').eq(fecha_sem_pasada))

    items_hoy = res_hoy.get('Items', [])
    df_v = pd.DataFrame([m for m in items_hoy if m.get('Tipo') == 'VENTA'])

    items_sem = res_sem.get('Items', [])
    df_v_sem = pd.DataFrame([m for m in items_sem if m.get('Tipo') == 'VENTA'])

    if df_v.empty:
        st.warning(f"📭 No hay ventas registradas el {fecha.strftime('%d/%m/%Y')}")
        if st.session_state.rol == "EMPLEADO":
            st.caption("Si hiciste ventas hoy, verifica que cerraste la venta correctamente.")
    else:
        df_v = df_v.sort_values('Hora', ascending=False)
        df_v['Total'] = pd.to_numeric(df_v['Total'], errors='coerce').fillna(0)
        df_v['Precio_Compra'] = pd.to_numeric(df_v['Precio_Compra'], errors='coerce').fillna(0)
        df_v['Cantidad'] = pd.to_numeric(df_v['Cantidad'], errors='coerce').fillna(0)
        df_v['Metodo'] = df_v['Metodo'].fillna('').astype(str)
        df_v['Costo'] = df_v['Precio_Compra'] * df_v['Cantidad']
        df_v['Ganancia_Item'] = df_v['Total'] - df_v['Costo']

        vt = df_v['Total'].sum()
        tk = len(df_v)
        tp = vt/tk if tk else 0
        costo_total = df_v['Costo'].sum()
        gn_total = df_v['Ganancia_Item'].sum()

        vt_sem = df_v_sem['Total'].sum() if not df_v_sem.empty else 0
        dif = vt - vt_sem
        pct = (dif / vt_sem * 100) if vt_sem > 0 else 0

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 💰 VENTA TOTAL")
            st.markdown(f"<h1 style='margin:0;font-size:38px;color:#3b82f6;'>S/ {float(vt):.2f}</h1>", unsafe_allow_html=True)
            if dif >= 0:
                st.success(f"↑ {abs(pct):.1f}% vs semana pasada")
            else:
                st.error(f"↓ {abs(pct):.1f}% vs semana pasada")

        with col2:
            if st.session_state.rol == "DUEÑO":
                st.markdown("### 📈 GANANCIA REAL")
                st.markdown(f"<h1 style='margin:0;font-size:38px;color:#10b981;'>S/ {float(gn_total):.2f}</h1>", unsafe_allow_html=True)
                st.info(f"Tickets: {tk} | Ticket Prom: S/{float(tp):.2f} | Margen: {(gn_total/vt*100) if vt > 0 else 0:.1f}%")
            else:
                st.markdown("### 📊 RESUMEN")
                st.markdown(f"<h1 style='margin:0;font-size:38px;color:#10b981;'>{tk} Tickets</h1>", unsafe_allow_html=True)
                st.info(f"Ticket Promedio: S/{float(tp):.2f}")

        st.write("---")

        with st.expander("🧾 VER TICKETS DEL DÍA - MÁS RECIENTE ARRIBA", expanded=True):
            df_tickets = df_v[['Hora', 'Producto', 'Cantidad', 'Total']].copy()
            df_tickets['Cantidad'] = df_tickets['Cantidad'].astype(int)
            df_tickets.columns = ['HORA', 'PROD', 'CANT', 'TOTAL']
            st.dataframe(
                df_tickets,
                use_container_width=True,
                hide_index=True,
                height=350,
                column_config={
                    "HORA": st.column_config.TextColumn("HORA", width="small"),
                    "PROD": st.column_config.TextColumn("PROD", width="medium"),
                    "CANT": st.column_config.NumberColumn("CANT", width="small"),
                    "TOTAL": st.column_config.NumberColumn("TOTAL", width="small", format="S/ %.2f")
                }
            )

        df_ef = df_v[df_v['Metodo'].str.contains('EFECTIVO')]
        df_yape = df_v[df_v['Metodo'].str.contains('YAPE')]
        df_plin = df_v[df_v['Metodo'].str.contains('PLIN')]

        cols = st.columns(3)
        if not df_ef.empty:
            venta_ef = df_ef['Total'].sum()
            gan_ef = df_ef['Ganancia_Item'].sum()
            if st.session_state.rol == "DUEÑO":
                cols[0].metric("💵 EFECTIVO", f"S/ {float(venta_ef):.2f}", f"Ganancia: S/ {float(gan_ef):.2f}")
            else:
                cols[0].metric("💵 EFECTIVO", f"S/ {float(venta_ef):.2f}")

        if not df_yape.empty:
            venta_yape = df_yape['Total'].sum()
            gan_yape = df_yape['Ganancia_Item'].sum()
            if st.session_state.rol == "DUEÑO":
                cols[1].metric("🟣 YAPE", f"S/ {float(venta_yape):.2f}", f"Ganancia: S/ {float(gan_yape):.2f}")
            else:
                cols[1].metric("🟣 YAPE", f"S/ {float(venta_yape):.2f}")

        if not df_plin.empty:
            venta_plin = df_plin['Total'].sum()
            gan_plin = df_plin['Ganancia_Item'].sum()
            if st.session_state.rol == "DUEÑO":
                cols[2].metric("🔵 PLIN", f"S/ {float(venta_plin):.2f}", f"Ganancia: S/ {float(gan_plin):.2f}")
            else:
                cols[2].metric("🔵 PLIN", f"S/ {float(venta_plin):.2f}")
# FIN PARTE 5/8
# === TAB HISTORIAL - DUEÑO Y EMPLEADO - CIERRE PARA AMBOS ===
with tabs[3]:
    st.subheader("📋 Historial Kardex")
    col_f1, col_f2 = st.columns([3,1])
    f_h = col_f1.date_input("Día:", value=datetime.now(tz_peru).date(), key="date_historial_fix")
    if col_f2.button("🔄 ACTUALIZAR", use_container_width=True, key="btn_actualizar_hist"): st.cache_data.clear(); st.rerun()

    fecha_iso_h = f_h.strftime('%Y-%m-%d')

    if st.session_state.rol == "EMPLEADO":
        res_h = tabla_movs.query(
            IndexName='TenantID-FechaISO-index',
            KeyConditionExpression=Key('TenantID').eq(st.session_state.tenant) & Key('FechaISO').eq(fecha_iso_h),
            FilterExpression=Attr('Usuario').eq(st.session_state.usuario)
        )
        st.info(f"📊 Viendo solo TUS movimientos - {st.session_state.usuario}")
    else:
        res_h = tabla_movs.query(IndexName='TenantID-FechaISO-index', KeyConditionExpression=Key('TenantID').eq(st.session_state.tenant) & Key('FechaISO').eq(fecha_iso_h))

    df_h = pd.DataFrame(res_h.get('Items', []))

    if not df_h.empty:
        df_h = df_h.sort_values('Hora', ascending=False)
        df_h['Total'] = pd.to_numeric(df_h['Total'], errors='coerce').fillna(0)
        df_h['Precio_Compra'] = pd.to_numeric(df_h['Precio_Compra'], errors='coerce').fillna(0)
        df_h['Cantidad'] = pd.to_numeric(df_h['Cantidad'], errors='coerce').fillna(0)
        df_h['Usuario'] = df_h['Usuario'].fillna('SISTEMA')
        df_h['Costo'] = df_h['Precio_Compra'] * df_h['Cantidad']
        df_h['Ganancia'] = df_h.apply(lambda r: r['Total'] - r['Costo'] if r['Tipo'] == 'VENTA' else 0, axis=1)

        df_tabla_h = df_h[['Hora', 'Producto', 'Tipo', 'Cantidad', 'Usuario']].copy()
        df_tabla_h['Cantidad'] = df_tabla_h['Cantidad'].astype(int)
        df_tabla_h.columns = ['HORA', 'PROD', 'TIPO', 'CANT', 'USUARIO']

        st.dataframe(
            df_tabla_h,
            use_container_width=True,
            hide_index=True,
            height=400,
            column_config={
                "HORA": st.column_config.TextColumn("HORA", width="small"),
                "PROD": st.column_config.TextColumn("PROD", width="medium"),
                "TIPO": st.column_config.TextColumn("TIPO", width="small"),
                "CANT": st.column_config.NumberColumn("CANT", width="small"),
                "USUARIO": st.column_config.TextColumn("QUIÉN", width="small")
            }
        )

        df_v_h = df_h[df_h['Tipo'] == 'VENTA']
        if not df_v_h.empty:
            vt_h = df_v_h['Total'].sum()
            costo_h = df_v_h['Costo'].sum()
            gn_h = df_v_h['Ganancia'].sum()

            if st.session_state.rol == "DUEÑO":
                col1, col2, col3 = st.columns(3)
                col1.metric("💰 VENTA TOTAL", f"S/ {float(vt_h):.2f}")
                col2.metric("💸 COSTO", f"S/ {float(costo_h):.2f}")
                col3.metric("📈 GANANCIA", f"S/ {float(gn_h):.2f}")
            else:
                col1, col2 = st.columns(2)
                col1.metric("💰 VENTA TOTAL", f"S/ {float(vt_h):.2f}")
                col2.metric("📊 TICKETS", len(df_v_h))

            # CIERRE DE CAJA - TODOS PUEDEN
            st.write("---")
            res_c = tabla_cierres.query(KeyConditionExpression=Key('TenantID').eq(st.session_state.tenant), FilterExpression=Attr('Fecha').eq(f_h.strftime('%d/%m/%Y')) & Attr('UsuarioTurno').eq(st.session_state.usuario))
            ya_c = len(res_c.get('Items', [])) > 0
            if ya_c:
                st.success(f"✅ Ya cerraste caja hoy a las {res_c['Items'][0]['Hora']}")
            else:
                if st.button("🔒 CERRAR CAJA", use_container_width=True, type="primary", key="btn_cerrar_caja"):
                    registrar_cierre(vt_h, st.session_state.usuario, "VENTAS_DEL_DIA", f"Total ventas: S/{float(vt_h):.2f}", f_h.strftime('%d/%m/%Y'))
                    st.success("✅ Caja cerrada"); time.sleep(1); st.rerun()
    else:
        st.info(f"📭 No hay movimientos el {f_h.strftime('%d/%m/%Y')}")
# FIN PARTE 6/8
# === TAB CARGAR - SOLO DUEÑO ===
if st.session_state.rol == "DUEÑO" and not st.session_state.get('modo_lectura', False):
    with tabs[4]:
        st.subheader("📥 Cargar/Actualizar Productos")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**📤 CARGAR EXCEL**")
            st.caption("Columnas: Producto | Precio_Compra | Precio | Stock")
            archivo = st.file_uploader("Excel:", type=['xlsx', 'xls'], key="up_excel")
            if archivo:
                try:
                    df_up = pd.read_excel(archivo)
                    df_up.columns = df_up.columns.str.strip()
                    cols_req = ['Producto', 'Precio_Compra', 'Precio', 'Stock']
                    if all(c in df_up.columns for c in cols_req):
                        st.dataframe(df_up.head(), use_container_width=True, hide_index=True)
                        if st.button("⬆️ CARGAR TODO", use_container_width=True, type="primary", key="btn_cargar_excel"):
                            total = contarProductosEnBD()
                            if total + len(df_up) > MAX_PRODUCTOS_TOTALES:
                                st.error(f"❌ Máximo {MAX_PRODUCTOS_TOTALES} productos")
                            else:
                                progreso = st.progress(0)
                                exitosos = 0
                                for idx, row in df_up.iterrows():
                                    try:
                                        producto = str(row['Producto']).upper().strip()
                                        if not producto: continue
                                        pc = to_decimal(row['Precio_Compra'])
                                        pv = to_decimal(row['Precio'])
                                        stock = int(row['Stock'])
                                        if stock > MAX_STOCK_POR_PRODUCTO:
                                            st.warning(f"⚠️ {producto}: Stock > {MAX_STOCK_POR_PRODUCTO}, se ajusta")
                                            stock = MAX_STOCK_POR_PRODUCTO
                                        tabla_stock.put_item(Item={
                                            'TenantID': st.session_state.tenant,
                                            'Producto': producto,
                                            'Precio_Compra': pc,
                                            'Precio': pv,
                                            'Stock': stock
                                        })
                                        exitosos += 1
                                    except Exception as e:
                                        st.error(f"Error en fila {idx+1}: {e}")
                                    progreso.progress((idx + 1) / len(df_up))
                                st.success(f"✅ {exitosos}/{len(df_up)} productos cargados")
                                st.cache_data.clear()
                                time.sleep(2)
                                st.rerun()
                    else:
                        st.error(f"❌ Faltan columnas: {cols_req}")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

        with col2:
            st.markdown("**➕ AGREGAR PRODUCTO MANUAL**")
            with st.form("form_nuevo_prod"):
                np = st.text_input("Nombre Producto:", key="np").upper()
                npc = st.number_input("Precio Compra:", min_value=0.0, value=0.0, key="npc")
                npv = st.number_input("Precio Venta:", min_value=0.0, value=0.0, key="npv")
                ns = st.number_input("Stock Inicial:", min_value=0, value=0, key="ns")
                if st.form_submit_button("➕ AGREGAR", use_container_width=True, type="primary"):
                    if np:
                        if ns > MAX_STOCK_POR_PRODUCTO:
                            st.error(f"❌ Stock máximo: {MAX_STOCK_POR_PRODUCTO}")
                        else:
                            try:
                                tabla_stock.put_item(Item={
                                    'TenantID': st.session_state.tenant,
                                    'Producto': np,
                                    'Precio_Compra': to_decimal(npc),
                                    'Precio': to_decimal(npv),
                                    'Stock': int(ns)
                                })
                                registrar_kardex(np, ns, "INGRESO_MANUAL", to_decimal(npc) * ns, to_decimal(npc), "CARGA_INICIAL")
                                st.success(f"✅ {np} agregado")
                                st.cache_data.clear()
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error: {e}")
                    else:
                        st.warning("⚠️ Ingresa nombre del producto")

        st.write("---")
        st.markdown("**📋 PLANTILLA EXCEL**")
        df_plantilla = pd.DataFrame({
            'Producto': ['CUADERNO A4', 'LAPIZ 2B', 'BORRADOR'],
            'Precio_Compra': [2.50, 0.50, 0.80],
            'Precio': [4.00, 1.00, 1.50],
            'Stock': [100, 200, 150]
        })
        buf_plantilla = io.BytesIO()
        with pd.ExcelWriter(buf_plantilla, engine='openpyxl') as w:
            df_plantilla.to_excel(w, index=False, sheet_name='Productos')
        st.download_button("📥 DESCARGAR PLANTILLA", buf_plantilla.getvalue(), "Plantilla_NEXUS.xlsx", use_container_width=True, key="btn_plantilla")

# === TAB MANTENIMIENTO - SOLO DUEÑO ===
if st.session_state.rol == "DUEÑO" and not st.session_state.get('modo_lectura', False):
    with tabs[5]:
        st.subheader("🛠️ Mantenimiento del Sistema")

        tab_ajustar, tab_eliminar, tab_empleados = st.tabs(["⚙️ AJUSTAR STOCK", "🗑️ ELIMINAR", "👥 EMPLEADOS"])

        with tab_ajustar:
            st.markdown("**⚙️ Ajustar Stock y Precios**")
            if not df_inv.empty:
                prod_aj = st.selectbox("Producto:", df_inv['Producto'].tolist(), key="sel_ajustar")
                if prod_aj:
                    df_p = df_inv[df_inv['Producto'] == prod_aj].iloc[0]
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Stock Actual", int(df_p['Stock']))
                    col2.metric("Costo Actual", f"S/ {df_p['Precio_Compra']:.2f}")
                    col3.metric("Venta Actual", f"S/ {df_p['Precio']:.2f}")

                    with st.form("form_ajustar"):
                        st.write("**Nuevos valores:**")
                        nuevo_stock = st.number_input("Stock:", min_value=0, value=int(df_p['Stock']), key="nuevo_stock")
                        nuevo_pc = st.number_input("Precio Compra:", min_value=0.0, value=float(df_p['Precio_Compra']), key="nuevo_pc")
                        nuevo_pv = st.number_input("Precio Venta:", min_value=0.0, value=float(df_p['Precio']), key="nuevo_pv")
                        motivo = st.text_input("Motivo del ajuste:", key="motivo_ajuste", placeholder="Ej: Inventario físico, corrección")
                        if st.form_submit_button("💾 GUARDAR CAMBIOS", use_container_width=True, type="primary"):
                            if nuevo_stock > MAX_STOCK_POR_PRODUCTO:
                                st.error(f"❌ Stock máximo: {MAX_STOCK_POR_PRODUCTO}")
                            else:
                                stock_dif = nuevo_stock - int(df_p['Stock'])
                                tabla_stock.update_item(
                                    Key={'TenantID': st.session_state.tenant, 'Producto': prod_aj},
                                    UpdateExpression="SET Stock = :s, Precio_Compra = :pc, Precio = :pv",
                                    ExpressionAttributeValues={
                                        ':s': nuevo_stock,
                                        ':pc': to_decimal(nuevo_pc),
                                        ':pv': to_decimal(nuevo_pv)
                                    }
                                )
                                if stock_dif!= 0:
                                    tipo = "AJUSTE_POSITIVO" if stock_dif > 0 else "AJUSTE_NEGATIVO"
                                    registrar_kardex(prod_aj, abs(stock_dif), tipo, to_decimal(nuevo_pc) * abs(stock_dif), to_decimal(nuevo_pc), motivo or "AJUSTE_MANUAL")
                                st.success(f"✅ {prod_aj} actualizado")
                                st.cache_data.clear()
                                time.sleep(1)
                                st.rerun()

        with tab_eliminar:
            st.markdown("**🗑️ Eliminar Productos**")
            st.warning("⚠️ Esta acción no se puede deshacer")
            if not df_inv.empty:
                prod_del = st.multiselect("Selecciona productos a eliminar:", df_inv['Producto'].tolist(), key="sel_eliminar")
                if prod_del:
                    st.error(f"Vas a eliminar {len(prod_del)} productos:")
                    for p in prod_del:
                        st.write(f"- {p}")
                    if st.button("🗑️ CONFIRMAR ELIMINACIÓN", use_container_width=True, type="primary", key="btn_eliminar"):
                        for p in prod_del:
                            tabla_stock.delete_item(Key={'TenantID': st.session_state.tenant, 'Producto': p})
                        st.success(f"✅ {len(prod_del)} productos eliminados")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()

        with tab_empleados:
            st.markdown("**👥 Gestionar Empleados**")
            try:
                res_tenant = tabla_tenants.get_item(Key={'TenantID': st.session_state.tenant})
                empleados = res_tenant.get('Item', {}).get('Empleados', {})

                if empleados:
                    st.write("**Empleados actuales:**")
                    for emp, pwd in empleados.items():
                        col1, col2 = st.columns([3,1])
                        col1.write(f"👤 {emp}")
                        if col2.button("🗑️", key=f"del_emp_{emp}"):
                            del empleados[emp]
                            tabla_tenants.update_item(
                                Key={'TenantID': st.session_state.tenant},
                                UpdateExpression="SET Empleados = :e",
                                ExpressionAttributeValues={':e': empleados}
                            )
                            st.success(f"✅ {emp} eliminado")
                            time.sleep(1)
                            st.rerun()
                else:
                    st.info("📭 No hay empleados registrados")

                st.write("---")
                with st.form("form_nuevo_empleado"):
                    st.write("**➕ Agregar Empleado**")
                    nuevo_emp = st.text_input("Nombre usuario:", key="nuevo_emp").upper()
                    nueva_pwd = st.text_input("Contraseña:", type="password", key="nueva_pwd_emp")
                    if st.form_submit_button("➕ AGREGAR EMPLEADO", use_container_width=True, type="primary"):
                        if nuevo_emp and nueva_pwd:
                            if nuevo_emp == "DUEÑO":
                                st.error("❌ No puedes usar 'DUEÑO' como nombre")
                            elif nuevo_emp in empleados:
                                st.error("❌ Ese empleado ya existe")
                            else:
                                empleados[nuevo_emp] = nueva_pwd
                                tabla_tenants.update_item(
                                    Key={'TenantID': st.session_state.tenant},
                                    UpdateExpression="SET Empleados = :e",
                                    ExpressionAttributeValues={':e': empleados}
                                )
                                st.success(f"✅ Empleado {nuevo_emp} agregado")
                                time.sleep(1)
                                st.rerun()
                        else:
                            st.warning("⚠️ Completa todos los campos")
            except Exception as e:
                st.error(f"❌ Error: {e}")
# FIN PARTE 7/8
# === SIDEBAR - CERRAR SESIÓN + SOPORTE ===
with st.sidebar:
    st.markdown("### ⚙️ OPCIONES")
    if st.button("🚪 CERRAR SESIÓN", use_container_width=True, key="btn_logout"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

    st.write("---")
    st.markdown("### 💬 SOPORTE")
    texto_soporte = f"Hola Alberto, soy {st.session_state.usuario} de {st.session_state.tenant}. Necesito ayuda con NEXUS."
    st.link_button(
        "📱 WhatsApp Soporte",
        f"https://wa.me/{NUMERO_SOPORTE}?text={urllib.parse.quote(texto_soporte)}",
        use_container_width=True,
        key="btn_soporte"
    )

    if st.session_state.rol == "DUEÑO":
        st.write("---")
        st.markdown("### 💎 PLAN ACTUAL")
        st.info(f"**{PLAN_ACTUAL}**\nS/ {PRECIO_ACTUAL}/mes")
        if dias_restantes:
            if dias_restantes > 7:
                st.success(f"✅ Activo - {dias_restantes} días")
            elif dias_restantes > 3:
                st.warning(f"⚠️ Vence en {dias_restantes} días")
            else:
                st.error(f"🚨 Vence en {dias_restantes} días")

# === FOOTER ===
st.markdown("---")
st.markdown(
    f"""
    <div style='text-align:center;color:#64748b;padding:20px;'>
        <p style='font-size:14px;font-weight:600;margin:0;'>{DESARROLLADOR}</p>
        <p style='font-size:12px;margin:5px 0;'>NEXUS BALLARTA v3.0 - Sistema POS Empresarial</p>
        <p style='font-size:11px;margin:0;opacity:0.7;'>© 2025 - Todos los derechos reservados</p>
    </div>
    """,
    unsafe_allow_html=True
)
# FIN PARTE 8/8 - CÓDIGO COMPLETO
