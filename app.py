import streamlit as st
import pandas as pd
import boto3
from datetime import datetime
import pytz
import time
import io

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Sistema Dental BALLARTA", layout="wide")

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
    st.error(f"Error de conexión: {e}")
    st.stop()

# 3. ESTADOS DE SESIÓN
if 'sesion_iniciada' not in st.session_state: st.session_state.sesion_iniciada = False
if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'boleta' not in st.session_state: st.session_state.boleta = None

# --- LOGIN ---
if not st.session_state.sesion_iniciada:
    st.markdown("<h1 style='text-align: center;'>🦷</h1>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: #2E86C1;'>Sistema Dental BALLARTA</h1>", unsafe_allow_html=True)
    col_login, _ = st.columns([1, 1])
    with col_login:
        clave = st.text_input("Clave del sistema:", type="password")
        if st.button("🔓 Ingresar", use_container_width=True):
            if clave == admin_pass:
                st.session_state.sesion_iniciada = True
                st.rerun()
            else: st.error("❌ Contraseña incorrecta")
    st.stop()

# SIDEBAR (Adaptable)
if st.sidebar.button("🔴 CERRAR SESIÓN"):
    st.session_state.sesion_iniciada = False
    st.rerun()

# CARGAR STOCK
def get_df_stock():
    items = tabla_stock.scan().get('Items', [])
    if items:
        df = pd.DataFrame(items)
        df['Stock'] = pd.to_numeric(df['Stock'])
        df['Precio'] = pd.to_numeric(df['Precio'])
        return df[['Producto', 'Stock', 'Precio']].sort_values(by='Producto')
    return pd.DataFrame(columns=['Producto', 'Stock', 'Precio'])

df_stock = get_df_stock()

t1, t2, t3, t4, t5, t6 = st.tabs(["🛒 Venta", "📦 Stock", "📊 Reportes", "📋 Historial", "📥 Cargar", "🛠️ Mant."])

# --- TAB 1: PUNTO DE VENTA ---
with t1:
    if st.session_state.boleta:
        st.balloons()
        b = st.session_state.boleta
        # Ticket con colores neutros para ambos modos
        ticket = f"""
        <div style="background-color: #f9f9f9; color: black; padding: 25px; border: 2px solid #333; border-radius: 10px; max-width: 450px; margin: auto; font-family: Arial;">
            <center><h2>🦷 BALLARTA</h2><p>Insumos Dentales</p></center>
            <hr style="border-top: 1px solid #333;">
            <p><b>FECHA:</b> {b['fecha']} | {b['hora']}</p>
            <table style="width: 100%; color: black;">
                <tr><td><b>Cant.</b></td><td><b>Producto</b></td><td style="text-align: right;"><b>Total</b></td></tr>
        """
        for i in b['items']:
            ticket += f"<tr><td>{i['Cantidad']}</td><td>{i['Producto']}</td><td style='text-align: right;'>S/ {float(i['Subtotal']):.2f}</td></tr>"
        ticket += f"""
            </table>
            <hr style="border-top: 1px solid #333;">
            <h3 style="text-align: right; color: black;">TOTAL: S/ {b['total']:.2f}</h3>
            <p style="color: black;"><b>MÉTODO:</b> {b['metodo']}</p>
        </div>
        """
        st.markdown(ticket, unsafe_allow_html=True)
        if st.button("⬅️ NUEVA VENTA"):
            st.session_state.boleta = None
            st.rerun()
    else:
        if not df_stock.empty:
            c1, c2 = st.columns([3, 1])
            with c1:
                p_sel = st.selectbox("Elegir Producto:", df_stock['Producto'].tolist())
                info = df_stock[df_stock['Producto'] == p_sel].iloc[0]
                if info['Stock'] <= 5:
                    st.error(f"⚠️ **STOCK CRÍTICO:** Solo quedan {info['Stock']:.0f} unidades.")
                else:
                    st.info(f"📦 Disponible: {info['Stock']:.0f} | 💰 Precio: S/ {info['Precio']:.2f}")
            with c2:
                cant = st.number_input("Cantidad:", min_value=1, value=1)
            
            if st.button("➕ AÑADIR AL CARRITO", use_container_width=True):
                if cant <= info['Stock']:
                    st.session_state.carrito.append({'Producto': p_sel, 'Cantidad': int(cant), 'Precio': float(info['Precio']), 'Subtotal': round(float(info['Precio']) * cant, 2)})
                    st.rerun()
                else: st.error("No hay stock suficiente.")

        if st.session_state.carrito:
            df_car = pd.DataFrame(st.session_state.carrito)
            st.table(df_car.style.format({"Precio": "{:.2f}", "Subtotal": "{:.2f}"}))
            total_v = df_car['Subtotal'].sum()
            
            # TOTAL ADAPTABLE (Sin fondo negro fijo)
            st.markdown(f"""
                <div style="border: 2px solid #2ECC71; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 20px;">
                    <h1 style="color: #2ECC71; margin: 0;">TOTAL: S/ {total_v:.2f}</h1>
                </div>
            """, unsafe_allow_html=True)
            
            metodo = st.radio("Método de Pago:", ["💵 Efectivo", "🟢 Yape", "🟣 Plin"], horizontal=True)
            confirmar = st.checkbox("Confirmar recepción de dinero")
            
            if st.button("🚀 FINALIZAR VENTA", disabled=not confirmar, type="primary", use_container_width=True):
                f, h, _, uid = obtener_tiempo_peru()
                st.session_state.boleta = {'fecha': f, 'hora': h, 'items': list(st.session_state.carrito), 'total': total_v, 'metodo': metodo}
                for item in st.session_state.carrito:
                    n_s = int(df_stock[df_stock['Producto'] == item['Producto']]['Stock'].values[0]) - item['Cantidad']
                    tabla_stock.update_item(Key={'Producto': item['Producto']}, UpdateExpression="set Stock = :s", ExpressionAttributeValues={':s': n_s})
                    tabla_ventas.put_item(Item={'ID_Venta': f"V-{uid}-{item['Producto'][:2]}", 'Fecha': f, 'Hora': h, 'Producto': item['Producto'], 'Cantidad': int(item['Cantidad']), 'Total': str(item['Subtotal']), 'Metodo': metodo})
                st.session_state.carrito = []
                st.rerun()

