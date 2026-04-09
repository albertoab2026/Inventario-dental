import streamlit as st
import pandas as pd
import boto3
from datetime import datetime
import pytz
import time
import io

# 1. CONFIGURACIÓN Y TIEMPO
st.set_page_config(page_title="Gestión Dental Tío - PRO", layout="wide")

def obtener_tiempo_peru():
    tz_peru = pytz.timezone('America/Lima')
    ahora = datetime.now(tz_peru)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%H:%M:%S")

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
except Exception as e:
    st.error(f"Error AWS: {e}")
    st.stop()

# LÓGICA DEL CARRITO
if 'carrito' not in st.session_state:
    st.session_state.carrito = []
if 'confirmar' not in st.session_state:
    st.session_state.confirmar = False

# CARGAR STOCK
try:
    items = tabla_stock.scan().get('Items', [])
    df_stock = pd.DataFrame(items) if items else pd.DataFrame(columns=['Producto', 'Stock', 'Precio'])
except:
    df_stock = pd.DataFrame(columns=['Producto', 'Stock', 'Precio'])

st.title("🦷 Punto de Venta Dental")

# --- SECCIÓN A: INVENTARIO ---
with st.expander("📦 Ver Stock Disponible"):
    if not df_stock.empty:
        df_stock['Stock'] = pd.to_numeric(df_stock['Stock'])
        st.dataframe(df_stock[['Producto', 'Stock', 'Precio']], use_container_width=True, hide_index=True)

st.divider()

# --- SECCIÓN B: CARRITO ---
st.subheader("🛒 Carrito de Compras")
col_sel, col_cant, col_btn = st.columns([3, 1, 1])

if not df_stock.empty:
    with col_sel:
        prod_sel = st.selectbox("Producto:", df_stock['Producto'].tolist())
    with col_cant:
        cant_sel = st.number_input("Cantidad:", min_value=1, value=1)
    with col_btn:
        st.write("##")
        if st.button("➕ Añadir"):
            precio = float(df_stock.loc[df_stock['Producto'] == prod_sel, 'Precio'].values[0])
            st.session_state.carrito.append({
                'Producto': prod_sel, 'Cantidad': cant_sel,
                'Precio': precio, 'Subtotal': round(precio * cant_sel, 2)
            })
            st.session_state.confirmar = False # Reset confirmación al añadir

if st.session_state.carrito:
    df_car = pd.DataFrame(st.session_state.carrito)
    st.table(df_car)
    total_car = df_car['Subtotal'].sum()
    st.markdown(f"### **TOTAL: S/ {total_car:.2f}**")
    
    v_metodo = st.radio("Método de Pago:", ["Yape", "Plin", "Efectivo"], horizontal=True)
    
    c_v1, c_v2 = st.columns(2)
    with c_v1:
        # PRIMER BOTÓN: PIDE CONFIRMACIÓN
        if st.button("🚀 PROCESAR VENTA", use_container_width=True, type="primary"):
            st.session_state.confirmar = True

    with c_v2:
        if st.button("🗑️ VACÍAR CARRITO", use_container_width=True):
            st.session_state.carrito = []
            st.session_state.confirmar = False
            st.rerun()

    # BLOQUE DE CONFIRMACIÓN (Solo aparece si dio clic a Procesar)
    if st.session_state.confirmar:
        st.warning(f"⚠️ **¿ESTÁ SEGURO?** Se descontará el stock y se registrará el ingreso de **S/ {total_car:.2f}**.")
        if st.button("✅ SÍ, CONFIRMAR COMPRA FINAL", use_container_width=True):
            try:
                fecha, hora = obtener_tiempo_peru()
                for item in st.session_state.carrito:
                    # 1. Descontar en AWS
                    res = tabla_stock.get_item(Key={'Producto': item['Producto']})
                    n_stock = int(res['Item']['Stock']) - item['Cantidad']
                    tabla_stock.update_item(
                        Key={'Producto': item['Producto']},
                        UpdateExpression="set Stock = :s",
                        ExpressionAttributeValues={':s': n_stock}
                    )
                    # 2. Registrar Venta
                    id_v = f"V-{fecha.replace('/','')}-{hora.replace(':','')}-{item['Producto'][:3]}"
                    tabla_ventas.put_item(Item={
                        'ID_Venta': id_v, 'Fecha': fecha, 'Hora': hora,
                        'Producto': item['Producto'], 'Cantidad': int(item['Cantidad']),
                        'Total': str(item['Subtotal']), 'Metodo': v_metodo
                    })
                
                st.balloons()
                st.session_state.carrito = []
                st.session_state.confirmar = False
                st.success("Venta completada con éxito.")
                time.sleep(1.5)
                st.rerun()
            except Exception as e:
                st.error(f"Error al grabar: {e}")

st.write("##")
st.divider()

# --- SECCIÓN C: GANANCIAS ---
with st.expander("🔐 PANEL ADMIN Y CIERRE DE CAJA"):
    password = st.text_input("Clave:", type="password")
    if password == admin_pass:
        fecha_hoy, _ = obtener_tiempo_peru()
        st.subheader(f"💰 Ganancias de Hoy: {fecha_hoy}")
        
        try:
            ventas_raw = tabla_ventas.scan().get('Items', [])
            df_hoy = pd.DataFrame([v for v in ventas_raw if v['Fecha'] == fecha_hoy])
            
            if not df_hoy.empty:
                df_hoy['Total'] = pd.to_numeric(df_hoy['Total'])
                total_soles = df_hoy['Total'].sum()
                
                c_m1, c_m2 = st.columns(2)
                c_m1.metric("DINERO EN CAJA", f"S/ {total_soles:.2f}")
                c_m2.metric("N° OPERACIONES", len(df_hoy))
                
                st.write("### Detalle de Ventas")
                st.dataframe(df_hoy[['Hora', 'Producto', 'Total', 'Metodo']], use_container_width=True, hide_index=True)
                
                # Botón de Excel
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_hoy.to_excel(writer, index=False)
                st.download_button("📥 Descargar Reporte Excel", output.getvalue(), f"Cierre_{fecha_hoy}.xlsx")
            else:
                st.info("No hay ventas hoy.")
        except: st.error("Error al cargar ganancias.")

        st.divider()
        st.subheader("📥 Actualizar Inventario")
        with st.form("stock_form"):
            f_p = st.selectbox("Elegir Producto:", df_stock['Producto'].tolist()) if not df_stock.empty else st.text_input("Producto")
            f_s = st.number_input("Nuevo Stock Total", min_value=0)
            f_pr = st.number_input("Precio S/", min_value=0.0)
            if st.form_submit_button("Guardar en AWS"):
                tabla_stock.put_item(Item={'Producto': f_p, 'Stock': int(f_s), 'Precio': str(f_pr)})
                st.success("Base de datos actualizada")
                st.rerun()
