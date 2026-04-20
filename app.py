import streamlit as st
import pandas as pd
import google.generativeai as genai
from fpdf import FPDF
import PyPDF2
import io

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="Alicantina de Vallas", layout="wide")

# Configurar la IA con la librería oficial
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"Error al configurar la API: {e}")

# Lógica de márgenes (Tu fórmula secreta)
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

# 2. GENERADOR DE PDF (Estética Industrial)
def generar_pdf(df, cliente):
    pdf = FPDF()
    pdf.add_page()
    # Cabecera Corporativa
    pdf.set_fill_color(204, 0, 0) # Rojo Alicantina
    pdf.rect(0, 0, 210, 35, 'F')
    pdf.set_font("Arial", 'B', 20)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(190, 15, "ALICANTINA DE VALLAS", ln=True, align='C')
    pdf.ln(20)
    # Tabla
    pdf.set_text_color(0, 0, 0)
    pdf.set_fill_color(30, 30, 30) # Negro
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
        pdf.cell(100, 9, f" {str(row['Descripción'])[:50]}", 1)
        pdf.cell(20, 9, str(row['Cant']), 1, 0, 'C')
        pdf.cell(35, 9, f"{row['PVP Ud (€)']} e", 1, 0, 'C')
        pdf.cell(35, 9, f"{row['Total (€)']} e", 1, 1, 'C')
    
    total_base = df["Total (€)"].sum()
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(204, 0, 0)
    pdf.cell(190, 10, f"TOTAL IVA INCLUIDO (21%): {total_base * 1.21:.2f} e", 0, 1, 'R')
    return pdf.output(dest='S').encode('latin-1', 'ignore')

# 3. INTERFAZ DE USUARIO
st.title("🏗️ Alicantina de Vallas - Generador")

if st.button("♻️ Reiniciar y Limpiar Pantalla"):
    st.session_state.lista = []
    st.rerun()

nombre_cliente = st.text_input("👤 Nombre del Cliente", value="David")

if 'lista' not in st.session_state:
    st.session_state.lista = []

archivo = st.file_uploader("📄 Subir Albarán", type=['jpg', 'jpeg', 'png', 'pdf'])

if archivo and st.button("🔍 ANALIZAR DOCUMENTO"):
    try:
        with st.spinner("La IA está trabajando..."):
            prompt = "Extrae los productos. Formato: PRODUCTO | CANTIDAD | PRECIO_UNITARIO. Ignora el resto."
            
            if archivo.type == "application/pdf":
                reader = PyPDF2.PdfReader(archivo)
                texto_pdf = "".join([p.extract_text() for p in reader.pages])
                response = model.generate_content(f"{prompt}\n\nTexto:\n{texto_pdf}")
            else:
                img_bytes = archivo.read()
                response = model.generate_content([prompt, {"mime_type": archivo.type, "data": img_bytes}])

            if response.text:
                st.session_state.lista = []
                for linea in response.text.split('\n'):
                    if '|' in linea:
                        partes = linea.split('|')
                        if len(partes) >= 3:
                            try:
                                d = partes[0].strip()
                                c = float(partes[1].strip().replace(',','.'))
                                pr = float(partes[2].strip().replace('€','').replace(',','.'))
                                pvp = calcular_pvp(pr, c)
                                st.session_state.lista.append({
                                    "Descripción": d, "Cant": int(c),
                                    "PVP Ud (€)": round(pvp, 2), "Total (€)": round(pvp * c, 2)
                                })
                            except: continue
                st.success("✅ Procesado con éxito")
            else:
                st.warning("No se detectaron productos. Revisa la imagen.")
    except Exception as e:
        st.error(f"Error de Google: {e}. Inténtalo de nuevo en un momento.")

if st.session_state.lista:
    df_f = pd.DataFrame(st.session_state.lista)
    st.table(df_f)
    pdf_out = generar_pdf(df_f, nombre_cliente)
    st.download_button("📥 DESCARGAR PDF", data=pdf_out, file_name=f"{nombre_cliente}.pdf", mime="application/pdf")
