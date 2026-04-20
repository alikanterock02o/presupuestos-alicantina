import json
import re
import streamlit as st
import pandas as pd
from google import genai
from fpdf import FPDF
import PyPDF2
import PIL.Image

st.set_page_config(page_title="Alicantina de Vallas - Gestor", layout="wide")

# =====================================
# 1. CONFIGURACIÓN API
# =====================================
if "GEMINI_API_KEY" not in st.secrets:
    st.error("⚠️ Falta la API KEY en Secrets.")
    st.stop()


# =====================================
# 2. LÓGICA DE MÁRGENES
# =====================================
def calcular_margen_por_total(total_linea_coste):
    if total_linea_coste <= 0.05:
        return 3.0
    elif total_linea_coste <= 0.25:
        return 2.5
    elif total_linea_coste <= 1.0:
        return 2.0
    elif total_linea_coste <= 3.0:
        return 1.75
    elif total_linea_coste <= 10.0:
        return 1.50
    elif total_linea_coste <= 50.0:
        return 1.43
    elif total_linea_coste <= 300.0:
        return 1.35
    elif total_linea_coste <= 1000.0:
        return 1.29
    else:
        return 1.25


def calcular_pvp_unitario(coste_unitario, cantidad):
    total_linea_coste = coste_unitario * cantidad
    margen = calcular_margen_por_total(total_linea_coste)
    return coste_unitario * margen, margen


# =====================================
# 3. UTILIDADES DE LIMPIEZA
# =====================================
def limpiar_numero(valor):
    """
    Convierte:
    '1,25 €' -> 1.25
    '1.234,56 €' -> 1234.56
    '€3,50' -> 3.50
    '2 uds' -> 2
    """
    if valor is None:
        raise ValueError("Valor vacío")

    valor = str(valor).strip()
    valor = valor.replace("€", "").replace("EUR", "").replace("eur", "")
    valor = valor.replace(" ", "")
    valor = re.sub(r"[^0-9,.\-]", "", valor)

    if not valor:
        raise ValueError("No se pudo interpretar el número")

    if "," in valor and "." in valor:
        valor = valor.replace(".", "").replace(",", ".")
    elif "," in valor:
        valor = valor.replace(",", ".")

    return float(valor)


def limpiar_texto_pdf(texto):
    if not texto:
        return ""
    texto = texto.replace("\x00", " ")
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def extraer_json_desde_texto(texto):
    texto = texto.strip()

    try:
        return json.loads(texto)
    except Exception:
        pass

    inicio = texto.find("{")
    fin = texto.rfind("}")

    if inicio != -1 and fin != -1 and fin > inicio:
        posible_json = texto[inicio:fin + 1]
        return json.loads(posible_json)

    raise ValueError("No se encontró un JSON válido en la respuesta del modelo.")


# =====================================
# 4. EXTRACCIÓN CON GEMINI
# =====================================
def analizar_documento(archivo):
    client = genai.Client(
        api_key=st.secrets["GEMINI_API_KEY"],
        http_options={"api_version": "v1"}
    )

    prompt = """
Extrae los productos del documento y devuelve SOLO un JSON válido.
No añadas explicación, no uses markdown, no pongas ```json.

Formato exacto esperado:
{
  "items": [
    {
      "descripcion": "texto",
      "cantidad": 1,
      "precio_coste": 0.0
    }
  ]
}

Reglas:
- Devuelve solo productos reales
- "cantidad" debe ser numérica
- "precio_coste" debe ser el coste unitario
- Si una línea no está clara, omítela
- No incluyas totales generales, portes, IVA, descuentos globales ni comentarios
- No devuelvas texto fuera del JSON
"""

    try:
        if archivo.type == "application/pdf":
            reader = PyPDF2.PdfReader(archivo)
            paginas_texto = [(pagina.extract_text() or "") for pagina in reader.pages]
            texto = limpiar_texto_pdf(" ".join(paginas_texto))

            if not texto:
                return {
                    "ok": False,
                    "error": "No se pudo extraer texto del PDF. Puede ser un PDF escaneado como imagen."
                }

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt + "\n\nDOCUMENTO:\n" + texto
            )

        else:
            img = PIL.Image.open(archivo)

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[prompt, img]
            )

        texto_respuesta = getattr(response, "text", None)

        if not texto_respuesta:
            return {
                "ok": False,
                "error": "El modelo no devolvió una respuesta válida."
            }

        data = extraer_json_desde_texto(texto_respuesta)

        if "items" not in data or not isinstance(data["items"], list):
            return {
                "ok": False,
                "error": "El JSON devuelto no contiene la clave 'items' correctamente."
            }

        return {
            "ok": True,
            "data": data,
            "raw": texto_respuesta
        }

    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }


