import streamlit as st
import pandas as pd

# Configuración de la página
st.set_page_config(page_title="Presupuestos Alicantina", page_icon="🏗️")

# Lógica de márgenes corregida (valores de la izquierda)
def calcular_pvp(coste):
    if coste <= 0.05: return coste * 3.0
    elif coste <= 0.25: return coste * 2.5
    elif coste <= 1.0: return coste * 2.0
    elif coste <= 3.0: return coste * 1.75
    elif coste <= 10.0: return coste * 1.50  # +50%
    elif coste <= 50.0: return coste * 1.43  # +43%
    elif coste <= 300.0: return coste * 1.35 # +35%
    elif coste <= 1000.0: return coste * 1.29
    elif coste <= 3000.0: return coste * 1.25
    else: return coste * 1.20

st.title("🏗️ Generador de Presupuestos")
st.subheader("Mantenimientos Alicantina de Vallas S.L.")

# Inicializar la lista de productos si no existe
if 'items' not in st.session_state:
    st.session_state.items = []

# Formulario de entrada
with st.form("nuevo_item", clear_on_submit=True):
    col1, col2, col3 = st.columns([3, 1, 1])
    desc = col1.text_input("Descripción del producto")
    cant = col2.number_input("Cantidad", min_value=1, value=1)
    coste = col3.number_input("Coste Unitario (€)", min_value=0.0, step=0.01)
    add = st.form_submit_button("Añadir al presupuesto")

if add and desc:
    pvp_unit = calcular_pvp(coste)
    st.session_state.items.append({
        "Descripción": desc,
        "Cant": cant,
        "Precio Ud. (€)": round(pvp_unit, 2),
        "Total (€)": round(pvp_unit * cant, 2)
    })

# SOLO mostrar la tabla si hay productos (esto evita tu error actual)
if len(st.session_state.items) > 0:
    df = pd.DataFrame(st.session_state.items)
    st.table(df)
    
    base_imponible = df["Total (€)"].sum()
    iva = base_imponible * 0.21
    total = base_imponible + iva
    
    st.write(f"**Base Imponible:** {base_imponible:.2f} €")
    st.write(f"**IVA (21%):** {iva:.2f} €")
    st.success(f"### TOTAL PRESUPUESTO: {total:.2f} €")
    
    if st.button("Limpiar Presupuesto"):
        st.session_state.items = []
        st.rerun()
else:
    st.info("Añade productos arriba para empezar a generar el presupuesto.")
