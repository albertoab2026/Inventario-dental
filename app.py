import streamlit as st
import pandas as pd
import boto3
from datetime import datetime
import pytz
import time
from boto3.dynamodb.conditions import Attr

# --- 0. CONFIGURACIÓN SaaS (Basado en tus fotos de AWS) ---
TABLA_STOCK = 'SaaS_Stock_Test'
TABLA_VENTAS = 'SaaS_Ventas_Test'

# --- 1. CONFIGURACIÓN E INTERFAZ ---
st.set_page_config(page_title="NEXUS BALLARTA SaaS", layout="wide", page_icon="🚀")
tz_peru = pytz.timezone('America/Lima')

def obtener_tiempo_peru():
    ahora = datetime.now(tz_peru)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%H:%M:%S"), ahora, ahora.strftime("%Y%m%d%H%M%S%f")

# --- 2. CONEXIÓN SEGURA AWS ---
try:
    dynamodb = boto3.resource('dynamodb', region_name=st.secrets["aws"]["aws_region"],
                              aws_access_key_id=st.secrets["aws"]["aws_access_key_id"],
                              aws_secret_access_key=st.secrets["aws"]["aws_secret_access_key"])
    tabla_stock = dynamodb.Table(TABLA_STOCK)
    tabla_ventas = dynamodb.Table(TABLA_VENTAS)
except Exception as e:
    st.error(f"Error de conexión AWS: {e}")
    st.stop()

# --- 3. CONTROL DE SESIÓN ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'tenant' not in st.session_state: st.session_state.tenant = None
if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'boleta' not in st.session_state: st.session_state.boleta = None

# --- LOGIN ---
if not st.session_state.auth:
    st.markdown("<h1 style='text-align: center;'>🚀 NEXUS BALLARTA SaaS</h1>", unsafe_allow_html=True)
    locales = list(st.secrets.get("auth_multi", {"Demo": ""}).keys())
    local_sel = st.selectbox("Seleccione Local:", locales)
    clave = st.text_input("Clave de acceso:", type="password")
    if st.button("🔓 Ingresar", use_container_width=True):
        if clave == "tiotuinventario":
            st.session_state.auth = True
            st.session_state.tenant = local_sel
            st.rerun()
        else:
            st.error("❌ Clave incorrecta")
    st.stop()

# --- CARGA DE DATOS (Blindaje total contra KeyError y NaN) ---
def obtener_stock_db():
    try:
        res = tabla_stock.scan(FilterExpression=Attr('TenantID').eq(st.session_state.tenant))
        items = res.get('Items', [])
        df = pd.DataFrame(items)
        
        columnas_necesarias = ['Producto', 'Stock', 'Precio', 'Precio_Compra']
        if df.empty:
            return pd.DataFrame(columns=columnas_necesarias)
        
        # Si falta una columna en la DB de AWS, la creamos con 0 para evitar el error rojo
        for col in columnas_necesarias:
            if col not in df.columns:
                df[col] = 0 if col != 'Producto' else "S/N"
        
        # Limpieza de datos (convierte nan a 0)
        df['Stock'] = pd.to_numeric(df['Stock'], errors='coerce').fillna(0).astype(int)
        df['Precio'] = pd.to_numeric(df['Precio'], errors='coerce').fillna(0.0)
        df['Precio_Compra'] = pd.to_numeric(df['Precio_Compra'], errors='coerce').fillna(0.0)
        
        return df[columnas_necesarias].sort_values(by='Producto')
    except:
        return pd.DataFrame(columns=['Producto', 'Stock', 'Precio', 'Precio_Compra'])

df_stock = obtener_stock_db()

# --- SIDEBAR ---
with st.sidebar:
    st.title(f"🏢 {st.session_state.tenant}")
    if st.button("🔴 CERRAR SESIÓN", use_container_width=True):
        st.session_state.auth = False; st.rerun()

tabs = st.tabs(["🛒 VENTA", "📦 STOCK", "📊 REPORTES", "📋 HISTORIAL", "📥 CARGAR", "🛠️ MANT."])