# =====================================
# 5. NORMALIZAR ITEMS
# =====================================
def normalizar_items(items):
    datos = []
    errores = []

    for item in items:
        try:
            descripcion = str(item.get("descripcion", "")).strip()
            cantidad = limpiar_numero(item.get("cantidad"))
            precio_coste = limpiar_numero(item.get("precio_coste"))

            if not descripcion:
                errores.append(f"Item sin descripción: {item}")
                continue

            if cantidad <= 0:
                errores.append(f"Cantidad inválida en item: {item}")
                continue

            if precio_coste < 0:
                errores.append(f"Precio de coste inválido en item: {item}")
                continue

            pvp_unitario, margen = calcular_pvp_unitario(precio_coste, cantidad)
            total_linea = pvp_unitario * cantidad
            total_coste_linea = precio_coste * cantidad

            datos.append({
                "Descripción": descripcion,
                "Cant": int(round(cantidad)),
                "Coste Ud (€)": round(precio_coste, 2),
                "Total Coste (€)": round(total_coste_linea, 2),
                "Margen": round(margen, 2),
                "PVP Ud (€)": round(pvp_unitario, 2),
                "Total (€)": round(total_linea, 2),
            })

        except Exception as e:
            errores.append(f"No se pudo normalizar item {item}: {e}")

    return datos, errores


# =====================================
# 6. RECÁLCULO DESDE TABLA EDITADA
# =====================================
def recalcular_dataframe(df):
    filas = []

    for _, row in df.iterrows():
        try:
            descripcion = str(row["Descripción"]).strip()
            cantidad = limpiar_numero(row["Cant"])
            coste_ud = limpiar_numero(row["Coste Ud (€)"])

            if not descripcion:
                continue
            if cantidad <= 0:
                continue
            if coste_ud < 0:
                continue

            pvp_ud, margen = calcular_pvp_unitario(coste_ud, cantidad)
            total_coste = coste_ud * cantidad
            total = pvp_ud * cantidad

            filas.append({
                "Descripción": descripcion,
                "Cant": int(round(cantidad)),
                "Coste Ud (€)": round(coste_ud, 2),
                "Total Coste (€)": round(total_coste, 2),
                "Margen": round(margen, 2),
                "PVP Ud (€)": round(pvp_ud, 2),
                "Total (€)": round(total, 2),
            })
        except Exception:
            continue

    return pd.DataFrame(filas)


# =====================================
# 7. PDF
# =====================================
class PDFPresupuesto(FPDF):
    def header(self):
        self.set_font("Arial", "B", 15)
        self.cell(0, 10, "PRESUPUESTO", ln=True, align="C")
        self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Pagina {self.page_no()}", align="C")


def texto_seguro_pdf(texto):
    texto = str(texto)
    reemplazos = {
        "€": "EUR",
        "–": "-",
        "—": "-",
        "´": "'",
        "`": "'",
        "“": '"',
        "”": '"',
        "ñ": "n",
        "Ñ": "N",
    }
    for k, v in reemplazos.items():
        texto = texto.replace(k, v)
    return texto.encode("latin-1", "replace").decode("latin-1")


