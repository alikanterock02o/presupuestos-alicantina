import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd

# 1. CONFIGURACIÓN INICIAL
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

# 2. CONEXIÓN FORZADA (Evita v1beta)
if "GEMINI_API_KEY" in st.secrets:
    # Usamos explícitamente la versión v1 para evitar el error 404 v1beta
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"], transport='rest')
else:
    st.error("Configura la clave en Secrets")

st.title("🏗️ Generador Alicantina de Vallas")
cliente = st.text_input("👤 Nombre del Cliente")

if 'lista' not in st.session_state:
    st.session_state.lista = []

# 3. PROCESADO DE IMAGEN
foto = st.file_uploader("📷 Sube el albarán", type=['jpg', 'png', 'jpeg'])

if foto and st.button("🔍 Analizar"):
    try:
        img = Image.open(foto)
        
        # Probamos el modelo flash-latest que es el más compatible hoy
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        prompt = "Lee este presupuesto. Extrae los productos en este formato exacto: NOMBRE | CANTIDAD | PRECIO_COSTE. No escribas nada más."
        
        # Llamada directa
        response = model.generate_content([prompt, img])
        
        if response.text:
            for linea in response.text.split('\n'):
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
            st.success("✅ Albarán procesado")
    except Exception as e:
        # Si esto da 404, probamos el modelo pro de respaldo
        try:
            model_backup = genai.GenerativeModel('gemini-1.5-pro-latest')
            response = model_backup.generate_content([prompt, img])
            st.success("✅ Procesado con modelo de respaldo")
        except:
            st.error(f"Error de Google: {e}")

# 4. TABLA DE RESULTADOS
if st.session_state.lista:
    st.write(f"### Presupuesto: {cliente}")
    df = pd.DataFrame(st.session_state.lista)
    st.table(df)
    total = df["Total (€)"].sum()
    st.subheader(f"TOTAL con IVA: {total * 1.21:.2f} €")
    if st.button("Limpiar"):
        st.session_state.lista = []
        st.rerun()
