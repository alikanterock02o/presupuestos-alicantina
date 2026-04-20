import streamlit as st
import pandas as pd
import requests
import base64
from fpdf import FPDF
import PyPDF2
import io

st.set_page_config(page_title="Alicantina de Vallas | Presupuestos", layout="wide")

# 1. LÓGICA DE MÁRGENES (Mantenemos tu lógica de kits)
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

# 2. GENERADOR DE PDF PREMIUM (Blindado)
def generar_pdf_premium(df, cliente):
    pdf = FPDF()
    pdf.add_page()
    
    # Cabecera Roja Corporativa
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
    pdf.set_draw_color(204, 0, 0)
    pdf.line(10, 55, 200, 55)
    pdf.ln(5)
    
    # Tabla
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
    
    pdf.ln(10)
    total_base = df["Total (€)"].sum()
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(204, 0, 0)
    pdf.cell(190, 10, f"TOTAL IVA INCLUIDO (21%): {total_base * 1.21:.2f} euros", 0, 1, 'R')
    
    return pdf.output(dest='S').encode('latin-1', 'ignore')

# 3. INTERFAZ
st.title("🏗️ Alicantina de Vallas - Sistema de Presupuestos")
api_key = st.secrets["GEMINI_API_KEY"]
nombre_cliente = st.text_input("👤 Nombre del Cliente", value="David")

if 'lista' not in st.session_state:
    st.session_state.lista = []

archivo = st.file_uploader("📄 Sube tu albarán (Foto o PDF)", type=['jpg', 'jpeg', 'png', 'pdf'])

if archivo and st.button("🔍 PROCESAR DOCUMENTO"):
    try:
        with st.spinner("Analizando documento a fondo..."):
            # Preparar el contenido para la IA
            parts = []
            
            # Instrucción maestra (más detallada)
            instruccion = (
                "Actúa como un experto contable. Analiza este documento y extrae CUALQUIER artículo, cantidad y precio unitario. "
                "Ignora logotipos o textos irrelevantes. Devuelve SOLO las líneas encontradas en este formato exacto: "
                "PRODUCTO | CANTIDAD | PRECIO_UNITARIO. No añadas encabezados ni notas."
            )
            parts.append({"text": instruccion})

            if archivo.type == "application/pdf":
                reader = PyPDF2.PdfReader(archivo)
                texto_pdf = ""
                for page in reader.pages:
                    texto_pdf += page.extract_text()
                parts.append({"text": f"DOCUMENTO TEXTO:\n{texto_pdf}"})
            else:
                img_data = base64.b64encode(archivo.read()).decode('utf-8')
                parts.append({"inline_data": {"mime_type": archivo.type, "data": img_data}})

            # Petición a Gemini 2.5 Flash
            payload = {"contents": [{"parts": parts}]}
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            
            response = requests.post(url, json=payload)
            res_json = response.json()

            if 'candidates' in res_json:
                texto_ia = res_json['candidates'][0]['content']['parts'][0]['text']
                st.session_state.lista = [] # Reiniciamos para nueva lectura
                
                encontrados = 0
                for linea in texto_ia.split('\n'):
                    if '|' in linea:
                        partes = linea.split('|')
                        if len(partes) >= 3:
                            try:
                                d = partes[0].strip()
                                # Limpiamos números (quitamos puntos de miles, cambiamos comas por puntos)
                                c_str = partes[1].strip().replace('.', '').replace(',', '.')
                                p_str = partes[2].strip().replace('€', '').replace('.', '').replace(',', '.').strip()
                                
                                cant = float(c_str)
                                precio = float(p_str)
                                
                                pvp_ud = calcular_pvp(precio, cant)
                                st.session_state.lista.append({
                                    "Descripción": d, "Cant": int(cant),
                                    "PVP Ud (€)": round(pvp_ud, 2), "Total (€)": round(pvp_ud * cant, 2)
                                })
                                encontrados += 1
                            except: continue
                
                if encontrados > 0:
                    st.success(f"✅ ¡Éxito! Hemos extraído {encontrados} productos.")
                else:
                    st.warning("⚠️ La IA no ha encontrado líneas con formato PRODUCTO | CANTIDAD | PRECIO. Revisa la calidad del archivo.")
            else:
                st.error("Error en la respuesta de Google. Prueba de nuevo en unos segundos.")
    except Exception as e:
        st.error(f"Error técnico crítico: {e}")

# 4. MOSTRAR Y DESCARGAR
if st.session_state.lista:
    df_f = pd.DataFrame(st.session_state.lista)
    st.table(df_f)
    
    pdf_bytes = generar_pdf_premium(df_f, nombre_cliente)
    st.download_button(
        label="📥 DESCARGAR PRESUPUESTO PDF",
        data=pdf_bytes,
        file_name=f"Presupuesto_Alicantina_{nombre_cliente}.pdf",
        mime="application/pdf"
    )

    if st.button("🗑️ Borrar y empezar de nuevo"):
        st.session_state.lista = []
        st.rerun()
