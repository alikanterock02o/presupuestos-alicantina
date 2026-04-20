import streamlit as st
import pandas as pd
import requests
import base64
from fpdf import FPDF
import PyPDF2
import io

st.set_page_config(page_title="Alicantina de Vallas", layout="wide")

# 1. NUEVA LÓGICA DE MÁRGENES (POR VOLUMEN TOTAL DE LÍNEA)
def calcular_pvp(coste_unitario, cantidad):
    # El tramo se decide por el importe total (Coste x Cantidad)
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
    
    # Retornamos el precio de UNA unidad con el margen aplicado
    return coste_unitario * margen

# 2. FUNCIÓN PARA GENERAR EL PDF
def generar_pdf(df, cliente):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "ALICANTINA DE VALLAS - PRESUPUESTO", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", '', 12)
    pdf.cell(200, 10, f"Cliente: {cliente}", ln=True)
    pdf.ln(5)
    
    # Cabecera de la tabla
    pdf.set_fill_color(200, 220, 255)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(100, 10, "Descripcion", 1, 0, 'C', True)
    pdf.cell(20, 10, "Cant.", 1, 0, 'C', True)
    pdf.cell(30, 10, "PVP Ud.", 1, 0, 'C', True)
    pdf.cell(30, 10, "Total", 1, 1, 'C', True)
    
    # Filas
    pdf.set_font("Arial", '', 9)
    for index, row in df.iterrows():
        pdf.cell(100, 10, str(row['Descripción'])[:55], 1)
        pdf.cell(20, 10, str(row['Cant']), 1, 0, 'C')
        pdf.cell(30, 10, f"{row['PVP Ud (€)']} e", 1, 0, 'C')
        pdf.cell(30, 10, f"{row['Total (€)']} e", 1, 1, 'C')
    
    pdf.ln(10)
    total_base = df["Total (€)"].sum()
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, f"TOTAL Base Imponible: {total_base:.2f} euros", ln=True, align='R')
    pdf.cell(200, 10, f"TOTAL con IVA (21%): {total_base * 1.21:.2f} euros", ln=True, align='R')
    
    return pdf.output(dest='S').encode('latin-1', 'ignore')

# 3. INTERFAZ DE USUARIO
st.title("🏗️ Generador Alicantina de Vallas")
api_key = st.secrets["GEMINI_API_KEY"]
nombre_cliente = st.text_input("👤 Nombre del Cliente", value="David")

if 'lista' not in st.session_state:
    st.session_state.lista = []

archivo = st.file_uploader("📄 Sube el albarán (Foto o PDF)", type=['jpg', 'jpeg', 'png', 'pdf'])

if archivo and st.button("🔍 Analizar y Calcular"):
    try:
        with st.spinner("Leyendo datos con IA..."):
            if archivo.type == "application/pdf":
                reader = PyPDF2.PdfReader(archivo)
                texto_pdf = "".join([page.extract_text() for page in reader.pages])
                prompt = f"Extrae: NOMBRE | CANTIDAD | PRECIO_COSTE. Texto: {texto_pdf}"
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
            else:
                img_b64 = base64.b64encode(archivo.read()).decode('utf-8')
                payload = {"contents": [{"parts": [
                    {"text": "Extrae los artículos. Formato: NOMBRE | CANTIDAD | PRECIO_COSTE. Solo las líneas de productos."},
                    {"inline_data": {"mime_type": archivo.type, "data": img_b64}}
                ]}]}

            # URL para Gemini 2.5 Flash
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            response = requests.post(url, json=payload)
            res_json = response.json()

            if 'candidates' in res_json:
                texto_ia = res_json['candidates'][0]['content']['parts'][0]['text']
                
                num_articulos = 0
                for linea in texto_ia.split('\n'):
                    if '|' in linea:
                        partes = linea.split('|')
                        if len(partes) >= 3:
                            try:
                                d = partes[0].strip()
                                c = float(partes[1].strip().replace(',', '.'))
                                p_coste = float(partes[2].strip().replace('€', '').replace(',', '.').strip())
                                
                                # APLICAMOS LA NUEVA LÓGICA DE KITS
                                pvp_unitario = calcular_pvp(p_coste, c)
                                
                                st.session_state.lista.append({
                                    "Descripción": d, 
                                    "Cant": int(c),
                                    "PVP Ud (€)": round(pvp_unitario, 2), 
                                    "Total (€)": round(pvp_unitario * c, 2)
                                })
                                num_articulos += 1
                            except: continue
                
                if num_articulos > 0:
                    st.success(f"✅ {num_articulos} artículos procesados con márgenes aplicados.")
                else:
                    st.error("No se detectaron datos claros. Revisa la foto.")
            else:
                st.error("Error de conexión con la IA. Espera 10 segundos.")
                
    except Exception as e:
        st.error(f"Error técnico: {e}")

# 4. MOSTRAR RESULTADOS Y DESCARGA
if st.session_state.lista:
    df_final = pd.DataFrame(st.session_state.lista)
    st.subheader(f"Presupuesto para: {nombre_cliente}")
    st.table(df_final)
    
    pdf_bytes = generar_pdf(df_final, nombre_cliente)
    st.download_button(
        label="📥 Descargar PDF para WhatsApp",
        data=pdf_bytes,
        file_name=f"Presupuesto_{nombre_cliente}.pdf",
        mime="application/pdf"
    )

    if st.button("🗑️ Nueva consulta"):
        st.session_state.lista = []
        st.rerun()
