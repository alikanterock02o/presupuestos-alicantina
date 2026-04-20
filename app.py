import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import os

st.set_page_config(page_title="Alicantina de Vallas", layout="wide")

# Lógica de márgenes (Alicantina de Vallas)
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

# CONFIGURACIÓN CON FORZADO DE VERSIÓN ESTABLE
if "GEMINI_API_KEY" in st.secrets:
    # Usamos el cliente directamente para evitar el error v1beta
    client = genai.GenerativeModel(
        model_name='gemini-1.5-flash'
    )
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Configura la clave en Secrets")

st.title("🏗️ Generador Automático de Presupuestos")
cliente = st.text_input("👤 Nombre del Cliente")

if 'lista' not in st.session_state:
    st.session_state.lista = []

foto = st.file_uploader("📷 Sube la foto del presupuesto", type=['jpg', 'png', 'jpeg'])

if foto and st.button("🔍 Generar Presupuesto"):
    try:
        with st.spinner('Procesando albarán...'):
            img = Image.open(foto)
            
            prompt = "Analiza este albarán. Extrae los productos en este formato: NOMBRE | CANTIDAD | PRECIO_COSTE_UNITARIO. No escribas nada más."
            
            # Forzamos la llamada a través de la API estable
            response = client.generate_content([prompt, img])
            
            if response.text:
                lineas = response.text.split('\n')
                for linea in lineas:
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
                st.success("✅ Albarán procesado con éxito")
    except Exception as e:
        # Si esto falla, nos dirá el motivo real (ubicación, cuota o clave)
        st.error(f"Detalle técnico: {e}")

if st.session_state.lista:
    st.write(f"### Presupuesto: {cliente}")
    df = pd.DataFrame(st.session_state.lista)
    st.table(df)
    total = df["Total (€)"].sum()
    st.subheader(f"TOTAL con IVA (21%): {total * 1.21:.2f} €")
    if st.button("Limpiar"):
        st.session_state.lista = []
        st.rerun()
