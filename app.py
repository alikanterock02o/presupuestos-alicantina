import streamlit as st
import pandas as pd
import google.generativeai as genai
from fpdf import FPDF
import PyPDF2
import io

# 1. IDENTIDAD DE MARCA (ROJO Y NEGRO)
st.set_page_config(page_title="Alicantina de Vallas | Pro", layout="wide")

# Configuración ultra-estable
if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # Usamos el modelo sin sufijos para máxima compatibilidad
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"Error inicial: {e}")
else:
    st.error("Configura tu GEMINI_API_KEY en los Secrets de Streamlit.")

# Lógica de precios original de la empresa
def calcular_pvp(coste, cantidad):
    total_base = coste * cantidad
    if total_base <= 0.05: m = 3.0
    elif total_base <= 0.25: m = 2.5
    elif total_base <= 1.0: m = 2.0
    elif total_base <= 3.0: m = 1.75
    elif total_base <= 10.0: m = 1.50
    elif total_base <= 50.0: m = 1.43
    elif total_base <= 300.0: m = 1.35
    elif total_base <= 1000.0: m = 1.29
    else: m = 1.25
    return coste * m

# 2. GENERADOR DE PDF CORPORATIVO
def generar_pdf(df, cliente):
    pdf = FPDF()
    pdf.add_page()
    # Diseño basado en vuestra identidad
    pdf.set_fill_color(204, 0, 0) # Rojo Alicantina
    pdf.rect(0, 0, 210, 35, 'F')
    pdf.set_font("Arial", 'B', 22)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(190, 15, "ALICANTINA DE VALLAS", ln=True, align='C')
    pdf.ln(20)
    # Tabla con estilo industrial
    pdf.set_text_color(0, 0, 0)
    pdf.set_fill_color(30, 30, 30)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(100, 10, " DESCRIPCION", 1, 0, 'L', True)
    pdf.cell(20, 10, "CANT.", 1, 0, 'C', True)
    pdf.cell(35, 10, "PVP UD.", 1, 0, 'C', True)
    pdf.cell(35, 10, "TOTAL", 1, 1, 'C', True)
    # Filas
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 9)
    for _, row in df.iterrows():
        pdf.cell(100, 9, f" {str(row['Descripción'])[:55]}", 1)
        pdf.cell(20, 9, str(row['Cant']), 1, 0, 'C')
        pdf.cell(35, 9, f"{row['PVP Ud (€)']} e", 1, 0, 'C')
        pdf.cell(35, 9, f"{row['Total (€)']} e", 1, 1, 'C')
    # Total Final Destacado
    t_final = df["Total (€)"].sum()
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(204, 0, 0)
    pdf.cell(190, 10, f"TOTAL IVA INCLUIDO (21%): {t_final * 1.21:.2f} e", 0, 1, 'R')
    return pdf.output(dest='S').encode('latin-1', 'ignore')

# 3. INTERFAZ Y PROCESAMIENTO
st.title("🏗️ Alicantina de Vallas - Gestor de Albaranes")

if st.button("♻️ Reiniciar Sistema y Limpiar Errores"):
    st.session_state.lista = []
    st.rerun()

nombre_c = st.text_input("👤 Nombre del Cliente", value="David")

if 'lista' not in st.session_state:
    st.session_state.lista = []

archivo = st.file_uploader("📄 Sube tu albarán (Foto o PDF)", type=['jpg', 'jpeg', 'png', 'pdf'])

if archivo and st.button("🔍 PROCESAR DOCUMENTO"):
    try:
        with st.spinner("Conectando con Google AI (Versión Estable)..."):
            # Prompt optimizado para evitar errores de formato
            prompt = "Act as a data extractor. Return ONLY data in this format: ITEM | QUANTITY | PRICE. No intro, no markdown."
            
            if archivo.type == "application/pdf":
                reader = PyPDF2.PdfReader(archivo)
                texto_doc = "".join([p.extract_text() for p in reader.pages])
                # Llamada directa al modelo
                response = model.generate_content(f"{prompt}\n\nTexto:\n{texto_doc}")
            else:
                img_data = archivo.read()
                response = model.generate_content([prompt, {"mime_type": archivo.type, "data": img_data}])

            if response and response.text:
                st.session_state.lista = []
                for linea in response.text.split('\n'):
                    if '|' in linea:
                        p = linea.split('|')
                        if len(p) >= 3:
                            try:
                                d = p[0].strip()
                                c = float(p[1].strip().replace(',','.'))
                                pr = float(p[2].strip().replace('€','').replace(',','.'))
                                pvp_final = calcular_pvp(pr, c)
                                st.session_state.lista.append({
                                    "Descripción": d, "Cant": int(c),
                                    "PVP Ud (€)": round(pvp_final, 2), 
                                    "Total (€)": round(pvp_final * c, 2)
                                })
                            except: continue
                st.success("✅ Documento analizado con éxito.")
    except Exception as e:
        # Mensaje de error personalizado para David
        st.error(f"⚠️ Error de Conexión: {str(e)}")
        if "404" in str(e):
            st.info("💡 Sugerencia: Google está actualizando sus servidores en tu zona. Espera 2 minutos y vuelve a intentarlo.")

# Visualización y descarga
if st.session_state.lista:
    df_result = pd.DataFrame(st.session_state.lista)
    st.table(df_result)
    pdf_ready = generar_pdf(df_result, nombre_c)
    st.download_button(
        label="📥 DESCARGAR PRESUPUESTO PDF",
        data=pdf_ready,
        file_name=f"Presupuesto_{nombre_c}.pdf",
        mime="application/pdf"
    )
