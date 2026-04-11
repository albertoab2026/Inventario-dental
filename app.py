import streamlit as st
import pandas as pd
import boto3
from datetime import datetime
import pytz
import time

# 1. CONFIGURACIÓN Y ESTILO PARA QUITAR EL CUADRO GRIS
st.set_page_config(page_title="Dental BALLARTA", layout="wide")

# Este bloque de abajo es el "secreto" para que no salgan cuadros negros/grises
st.markdown("""
    <style>
    .stMarkdown {
        display: flex;
        justify-content: center;
    }
    </style>
    """, unsafe_allow_html=True)

def obtener_tiempo_peru():
    tz_peru = pytz.timezone('America/Lima')
    ahora = datetime.now(tz_peru)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%H:%M:%S"), ahora, ahora.strftime("%Y%m%d%H%M%S%f")

# 2. CONEXIÓN AWS
try:
    aws_id = st.secrets["aws"]["aws_access_key_id"]
    aws_key = st.secrets["aws"]["aws_secret_access_key"]
    aws_region = st.secrets["aws"]["aws_region"]
    admin_pass = st.secrets["auth"]["admin_password"]
    
    dynamodb = boto3.resource('dynamodb', region_name=aws_region,
                              aws_access_key_id=aws_id,
                              aws_secret_access_key=aws_key)
    
    tabla_ventas = dynamodb.Table('VentasDentaltio')
    tabla_stock = dynamodb.Table('StockProductos')
    tabla_auditoria = dynamodb.Table('EntradasInventario') 
except Exception as e:
    st.error(f"Error AWS: {e}"); st.stop()

if 'sesion_iniciada' not in st.session_state: st.session_state.sesion_iniciada = False
if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'boleta' not in st.session_state: st.session_state.boleta = None

if not st.session_state.sesion_iniciada:
    st.markdown("<h2 style='text-align: center;'>🦷 Sistema BALLARTA</h2>", unsafe_allow_html=True)
    clave = st.text_input("Contraseña:", type="password")
    if st.button("🔓 INGRESAR", use_container_width=True):
        if clave == admin_pass: st.session_state.sesion_iniciada = True; st.rerun()
    st.stop()

def get_df_stock():
    try:
        items = tabla_stock.scan().get('Items', [])
        if items:
            df = pd.DataFrame(items)
            df['Stock'] = pd.to_numeric(df['Stock'], errors='coerce').fillna(0).astype(int)
            df['Precio'] = pd.to_numeric(df['Precio'], errors='coerce').fillna(0.0)
            return df[['Producto', 'Stock', 'Precio']].sort_values(by='Producto')
    except: pass
    return pd.DataFrame(columns=['Producto', 'Stock', 'Precio'])

df_stock = get_df_stock()
tabs = st.tabs(["🛒 VENTA", "📦 STOCK", "📊 HOY", "📋 HISTORIAL", "📥 CARGAR", "🛠️ MANT."])

