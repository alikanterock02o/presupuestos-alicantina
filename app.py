import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd

st.set_page_config(page_title="Alicantina de Vallas", layout="wide")

# Lógica de márgenes
def calcular_pvp(coste):
    if coste <= 0.05: return coste * 3.0
    elif coste <= 0.25: return coste * 2.5
    elif coste <= 1.0: return coste * 2.0
    elif coste <= 3.0: return coste * 1.75
    elif coste <= 10.0: return coste * 1.50
    elif coste <= 50.0: return coste * 1.43
    elif coste <= 300.0: return coste * 1.35
    elif coste <= 1000.0: return coste * 1.29
    else: return coste * 1.25

# CONFIGURACIÓN
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Configura la clave en Secrets")

st.title("🏗️ Generador Alicantina de Vallas")
cliente = st.text_input("👤 Nombre del Cliente")

if 'lista' not in st.session_state:
    st.session_state.lista = []

foto = st.file_uploader("📷 Sube el albarán", type=['jpg', 'png', 'jpeg'])

if foto and st.button("🔍 Analizar"):
    try:
        # Usamos el modelo flash-8b si el flash normal da 404, es casi igual de listo
        try:
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            img = Image.open(foto)
            response = model.generate_content(["Lee este albarán y extrae: NOMBRE | CANTIDAD | PRECIO_COSTE", img])
        except:
            model = genai.GenerativeModel('gemini-pro-vision')
            img = Image.open(foto)
            response = model.generate_content(["Lee este albarán y extrae: NOMBRE | CANTIDAD | PRECIO_COSTE", img])

        if response.text:
            for linea in response.text.split('\n'):
                if '|' in linea:
                    p = linea.split('|')
                    try:
                        desc = p[0].strip()
                        cant = float(p[1].strip().replace(',', '.'))
                        coste = float(p[2].strip().replace('€', '').replace(',', '.').strip())
                        pvp = calcular_pvp(coste)
                        st.session_state.lista.append({
                            "Descripción": desc, "Cant": int(cant), 
                            "PVP Ud (€)": round(pvp, 2), "Total (€)": round(pvp * cant, 2)
                        })
                    except: continue
            st.success("✅ ¡Leído!")
    except Exception as e:
        st.error(f"Error: {e}")

if st.session_state.lista:
    df = pd.DataFrame(st.session_state.lista)
    st.table(df)
    total = df["Total (€)"].sum()
    st.subheader(f"TOTAL: {total * 1.21:.2f} €")
    if st.button("Limpiar"):
        st.session_state.lista = []
        st.rerun()