def generar_pdf(nombre_cliente, df, aplicar_iva=False):
    pdf = PDFPresupuesto()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, texto_seguro_pdf(f"Cliente: {nombre_cliente}"), ln=True)
    pdf.ln(4)

    pdf.set_font("Arial", "B", 9)
    pdf.cell(80, 8, "Descripcion", border=1)
    pdf.cell(18, 8, "Cant", border=1, align="C")
    pdf.cell(30, 8, "PVP Ud", border=1, align="C")
    pdf.cell(30, 8, "Total", border=1, ln=True, align="C")

    pdf.set_font("Arial", "", 8)

    subtotal = 0.0

    for _, row in df.iterrows():
        descripcion = texto_seguro_pdf(str(row["Descripción"])[:48])
        cantidad = str(row["Cant"])
        pvp_ud = f'{float(row["PVP Ud (€)"]):.2f}'
        total_linea = f'{float(row["Total (€)"]):.2f}'

        pdf.cell(80, 8, descripcion, border=1)
        pdf.cell(18, 8, cantidad, border=1, align="C")
        pdf.cell(30, 8, pvp_ud, border=1, align="C")
        pdf.cell(30, 8, total_linea, border=1, ln=True, align="C")

        subtotal += float(row["Total (€)"])

    iva = subtotal * 0.21 if aplicar_iva else 0.0
    total_final = subtotal + iva

    pdf.ln(4)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, texto_seguro_pdf(f"Subtotal: {subtotal:.2f} EUR"), ln=True, align="R")

    if aplicar_iva:
        pdf.cell(0, 8, texto_seguro_pdf(f"IVA 21%: {iva:.2f} EUR"), ln=True, align="R")

    pdf.cell(0, 10, texto_seguro_pdf(f"TOTAL PRESUPUESTO: {total_final:.2f} EUR"), ln=True, align="R")

    return pdf.output(dest="S").encode("latin-1")


# =====================================
# 8. INTERFAZ
# =====================================
st.title("🏗️ Alicantina de Vallas - Gestor de Presupuestos")
st.caption("Convierte presupuestos de proveedor en presupuestos para cliente final con tu tabla de márgenes.")

col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    nombre_cliente = st.text_input("👤 Cliente", value="David")

with col2:
    aplicar_iva = st.checkbox("Añadir IVA 21%", value=False)

with col3:
    st.write("")
    if st.button("♻️ Reiniciar", use_container_width=True):
        st.session_state.clear()
        st.rerun()

archivo = st.file_uploader(
    "📄 Sube presupuesto del proveedor o una foto",
    type=["pdf", "jpg", "jpeg", "png"]
)

if archivo and st.button("🚀 Procesar documento", use_container_width=True):
    with st.spinner("Analizando documento..."):
        resultado = analizar_documento(archivo)

        if not resultado["ok"]:
            st.error(f"Error al analizar el documento: {resultado['error']}")
        else:
            datos, errores = normalizar_items(resultado["data"]["items"])
            st.session_state["datos"] = datos
            st.session_state["errores"] = errores
            st.session_state["salida_cruda"] = resultado["raw"]


# =====================================
# 9. RESULTADOS
# =====================================
if "salida_cruda" in st.session_state:
    with st.expander("Ver respuesta cruda del modelo"):
        st.code(st.session_state["salida_cruda"], language="json")

if "errores" in st.session_state and st.session_state["errores"]:
    with st.expander("Ver incidencias detectadas"):
        for err in st.session_state["errores"]:
            st.warning(err)

if "datos" in st.session_state and st.session_state["datos"]:
    st.subheader("Líneas del presupuesto")

    df_inicial = pd.DataFrame(st.session_state["datos"])
    columnas_editables = ["Descripción", "Cant", "Coste Ud (€)"]
    df_editable = df_inicial[columnas_editables].copy()

    df_editado = st.data_editor(
        df_editable,
        use_container_width=True,
        num_rows="dynamic",
        key="editor_presupuesto"
    )

    df_final = recalcular_dataframe(df_editado)

    if not df_final.empty:
        subtotal = float(df_final["Total (€)"].sum())
        iva = round(subtotal * 0.21, 2) if aplicar_iva else 0.0
        total_final = subtotal + iva

        st.subheader("Resultado recalculado")
        st.dataframe(df_final, use_container_width=True)

        c1, c2, c3 = st.columns(3)
        c1.metric("Subtotal", f"{subtotal:.2f} €")
        c2.metric("IVA", f"{iva:.2f} €")
        c3.metric("Total final", f"{total_final:.2f} €")

        pdf_bytes = generar_pdf(nombre_cliente, df_final, aplicar_iva=aplicar_iva)

        st.download_button(
            "📥 Descargar presupuesto PDF",
            data=pdf_bytes,
            file_name=f"Presupuesto_{nombre_cliente}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    else:
        st.warning("No hay líneas válidas para recalcular.")

elif "datos" in st.session_state and not st.session_state["datos"]:
    st.warning("No se pudieron extraer productos válidos del documento.")
