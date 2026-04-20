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
        img_bytes = foto.read()
        img_b64 = base64.b64encode(img_bytes).decode('utf-8')
        
        # URL forzada a la versión estable
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": "Extrae los artículos de este albarán. Formato: NOMBRE | CANTIDAD | PRECIO_COSTE_UNITARIO. No añadas nada más."},
                    {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
                ]
            }],
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ]
        }
        
        response = requests.post(url, json=payload)
        res_json = response.json()
        
        # COMPROBACIÓN DE ERRORES DE RESPUESTA
        if 'error' in res_json:
            st.error(f"❌ Error de Google: {res_json['error']['message']}")
        elif 'candidates' not in res_json or not res_json['candidates'][0].get('content'):
            st.warning("⚠️ La IA no ha podido leer datos claros. Intenta que la foto tenga más luz o esté mejor enfocada.")
            if 'promptFeedback' in res_json:
                st.info("Nota: La imagen ha sido filtrada por seguridad de Google.")
        else:
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
            st.success("✅ ¡Presupuesto generado!")
            
    except Exception as e:
        st.error(f"Error inesperado: {e}")

if st.session_state.lista:
    st.write(f"### Presupuesto: {cliente}")
    df = pd.DataFrame(st.session_state.lista)
    st.table(df)
    total = df["Total (€)"].sum()
    st.subheader(f"TOTAL con IVA (21%): {total * 1.21:.2f} €")
    if st.button("Limpiar datos"):
        st.session_state.lista = []
        st.rerun()