# --- 1. PESTAÑA DE VENTAS ---
with tabs[0]:
    if st.session_state.boleta:
        st.balloons()
        b = st.session_state.boleta
        ticket = f"""
        <div style="background-color: white; color: #000; padding: 20px; border: 2px solid #000; border-radius: 10px; max-width: 350px; margin: auto; font-family: monospace;">
            <center><b>{st.session_state.tenant}</b><br>{b['fecha']} {b['hora']}</center>
            <hr>
            <table style="width: 100%;">
        """
        for i in b['items']:
            ticket += f"<tr><td>{i['Cantidad']}</td><td>{i['Producto']}</td><td style='text-align: right;'>S/ {i['Subtotal']:.2f}</td></tr>"
        ticket += f"</table><hr><div style='text-align: right;'><b>TOTAL: S/ {b['total_neto']:.2f}</b></div><center><br>Pago: {b['metodo']}</center></div>"
        st.markdown(ticket, unsafe_allow_html=True)
        if st.button("⬅️ NUEVA VENTA"):
            st.session_state.boleta = None; st.rerun()
    else:
        st.subheader("🛒 Punto de Venta")
        bus_v = st.text_input("🔍 Buscar:").strip().upper()
        prod_filt = [p for p in df_stock['Producto'].tolist() if bus_v in str(p)]
        
        c1, c2 = st.columns([3, 1])
        with c1:
            p_sel = st.selectbox("Producto:", prod_filt) if prod_filt else None
        with c2:
            cant = st.number_input("Cant:", min_value=1, value=1)
        
        if p_sel:
            info = df_stock[df_stock['Producto'] == p_sel].iloc[0]
            st.info(f"💰 S/ {info['Precio']:.2f} | 📦 Disp: {info['Stock']}")
            if st.button("➕ AÑADIR AL CARRITO", use_container_width=True):
                if cant <= info['Stock']:
                    st.session_state.carrito.append({
                        'Producto': p_sel, 'Cantidad': int(cant), 
                        'Precio': float(info['Precio']), 'Precio_Compra': float(info['Precio_Compra']),
                        'Subtotal': round(float(info['Precio']) * cant, 2)
                    })
                    st.rerun()
                else: st.error("Sin stock")

        if st.session_state.carrito:
            st.divider()
            df_c = pd.DataFrame(st.session_state.carrito)
            st.table(df_c[['Producto', 'Cantidad', 'Precio', 'Subtotal']].style.format({"Precio": "{:.2f}", "Subtotal": "{:.2f}"}))
            total = df_c['Subtotal'].sum()
            st.markdown(f"<h3 style='text-align:center;'>TOTAL: S/ {total:.2f}</h3>", unsafe_allow_html=True)
            metodo = st.radio("Pago:", ["💵 Efectivo", "🟣 Yape", "🔵 Plin"], horizontal=True)
            
            confirmar = st.checkbox("✅ ¿Desea realmente hacer la compra?")
            if st.button("🚀 FINALIZAR", type="primary", use_container_width=True, disabled=not confirmar):
                f, h, _, uid = obtener_tiempo_peru()
                st.session_state.boleta = {'fecha': f, 'hora': h, 'items': list(st.session_state.carrito), 'total_neto': total, 'metodo': metodo}
                for idx, item in enumerate(st.session_state.carrito):
                    # --- VentalID (Exacto como tu captura) ---
                    tabla_ventas.put_item(Item={
                        'TenantID': st.session_state.tenant, 'VentalID': f"V-{uid}-{idx}",
                        'Fecha': f, 'Hora': h, 'Producto': item['Producto'], 
                        'Cantidad': int(item['Cantidad']), 'Total': str(round(item['Subtotal'], 2)),
                        'Precio_Compra': str(round(item['Precio_Compra'], 2)), 'Metodo': metodo
                    })
                    # Descontar stock
                    n_stock = int(df_stock[df_stock['Producto'] == item['Producto']]['Stock'].values[0]) - item['Cantidad']
                    tabla_stock.update_item(
                        Key={'TenantID': st.session_state.tenant, 'Producto': item['Producto']},
                        UpdateExpression="SET Stock = :s", ExpressionAttributeValues={':s': n_stock}
                    )
                st.session_state.carrito = []; st.rerun()

