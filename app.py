import streamlit as st
import pandas as pd
import requests
import base64
import json
import PyPDF2
from PIL import Image
import io

# Configuración de la página
st.set_page_config(page_title="Alicantina de Vallas - Generador", layout="wide")

# 1. Escala de precios (Tu lógica de negocio)
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

# UI Principal
st.title("🏗️ Generador Alicantina de Vallas")
api_key = st.secrets["GEMINI_API_KEY"]
cliente = st.text_input("👤 Nombre del Cliente", placeholder="Ej: Juan Pérez")

if 'lista' not in st.session_state:
    st.session_state.lista = []

# Selector de archivo
archivo = st.file_uploader("📄 Sube el albarán (Foto o PDF)", type=['jpg', 'jpeg', 'png', 'pdf'])

if archivo and st.button("🔍 Analizar y Calcular"):
    try:
        with st.spinner("Procesando con Inteligencia Artificial..."):
            payload = {}
            
            # Caso A: Es un PDF (Extraemos texto)
            if archivo.type == "application/pdf":
                reader = PyPDF2.PdfReader(archivo)
                texto_pdf = ""
                for page in reader.pages:
                    texto_pdf += page.extract_text()
                
                payload = {
                    "contents": [{
                        "parts": [{
                            "text": f"Extrae los productos de este texto. Formato: NOMBRE | CANTIDAD | PRECIO_COSTE. No digas nada más. Texto: {texto_pdf}"
                        }]
                    }]
                }
            
            # Caso B: Es una Imagen
            else:
                img_bytes = archivo.read()
                img_b64 = base64.b64encode(img_bytes).decode('utf-8')
                payload = {
                    "contents": [{
                        "parts": [
                            {"text": "Extrae los artículos de este albarán. Formato: NOMBRE | CANTIDAD | PRECIO_COSTE. No digas nada más."},
                            {"inline_data": {"mime_type": archivo.type, "data": img_b64}}
                        ]
                    }]
                }

            # Llamada REST a la API (Modelo 2.5 Flash para evitar 404 y 429)
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            response = requests.post(url, json=payload)
            res_json = response.json()

            if 'candidates' in res_json:
                texto_ia = res_json['candidates'][0]['content']['parts'][0]['text']
                
                # Procesar líneas recibidas
                nuevos_items = 0
                for linea in texto_ia.split('\n'):
                    if '|' in linea:
                        p = linea.split('|')
                        try:
                            desc = p[0].strip()
                            cant = float(p[1].strip().replace(',', '.'))
                            coste = float(p[2].strip().replace('€', '').replace(',', '.').strip())
                            pvp_ud = calcular_pvp(coste)
                            
                            st.session_state.lista.append({
                                "Descripción": desc,
                                "Cant": int(cant),
                                "Coste Ud (€)": round(coste, 2),
                                "PVP Ud (€)": round(pvp_ud, 2),
                                "Total PVP (€)": round(pvp_ud * cant, 2)
                            })
                            nuevos_items += 1
                        except: continue
                
                if nuevos_items > 0:
                    st.success(f"✅ Se han añadido {nuevos_items} artículos.")
                else:
                    st.warning("⚠️ No se detectaron artículos con el formato correcto.")
            else:
                st.error(f"Error de Google: {res_json.get('error', {}).get('message', 'Desconocido')}")

    except Exception as e:
        st.error(f"Error técnico: {e}")

# Mostrar Tabla de Resultados
if st.session_state.lista:
    st.write(f"### Presupuesto para: **{cliente if cliente else 'Cliente General'}**")
    df = pd.DataFrame(st.session_state.lista)
    
    # Mostrar tabla estilizada
    st.dataframe(df, use_container_width=True)
    
    # Cálculos totales
    total_pvp = df["Total PVP (€)"].sum()
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Base Imponible", f"{total_pvp:.2f} €")
    with col2:
        st.metric("TOTAL (IVA 21%)", f"{total_pvp * 1.21:.2f} €")

    if st.button("🗑️ Limpiar Todo"):
        st.session_state.lista = []
        st.rerun()
