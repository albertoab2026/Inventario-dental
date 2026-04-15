import streamlit as st
import pandas as pd
import boto3
from datetime import datetime
import pytz
from boto3.dynamodb.conditions import Attr

# ==========================================
# 1. CONFIGURACIÓN DE MARCA Y PÁGINA
# ==========================================
MARCA_SaaS = "NEXUS BALLARTA SaaS"
st.set_page_config(page_title=MARCA_SaaS, layout="wide", page_icon="🚀")

TABLA_VENTAS_NAME = 'SaaS_Ventas_Test'
TABLA_STOCK_NAME = 'SaaS_Stock_Test'
tz_peru = pytz.timezone('America/Lima')

def obtener_tiempo_peru():
    ahora = datetime.now(tz_peru)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%H:%M:%S"), ahora, ahora.strftime("%Y%m%d%H%M%S%f")

# ==========================================
# 2. CONEXIÓN SEGURA AWS
# ==========================================
try:
    aws_id = st.secrets["aws"]["aws_access_key_id"].strip()
    aws_key = st.secrets["aws"]["aws_secret_access_key"].strip()
    aws_region = st.secrets["aws"]["aws_region"].strip()
    aws_token = st.secrets["aws"].get("aws_session_token", None)
    
    dynamodb = boto3.resource('dynamodb', region_name=aws_region,
                              aws_access_key_id=aws_id,
                              aws_secret_access_key=aws_key,
                              aws_session_token=aws_token)
    
    tabla_ventas = dynamodb.Table(TABLA_VENTAS_NAME)
    tabla_stock = dynamodb.Table(TABLA_STOCK_NAME)
except Exception as e:
    st.error(f"Error de conexión AWS: {e}")
    st.stop()

# ==========================================
# 3. CONTROL DE ESTADOS
# ==========================================
if 'sesion_iniciada' not in st.session_state: st.session_state.sesion_iniciada = False
if 'tenant_id' not in st.session_state: st.session_state.tenant_id = None
if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'boleta' not in st.session_state: st.session_state.boleta = None
if 'reset_v' not in st.session_state: st.session_state.reset_v = 0
if 'df_stock_local' not in st.session_state: st.session_state.df_stock_local = pd.DataFrame()

def actualizar_stock_local():
    try:
        response = tabla_stock.scan(FilterExpression=Attr('TenantID').eq(st.session_state.tenant_id))
        items = response.get('Items', [])
        if items:
            df = pd.DataFrame(items)
            for col in ['Stock', 'Precio', 'P_Compra_U']:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            df['Stock'] = df['Stock'].astype(int)
            df['Producto'] = df['Producto'].astype(str).str.upper().str.strip()
            st.session_state.df_stock_local = df.sort_values(by='Producto')
        else:
            st.session_state.df_stock_local = pd.DataFrame(columns=['Producto', 'Stock', 'Precio', 'P_Compra_U'])
    except:
        st.session_state.df_stock_local = pd.DataFrame(columns=['Producto', 'Stock', 'Precio', 'P_Compra_U'])

# ==========================================
# 4. LOGIN MULTIUSUARIO
# ==========================================
if not st.session_state.sesion_iniciada:
    st.markdown(f"<h1 style='text-align: center; color: #3498DB;'>{MARCA_SaaS}</h1>", unsafe_allow_html=True)
    auth_multi = st.secrets.get("auth_multi", {})
    locales = list(auth_multi.keys())
    col1, _ = st.columns([1, 1])
    with col1:
        st.subheader("🔑 Acceso")
        local_sel = st.selectbox("Empresa:", locales)
        clave = st.text_input("Contraseña:", type="password")
        if st.button("🔓 Entrar", use_container_width=True):
            if local_sel in auth_multi and clave == auth_multi[local_sel].strip():
                st.session_state.sesion_iniciada = True
                st.session_state.tenant_id = local_sel
                actualizar_stock_local()
                st.rerun()
            else: st.error("Contraseña incorrecta.")
    st.stop()
