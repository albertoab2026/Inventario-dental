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
st.set_page_config(page_title="Sistema Dental Alberto", layout="wide")

def obtener_tiempo_peru():
    ahora = datetime.utcnow() - timedelta(hours=5)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%H:%M:%S")

def cargar_datos():
    try:
        data = tabla_inventario.scan()["Items"]
        df = pd.DataFrame(data)
        if not df.empty:
            df["Stock_Actual"] = pd.to_numeric(df["Stock_Actual"]).astype(int)
            df["Precio_Venta"] = pd.to_numeric(df["Precio_Venta"]).astype(float).round(2)
            return df.sort_values(by="ID_Producto").reset_index(drop=True)
        return pd.DataFrame()
    except: return pd.DataFrame()

if "df" not in st.session_state: st.session_state.df = cargar_datos()
if "carrito" not in st.session_state: st.session_state.carrito = []
if "admin_auth" not in st.session_state: st.session_state.admin_auth = False

# --- 3. INTERFAZ ---
st.markdown("<h1 style='text-align: center; color: #00acc1;'>🦷 CONTROL DENTAL - ALBERTO</h1>", unsafe_allow_html=True)

df = st.session_state.df
if not df.empty:
    st.subheader("📋 Inventario")
    st.dataframe(df[['Producto', 'Stock_Actual', 'Precio_Venta']].style.format({"Precio_Venta": "{:.2f}"}), 
                 use_container_width=True, hide_index=True)

# Sección Venta
st.divider()
if not df.empty:
    c1, c2 = st.columns([2,1])
    p_sel = c1.selectbox("Producto:", df["Producto"].tolist(), key="sel_venta")
    fila_p = df[df["Producto"] == p_sel].iloc[0]
    cant = c2.number_input("Cantidad:", min_value=1, max_value=int(fila_p["Stock_Actual"]), value=1, key="cant_venta")
    
    if st.button("➕ AGREGAR AL CARRITO", use_container_width=True):
        st.session_state.carrito.append({
            "id": fila_p["ID_Producto"], "nombre": p_sel, 
            "cantidad": int(cant), "precio": Decimal(str(fila_p["Precio_Venta"]))
        })
        st.rerun()

# --- 4. CARRITO ---
if st.session_state.carrito:
    st.markdown("### 🛒 Detalle del Pedido")
    df_c = pd.DataFrame(st.session_state.carrito)
    total_v = sum(df_c["cantidad"] * df_c["precio"])
    st.table(df_c[["nombre", "cantidad"]])
    
    metodo_pago = st.radio("Pago:", ["Efectivo", "Yape", "Plin"], horizontal=True)
    st.metric("TOTAL", f"S/ {float(total_v):.2f}")
    
    if st.button("🚀 FINALIZAR VENTA", type="primary", use_container_width=True):
        f, h = obtener_tiempo_peru()
        tabla_ventas.put_item(Item={
            "ID_Venta": f"V-{int(time.time())}", "Fecha": f, "Hora": h, 
            "Total": Decimal(str(total_v)), "Metodo": metodo_pago, "Productos": st.session_state.carrito
        })
        for i in st.session_state.carrito:
            tabla_inventario.update_item(Key={"ID_Producto": i["id"]}, UpdateExpression="SET Stock_Actual = Stock_Actual - :q", ExpressionAttributeValues={":q": int(i["cantidad"])})
        
        st.balloons()
        st.success("✅ Venta Guardada")
        st.session_state.carrito = []
        st.session_state.df = cargar_datos()
        time.sleep(1)
        st.rerun()

# --- 5. PANEL ADMIN Y CIERRE ---
st.divider()
with st.expander("🔐 PANEL DE ADMINISTRADOR"):
    if not st.session_state.admin_auth:
        with st.form("login"):
            clave = st.text_input("Clave:", type="password")
            if st.form_submit_button("Entrar"):
                if clave == "admin123": st.session_state.admin_auth = True; st.rerun()
    else:
        if st.button("🔒 CERRAR SESIÓN"): st.session_state.admin_auth = False; st.rerun()

        # CIERRE DE CAJA
        st.subheader("💰 Resumen del Día")
        fecha_hoy, _ = obtener_tiempo_peru()
        ventas_hoy = [v for v in tabla_ventas.scan().get("Items", []) if v['Fecha'] == fecha_hoy]
        # ORDENAR POR HORA (Más reciente primero)
        ventas_hoy = sorted(ventas_hoy, key=lambda x: x['Hora'], reverse=True)

        if ventas_hoy:
            total_dia = sum([float(v['Total']) for v in ventas_hoy])
            st.metric("TOTAL RECAUDADO HOY", f"S/ {total_dia:.2f}")

            filas_reporte = []
            for v in ventas_hoy:
                first = True
                for p in v['Productos']:
                    filas_reporte.append({
                        "Hora": v['Hora'],
                        "Producto": p['nombre'],
                        "Cant": int(p['cantidad']),
                        "Pago": v.get('Metodo', 'Efectivo'),
                        "Total Cliente": f"S/ {float(v['Total']):.2f}" if first else ""
                    })
                    first = False
                # FILA VACÍA PARA SEPARAR CLIENTES
                filas_reporte.append({"Hora": "---", "Producto": "---", "Cant": "", "Pago": "", "Total Cliente": ""})
            
            st.table(pd.DataFrame(filas_reporte))

            # EXCEL PARA EL TÍO
            if st.button("📊 GENERAR EXCEL DE HOY"):
                out = io.BytesIO()
                with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                    df_ex = pd.DataFrame(filas_reporte)
                    df_ex.to_excel(writer, index=False, sheet_name='Ventas')
                st.download_button("📥 DESCARGAR EXCEL", out.getvalue(), f"Cierre_{fecha_hoy.replace('/','-')}.xlsx")
        else:
            st.info("Sin ventas hoy.")
