import streamlit as st
import pandas as pd
import requests
import base64
import json
import PyPDF2
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

archivo = st.file_uploader("📄 Sube el albarán (Foto o PDF)", type=['jpg', 'jpeg', 'png', 'pdf'])

if archivo and st.button("🔍 Analizar y Calcular"):
    try:
        with st.spinner("Conectando con Google..."):
            if archivo.type == "application/pdf":
                reader = PyPDF2.PdfReader(archivo)
                texto_pdf = "".join([page.extract_text() for page in reader.pages])
                payload = {"contents": [{"parts": [{"text": f"Extrae: PRODUCTO | CANTIDAD | PRECIO_COSTE. Texto: {texto_pdf}"}]}]}
            else:
                img_b64 = base64.b64encode(archivo.read()).decode('utf-8')
                payload = {"contents": [{"parts": [
                    {"text": "Extrae: PRODUCTO | CANTIDAD | PRECIO_COSTE."},
                    {"inline_data": {"mime_type": archivo.type, "data": img_b64}}
                ]}]}

            # USAMOS EL MODELO ESTABLE (v1 en lugar de v1beta para evitar el 404)
            url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
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
                            pvp_ud = calcular_pvp(coste)
                            st.session_state.lista.append({
                                "Descripción": desc, "Cant": int(cant),
                                "PVP Ud (€)": round(pvp_ud, 2), "Total (€)": round(pvp_ud * cant, 2)
                            })
                        except: continue
                st.success("✅ Procesado correctamente")
            elif 'error' in res_json:
                msg = res_json['error'].get('message', '')
                if "high demand" in msg.lower():
                    st.warning("⚠️ Google está saturado ahora mismo. Espera 10 segundos y vuelve a pulsar el botón.")
                else:
                    st.error(f"Error: {msg}")
    except Exception as e:
        st.error(f"Error inesperado: {e}")

if st.session_state.lista:
    df = pd.DataFrame(st.session_state.lista)
    st.table(df)
    total = df["Total (€)"].sum()
    st.subheader(f"TOTAL con IVA (21%): {total * 1.21:.2f} €")
    if st.button("🗑️ Limpiar"):
        st.session_state.lista = []
        st.rerun()
