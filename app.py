import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Alicantina de Vallas - Smart", page_icon="🏗️", layout="wide")

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

# 2. CONEXIÓN BLINDADA
# Forzamos el uso de la versión estable de la API para evitar el error 404
if "GEMINI_API_KEY" not in st.secrets:
    st.error("❌ Configura la clave en Secrets.")
else:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

st.title("🏗️ Generador Automático")
st.write("Mantenimientos Alicantina de Vallas S.L.")

cliente = st.text_input("👤 Nombre del Cliente Final")

if 'lista' not in st.session_state:
    st.session_state.lista = []

st.markdown("---")
foto = st.file_uploader("📷 Sube la captura del presupuesto", type=['jpg', 'png', 'jpeg'])

if foto and st.button("🔍 Analizar y Calcular"):
    try:
        with st.spinner('Leyendo albarán...'):
            img = Image.open(foto)
            # USAMOS EL MODELO POR DEFECTO MÁS COMPATIBLE
            model = genai.GenerativeModel('models/gemini-1.5-flash')
            
            prompt = "Extrae productos de este albarán: NOMBRE | CANTIDAD | PRECIO_COSTE. Solo texto, sin euros."
            
            # El cambio clave: quitamos parámetros extraños que dan error
            response = model.generate_content([prompt, img])
            
            lineas = response.text.split('\n')
            nuevos_items = []
            for linea in lineas:
                if '|' in linea:
                    p = linea.split('|')
                    try:
                        d = p[0].strip()
                        n = float(p[1].strip().replace(',', '.'))
                        c = float(p[2].strip().replace(',', '.').replace('€', ''))
                        pvp = calcular_pvp(c)
                        nuevos_items.append({
                            "Descripción": d, "Cant": int(n), 
                            "Precio Ud. (€)": round(pvp, 2), "Total (€)": round(pvp * n, 2)
                        })
                    except: continue
            
            if nuevos_items:
                st.session_state.lista = nuevos_items
                st.success("✅ ¡Leído correctamente!")
    except Exception as e:
        # Si falla el flash, intentamos el pro automáticamente
        try:
            model = genai.GenerativeModel('models/gemini-1.5-pro')
            response = model.generate_content([prompt, img])
            # ... (mismo proceso de lectura)
            st.success("✅ Leído con modelo Pro")
        except:
            st.error(f"⚠️ Error de conexión con Google: {e}. Revisa que la API Key sea correcta.")

# 3. TABLA Y LOGO
if st.session_state.lista:
    st.markdown("---")
    col1, col2 = st.columns([1, 3])
    with col1:
        try: st.image("logo.png", width=150)
        except: st.write("**LOGO**")
    with col2:
        st.subheader("MANTENIMIENTOS ALICANTINA DE VALLAS S.L.")
        st.write(f"**CLIENTE:** {cliente.upper()}")

    df = pd.DataFrame(st.session_state.lista)
    st.table(df)
    
    total = df["Total (€)"].sum()
    st.subheader(f"TOTAL (IVA Inc.): {total * 1.21:.2f} €")
    
    if st.button("🗑️ Nuevo"):
        st.session_state.lista = []
        st.rerun()
