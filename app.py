import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd

# CONFIGURACIÓN BÁSICA
st.set_page_config(page_title="Alicantina de Vallas", layout="wide")

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

# CONEXIÓN
if "GEMINI_API_KEY" not in st.secrets:
    st.error("Falta la clave en Secrets")
else:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

st.title("🏗️ Generador Automático")
cliente = st.text_input("👤 Nombre del Cliente")

if 'lista' not in st.session_state:
    st.session_state.lista = []

foto = st.file_uploader("📷 Sube el presupuesto del proveedor", type=['jpg', 'png', 'jpeg'])

if foto and st.button("🔍 Analizar y Calcular"):
    try:
        img = Image.open(foto)
        # Usamos el nombre de modelo más básico para evitar el 404
        model = genai.GenerativeModel('gemini-pro-vision')
        
        prompt = "Analiza la imagen y extrae los productos en este formato: NOMBRE | CANTIDAD | PRECIO_COSTE. No escribas nada más."
        
        response = model.generate_content([prompt, img])
        
        lineas = response.text.split('\n')
        for linea in lineas:
            if '|' in linea:
                partes = linea.split('|')
                try:
                    desc = partes[0].strip()
                    cant = float(partes[1].strip().replace(',', '.'))
                    coste = float(partes[2].strip().replace(',', '.').replace('€', ''))
                    pvp = calcular_pvp(coste)
                    st.session_state.lista.append({
                        "Descripción": desc, "Cant": int(cant), 
                        "Precio Ud. (€)": round(pvp, 2), "Total (€)": round(pvp * cant, 2)
                    })
                except: continue
        st.success("¡Lectura finalizada!")
    except Exception as e:
        st.error(f"Error: {e}")

# MOSTRAR RESULTADOS
if st.session_state.lista:
    st.markdown("---")
    st.subheader(f"Presupuesto: {cliente}")
    df = pd.DataFrame(st.session_state.lista)
    st.table(df)
    total = df["Total (€)"].sum()
    st.subheader(f"TOTAL + IVA: {total * 1.21:.2f} €")
    if st.button("Limpiar"):
        st.session_state.lista = []
        st.rerun()
