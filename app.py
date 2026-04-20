import streamlit as st
import pandas as pd
import google.generativeai as genai
from fpdf import FPDF
import PyPDF2

# 1. INICIO SEGURO
st.set_page_config(page_title="Alicantina de Vallas - Gestor", layout="wide")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("⚠️ Configura la API KEY en Secrets.")

# Lógica de precios de David
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

# 2. MOTOR DE IA (Versión Estándar)
def analizar_documento(archivo):
    # GenerativeModel sin parámetros extra para evitar el TypeError
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = "Analiza y devuelve: PRODUCTO | CANTIDAD | PRECIO_COSTE. Solo texto."
    
    try:
        if archivo.type == "application/pdf":
            reader = PyPDF2.PdfReader(archivo)
            texto = ""
            for page in reader.pages:
                texto += page.extract_text()
            response = model.generate_content(prompt + "\n\n" + texto)
        else:
            # Procesar como imagen (JPG/PNG)
            import PIL.Image
            img = PIL.Image.open(archivo)
            response = model.generate_content([prompt, img])
        
        return response.text
    except Exception as e:
        return f"ERROR_SISTEMA: {str(e)}"

# 3. INTERFAZ
st.title("🏗️ Alicantina de Vallas")

if st.button("♻️ REINICIAR"):
    st.session_state.clear()
    st.rerun()

nombre_cliente = st.text_input("👤 Cliente", value="David")

if 'datos' not in st.session_state:
    st.session_state.datos = []

archivo = st.file_uploader("📄 Sube tu documento", type=['jpg', 'jpeg', 'png', 'pdf'])

if archivo and st.button("🚀 PROCESAR"):
    with st.spinner("Conectando con Google..."):
        resultado = analizar_documento(archivo)
        
        if "ERROR_SISTEMA" in resultado:
            st.error(f"Error técnico: {resultado}")
        else:
            lineas = resultado.split('\n')
            temp_lista = []
            for l in lineas:
                if '|' in l:
                    try:
                        p = l.split('|')
                        desc = p[0].strip()
                        cant = float(p[1].strip())
                        coste = float(p[2].strip().replace('€',''))
                        
                        pvp = calcular_pvp(coste, cant)
                        temp_lista.append({
                            "Descripción": desc,
                            "Cant": int(cant),
                            "PVP Ud (€)": round(pvp, 2),
                            "Total (€)": round(pvp * cant, 2)
                        })
                    except: continue
            st.session_state.datos = temp_lista

# 4. TABLA Y EXPORTACIÓN
if st.session_state.datos:
    df = pd.DataFrame(st.session_state.datos)
    st.table(df)
    
    # Generar PDF rápido
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(190, 10, f"Presupuesto - {nombre_cliente}", ln=True, align='C')
    st.download_button("📥 DESCARGAR PDF", data=pdf.output(dest='S').encode('latin-1'), file_name="Presupuesto.pdf")
