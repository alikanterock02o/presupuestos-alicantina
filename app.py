import streamlit as st
import pandas as pd
import requests
import base64
from fpdf import FPDF
import PyPDF2
import io

st.set_page_config(page_title="Alicantina de Vallas | Presupuestos", layout="wide")

# 1. LÓGICA DE MÁRGENES (POR VOLUMEN TOTAL DE LÍNEA)
def calcular_pvp(coste_unitario, cantidad):
    importe_total_linea = coste_unitario * cantidad
    if importe_total_linea <= 0.05: margen = 3.0
    elif importe_total_linea <= 0.25: margen = 2.5
    elif importe_total_linea <= 1.0: margen = 2.0
    elif importe_total_linea <= 3.0: margen = 1.75
    elif importe_total_linea <= 10.0: margen = 1.50
    elif importe_total_linea <= 50.0: margen = 1.43
    elif importe_total_linea <= 300.0: margen = 1.35
    elif importe_total_linea <= 1000.0: margen = 1.29
    else: margen = 1.25
    return coste_unitario * margen

# 2. FUNCIÓN DE PDF PREMIUM (CORREGIDA)
def generar_pdf_premium(df, cliente):
    pdf = FPDF()
    pdf.add_page()
    
    # Cabecera Roja
    pdf.set_fill_color(204, 0, 0) 
    pdf.rect(0, 0, 210, 35, 'F')
    pdf.set_font("Arial", 'B', 20)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(190, 15, "ALICANTINA DE VALLAS", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(190, 5, "CERRAMIENTOS INDUSTRIALES Y SEGURIDAD", ln=True, align='C')
    
    pdf.ln(20)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(100, 10, f"CLIENTE: {cliente.upper()}", ln=True)
    pdf.ln(5)
    
    # Cabecera Tabla Negra
    pdf.set_fill_color(30, 30, 30) 
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
        pdf.cell(100, 9, f" {str(row['Descripción'])[:50]}", 1)
        pdf.cell(20, 9, str(row['Cant']), 1, 0, 'C')
        pdf.cell(35, 9, f"{row['PVP Ud (€)']} e", 1, 0, 'C')
        pdf.cell(35, 9, f"{row['Total (€)']} e", 1, 1, 'C')
    
    pdf.ln(10)
    total_base = df["Total (€)"].sum()
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(204, 0, 0)
    pdf.cell(190, 10, f"TOTAL IVA INCLUIDO: {total_base * 1.21:.2f} euros", 0, 1, 'R')
    
    return pdf.output(dest='S').encode('latin-1', 'ignore')

# 3. INTERFAZ
st.title("🏗️ Alicantina de Vallas - Generador")
api_key = st.secrets["GEMINI_API_KEY"]
nombre_cliente = st.text_input("👤 Nombre del Cliente", value="David")

if 'lista' not in st.session_state:
    st.session_state.lista = []

archivo = st.file_uploader("📄 Sube el documento", type=['jpg', 'jpeg', 'png', 'pdf'])

if archivo and st.button("🔍 Analizar Presupuesto"):
    try:
        with st.spinner("Leyendo datos..."):
            if archivo.type == "application/pdf":
                reader = PyPDF2.PdfReader(archivo)
                texto_pdf = "".join([page.extract_text() for page in reader.pages])
                prompt = f"Dame solo esto: PRODUCTO | CANTIDAD | PRECIO. Texto: {texto_pdf}"
            else:
                img_data = base64.b64encode(archivo.read()).decode('utf-8')
                prompt = "Extrae los artículos de esta imagen. Formato: PRODUCTO | CANTIDAD | PRECIO. Ignora lo que no entiendas."

            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            if archivo.type != "application/pdf":
                payload["contents"][0]["parts"].append({"inline_data": {"mime_type": archivo.type, "data": img_data}})

            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            response = requests.post(url, json=payload)
            res_json = response.json()

            if 'candidates' in res_json:
                texto_ia = res_json['candidates'][0]['content']['parts'][0]['text']
                st.session_state.lista = [] 
                
                for linea in texto_ia.split('\n'):
                    if '|' in linea:
                        partes = linea.split('|')
                        if len(partes) >= 3:
                            try:
                                d = partes[0].strip()
                                c = float(partes[1].strip().replace(',', '.'))
                                p = float(partes[2].strip().replace('€', '').replace(',', '.').strip())
                                pvp = calcular_pvp(p, c)
                                st.session_state.lista.append({
                                    "Descripción": d, "Cant": int(c),
                                    "PVP Ud (€)": round(pvp, 2), "Total (€)": round(pvp * c, 2)
                                })
                            except: continue
                st.success("✅ Albarán procesado")
            else:
                st.error("La IA no pudo leer la imagen. Prueba a sacarla con más luz.")
    except Exception as e:
        st.error(f"Error: {e}")

if st.session_state.lista:
    df_f = pd.DataFrame(st.session_state.lista)
    st.table(df_f)
    
    try:
        pdf_out = generar_pdf_premium(df_f, nombre_cliente)
        st.download_button(
            label="📥 Descargar PDF Premium",
            data=pdf_out,
            file_name=f"Presupuesto_{nombre_cliente}.pdf",
            mime="application/pdf"
        )
    except:
        st.error("Hubo un problema al generar el archivo PDF.")
