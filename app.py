import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
import io

# 1. CONFIGURACIÓN Y CEREBRO (GEMINI)
st.set_page_config(page_title="Alicantina de Vallas - Auto", page_icon="🏗️", layout="wide")

# Conectar con la clave que guardaste en Secrets
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.error("⚠️ Error con la clave API. Revisa los Secrets en Streamlit.")

# LÓGICA DE MÁRGENES
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

# 2. INTERFAZ DE USUARIO
st.title("🏗️ Generador Automático de Presupuestos")
st.write("Mantenimientos Alicantina de Vallas S.L.")

# Campos principales
cliente = st.text_input("👤 Nombre del Cliente Final", placeholder="Ej: Juan Pérez / Comunidad Propietarios X")

if 'lista' not in st.session_state: st.session_state.lista = []

# 3. CARGA DE FOTO Y MAGIA IA
st.subheader("📷 Subir Albarán del Proveedor")
foto = st.file_uploader("Arrastra aquí la foto o captura del presupuesto del proveedor", type=['jpg', 'png', 'jpeg'])

if foto and not st.session_state.lista:
    with st.spinner('IA analizando el albarán...'):
        img = Image.open(foto)
        # Instrucción para la IA
        prompt = """Analiza este albarán. Extrae los productos. 
        Para cada producto devuelve SOLO una línea con este formato: 
        NOMBRE | CANTIDAD | PRECIO_COSTE_UNITARIO
        Usa punto para los decimales. No escribas nada más."""
        
        response = model.generate_content([prompt, img])
        
        # Procesar la respuesta de la IA y meterla en la lista
        lineas = response.text.split('\n')
        for linea in lineas:
            if '|' in linea:
                partes = linea.split('|')
                try:
                    desc = partes[0].strip()
                    cant = int(float(partes[1].strip()))
                    coste = float(partes[2].strip())
                    pvp = calcular_pvp(coste)
                    st.session_state.lista.append({
                        "Descripción": desc,
                        "Cant": cant,
                        "Precio Ud. (€)": round(pvp, 2),
                        "Total (€)": round(pvp * cant, 2)
                    })
                except: continue
        st.success("¡Albarán procesado con éxito!")

# 4. TABLA DE RESULTADOS Y PDF
if st.session_state.lista:
    st.markdown(f"### Presupuesto para: **{cliente if cliente else '__________'}**")
    
    df = pd.DataFrame(st.session_state.lista)
    st.table(df)
    
    total_base = df["Total (€)"].sum()
    st.write(f"**Base Imponible:** {total_base:.2f} €")
    st.subheader(f"TOTAL (IVA Inc.): {total_base * 1.21:.2f} €")
    
    if st.button("🗑️ Borrar y Nuevo Presupuesto"):
        st.session_state.lista = []
        st.rerun()

    st.info("💡 Pulsa Ctrl+P para guardar como PDF.")