# --- TAB 1: VENTA (DISEÑO ANTI-ERRORES) ---
with tabs[0]:
    if st.session_state.boleta:
        b = st.session_state.boleta
        
        # HTML Ultra-simple para evitar que Streamlit lo bloquee
        filas_productos = ""
        for i in b['items']:
            filas_productos += f"""
                <tr>
                    <td style='text-align:left;'>{i['Cantidad']}</td>
                    <td style='text-align:left;'>{i['Producto']}</td>
                    <td style='text-align:right;'>{i['Precio']:.2f}</td>
                    <td style='text-align:right;'>{i['Subtotal']:.2f}</td>
                </tr>"""

        boleta_final = f"""
        <div style="background-color: white; color: black; padding: 20px; border: 2px solid #000; border-radius: 5px; width: 300px; font-family: monospace;">
            <center>
                <b style="font-size: 18px;">BALLARTA DENTAL</b><br>
                <span style="font-size: 12px;">Carabayllo, Lima</span><br>
                <span style="font-size: 12px;">{b['fecha']} {b['hora']}</span>
            </center>
            <hr>
            <table style="width: 100%; font-size: 12px;">
                <tr>
                    <th style="text-align:left;">Cant</th>
                    <th style="text-align:left;">Prod</th>
                    <th style="text-align:right;">P.U</th>
                    <th style="text-align:right;">Tot</th>
                </tr>
                {filas_productos}
            </table>
            <hr>
            <div style="text-align: right; font-size: 16px;">
                <b>TOTAL: S/ {b['total']:.2f}</b>
            </div>
            <div style="font-size: 12px;">Pago: {b['metodo']}</div>
            <br>
            <center><b>¡Gracias por su preferencia!</b></center>
        </div>
        """
        st.markdown(boleta_final, unsafe_allow_html=True)
        
        if st.button("⬅️ NUEVA VENTA", use_container_width=True):
            st.session_state.boleta = None
            st.rerun()
    else:
        # Carrito y selección
        if not df_stock.empty:
            p_sel = st.selectbox("Producto:", df_stock['Producto'].tolist())
            info = df_stock[df_stock['Producto'] == p_sel].iloc[0]
            st.caption(f"Stock actual: {info['Stock']}")
            
            c1, c2 = st.columns(2)
            with c1: p_u = st.number_input("S/ Unidad:", value=float(info['Precio']))
            with c2: cant = st.number_input("Cantidad:", min_value=1, value=1)
            
            sub = p_u * cant
            st.markdown(f"<h3 style='text-align:center; color:green;'>Subtotal: S/ {sub:.2f}</h3>", unsafe_allow_html=True)
            
            if st.button("➕ AÑADIR", use_container_width=True):
                if cant <= info['Stock']:
                    st.session_state.carrito.append({'Producto': p_sel, 'Original': p_sel, 'Cantidad': int(cant), 'Precio': float(p_u), 'Subtotal': round(sub, 2)})
                    st.rerun()
                else: st.error("No hay stock")

        if st.session_state.carrito:
            st.table(pd.DataFrame(st.session_state.carrito)[['Producto', 'Cantidad', 'Subtotal']])
            m = st.radio("Pago:", ["Efectivo", "Yape", "Plin"], horizontal=True)
            if st.button("🚀 COBRAR", type="primary", use_container_width=True):
                f, h, _, uid = obtener_tiempo_peru()
                total_final = sum(item['Subtotal'] for item in st.session_state.carrito)
                st.session_state.boleta = {'fecha': f, 'hora': h, 'items': list(st.session_state.carrito), 'total': total_final, 'metodo': m}
                for item in st.session_state.carrito:
                    s_act = int(df_stock[df_stock['Producto'] == item['Original']]['Stock'].values[0])
                    tabla_stock.update_item(Key={'Producto': item['Original']}, UpdateExpression="set Stock = :s", ExpressionAttributeValues={':s': s_act - item['Cantidad']})
                    tabla_ventas.put_item(Item={'ID_Venta': f"V-{uid}", 'Fecha': f, 'Hora': h, 'Producto': item['Producto'], 'Cantidad': int(item['Cantidad']), 'Total': str(item['Subtotal']), 'Metodo': m})
                st.session_state.carrito = []
                st.rerun()

# --- REPORTE DE HOY ---
with tabs[2]:
    st.subheader("📊 Caja")
    _, _, ahora_dt, _ = obtener_tiempo_peru()
    f_bus = st.date_input("Fecha:", ahora_dt).strftime("%d/%m/%Y")
    v_data = tabla_ventas.scan().get('Items', [])
    if v_data:
        df_v = pd.DataFrame(v_data)
        df_dia = df_v[df_v['Fecha'] == f_bus].copy()
        if not df_dia.empty:
            df_dia['Total'] = pd.to_numeric(df_dia['Total'])
            st.metric("Total Hoy", f"S/ {df_dia['Total'].sum():.2f}")
            st.dataframe(df_dia[['Hora', 'Producto', 'Total', 'Metodo']], use_container_width=True)

# --- LAS DEMÁS PESTAÑAS (Mantenlas igual) ---
with tabs[1]: st.dataframe(df_stock, use_container_width=True)
with tabs[4]:
    with st.form("fc"):
        pn = st.text_input("Nombre:").upper()
        cn = st.number_input("Cant:", min_value=1)
        pr = st.number_input("Precio:", min_value=1.0)
        if st.form_submit_button("GUARDAR"):
            f, h, _, uid = obtener_tiempo_peru()
            s_ant = int(df_stock[df_stock['Producto'] == pn]['Stock'].values[0]) if pn in df_stock['Producto'].values else 0
            tabla_stock.put_item(Item={'Producto': pn, 'Stock': s_ant + cn, 'Precio': str(pr)})
            tabla_auditoria.put_item(Item={'ID_Ingreso': f"I-{uid}", 'Fecha': f, 'Hora': h, 'Producto': pn, 'Cantidad_Entrante': int(cn), 'Stock_Resultante': int(s_ant + cn)})
            st.success("Ok"); time.sleep(1); st.rerun()
