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
    st.error(f"Error Crítico de Conexión AWS: {e}")

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

# Estados de sesión
if "df" not in st.session_state: st.session_state.df = cargar_datos()
if "carrito" not in st.session_state: st.session_state.carrito = []

# --- 3. INTERFAZ DE VENTA ---
df = st.session_state.df
if not df.empty:
    with st.container():
        c1, c2 = st.columns([2,1])
        prod_sel = c1.selectbox("Producto:", df["Producto"].tolist())
        fila = df[df["Producto"] == prod_sel].iloc[0]
        cant = c2.number_input("Cantidad:", min_value=1, max_value=int(fila["Stock_Actual"]), value=1)
        
        if st.button("➕ AGREGAR AL CARRITO", use_container_width=True):
            st.session_state.carrito.append({
                "id": fila["ID_Producto"], "nombre": prod_sel, 
                "cantidad": int(cant), "precio": Decimal(str(fila["Precio_Venta"]))
            })
            st.rerun()

# --- 4. PROCESAR VENTA (EL ARREGLO ESTÁ AQUÍ) ---
if st.session_state.carrito:
    st.divider()
    df_c = pd.DataFrame(st.session_state.carrito)
    total_v = sum(df_c["cantidad"] * df_c["precio"])
    st.table(df_c[["nombre", "cantidad"]])
    st.metric("TOTAL", f"S/ {float(total_v):.2f}")
    
    metodo = st.radio("Pago:", ["Efectivo", "Yape", "Plin"], horizontal=True)

    # Solo un botón para evitar el doble mensaje
    if st.button("✅ CONFIRMAR Y GUARDAR EN NUBE", type="primary", use_container_width=True):
        f, h = obtener_tiempo_peru()
        exito_nube = False
        
        with st.spinner("Subiendo a AWS DynamoDB..."):
            try:
                # 1. Intentar grabar la venta
                tabla_ventas.put_item(Item={
                    "ID_Venta": f"V-{int(time.time())}",
                    "Fecha": f, "Hora": h, "Total": Decimal(str(total_v)),
                    "Metodo": metodo, "Productos": st.session_state.carrito
                })
                
                # 2. Intentar descontar stock
                for item in st.session_state.carrito:
                    tabla_inventario.update_item(
                        Key={"ID_Producto": item["id"]},
                        UpdateExpression="SET Stock_Actual = Stock_Actual - :q",
                        ExpressionAttributeValues={":q": item["cantidad"]}
                    )
                exito_nube = True
            except Exception as e:
                st.error(f"❌ ERROR REAL DE AWS: {e}")

        if exito_nube:
            st.success("✨ VENTA GUARDADA EN DYNAMODB CORRECTAMENTE")
            st.session_state.carrito = []
            st.session_state.df = cargar_datos()
            time.sleep(2)
            st.rerun()

# --- 5. PANEL ADMIN ---
with st.expander("📊 Ver Historial de la Nube"):
    if st.button("Actualizar Historial"):
        res = tabla_ventas.scan()
        st.write(f"Ventas totales registradas: {len(res.get('Items', []))}")
        st.dataframe(res.get("Items", []))
