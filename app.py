import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import re

st.set_page_config(page_title="Alicantina de Vallas - Smart", page_icon="🏗️")

# LÓGICA DE MÁRGENES
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

st.title("🏗️ Lector de Albaranes Inteligente")

if 'lista' not in st.session_state: st.session_state.lista = []

# --- SECCIÓN DE LECTURA DE FOTO ---
st.sidebar.header("📷 Escanear Albarán")
foto = st.sidebar.file_uploader("Sube la foto del proveedor", type=['jpg', 'png', 'jpeg'])

if foto:
    img = Image.open(foto)
    texto = pytesseract.image_to_string(img)
    st.sidebar.success("¡Foto leída!")
    
    # Intento de extraer precios automáticamente (Busca números con decimales)
    precios = re.findall(r'\d+,\d{2}', texto)
    if precios:
        st.sidebar.write("He detectado estos posibles importes:")
        for p in precios[:5]: # Mostramos los 5 primeros para no saturar
            st.sidebar.code(f"{p} €")

# --- FORMULARIO MANUAL / CONFIRMACIÓN ---
with st.expander("📝 Confirmar datos del producto", expanded=True):
    with st.form("add_form", clear_on_submit=True):
        col1, col2, col3 = st.columns([3, 1, 1])
        d = col1.text_input("Producto / Descripción")
        n = col2.number_input("Cant", min_value=1, value=1)
        c = col3.number_input("Coste Proveedor (€)", min_value=0.0, step=0.01)
        if st.form_submit_button("Añadir al Presupuesto"):
            if d:
                pvp = calcular_pvp(c)
                st.session_state.lista.append({
                    "Descripción": d, "Cant": n, "PVP Ud": round(pvp, 2), "Total": round(pvp * n, 2)
                })

# --- DISEÑO DEL PRESUPUESTO ---
if st.session_state.lista:
    st.markdown("---")
    st.subheader("MANTENIMIENTOS ALICANTINA DE VALLAS S.L.")
    st.write("Calle Burgos N12-14, 03015 Alicante")
    
    df = pd.DataFrame(st.session_state.lista)
    st.table(df)
    
    total = df["Total"].sum()
    st.metric("TOTAL (con IVA)", f"{total * 1.21:.2f} €")
    
    if st.button("Limpiar todo"):
        st.session_state.lista = []
        st.rerun()
