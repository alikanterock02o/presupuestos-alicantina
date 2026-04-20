import streamlit as st
import pandas as pd
import google.generativeai as genai
from fpdf import FPDF
import PyPDF2
import io

# 1. ESTILO CORPORATIVO ALICANTINA DE VALLAS
st.set_page_config(page_title="Alicantina de Vallas | Gestión", layout="wide")

# Configuración de IA con ruta de transporte forzada
if "GEMINI_API_KEY" in st.secrets:
    try:
        # Usamos transport='rest' para evitar los errores 404 de v1beta/v1
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"], transport='rest')
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"Error de inicialización: {e}")
else:
    st.error("⚠️ Falta GEMINI_API_KEY en los Secrets de Streamlit.")

# Lógica de márgenes comercial
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

# 2. GENERADOR DE PDF PROFESIONAL
def generar_pdf(df, cliente):
    pdf = FPDF()
    pdf.add_page()
    # Encabezado Rojo Alicantina
    pdf.set_fill_color(204, 0, 0) 
    pdf.rect(0, 0, 210, 35, 'F')
    pdf.set_font("Arial", 'B', 22)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(190, 15, "ALICANTINA DE VALLAS", ln=True, align='C')
    pdf.ln(20)
    # Tabla Industrial
    pdf.set_fill_color(30, 30, 30)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(100, 10, " PRODUCTO", 1, 0, 'L', True)
    pdf.cell(20, 10, "CANT.", 1, 0, 'C', True)
    pdf.cell(35, 10, "PVP UD.", 1, 0, 'C', True)
    pdf.cell(35, 10, "TOTAL", 1, 1, 'C', True)
    # Datos
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 9)
    for _, row in df.iterrows():
        pdf.cell(100, 9, f" {str(row['Descripción'])[:55]}", 1)
        pdf.cell(20, 9, str(row['Cant']), 1, 0, 'C')
        pdf.cell(35, 9, f"{row['PVP Ud (€)']} e", 1, 0, 'C')
        pdf.cell(35, 9, f"{row['Total (€)']} e", 1, 1, 'C')
    # Total
    t_f = df["Total (€)"].sum()
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(204, 0, 0)
    pdf.cell(190, 10, f"TOTAL IVA INCLUIDO: {t_f * 1.21:.2f} e", 0, 1, 'R')
    return pdf.output(dest='S').encode('latin-1', 'ignore')

# 3. INTERFAZ
st.title("🏗️ Alicantina de Vallas - Gestor de Albaranes")

if st.button("♻️ LIMPIAR TODO Y REINICIAR"):
    st.session_state.lista = []
    st.rerun()

nombre_c = st.text_input("👤 Cliente", value="David")

if 'lista' not in st.session_state:
    st.session_state.lista = []

archivo = st.file_uploader("📄 Sube tu documento", type=['jpg', 'jpeg', 'png', 'pdf'])

if archivo and st.button("🔍 PROCESAR AHORA"):
    try:
        with st.spinner("Analizando con Google AI (Ruta REST)..."):
            prompt = "Extract items. Format: ITEM | QTY | UNIT_PRICE. NO markdown, NO text."
            
            if archivo.type == "application/pdf":
                reader = PyPDF2.PdfReader(archivo)
                texto = "".join([p.extract_text() for p in reader.pages])
                response = model.generate_content(f"{prompt}\n\nData:\n{texto}")
            else:
                img_bytes = archivo.read()
                response = model.generate_content([prompt, {"mime_type": archivo.type, "data": img_bytes}])

            if response.text:
                st.session_state.lista = []
                for linea in response.text.split('\n'):
                    if '|' in linea:
                        pts = linea.split('|')
                        if len(pts) >= 3:
                            try:
                                d = pts[0].strip()
                                c = float(pts[1].strip().replace(',','.'))
                                p_in = float(pts[2].strip().replace('€','').replace(',','.'))
                                pvp = calcular_pvp(p_in, c)
                                st.session_state.lista.append({
                                    "Descripción": d, "Cant": int(c),
                                    "PVP Ud (€)": round(pvp, 2), "Total (€)": round(pvp * c, 2)
                                })
                            except: continue
                st.success("✅ Documento procesado correctamente.")
    except Exception as e:
        st.error(f"Error técnico detectado: {str(e)}")
        st.info("💡 Si el error persiste, comprueba que 'google-generativeai' esté actualizado en tu requirements.txt")

if st.session_state.lista:
    df = pd.DataFrame(st.session_state.lista)
    st.table(df)
    pdf_out = generar_pdf(df, nombre_c)
    st.download_button("📥 DESCARGAR PDF", data=pdf_out, file_name=f"Presupuesto_{nombre_c}.pdf")
