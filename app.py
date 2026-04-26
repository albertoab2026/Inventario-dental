# === SIDEBAR ===
with st.sidebar:
    st.title(f"🏢 {st.session_state.tenant}")
    st.write(f"Usuario: **{st.session_state.usuario}**")
    st.caption(f"{'🔵' if PLAN_ACTUAL=='BASICO' else '🟣' if PLAN_ACTUAL=='PRO' else '🟡'} **Plan {PLAN_ACTUAL}** | S/ {float(PRECIO_ACTUAL):.0f}/mes")

    st.markdown("---")
    if st.button("🔒 CERRAR CAJA", use_container_width=True, type="primary"):
        f_hoy, _, _ = obtener_tiempo_peru()
        res_c = tabla_cierres.query(KeyConditionExpression=Key('TenantID').eq(st.session_state.tenant), FilterExpression=Attr('Fecha').eq(f_hoy) & Attr('UsuarioTurno').eq(st.session_state.usuario))
        cierres = res_c.get('Items', [])
        hora_ult = max([c['Hora'] for c in cierres]) if cierres else "00:00:00"
        res_v = tabla_ventas.query(KeyConditionExpression=Key('TenantID').eq(st.session_state.tenant), FilterExpression=Attr('Fecha').eq(f_hoy) & Attr('Usuario').eq(st.session_state.usuario) & Attr('Hora').gt(hora_ult))
        total = sum([Decimal(str(v['Total'])) for v in res_v.get('Items', [])])
        if total > 0: registrar_cierre(total, st.session_state.usuario, f"CIERRE {st.session_state.rol}", st.session_state.usuario); st.success(f"✅ S/ {float(total):.2f}"); st.balloons(); time.sleep(1); st.rerun()
        else: st.warning("No hay ventas nuevas")

    if st.session_state.rol == "DUEÑO":
        st.markdown("---"); st.subheader("🚨 CIERRE TARDÍO")
        if 0 <= datetime.now(tz_peru).hour <= 6:
            ayer = (datetime.now(tz_peru) - timedelta(days=1)).strftime("%d/%m/%Y")
            res_v = tabla_ventas.query(KeyConditionExpression=Key('TenantID').eq(st.session_state.tenant), FilterExpression=Attr('Fecha').eq(ayer))
            res_c = tabla_cierres.query(KeyConditionExpression=Key('TenantID').eq(st.session_state.tenant), FilterExpression=Attr('Fecha').eq(ayer))
            if res_v.get('Items') and not res_c.get('Items'):
                users = {}
                for v in res_v.get('Items'): users[v['Usuario']] = users.get(v['Usuario'], Decimal('0.00')) + Decimal(str(v['Total']))
                st.warning(f"⚠️ {len(users)} no cerraron")
                u_sel = st.selectbox("Empleado:", list(users.keys()))
                st.metric("Pendiente", f"S/ {float(users[u_sel]):.2f}")
                if st.button("🔒 CERRAR CAJA EMPLEADO", use_container_width=True):
                    registrar_cierre(users[u_sel], u_sel, "CIERRE TARDÍO DUEÑO", st.session_state.usuario, ayer); st.success("✅"); time.sleep(1); st.rerun()
            else: st.success("✅ Todo cerrado")
        else: st.info("⏰ Solo 12am-6am")

    st.markdown("---")
    st.caption(f"📲 Soporte: +{NUMERO_SOPORTE}")
    st.caption(f"💳 Yape/Plin: {YAPE_SOPORTE}")
    if st.button("🔴 CERRAR SESIÓN"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()
# === LOGIN ===
if not st.session_state.auth:
    st.markdown("<h1 style='text-align:center;color:#3498db;'>🚀 NEXUS BALLARTA</h1>", unsafe_allow_html=True)
    st.caption(f"<center>{DESARROLLADOR}</center>", unsafe_allow_html=True)
    tenants = [k for k in st.secrets if k not in ["tablas", "aws"] and not k.endswith("_emp")]
    t_sel = st.selectbox("📍 Negocio:", [t.replace("_", " ") for t in tenants])
    t_key = t_sel.replace(" ", "_")
    clave = st.text_input("🔑 Contraseña:", type="password").strip()[:30]
    col1, col2 = st.columns(2)
    if col1.button("🔓 DUEÑO", use_container_width=True):
        if clave == str(st.secrets[t_key]["clave"]):
            st.session_state.update({'auth':True,'tenant':t_sel,'rol':'DUEÑO','usuario':'DUEÑO'}); st.rerun()
        else: st.error("❌ Incorrecta")
    with col2:
        nombre = st.text_input("👤 Tu nombre:", max_chars=20).upper().strip()
        if st.button("🧑‍💼 EMPLEADO", use_container_width=True):
            if nombre and clave == str(st.secrets[f"{t_key}_emp"]["clave"]):
                st.session_state.update({'auth':True,'tenant':t_sel,'rol':'EMPLEADO','usuario':nombre}); st.rerun()
            else: st.error("❌ Nombre o clave incorrecta")
    st.stop()

# === POST LOGIN ===
MAX_PRODUCTOS_TOTALES, MAX_STOCK_POR_PRODUCTO, PLAN_ACTUAL, PRECIO_ACTUAL = obtener_limites_tenant()
df_inv = obtener_datos()
if st.session_state.get('modo_lectura', False): st.warning(st.session_state.mensaje_lectura)

# === TABS ===
tabs_list = ["🛒 VENTA", "📦 STOCK", "📊 REPORTES"]
if st.session_state.rol == "DUEÑO" and not st.session_state.get('modo_lectura', False):
    tabs_list += ["📋 HISTORIAL", "📥 CARGAR", "🛠️ MANT."]
tabs = st.tabs(tabs_list)

# === TAB VENTA ===
with tabs[0]:
    if st.session_state.boleta:
        b = st.session_state.boleta
        st.success("✅ VENTA REALIZADA")
        st.markdown(f"""<div style="background:white;color:black;padding:20px;border:2px solid #333;max-width:350px;margin:auto;font-family:monospace;">
            <h3 style="text-align:center;margin:0;">{st.session_state.tenant}</h3>
            <p style="text-align:center;margin:0;">{b['fecha']} {b['hora']}</p><hr>
            {''.join([f'<div style="display:flex;justify-content:space-between;"><span>{i["Cantidad"]}x {i["Producto"]}</span><span>S/{float(i["Subtotal"]):.2f}</span></div>' for i in b['items']])}
            <hr><div style="display:flex;justify-content:space-between;"><span>MÉTODO:</span><span>{b['metodo']}</span></div>
            <div style="display:flex;justify-content:space-between;color:red;"><span>DESC:</span><span>- S/{float(b['rebaja']):.2f}</span></div>
            <div style="display:flex;justify-content:space-between;font-size:18px;"><b>NETO:</b><b>S/{float(b['t_neto']):.2f}</b></div></div>""", unsafe_allow_html=True)
        if tiene_whatsapp_habilitado():
            texto = f"*TICKET - {st.session_state.tenant}*\n{b['fecha']} {b['hora']}\n---\n" + "\n".join([f"{i['Cantidad']}x {i['Producto']} - S/{float(i['Subtotal']):.2f}" for i in b['items']]) + f"\n---\n*TOTAL: S/{float(b['t_neto']):.2f}*\nMetodo: {b['metodo']}"
            st.link_button("📲 WhatsApp", f"https://wa.me/?text={urllib.parse.quote(texto)}", use_container_width=True)
        if st.button("⬅️ NUEVA VENTA", use_container_width=True): st.session_state.boleta = None; st.rerun()
    else:
        st.subheader("🛍️ Nueva Venta")
        busq = st.text_input("🔍 Buscar:", key="bv").upper()
        ops = []
        for _, f in df_inv.iterrows():
            if busq in str(f['Producto']):
                est = f"STOCK: {f['Stock']}" if f['Stock'] > 0 else "🚫 AGOTADO"
                ops.append(f"{f['Producto']} | S/ {f['Precio']:.2f} | {est}")
        col1, col2 = st.columns([3, 1])
        sel = col1.selectbox("Producto:", ops, key="sel_v")
        p_sel = sel.split(" | ")[0] if sel else None
        cant = col2.number_input("Cant:", min_value=1, value=1, key="cant_v")
        if p_sel:
            dp = df_inv[df_inv['Producto'] == p_sel].iloc[0]
            en_carro = sum(i['Cantidad'] for i in st.session_state.carrito if i['Producto'] == p_sel)
            disp = dp.Stock - en_carro
            st.info(f"Disponible: {disp}")
            if st.button("➕ Añadir", use_container_width=True):
                if cant <= disp:
                    st.session_state.carrito.append({'Producto': p_sel, 'Cantidad': int(cant), 'Precio': to_decimal(dp.Precio), 'Precio_Compra': to_decimal(dp.Precio_Compra), 'Subtotal': to_decimal(dp.Precio) * int(cant)})
                    st.rerun()
                else: st.error("❌ Sin stock")
        if st.session_state.carrito:
            st.table(pd.DataFrame(st.session_state.carrito)[['Producto', 'Cantidad', 'Subtotal']])
            if st.button("🗑️ VACIAR"): st.session_state.carrito = []; st.rerun()
            metodo = st.radio("Pago:", ["💵 EFECTIVO", "🟣 YAPE", "🔵 PLIN"], horizontal=True)
            rebaja = st.number_input("💸 Descuento:", min_value=0.0, value=0.0)
            total = max(Decimal('0.00'), sum(i['Subtotal'] for i in st.session_state.carrito) - to_decimal(rebaja))
            st.markdown(f"<h1 style='text-align:center;color:#2ecc71;'>S/ {float(total):.2f}</h1>", unsafe_allow_html=True)
            if st.button("🚀 FINALIZAR", use_container_width=True, type="primary"): st.session_state.confirmar = True
            if st.session_state.confirmar:
                if st.button(f"✅ CONFIRMAR S/ {float(total):.2f}", use_container_width=True):
                    f, h, uid = obtener_tiempo_peru()
                    for item in st.session_state.carrito:
                        tabla_stock.update_item(Key={'TenantID': st.session_state.tenant, 'Producto': item['Producto']}, UpdateExpression="SET Stock = Stock - :s", ConditionExpression="Stock >= :s", ExpressionAttributeValues={':s': item['Cantidad']})
                        tabla_ventas.put_item(Item={'TenantID': st.session_state.tenant, 'VentaID': f"V-{uid}", 'Fecha': f, 'Hora': h, 'Producto': item['Producto'], 'Cantidad': int(item['Cantidad']), 'Total': item['Subtotal'], 'Precio_Compra': item['Precio_Compra'], 'Metodo': metodo, 'Rebaja': to_decimal(rebaja), 'Usuario': st.session_state.usuario})
                        registrar_kardex(item['Producto'], item['Cantidad'], "VENTA", item['Subtotal'], item['Precio_Compra'], metodo)
                    st.session_state.boleta = {'items': st.session_state.carrito, 't_neto': total, 'rebaja': to_decimal(rebaja), 'metodo': metodo, 'fecha': f, 'hora': h}
                    st.session_state.carrito = []; st.session_state.confirmar = False; st.rerun()
# === TAB STOCK ===
with tabs[1]:
    st.subheader("📦 Inventario")
    if not df_inv.empty:
        busq = st.text_input("🔍 Buscar:", key="bs").upper()
        df_f = df_inv[df_inv['Producto'].str.contains(busq)] if busq else df_inv
        st.dataframe(df_f[['Producto', 'Stock', 'Precio_Compra', 'Precio']], use_container_width=True, hide_index=True)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as w: df_f.to_excel(w, index=False)
        st.download_button("📥 DESCARGAR EXCEL", buf.getvalue(), f"Inventario_{st.session_state.tenant}_{datetime.now(tz_peru).strftime('%Y%m%d')}.xlsx", use_container_width=True)
        bajo = df_f[df_f['Stock'] < 5]
        if not bajo.empty: st.warning(f"⚠️ Stock crítico: {len(bajo)} productos"); st.dataframe(bajo[['Producto', 'Stock']], hide_index=True)
    else: st.info("No hay productos")

# === TAB REPORTES PARCHADO ===
with tabs[2]:
    if st.session_state.rol == "DUEÑO":
        fecha = st.date_input("Día:", value=datetime.now(tz_peru).date(), label_visibility="collapsed")
        if st.button("📈 GENERAR", use_container_width=True, type="primary"):
            fecha_iso = fecha.strftime('%Y-%m-%d')
            res = tabla_movs.query(IndexName='TenantID-FechaISO-index', KeyConditionExpression=Key('TenantID').eq(st.session_state.tenant) & Key('FechaISO').eq(fecha_iso))
            items = res.get('Items', [])
            df_v = pd.DataFrame([m for m in items if m['Tipo'] == 'VENTA'])

            if not df_v.empty:
                df_v['Total'] = pd.to_numeric(df_v['Total'], errors='coerce').fillna(0)
                df_v['Precio_Compra'] = pd.to_numeric(df_v['Precio_Compra'], errors='coerce').fillna(0)
                df_v['Cantidad'] = pd.to_numeric(df_v['Cantidad'], errors='coerce').fillna(0)

                vt = df_v['Total'].sum(); tk = len(df_v); tp = vt/tk if tk else 0; gn = vt - (df_v['Precio_Compra'] * df_v['Cantidad']).sum()

                st.markdown(f"### 💰 VENTA TOTAL\n<h1 style='margin:0;font-size:48px;'>S/ {float(vt):.2f}</h1>", unsafe_allow_html=True)
                st.write("")
                st.markdown(f"### 🧾 TICKET PROMEDIO\n<h1 style='margin:0;font-size:48px;'>S/ {float(tp):.2f}</h1>", unsafe_allow_html=True)
                st.markdown(f"<div style='background:#2ecc71;color:white;padding:4px 12px;border-radius:20px;display:inline-block;font-size:14px;'>↑ {tk} Tickets</div>", unsafe_allow_html=True)
                st.write("")
                st.markdown(f"### 📈 GANANCIA\n<h1 style='margin:0;font-size:48px;'>S/ {float(gn):.2f}</h1>", unsafe_allow_html=True)
                st.write("---")

                # === MÉTODOS DE PAGO SEPARADOS ===
                if 'Metodo' in df_v.columns:
                    metodos = df_v['Metodo'].fillna('').astype(str)

                    total_ef = df_v[metodos.str.contains('EFECTIVO', na=False)]['Total'].sum()
                    if total_ef > 0:
                        st.markdown(f"### 💵 EFECTIVO\n<h1 style='margin:0;font-size:48px;'>S/ {float(total_ef):.2f}</h1>", unsafe_allow_html=True)
                        st.write("")

                    total_yape = df_v[metodos.str.contains('YAPE', na=False)]['Total'].sum()
                    if total_yape > 0:
                        st.markdown(f"### 🟣 YAPE\n<h1 style='margin:0;font-size:48px;'>S/ {float(total_yape):.2f}</h1>", unsafe_allow_html=True)
                        st.write("")

                    total_plin = df_v[metodos.str.contains('PLIN', na=False)]['Total'].sum()
                    if total_plin > 0:
                        st.markdown(f"### 🔵 PLIN\n<h1 style='margin:0;font-size:48px;'>S/ {float(total_plin):.2f}</h1>", unsafe_allow_html=True)
                else:
                    st.error("⚠️ Las ventas viejas no tienen campo Metodo. Vende algo nuevo con YAPE pa' probar.")
            else:
                st.info(f"No hay ventas {fecha.strftime('%d/%m/%Y')}")
# === TAB HISTORIAL/CARGAR/MANT SOLO DUEÑO ===
if st.session_state.rol == "DUEÑO" and not st.session_state.get('modo_lectura', False):
    # TAB 3: HISTORIAL
    with tabs[3]:
        st.subheader("📋 Kardex")
        fecha_b = st.date_input("📅 Fecha:", value=datetime.now(tz_peru).date(), key="hf")
        if st.button("🔎 BUSCAR", use_container_width=True, type="primary"):
            res = tabla_movs.query(IndexName='TenantID-FechaISO-index', KeyConditionExpression=Key('TenantID').eq(st.session_state.tenant) & Key('FechaISO').eq(fecha_b.strftime('%Y-%m-%d')), Limit=500)
            df_h = pd.DataFrame(res.get('Items', []))
            if not df_h.empty: st.dataframe(df_h[['Hora', 'Producto', 'Cantidad', 'Metodo', 'Tipo', 'Usuario']], use_container_width=True, hide_index=True)
            else: st.info("No hay movimientos")
        with st.expander("📥 DESCARGAR MES"):
            mes = st.date_input("Mes:", value=datetime.now(tz_peru).date().replace(day=1))
            if st.button("📊 EXCEL MES", use_container_width=True):
                inicio = mes.replace(day=1).strftime('%Y-%m-%d')
                fin = (mes.replace(month=mes.month+1, day=1) - timedelta(days=1)).strftime('%Y-%m-%d') if mes.month < 12 else (mes.replace(year=mes.year+1, month=1, day=1) - timedelta(days=1)).strftime('%Y-%m-%d')
                res = tabla_movs.query(IndexName='TenantID-FechaISO-index', KeyConditionExpression=Key('TenantID').eq(st.session_state.tenant) & Key('FechaISO').between(inicio, fin))
                df_m = pd.DataFrame(res.get('Items', []))
                if not df_m.empty:
                    buf = io.BytesIO()
                    with pd.ExcelWriter(buf, engine='openpyxl') as w: df_m.to_excel(w, index=False)
                    st.download_button("📥 DESCARGAR", buf.getvalue(), f"Kardex_{mes.strftime('%Y%m')}.xlsx", use_container_width=True)

    # TAB 4: CARGAR
    with tabs[4]:
        st.subheader("📂 Carga Masiva")
        st.caption(f"Columnas: Producto, Precio_Compra, Precio, Stock | Máx: 500")
        archivo = st.file_uploader("Excel/CSV", type=['xlsx', 'csv'])
        if archivo:
            df_b = pd.read_excel(archivo) if archivo.name.endswith('xlsx') else pd.read_csv(archivo)
            df_b.columns = [str(c).strip().title() for c in df_b.columns]
            st.write(df_b.head(3))
            if len(df_b) > 500: st.error("❌ Máx 500"); st.stop()
            if contarProductosEnBD() + len(df_b) > MAX_PRODUCTOS_TOTALES: st.error(f"❌ Solo {MAX_PRODUCTOS_TOTALES - contarProductosEnBD()} espacios"); st.stop()
            if st.button("⚡ PROCESAR", use_container_width=True):
                barra = st.progress(0)
                with tabla_stock.batch_writer() as batch:
                    for i, f in df_b.iterrows():
                        p = str(f['Producto']).upper().strip()
                        batch.put_item(Item={'TenantID': st.session_state.tenant, 'Producto': p, 'Precio_Compra': to_decimal(f['Precio_Compra']), 'Precio': to_decimal(f['Precio']), 'Stock': int(f['Stock'])})
                        registrar_kardex(p, int(f['Stock']), "CARGA MASIVA", to_decimal(f['Precio']) * int(f['Stock']), to_decimal(f['Precio_Compra']), "")
                        barra.progress((i + 1) / len(df_b))
                st.success(f"✅ {len(df_b)} productos"); time.sleep(1); st.rerun()

    # TAB 5: MANT
    with tabs[5]:
        st.subheader("🛠️ Mantenimiento")
        with st.expander("➕ CREAR PRODUCTO"):
            c1, c2 = st.columns(2)
            np = c1.text_input("Nombre:").upper().strip()
            nc = c1.number_input("Precio Compra:", min_value=0.0)
            nv = c2.number_input("Precio Venta:", min_value=0.0)
            ns = c2.number_input("Stock:", min_value=1, value=1)
            if st.button("💾 CREAR", use_container_width=True):
                if np and ns > 0 and contarProductosEnBD() < MAX_PRODUCTOS_TOTALES:
                    tabla_stock.put_item(Item={'TenantID': st.session_state.tenant, 'Producto': np, 'Precio_Compra': to_decimal(nc), 'Precio': to_decimal(nv), 'Stock': int(ns)})
                    registrar_kardex(np, ns, "PRODUCTO NUEVO", to_decimal(nv) * ns, to_decimal(nc), "")
                    st.success(f"✅ {np} creado"); time.sleep(1); st.rerun()
        st.divider()
        acc = st.radio("Acción:", ["➕ REPONER", "📝 PRECIOS", "🗑️ ELIMINAR"], horizontal=True)
        busq_m = st.text_input("🔍 Buscar:").upper()
        lista = [p for p in df_inv['Producto'].tolist() if busq_m in str(p)]
        if lista:
            p_sel = st.selectbox("Producto:", lista)
            idx = df_inv[df_inv['Producto'] == p_sel].index[0]
            if acc == "➕ REPONER":
                cant = st.number_input("Ingreso:", min_value=1)
                if st.button("✅ ACTUALIZAR"):
                    nuevo = int(df_inv.at[idx, 'Stock'] + cant)
                    if nuevo <= MAX_STOCK_POR_PRODUCTO:
                        tabla_stock.update_item(Key={'TenantID': st.session_state.tenant, 'Producto': p_sel}, UpdateExpression="SET Stock = :s", ExpressionAttributeValues={':s': nuevo})
                        registrar_kardex(p_sel, cant, f"REPOSICIÓN", 0, 0, ""); st.success("✅"); time.sleep(1); st.rerun()
                    else: st.error(f"❌ Máx {MAX_STOCK_POR_PRODUCTO}")
            elif acc == "📝 PRECIOS":
                nc = st.number_input("Costo:", value=float(df_inv.at[idx, 'Precio_Compra']))
                nv = st.number_input("Venta:", value=float(df_inv.at[idx, 'Precio']))
                if st.button("💾 GUARDAR"):
                    tabla_stock.update_item(Key={'TenantID': st.session_state.tenant, 'Producto': p_sel}, UpdateExpression="SET Precio_Compra=:pc,Precio=:pv", ExpressionAttributeValues={':pc': to_decimal(nc), ':pv': to_decimal(nv)})
                    registrar_kardex(p_sel, 0, "CAMBIO PRECIOS", 0, 0, ""); st.success("✅"); time.sleep(1); st.rerun()
            else:
                if st.button(f"🗑️ ELIMINAR {p_sel}"):
                    tabla_stock.delete_item(Key={'TenantID': st.session_state.tenant, 'Producto': p_sel})
                    registrar_kardex(p_sel, 0, "BORRADO", 0, 0, ""); st.warning("Eliminado"); time.sleep(1); st.rerun()
# === SIDEBAR ===
with st.sidebar:
    st.title(f"🏢 {st.session_state.tenant}")
    st.write(f"Usuario: **{st.session_state.usuario}**")
    st.caption(f"{'🔵' if PLAN_ACTUAL=='BASICO' else '🟣' if PLAN_ACTUAL=='PRO' else '🟡'} **Plan {PLAN_ACTUAL}** | S/ {float(PRECIO_ACTUAL):.0f}/mes")

    st.markdown("---")
    if st.button("🔒 CERRAR CAJA", use_container_width=True, type="primary"):
        f_hoy, _, _ = obtener_tiempo_peru()
        res_c = tabla_cierres.query(KeyConditionExpression=Key('TenantID').eq(st.session_state.tenant), FilterExpression=Attr('Fecha').eq(f_hoy) & Attr('UsuarioTurno').eq(st.session_state.usuario))
        cierres = res_c.get('Items', [])
        hora_ult = max([c['Hora'] for c in cierres]) if cierres else "00:00:00"
        res_v = tabla_ventas.query(KeyConditionExpression=Key('TenantID').eq(st.session_state.tenant), FilterExpression=Attr('Fecha').eq(f_hoy) & Attr('Usuario').eq(st.session_state.usuario) & Attr('Hora').gt(hora_ult))
        total = sum([Decimal(str(v['Total'])) for v in res_v.get('Items', [])])
        if total > 0: registrar_cierre(total, st.session_state.usuario, f"CIERRE {st.session_state.rol}", st.session_state.usuario); st.success(f"✅ S/ {float(total):.2f}"); st.balloons(); time.sleep(1); st.rerun()
        else: st.warning("No hay ventas nuevas")

    if st.session_state.rol == "DUEÑO":
        st.markdown("---"); st.subheader("🚨 CIERRE TARDÍO")
        if 0 <= datetime.now(tz_peru).hour <= 6:
            ayer = (datetime.now(tz_peru) - timedelta(days=1)).strftime("%d/%m/%Y")
            res_v = tabla_ventas.query(KeyConditionExpression=Key('TenantID').eq(st.session_state.tenant), FilterExpression=Attr('Fecha').eq(ayer))
            res_c = tabla_cierres.query(KeyConditionExpression=Key('TenantID').eq(st.session_state.tenant), FilterExpression=Attr('Fecha').eq(ayer))
            if res_v.get('Items') and not res_c.get('Items'):
                users = {}
                for v in res_v.get('Items'): users[v['Usuario']] = users.get(v['Usuario'], Decimal('0.00')) + Decimal(str(v['Total']))
                st.warning(f"⚠️ {len(users)} no cerraron")
                u_sel = st.selectbox("Empleado:", list(users.keys()))
                st.metric("Pendiente", f"S/ {float(users[u_sel]):.2f}")
                if st.button("🔒 CERRAR CAJA EMPLEADO", use_container_width=True):
                    registrar_cierre(users[u_sel], u_sel, "CIERRE TARDÍO DUEÑO", st.session_state.usuario, ayer); st.success("✅"); time.sleep(1); st.rerun()
            else: st.success("✅ Todo cerrado")
        else: st.info("⏰ Solo 12am-6am")

    st.markdown("---")
    st.caption(f"📲 Soporte: +{NUMERO_SOPORTE}")
    st.caption(f"💳 Yape/Plin: {YAPE_SOPORTE}")
    if st.button("🔴 CERRAR SESIÓN"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()
