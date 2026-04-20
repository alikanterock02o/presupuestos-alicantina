import streamlit as st
import pandas as pd
import requests
import base64
from fpdf import FPDF
import PyPDF2

st.set_page_config(page_title="Alicantina de Vallas", layout="wide")

# Lógica de precios
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

# Función para crear el PDF
def generar_pdf(df, cliente):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "PRESUPUESTO: ALICANTINA DE VALLAS", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", '', 12)
    pdf.cell(200, 10, f"Cliente: {cliente}", ln=True)
    pdf.ln(5)
    
    # Cabecera tabla
    pdf.set_fill_color(200, 220, 255)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(100, 10, "Descripcion", 1, 0, 'C', True)
    pdf.cell(20, 10, "Cant.", 1, 0, 'C', True)
    pdf.cell(30, 10, "PVP Ud.", 1, 0, 'C', True)
    pdf.cell(30, 10, "Total", 1, 1, 'C', True)
    
    # Filas
    pdf.set_font("Arial", '', 9)
    for index, row in df.iterrows():
        pdf.cell(100, 10, str(row['Descripción'])[:50], 1)
        pdf.cell(20, 10, str(row['Cant']), 1, 0, 'C')
        pdf.cell(30, 10, f"{row['PVP Ud (€)']} e", 1, 0, 'C')
        pdf.cell(30, 10, f"{row['Total (€)']} e", 1, 1, 'C')
    
    pdf.ln(10)
    total = df["Total (€)"].sum()
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, f"TOTAL Base Imponible: {total:.2f} euros", ln=True, align='R')
    pdf.cell(200, 10, f"TOTAL con IVA (21%): {total * 1.21:.2f} euros", ln=True, align='R')
    
    return pdf.output(dest='S').encode('latin-1')

st.title("🏗️ Generador Alicantina de Vallas")
api_key = st.secrets["GEMINI_API_KEY"]
cliente = st.text_input("👤 Nombre del Cliente", value="General")

if 'lista' not in st.session_state:
    st.session_state.lista = []

archivo = st.file_uploader("📄 Sube el albarán (Foto o PDF)", type=['jpg', 'jpeg', 'png', 'pdf'])

if archivo and st.button("🔍 Analizar y Calcular"):
    try:
        with st.spinner("Leyendo albarán..."):
            if archivo.type == "application/pdf":
                reader = PyPDF2.PdfReader(archivo)
                texto_pdf = "".join([page.extract_text() for page in reader.pages])
                payload = {"contents": [{"parts": [{"text": f"Extrae: PRODUCTO | CANTIDAD | PRECIO_COSTE. Texto: {texto_pdf}"}]}]}
            else:
                img_b64 = base64.b64encode(archivo.read()).decode('utf-8')
                payload = {"contents": [{"parts": [
                    {"text": "Extrae: PRODUCTO | CANTIDAD | PRECIO_COSTE. Solo texto limpio."},
                    {"inline_data": {"mime_type": archivo.type, "data": img_b64}}
                ]}]}

            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            response = requests.post(url, json=payload)
            res_json = response.json()

            if 'candidates' in res_json:
                texto_ia = res_json['candidates'][0]['content']['parts'][0]['text']
                for linea in texto_ia.split('\n'):
                    if '|' in linea:
                        p = linea.split('|')
                        try:
                            desc = p[0].strip()
                            cant = float(p[1].strip().replace(',', '.'))
                            coste = float(p[2].strip().replace('€', '').replace(',', '.').strip())
                            pvp_ud = calcular_pvp(coste)
                            st.session_state.lista.append({
                                "Descripción": desc, "Cant": int(cant),
                                "PVP Ud (€)": round(pvp_ud, 2), "Total (€)": round(pvp_ud * cant, 2)
                            })
                        except: continue
                st.success("✅ Albarán procesado")
            else:
                st.error("Error al conectar con Google. Reintenta en 5 segundos.")
    except Exception as e:
        st.error(f"Error: {e}")

if st.session_state.lista:
    df = pd.DataFrame(st.session_state.lista)
    st.table(df)
    
    # BOTÓN DE DESCARGA PDF
    pdf_output = generar_pdf(df, cliente)
    st.download_button(
        label="📥 Descargar Presupuesto en PDF",
        data=pdf_output,
        file_name=f"Presupuesto_{cliente}.pdf",
        mime="application/pdf",
    )

    if st.button("🗑️ Limpiar"):
        st.session_state.lista = []
        st.rerun()
