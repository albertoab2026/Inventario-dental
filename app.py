# --- 6. PANEL DE ADMINISTRADOR ---
st.divider()

# Usamos un estado para controlar si mostramos el contenido o no
if 'admin_autenticado' not in st.session_state:
    st.session_state.admin_autenticado = False

with st.expander("🔐 PANEL DE ADMINISTRADOR"):
    # Si no está autenticado, pide la clave
    if not st.session_state.admin_autenticado:
        clave_ingresada = st.text_input("Contraseña de Seguridad:", type="password", key="input_clave")
        
        if clave_ingresada == "admin123":
            st.session_state.admin_autenticado = True
            st.rerun()
        elif clave_ingresada != "":
            st.error("❌ Clave incorrecta")
    
    # Si ya puso la clave bien, mostramos los controles y un botón de CERRAR SESIÓN
    else:
        st.success("✅ Modo Administrador Activo")
        
        if st.session_state.ventas_dia:
            df_recaudacion = pd.DataFrame(st.session_state.ventas_dia)
            st.write(f"### 💰 CAJA TOTAL: S/ {df_recaudacion['Total'].sum():,.2f}")
            st.table(df_recaudacion)
            
            if st.button("🗑️ LIMPIAR CAJA Y CERRAR"):
                st.session_state.ventas_dia = []
                st.session_state.admin_autenticado = False # Cerramos sesión
                st.success("Caja limpia y sesión cerrada.")
                st.rerun()
        else:
            st.info("No hay ventas registradas.")
            if st.button("Cerrar Sesión"):
                st.session_state.admin_autenticado = False
                st.rerun()
