import streamlit as st
import pandas as pd
import boto3
from datetime import datetime, timedelta

# --- 1. CONEXIÓN CON AMAZON DYNAMODB ---
# Usamos los Secrets que guardaste en Streamlit Cloud
try:
    session = boto3.Session(
        aws_access_key_id=st.secrets["aws"]["aws_access_key_id"],
        aws_secret_access_key=st.secrets["aws"]["aws_secret_access_key"],
        region_name=st.secrets["aws"]["aws_region"]
    )
    dynamodb = session.resource('dynamodb')
    # NOMBRE ACTUALIZADO SEGÚN TU CAPTURA DE PANTALLA
    tabla = dynamodb.Table('Inventariodentaltio')
except Exception as e:
    st.error(f"Error de conexión con AWS: {e}")

# --- 2. CONFIGURACIÓN VISUAL (TU DISEÑO) ---
st.set_page_config(page_title="Inventario Dental Pro", layout="wide")
st.markdown("<h1 style='text-align: center; color: #00acc1;'>🦷 SISTEMA DENTAL - ALBERTO BALLARTA</h1>", unsafe_allow_html=True)

def obtener_hora_peru():
    return (datetime.utcnow() - timedelta(hours=5)).strftime("%H:%M:%S")

# --- 3. FUNCIÓN PARA TRAER DATOS REALES ---
def cargar_datos_aws():
    try:
        respuesta = tabla.scan()
        items = respuesta.get('Items', [])
        if not items:
            # Si no hay nada en Amazon, muestra esto para que no salga error
            return pd.DataFrame({
                "Producto": ["Esperando datos de AWS..."],
                "Stock_Actual": [0],
                "Precio_Venta": [0.0]
            })
        df = pd.DataFrame(items)
        # Convertimos a números para que los cálculos funcionen
        df["Stock_Actual"] = pd.to_numeric(df["Stock_Actual"])
        df["Precio_Venta"] = pd.to_numeric(df["Precio_Venta"])
        return df
    except Exception as e:
        st.error(f"Error al leer la tabla: {e}")
        return pd.DataFrame()

# Guardar en la memoria de la página
if 'df_memoria' not in st.session_state:
    st.session_state.df_memoria = cargar_datos_aws()
if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'ventas_dia' not in st.session_state: st.session_state.ventas_dia = []

# --- 4. MOSTRAR TABLA DE STOCK ---
st.subheader("📋 Control de Stock Actual (Desde Amazon AWS)")
df_vis = st.session_state.df_memoria.copy()
# Formato de moneda para la vista
df_vis_copy = df_vis.copy()
if 'Precio_Venta' in df_vis_copy.columns:
    df_vis_copy['Precio_Venta'] = df_vis_copy['Precio_Venta'].map('S/ {:,.2f}'.format)
st.table(df_vis_copy)

st.divider()

# --- 5. ARMAR PEDIDO ---
st.subheader("🛒 Armar Pedido del Cliente")
if not st.session_state.df_memoria.empty and "Producto" in st.session_state.df_memoria.columns:
    c1, c2 = st.columns(2)
    with c1:
        lista_productos = st.session_state.df_memoria["Producto"].tolist()
        prod_sel = st.selectbox("Selecciona Producto:", lista_productos)
    with c2:
        if "contador_reset" not in st.session_state: st.session_state.contador_reset = 0
        cant_sel = st.number_input("Cantidad:", min_value=1, value=1, key=f"input_cant_{st.session_state.contador_reset}")

    if st.button("➕ Agregar al Carrito", type="primary"):
        idx = st.session_state.df_memoria[st.session_state.df_memoria['Producto'] == prod_sel].index[0]
        ya_en_carrito = sum(item['Cant'] for item in st.session_state.carrito if item['Producto'] == prod_sel)
        stock_disponible = st.session_state.df_memoria.at[idx, 'Stock_Actual'] - ya_en_carrito
        
        if cant_sel > stock_disponible:
            st.error(f"❌ Stock insuficiente en AWS. Quedan {stock_disponible}.")
        else:
            precio = st.session_state.df_memoria.at[idx, 'Precio_Venta']
            st.session_state.carrito.append({"Producto": prod_sel, "Cant": cant_sel, "Subtotal": float(cant_sel * precio)})
            st.success(f"✅ {prod_sel} añadido.")
            st.session_state.contador_reset += 1
            st.rerun()

# --- 6. FINALIZAR VENTA ---
if st.session_state.carrito:
    st.divider()
    st.subheader("📝 VENTA ACTUAL")
    df_car = pd.DataFrame(st.session_state.carrito)
    df_car_v = df_car.copy()
    df_car_v['Subtotal'] = df_car_v['Subtotal'].map('S/ {:,.2f}'.format)
    st.dataframe(df_car_v, use_container_width=True, hide_index=True)
    
    total_ped = df_car['Subtotal'].sum()
    st.info(f"### TOTAL A COBRAR: S/ {total_ped:,.2f}")
    metodo = st.selectbox("Pago:", ["Efectivo", "Yape", "Plin"])

    if st.button("🚀 FINALIZAR VENTA", type="primary", use_container_width=True):
        # Actualizamos stock localmente
        for item in st.session_state.carrito:
            idx = st.session_state.df_
