import streamlit as st
import pandas as pd
import google.generativeai as genai
from fpdf import FPDF
import PyPDF2

# 1. CONFIGURACIÓN E IDENTIDAD CORPORATIVA
st.set_page_config(page_title="Alicantina de Vallas | Facturación", layout="wide")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Configura la API KEY en Secrets.")

# Lógica de márgenes Alicantina de Vallas
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

# 2. PROCESO DE IA CON FALLBACK (ANTI-404)
def analizar_con_ia(archivo):
    # Intentamos primero con Flash (rápido), si falla vamos a Pro (robusto)
    modelos_a_probar = ['gemini-1.5-flash', 'gemini-1.5-pro']
    
    for nombre_modelo in modelos_a_probar:
        try:
            model = genai.GenerativeModel(nombre_modelo)
            prompt = "Extract: ITEM | QTY | UNIT_PRICE. Clean text only."
            
            if archivo.type == "application/pdf":
                reader = PyPDF2.PdfReader(archivo)
                texto = "".join([p.extract_text() for p in reader.pages])
                res = model.generate_content(f"{prompt}\n\nDocumento:\n{texto}")
            else:
                img = archivo.read()
                res = model.generate_content([prompt, {"mime_type": archivo.type, "data": img}])
            
            if res.text: return res.text
        except Exception:
            continue # Si falla uno, salta al siguiente modelo
    return None

# 3. GENERADOR DE PDF ALICANTINA
def generar_pdf(df, cliente):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_fill_color(204, 0, 0) # Rojo corporativo
    pdf.rect(0, 0, 210, 35, 'F')
    pdf.set_font("Arial", 'B', 22)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(190, 15, "ALICANTINA DE VALLAS", ln=True, align='C')
    pdf.ln(20)
    pdf.set_fill_color(40, 40, 40)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(100, 10, " PRODUCTO", 1, 0, 'L', True)
    pdf.cell(20, 10, "CANT.", 1, 0, 'C', True)
    pdf.cell(35, 10, "PVP UD.", 1, 0, 'C', True)
    pdf.cell(35, 10, "TOTAL", 1, 1, 'C', True)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 9)
    for _, row in df.iterrows():
        pdf.cell(100, 9, f" {str(row['Descripción'])[:55]}", 1)
        pdf.cell(20, 9, str(row['Cant']), 1, 0, 'C')
        pdf.cell(35, 9, f"{row['PVP Ud (€)']} e", 1, 0, 'C')
        pdf.cell(35, 9, f"{row['Total (€)']} e", 1, 1, 'C')
    t_final = df["Total (€)"].sum()
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(204, 0, 0)
    pdf.cell(190, 10, f"TOTAL IVA INCLUIDO (21%): {t_final * 1.21:.2f} e", 0, 1, 'R')
    return pdf.output(dest='S').encode('latin-1', 'ignore')

# 4. INTERFAZ DE USUARIO
st.title("🏗️ Alicantina de Vallas - Gestor de Albaranes")

if st.button("♻️ REINICIAR Y LIMPIAR CACHÉ"):
    st.session_state.lista = []
    st.rerun()

nombre_c = st.text_input("👤 Cliente", value="David")

if 'lista' not in st.session_state:
    st.session_state.lista = []

archivo = st.file_uploader("📄 Sube el documento", type=['jpg', 'jpeg', 'png', 'pdf'])

if archivo and st.button("🔍 ANALIZAR DOCUMENTO"):
    with st.spinner("Conectando con servidores estables de Google..."):
        resultado_texto = analizar_con_ia(archivo)
        
        if resultado_texto:
            st.session_state.lista = []
            for linea in resultado_texto.split('\n'):
                if '|' in linea:
                    pts = linea.split('|')
                    if len(pts) >= 3:
                        try:
                            d, c, p = pts[0].strip(), float(pts[1].strip().replace(',','.')), float(pts[2].strip().replace('€','').replace(',','.'))
                            pvp = calcular_pvp(p, c)
                            st.session_state.lista.append({"Descripción": d, "Cant": int(c), "PVP Ud (€)": round(pvp, 2), "Total (€)": round(pvp * c, 2)})
                        except: continue
            st.success("✅ Análisis realizado.")
        else:
            st.error("❌ Google sigue devolviendo error 404 en tu zona. Intenta 'Reboot' desde el panel de Streamlit.")

if st.session_state.lista:
    df = pd.DataFrame(st.session_state.lista)
    st.table(df)
    pdf_out = generar_pdf(df, nombre_c)
    st.download_button("📥 DESCARGAR PRESUPUESTO", data=pdf_out, file_name=f"Presupuesto_{nombre_c}.pdf")
