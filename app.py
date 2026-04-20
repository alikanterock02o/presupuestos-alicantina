import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Alicantina de Vallas - Diagnóstico")

st.title("🕵️‍♂️ Diagnóstico de Conexión")
api_key = st.secrets["GEMINI_API_KEY"]

if st.button("🔎 Verificar mis modelos disponibles"):
    # Esta es la llamada que nos pide el error 404
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        response = requests.get(url)
        res = response.json()
        
        if 'models' in res:
            st.success("✅ ¡Conectado! Estos son tus modelos disponibles:")
            modelos = [m['name'] for m in res['models']]
            st.write(modelos)
            
            # Buscamos si tienes algún 'flash' disponible
            flash_disponible = next((m for m in modelos if 'flash' in m), None)
            if flash_disponible:
                st.info(f"Sugerencia: Usa el nombre exacto '{flash_disponible}'")
        else:
            st.error(f"❌ Google no devuelve modelos. Respuesta: {res}")
    except Exception as e:
        st.error(f"Error de red: {e}")

st.divider()
st.write("Si no aparece ningún modelo con '1.5-flash', el problema es la región o la configuración de tu cuenta en Google AI Studio.")
