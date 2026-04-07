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

# --- 2. FUNCIONES AUXILIARES ---
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

# Inicialización de estados
if "df" not in st.session_state: st.session_state.df = cargar_datos()
if "carrito" not in st.session_state: st.session_state.carrito = []

# --- 3. INTERFAZ PRINCIPAL ---
st.markdown("<h1 style='text-align: center; color: #00acc1;'>🦷 SISTEMA DENTAL PRO</h1>", unsafe_allow_html=True)

# Mostrar Inventario
df = st.session_state.df
if not df.empty:
    def color_critico(val):
        return 'color: red; font-weight: bold' if val <= 5 else 'color: white'
    
    st.subheader("📋 Stock Disponible")
    st.dataframe(df[['Producto', 'Stock_Actual', 'Precio_Venta']].style.map(color_critico, subset=['Stock_Actual']), 
                 use_container_width=True, hide_index=True)

# Sección de Venta
st.divider()
c1, c2 = st.columns([2,1])
with c1:
    p_sel = st.selectbox("Producto:", df["Producto"].tolist() if not df.empty else [])
with c2:
    fila_prod = df[df["Producto"] == p_sel].iloc[0] if not df.empty else None
    stock_max = int(fila_prod["Stock_Actual"]) if fila_prod is not None else 1
    cant = st.number_input("Cantidad:", min_value=1, max_value=stock_max, value=1)

if st.button("➕ AGREGAR AL CARRITO", use_container_width=True):
    st.session_state.carrito.append({
        "id": fila_prod["ID_Producto"], "nombre": p_sel, 
        "cantidad": int(cant), "precio": Decimal(str(fila_prod["Precio_Venta"]))
    })
    st.rerun()

# --- 4. CARRITO Y VACIAR ---
if st.session_state.carrito:
    st.markdown("### 🛒 Tu Pedido Actual")
    df_carrito = pd.DataFrame(st.session_state.carrito)
    total_venta = sum(df_carrito["cantidad"] * df_carrito["precio"])
    st.table(df_carrito[["nombre", "cantidad"]])
    st.metric("TOTAL A PAGAR", f"S/ {float(total_venta):.2f}")
    
    col_vaciar, col_finalizar = st.columns(2)
    
    # BOTÓN VACIAR (RESTAURADO)
    if col_vaciar.button("🗑️ VACIAR CARRITO", use_container_width=True):
        st.session_state.carrito = []
        st.rerun()

    if col_finalizar.button("🚀 FINALIZAR COMPRA", type="primary", use_container_width=True):
        f, h = obtener_tiempo_peru()
        id_v = f"V-{int(time.time())}"
        try:
            tabla_ventas.put_item(Item={
                "ID_Venta": id_v, "Fecha": f, "Hora": h, 
                "Total": Decimal(str(total_venta)), "Productos": st.session_state.carrito
            })
            for item in st.session_state.carrito:
                tabla_inventario.update_item(
                    Key={"ID_Producto": item["id"]},
                    UpdateExpression="SET Stock_Actual = Stock_Actual - :q",
                    ExpressionAttributeValues={":q": item["cantidad"]}
                )
            st.success("✅ Venta guardada correctamente.")
            st.session_state.carrito = []
            st.session_state.df = cargar_datos()
            time.sleep(1.5)
            st.rerun()
        except: st.error("Error al grabar en la nube.")

# --- 5. PANEL ADMIN (ABASTECER + EXCEL) ---
st.divider()
with st.expander("🔐 PANEL DE CONTROL (ADMIN)"):
    pass_admin = st.text_input("Contraseña:", type="password")
    if pass_admin == "admin123":
        
        # ABASTECER STOCK (RESTAURADO)
        st.subheader("📦 Abastecer Inventario")
        c_a1, c_a2 = st.columns(2)
        prod_a = c_a1.selectbox("Producto a recargar:", df["Producto"].tolist())
        cant_a = c_a2.number_input("Cantidad nueva:", min_value=1, value=10)
        
        if st.button("Cargar Inventario"):
            id_a = df[df["Producto"] == prod_a].iloc[0]["ID_Producto"]
            tabla_inventario.update_item(
                Key={"ID_Producto": id_a},
                UpdateExpression="SET Stock_Actual = Stock_Actual + :q",
                ExpressionAttributeValues={":q": int(cant_a)}
            )
            st.success(f"Stock de {prod_a} actualizado.")
            st.session_state.df = cargar_datos()
            time.sleep(1)
            st.rerun()

        st.divider()
        
        # EXCEL MEJORADO
        st.subheader("📊 Reporte Detallado")
        if st.button("Generar Excel para el Tío"):
            items = tabla_ventas.scan().get("Items", [])
            if items:
                filas = []
                # Ordenar por fecha y hora para que el Excel sea cronológico
                items = sorted(items, key=lambda x: (x['Fecha'], x['Hora']), reverse=True)
                
                for v in items:
                    # El total solo aparece en la primera fila de la compra del cliente
                    primer_item = True
                    for p in v.get('Productos', []):
                        filas.append({
                            "ID Venta": v['ID_Venta'],
                            "Fecha": v['Fecha'],
                            "Producto": p['nombre'],
                            "Cant": int(p['cantidad']),
                            "Precio Unit": float(p['precio']),
                            "Subtotal": int(p['cantidad']) * float(p['precio']),
                            "TOTAL CLIENTE": float(v['Total']) if primer_item else "" 
                        })
                        primer_item = False
                    # Añadir fila vacía de separación entre clientes
                    filas.append({k: "" for k in ["ID Venta", "Fecha", "Producto", "Cant", "Precio Unit", "Subtotal", "TOTAL CLIENTE"]})

                df_ex = pd.DataFrame(filas)
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_ex.to_excel(writer, index=False, sheet_name='Ventas')
                    workbook = writer.book
                    worksheet = writer.sheets['Ventas']
                    
                    # Formato: El total en negrita y azul
                    fmt_total = workbook.add_format({'bold': True, 'font_color': 'blue', 'num_format': '#,##0.00'})
                    worksheet.set_column('G:G', 15, fmt_total)
                    worksheet.set_column('A:F', 18)

                st.download_button("📥 DESCARGAR EXCEL", output.getvalue(), "Reporte_Dental_Pro.xlsx")
