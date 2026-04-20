import streamlit as st
import pandas as pd
import google.generativeai as genai
from fpdf import FPDF
import PyPDF2
import io

# 1. Configuración de Marca (Rojo y Negro Industrial)
st.set_page_config(page_title="Alicantina de Vallas | Sistema Pro", layout="wide")

# Configuración robusta de la IA
if "GEMINI_API_KEY" not in st.secrets:
    st.error("⚠️ No se encuentra la clave GEMINI_API_KEY en los Secrets de Streamlit.")
else:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # Usamos el modelo estable sin prefijos extraños
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"Error al inicializar Google AI: {e}")

# Lógica de márgenes para presupuestos
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

# Generador de PDF con estética corporativa
def generar_pdf(df, cliente):
    pdf = FPDF()
    pdf.add_page()
    # Cabecera Roja Alicantina
    pdf.set_fill_color(204, 0, 0) 
    pdf.rect(0, 0, 210, 35, 'F')
    pdf.set_font("Arial", 'B', 20)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(190, 15, "ALICANTINA DE VALLAS", ln=True, align='C')
    pdf.ln(20)
    # Tabla en Negro Industrial
    pdf.set_text_color(0, 0, 0)
    pdf.set_fill_color(30, 30, 30) 
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(100, 10, " PRODUCTO", 1, 0, 'L', True)
    pdf.cell(20, 10, "CANT.", 1, 0, 'C', True)
    pdf.cell(35, 10, "PVP UD.", 1, 0, 'C', True)
    pdf.cell(35, 10, "TOTAL", 1, 1, 'C', True)
    # Filas de datos
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 9)
    for _, row in df.iterrows():
        pdf.cell(100, 9, f" {str(row['Descripción'])[:50]}", 1)
        pdf.cell(20, 9, str(row['Cant']), 1, 0, 'C')
        pdf.cell(35, 9, f"{row['PVP Ud (€)']} e", 1, 0, 'C')
        pdf.cell(35, 9, f"{row['Total (€)']} e", 1, 1, 'C')
    # Total en Rojo
    total_base = df["Total (€)"].sum()
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(204, 0, 0)
    pdf.cell(190, 10, f"TOTAL IVA INCLUIDO (21%): {total_base * 1.21:.2f} e", 0, 1, 'R')
    return pdf.output(dest='S').encode('latin-1', 'ignore')

# 3. Interfaz de Usuario
st.title("🏗️ Alicantina de Vallas - Generador de Presupuestos")

if st.button("♻️ Reiniciar Sistema"):
    st.session_state.lista = []
    st.rerun()

nombre_c = st.text_input("👤 Cliente", value="David")

if 'lista' not in st.session_state:
    st.session_state.lista = []

archivo = st.file_uploader("📄 Subir Albarán o Foto", type=['jpg', 'jpeg', 'png', 'pdf'])

if archivo and st.button("🔍 ANALIZAR AHORA"):
    try:
        with st.spinner("Analizando con Google AI..."):
            prompt = "Extract items. Format: DESCRIPTION | QUANTITY | UNIT_COST. Use '|' separator."
            
            if archivo.type == "application/pdf":
                reader = PyPDF2.PdfReader(archivo)
                txt = "".join([p.extract_text() for p in reader.pages])
                response = model.generate_content(f"{prompt}\n\nDocument Text:\n{txt}")
            else:
                bytes_data = archivo.getvalue()
                response = model.generate_content([prompt, {"mime_type": archivo.type, "data": bytes_data}])

            if response and response.text:
                st.session_state.lista = []
                for line in response.text.split('\n'):
                    if '|' in line:
                        parts = line.split('|')
                        if len(parts) >= 3:
                            try:
                                d = parts[0].strip()
                                c = float(parts[1].strip().replace(',','.'))
                                pr = float(parts[2].strip().replace('€','').replace(',','.'))
                                pvp_calc = calcular_pvp(pr, c)
                                st.session_state.lista.append({
                                    "Descripción": d, "Cant": int(c),
                                    "PVP Ud (€)": round(pvp_calc, 2), 
                                    "Total (€)": round(pvp_calc * c, 2)
                                })
                            except: continue
                if not st.session_state.lista:
                    st.warning("No se encontraron productos con el formato esperado.")
                else:
                    st.success("✅ Documento procesado.")
    except Exception as e:
        # Aquí capturamos el error real para saber qué pasa
        st.error(f"❌ Error de diagnóstico: {str(e)}")
        if "quota" in str(e).lower():
            st.info("💡 Pareces haber agotado el límite de hoy. Prueba de nuevo en unos minutos.")

# Mostrar Resultados
if st.session_state.lista:
    df_res = pd.DataFrame(st.session_state.lista)
    st.table(df_res)
    pdf_bytes = generar_pdf(df_res, nombre_c)
    st.download_button("📥 DESCARGAR PRESUPUESTO PDF", data=pdf_bytes, file_name=f"Presupuesto_{nombre_c}.pdf")
