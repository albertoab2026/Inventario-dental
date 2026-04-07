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

# --- 2. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="Inventario Dental Pro", layout="wide")
st.markdown("""
    <style>
    .titulo-seccion { font-size:28px !important; font-weight: bold; color: #00acc1; margin-top: 20px; }
    .stButton>button { border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center; color: #00acc1;'>🦷 SISTEMA DENTAL - ALBERTO BALLARTA</h1>", unsafe_allow_html=True)

# --- 3. FUNCIONES AUXILIARES ---
def obtener_tiempo_peru():
    ahora = datetime.utcnow() - timedelta(hours=5)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%H:%M:%S")

def cargar_datos():
    try:
        data = tabla_inventario.scan()["Items"]
        df = pd.DataFrame(data)
        if not df.empty:
            df["Stock_Actual"] = pd.to_numeric(df["Stock_Actual"], errors='coerce').fillna(0).astype(int)
            df["Precio_Venta"] = pd.to_numeric(df["Precio_Venta"], errors='coerce').fillna(0)
            return df.sort_values(by="ID_Producto").reset_index(drop=True)
        return pd.DataFrame()
    except:
        return pd.DataFrame()

# --- 4. ESTADO DE SESIÓN ---
if "df" not in st.session_state: st.session_state.df = cargar_datos()
if "carrito" not in st.session_state: st.session_state.carrito = []
if "admin_logueado" not in st.session_state: st.session_state.admin_logueado = False
if "confirmar_final" not in st.session_state: st.session_state.confirmar_final = False

# --- 5. TABLA INVENTARIO CON ALERTAS ---
st.markdown("<p class='titulo-seccion'>📋 Inventario Actual</p>", unsafe_allow_html=True)
df = st.session_state.df

if not df.empty:
    def resaltar_stock(row):
        return ['color: #ff1744; font-weight: bold' if row.Stock_Actual <= 5 else '' for _ in row]

    df_view = df.copy()
    df_view["Precio_Venta"] = df_view["Precio_Venta"].map("S/ {:.2f}".format)
    st.dataframe(df_view[['ID_Producto', 'Producto', 'Stock_Actual', 'Precio_Venta']].style.apply(resaltar_stock, axis=1), 
                 use_container_width=True, hide_index=True)
    
    if (df["Stock_Actual"] <= 5).any():
        st.warning("⚠️ ¡Atención! Reponer productos resaltados en rojo.")

# --- 6. REGISTRO DE VENTA ---
st.divider()
st.markdown("<p class='titulo-seccion'>🛒 Nueva Venta</p>", unsafe_allow_html=True)

if not df.empty:
    c_sel, c_cant = st.columns([2, 1])
    with c_sel:
        prod_sel = st.selectbox("Producto:", sorted(df["Producto"].tolist()), key="sel_prod")
    with c_cant:
        fila = df[df["Producto"] == prod_sel].iloc[0]
        stock_r = int(fila["Stock_Actual"])
        cant_carro = sum(i["cantidad"] for i in st.session_state.carrito if i["nombre"] == prod_sel)
        disp = stock_r - cant_carro
        cant = st.number_input(f"Cant. (Disp: {disp})", min_value=1, max_value=max(1, disp), value=1, key="num_cant")

    if st.button("➕ AGREGAR AL PEDIDO", use_container_width=True):
        if disp > 0:
            st.session_state.carrito.append({
                "id": fila["ID_Producto"], "nombre": prod_sel, 
                "cantidad": int(cant), "precio": Decimal(str(fila["Precio_Venta"]))
            })
            st.rerun()

# --- 7. PROCESAR COMPRA ---
if st.session_state.carrito:
    st.divider()
    df_c = pd.DataFrame(st.session_state.carrito)
    df_c["Subtotal"] = df_c["cantidad"] * df_c["precio"]
    total_venta = df_c["Subtotal"].sum()
    
    st.table(df_c[['nombre', 'cantidad', 'Subtotal']])
    st.metric("TOTAL A COBRAR", f"S/ {float(total_venta):.2f}")
    metodo_pago = st.radio("Método de Pago:", ["Efectivo", "Yape", "Plin"], horizontal=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Vaciar Carrito", use_container_width=True):
            st.session_state.carrito = []
            st.session_state.confirmar_final = False
            st.rerun()
    with col2:
        if st.button("🚀 FINALIZAR VENTA", type="primary", use_container_width=True):
            st.session_state.confirmar_final = True

    if st.session_state.confirmar_final:
        st.info("💡 Haz clic abajo para confirmar y guardar en la nube.")
        if st.button("✅ SÍ, CONFIRMAR Y GRABAR", use_container_width=True):
            fecha_v, hora_v = obtener_tiempo_peru()
            try:
                # Grabar en DynamoDB Ventas
                tabla_ventas.put_item(Item={
                    "ID_Venta": f"V-{int(time.time())}",
                    "Fecha": fecha_v, "Hora": hora_v, "Total": Decimal(str(total_venta)),
                    "Metodo": metodo_pago, "Productos": st.session_state.carrito
                })
                # Descontar de DynamoDB Inventario
                for item in st.session_state.carrito:
                    tabla_inventario.update_item(
                        Key={"ID_Producto": item["id"]},
                        UpdateExpression="SET Stock_Actual = Stock_Actual - :q",
                        ExpressionAttributeValues={":q": item["cantidad"]}
                    )
                # Limpieza y Refresco
                st.session_state.carrito = []
                st.session_state.confirmar_final = False
                st.session_state.df = cargar_datos()
                st.success("✨ Venta grabada con éxito.")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Error al grabar: {e}")

# --- 8. PANEL ADMINISTRADOR (ABASTECER + EXCEL PRO) ---
st.divider()
with st.expander("🔐 PANEL DE ADMINISTRADOR"):
    if not st.session_state.admin_logueado:
        clave_acceso = st.text_input("Ingresa la clave:", type="password")
        if st.button("Entrar"):
            if clave_acceso == "admin123":
                st.session_state.admin_logueado = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta")
    else:
        if st.button("🔒 Cerrar Sesión Admin", use_container_width=True):
            st.session_state.admin_logueado = False
            st.rerun()
            
        st.markdown("### 📦 Abastecer Inventario")
        with st.form("form_reposicion"):
            p_repo = st.selectbox("Producto que llegó:", df["Producto"].tolist())
            c_repo = st.number_input("Cantidad nueva:", min_value=1, value=10)
            if st.form_submit_button("✅ ACTUALIZAR STOCK"):
                id_p = df[df["Producto"] == p_repo].iloc[0]["ID_Producto"]
                tabla_inventario.update_item(
                    Key={"ID_Producto": id_p},
                    UpdateExpression="SET Stock_Actual = Stock_Actual + :q",
                    ExpressionAttributeValues={":q": int(c_repo)}
                )
                st.session_state.df = cargar_datos()
                st.success(f"Se agregaron {c_repo} unidades a {p_repo}")
                time.sleep(1)
                st.rerun()

        st.divider()
        st.markdown("### 📊 Historial y Reportes")
        try:
            res_v = tabla_ventas.scan()
            datos_v = res_v.get("Items", [])
            if datos_v:
                df_hist = pd.DataFrame(datos_v)
                df_hist["Total"] = pd.to_numeric(df_hist["Total"]).fillna(0)
                df_hist['Aux_Fecha'] = pd.to_datetime(df_hist['Fecha'] + ' ' + df_hist['Hora'], dayfirst=True)
                df_hist = df_hist.sort_values(by='Aux_Fecha', ascending=False)

                st.write(f"💰 **Caja Total:** S/ {df_hist['Total'].sum():,.2f}")
                
                # --- GENERACIÓN DE EXCEL PROFESIONAL ---
                try:
                    import xlsxwriter
                    filas_para_excel = []
                    for _, venta in df_hist.iterrows():
                        es_primero = True
                        for prod in venta.get('Productos', []):
                            filas_para_excel.append({
                                "ID_Venta": venta['ID_Venta'], "Fecha": venta['Fecha'], "Hora": venta['Hora'],
                                "Producto": prod['nombre'], "Cantidad": int(prod['cantidad']),
                                "Precio Unit": float(prod['precio']),
                                "Subtotal": int(prod['cantidad']) * float(prod['precio']),
                                "TOTAL VENTA": float(venta['Total']) if es_primero else "",
                                "Metodo": venta['Metodo']
                            })
                            es_primero = False
                    
                    df_final_ex = pd.DataFrame(filas_para_excel)
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                        df_final_ex.to_excel(writer, index=False, sheet_name='Reporte')
                        wb = writer.book
                        ws = writer.sheets['Reporte']
                        
                        # Estilos
                        cabecera = wb.add_format({'bold': True, 'bg_color': '#00acc1', 'font_color': 'white', 'border': 1})
                        moneda = wb.add_format({'num_format': '"S/" #,##0.00', 'border': 1})
                        total_f = wb.add_format({'bold': True, 'bg_color': '#E0F7FA', 'border': 1, 'num_format': '"S/" #,##0.00'})
                        
                        for i, col in enumerate(df_final_ex.columns):
                            ws.write(0, i, col, cabecera)
                            ws.set_column(i, i, 18)

                        pintar, id_anterior = True, ""
                        for r in range(1, len(df_final_ex) + 1):
                            id_actual = df_final_ex.iloc[r-1]['ID_Venta']
                            if id_actual != id_anterior:
                                pintar, id_anterior = not pintar, id_actual
                            
                            estilo_celda = wb.add_format({'border': 1, 'bg_color': '#F9F9F9' if pintar else '#FFFFFF'})
                            for c in range(len(df_final_ex.columns)):
                                valor = df_final_ex.iloc[r-1, c]
                                if c == 7 and valor != "": # TOTAL VENTA
                                    ws.write(r, c, valor, total_f)
                                elif c in [5, 6]: # Precios
                                    ws.write(r, c, valor, moneda)
                                else:
                                    ws.write(r, c, valor, estilo_celda)

                    st.download_button("📥 DESCARGAR EXCEL DETALLADO", buffer.getvalue(), "Ventas_Dental.xlsx", "application/vnd.ms-excel", use_container_width=True)
                
                except ImportError:
                    st.warning("⚠️ Módulo de Excel avanzado no detectado. Descargando versión simple.")
                    csv = df_hist.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 DESCARGAR REPORTE CSV", csv, "Reporte.csv", "text/csv")
            else:
                st.info("No hay ventas registradas en la base de datos.")
        except Exception as e:
            st.error(f"Error al cargar historial: {e}")
