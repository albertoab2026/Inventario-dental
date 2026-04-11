import streamlit as st
import pandas as pd
import boto3
from datetime import datetime
import pytz
import time

# 1. CONFIGURACIÓN E INTERFAZ
st.set_page_config(page_title="Sistema Dental BALLARTA", layout="wide")

def obtener_tiempo_peru():
    tz_peru = pytz.timezone('America/Lima')
    ahora = datetime.now(tz_peru)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%H:%M:%S"), ahora, ahora.strftime("%Y%m%d%H%M%S%f")

# 2. CONEXIÓN AWS DYNAMODB
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

# 3. CONTROL DE ESTADOS (SESSION STATE)
if 'sesion_iniciada' not in st.session_state: st.session_state.sesion_iniciada = False
if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'boleta' not in st.session_state: st.session_state.boleta = None
if 'reset_counter' not in st.session_state: st.session_state.reset_counter = 0

# --- LOGIN ---
if not st.session_state.sesion_iniciada:
    st.markdown("<h1 style='text-align: center;'>🦷</h1><h1 style='text-align: center; color: #2E86C1;'>Sistema Dental BALLARTA</h1>", unsafe_allow_html=True)
    col_login, _ = st.columns([1, 1])
    with col_login:
        clave = st.text_input("Clave del sistema:", type="password")
        if st.button("🔓 Ingresar", use_container_width=True):
            if clave == admin_pass:
                st.session_state.sesion_iniciada = True
                st.rerun()
            else: st.error("❌ Contraseña incorrecta")
    st.stop()

if st.sidebar.button("🔴 CERRAR SESIÓN"):
    st.session_state.sesion_iniciada = False
    st.rerun()

# Función para jalar stock actualizado
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

# --- TABS ORDENADAS ---
tabs = st.tabs(["🛒 VENTA", "📦 STOCK", "📊 REPORTES", "📋 HISTORIAL", "📥 CARGAR", "🛠️ MANT."])

# 1. PESTAÑA DE VENTAS
with tabs[0]:
    if st.session_state.boleta:
        st.balloons()
        b = st.session_state.boleta
        # Diseño de Ticket Profesional
        ticket = f"""
        <div style="background-color: white; color: #000; padding: 20px; border: 2px solid #000; border-radius: 10px; max-width: 350px; margin: auto; font-family: monospace;">
            <center><b>BALLARTA DENTAL</b><br>Carabayllo, Lima<br>{b['fecha']} {b['hora']}</center>
            <hr>
            <table style="width: 100%;">
                <tr><td><b>Cant</b></td><td><b>Prod</b></td><td style="text-align: right;"><b>Tot</b></td></tr>
        """
        for i in b['items']:
            ticket += f"<tr><td>{i['Cantidad']}</td><td>{i['Producto']}</td><td style='text-align: right;'>S/ {i['Subtotal']:.2f}</td></tr>"
        
        ticket += f"""
            </table>
            <hr>
            <div style="text-align: right;"><b>TOTAL: S/ {b['total_neto']:.2f}</b></div>
            <br><center>¡Gracias por su preferencia!</center>
        </div>
        """
        st.markdown(ticket, unsafe_allow_html=True)
        if st.button("⬅️ NUEVA VENTA"):
            st.session_state.boleta = None
            st.rerun()
    else:
        c1, c2 = st.columns([3, 1])
        with c1:
            p_sel = st.selectbox("Elegir Producto:", df_stock['Producto'].tolist(), 
                               on_change=lambda: st.session_state.update({"reset_counter": st.session_state.reset_counter + 1}))
            info = df_stock[df_stock['Producto'] == p_sel].iloc[0]
            st.info(f"Precio: S/ {info['Precio']:.2f} | Stock: {info['Stock']}")
        with c2:
            cant = st.number_input("Cantidad:", min_value=1, value=1, key=f"c_{st.session_state.reset_counter}")
        
        if st.button("➕ AÑADIR AL CARRITO", use_container_width=True):
            if cant <= info['Stock']:
                st.session_state.carrito.append({'Producto': p_sel, 'Cantidad': int(cant), 'Precio': float(info['Precio']), 'Subtotal': round(float(info['Precio']) * cant, 2)})
                st.session_state.reset_counter += 1
                st.rerun()
            else: st.error("No hay suficiente stock")

        if st.session_state.carrito:
            df_c = pd.DataFrame(st.session_state.carrito)
            st.table(df_c)
            t_bruto = df_c['Subtotal'].sum()
            rebaja = st.number_input("Descuento (S/):", min_value=0.0, value=0.0)
            t_final = t_bruto - rebaja
            
            st.markdown(f"### Total a Cobrar: S/ {t_final:.2f}")
            metodo = st.radio("Pago:", ["Efectivo", "Yape", "Plin"], horizontal=True)
            
            if st.button("🚀 FINALIZAR VENTA"):
                f, h, _, uid = obtener_tiempo_peru()
                st.session_state.boleta = {'fecha': f, 'hora': h, 'items': list(st.session_state.carrito), 'total_neto': t_final, 'metodo': metodo}
                
                for idx, item in enumerate(st.session_state.carrito):
                    # Actualizar Stock
                    nuevo_s = int(df_stock[df_stock['Producto'] == item['Producto']]['Stock'].values[0]) - item['Cantidad']
                    tabla_stock.update_item(Key={'Producto': item['Producto']}, UpdateExpression="set Stock = :s", ExpressionAttributeValues={':s': nuevo_s})
                    # Guardar Venta (Rebaja aplicada al primer item para cuadre)
                    valor_venda = item['Subtotal'] - rebaja if idx == 0 else item['Subtotal']
                    tabla_ventas.put_item(Item={'ID_Venta': f"V-{uid}-{idx}", 'Fecha': f, 'Hora': h, 'Producto': item['Producto'], 'Cantidad': int(item['Cantidad']), 'Total': str(round(valor_venda, 2)), 'Metodo': metodo})
                
                st.session_state.carrito = []
                st.rerun()

