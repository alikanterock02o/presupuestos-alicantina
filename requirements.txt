import streamlit as st
import pandas as pd
import google.generativeai as genai
from docx import Document
import PyPDF2

st.set_page_config(page_title="Alicantina de Vallas - Docs", layout="wide")

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
    st.error("Falta la API Key en Secrets")

st.title("🏗️ Generador Alicantina de Vallas (Documentos)")
cliente = st.text_input("👤 Nombre del Cliente")

if 'lista' not in st.session_state:
    st.session_state.lista = []

# CAMBIO: Ahora aceptamos PDF y Word
archivo = st.file_uploader("📄 Sube el presupuesto (PDF o Word)", type=['pdf', 'docx'])

if archivo and st.button("🔍 Analizar Documento"):
    texto_extraido = ""
    try:
        # Leer Word
        if archivo.name.endswith('.docx'):
            doc = Document(archivo)
            texto_extraido = "\n".join([para.text for para in doc.paragraphs])
        # Leer PDF
        else:
            reader = PyPDF2.PdfReader(archivo)
            for page in reader.pages:
                texto_extraido += page.extract_text()

        if texto_extraido:
            # Usamos el modelo de texto puro, que NO da el error 404 de la cámara
            model = genai.GenerativeModel('gemini-1.5-pro')
            prompt = f"De este texto de presupuesto, extrae: PRODUCTO | CANTIDAD | PRECIO_COSTE. Texto: {texto_extraido}"
            
            response = model.generate_content(prompt)
            
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
            st.success("✅ Documento procesado")
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")

if st.session_state.lista:
    st.write(f"### Presupuesto: {cliente}")
    df = pd.DataFrame(st.session_state.lista)
    st.table(df)
    total = df["Total (€)"].sum()
    st.subheader(f"TOTAL con IVA: {total * 1.21:.2f} €")
    if st.button("Limpiar"):
        st.session_state.lista = []
        st.rerun()