# --- 2. STOCK ---
with tabs[1]:
    st.subheader("📦 Inventario")
    st.dataframe(df_stock.style.format({"Precio": "{:.2f}", "Precio_Compra": "{:.2f}"}), use_container_width=True, hide_index=True)

# --- 3. REPORTES ---
with tabs[2]:
    st.subheader("📊 Reporte de Ganancias")
    res_v = tabla_ventas.scan(FilterExpression=Attr('TenantID').eq(st.session_state.tenant))
    v_items = res_v.get('Items', [])
    if v_items:
        df_v = pd.DataFrame(v_items)
        # Forzar columnas para evitar el KeyError de tus fotos
        for c in ['Total', 'Precio_Compra', 'Cantidad', 'Fecha', 'Metodo']:
            if c not in df_v.columns: df_v[c] = 0 if c != 'Fecha' and c != 'Metodo' else "---"
        
        df_v['Total'] = pd.to_numeric(df_v['Total'])
        df_v['Ganancia'] = df_v['Total'] - (pd.to_numeric(df_v['Precio_Compra']) * pd.to_numeric(df_v['Cantidad']))
        st.metric("GANANCIA TOTAL", f"S/ {df_v['Ganancia'].sum():.2f}")
        st.dataframe(df_v[['Fecha', 'Producto', 'Total', 'Metodo']], use_container_width=True)
    else: st.info("Sin ventas registradas")

# --- 4. HISTORIAL ---
with tabs[3]:
    st.subheader("📋 Movimientos DynamoDB")
    if v_items: st.dataframe(pd.DataFrame(v_items), use_container_width=True)

# --- 5. CARGAR ---
with tabs[4]:
    opc = st.radio("Modo:", ["Individual", "Masiva (Excel)"], horizontal=True)
    if opc == "Individual":
        with st.form("f_ind"):
            p_n = st.text_input("Nombre:").upper()
            s_n = st.number_input("Stock:", min_value=0)
            pv_n = st.number_input("Precio Venta:", min_value=0.0)
            pc_n = st.number_input("Costo:", min_value=0.0)
            if st.form_submit_button("Guardar"):
                tabla_stock.put_item(Item={'TenantID': st.session_state.tenant, 'Producto': p_n, 'Stock': int(s_n), 'Precio': str(pv_n), 'Precio_Compra': str(pc_n)})
                st.success("Guardado"); time.sleep(1); st.rerun()
    else:
        file = st.file_uploader("Subir Excel", type=['xlsx'])
        if file and st.button("🚀 Iniciar Carga"):
            df_m = pd.read_excel(file)
            # Limpiar nombres de columnas del Excel
            df_m.columns = [c.strip() for c in df_m.columns]
            for _, r in df_m.iterrows():
                tabla_stock.put_item(Item={
                    'TenantID': st.session_state.tenant, 
                    'Producto': str(r.get('Producto', 'S/N')).upper(),
                    'Stock': int(r.get('Stock', 0)), 
                    'Precio': str(r.get('Precio', 0)), 
                    'Precio_Compra': str(r.get('Precio_Compra', 0))
                })
            st.success("Carga completada"); st.rerun()

# --- 6. MANTENIMIENTO ---
with tabs[5]:
    st.subheader("🛠️ Editar Productos")
    if not df_stock.empty:
        p_edit = st.selectbox("Seleccione producto:", df_stock['Producto'].tolist())
        with st.form("f_edit"):
            new_s = st.number_input("Nuevo Stock:")
            new_p = st.number_input("Nuevo Precio:")
            if st.form_submit_button("Actualizar"):
                tabla_stock.update_item(
                    Key={'TenantID': st.session_state.tenant, 'Producto': p_edit},
                    UpdateExpression="SET Stock = :s, Precio = :p",
                    ExpressionAttributeValues={':s': int(new_s), ':p': str(new_p)}
                )
                st.success("Actualizado"); st.rerun()
