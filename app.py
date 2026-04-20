import streamlit as st
import pandas as pd
import requests
import base64
from PIL import Image
import io

st.set_page_config(page_title="Alicantina de Vallas", layout="wide")

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

st.title("🏗️ Generador Alicantina de Vallas")
api_key = st.secrets["GEMINI_API_KEY"]
cliente = st.text_input("👤 Nombre del Cliente")

if 'lista' not in st.session_state:
    st.session_state.lista = []

foto = st.file_uploader("📷 Sube la foto del albarán", type=['jpg', 'png', 'jpeg'])

if foto and st.button("🔍 Analizar Presupuesto"):
    try:
        # Convertimos la imagen a formato que entienda la API directa
        img_bytes = foto.read()
        img_b64 = base64.b64encode(img_bytes).decode('utf-8')
        
        # URL de la API estable de Google (v1)
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": "Analiza este presupuesto. Extrae los productos en este formato exacto: NOMBRE | CANTIDAD | PRECIO_COSTE_UNITARIO. No escribas nada más."},
                    {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
                ]
            }]
        }
        
        response = requests.post(url, json=payload)
        res_json = response.json()
        
        # Extraemos el texto de la respuesta
        texto_ia = res_json['candidates'][0]['content']['parts'][0]['text']
        
        if texto_ia:
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
            st.success("✅ ¡Analizado con éxito!")
    except Exception as e:
        st.error(f"Error en la conexión directa: {e}")

if st.session_state.lista:
    st.write(f"### Presupuesto: {cliente}")
    df = pd.DataFrame(st.session_state.lista)
    st.table(df)
    total = df["Total (€)"].sum()
    st.subheader(f"TOTAL con IVA: {total * 1.21:.2f} €")
    if st.button("Limpiar"):
        st.session_state.lista = []
        st.rerun()
