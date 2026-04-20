import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
import io

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Alicantina de Vallas - Smart", page_icon="🏗️", layout="wide")

# LÓGICA DE MÁRGENES (Según tus tablas)
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

# 2. CONEXIÓN CON EL CEREBRO (IA)
try:
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("❌ Falta la clave GEMINI_API_KEY en los Secrets de Streamlit.")
    else:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # Usamos 1.5-flash que es el más rápido y eficiente para leer fotos
        model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"❌ Error al conectar con la IA: {e}")

# 3. INTERFAZ DE USUARIO
st.title("🏗️ Generador Automático de Presupuestos")
st.write("Mantenimientos Alicantina de Vallas S.L.")

# Formulario inicial
with st.container():
    col_a, col_b = st.columns(2)
    with col_a:
        cliente = st.text_input("👤 Nombre del Cliente Final", placeholder="Ej: Comunidad de Propietarios Calle Burgos")
    with col_b:
        st.write(" ") # Espaciador

if 'lista' not in st.session_state:
    st.session_state.lista = []

# 4. SUBIDA Y PROCESADO DE FOTO
st.markdown("---")
foto = st.file_uploader("📷 Sube la captura del presupuesto del proveedor", type=['jpg', 'png', 'jpeg'])

if foto and st.button("🔍 Analizar y Calcular Presupuesto"):
    try:
        with st.spinner('La IA está leyendo el albarán y aplicando tus márgenes...'):
            img = Image.open(foto)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # Instrucción maestra para la IA
            prompt = """Analiza este albarán. Busca los artículos y sus precios de coste.
            Devuelve SOLO una lista con este formato exacto:
            NOMBRE DEL PRODUCTO | CANTIDAD | PRECIO COSTE UNITARIO
            No escribas nada más, solo las líneas con el símbolo |."""
            
            response = model.generate_content([prompt, img])
            
            # Procesar el texto que nos devuelve la IA
            lineas = response.text.split('\n')
            nuevos_items = []
            
            for linea in lineas:
                if '|' in linea:
                    partes = linea.split('|')
                    try:
                        desc = partes[0].strip()
                        cant = float(partes[1].strip().replace(',', '.'))
                        # Limpiamos el precio de símbolos de moneda
                        coste_str = partes[2].strip().replace('€', '').replace('$', '').replace(',', '.')
                        coste = float(coste_str)
                        
                        pvp_ud = calcular_pvp(coste)
                        nuevos_items.append({
                            "Descripción": desc,
                            "Cant": int(cant),
                            "Precio Ud. (€)": round(pvp_ud, 2),
                            "Total (€)": round(pvp_ud * cant, 2)
                        })
                    except:
                        continue
            
            if nuevos_items:
                st.session_state.lista = nuevos_items
                st.success(f"✅ ¡Hecho! He detectado {len(nuevos_items)} productos.")
            else:
                st.warning("⚠️ No he podido extraer datos claros de la foto. Intenta que se vea bien el precio.")

    except Exception as e:
        st.error(f"⚠️ Error al procesar la imagen: {e}")

# 5. TABLA FINAL Y GENERACIÓN DE "PDF"
if st.session_state.lista:
    st.markdown("---")
    # Cabecera profesional del presupuesto
    c1, c2 = st.columns([1, 3])
    with c1:
        try:
            st.image("logo.png", width=150)
        except:
            st.write("**LOGO**")
    with c2:
        st.subheader("MANTENIMIENTOS ALICANTINA DE VALLAS S.L.")
        st.write(f"**PRESUPUESTO PARA:** {cliente.upper() if cliente else 'CLIENTE FINAL'}")
        st.write("Calle Burgos N12-14, 03015 Alicante | CIF: B54120274")

    df = pd.DataFrame(st.session_state.lista)
    st.table(df)
    
    # Totales
    base_imponible = df["Total (€)"].sum()
    iva = base_imponible * 0.21
    total_final = base_imponible + iva
    
    col_t1, col_t2 = st.columns([3, 1])
    with col_t2:
        st.write(f"**Base Imponible:** {base_imponible:.2f} €")
        st.write(f"**IVA (21%):** {iva:.2f} €")
        st.subheader(f"TOTAL: {total_final:.2f} €")

    if st.button("🗑️ Borrar todo y empezar nuevo"):
        st.session_state.lista = []
        st.rerun()

    st.write("---")
    st.caption("💡 Para guardar en PDF: Pulsa Ctrl+P (o Imprimir en el móvil) y elige 'Guardar como PDF'.")
