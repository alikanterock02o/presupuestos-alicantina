import streamlit as st
import pandas as pd
import google.generativeai as genai
# Importación específica para evitar el TypeError
from google.generativeai import types 
from fpdf import FPDF
import PyPDF2
import PIL.Image

st.set_page_config(page_title="Alicantina de Vallas - Oficial", layout="wide")

# Configuración de API
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Falta la API KEY en Secrets.")

# Tu tabla de márgenes comerciales
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

# EL MOTOR QUE FUNCIONA (v1 forzada)
def analizar_documento(archivo):
    # Forzamos v1 para evitar el 404 de la v1beta
    # Usamos la sintaxis correcta para evitar el TypeError
    model = genai.GenerativeModel('gemini-1.5-flash')
    config_v1 = types.RequestOptions(api_version='v1')
    
    prompt = "Extrae: PRODUCTO | CANTIDAD | PRECIO_COSTE. Solo texto plano."
    
    try:
        if archivo.type == "application/pdf":
            reader = PyPDF2.PdfReader(archivo)
            texto = " ".join([p.extract_text() for p in reader.pages])
            response = model.generate_content(prompt + "\n\n" + texto, request_options=config_v1)
        else:
            img = PIL.Image.open(archivo)
            response = model.generate_content([prompt, img], request_options=config_v1)
        return response.text
    except Exception as e:
        return f"ERROR_TECNICO: {str(e)}"

# INTERFAZ
st.title("🏗️ Alicantina de Vallas - Gestor")

if st.button("♻️ REINICIAR SISTEMA"):
    st.session_state.clear()
    st.rerun()

nombre = st.text_input("👤 Nombre Cliente", value="David")
archivo = st.file_uploader("📄 Albarán o Foto", type=['jpg', 'jpeg', 'png', 'pdf'])

if archivo and st.button("🔍 ANALIZAR AHORA"):
    with st.spinner("Conectando con servidor estable (v1)..."):
        res = analizar_documento(archivo)
        
        if "ERROR_TECNICO" in res:
            st.error(res)
        else:
            datos_lista = []
            for linea in res.split('\n'):
                if '|' in linea:
                    try:
                        p = linea.split('|')
                        d, c, pr = p[0].strip(), float(p[1].strip()), float(p[2].strip().replace('€',''))
                        pvp = calcular_pvp(pr, c)
                        datos_lista.append({
                            "Descripción": d, "Cant": int(c), 
                            "PVP Ud (€)": round(pvp, 2), "Total (€)": round(pvp * c, 2)
                        })
                    except: continue
            st.session_state.datos = datos_lista

# TABLA Y PDF
if 'datos' in st.session_state and st.session_state.datos:
    df = pd.DataFrame(st.session_state.datos)
    st.table(df)
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, f"PRESUPUESTO - {nombre}", ln=True, align='C')
    st.download_button("📥 DESCARGAR PDF", data=pdf.output(dest='S').encode('latin-1'), file_name="Presupuesto.pdf")
