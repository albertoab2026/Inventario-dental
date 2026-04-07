import streamlit as st
import pandas as pd
import boto3
import time
from datetime import datetime, timedelta
from decimal import Decimal

# --- CONEXIÓN AWS ---
try:
    session = boto3.Session(
        aws_access_key_id=st.secrets["aws"]["aws_access_key_id"],
        aws_secret_access_key=st.secrets["aws"]["aws_secret_access_key"],
        region_name=st.secrets["aws"]["aws_region"]
    )
    dynamodb = session.resource('dynamodb')
    tabla = dynamodb.Table('Inventariodentaltio')
    tabla_ventas = dynamodb.Table('VentasDentaltio')
except Exception as e:
    st.error(f"Error AWS: {e}")

# --- UI ---
st.set_page_config(page_title="Inventario Dental Pro", layout="wide")

st.markdown("<h1 style='text-align:center;color:#00acc1;'>🦷 SISTEMA DENTAL</h1>", unsafe_allow_html=True)

# --- FUNCIONES ---
def obtener_tiempo_peru():
    ahora = datetime.utcnow() - timedelta(hours=5)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%H:%M:%S")

def cargar_datos():
    try:
        data = tabla.scan()["Items"]
        df = pd.DataFrame(data)
        df["Stock_Actual"] = pd.to_numeric(df["Stock_Actual"])
        df["Precio_Venta"] = pd.to_numeric(df["Precio_Venta"])
        return df
    except:
        return pd.DataFrame()

# --- ESTADO ---
if "df" not in st.session_state:
    st.session_state.df = cargar_datos()

if "carrito" not in st.session_state:
    st.session_state.carrito = []

# --- INVENTARIO ---
st.write("## 📦 Inventario")

df = st.session_state.df
if not df.empty:
    df_view = df.copy()
    df_view["Precio_Venta"] = df_view["Precio_Venta"].map("S/ {:.2f}".format)
    st.dataframe(df_view)

# --- SELECCIÓN PRODUCTO ---
st.write("## 🛒 Venta")

producto = st.selectbox("Producto", df["Producto"])

fila = df[df["Producto"] == producto].iloc[0]

stock = int(fila["Stock_Actual"])
en_carrito = sum(i["cantidad"] for i in st.session_state.carrito if i["nombre"] == producto)

cantidad = st.number_input(f"Cantidad (Disponible: {stock - en_carrito})", 1)

if st.button("➕ Agregar"):
    if cantidad > (stock - en_carrito):
        st.warning("Sin stock")
    else:
        st.session_state.carrito.append({
            "id": fila["ID_Producto"],
            "nombre": producto,
            "cantidad": int(cantidad),
            "precio": Decimal(str(fila["Precio_Venta"]))
        })
        st.rerun()

# --- CARRITO ---
if st.session_state.carrito:

    st.write("## 🛒 Carrito de Compras")

    dfc = pd.DataFrame(st.session_state.carrito)
    dfc["Subtotal"] = dfc["cantidad"] * dfc["precio"]

    total = dfc["Subtotal"].sum()

    st.dataframe(dfc)
    st.metric("Total", f"S/ {float(total):.2f}")

    metodo = st.radio("Pago", ["Efectivo", "Yape", "Plin"])

    if st.button("🚀 FINALIZAR VENTA"):

        fecha, hora = obtener_tiempo_peru()

        try:
            # Guardar venta
            tabla_ventas.put_item(Item={
                "ID_Venta": str(time.time()),
                "Fecha": fecha,
                "Hora": hora,
                "Total": Decimal(str(total)),
                "Metodo": metodo,
                "Productos": st.session_state.carrito
            })

            # Descontar stock
            for item in st.session_state.carrito:
                tabla.update_item(
                    Key={"ID_Producto": item["id"]},
                    UpdateExpression="SET Stock_Actual = Stock_Actual - :c",
                    ExpressionAttributeValues={":c": item["cantidad"]}
                )

            st.success("✅ Venta guardada correctamente")

            st.session_state.carrito = []
            st.session_state.df = cargar_datos()

            st.balloons()
            st.rerun()

        except Exception as e:
            st.error(f"Error: {e}")
