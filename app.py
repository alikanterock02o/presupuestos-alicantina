import streamlit as st
import pandas as pd
import google.generativeai as genai
from fpdf import FPDF
import PyPDF2

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Alicantina de Vallas - Gestor", layout="wide")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("⚠️ Configura la API KEY en Secrets.")

# Lógica comercial
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

# 2. MOTOR DE ANÁLISIS (Súper simple para evitar TypeError)
def analizar_documento(archivo):
    # Usamos el modelo directamente, que ya vimos que lo encuentra
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = "Extrae los datos en este formato: PRODUCTO | CANTIDAD | PRECIO_COSTE. Solo texto plano."
    
    try:
        if archivo.type == "application/pdf":
            reader = PyPDF2.PdfReader(archivo)
            texto = "".join([p.extract_text() for p in reader.pages])
            response = model.generate_content(f"{prompt}\n\nDocumento:\n{texto}")
        else:
            img_data = archivo.read()
            # Formato estándar de imagen
            response = model.generate_content([prompt, {"mime_type": archivo.type, "data": img_data}])
        return response.text
    except Exception as e:
        return f"ERROR: {str(e)}"

# 3. INTERFAZ
st.title("🏗️ Alicantina de Vallas - Gestor")

if st.button("♻️ REINICIAR"):
    st.session_state.clear()
    st.rerun()

nombre_cliente = st.text_input("👤 Cliente", value="David")

if 'datos' not in st.session_state:
    st.session_state.datos = []

archivo = st.file_uploader("📄 Sube foto o PDF", type=['jpg', 'jpeg', 'png', 'pdf'])

if archivo and st.button("🚀 ANALIZAR"):
    with st.spinner("Leyendo albarán..."):
        resultado = analizar_documento(archivo)
        
        if "ERROR" in resultado:
            st.error(resultado)
        else:
            temp_lista = []
            for l in resultado.split('\n'):
                if '|' in l:
                    try:
                        partes = l.split('|')
                        desc = partes[0].strip()
                        cant = float(partes[1].strip().replace(',','.'))
                        coste = float(partes[2].strip().replace('€','').replace(',','.'))
                        
                        pvp_unidad = calcular_pvp(coste, cant)
                        temp_lista.append({
                            "Descripción": desc,
                            "Cant": int(cant),
                            "PVP Ud (€)": round(pvp_unidad, 2),
                            "Total (€)": round(pvp_unidad * cant, 2)
                        })
                    except: continue
            st.session_state.datos = temp_lista

# 4. RESULTADOS
if st.session_state.datos:
    df = pd.DataFrame(st.session_state.datos)
    st.table(df)
    
    # PDF Minimalista
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, f"PRESUPUESTO: {nombre_cliente}", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", '', 10)
    for _, fila in df.iterrows():
        pdf.cell(190, 8, f"{fila['Cant']}x {fila['Descripción'][:50]}... | {fila['Total (€)']} e", ln=True)
    
    st.download_button("📥 DESCARGAR PDF", data=pdf.output(dest='S').encode('latin-1', 'ignore'), file_name="Presupuesto.pdf")
