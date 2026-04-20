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

# 2. CONEXIÓN (Secrets)
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Falta la clave API en Secrets")

st.title("🏗️ Generador Alicantina de Vallas")

cliente = st.text_input("👤 Nombre del Cliente Final")

if 'lista' not in st.session_state:
    st.session_state.lista = []

# 3. SUBIDA DE FOTO
foto = st.file_uploader("📷 Sube el presupuesto del proveedor", type=['jpg', 'png', 'jpeg'])

if foto and st.button("🔍 Analizar Presupuesto"):
    try:
        img = Image.open(foto)
        # Usamos el modelo 'gemini-1.5-flash' que es el estándar actual
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = "Analiza este presupuesto. Extrae los artículos en este formato exacto: NOMBRE | CANTIDAD | PRECIO_COSTE. Usa puntos para decimales."
        
        response = model.generate_content([prompt, img])
        
        # Procesar texto
        lineas = response.text.split('\n')
        for linea in lineas:
            if '|' in linea:
                partes = linea.split('|')
                try:
                    desc = partes[0].strip()
                    cant = float(partes[1].strip().replace(',', '.'))
                    coste = float(partes[2].strip().replace(',', '.').replace('€', ''))
                    pvp = calcular_pvp(coste)
                    st.session_state.lista.append({
                        "Descripción": desc, "Cant": int(cant), 
                        "PVP Ud (€)": round(pvp, 2), "Total (€)": round(pvp * cant, 2)
                    })
                except: continue
        st.success("¡Leído!")
    except Exception as e:
        st.error(f"Hubo un problema: {e}")

# 4. RESULTADO
if st.session_state.lista:
    st.markdown("---")
    st.write(f"### Presupuesto para: {cliente}")
    df = pd.DataFrame(st.session_state.lista)
    st.table(df)
    
    total = df["Total (€)"].sum()
    st.subheader(f"TOTAL con IVA: {total * 1.21:.2f} €")
    
    if st.button("Limpiar todo"):
        st.session_state.lista = []
        st.rerun()
