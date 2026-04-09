import streamlit as st
import pandas as pd
import boto3
import time
import io
from datetime import datetime
import pytz

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="Inventario Dental Tío", layout="wide")

def obtener_tiempo_peru():
    tz_peru = pytz.timezone('America/Lima')
    ahora = datetime.now(tz_peru)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%H:%M:%S")

# 2. CARGA DE SECRETOS Y CONEXIÓN AWS
try:
    aws_id = st.secrets["aws"]["aws_access_key_id"]
    aws_key = st.secrets["aws"]["aws_secret_access_key"]
    aws_region = st.secrets["aws"]["aws_region"]
    admin_pass = st.secrets["auth"]["admin_password"]
    
    # Conexión a DynamoDB
    dynamodb = boto3.resource('dynamodb', region_name=aws_region,
                              aws_access_key_id=aws_id,
                              aws_secret_access_key=aws_key)
    
    tabla_ventas = dynamodb.Table('VentasInventario') # Asegúrate que estos nombres sean exactos en AWS
    tabla_ingresos = dynamodb.Table('EntradasInventario')
except Exception as e:
    st.error(f"Error de configuración: {e}")
    st.stop()

# 3. CARGA DE DATOS (CSV local para el stock)
@st.cache_data
def cargar_datos():
    try:
        df = pd.read_csv("inventario.csv")
        df.columns = df.columns.str.strip()
        return df
    except:
        st.error("No se encontró inventario.csv")
        return pd.DataFrame()

df = cargar_datos()

# 4. INTERFAZ PÚBLICA
st.title("🦷 Suministros Dentales - Gestión")

# Mostrar stock siempre al inicio
st.subheader("Stock Actual")
st.dataframe(df, use_container_width=True, hide_index=True)

st.divider()

# 5. PANEL DE ADMINISTRADOR (Con tu código recuperado)
with st.expander("🔐 PANEL DE CONTROL (ADMIN)"):
    password = st.text_input("Contraseña:", type="password")
    
    if password == admin_pass:
        st.success("Acceso Administrador Activo")
        
        c_adm1, c_adm2 = st.columns(2)
        
        with c_adm1:
            st.subheader("📦 Abastecer Stock")
            col_prod = [c for c in df.columns if c.lower() == 'producto'][0]
            prod_sel = st.selectbox("Elegir producto:", df[col_prod].tolist())
            cant_add = st.number_input("Cantidad a ingresar:", min_value=1, value=1)
            
            if st.button("Actualizar Stock en AWS"):
                try:
                    fecha, hora = obtener_tiempo_peru()
                    # Aquí envías a la tabla de ingresos de AWS
                    tabla_ingresos.put_item(Item={
                        'Fecha': fecha,
                        'Hora': hora,
                        'Producto': prod_sel,
                        'Cantidad': cant_add
                    })
                    st.success("¡Stock actualizado en AWS!")
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error en AWS: {e}")

        with c_adm2:
            st.subheader("📜 Historial de Ingresos")
            if st.button("Cargar Historial"):
                try:
                    ingresos = tabla_ingresos.scan().get("Items", [])
                    if ingresos:
                        df_ingresos = pd.DataFrame(ingresos).sort_values(by=["Fecha", "Hora"], ascending=False)
                        st.dataframe(df_ingresos[["Fecha", "Hora", "Producto", "Cantidad"]], use_container_width=True, hide_index=True)
                    else:
                        st.info("Sin historial.")
                except: st.info("Error al leer historial.")

        st.divider()
        
        # CIERRE DE CAJA (Tu código del Block de notas)
        st.subheader("💰 Cierre de Caja del Día")
        fecha_hoy, _ = obtener_tiempo_peru()
        
        if st.button("🔄 ACTUALIZAR Y GENERAR REPORTE"):
            try:
                ventas_lista = tabla_ventas.scan().get("Items", [])
                ventas_hoy = [v for v in ventas_lista if v['Fecha'] == fecha_hoy]
                
                if ventas_hoy:
                    total_recaudado = sum([float(v['Total']) for v in ventas_hoy])
                    st.metric("TOTAL RECAUDADO HOY", f"S/ {total_recaudado:.2f}")
                    
                    filas_tabla = []
                    filas_excel = []
                    
                    for v in sorted(ventas_hoy, key=lambda x: x['Hora'], reverse=True):
                        primero = True
                        for p in v['Productos']:
                            filas_tabla.append({
                                "Hora": v['Hora'] if primero else "",
                                "Producto": p['nombre'], "Cant": p['cantidad'],
                                "Pago": v.get('Metodo', 'Efectivo') if primero else "",
                                "Total Cliente": f"S/ {float(v['Total']):.2f}" if primero else ""
                            })
                            filas_excel.append({
                                "Fecha": v['Fecha'], "Hora": v['Hora'], "Producto": p['nombre'],
                                "Cantidad": p['cantidad'], "Total Venta": float(v['Total']), "Metodo": v.get('Metodo', 'Efectivo')
                            })
                            primero = False
                    
                    st.table(pd.DataFrame(filas_tabla))
                    
                    # Generador de Excel
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        pd.DataFrame(filas_excel).to_excel(writer, index=False, sheet_name='Ventas')
                    
                    st.download_button(
                        label="📥 DESCARGAR EXCEL DE HOY",
                        data=output.getvalue(),
                        file_name=f"Reporte_{fecha_hoy.replace('/','_')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                else:
                    st.warning("No hay ventas hoy.")
            except Exception as e:
                st.error(f"Error al generar reporte: {e}")

        if st.button("CERRAR SESIÓN"):
            st.rerun()
            
    elif password != "":
        st.error("Contraseña incorrecta")

# 6. SECCIÓN DE VENTAS (YAPE/PLIN Y GLOBOS)
st.subheader("🛒 Registrar Venta Nueva")
col1, col2 = st.columns(2)

with col1:
    v_prod = st.selectbox("Producto a vender:", df[[c for c in df.columns if c.lower() == 'producto'][0]].tolist(), key="venta_prod")
    v_cant = st.number_input("Cantidad:", min_value=1, value=1)

with col2:
    v_metodo = st.radio("Pago:", ["Yape", "Plin", "Efectivo"], horizontal=True)

if st.button("Confirmar Venta 🚀"):
    # Aquí puedes añadir la lógica para guardar en la tabla_ventas de AWS
    st.balloons()
    st.success(f"Venta de {v_prod} registrada. ¡A cobrar!")
