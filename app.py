import streamlit as st
import pandas as pd
import google.generativeai as genai
from fpdf import FPDF
import PyPDF2

# 1. IDENTIDAD ALICANTINA DE VALLAS
st.set_page_config(page_title="Alicantina de Vallas - Pro", layout="wide")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Falta la API KEY en Secrets.")

# Función para encontrar el modelo disponible (Evita el 404)
def obtener_modelo_activo():
    try:
        # Listamos qué modelos tiene David permitidos ahora mismo
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                # Prioridad: Flash -> Pro -> Cualquier otro
                if '1.5-flash' in m.name: return m.name
                if '1.5-pro' in m.name: return m.name
        # Si no encuentra los anteriores, devuelve el primero disponible
        return genai.list_models()[0].name
    except:
        return "gemini-1.5-flash" # Fallback por si acaso

# Lógica de precios
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

# 2. PROCESAMIENTO DE DOCUMENTOS
def procesar_albaran(archivo, nombre_modelo):
    model = genai.GenerativeModel(nombre_modelo)
    prompt = "Extract data: ITEM | QTY | UNIT_PRICE. Clean text format only."
    
    if archivo.type == "application/pdf":
        reader = PyPDF2.PdfReader(archivo)
        texto = "".join([p.extract_text() for p in reader.pages])
        return model.generate_content(f"{prompt}\n\nTexto:\n{texto}")
    else:
        img = archivo.read()
        return model.generate_content([prompt, {"mime_type": archivo.type, "data": img}])

# 3. INTERFAZ
st.title("🏗️ Alicantina de Vallas - Gestor")

# Diagnóstico en vivo para David
nombre_modelo_real = obtener_modelo_activo()
st.info(f"📡 Conectado vía: {nombre_modelo_real}")

if st.button("♻️ LIMPIAR Y REINTENTAR"):
    st.session_state.lista = []
    st.rerun()

nombre_c = st.text_input("👤 Cliente", value="David")

if 'lista' not in st.session_state:
    st.session_state.lista = []

archivo = st.file_uploader("📄 Sube foto o PDF", type=['jpg', 'jpeg', 'png', 'pdf'])

if archivo and st.button("🔍 PROCESAR"):
    with st.spinner("Analizando albarán..."):
        try:
            res = procesar_albaran(archivo, nombre_modelo_real)
            if res.text:
                st.session_state.lista = []
                for linea in res.text.split('\n'):
                    if '|' in linea:
                        p = linea.split('|')
                        if len(p) >= 3:
                            try:
                                d = p[0].strip()
                                c = float(p[1].strip().replace(',','.'))
                                pr = float(p[2].strip().replace('€','').replace(',','.'))
                                pvp = calcular_pvp(pr, c)
                                st.session_state.lista.append({
                                    "Descripción": d, "Cant": int(c),
                                    "PVP Ud (€)": round(pvp, 2), "Total (€)": round(pvp * c, 2)
                                })
                            except: continue
                st.success("✅ Hecho.")
        except Exception as e:
            st.error(f"Error crítico: {e}")

# 4. TABLA Y PDF
if st.session_state.lista:
    df = pd.DataFrame(st.session_state.lista)
    st.table(df)
    
    # Generador PDF (Alicantina Style)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_fill_color(204, 0, 0)
    pdf.rect(0, 0, 210, 35, 'F')
    pdf.set_font("Arial", 'B', 20)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(190, 15, "ALICANTINA DE VALLAS", ln=True, align='C')
    pdf.ln(20)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", 'B', 10)
    for _, row in df.iterrows():
        pdf.cell(100, 10, f" {row['Descripción'][:50]}", 1)
        pdf.cell(20, 10, str(row['Cant']), 1, 0, 'C')
        pdf.cell(35, 10, f"{row['PVP Ud (€)']} e", 1, 0, 'C')
        pdf.cell(35, 10, f"{row['Total (€)']} e", 1, 1, 'C')
    
    st.download_button("📥 DESCARGAR PDF", data=pdf.output(dest='S').encode('latin-1', 'ignore'), file_name="Presupuesto.pdf")