with st.sidebar:
    st.markdown(f"### {MARCA_SaaS}")
    st.info(f"🏢 {st.session_state.tenant_id}")
    if st.button("🔴 CERRAR SESIÓN"):
        st.session_state.sesion_iniciada = False
        st.rerun()

tabs = st.tabs(["🛒 VENTA", "📦 STOCK", "📊 REPORTES", "📋 HISTORIAL", "📥 CARGAR", "🛠️ MANT."])
df_stock = st.session_state.df_stock_local

# --- PESTAÑA VENTA ---
with tabs[0]:
    if st.session_state.boleta:
        b = st.session_state.boleta
        st.success("✅ VENTA REALIZADA")
        items_html = ''.join([f'<p>{i["Cantidad"]} x {i["Producto"]} - S/ {i["Subtotal"]:.2f}</p>' for i in b['items']])
        st.markdown(f"<div style='background-color: white; color: black; padding: 20px; border: 2px solid black; max-width: 320px; margin: auto; font-family: monospace;'><center><b>{st.session_state.tenant_id}</b><br>{b['fecha']}</center><hr>{items_html}<hr><h3>TOTAL: S/ {b['total_neto']:.2f}</h3></div>", unsafe_allow_html=True)
        if st.button("⬅️ NUEVA VENTA"): st.session_state.boleta = None; st.rerun()
    else:
        st.subheader("Punto de Venta")
        bus_v = st.text_input("🔍 Buscar Producto:", key="bus_v").upper()
        prod_filt = [p for p in df_stock['Producto'].tolist() if bus_v in p]
        c1, c2 = st.columns(2)
        with c1:
            if prod_filt:
                p_sel = st.selectbox("Seleccionar:", prod_filt, key=f"v_{st.session_state.reset_v}")
                info = df_stock[df_stock['Producto'] == p_sel].iloc[0]
                st.write(f"Stock: **{info['Stock']}** | Precio: **S/ {info['Precio']:.2f}**")
            else: st.warning("Sin resultados.")
        with c2: cant = st.number_input("Cantidad:", min_value=1, value=1, key=f"c_{st.session_state.reset_v}")
        
        if st.button("➕ AÑADIR AL CARRITO", use_container_width=True) and prod_filt:
            if cant <= info['Stock']:
                st.session_state.carrito.append({'Producto': p_sel, 'Cantidad': int(cant), 'Precio': float(info['Precio']), 'P_Compra_U': float(info['P_Compra_U']), 'Subtotal': round(float(info['Precio']) * cant, 2), 'TenantID': st.session_state.tenant_id})
                st.session_state.reset_v += 1; st.rerun()
            else: st.error("Stock insuficiente.")
        
        if st.session_state.carrito:
            df_c = pd.DataFrame(st.session_state.carrito)
            st.table(df_c[['Producto', 'Cantidad', 'Subtotal']])
            if st.button("🚀 FINALIZAR VENTA"):
                f, h, dt, idv = obtener_tiempo_peru()
                total = df_c['Subtotal'].sum()
                try:
                    tabla_ventas.put_item(Item={'VentaID': idv, 'TenantID': st.session_state.tenant_id, 'Fecha': f, 'Total': str(total), 'Items': st.session_state.carrito})
                    for item in st.session_state.carrito:
                        tabla_stock.update_item(
                            Key={'Producto': item['Producto'], 'TenantID': st.session_state.tenant_id}, 
                            UpdateExpression="SET Stock = Stock - :v", 
                            ExpressionAttributeValues={':v': item['Cantidad']}
                        )
                    st.session_state.boleta = {'fecha': f, 'items': st.session_state.carrito, 'total_neto': total}
                    st.session_state.carrito = []; actualizar_stock_local(); st.rerun()
                except Exception as e: st.error(f"Error en AWS: {e}")
# --- PESTAÑA STOCK, REPORTES, HISTORIAL ---
with tabs[1]: 
    st.subheader("📦 Inventario Actual")
    st.dataframe(df_stock, use_container_width=True)

with tabs[2]: 
    st.info("📊 Reportes Nexus próximamente (Análisis de utilidades y ventas).")

