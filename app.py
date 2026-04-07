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

# --- 3. INTERFAZ DE VENTAS ---
st.markdown("<h1 style='text-align: center; color: #00acc1;'>🦷 SISTEMA DENTAL - ALBERTO</h1>", unsafe_allow_html=True)

df = st.session_state.df
if not df.empty:
    # Alerta de Stock sutil
    def resaltar_stock(val):
        color = 'red' if val <= 5 else 'white'
        return f'color: {color}; font-weight: bold' if val <= 5 else ''

    st.dataframe(df[['Producto', 'Stock_Actual', 'Precio_Venta']].style.applymap(resaltar_stock, subset=['Stock_Actual']), use_container_width=True, hide_index=True)

# Lógica del Carrito (Selección)
st.divider()
if not df.empty:
    c1, c2 = st.columns([2,1])
    prod_sel = c1.selectbox("Elegir Producto:", df["Producto"].tolist())
    fila = df[df["Producto"] == prod_sel].iloc[0]
    cant = c2.number_input("Cantidad:", min_value=1, max_value=int(fila["Stock_Actual"]), value=1)
    
    if st.button("➕ AGREGAR AL PEDIDO", use_container_width=True):
        st.session_state.carrito.append({
            "id": fila["ID_Producto"], "nombre": prod_sel, 
            "cantidad": int(cant), "precio": Decimal(str(fila["Precio_Venta"]))
        })
        st.rerun()

# Procesar Venta
if st.session_state.carrito:
    st.markdown("### 🛒 Detalle de Venta")
    df_c = pd.DataFrame(st.session_state.carrito)
    total_v = sum(df_c["cantidad"] * df_c["precio"])
    st.table(df_c[["nombre", "cantidad"]])
    st.metric("TOTAL A COBRAR", f"S/ {float(total_v):.2f}")
    
    col_v, col_f = st.columns(2)
    if col_v.button("🗑️ VACIAR", use_container_width=True):
        st.session_state.carrito = []
        st.rerun()

    if col_f.button("🚀 FINALIZAR VENTA", type="primary", use_container_width=True):
        f, h = obtener_tiempo_peru()
        try:
            # GUARDAR EN NUBE
            tabla_ventas.put_item(Item={
                "ID_Venta": f"V-{int(time.time())}", "Fecha": f, "Hora": h, 
                "Total": Decimal(str(total_v)), "Productos": st.session_state.carrito
            })
            # DESCONTAR STOCK
            for item in st.session_state.carrito:
                tabla_inventario.update_item(
                    Key={"ID_Producto": item["id"]},
                    UpdateExpression="SET Stock_Actual = Stock_Actual - :q",
                    ExpressionAttributeValues={":q": item["cantidad"]}
                )
            st.success("✅ ¡VENTA GUARDADA EN DYNAMODB!")
            st.session_state.carrito = []
            st.session_state.df = cargar_datos()
            time.sleep(2)
            st.rerun() # Esto limpia los mensajes viejos automáticamente
        except Exception as e:
            st.error(f"❌ Error de conexión: {e}")

# --- 4. EXCEL DETALLADO (PARA EL TÍO) ---
st.divider()
with st.expander("🔐 PANEL DE ADMINISTRADOR"):
    clave = st.text_input("Clave:", type="password")
    if clave == "admin123":
        st.markdown("### 📊 Descargar Reporte")
        if st.button("GENERAR EXCEL DE VENTAS"):
            res = tabla_ventas.scan()
            items = res.get("Items", [])
            if items:
                # AQUÍ ESTÁ EL TRUCO: Separamos cada producto en una fila nueva
                datos_para_excel = []
                for v in items:
                    for p in v.get('Productos', []):
                        datos_para_excel.append({
                            "Fecha": v['Fecha'],
                            "Hora": v['Hora'],
                            "Producto": p['nombre'],
                            "Cantidad": int(p['cantidad']),
                            "Precio Unit": float(p['precio']),
                            "Subtotal": int(p['cantidad']) * float(p['precio']),
                            "TOTAL BOLETA": float(v['Total'])
                        })
                
                df_excel = pd.DataFrame(datos_para_excel)
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_excel.to_excel(writer, index=False, sheet_name='Ventas')
                    # Auto-ajuste de columnas
                    worksheet = writer.sheets['Ventas']
                    for i, col in enumerate(df_excel.columns):
                        worksheet.set_column(i, i, 15)
                
                st.download_button(
                    label="📥 DESCARGAR EXCEL DETALLADO",
                    data=output.getvalue(),
                    file_name=f"Reporte_Ventas_{datetime.now().strftime('%d_%m')}.xlsx",
                    mime="application/vnd.ms-excel"
                )
            else:
                st.info("No hay ventas registradas aún.")