# 2. PESTAÑA DE STOCK
with tabs[1]:
    st.subheader("📦 Inventario de Productos")
    st.dataframe(df_stock, use_container_width=True, hide_index=True)

# 3. PESTAÑA DE REPORTES
with tabs[2]:
    st.subheader("📊 Reportes Diarios")
    f_bus = st.date_input("Seleccionar Fecha:").strftime("%d/%m/%Y")
    ventas = tabla_ventas.scan().get('Items', [])
    if ventas:
        df_v = pd.DataFrame(ventas)
        df_hoy = df_v[df_v['Fecha'] == f_bus].copy()
        if not df_hoy.empty:
            df_hoy['Total'] = pd.to_numeric(df_hoy['Total'])
            st.metric("VENTA TOTAL DEL DÍA", f"S/ {df_hoy['Total'].sum():.2f}")
            st.dataframe(df_hoy[['Hora', 'Producto', 'Cantidad', 'Total', 'Metodo']], hide_index=True)
        else: st.warning("No hay ventas en esta fecha")

# 4. PESTAÑA DE HISTORIAL
with tabs[3]:
    st.subheader("📋 Historial de Ingresos")
    historial = tabla_auditoria.scan().get('Items', [])
    if historial:
        df_h = pd.DataFrame(historial).sort_values(by=['Fecha', 'Hora'], ascending=False)
        st.dataframe(df_h[['Fecha', 'Hora', 'Producto', 'Cantidad_Entrante', 'Stock_Resultante']], use_container_width=True)

# 5. PESTAÑA DE CARGAR
with tabs[4]:
    st.subheader("📥 Cargar Nuevo Stock")
    with st.form("carga"):
        p_nombre = st.text_input("Nombre del Producto:").upper()
        p_cant = st.number_input("Cantidad que entra:", min_value=1)
        p_precio = st.number_input("Precio de Venta:", min_value=0.1)
        if st.form_submit_button("REGISTRAR INGRESO"):
            f, h, _, uid = obtener_tiempo_peru()
            s_actual = int(df_stock[df_stock['Producto'] == p_nombre]['Stock'].values[0]) if p_nombre in df_stock['Producto'].values else 0
            tabla_stock.put_item(Item={'Producto': p_nombre, 'Stock': s_actual + p_cant, 'Precio': str(p_precio)})
            tabla_auditoria.put_item(Item={'ID_Ingreso': f"I-{uid}", 'Fecha': f, 'Hora': h, 'Producto': p_nombre, 'Cantidad_Entrante': int(p_cant), 'Stock_Resultante': int(s_actual + p_cant)})
            st.success("Inventario actualizado"); time.sleep(1); st.rerun()

# 6. PESTAÑA DE MANTENIMIENTO
with tabs[5]:
    st.subheader("🛠️ Mantenimiento de Base de Datos")
    prod_borrar = st.selectbox("Eliminar Producto permanentemente:", [""] + df_stock['Producto'].tolist())
    if st.button("🗑️ ELIMINAR") and prod_borrar != "":
        tabla_stock.delete_item(Key={'Producto': prod_borrar})
        st.success("Producto borrado"); time.sleep(1); st.rerun()
