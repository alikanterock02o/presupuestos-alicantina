import streamlit as st
import pandas as pd
import google.generativeai as genai
from fpdf import FPDF
import PyPDF2
import io

# 1. IDENTIDAD CORPORATIVA
st.set_page_config(page_title="Alicantina de Vallas | Presupuestos", layout="wide")

# Configuración de la IA usando la ruta estable (v1)
if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # Forzamos el uso del modelo de producción estable
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"Error de inicialización: {e}")
else:
    st.error("Falta la clave GEMINI_API_KEY en Secrets.")

# Lógica de márgenes de Alicantina de Vallas
def calcular_pvp(coste, cantidad):
    total_linea = coste * cantidad
    if total_linea <= 0.05: m = 3.0
    elif total_linea <= 0.25: m = 2.5
    elif total_linea <= 1.0: m = 2.0
    elif total_linea <= 3.0: m = 1.75
    elif total_linea <= 10.0: m = 1.50
    elif total_linea <= 50.0: m = 1.43
    elif total_linea <= 300.0: m = 1.35
    elif total_linea <= 1000.0: m = 1.29
    else: m = 1.25
    return coste * m

# 2. GENERADOR DE PDF PROFESIONAL
def generar_pdf(df, cliente):
    pdf = FPDF()
    pdf.add_page()
    # Cabecera Roja Corporativa
    pdf.set_fill_color(204, 0, 0) 
    pdf.rect(0, 0, 210, 35, 'F')
    pdf.set_font("Arial", 'B', 22)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(190, 15, "ALICANTINA DE VALLAS", ln=True, align='C')
    pdf.ln(20)
    # Tabla de Productos
    pdf.set_text_color(0, 0, 0)
    pdf.set_fill_color(40, 40, 40)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(100, 10, " PRODUCTO", 1, 0, 'L', True)
    pdf.cell(20, 10, "CANT.", 1, 0, 'C', True)
    pdf.cell(35, 10, "PVP UD.", 1, 0, 'C', True)
    pdf.cell(35, 10, "TOTAL", 1, 1, 'C', True)
    # Contenido
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 9)
    for _, row in df.iterrows():
        pdf.cell(100, 9, f" {str(row['Descripción'])[:55]}", 1)
        pdf.cell(20, 9, str(row['Cant']), 1, 0, 'C')
        pdf.cell(35, 9, f"{row['PVP Ud (€)']} e", 1, 0, 'C')
        pdf.cell(35, 9, f"{row['Total (€)']} e", 1, 1, 'C')
    # Total Final
    t_final = df["Total (€)"].sum()
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(204, 0, 0)
    pdf.cell(190, 10, f"TOTAL IVA INCLUIDO: {t_final * 1.21:.2f} e", 0, 1, 'R')
    return pdf.output(dest='S').encode('latin-1', 'ignore')

# 3. INTERFAZ DE USUARIO
st.title("🏗️ Alicantina de Vallas - Sistema de Presupuestos")

if st.button("♻️ Reiniciar y Limpiar Pantalla"):
    st.session_state.lista = []
    st.rerun()

nombre_c = st.text_input("👤 Nombre del Cliente", value="David")

if 'lista' not in st.session_state:
    st.session_state.lista = []

archivo = st.file_uploader("📄 Sube el Albarán (Foto o PDF)", type=['jpg', 'jpeg', 'png', 'pdf'])

if archivo and st.button("🔍 ANALIZAR AHORA"):
    try:
        with st.spinner("Procesando documento..."):
            instruccion = "Extract items: DESCRIPTION | QUANTITY | UNIT_PRICE. Just the text, no markdown."
            
            if archivo.type == "application/pdf":
                reader = PyPDF2.PdfReader(archivo)
                texto = "".join([p.extract_text() for p in reader.pages])
                res = model.generate_content(f"{instruccion}\n\nDocument:\n{texto}")
            else:
                img_data = archivo.read()
                res = model.generate_content([instruccion, {"mime_type": archivo.type, "data": img_data}])

            if res.text:
                st.session_state.lista = []
                for linea in res.text.split('\n'):
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
                st.success("✅ Análisis completado")
            else:
                st.warning("No se pudo extraer información. Prueba con una foto más clara.")
    except Exception as e:
        # Si da error, mostramos una guía clara
        st.error(f"Error de conexión con Google: {str(e)}")
        if "404" in str(e):
            st.info("💡 El modelo está en mantenimiento. Intenta de nuevo en unos minutos.")

if st.session_state.lista:
    df_ver = pd.DataFrame(st.session_state.lista)
    st.table(df_ver)
    pdf_final = generar_pdf(df_ver, nombre_c)
    st.download_button("📥 DESCARGAR PRESUPUESTO PDF", data=pdf_final, file_name=f"Alicantina_{nombre_c}.pdf")
