import streamlit as st
import pandas as pd
import boto3
from datetime import datetime
import pytz
from boto3.dynamodb.conditions import Attr

# --- 0. CONFIGURACIÓN ---
TABLA_STOCK = 'SaaS_Stock_Test'
TABLA_VENTAS = 'SaaS_Ventas_Test'
TABLA_MOVS = 'SaaS_Movimientos_Test'

st.set_page_config(page_title="NEXUS BALLARTA SaaS", layout="wide", page_icon="🚀")
tz_peru = pytz.timezone('America/Lima')

def obtener_tiempo_peru():
    ahora = datetime.now(tz_peru)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%H:%M:%S"), ahora.strftime("%Y%m%d%H%M%S%f")

try:
    dynamodb = boto3.resource('dynamodb', 
                              region_name=st.secrets["aws"]["aws_region"],
                              aws_access_key_id=st.secrets["aws"]["aws_access_key_id"],
                              aws_secret_access_key=st.secrets["aws"]["aws_secret_access_key"])
    tabla_stock = dynamodb.Table(TABLA_STOCK)
    tabla_ventas = dynamodb.Table(TABLA_VENTAS)
    tabla_movs = dynamodb.Table(TABLA_MOVS)
except Exception as e:
    st.error(f"Error AWS: {e}"); st.stop()

def registrar_kardex(producto, cantidad, tipo):
    f, h, uid = obtener_tiempo_peru()
    tabla_movs.put_item(Item={
        'TenantID': st.session_state.tenant,
        'MovID': f"M-{uid}",
        'Fecha': f, 'Hora': h,
        'Producto': producto,
        'Cantidad': int(cantidad),
        'Tipo': tipo
    })

if 'auth' not in st.session_state: st.session_state.auth = False
if 'tenant' not in st.session_state: st.session_state.tenant = None
if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'boleta' not in st.session_state: st.session_state.boleta = None
def obtener_datos():
    res = tabla_stock.scan(FilterExpression=Attr('TenantID').eq(st.session_state.tenant))
    df = pd.DataFrame(res.get('Items', []))
    if df.empty: return pd.DataFrame(columns=['Producto', 'Precio_Compra', 'Precio', 'Stock'])
    df['Stock'] = pd.to_numeric(df['Stock'], errors='coerce').fillna(0).astype(int)
    df['Precio'] = pd.to_numeric(df['Precio'], errors='coerce').fillna(0.0)
    df['Precio_Compra'] = pd.to_numeric(df['Precio_Compra'], errors='coerce').fillna(0.0)
    return df[['Producto', 'Precio_Compra', 'Precio', 'Stock']].sort_values('Producto')

df_inv = obtener_datos()
t1, t2, t3, t4, t5, t6 = st.tabs(["🛒 VENTA", "📦 STOCK", "📊 REPORTES", "📋 HISTORIAL", "📥 CARGAR", "🛠️ MANT."])

with t2: # STOCK CON LETRA ROJA
    st.subheader("📦 Inventario de Almacén")
    def resaltar_stock(row):
        return ['color: #ff4b4b; font-weight: bold;'] * len(row) if row.Stock < 5 else [''] * len(row)
    
    st.dataframe(df_inv.style.apply(resaltar_stock, axis=1), use_container_width=True, hide_index=True)
with t3: # REPORTES SEPARADOS
    st.subheader("📊 Reporte de Ganancias")
    f_sel = st.date_input("Día:", datetime.now(tz_peru)).strftime("%d/%m/%Y")
    res_v = tabla_ventas.scan(FilterExpression=Attr('TenantID').eq(st.session_state.tenant) & Attr('Fecha').eq(f_sel))
    v_data = res_v.get('Items', [])
    
    if v_data:
        df_v = pd.DataFrame(v_data)
        for col in ['Total', 'Precio_Compra', 'Cantidad']: df_v[col] = pd.to_numeric(df_v[col])
        
        # Totales por método
        efectivo = df_v[df_v['Metodo'].str.contains("EFECTIVO", na=False)]['Total'].sum()
        yape = df_v[df_v['Metodo'].str.contains("YAPE", na=False)]['Total'].sum()
        plin = df_v[df_v['Metodo'].str.contains("PLIN", na=False)]['Total'].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("💵 EFECTIVO", f"S/ {efectivo:.2f}")
        c2.metric("🟣 YAPE", f"S/ {yape:.2f}")
        c3.metric("🔵 PLIN", f"S/ {plin:.2f}")
        
        st.write("---")
        total_dia = df_v['Total'].sum()
        st.subheader(f"Total Neto del Día: S/ {total_dia:.2f}")
        st.dataframe(df_v[['Hora', 'Producto', 'Cantidad', 'Total', 'Metodo']], use_container_width=True, hide_index=True)
with t6: # MANTENIMIENTO PROTEGIDO
    st.subheader("🛠️ Reposición de Mercadería")
    st.info("⚠️ En esta sección solo se puede SUMAR stock nuevo. Los ajustes manuales deben ser autorizados.")
    
    if not df_inv.empty:
        p_edit = st.selectbox("Producto a Reponer:", df_inv['Producto'].tolist())
        stock_actual = int(df_inv[df_inv['Producto'] == p_edit]['Stock'].values[0])
        
        cant_mas = st.number_input("¿Cuántas unidades están ingresando?", min_value=1, value=1)
        
        if st.button("✅ REGISTRAR INGRESO"):
            nuevo_total = stock_actual + cant_mas
            # Actualizar AWS
            tabla_stock.update_item(
                Key={'TenantID': st.session_state.tenant, 'Producto': p_edit},
                UpdateExpression="SET Stock = :s",
                ExpressionAttributeValues={':s': nuevo_total}
            )
            # Guardar quien y cuanto entró en el historial
            registrar_kardex(p_edit, cant_mas, f"REPOSICIÓN (+{cant_mas})")
            
            st.success(f"¡Hecho! El nuevo stock de {p_edit} es {nuevo_total}")
            st.rerun()

with st.sidebar:
    if st.session_state.auth:
        st.title(f"🏢 {st.session_state.tenant}")
        if st.button("🔴 CERRAR SESIÓN"): st.session_state.auth = False; st.rerun()
