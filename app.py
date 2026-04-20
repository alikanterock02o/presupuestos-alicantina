import streamlit as st
import pandas as pd
import requests
import base64
from fpdf import FPDF
import PyPDF2
import io

st.set_page_config(page_title="Alicantina de Vallas", layout="wide")

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

def generar_pdf(df, cliente):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "ALICANTINA DE VALLAS - PRESUPUESTO", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", '', 12)
    pdf.cell(200, 10, f"Cliente: {cliente}", ln=True)
    pdf.ln(5)
    pdf.set_fill_color(200, 220, 255)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(100, 10, "Descripcion", 1, 0, 'C', True)
    pdf.cell(20, 10, "Cant.", 1, 0, 'C', True)
    pdf.cell(30, 10, "PVP Ud.", 1, 0, 'C', True)
    pdf.cell(30, 10, "Total", 1, 1, 'C', True)
    pdf.set_font("Arial", '', 9)
    for index, row in df.iterrows():
        pdf.cell(100, 10, str(row['Descripción'])[:55], 1)
        pdf.cell(20, 10, str(row['Cant']), 1, 0, 'C')
        pdf.cell(30, 10, f"{row['PVP Ud (€)']} e", 1, 0, 'C')
        pdf.cell(30, 10, f"{row['Total (€)']} e", 1, 1, 'C')
    pdf.ln(10)
    total = df["Total (€)"].sum()
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, f"TOTAL Base Imponible: {total:.2f} euros", ln=True, align='R')
    pdf.cell(200, 10, f"TOTAL con IVA (21%): {total * 1.21:.2f} euros", ln=True, align='R')
    return pdf.output(dest='S').encode('latin-1', 'ignore')

st.title("🏗️ Generador Alicantina de Vallas")
api_key = st.secrets["GEMINI_API_KEY"]
cliente = st.text_input("👤 Nombre del Cliente", value="David")

if 'lista' not in st.session_state:
    st.session_state.lista = []

archivo = st.file_uploader("📄 Sube el albarán (Foto o PDF)", type=['jpg', 'jpeg', 'png', 'pdf'])

if archivo and st.button("🔍 Analizar y Calcular"):
    try:
        with st.spinner("Leyendo datos..."):
            if archivo.type == "application/pdf":
                reader = PyPDF2.PdfReader(archivo)
                texto_pdf = "".join([page.extract_text() for page in reader.pages])
                prompt = f"Extrae los productos. Formato estricto: NOMBRE | CANTIDAD | PRECIO_COSTE. Texto: {texto_pdf}"
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
            else:
                img_content = archivo.read()
                img_b64 = base64.b64encode(img_content).decode('utf-8')
                payload = {"contents": [{"parts": [
                    {"text": "Dime los artículos de esta imagen. Formato: NOMBRE | CANTIDAD | PRECIO_COSTE. No digas nada más, solo las líneas con ese formato."},
                    {"inline_data": {"mime_type": archivo.type, "data": img_b64}}
                ]}]}

            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            response = requests.post(url, json=payload)
            res_json = response.json()

            if 'candidates' in res_json:
                texto_ia = res_json['candidates'][0]['content']['parts'][0]['text']
                # Debug por si acaso
                # st.write(texto_ia) 
                
                lineas_detectadas = 0
                for linea in texto_ia.split('\n'):
                    if '|' in linea:
                        partes = linea.split('|')
                        if len(partes) >= 3:
                            try:
                                d = partes[0].strip()
                                c = float(partes[1].strip().replace(',', '.'))
                                p_coste = float(partes[2].strip().replace('€', '').replace(',', '.').strip())
                                pvp = calcular_pvp(p_coste)
                                st.session_state.lista.append({
                                    "Descripción": d, "Cant": int(c),
                                    "PVP Ud (€)": round(pvp, 2), "Total (€)": round(pvp * c, 2)
                                })
                                lineas_detectadas += 1
                            except: continue
                
                if lineas_detectadas > 0:
                    st.success(f"✅ Se han encontrado {lineas_detectadas} artículos.")
                else:
                    st.error("❌ La IA leyó el albarán pero no pudo extraer los datos. Prueba con una foto más clara.")
            else:
                st.error("Error de conexión. Intenta de nuevo.")
    except Exception as e:
        st.error(f"Error: {e}")

if st.session_state.lista:
    df = pd.DataFrame(st.session_state.lista)
    st.subheader(f"Presupuesto para {cliente}")
    st.table(df) # Esto fuerza a que se vea la tabla sí o sí
    
    pdf_bytes = generar_pdf(df, cliente)
    st.download_button(
        label="📥 Descargar PDF para WhatsApp",
        data=pdf_bytes,
        file_name=f"Presupuesto_{cliente}.pdf",
        mime="application/pdf"
    )

    if st.button("🗑️ Nueva consulta"):
        st.session_state.lista = []
        st.rerun()
