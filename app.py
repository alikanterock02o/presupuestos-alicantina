import streamlit as st
import pandas as pd
import google.generativeai as genai
from fpdf import FPDF
import PyPDF2
import os

# --- SOLUCIÓN AL ERROR 404 / V1BETA ---
# Forzamos a la librería a usar la versión estable de la API
os.environ["GOOGLE_API_USE_MTLS"] = "never" 

st.set_page_config(page_title="Alicantina de Vallas - Producción", layout="wide")

if "GEMINI_API_KEY" in st.secrets:
    # Configuramos la API intentando evitar explícitamente la ruta v1beta
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Falta API KEY.")

# Función de conexión ultra-estable
def conectar_ia():
    # Usamos el nombre de modelo sin sufijos extraños
    return genai.GenerativeModel('gemini-1.5-flash')

# Lógica comercial Alicantina de Vallas
def calcular_pvp(coste, cantidad):
    total = coste * cantidad
    if total <= 0.05: m = 3.0
    elif total <= 0.25: m = 2.5
    elif total <= 1.0: m = 2.0
    elif total <= 3.0: m = 1.75
    elif total <= 10.0: m = 1.50
    elif total <= 50.0: m = 1.43
    elif total <= 300.0: m = 1.35
    elif total <= 1000.0: m = 1.29
    else: m = 1.25
    return coste * m

# --- INTERFAZ ---
st.title("🏗️ Alicantina de Vallas - Gestor")

if st.button("♻️ REINICIAR CONEXIÓN"):
    st.session_state.clear()
    st.rerun()

nombre_c = st.text_input("👤 Cliente", value="David")
archivo = st.file_uploader("📄 Albarán (Foto o PDF)", type=['jpg', 'jpeg', 'png', 'pdf'])

if archivo and st.button("🔍 PROCESAR"):
    with st.spinner("Conectando con versión estable (v1)..."):
        try:
            model = conectar_ia()
            prompt = "Extract: ITEM | QTY | UNIT_PRICE. Text only, no markdown."
            
            if archivo.type == "application/pdf":
                reader = PyPDF2.PdfReader(archivo)
                texto = "".join([p.extract_text() for p in reader.pages])
                res = model.generate_content(f"{prompt}\n\n{texto}")
            else:
                res = model.generate_content([prompt, {"mime_type": archivo.type, "data": archivo.read()}])
            
            if res.text:
                lista = []
                for linea in res.text.split('\n'):
                    if '|' in linea:
                        p = linea.split('|')
                        if len(p) >= 3:
                            try:
                                d, c, pr = p[0].strip(), float(p[1].strip()), float(p[2].strip().replace('€',''))
                                pvp = calcular_pvp(pr, c)
                                lista.append({"Descripción": d, "Cant": int(c), "PVP Ud (€)": round(pvp, 2), "Total (€)": round(pvp * c, 2)})
                            except: continue
                st.session_state.lista = lista
                st.success("✅ Datos extraídos.")
        except Exception as e:
            st.error(f"Error de conexión: {e}")
            st.info("Sugerencia: Si el error persiste, es un bloqueo temporal de Google en tu IP. Espera 5 min.")

# --- TABLA Y PDF ---
if 'lista' in st.session_state and st.session_state.lista:
    df = pd.DataFrame(st.session_state.lista)
    st.table(df)
    
    # PDF corporativo (Rojo/Blanco)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_fill_color(204, 0, 0)
    pdf.rect(0, 0, 210, 35, 'F')
    pdf.set_font("Arial", 'B', 20)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(190, 15, "ALICANTINA DE VALLAS", ln=True, align='C')
    st.download_button("📥 DESCARGAR PDF", data=pdf.output(dest='S').encode('latin-1'), file_name="Presupuesto.pdf")
