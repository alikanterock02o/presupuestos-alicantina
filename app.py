import streamlit as st
import pandas as pd
import base64

# CONFIGURACIÓN PROFESIONAL
st.set_page_config(page_title="Alicantina de Vallas - Presupuestos", page_icon="🏗️", layout="wide")

# LOGICA DE MARGENES (Tus tablas reales)
def calcular_pvp(coste):
    if coste <= 0.05: return coste * 3.0
    elif coste <= 0.25: return coste * 2.5
    elif coste <= 1.0: return coste * 2.0
    elif coste <= 3.0: return coste * 1.75
    elif coste <= 10.0: return coste * 1.50
    elif coste <= 50.0: return coste * 1.43
    elif coste <= 300.0: return coste * 1.35
    elif coste <= 1000.0: return coste * 1.29
    elif coste <= 3000.0: return coste * 1.25
    else: return coste * 1.20

# ESTILO PARA EL PRESUPUESTO FINAL
st.markdown("""
    <style>
    .reportview-container { background: #f0f2f6; }
    .print-container { background: white; padding: 40px; border: 1px solid #ddd; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏗️ Sistema de Presupuestos Inteligente")

# --- NUEVA FUNCIÓN: SUBIR FOTO ---
st.sidebar.header("📷 Lectura Automática")
archivo_foto = st.sidebar.file_uploader("Sube la foto del albarán", type=['jpg', 'png', 'jpeg'])

if archivo_foto:
    st.sidebar.success("Foto cargada. (En la v2 conectaremos la IA para leerla sola)")
    st.sidebar.info("💡 Por ahora, introduce los datos abajo. Estoy configurando el lector automático.")

# --- FORMULARIO DE PRODUCTOS ---
if 'lista' not in st.session_state: st.session_state.lista = []

with st.expander("➕ Añadir Productos al Presupuesto", expanded=True):
    with st.form("add_form", clear_on_submit=True):
        col1, col2, col3 = st.columns([3, 1, 1])
        d = col1.text_input("Descripción del Artículo")
        n = col2.number_input("Cantidad", min_value=1, value=1)
        c = col3.number_input("Coste Proveedor (€)", min_value=0.0, step=0.01)
        if st.form_submit_button("Añadir"):
            if d:
                pvp = calcular_pvp(c)
                st.session_state.lista.append({
                    "Descripción": d, "Cant": n, 
                    "Precio Ud.": round(pvp, 2), "Total": round(pvp * n, 2)
                })

# --- VISTA PREVIA Y PDF ---
if st.session_state.lista:
    st.markdown('<div class="print-container">', unsafe_allow_html=True)
    st.header("PRESUPUESTO")
    st.write("**Mantenimientos Alicantina de Vallas S.L.**")
    
    df = pd.DataFrame(st.session_state.lista)
    st.table(df)
    
    sub = df["Total"].sum()
    iva = sub * 0.21
    total = sub + iva
    
    c1, c2 = st.columns(2)
    with c2:
        st.write(f"**Base Imponible:** {sub:.2f} €")
        st.write(f"**IVA (21%):** {iva:.2f} €")
        st.subheader(f"TOTAL: {total:.2f} €")
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("🗑️ Borrar y empezar nuevo"):
        st.session_state.lista = []
        st.rerun()

    st.write("---")
    st.info("Para generar el PDF: Pulsa **Ctrl + P** en PC o **Compartir > Imprimir** en móvil y selecciona 'Guardar como PDF'.")
