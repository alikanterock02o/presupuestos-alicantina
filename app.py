import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
import io

# CONFIGURACIÓN
st.set_page_config(page_title="Alicantina de Vallas - Smart", page_icon="🏗️", layout="wide")

# MÁRGENES
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

# INICIALIZAR IA
# --- INICIALIZAR IA CON PRUEBA DE MODELOS ---
try:
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("❌ No he encontrado la clave API en los Secrets.")
    else:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        
        # Probamos los 3 nombres posibles por orden de modernidad
        modelos_a_probar = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro-vision']
        model = None
        
        for nombre in modelos_a_probar:
            try:
                model = genai.GenerativeModel(nombre)
                # Prueba rápida para ver si el modelo responde
                st.write(f"🟢 Conectado con: {nombre}")
                break
            except:
                continue
        
        if model is None:
            st.error("❌ Ninguno de los modelos de Google está disponible con tu clave.")
except Exception as e:
    st.error(f"❌ Error crítico: {e}")

st.title("🏗️ Generador Automático de Presupuestos")
st.write("Mantenimientos Alicantina de Vallas S.L.")

cliente = st.text_input("👤 Nombre del Cliente Final")

if 'lista' not in st.session_state: 
    st.session_state.lista = []

# SUBIDA DE FOTO
foto = st.file_uploader("📷 Sube la foto del albarán", type=['jpg', 'png', 'jpeg'])

if foto and st.button("🔍 Analizar Albarán"):
    try:
        with st.spinner('Leyendo imagen con IA...'):
            img = Image.open(foto)
            # Convertir a RGB por si es un PNG con transparencia
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            prompt = "Analiza este albarán. Extrae productos en este formato: NOMBRE | CANTIDAD | PRECIO_COSTE. Usa punto para decimales."
            response = model.generate_content([prompt, img])
            
            # Limpiar lista antes de nueva lectura si quieres, o dejar que acumule
            lineas = response.text.split('\n')
            for linea in lineas:
                if '|' in linea:
                    p = linea.split('|')
                    try:
                        desc = p[0].strip()
                        cant = int(float(p[1].strip()))
                        coste = float(p[2].strip().replace('€', '').replace('$', ''))
                        pvp = calcular_pvp(coste)
                        st.session_state.lista.append({
                            "Descripción": desc, "Cant": cant, 
                            "Precio Ud. (€)": round(pvp, 2), "Total (€)": round(pvp * cant, 2)
                        })
                    except: continue
            st.success("¡Lectura completada!")
    except Exception as e:
        st.error(f"⚠️ La IA ha tenido un problema: {e}")

# TABLA Y PDF
if st.session_state.lista:
    st.write(f"### Presupuesto: {cliente}")
    df = pd.DataFrame(st.session_state.lista)
    st.table(df)
    
    base = df["Total (€)"].sum()
    st.subheader(f"TOTAL (IVA Inc.): {base * 1.21:.2f} €")
    
    if st.button("🗑️ Limpiar"):
        st.session_state.lista = []
        st.rerun()
