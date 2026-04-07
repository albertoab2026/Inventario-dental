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

# --- 2. FUNCIONES ---
def obtener_tiempo_peru():
    ahora = datetime.utcnow() - timedelta(hours=5)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%H:%M:%S")

def cargar_datos():
    try:
        data = tabla_inventario.scan()["Items"]
        df = pd.DataFrame(data)
        if not df.empty:
            df["Stock_Actual"] = pd.to_numeric(df["Stock_Actual"]).astype(int)
            df["Precio_Venta"] = pd.to_numeric(df["Precio_Venta"])
            return df.sort_values(by="ID_Producto").reset_index(drop=True)
        return pd.DataFrame()
    except: return pd.DataFrame()

# Inicialización
if "df" not in st.session_state: st.session_state.df = cargar_datos()
if "carrito" not in st.session_state: st.session_state.carrito = []
if "admin_auth" not in st.session_state: st.session_state.admin_auth = False

# --- 3. INTERFAZ ---
st.markdown("<h1 style='text-align: center; color: #00acc1;'>🦷 SISTEMA DENTAL PRO</h1>", unsafe_allow_html=True)

df = st.session_state.df
if not df.empty:
    def color_critico(val):
        return 'color: red; font-weight: bold' if val <= 5 else ''
    st.subheader("📋 Stock Disponible")
    st.dataframe(df[['Producto', 'Stock_Actual', 'Precio_Venta']].style.map(color_critico, subset=['Stock_Actual']), 
                 use_container_width=True, hide_index=True)

# Sección Venta
st.divider()
if not df.empty:
    c1, c2 = st.columns([2,1])
    # LLAVE ÚNICA: key="sel_venta"
    p_sel = c1.selectbox("Producto:", df["Producto"].tolist(), key="sel_venta")
    fila_p = df[df["Producto"] == p_sel].iloc[0]
    cant = c2.number_input("Cantidad:", min_value=1, max_value=int(fila_p["Stock_Actual"]), value=1, key="cant_venta")
    
    if st.button("➕ AGREGAR AL CARRITO", use_container_width=True):
        st.session_state.carrito.append({
            "id": fila_p["ID_Producto"], "nombre": p_sel, 
            "cantidad": int(cant), "precio": Decimal(str(fila_p["Precio_Venta"]))
        })
        st.rerun()

# --- 4. CARRITO Y PAGOS ---
if st.session_state.carrito:
    st.markdown("### 🛒 Detalle del Pedido")
    df_c = pd.DataFrame(st.session_state.carrito)
    total_v = sum(df_c["cantidad"] * df_c["precio"])
    st.table(df_c[["nombre", "cantidad"]])
    
    metodo_pago = st.radio("Forma de Pago:", ["Efectivo", "Yape", "Plin"], horizontal=True)
    st.metric("TOTAL", f"S/ {float(total_v):.2f}")
    
    cv, cf = st.columns(2)
    if cv.button("🗑️ VACIAR CARRITO", use_container_width=True):
        st.session_state.carrito = []
        st.rerun()

    if cf.button("🚀 FINALIZAR VENTA", type="primary", use_container_width=True):
        f, h = obtener_tiempo_peru()
        try:
            tabla_ventas.put_item(Item={
                "ID_Venta": f"V-{int(time.time())}", "Fecha": f, "Hora": h, 
                "Total": Decimal(str(total_v)), "Metodo": metodo_pago, "Productos": st.session_state.carrito
            })
            for i in st.session_state.carrito:
                tabla_inventario.update_item(
                    Key={"ID_Producto": i["id"]},
                    UpdateExpression="SET Stock_Actual = Stock_Actual - :q",
                    ExpressionAttributeValues={":q": i["cantidad"]}
                )
            st.success(f"✅ Venta en {metodo_pago} guardada.")
            st.session_state.carrito = []
            st.session_state.df = cargar_datos()
            time.sleep(1.2)
            st.rerun()
        except: st.error("Error AWS")

# --- 5. PANEL ADMIN ---
st.divider()
with st.expander("🔐 PANEL DE ADMINISTRADOR"):
    if not st.session_state.admin_auth:
        with st.form("login_admin"):
            input_clave = st.text_input("Contraseña Maestra:", type="password")
            if st.form_submit_button("Entrar"):
                if input_clave == "admin123":
                    st.session_state.admin_auth = True
                    st.rerun()
                else:
                    st.error("Clave Incorrecta")
    else:
        if st.button("🔒 CERRAR SESIÓN ADMIN", use_container_width=True):
            st.session_state.admin_auth = False
            st.rerun()

        st.subheader("📦 Abastecer Stock")
        # LLAVE ÚNICA: key="sel_admin" (ESTO EVITA EL ERROR DE LA IMAGEN)
        p_abast = st.selectbox("Producto a recargar:", df["Producto"].tolist(), key="sel_admin")
        c_abast = st.number_input("Añadir cantidad:", min_value=1, value=5, key="cant_admin")
        
        if st.button("Actualizar Stock"):
            id_a = df[df["Producto"] == p_abast].iloc[0]["ID_Producto"]
            tabla_inventario.update_item(
                Key={"ID_Producto": id_a}, 
                UpdateExpression="SET Stock_Actual = Stock_Actual + :q", 
                ExpressionAttributeValues={":q": int(c_abast)}
            )
            st.success("Stock actualizado.")
            st.session_state.df = cargar_datos()
            time.sleep(1)
            st.rerun()

        st.divider()
        st.subheader("📊 Reporte Detallado")
        if st.button("Generar Excel para el Tío"):
            ventas = tabla_ventas.scan().get("Items", [])
            if ventas:
                ventas = sorted(ventas, key=lambda x: (x['Fecha'], x['Hora']), reverse=True)
                filas = []
                for v in ventas:
                    primera = True
                    for p in v.get('Productos', []):
                        filas.append({
                            "Fecha": v['Fecha'], "Hora": v['Hora'], "Producto": p['nombre'],
                            "Cant": int(p['cantidad']), "P. Unit": float(p['precio']),
                            "Pago": v.get('Metodo', 'N/A'),
                            "TOTAL CLIENTE": float(v['Total']) if primera else ""
                        })
                        primera = False
                    filas.append({k: "" for k in ["Fecha", "Hora", "Producto", "Cant", "P. Unit", "Pago", "TOTAL CLIENTE"]})
                
                df_ex = pd.DataFrame(filas)
                out = io.BytesIO()
                with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                    df_ex.to_excel(writer, index=False, sheet_name='Ventas')
                    ws = writer.sheets['Ventas']
                    ws.set_column('A:G', 16)
                st.download_button("📥 DESCARGAR EXCEL", out.getvalue(), "Ventas_Dental.xlsx")
