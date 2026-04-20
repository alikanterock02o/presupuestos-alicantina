import streamlit as st
import pandas as pd
import google.generativeai as genai
from fpdf import FPDF
import PyPDF2
import io

# 1. CONFIGURACIÓN DE MARCA
st.set_page_config(page_title="Alicantina de Vallas", layout="wide")

# Configurar IA con la versión estable
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # Usamos la versión de producción directa
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"Error de configuración: {e}")

# Lógica de márgenes exacta de Alicantina de Vallas
def calcular_pvp(coste, cantidad):
    total_l = coste * cantidad
    if total_l <= 0.05: m = 3.0
    elif total_l <= 0.25: m = 2.5
    elif total_l <= 1.0: m = 2.0
    elif total_l <= 3.0: m = 1.75
    elif total_l <= 10.0: m = 1.50
    elif total_l <= 50.0: m = 1.43
    elif total_l <= 300.0: m = 1.35
    elif total_l <= 1000.0: m = 1.29
    else: m = 1.25
    return coste * m

# 2. GENERADOR DE PDF PROFESIONAL
def generar_pdf(df, cliente):
    pdf = FPDF()
    pdf.add_page()
    # Estética de la empresa: Rojo y Blanco
    pdf.set_fill_color(204, 0, 0) 
    pdf.rect(0, 0, 210, 35, 'F')
    pdf.set_font("Arial", 'B', 22)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(190, 20, "ALICANTINA DE VALLAS", ln=True, align='C')
    pdf.ln(20)
    # Tabla de productos
    pdf.set_text_color(0, 0, 0)
    pdf.set_fill_color(30, 30, 30)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(100, 10, " DESCRIPCION", 1, 0, 'L', True)
    pdf.cell(20, 10, "CANT.", 1, 0, 'C', True)
    pdf.cell(35, 10, "PRECIO UD.", 1, 0, 'C', True)
    pdf.cell(35, 10, "SUBTOTAL", 1, 1, 'C', True)
    # Contenido de la tabla
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 9)
    for _, row in df.iterrows():
        pdf.cell(100, 9, f" {str(row['Descripción'])[:55]}", 1)
        pdf.cell(20, 9, str(row['Cant']), 1, 0, 'C')
        pdf.cell(35, 9, f"{row['PVP Ud (€)']} e", 1, 0, 'C')
        pdf.cell(35, 9, f"{row['Total (€)']} e", 1, 1, 'C')
    # Total destacado
    t_final = df["Total (€)"].sum()
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(204, 0, 0)
    pdf.cell(190, 10, f"TOTAL IVA INCLUIDO: {t_final * 1.21:.2f} euros", 0, 1, 'R')
    return pdf.output(dest='S').encode('latin-1', 'ignore')

# 3. INTERFAZ DE USUARIO
st.title("🏗️ Alicantina de Vallas - Sistema Pro")

if st.button("♻️ Reiniciar Sistema"):
    st.session_state.lista = []
    st.rerun()

nombre_c = st.text_input("👤 Cliente", value="David")

if 'lista' not in st.session_state:
    st.session_state.lista = []

archivo = st.file_uploader("📄 Subir Albarán o Foto", type=['jpg', 'jpeg', 'png', 'pdf'])

if archivo and st.button("🔍 ANALIZAR Y CALCULAR"):
    try:
        with st.spinner("Analizando con tecnología Google..."):
            instruccion = "Analiza el documento y devuelve solo: PRODUCTO | CANTIDAD | PRECIO_UNITARIO"
            
            if archivo.type == "application/pdf":
                reader = PyPDF2.PdfReader(archivo)
                texto = "".join([p.extract_text() for p in reader.pages])
                res = model.generate_content(f"{instruccion}\n\nTexto:\n{texto}")
            else:
                img = archivo.read()
                res = model.generate_content([instruccion, {"mime_type": archivo.type, "data": img}])

            if res.text:
                st.session_state.lista = []
                for linea in res.text.split('\n'):
                    if '|' in linea:
                        p = linea.split('|')
                        if len(p) >= 3:
                            try:
                                d = p[0].strip()
                                c = float(p[1].strip().replace(',','.'))
                                pr = float(p[2].strip().replace('€','').replace(',','.'))
                                pvp = calcular_pvp(pr, c)
                                st.session_state.lista.append({
                                    "Descripción": d, "Cant": int(c),
                                    "PVP Ud (€)": round(pvp, 2), "Total (€)": round(pvp * c, 2)
                                })
                            except: continue
                st.success("✅ Datos extraídos")
    except Exception as e:
        st.error(f"Error temporal del servicio. Por favor, pulsa 'Reiniciar' e intenta de nuevo.")

if st.session_state.lista:
    df_m = pd.DataFrame(st.session_state.lista)
    st.table(df_m)
    pdf_f = generar_pdf(df_m, nombre_c)
    st.download_button("📥 DESCARGAR PRESUPUESTO PDF", data=pdf_f, file_name=f"Presupuesto_{nombre_c}.pdf")