# --- TAB 2: STOCK (Resaltado Adaptable) ---
with t2:
    st.subheader("📦 Inventario Actual")
    def resaltar_stock(val):
        color = '#E74C3C' if val <= 5 else '' # Rojo suave para ambos modos
        return f'color: {"white" if color else ""}; background-color: {color}; font-weight: bold' if color else ''

    st.dataframe(df_stock.style.applymap(resaltar_stock, subset=['Stock']).format({"Precio": "S/ {:.2f}", "Stock": "{:.0f}"}), use_container_width=True, hide_index=True)

# --- TAB 3: REPORTES ---
with t3:
    st.subheader("📊 Reporte Diario")
    _, _, ahora_dt, _ = obtener_tiempo_peru()
    f_bus = st.date_input("Consultar fecha:", ahora_dt).strftime("%d/%m/%Y")
    ventas = tabla_ventas.scan().get('Items', [])
    if ventas:
        df_v = pd.DataFrame(ventas)
        df_v_dia = df_v[df_v['Fecha'] == f_bus].copy()
        if not df_v_dia.empty:
            df_v_dia['Total'] = pd.to_numeric(df_v_dia['Total'])
            ce, cy, cp = df_v_dia[df_v_dia['Metodo'] == "💵 Efectivo"]['Total'].sum(), df_v_dia[df_v_dia['Metodo'] == "🟢 Yape"]['Total'].sum(), df_v_dia[df_v_dia['Metodo'] == "🟣 Plin"]['Total'].sum()
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("💵 EFECTIVO", f"S/ {ce:.2f}"); m2.metric("🟢 YAPE", f"S/ {cy:.2f}"); m3.metric("🟣 PLIN", f"S/ {cp:.2f}"); m4.metric("💰 TOTAL", f"S/ {df_v_dia['Total'].sum():.2f}")
            df_v_ord = df_v_dia.sort_values(by='Hora', ascending=False)
            st.dataframe(df_v_ord[['Hora', 'Producto', 'Cantidad', 'Total', 'Metodo']], use_container_width=True, hide_index=True)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_v_ord.to_excel(writer, index=False)
            st.download_button("📥 Descargar Excel", output.getvalue(), f"Ventas_{f_bus}.xlsx")

# --- TAB 4: HISTORIAL ---
with t4:
    st.subheader("📋 Historial de Ingresos")
    historial = tabla_auditoria.scan().get('Items', [])
    if historial:
        df_h = pd.DataFrame(historial)
        df_h['Sort'] = pd.to_datetime(df_h['Fecha'] + ' ' + df_h['Hora'], format='%d/%m/%Y %H:%M:%S')
        df_h = df_h.sort_values(by='Sort', ascending=False)
        st.dataframe(df_h[['Fecha', 'Hora', 'Producto', 'Cantidad_Entrante', 'Stock_Resultante']].style.format({"Cantidad_Entrante": "{:.0f}", "Stock_Resultante": "{:.0f}"}), use_container_width=True, hide_index=True)
        out_h = io.BytesIO()
        with pd.ExcelWriter(out_h, engine='xlsxwriter') as writer:
            df_h.drop(columns=['Sort']).to_excel(writer, index=False)
        st.download_button("📥 Descargar Historial", out_h.getvalue(), "Historial.xlsx")

# --- TAB 5: CARGAR STOCK ---
with t5:
    st.subheader("📥 Cargar Mercadería")
    with st.form("f_carga"):
        p_ex = st.selectbox("Producto existente:", [""] + df_stock['Producto'].tolist())
        p_nu = st.text_input("O Nuevo:").upper()
        p_fin = p_nu if p_nu else p_ex
        c_in = st.number_input("Cantidad:", min_value=1)
        pr_in = st.number_input("Precio:", min_value=0.1)
        if st.form_submit_button("💾 GUARDAR"):
            if p_fin:
                f, h, _, uid = obtener_tiempo_peru()
                s_act = int(df_stock[df_stock['Producto'] == p_fin]['Stock'].values[0]) if p_fin in df_stock['Producto'].values else 0
                nuevo_s = s_act + c_in
                tabla_stock.put_item(Item={'Producto': p_fin, 'Stock': nuevo_s, 'Precio': str(pr_in)})
                tabla_auditoria.put_item(Item={'ID_Ingreso': f"ING-{uid}", 'Fecha': f, 'Hora': h, 'Producto': p_fin, 'Cantidad_Entrante': int(c_in), 'Stock_Resultante': int(nuevo_s)})
                st.success(f"Registrado: {p_fin}")
                time.sleep(1); st.rerun()

# --- TAB 6: MANTENIMIENTO ---
with t6:
    st.subheader("🛠️ Mantenimiento")
    if not df_stock.empty:
        p_del = st.selectbox("Seleccionar para ELIMINAR:", df_stock['Producto'].tolist())
        if st.button("🗑️ ELIMINAR PERMANENTEMENTE", use_container_width=True):
            tabla_stock.delete_item(Key={'Producto': p_del})
            st.success(f"✅ Se eliminó: {p_del}")
            time.sleep(2); st.rerun()