with tabs[3]: 
    st.info("📋 Historial de Movimientos próximamente.")

# --- PESTAÑA CARGAR (SOLUCIÓN ERROR DE DUPLICADOS) ---
with tabs[4]:
    st.subheader("📥 Carga de Mercadería")
    c_i, c_m = st.columns(2)
    with c_i:
        st.write("✍️ Registro Individual")
        with st.form("f_ind"):
            ni = st.text_input("Nombre del Producto:").upper().strip()
            si = st.number_input("Stock Inicial:", min_value=0)
            pi = st.number_input("Precio Venta:", min_value=0.0)
            ci = st.number_input("Precio Compra:", min_value=0.0)
            if st.form_submit_button("Guardar"):
                if ni:
                    tabla_stock.put_item(Item={
                        'Producto': ni, 
                        'TenantID': st.session_state.tenant_id, 
                        'Stock': int(si), 
                        'Precio': str(pi), 
                        'P_Compra_U': str(ci)
                    })
                    st.success("¡Producto Guardado!"); actualizar_stock_local(); st.rerun()
    
    with c_m:
        st.write("📂 Carga Masiva (Excel/CSV)")
        archivo = st.file_uploader("Subir archivo:", type=['csv', 'xlsx'])
        if archivo:
            try:
                df_m = pd.read_csv(archivo) if archivo.name.endswith('.csv') else pd.read_excel(archivo)
                
                # --- LIMPIEZA CLAVE: Elimina duplicados para evitar el error de AWS ---
                df_m['Producto'] = df_m['Producto'].astype(str).str.upper().str.strip()
                df_m = df_m.drop_duplicates(subset=['Producto']) 
                
                st.write(f"Registros únicos a subir: {len(df_m)}")
                st.dataframe(df_m.head(3))
                
                if st.button("🚀 INICIAR CARGA MASIVA"):
                    with tabla_stock.batch_writer() as batch:
                        for _, r in df_m.iterrows():
                            batch.put_item(Item={
                                'Producto': r['Producto'], 
                                'TenantID': st.session_state.tenant_id, 
                                'Stock': int(r.get('Stock', 0)), 
                                'Precio': str(r.get('Precio', 0)), 
                                'P_Compra_U': str(r.get('P_Compra_U', 0))
                            })
                    st.success("¡Carga terminada con éxito!"); actualizar_stock_local(); st.rerun()
            except Exception as e:
                st.error(f"Error procesando archivo: {e}")

# --- PESTAÑA MANTENIMIENTO (LLAVE COMPUESTA) ---
with tabs[5]:
    st.subheader("🛠️ Gestión de Inventario")
    if not df_stock.empty:
        p_lista = df_stock['Producto'].tolist()
        pm = st.selectbox("Seleccione producto para editar/borrar:", p_lista)
        im = df_stock[df_stock['Producto'] == pm].iloc[0]
        
        c_m1, c_m2 = st.columns(2)
        with c_m1:
            st.write("🔄 **Actualizar**")
            nv = st.number_input("Nuevo Precio Venta:", value=float(im['Precio']))
            nc = st.number_input("Nuevo Precio Compra:", value=float(im['P_Compra_U']))
            if st.button("🔄 ACTUALIZAR DATOS"):
                tabla_stock.update_item(
                    Key={'Producto': pm, 'TenantID': st.session_state.tenant_id}, 
                    UpdateExpression="SET Precio = :v, P_Compra_U = :c", 
                    ExpressionAttributeValues={':v': str(nv), ':c': str(nc)}
                )
                st.success("Actualizado"); actualizar_stock_local(); st.rerun()
        
        with c_m2:
            st.write("🗑️ **Eliminar**")
            st.warning(f"¿Borrar permanentemente {pm}?")
            if st.button("❌ ELIMINAR AHORA"):
                tabla_stock.delete_item(Key={'Producto': pm, 'TenantID': st.session_state.tenant_id})
                st.error("Producto eliminado"); actualizar_stock_local(); st.rerun()
    else:
        st.info("No hay productos cargados.")
