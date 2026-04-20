import streamlit as st
import pandas as pd
import requests
import base64
from fpdf import FPDF
import PyPDF2
import io

st.set_page_config(page_title="Alicantina de Vallas | Sistema de Presupuestos", layout="wide")

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

# 2. FUNCIÓN DE PDF CON ESTÉTICA INDUSTRIAL (ROJO Y NEGRO)
def generar_pdf_premium(df, cliente):
    pdf = FPDF()
    pdf.add_page()
    
    # --- CABECERA ESTILO FACHADA ---
    # Fondo rojo para el título principal
    pdf.set_fill_color(204, 0, 0) # Rojo corporativo
    pdf.rect(0, 0, 210, 40, 'F')
    
    pdf.set_font("Arial", 'B', 22)
    pdf.set_text_color(255, 255, 255) # Blanco
    pdf.cell(190, 20, "ALICANTINA DE VALLAS", ln=True, align='C')
    
    pdf.set_font("Arial", '', 10)
    pdf.cell(190, 5, "FERRETERIA INDUSTRIAL - CERRAMIENTOS DE SEGURIDAD", ln=True, align='C')
    pdf.ln(15)
    
    # --- DATOS DEL CLIENTE ---
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(100, 10, f"PRESUPUESTO PARA: {cliente.upper()}", ln=True)
    pdf.set_draw_color(204, 0, 0)
    pdf.line(10, 52, 200, 52) # Línea roja divisoria
    pdf.ln(5)
    
    # --- TABLA DE ARTÍCULOS ---
    # Cabecera de tabla en Negro Industrial
    pdf.set_fill_color(30, 30, 30) 
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 10)
    
    pdf.cell(100, 10, " DESCRIPCION DEL PRODUCTO", 1, 0, 'L', True)
    pdf.cell(20, 10, "CANT.", 1, 0, 'C', True)
    pdf.cell(35, 10, "PRECIO UD.", 1, 0, 'C', True)
    pdf.cell(35, 10, "SUBTOTAL", 1, 1, 'C', True)
    
    # Filas de la tabla
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 9)
    pdf.set_fill_color(245, 245, 245) # Gris muy claro para filas alternas
    
    toggle_bg = False
    for index, row in df.iterrows():
        fill = toggle_bg
        pdf.cell(100, 9, f" {str(row['Descripción'])[:50]}", 1, 0, 'L', fill)
        pdf.cell(20, 9, str(row['Cant']), 1, 0, 'C', fill)
        pdf.cell(35, 9, f"{row['PVP Ud (€)']} e", 1, 0, 'C', fill)
        pdf.cell(35, 9, f"{row['Total (€)']} e", 1, 1, 'C', fill)
        toggle_bg = not toggle_bg
    
    # --- TOTALES FINALES ---
    pdf.ln(10)
    total_base = df["Total (€)"].sum()
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(155, 10, "TOTAL BASE IMPONIBLE:", 0, 0, 'R')
    pdf.set_text_color(0, 0, 0)
    pdf.cell(35, 10, f"{total_base:.2f} e", 0, 1, 'R')
    
    # Destacado en Rojo para el Total con IVA
    pdf.set_text_color(204, 0, 0)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(155, 12, "TOTAL IVA INCLUIDO (21%):", 0, 0, 'R')
    pdf.cell(35, 12, f"{total_base * 1.21:.2f} e", 0, 1, 'R')
    
    # Pie de página
    pdf.set_y(-30)
    pdf.set_font("Arial", 'I', 8)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, "Gracias por confiar en Alicantina de Vallas. Calidad y seguridad en cada proyecto.", 0, 0, 'C')
    
    return pdf.output(dest='S').encode('latin-1', 'ignore')

# 3. INTERFAZ DE USUARIO
st.title("🏗️ Alicantina de Vallas - Generador Pro")
api_key = st.secrets["GEMINI_API_KEY"]
nombre_cliente = st.text_input("👤 Nombre del Cliente", value="Cliente")

if 'lista' not in st.session_state:
    st.session_state.lista = []

archivo = st.file_uploader("📄 Sube el albarán o presupuesto", type=['jpg', 'jpeg', 'png', 'pdf'])

if archivo and st.button("🔍 Analizar y Calcular Márgenes"):
    try:
        with st.spinner("Procesando con Inteligencia Industrial..."):
            if archivo.type == "application/pdf":
                reader = PyPDF2.PdfReader(archivo)
                texto_pdf = "".join([page.extract_text() for page in reader.pages])
                prompt = f"Extrae: NOMBRE | CANTIDAD | PRECIO_COSTE. Texto: {texto_pdf}"
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
            else:
                img_b64 = base64.b64encode(archivo.read()).decode('utf-8')
                payload = {"contents": [{"parts": [
                    {"text": "Extrae artículos del albarán. Formato: NOMBRE | CANTIDAD | PRECIO_COSTE."},
                    {"inline_data": {"mime_type": archivo.type, "data": img_b64}}
                ]}]}

            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            response = requests.post(url, json=payload)
            res_json = response.json()

            if 'candidates' in res_json:
                texto_ia = res_json['candidates'][0]['content']['parts'][0]['text']
                st.session_state.lista = [] # Limpiar lista previa
                
                for linea in texto_ia.split('\n'):
                    if '|' in linea:
                        partes = linea.split('|')
                        if len(partes) >= 3:
                            try:
                                d = partes[0].strip()
                                c = float(partes[1].strip().replace(',', '.'))
                                p_coste = float(partes[2].strip().replace('€', '').replace(',', '.').strip())
                                pvp_unitario = calcular_pvp(p_coste, c)
                                st.session_state.lista.append({
                                    "Descripción": d, 
                                    "Cant": int(c),
                                    "PVP Ud (€)": round(pvp_unitario, 2), 
                                    "Total (€)": round(pvp_unitario * c, 2)
                                })
                            except: continue
                st.success("✅ Datos procesados correctamente.")
            else:
                st.error("Error en la lectura. Intenta subir una foto más clara.")
    except Exception as e:
        st.error(f"Error técnico: {e}")

# 4. MOSTRAR RESULTADOS Y DESCARGA
if st.session_state.lista:
    df_final = pd.DataFrame(st.session_state.lista)
    st.subheader(f"Vista Previa: {nombre_cliente}")
    st.table(df_final)
    
    pdf_bytes = generar_pdf_premium(df_final, nombre_cliente)
    st.download_button(
        label="📥 Descargar Presupuesto Premium (PDF)",
        data=pdf_bytes,
        file_name=f"Presupuesto_Alicantina_{nombre_cliente}.pdf",
        mime="application/pdf"
    )
    
    if st.button("🗑️ Limpiar y Nuevo"):
        st.session_state.lista = []
        st.rerun()
