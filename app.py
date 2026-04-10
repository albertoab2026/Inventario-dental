import streamlit as st
import pandas as pd
import boto3
from datetime import datetime
import pytz
import time
from io import BytesIO

# 1. CONFIGURACIÓN VISUAL PARA CELULAR
st.set_page_config(page_title="Dental BALLARTA", layout="wide")

def obtener_tiempo_peru():
    tz_peru = pytz.timezone('America/Lima')
    ahora = datetime.now(tz_peru)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%H:%M:%S"), ahora, ahora.strftime("%Y%m%d%H%M%S%f")

# 2. CONEXIÓN AWS (DynamoDB)
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
    st.error(f"Error de conexión: {e}")
    st.stop()

# 3. ESTADOS DE SESIÓN
if 'sesion_iniciada' not in st.session_state: st.session_state.sesion_iniciada = False
if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'boleta' not in st.session_state: st.session_state.boleta = None

# --- LOGIN ---
if not st.session_state.sesion_iniciada:
    st.markdown("<h1 style='text-align: center;'>🦷</h1><h2 style='text-align: center;'>Sistema BALLARTA</h2>", unsafe_allow_html=True)
    clave = st.text_input("Contraseña del sistema:", type="password")
    if st.button("🔓 INGRESAR", use_container_width=True):
        if clave == admin_pass:
            st.session_state.sesion_iniciada = True
            st.rerun()
        else: st.error("Clave incorrecta")
    st.stop()

# BOTÓN DE CIERRE EN EL MENÚ LATERAL
if st.sidebar.button("🔴 CERRAR SESIÓN"):
    st.session_state.sesion_iniciada = False
    st.rerun()

# CARGAR DATOS DE PRODUCTOS
def get_df_stock():
    try:
        items = tabla_stock.scan().get('Items', [])
        if items:
            df = pd.DataFrame(items)
            for col in ['Stock', 'Precio', 'Producto']:
                if col not in df.columns: df[col] = 0 if col != 'Producto' else "Sin Nombre"
            df['Stock'] = pd.to_numeric(df['Stock'], errors='coerce').fillna(0).astype(int)
            df['Precio'] = pd.to_numeric(df['Precio'], errors='coerce').fillna(0.0)
            return df[['Producto', 'Stock', 'Precio']].sort_values(by='Producto')
    except: pass
    return pd.DataFrame(columns=['Producto', 'Stock', 'Precio'])

df_stock = get_df_stock()

# PESTAÑAS PRINCIPALES
tabs = st.tabs(["🛒 VENTA", "📦 STOCK", "📊 HOY", "📋 LOGS", "📥 CARGAR", "🛠️ MANT."])

