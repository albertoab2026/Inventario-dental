import streamlit as st
import pandas as pd
import time

# 1. CONFIGURACIÓN Y ESTILOS
st.set_page_config(page_title="Inventario Dental Tío", layout="wide")

# Estilo para que se vea más profesional
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 20px; height: 3em; background-color: #007bff; color: white; }
    .main { background-color: #f5f7f9; }
    </style>
    """, unsafe_allow_html=True)

# 2. CARGA DE DATOS Y SECRETOS
@st.cache_data
def cargar_datos():
    df = pd.read_csv("inventario.csv")
    df.columns = df.columns.str.strip() # Limpia espacios
    return df

try:
    admin_pass = st.secrets["auth"]["admin_password"]
except:
    st.error("Configura la clave en Settings > Secrets")
    st.stop()

df = cargar_datos()

# 3. INTERFAZ PÚBLICA (LO QUE VE EL CLIENTE)
st.title("🦷 Suministros Dentales")
st.subheader("Stock Disponible para Venta")

# Filtramos la columna producto sin importar mayúsculas
col_prod = [c for c in df.columns if c.lower() == 'producto'][0]
col_precio = [c for c in df.columns if c.lower() == 'precio'][0]

# MOSTRAR STOCK AL INICIO (Como lo tenías antes)
st.dataframe(df, use_container_width=True)

st.divider()

# 4. PROCESO DE VENTA (Yape, Plin, Globos)
st.subheader("🛒 Realizar Pedido")
c1, c2 = st.columns(2)

with c1:
    prod_vender = st.selectbox("Selecciona producto:", df[col_prod].tolist())
    cant_vender = st.number_input("Cantidad:", min_value=1, value=1)

with c2:
    metodo_pago = st.radio("Método de pago:", ["Yape", "Plin", "Efectivo", "Transferencia"])

if st.button("Confirmar Compra 🚀"):
    with st.spinner("Procesando pago..."):
        time.sleep(2) # Simulación de espera
        st.balloons() # ¡Tus globos de vuelta!
        st.success(f"¡Compra confirmada! Producto: {prod_vender} x{cant_vender}")
        st.info(f"Por favor, realiza el pago por **{metodo_pago}** al número de tu tío.")

st.divider()

# 5. PANEL DE ADMIN (Oculto con asteriscos)
with st.expander("🔐 ACCESO ADMINISTRADOR (Solo para el Tío)"):
    # El 'type="password"' es lo que pone los asteriscos por seguridad
    password = st.text_input("Contraseña de gestión:", type="password")
    
    if password == admin_pass:
        st.write("### Bienvenido al Panel de Control")
        # Aquí puedes poner más cosas de gestión luego
        st.write(f"Has accedido como Administrador. Puedes ver reportes aquí.")
        
        if st.button("Cerrar Sesión"):
            st.rerun()
    elif password != "":
        st.error("Clave incorrecta")
