import streamlit as st
import pandas as pd
import requests
import base64
from fpdf import FPDF
import PyPDF2

# Configuración de página
st.set_page_config(page_title="Alicantina de Vallas", layout="wide")

# 1. LÓGICA DE PRECIOS
def calcular_pvp(coste_unitario, cantidad):
    total_linea = coste_unitario * cantidad
    if total_linea <= 0.05: margen = 3.0
    elif total_linea <= 0.25: margen = 2.5
    elif total_linea <= 1.0: margen = 2.0
    elif total_linea <= 3.0: margen = 1.75
    elif total_linea <= 10.0: margen = 1.50
    elif total_linea <= 50.0: margen = 1.43
    elif total_linea <= 300.0: margen = 1.35
    elif total_linea <= 1000.0: margen = 1.29
    else: margen = 1.25
    return coste_unitario * margen

# 2. GENERADOR DE PDF PREMIUM
def generar_pdf(df, cliente):
    pdf = FPDF()
    pdf.add_page()
    # Cabecera Roja (Inspirada en tu fachada)
    pdf.set_fill_color(204, 0, 0) 
    pdf.rect(0, 0, 210, 35, 'F')
    pdf.set_font("Arial", 'B', 20)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(190, 15, "ALICANTINA DE VALLAS", ln=True, align='C')
    pdf.ln(20)
    # Datos Cliente
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(100, 10, f"PRESUPUESTO: {cliente.upper()}", ln=True)
    pdf.ln(5)
    # Tabla Negra
    pdf.set_fill_color(30, 30, 30) 
    pdf.set_text_color(255, 255, 255)
    pdf.cell(100, 10, " PRODUCTO", 1, 0, 'L', True)
    pdf.cell(20, 10, "CANT.", 1, 0, 'C', True)
    pdf.cell(35, 10, "PVP UD.", 1, 0, 'C', True)
    pdf.cell(35, 10, "TOTAL", 1, 1, 'C', True)
    # Filas
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 9)
    for _, row in df.iterrows():
        pdf.cell(100, 9, f" {str(row['Descripción'])[:50]}", 1)
        pdf.cell(20, 9, str(row['Cant']), 1, 0, 'C')
        pdf.cell(35, 9, f"{row['PVP Ud (€)']} e", 1, 0, 'C')
        pdf.cell(35, 9, f"{row['Total (€)']} e", 1, 1, 'C')
    # Total
    total_base = df["Total (€)"].sum()
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(204, 0, 0)
    pdf.cell(190, 10, f"TOTAL IVA INCLUIDO (21%): {total_base * 1.21:.2f} e", 0, 1, 'R')
    return pdf.output(dest='S').encode('latin-1', 'ignore')

# 3. INTERFAZ
st.title("🏗️ Generador Alicantina de Vallas")

if st.button("♻️ Limpiar Errores / Reiniciar"):
    st.session_state.lista = []
    st.rerun()

api_key = st.secrets["GEMINI_API_KEY"]
nombre_cliente = st.text_input("👤 Nombre del Cliente", value="David")

if 'lista' not in st.session_state:
    st.session_state.lista = []

archivo = st.file_uploader("📄 Sube el albarán (Foto o PDF)", type=['jpg', 'jpeg', 'png', 'pdf'])

if archivo and st.button("🔍 ANALIZAR AHORA"):
    try:
        with st.spinner("Leyendo documento..."):
            prompt = "Extrae los productos de este documento. Formato exacto: PRODUCTO | CANTIDAD | PRECIO_UNITARIO"
            
            if archivo.type == "application/pdf":
                reader = PyPDF2.PdfReader(archivo)
                texto_extraido = "".join([p.extract_text() for p in reader.pages])
                payload = {"contents": [{"parts": [{"text": f"{prompt}\n\nDocumento:\n{texto_extraido}"}]}]}
            else:
                img_64 = base64.b64encode(archivo.read()).decode('utf-8')
                payload = {"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": archivo.type, "data": img_64}}]}]}

            # URL ESTABLE (v1)
            url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
            res = requests.post(url, json=payload)
            data = res.json()

            if 'candidates' in data:
                texto_ia = data['candidates'][0]['content']['parts'][0]['text']
                st.session_state.lista = []
                for line in texto_ia.split('\n'):
                    if '|' in line:
                        p = line.split('|')
                        if len(p) >= 3:
                            try:
                                d = p[0].strip()
                                c = float(p[1].strip().replace(',','.'))
                                pr = float(p[2].strip().replace('€','').replace(',','.'))
                                pvp = calcular_pvp(pr, c)
                                st.session_state.lista.append({"Descripción": d, "Cant": int(c), "PVP Ud (€)": round(pvp,2), "Total (€)": round(pvp*c,2)})
                            except: continue
                st.success("✅ Documento procesado")
            else:
                st.error(f"Error de Google: {data.get('error', {}).get('message', 'Problema de conexión')}")
    except Exception as e:
        st.error(f"Error inesperado: {e}")

if st.session_state.lista:
    df = pd.DataFrame(st.session_state.lista)
    st.table(df)
    pdf_b = generar_pdf(df, nombre_cliente)
    st.download_button("📥 DESCARGAR PRESUPUESTO PDF", data=pdf_b, file_name=f"Presupuesto_{nombre_cliente}.pdf", mime="application/pdf")
