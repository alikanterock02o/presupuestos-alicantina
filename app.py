import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd

# 1. CONFIGURACIÓN
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

# 2. CONEXIÓN INTELIGENTE
if "GEMINI_API_KEY" not in st.secrets:
    st.error("❌ Falta la clave en Secrets")
else:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

st.title("🏗️ Generador Alicantina de Vallas")
cliente = st.text_input("👤 Nombre del Cliente")

if 'lista' not in st.session_state:
    st.session_state.lista = []

foto = st.file_uploader("📷 Sube el presupuesto del proveedor", type=['jpg', 'png', 'jpeg'])

if foto and st.button("🔍 Analizar Presupuesto"):
    try:
        img = Image.open(foto)
        if img.mode != 'RGB':
            img = img.convert('RGB')
            
        # PROBAMOS VARIOS MODELOS POR SI UNO FALLA
        modelos_disponibles = ['gemini-1.5-flash', 'gemini-pro-vision']
        response = None
        
        for nombre_modelo in modelos_disponibles:
            try:
                model = genai.GenerativeModel(nombre_modelo)
                prompt = "Extrae los productos de esta imagen en formato: NOMBRE | CANTIDAD | PRECIO_COSTE"
                response = model.generate_content([prompt, img])
                if response:
                    st.toast(f"✅ Conectado vía {nombre_modelo}")
                    break
            except:
                continue
        
        if response:
            lineas = response.text.split('\n')
            for linea in lineas:
                if '|' in linea:
                    partes = linea.split('|')
                    try:
                        desc = partes[0].strip()
                        cant = float(partes[1].strip().replace(',', '.'))
                        coste = float(partes[2].strip().replace(',', '.').replace('€', '').replace('$', ''))
                        pvp = calcular_pvp(coste)
                        st.session_state.lista.append({
                            "Descripción": desc, "Cant": int(cant), 
                            "PVP Ud (€)": round(pvp, 2), "Total (€)": round(pvp * cant, 2)
                        })
                    except: continue
            st.success("¡Lectura finalizada!")
        else:
            st.error("❌ Google no responde. Revisa tu API Key.")
            
    except Exception as e:
        st.error(f"Error inesperado: {e}")

# 3. MOSTRAR RESULTADOS
if st.session_state.lista:
    st.markdown("---")
    st.subheader(f"Presupuesto: {cliente}")
    df = pd.DataFrame(st.session_state.lista)
    st.table(df)
    total = df["Total (€)"].sum()
    st.subheader(f"TOTAL con IVA: {total * 1.21:.2f} €")
    if st.button("Limpiar"):
        st.session_state.lista = []
        st.rerun()
