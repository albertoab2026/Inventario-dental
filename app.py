import streamlit as st
import pandas as pd
import boto3
from datetime import datetime
import pytz
import time
import io

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Sistema Dental Tío - PRO", layout="wide")

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
    tabla_auditoria = dynamodb.Table('EntradasInventario')
except Exception as e:
    st.error(f"Error AWS: {e}")
    st.stop()

# ESTADOS DE SESIÓN
if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'confirmar' not in st.session_state: st.session_state.confirmar = False
if 'autenticado' not in st.session_state: st.session_state.autenticado = False

# CARGAR STOCK
try:
    items = tabla_stock.scan().get('Items', [])
    df_stock = pd.DataFrame(items) if items else pd.DataFrame(columns=['Producto', 'Stock', 'Precio'])
except:
    df_stock = pd.DataFrame(columns=['Producto', 'Stock', 'Precio'])

st.title("🦷 Sistema Dental: Control de Ventas")

# --- SECCIÓN A: STOCK ---
with st.expander("📦 Inventario Actual"):
    if not df_stock.empty:
        df_stock['Stock'] = pd.to_numeric(df_stock['Stock'])
        st.dataframe(df_stock[['Producto', 'Stock', 'Precio']], use_container_width=True, hide_index=True)

st.divider()

# --- SECCIÓN B: CARRITO ---
st.subheader("🛒 Punto de Venta")
if not df_stock.empty:
    c1, c2, c3 = st.columns([3, 1, 1])
    with c1:
        prod_sel = st.selectbox("Producto:", df_stock['Producto'].tolist())
    with c2:
        cant_sel = st.number_input("Cantidad:", min_value=1, value=1)
    with c3:
        st.write("##")
        if st.button("➕ Añadir"):
            # BLOQUEO DE SOBRE-VENTA
            stock_actual = int(df_stock.loc[df_stock['Producto'] == prod_sel, 'Stock'].values[0])
            if cant_sel <= stock_actual:
                precio = float(df_stock.loc[df_stock['Producto'] == prod_sel, 'Precio'].values[0])
                st.session_state.carrito.append({
                    'Producto': prod_sel, 'Cantidad': cant_sel,
                    'Precio': precio, 'Subtotal': round(precio * cant_sel, 2)
                })
            else:
                st.error(f"Stock insuficiente ({stock_actual} disp.)")

if st.session_state.carrito:
    df_car = pd.DataFrame(st.session_state.carrito)
    st.table(df_car)
    total_car = df_car['Subtotal'].sum()
    st.markdown(f"### **TOTAL: S/ {total_car:.2f}**")
    v_metodo = st.radio("Pago:", ["Yape", "Plin", "Efectivo"], horizontal=True)
    
    cv1, cv2 = st.columns(2)
    with cv1:
        if st.button("🚀 PROCESAR VENTA", type="primary", use_container_width=True):
            st.session_state.confirmar = True
    with cv2:
        if st.button("🗑️ VACÍAR", use_container_width=True):
            st.session_state.carrito = []; st.rerun()

    if st.session_state.confirmar:
        st.warning(f"¿Confirmar venta por S/ {total_car:.2f}?")
        if st.button("✅ SÍ, FINALIZAR"):
            fecha, hora = obtener_tiempo_peru()
            for item in st.session_state.carrito:
                res = tabla_stock.get_item(Key={'Producto': item['Producto']})
                n_stock = int(res['Item']['Stock']) - item['Cantidad']
                tabla_stock.update_item(Key={'Producto': item['Producto']}, UpdateExpression="set Stock = :s", ExpressionAttributeValues={':s': n_stock})
                id_v = f"V-{fecha.replace('/','')}-{hora.replace(':','')}-{item['Producto'][:3]}"
                tabla_ventas.put_item(Item={
                    'ID_Venta': id_v, 'Fecha': fecha, 'Hora': hora, 'Producto': item['Producto'],
                    'Cantidad': int(item['Cantidad']), 'Total': str(item['Subtotal']), 'Metodo': v_metodo
                })
            st.balloons(); st.session_state.carrito = []; st.session_state.confirmar = False
            st.success("Venta completada"); time.sleep(1); st.rerun()

st.divider()

# --- SECCIÓN C: ADMIN (CON CIERRE DE SESIÓN) ---
if not st.session_state.autenticado:
    with st.expander("🔐 Ingresar al Panel de Control"):
        ingreso_pass = st.text_input("Contraseña:", type="password")
        if st.button("Entrar"):
            if ingreso_pass == admin_pass:
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("Clave incorrecta")
else:
    # BOTÓN CERRAR SESIÓN (Arriba para que se vea)
    if st.button("🔓 CERRAR SESIÓN (Salir del Admin)"):
        st.session_state.autenticado = False
        st.rerun()

    st.subheader("📊 Reportes y Gestión")
    t1, t2 = st.tabs(["💰 Ganancias Hoy", "📥 Mercadería e Historial"])
    
    with t1:
        fecha_hoy, _ = obtener_tiempo_peru()
        ventas = tabla_ventas.scan().get('Items', [])
        df_hoy = pd.DataFrame([v for v in ventas if v['Fecha'] == fecha_hoy])
        if not df_hoy.empty:
            df_hoy['Total'] = pd.to_numeric(df_hoy['Total'])
            st.metric("TOTAL CAJA", f"S/ {df_hoy['Total'].sum():.2f}")
            st.write("**Detalle de ventas:**")
            st.dataframe(df_hoy[['Hora', 'Producto', 'Total', 'Metodo']], use_container_width=True, hide_index=True)
        else: st.info("Sin ventas hoy.")

    with t2:
        st.write("### Registrar llegada de productos")
        with st.form("abastecimiento"):
            f_p = st.selectbox("Producto:", df_stock['Producto'].tolist()) if not df_stock.empty else st.text_input("Nombre")
            f_cant = st.number_input("Cantidad entrante:", min_value=1)
            f_precio = st.number_input("Precio venta actual:", min_value=0.0)
            if st.form_submit_button("Guardar Ingreso"):
                res = tabla_stock.get_item(Key={'Producto': f_p})
                s_final = (int(res['Item']['Stock']) if 'Item' in res else 0) + f_cant
                tabla_stock.put_item(Item={'Producto': f_p, 'Stock': s_final, 'Precio': str(f_precio)})
                
                # AUDITORÍA (LIMPIA SIN NONE)
                f, h = obtener_tiempo_peru()
                tabla_auditoria.put_item(Item={
                    'ID_Ingreso': f"IN-{f.replace('/','')}-{h.replace(':','')}",
                    'Fecha': f, 'Hora': h, 'Producto': f_p,
                    'Cantidad_Entrante': int(f_cant), 'Stock_Resultante': int(s_final), 'Precio_Fijado': str(f_precio)
                })
                st.success("Inventario actualizado"); time.sleep(1); st.rerun()

        st.divider()
        st.write("### Historial de Stock (Ordenado)")
        ingresos_raw = tabla_auditoria.scan().get('Items', [])
        if ingresos_raw:
            df_ing = pd.DataFrame(ingresos_raw)
            # Limpiamos columnas None para que no se vea feo
            df_ing = df_ing.dropna(axis=1, how='all').fillna('-')
            # Ordenamos por Fecha y Hora (Lo más nuevo primero)
            df_ing = df_ing.sort_values(by=['Fecha', 'Hora'], ascending=False)
            st.dataframe(df_ing, use_container_width=True, hide_index=True)
