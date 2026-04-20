import streamlit as st
import pandas as pd
import requests
import base64
from fpdf import FPDF
import PyPDF2
import io

st.set_page_config(page_title="Alicantina de Vallas", layout="wide")

# Lógica de márgenes
def calcular_pvp(coste_unitario, cantidad):
    total = coste_unitario * cantidad
    if total <= 0.05: m = 3.0
    elif total <= 0.25: m = 2.5
    elif total <= 1.0: m = 2.0
    elif total <= 3.0: m = 1.75
    elif total <= 10.0: m = 1.50
    elif total <= 50.0: m = 1.43
    elif total <= 300.0: m = 1.35
    elif total <= 1000.0: m = 1.29
    else: m = 1.25
    return coste_unitario * m

def generar_pdf(df, cliente):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_fill_color(204, 0, 0) 
    pdf.rect(0, 0, 210, 35, 'F')
    pdf.set_font("Arial", 'B', 20)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(190, 15, "ALICANTINA DE VALLAS", ln=True, align='C')
    pdf.ln(20)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(100, 10, f"CLIENTE: {cliente.upper()}", ln=True)
    pdf.set_fill_color(30, 30, 30) 
    pdf.set_text_color(255, 255, 255)
    pdf.cell(100, 10, " PRODUCTO", 1, 0, 'L', True)
    pdf.cell(20, 10, "CANT.", 1, 0, 'C', True)
    pdf.cell(35, 10, "PVP UD.", 1, 0, 'C', True)
    pdf.cell(35, 10, "TOTAL", 1, 1, 'C', True)
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
    pdf.cell(190, 10, f"TOTAL IVA INCLUIDO: {total_base * 1.21:.2f} e", 0, 1, 'R')
    return pdf.output(dest='S').encode('latin-1', 'ignore')

st.title("🏗️ Alicantina de Vallas - Generador")

# Botón para limpiar errores bloqueados
if st.button("♻️ Reiniciar Sistema (Limpiar Errores)"):
    st.session_state.lista = []
    st.rerun()

api_key = st.secrets["GEMINI_API_KEY"]
nombre_cliente = st.text_input("👤 Nombre Cliente", value="David")

if 'lista' not in st.session_state:
    st.session_state.lista = []

archivo = st.file_uploader("📄 Subir Albarán", type=['jpg', 'jpeg', 'png', 'pdf'])

if archivo and st.button("🔍 ANALIZAR AHORA"):
    try:
        with st.spinner("Conectando con Google..."):
            parts = [{"text": "Extrae: PRODUCTO | CANTIDAD | PRECIO_UNITARIO. Solo texto plano, sin negritas ni tablas."}]
            
            if archivo.type == "application/pdf":
                reader = PyPDF2.PdfReader(archivo)
                txt = "".join([p.extract_text() for p in reader.pages])
                parts.append({"text": txt})
            else:
                img_b64 = base64.b64encode(archivo.read()).decode('utf-8')
                parts.append({"inline_data": {"mime_type": archivo.type, "data": img_b64}})

            # USAMOS LA VERSIÓN MÁS ESTABLE
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}"
            res = requests.post(url, json={"contents": [{"parts": parts}]})
            data = res.json()

            if 'candidates' in data:
                texto = data['candidates'][0]['content']['parts'][0]['text']
                st.session_state.lista = []
                for line in texto.split('\n'):
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
                st.success("✅ Procesado")
            else:
                st.error(f"Error de Google: {data.get('error', {}).get('message', 'Desconocido')}")
    except Exception as e:
        st.error(f"Error de conexión: {e}")

if st.session_state.lista:
    df = pd.DataFrame(st.session_state.lista)
    st.table(df)
    pdf_b = generar_pdf(df, nombre_cliente)
    st.download_button("📥 DESCARGAR PDF", data=pdf_b, file_name=f"{nombre_cliente}.pdf", mime="application/pdf")
