import streamlit as st
import pandas as pd
import google.generativeai as genai
# Importamos 'types' para que la librería no dé el TypeError de antes
from google.generativeai import types 
from fpdf import FPDF
import PyPDF2
import PIL.Image

st.set_page_config(page_title="Alicantina de Vallas - Gestor", layout="wide")

# 1. SEGURIDAD DE API
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("⚠️ Falta la API KEY en Secrets.")

# Tu lógica de márgenes
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

# 2. EL MOTOR QUE SÍ FUNCIONA (v1 Forzada)
def analizar_documento(archivo):
    # Esta es la línea clave corregida para evitar el TypeError
    opciones = types.RequestOptions(api_version='v1')
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = "Extrae los datos: PRODUCTO | CANTIDAD | PRECIO_COSTE. Solo texto plano."
    
    try:
        if archivo.type == "application/pdf":
            reader = PyPDF2.PdfReader(archivo)
            texto = " ".join([p.extract_text() for p in reader.pages])
            response = model.generate_content(prompt + "\n\n" + texto, request_options=opciones)
        else:
            # Para fotos de WhatsApp (JPG/PNG)
            img = PIL.Image.open(archivo)
            response = model.generate_content([prompt, img], request_options=opciones)
        return response.text
    except Exception as e:
        return f"ERROR: {str(e)}"

# 3. INTERFAZ Y RESULTADOS
st.title("🏗️ Alicantina de Vallas - Gestor")

if st.button("♻️ REINICIAR Y LIMPIAR"):
    st.session_state.clear()
    st.rerun()

nombre = st.text_input("👤 Cliente", value="David")
archivo = st.file_uploader("📄 Sube albarán o foto", type=['jpg', 'jpeg', 'png', 'pdf'])

if archivo and st.button("🚀 PROCESAR"):
    with st.spinner("Conectando con Google vía estable..."):
        res = analizar_documento(archivo)
        
        if "ERROR" in res:
            st.error(f"Fallo en la conexión: {res}")
        else:
            datos_lista = []
            for linea in res.split('\n'):
                if '|' in linea:
                    try:
                        p = linea.split('|')
                        desc, cant, pre = p[0].strip(), float(p[1].strip()), float(p[2].strip().replace('€',''))
                        pvp_ud = calcular_pvp(pre, cant)
                        datos_lista.append({
                            "Descripción": desc, "Cant": int(cant), 
                            "PVP Ud (€)": round(pvp_ud, 2), "Total (€)": round(pvp_ud * cant, 2)
                        })
                    except: continue
            st.session_state.datos = datos_lista

if 'datos' in st.session_state and st.session_state.datos:
    df = pd.DataFrame(st.session_state.datos)
    st.table(df)
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, f"PRESUPUESTO - {nombre}", ln=True, align='C')
    st.download_button("📥 DESCARGAR PDF", data=pdf.output(dest='S').encode('latin-1'), file_name="Presupuesto.pdf")
