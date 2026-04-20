import streamlit as st
import pandas as pd
import PyPDF2
import requests
import json

st.set_page_config(page_title="Alicantina de Vallas - Fix", layout="wide")

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

archivo = st.file_uploader("📄 Sube el presupuesto (PDF)", type=['pdf'])

if archivo and st.button("🔍 Analizar Presupuesto"):
    try:
        # 1. Extraer texto del PDF localmente
        reader = PyPDF2.PdfReader(archivo)
        texto_pdf = ""
        for page in reader.pages:
            texto_pdf += page.extract_text()
        
        if texto_pdf:
            # 2. Llamada directa a la API (Ruta estable v1)
            # Esta URL es manual para saltarnos el error 404 de la librería
            url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
            
            headers = {'Content-Type': 'application/json'}
            payload = {
                "contents": [{
                    "parts": [{
                        "text": f"Extrae los productos de este texto. Formato exacto: NOMBRE | CANTIDAD | PRECIO_COSTE. Texto: {texto_pdf}"
                    }]
                }]
            }
            
            response = requests.post(url, headers=headers, data=json.dumps(payload))
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
                st.success("✅ ¡Presupuesto procesado!")
            else:
                st.error(f"Error de Google: {res_json}")
    except Exception as e:
        st.error(f"Error técnico: {e}")

if st.session_state.lista:
    df = pd.DataFrame(st.session_state.lista)
    st.table(df)
    total = df["Total (€)"].sum()
    st.subheader(f"TOTAL con IVA (21%): {total * 1.21:.2f} €")
    if st.button("Limpiar"):
        st.session_state.lista = []
        st.rerun()
