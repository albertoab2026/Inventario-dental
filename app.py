import streamlit as st
import pandas as pd
import boto3
import time
import io
from datetime import datetime, timedelta
from decimal import Decimal

# --- 1. CONEXIÓN AWS ---
try:
    session = boto3.Session(
        aws_access_key_id=st.secrets["aws"]["aws_access_key_id"],
        aws_secret_access_key=st.secrets["aws"]["aws_secret_access_key"],
        region_name=st.secrets["aws"]["aws_region"]
    )
    dynamodb = session.resource('dynamodb')
    tabla_inventario = dynamodb.Table('Inventariodentaltio')
    tabla_ventas = dynamodb.Table('VentasDentaltio')
except Exception as e:
    st.error(f"Error AWS: {e}")

# --- 2. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="Inventario Dental Pro", layout="wide")
st.markdown("<h1 style='text-align: center; color: #00acc1;'>🦷 SISTEMA DENTAL - ALBERTO</h1>", unsafe_allow_html=True)

def obtener_tiempo_peru():
    ahora = datetime.utcnow() - timedelta(hours=5)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%H:%M:%S")

def cargar_datos():
    try:
        data = tabla_inventario.scan()["Items"]
        df = pd.DataFrame(data)
        if not df.empty:
            df["Stock_Actual"] = pd.to_numeric(df["Stock_Actual"], errors='coerce').fillna(0).astype(int)
            df["Precio_Venta"] = pd.to_numeric(df["Precio_Venta"], errors='coerce').fillna(0)
            return df.sort_values(by="ID_Producto").reset_index(drop=True)
        return pd.DataFrame()
    except: return pd.DataFrame()

if "df" not in st.session_state: st.session_state.df = cargar_datos()
if "carrito" not in st.session_state: st.session_state.carrito = []
if "admin_logueado" not in st.session_state: st.session_state.admin_logueado = False

# --- 3. INVENTARIO CON ALERTAS ROJAS (RESTAURADO) ---
st.markdown("### 📋 Stock Actual")
df = st.session_state.df
if not df.empty:
    def resaltar_stock(row):
        # Si el stock es 5 o menos, se pone rojo y negrita
        return ['color: #ff1744; font-weight: bold' if row.Stock_Actual <= 5 else '' for _ in row]

    df_view = df.copy()
    df_view["Precio_Venta"] = df_view["Precio_Venta"].map("S/ {:.2f}".format)
    st.dataframe(
        df_view[['ID_Producto', 'Producto', 'Stock_Actual', 'Precio_Venta']].style.apply(resaltar_stock, axis=1),
        use_container_width=True, hide_index=True
    )
    if (df["Stock_Actual"] <= 5).any():
        st.warning("⚠️ Atención: Hay productos con poco stock.")

# --- 4. VENTA Y VACIAR CARRITO ---
st.divider()
if not df.empty:
    c1, c2 = st.columns([2,1])
    prod_sel = c1.selectbox("Producto:", sorted(df["Producto"].tolist()))
    fila = df[df["Producto"] == prod_sel].iloc[0]
    cant = c2.number_input("Cantidad:", min_value=1, max_value=max(1, int(fila["Stock_Actual"])), value=1)
    
    if st.button("➕ AGREGAR AL PEDIDO", use_container_width=True):
        st.session_state.carrito.append({
            "id": fila["ID_Producto"], "nombre": prod_sel, 
            "cantidad": int(cant), "precio": Decimal(str(fila["Precio_Venta"]))
        })
        st.rerun()

if st.session_state.carrito:
    st.markdown("### 🛒 Detalle del Pedido")
    df_c = pd.DataFrame(st.session_state.carrito)
    total_v = sum(df_c["cantidad"] * df_c["precio"])
    st.table(df_c[["nombre", "cantidad"]])
    st.metric("TOTAL", f"S/ {float(total_v):.2f}")
    
    metodo = st.radio("Pago:", ["Efectivo", "Yape", "Plin"], horizontal=True)

    col_v, col_f = st.columns(2)
    if col_v.button("🗑️ VACIAR TODO", use_container_width=True):
        st.session_state.carrito = []
        st.rerun()

    if col_f.button("🚀 FINALIZAR VENTA", type="primary", use_container_width=True):
        f, h = obtener_tiempo_peru()
        try:
            tabla_ventas.put_item(Item={
                "ID_Venta": f"V-{int(time.time())}", "Fecha": f, "Hora": h, 
                "Total": Decimal(str(total_v)), "Metodo": metodo, "Productos": st.session_state.carrito
            })
            for item in st.session_state.carrito:
                tabla_inventario.update_item(
                    Key={"ID_Producto": item["id"]},
                    UpdateExpression="SET Stock_Actual = Stock_Actual - :q",
                    ExpressionAttributeValues={":q": item["cantidad"]}
                )
            st.success("✅ Venta guardada en la nube")
            st.session_state.carrito = []
            st.session_state.df = cargar_datos()
            time.sleep(1.5)
            st.rerun()
        except: st.error("Error al conectar con AWS")

# --- 5. PANEL ADMIN Y EXCEL PROFESIONAL ---
st.divider()
with st.expander("🔐 PANEL DE ADMINISTRADOR"):
    if not st.session_state.admin_logueado:
        if st.text_input("Clave:", type="password") == "admin123":
            if st.button("Entrar"):
                st.session_state.admin_logueado = True
                st.rerun()
    else:
        if st.button("Cerrar Sesión Admin"):
            st.session_state.admin_logueado = False
            st.rerun()

        st.markdown("### 📊 Reportes Detallados")
        try:
            res = tabla_ventas.scan()
            items = res.get("Items", [])
            if items:
                # CREACIÓN DE EXCEL "BONITO" (RESTAURADO)
                filas_excel = []
                for v in items:
                    for p in v.get('Productos', []):
                        filas_excel.append({
                            "Fecha": v['Fecha'], "Hora": v['Hora'],
                            "Producto": p['nombre'], "Cantidad": int(p['cantidad']),
                            "Precio Unit": float(p['precio']), "Subtotal": int(p['cantidad']) * float(p['precio']),
                            "Total Boleta": float(v['Total']), "Método": v['Metodo']
                        })
                
                df_reporte = pd.DataFrame(filas_excel)
                buffer = io.BytesIO()
                # Usamos xlsxwriter para que el Excel sea profesional
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df_reporte.to_excel(writer, index=False, sheet_name='Ventas')
                    workbook = writer.book
                    worksheet = writer.sheets['Ventas']
                    # Formato para que no se vea "pegado"
                    header_format = workbook.add_format({'bold': True, 'bg_color': '#00acc1', 'font_color': 'white'})
                    for col_num, value in enumerate(df_reporte.columns.values):
                        worksheet.write(0, col_num, value, header_format)
                        worksheet.set_column(col_num, col_num, 15) # Ancho de columna

                st.download_button(
                    label="📥 DESCARGAR EXCEL PARA MI TÍO",
                    data=buffer.getvalue(),
                    file_name=f"Reporte_Ventas_{datetime.now().strftime('%d_%m')}.xlsx",
                    mime="application/vnd.ms-excel",
                    use_container_width=True
                )
            else: st.info("No hay datos en la nube.")
        except: st.warning("Configura xlsxwriter en requirements.txt")
