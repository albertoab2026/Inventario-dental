import streamlit as st
import pandas as pd
import boto3
from datetime import datetime
import pytz
from boto3.dynamodb.conditions import Attr
import io

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="NEXUS BALLARTA SaaS", layout="wide", page_icon="🚀")
tz_peru = pytz.timezone('America/Lima')

def obtener_info_tiempo():
    ahora = datetime.now(tz_peru)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%H:%M:%S"), ahora.strftime("%Y%m%d%H%M%S%f")

# --- 2. CONEXIÓN AWS ---
try:
    dynamodb = boto3.resource(
        'dynamodb',
        region_name=st.secrets["aws"]["aws_region"],
        aws_access_key_id=st.secrets["aws"]["aws_access_key_id"],
        aws_secret_access_key=st.secrets["aws"]["aws_secret_access_key"]
    )
    t_stock = dynamodb.Table('SaaS_Stock_Test')
    t_ventas = dynamodb.Table('SaaS_Ventas_Test')
except Exception as e:
    st.error(f"Error de conexión AWS: {e}")
    st.stop()

# --- 3. GESTIÓN DE SESIÓN ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'tenant' not in st.session_state: st.session_state.tenant = None
if 'carrito' not in st.session_state: st.session_state.carrito = []

# --- 4. LOGIN ---
if not st.session_state.auth:
    st.markdown("<h1 style='text-align: center;'>🚀 NEXUS BALLARTA SaaS</h1>", unsafe_allow_html=True)
    locales = list(st.secrets.get("auth_multi", {"Demo": ""}).keys())
    local_sel = st.selectbox("Seleccione su Empresa/Local:", locales)
    clave = st.text_input("Contraseña de acceso:", type="password")
    
    if st.button("🔓 Iniciar Sesión", use_container_width=True):
        if clave == "tiotuinventario":
            st.session_state.auth = True
            st.session_state.tenant = local_sel
            st.rerun()
        else:
            st.error("❌ Contraseña incorrecta")
    st.stop()

# --- 5. INTERFAZ PRINCIPAL ---
st.sidebar.title(f"🏢 {st.session_state.tenant}")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.auth = False
    st.rerun()

tabs = st.tabs(["🛒 VENTA", "📦 STOCK", "📊 REPORTES", "📋 HISTORIAL", "📥 CARGA", "🛠️ MANTENIMIENTO"])

# Consulta de Stock para las demás pestañas
res_stock = t_stock.scan(FilterExpression=Attr('TenantID').eq(st.session_state.tenant))
df_stock = pd.DataFrame(res_stock.get('Items', []))

