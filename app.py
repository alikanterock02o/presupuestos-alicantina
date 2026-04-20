import streamlit as st
import pandas as pd
import google.generativeai as genai
from google.generativeai.types import RequestOptions
from fpdf import FPDF
import PyPDF2

# 1. CONFIGURACIÓN CORPORATIVA
st.set_page_config(page_title="Alicantina de Vallas - Estabilizado", layout="wide")

# Forzamos la configuración inicial para evitar v1beta
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("⚠️ Configura la API KEY en Secrets.")

# Lógica de márgenes según presupuesto
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

# 2. MOTOR DE IA FORZADO A V1 (ESTABLE)
def analizar_documento(archivo):
    # Forzamos a la API a usar la versión de producción 'v1'
    # Esto elimina el error 404 de la ruta 'v1beta'
    opciones = RequestOptions(api_version='v1')
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = "Extract data exactly as: PRODUCT | QTY | UNIT_COST. Use only plain text."
    
    try:
        if archivo.type == "application/pdf":
            reader = PyPDF2.PdfReader(archivo)
            texto = "".join([p.extract_text() for p in reader.pages])
            response = model.generate_content(f"{prompt}\n\nDocumento:\n{texto}", request_options=opciones)
        else:
            # Procesamiento de imagen (WhatsApp o fotos)
            img_data = archivo.read()
            response = model.generate_content(
                contents=[prompt, {"mime_type": archivo.type, "data": img_data}],
                request_options=opciones
            )
        return response.text
    except Exception as e:
        return f"ERROR_TECNICO: {str(e)}"

# 3. INTERFAZ Y FLUJO
st.title("🏗️ Alicantina de Vallas - Gestor de Presupuestos")

if st.button("♻️ LIMPIAR TODO"):
    st.session_state.clear()
    st.rerun()

nombre_cliente = st.text_input("👤 Nombre del Cliente", value="David")

if 'datos' not in st.session_state:
    st.session_state.datos = []

archivo = st.file_uploader("📄 Sube tu albarán (Foto o PDF)", type=['jpg', 'jpeg', 'png', 'pdf'])

if archivo and st.button("🚀 PROCESAR AHORA"):
    with st.spinner("Analizando vía Servidor Estable (v1)..."):
        resultado = analizar_documento(archivo)
        
        if "ERROR_TECNICO" in resultado:
            st.error(f"Error detectado: {resultado}")
            st.info("Si el error persiste, es un bloqueo de Google en esta zona horaria. Reintenta en 1 minuto.")
        else:
            lineas = resultado.split('\n')
            temp_lista = []
            for l in lineas:
                if '|' in l:
                    try:
                        partes = l.split('|')
                        desc = partes[0].strip()
                        cant = float(partes[1].strip().replace(',','.'))
                        coste = float(partes[2].strip().replace('€','').replace(',','.'))
                        
                        pvp_unidad = calcular_pvp(coste, cant)
                        temp_lista.append({
                            "Descripción": desc,
                            "Cant": int(cant),
                            "PVP Ud (€)": round(pvp_unidad, 2),
                            "Total (€)": round(pvp_unidad * cant, 2)
                        })
                    except: continue
            st.session_state.datos = temp_lista

# 4. TABLA DE RESULTADOS Y EXPORTACIÓN
if st.session_state.datos:
    df = pd.DataFrame(st.session_state.datos)
    st.subheader(f"Presupuesto para: {nombre_cliente}")
    st.table(df)
    
    total_presupuesto = df["Total (€)"].sum()
    st.metric("Total Neto", f"{total_presupuesto:.2f} €")

    # Generación simple de PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, "ALICANTINA DE VALLAS - PRESUPUESTO", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.ln(10)
    for _, fila in df.iterrows():
        linea = f"{fila['Cant']}x {fila['Descripción'][:40]}... | {fila['Total (€)']} e"
        pdf.cell(190, 8, linea, ln=True)
    
    pdf_output = pdf.output(dest='S').encode('latin-1', 'ignore')
    st.download_button("📥 DESCARGAR PRESUPUESTO PDF", data=pdf_output, file_name=f"Presupuesto_{nombre_cliente}.pdf")
