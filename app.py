import streamlit as st
import pandas as pd
import requests
import base64
import json
from PIL import Image

st.set_page_config(page_title="Alicantina de Vallas - v3.1", layout="wide")

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

st.title("🏗️ Generador Alicantina de Vallas (v3.1)")
api_key = st.secrets["GEMINI_API_KEY"]
cliente = st.text_input("👤 Nombre del Cliente")

if 'lista' not in st.session_state:
    st.session_state.lista = []

# Volvemos a las fotos, que ahora sí funcionarán con el modelo correcto
foto = st.file_uploader("📷 Sube la foto del albarán", type=['jpg', 'png', 'jpeg'])

if foto and st.button("🔍 Analizar Albarán"):
    try:
        img_bytes = foto.read()
        img_b64 = base64.b64encode(img_bytes).decode('utf-8')
        
        # USAMOS EL MODELO 3.1 QUE APARECE EN TU LISTA
        # Cambiamos a v1beta porque los modelos 'preview' suelen requerir esa versión
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image-preview:generateContent?key={api_key}"
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": "Extrae los artículos de este albarán. Formato: NOMBRE | CANTIDAD | PRECIO_COSTE. No digas nada más."},
                    {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
                ]
            }]
        }
        
        response = requests.post(url, json=payload)
        res_json = response.json()
        
        if 'candidates' in res_json:
            texto_ia = res_json['candidates'][0]['content']['parts'][0]['text']
            for linea in texto_ia.split('\n'):
                if '|' in linea:
                    p = linea.split('|')
                    try:
                        desc = p[0].strip()
                        cant = float(p[1].strip().replace(',', '.'))
                        coste = float(p[2].strip().replace('€', '').replace(',', '.').strip())
                        pvp = calcular_pvp(coste)
                        st.session_state.lista.append({
                            "Descripción": desc, "Cant": int(cant), 
                            "PVP Ud (€)": round(pvp, 2), "Total (€)": round(pvp * cant, 2)
                        })
                    except: continue
            st.success("✅ Albarán procesado con Gemini 3.1")
        else:
            st.error(f"Error de respuesta: {res_json}")
            
    except Exception as e:
        st.error(f"Error técnico: {e}")

if st.session_state.lista:
    st.write(f"### Presupuesto: {cliente}")
    df = pd.DataFrame(st.session_state.lista)
    st.table(df)
    total = df["Total (€)"].sum()
    st.subheader(f"TOTAL con IVA (21%): {total * 1.21:.2f} €")
    if st.button("Limpiar"):
        st.session_state.lista = []
        st.rerun()
