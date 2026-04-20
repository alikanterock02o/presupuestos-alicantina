import streamlit as st
import pandas as pd

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Presupuestos Alicantina", page_icon="🏗️")

# 2. LÓGICA DE MÁRGENES (SEGÚN TU TABLA REAL)
def calcular_pvp(coste):
    if coste <= 0.05: return coste * 3.0
    elif coste <= 0.25: return coste * 2.5
    elif coste <= 1.0: return coste * 2.0
    elif coste <= 3.0: return coste * 1.75
    elif coste <= 10.0: return coste * 1.50  # Margen 50%
    elif coste <= 50.0: return coste * 1.43  # Margen 43%
    elif coste <= 300.0: return coste * 1.35 # Margen 35%
    elif coste <= 1000.0: return coste * 1.29 # Margen 29%
    elif coste <= 3000.0: return coste * 1.25 # Margen 25%
    else: return coste * 1.20                  # Margen 20%

# 3. INTERFAZ
st.title("🏗️ Generador de Presupuestos")
st.write("Mantenimientos Alicantina de Vallas S.L.")

# Inicializar lista si está vacía
if 'lista_productos' not in st.session_state:
    st.session_state.lista_productos = []

# Formulario para añadir productos
with st.form("form_añadir", clear_on_submit=True):
    c1, c2, c3 = st.columns([3, 1, 1])
    d = c1.text_input("Producto")
    n = c2.number_input("Cant", min_value=1, value=1)
    c = c3.number_input("Coste Unit (€)", min_value=0.0, step=0.01)
    boton = st.form_submit_button("Añadir")

if boton and d:
    precio_venta = calcular_pvp(c)
    st.session_state.lista_productos.append({
        "Descripción": d,
        "Cant": n,
        "Precio Ud.": round(precio_venta, 2),
        "Total": round(precio_venta * n, 2)
    })

# 4. TABLA Y RESULTADOS
if len(st.session_state.lista_productos) > 0:
    df = pd.DataFrame(st.session_state.lista_productos)
    st.table(df)
    
    subtotal = df["Total"].sum()
    iva = subtotal * 0.21
    st.write(f"**Base:** {subtotal:.2f}€ | **IVA:** {iva:.2f}€")
    st.success(f"### TOTAL: {subtotal + iva:.2f}€")
    
    if st.button("Borrar todo"):
        st.session_state.lista_productos = []
        st.rerun()
else:
    st.info("Introduce un producto para empezar.")
