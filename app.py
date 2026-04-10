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
    # Usamos milisegundos para que el ID sea único siempre
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

# 3. ESTADOS
if 'sesion_iniciada' not in st.session_state: st.session_state.sesion_iniciada = False
if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'boleta' not in st.session_state: st.session_state.boleta = None

if not st.session_state.sesion_iniciada:
    st.markdown("<h1 style='text-align: center;'>🦷</h1>", unsafe_allow_html=True)
    st.title("Sistema Dental BALLARTA")
    clave = st.text_input("Clave:", type="password")
    if st.button("Ingresar"):
        if clave == admin_pass:
            st.session_state.sesion_iniciada = True
            st.rerun()
    st.stop()

# CARGAR STOCK GLOBAL
def get_df_stock():
    try:
        items = tabla_stock.scan().get('Items', [])
        if items:
            df = pd.DataFrame(items)
            df['Stock'] = pd.to_numeric(df['Stock'])
            df['Precio'] = pd.to_numeric(df['Precio'])
            return df.sort_values(by='Producto')
    except: pass
    return pd.DataFrame(columns=['Producto', 'Stock', 'Precio'])

df_stock = get_df_stock()

t1, t2, t3, t4, t5, t6 = st.tabs(["🛒 Venta", "📦 Stock", "📊 Reportes", "📋 Historial", "📥 Cargar", "🛠️ Mant."])

# --- VENTA ---
with t1:
    if st.session_state.boleta:
        b = st.session_state.boleta
        st.success("✅ Venta realizada con éxito")
        st.markdown(f"**Total: S/ {b['total']:.2f}**")
        if st.button("Nueva Venta"):
            st.session_state.boleta = None
            st.rerun()
    else:
        with st.container():
            col1, col2 = st.columns([2,1])
            with col1:
                p_sel = st.selectbox("Producto:", df_stock['Producto'].tolist() if not df_stock.empty else [])
            with col2:
                cant = st.number_input("Cant:", min_value=1, value=1)
            
            if st.button("Añadir"):
                item_data = df_stock[df_stock['Producto'] == p_sel].iloc[0]
                st.session_state.carrito.append({'Producto': p_sel, 'Cantidad': cant, 'Precio': item_data['Precio'], 'Subtotal': item_data['Precio']*cant})
                st.rerun()

        if st.session_state.carrito:
            st.table(pd.DataFrame(st.session_state.carrito))
            total = sum(i['Subtotal'] for i in st.session_state.carrito)
            st.subheader(f"Total: S/ {total:.2f}")
            if st.button("Finalizar"):
                f, h, _, _ = obtener_tiempo_peru()
                st.session_state.boleta = {'total': total, 'fecha': f, 'hora': h, 'items': st.session_state.carrito, 'metodo': 'Efectivo'}
                for i in st.session_state.carrito:
                    # Actualizar Stock
                    nuevo_s = int(df_stock[df_stock['Producto'] == i['Producto']]['Stock'].values[0]) - i['Cantidad']
                    tabla_stock.update_item(Key={'Producto': i['Producto']}, UpdateExpression="set Stock = :s", ExpressionAttributeValues={':s': nuevo_s})
                st.session_state.carrito = []
                st.rerun()

# --- STOCK ---
with t2:
    st.dataframe(df_stock, use_container_width=True)

# --- REPORTES ---
with t3:
    st.subheader("Ventas del día")
    ventas = tabla_ventas.scan().get('Items', [])
    if ventas:
        df_v = pd.DataFrame(ventas)
        st.dataframe(df_v)
        # Botón Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_v.to_excel(writer, index=False)
        st.download_button("Descargar Excel", output.getvalue(), "ventas.xlsx")

# --- HISTORIAL ---
with t4:
    st.subheader("Historial de Entradas")
    try:
        hist = tabla_auditoria.scan().get('Items', [])
        if hist:
            df_h = pd.DataFrame(hist)
            st.dataframe(df_h, use_container_width=True)
            # Botón Excel
            out_h = io.BytesIO()
            with pd.ExcelWriter(out_h, engine='xlsxwriter') as writer:
                df_h.to_excel(writer, index=False)
            st.download_button("Descargar Historial Excel", out_h.getvalue(), "historial.xlsx")
    except: st.info("No hay registros.")

# --- CARGAR STOCK ---
with t5:
    st.subheader("Cargar Mercadería")
    with st.form("f_carga"):
        p_ex = st.selectbox("Existente:", [""] + df_stock['Producto'].tolist() if not df_stock.empty else [""])
        p_nu = st.text_input("Nuevo:").upper()
        p_fin = p_nu if p_nu else p_ex
        c_in = st.number_input("Cantidad:", min_value=1)
        pr_in = st.number_input("Precio:", min_value=0.1)
        
        if st.form_submit_button("REGISTRAR"):
            if p_fin:
                f, h, _, uid = obtener_tiempo_peru()
                s_act = int(df_stock[df_stock['Producto'] == p_fin]['Stock'].values[0]) if p_fin in df_stock['Producto'].values else 0
                nuevo_s = s_act + c_in
                # Guardar con ID Único (Timestamp con milisegundos)
                tabla_stock.put_item(Item={'Producto': p_fin, 'Stock': nuevo_s, 'Precio': str(pr_in)})
                tabla_auditoria.put_item(Item={
                    'ID_Ingreso': f"ING-{uid}", 
                    'Fecha': f, 'Hora': h, 
                    'Producto': p_fin, 
                    'Cantidad_Entrante': int(c_in), 
                    'Stock_Resultante': int(nuevo_s)
                })
                st.success(f"Registrado: {p_fin}")
                time.sleep(1)
                st.rerun()

# --- MANTENIMIENTO ---
with t6:
    if not df_stock.empty:
        p_del = st.selectbox("Eliminar:", df_stock['Producto'].tolist())
        if st.button("Eliminar Producto"):
            tabla_stock.delete_item(Key={'Producto': p_del})
            st.rerun()