# --- TAB 1: VENTA (CÁLCULO AUTOMÁTICO) ---
with tabs[0]:
    if st.session_state.boleta:
        b = st.session_state.boleta
        ticket = f"""
        <div style="background-color: white; color: black; padding: 20px; border: 2px solid black; border-radius: 10px; font-family: monospace;">
            <center><h3>BALLARTA DENTAL</h3></center>
            <p>FECHA: {b['fecha']} {b['hora']}</p>
            <hr>
        """
        for i in b['items']:
            ticket += f"<p>{i['Cantidad']} x {i['Producto']} <span style='float:right;'>S/ {i['Subtotal']:.2f}</span></p>"
        ticket += f"<hr><h3 style='text-align:right;'>TOTAL: S/ {b['total']:.2f}</h3><p>Pago: {b['metodo']}</p></div>"
        st.markdown(ticket, unsafe_allow_html=True)
        if st.button("⬅️ NUEVA VENTA", use_container_width=True):
            st.session_state.boleta = None
            st.rerun()
    else:
        if not df_stock.empty:
            p_sel = st.selectbox("Buscar Producto:", df_stock['Producto'].tolist())
            info = df_stock[df_stock['Producto'] == p_sel].iloc[0]
            
            st.warning(f"Stock disponible: {info['Stock']} unidades")
            
            c1, c2 = st.columns(2)
            with c1:
                # Precio unitario (puedes editarlo para REBAJAS)
                precio_u = st.number_input("Precio Unidad (S/):", value=float(info['Precio']), step=1.0, key=f"p_{p_sel}")
            with c2:
                # Cantidad (solo números enteros para evitar líos)
                cant = st.number_input("Cantidad:", min_value=1, value=1, key=f"c_{p_sel}")
            
            # --- AQUÍ ESTÁ EL CÁLCULO EN VIVO QUE PEDISTE ---
            sub_total = precio_u * cant
            st.markdown(f"""
                <div style="background-color: #D4E6F1; padding: 10px; border-radius: 5px; text-align: center;">
                    <h3 style="color: #1B4F72; margin: 0;">Subtotal: S/ {sub_total:.2f}</h3>
                </div>
            """, unsafe_allow_html=True)
            
            nota = st.text_input("Nota (opcional: ej. Rebaja)", key=f"n_{p_sel}")

            if st.button("➕ AÑADIR A LA LISTA", use_container_width=True, type="secondary"):
                if cant <= info['Stock']:
                    nombre_f = f"{p_sel} ({nota})" if nota else p_sel
                    st.session_state.carrito.append({
                        'Producto': nombre_f, 
                        'Original': p_sel, 
                        'Cantidad': int(cant), 
                        'Precio': float(precio_u), 
                        'Subtotal': round(sub_total, 2)
                    })
                    st.rerun()
                else:
                    st.error("No hay stock suficiente")

        if st.session_state.carrito:
            st.divider()
            df_c = pd.DataFrame(st.session_state.carrito)
            st.dataframe(df_c[['Producto', 'Cantidad', 'Subtotal']], use_container_width=True, hide_index=True)
            total_final = df_c['Subtotal'].sum()
            st.subheader(f"Total a Cobrar: S/ {total_final:.2f}")
            
            if st.button("🗑️ VACIAR CARRITO", use_container_width=True):
                st.session_state.carrito = []
                st.rerun()

            metodo = st.radio("Método de Pago:", ["Efectivo", "Yape", "Plin"], horizontal=True)
            if st.button("🚀 REGISTRAR VENTA FINAL", type="primary", use_container_width=True):
                f, h, _, uid = obtener_tiempo_peru()
                st.session_state.boleta = {'fecha': f, 'hora': h, 'items': list(st.session_state.carrito), 'total': total_final, 'metodo': metodo}
                for item in st.session_state.carrito:
                    # Restar de DynamoDB
                    s_act = int(df_stock[df_stock['Producto'] == item['Original']]['Stock'].values[0])
                    tabla_stock.update_item(Key={'Producto': item['Original']}, UpdateExpression="set Stock = :s", ExpressionAttributeValues={':s': s_act - item['Cantidad']})
                    # Guardar venta
                    tabla_ventas.put_item(Item={'ID_Venta': f"V-{uid}", 'Fecha': f, 'Hora': h, 'Producto': item['Producto'], 'Cantidad': int(item['Cantidad']), 'Total': str(item['Subtotal']), 'Metodo': metodo})
                st.session_state.carrito = []
                st.rerun()

# --- TAB 2: STOCK ---
with tabs[1]:
    st.subheader("📦 Almacén")
    st.dataframe(df_stock, use_container_width=True, hide_index=True)

# --- TAB 3: HOY (REPORTES) ---
with tabs[2]:
    st.subheader("📊 Ventas de Hoy")
    _, _, ahora_dt, _ = obtener_tiempo_peru()
    f_bus = st.date_input("Fecha:", ahora_dt).strftime("%d/%m/%Y")
    v_data = tabla_ventas.scan().get('Items', [])
    if v_data:
        df_v = pd.DataFrame(v_data)
        df_dia = df_v[df_v['Fecha'] == f_bus].copy()
        if not df_dia.empty:
            df_dia['Total'] = pd.to_numeric(df_dia['Total'])
            st.metric("GANANCIA DEL DÍA", f"S/ {df_dia['Total'].sum():.2f}")
            st.dataframe(df_dia[['Hora', 'Producto', 'Total', 'Metodo']], use_container_width=True, hide_index=True)

# --- TAB 5: CARGAR STOCK ---
with tabs[4]:
    st.subheader("📥 Cargar Mercadería")
    with st.form("form_carga"):
        p_n = st.text_input("Nombre del Producto:").upper().strip()
        c_n = st.number_input("Cantidad que entra:", min_value=1)
        pr_n = st.number_input("Precio de Venta Normal:", min_value=1.0)
        if st.form_submit_button("💾 GUARDAR"):
            f, h, _, uid = obtener_tiempo_peru()
            s_ant = int(df_stock[df_stock['Producto'] == p_n]['Stock'].values[0]) if p_n in df_stock['Producto'].values else 0
            tabla_stock.put_item(Item={'Producto': p_n, 'Stock': s_ant + c_n, 'Precio': str(pr_n)})
            tabla_auditoria.put_item(Item={'ID_Ingreso': f"I-{uid}", 'Fecha': f, 'Hora': h, 'Producto': p_n, 'Cantidad_Entrante': int(c_n), 'Stock_Resultante': int(s_ant + c_n), 'Tipo': 'INGRESO'})
            st.success("Guardado!"); time.sleep(1); st.rerun()

# --- TAB 6: MANTENIMIENTO ---
with tabs[5]:
    st.subheader("🛠️ Eliminar Producto")
    p_del = st.selectbox("Seleccione producto a borrar:", df_stock['Producto'].tolist())
    if st.button("🗑️ ELIMINAR TOTALMENTE", type="primary"):
        tabla_stock.delete_item(Key={'Producto': p_del})
        st.success("Borrado"); time.sleep(1); st.rerun()
