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

# --- 2. CONFIGURACIÓN ---
st.set_page_config(page_title="Inventario Dental Pro", layout="wide")
st.markdown("<h1 style='text-align: center; color: #00acc1;'>🦷 CONTROL DE VENTAS - DYNAMODB</h1>", unsafe_allow_html=True)

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

if "df" not in st.session_state: st.session_state.df = cargar_datos()
if "carrito" not in st.session_state: st.session_state.carrito = []
if "admin_logueado" not in st.session_state: st.session_state.admin_logueado = False

# --- 3. INVENTARIO ---
df = st.session_state.df
if not df.empty:
    st.markdown("### 📋 Stock Actual")
    st.dataframe(df[['ID_Producto', 'Producto', 'Stock_Actual', 'Precio_Venta']], use_container_width=True, hide_index=True)

# --- 4. SELECCIÓN ---
st.divider()
if not df.empty:
    c1, c2 = st.columns([2,1])
    prod_sel = c1.selectbox("Elegir Producto:", df["Producto"].tolist())
    fila = df[df["Producto"] == prod_sel].iloc[0]
    cant = c2.number_input("Cantidad:", min_value=1, max_value=int(fila["Stock_Actual"]), value=1)
    
    if st.button("➕ AGREGAR AL CARRITO", use_container_width=True):
        st.session_state.carrito.append({
            "id": fila["ID_Producto"], "nombre": prod_sel, 
            "cantidad": int(cant), "precio": Decimal(str(fila["Precio_Venta"]))
        })
        st.rerun()

# --- 5. CARRITO Y VACIAR (RESTAURADO) ---
if st.session_state.carrito:
    st.divider()
    st.markdown("### 🛒 Tu Pedido")
    df_c = pd.DataFrame(st.session_state.carrito)
    total_v = sum(df_c["cantidad"] * df_c["precio"])
    st.table(df_c[["nombre", "cantidad"]])
    st.metric("TOTAL", f"S/ {float(total_v):.2f}")
    
    metodo = st.radio("Pago:", ["Efectivo", "Yape", "Plin"], horizontal=True)

    col_vaciar, col_pagar = st.columns(2)
    
    # Botón para limpiar si hubo error de selección
    if col_vaciar.button("🗑️ VACIAR CARRITO", use_container_width=True):
        st.session_state.carrito = []
        st.rerun()

    if col_pagar.button("✅ FINALIZAR Y GUARDAR", type="primary", use_container_width=True):
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
            st.success("✨ ¡VENTA REGISTRADA!")
            st.session_state.carrito = []
            st.session_state.df = cargar_datos()
            time.sleep(1.5)
            st.rerun()
        except Exception as e:
            st.error(f"Error de red: {e}")

# --- 6. PANEL ADMIN Y EXCEL (RESTAURADO) ---
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
            
        st.markdown("### 📦 Abastecer Stock")
        p_repo = st.selectbox("Producto:", df["Producto"].tolist(), key="repo")
        c_repo = st.number_input("Cantidad nueva:", min_value=1, value=10)
        if st.button("Actualizar Inventario"):
            id_p = df[df["Producto"] == p_repo].iloc[0]["ID_Producto"]
            tabla_inventario.update_item(Key={"ID_Producto": id_p}, UpdateExpression="SET Stock_Actual = Stock_Actual + :q", ExpressionAttributeValues={":q": int(c_repo)})
            st.session_state.df = cargar_datos()
            st.success("Stock actualizado.")
            st.rerun()

        st.divider()
        st.markdown("### 📊 Reportes Excel")
        try:
            # Traemos las ventas de la nube para el reporte
            ventas_nube = tabla_ventas.scan().get("Items", [])
            if ventas_nube:
                df_excel = pd.DataFrame(ventas_nube)
                # Formatear el Excel en memoria
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df_excel.to_excel(writer, index=False, sheet_name='Ventas')
                
                st.download_button(
                    label="📥 DESCARGAR REPORTE EXCEL",
                    data=buffer.getvalue(),
                    file_name=f"Reporte_Ventas_{datetime.now().strftime('%d_%m')}.xlsx",
                    mime="application/vnd.ms-excel",
                    use_container_width=True
                )
            else:
                st.info("Aún no hay ventas en la nube para descargar.")
        except Exception as e:
            st.error("Instala 'xlsxwriter' en requirements.txt para descargar el reporte.")