# --- PESTAÑA: CARGA (CON CARGA MASIVA EXCEL/CSV) ---
with tabs[4]:
    st.subheader("📥 Gestión de Carga de Productos")
    
    modo_carga = st.radio("Seleccione método:", ["Individual (Manual)", "Masivo (Excel / CSV)"], horizontal=True)

    if modo_carga == "Individual (Manual)":
        with st.form("form_registro"):
            col1, col2 = st.columns(2)
            with col1:
                nom = st.text_input("Nombre del Producto:").upper().strip()
                stk = st.number_input("Stock Inicial:", min_value=0, step=1)
            with col2:
                p_v = st.number_input("Precio Venta (S/):", min_value=0.0)
                p_c = st.number_input("Precio Compra (S/):", min_value=0.0)
            
            if st.form_submit_button("🚀 Guardar Producto"):
                if nom:
                    t_stock.put_item(Item={
                        'TenantID': st.session_state.tenant,
                        'Producto': nom,
                        'Stock': int(stk),
                        'Precio': str(p_v),
                        'Precio_Compra': str(p_c)
                    })
                    st.success(f"✅ {nom} guardado.")
                    st.rerun()
    
    else:
        st.info("💡 Sube un archivo con 4 columnas: **Producto, Stock, Precio, Precio_Compra**")
        
        # Botón para descargar plantilla de ejemplo
        df_ejemplo = pd.DataFrame(columns=["Producto", "Stock", "Precio", "Precio_Compra"])
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_ejemplo.to_excel(writer, index=False)
        
        st.download_button(
            label="📄 Descargar Plantilla Excel",
            data=buffer.getvalue(),
            file_name="plantilla_carga_nexus.xlsx",
            mime="application/vnd.ms-excel"
        )

        archivo_subido = st.file_uploader("Arrastra tu Excel o CSV aquí", type=['xlsx', 'csv'])
        
        if archivo_subido:
            try:
                if archivo_subido.name.endswith('.csv'):
                    df_masivo = pd.read_csv(archivo_subido)
                else:
                    df_masivo = pd.read_excel(archivo_subido)
                
                st.write("### Vista previa de productos a subir:")
                st.dataframe(df_masivo, use_container_width=True)
                
                if st.button("⬆️ Subir todos los productos a la Nube"):
                    progreso = st.progress(0)
                    total_filas = len(df_masivo)
                    
                    for i, fila in df_masivo.iterrows():
                        t_stock.put_item(Item={
                            'TenantID': st.session_state.tenant,
                            'Producto': str(fila['Producto']).upper().strip(),
                            'Stock': int(fila['Stock']),
                            'Precio': str(fila['Precio']),
                            'Precio_Compra': str(fila['Precio_Compra'])
                        })
                        progreso.progress((i + 1) / total_filas)
                    
                    st.success(f"✅ ¡Éxito! Se han cargado {total_filas} productos.")
                    st.rerun()
            except Exception as e:
                st.error(f"Error en el formato del archivo: {e}")

# --- PESTAÑA: STOCK ---
with tabs[1]:
    st.subheader("📦 Inventario")
    if not df_stock.empty:
        st.dataframe(df_stock[['Producto', 'Stock', 'Precio']], use_container_width=True, hide_index=True)
    else:
        st.warning("Inventario vacío. Usa la pestaña CARGA.")

# --- PESTAÑA: VENTA ---
with tabs[0]:
    st.subheader("🛒 Punto de Venta")
    if not df_stock.empty:
        df_con_stock = df_stock[df_stock['Stock'].astype(int) > 0]
        if not df_con_stock.empty:
            p_sel = st.selectbox("Producto:", df_con_stock['Producto'].tolist())
            datos_p = df_con_stock[df_con_stock['Producto'] == p_sel].iloc[0]
            st.metric("Precio", f"S/ {datos_p['Precio']}")
            cant = st.number_input("Cantidad:", min_value=1, max_value=int(datos_p['Stock']), value=1)
            
            if st.button("➕ Añadir"):
                st.session_state.carrito.append({
                    'Producto': p_sel, 'Cantidad': int(cant), 
                    'Precio': float(datos_p['Precio']), 'Subtotal': round(float(datos_p['Precio']) * cant, 2)
                })
                st.rerun()

        if st.session_state.carrito:
            df_car = pd.DataFrame(st.session_state.carrito)
            st.table(df_car)
            if st.button("🚀 FINALIZAR VENTA"):
                f, h, uid = obtener_info_tiempo()
                t_ventas.put_item(Item={
                    'TenantID': st.session_state.tenant, 'VentaID': f"V-{uid}",
                    'Fecha': f, 'Hora': h, 'Total': str(df_car['Subtotal'].sum())
                })
                for item in st.session_state.carrito:
                    t_stock.update_item(
                        Key={'TenantID': st.session_state.tenant, 'Producto': item['Producto']},
                        UpdateExpression="SET Stock = Stock - :val",
                        ExpressionAttributeValues={':val': int(item['Cantidad'])}
                    )
                st.session_state.carrito = []
                st.success("Venta realizada.")
                st.rerun()

# --- PESTAÑA: MANTENIMIENTO ---
with tabs[5]:
    st.subheader("🛠️ Mantenimiento")
    if not df_stock.empty:
        p_mant = st.selectbox("Seleccione producto para borrar:", df_stock['Producto'].tolist())
        if st.button("🗑️ Borrar Producto"):
            t_stock.delete_item(Key={'TenantID': st.session_state.tenant, 'Producto': p_mant})
            st.rerun()
