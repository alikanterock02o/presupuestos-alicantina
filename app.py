import json
import re
import os
from datetime import datetime
from io import BytesIO

import streamlit as st
import pandas as pd
from google import genai
from fpdf import FPDF
import PyPDF2
import PIL.Image

st.set_page_config(
    page_title="Alicantina de Vallas - Gestor",
    layout="wide"
)

# =====================================
# 1. CONFIGURACIÓN EMPRESA
# =====================================
EMPRESA_NOMBRE = "Alicantina de Vallas"
EMPRESA_SUBTITULO = "Presupuestos"
EMPRESA_DIRECCION = "Calle Burgos 12-14, 03015, Alicante"
EMPRESA_EMAIL = "compras@alicantinadevallas.com"
EMPRESA_TELEFONO = "692 607 896"
EMPRESA_WEB = "www.alicantinadevallas.com"
LOGO_PATH = "logo.png"   # pon tu logo en la raíz del proyecto

HISTORIAL_CSV = "historial_presupuestos.csv"
os.makedirs("data", exist_ok=True)

if "GEMINI_API_KEY" not in st.secrets:
    st.error("⚠️ Falta la API KEY en Secrets.")
    st.stop()


# =====================================
# 2. CLIENTE GEMINI
# =====================================
@st.cache_resource
def get_gemini_client():
    return genai.Client(
        api_key=st.secrets["GEMINI_API_KEY"],
        http_options={"api_version": "v1"}
    )


# =====================================
# 3. LÓGICA DE MÁRGENES
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
# 4. UTILIDADES
# =====================================
def limpiar_numero(valor):
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


def generar_numero_presupuesto():
    fecha = datetime.now().strftime("%Y%m%d")
    if "contador_presupuesto" not in st.session_state:
        st.session_state["contador_presupuesto"] = 1
    return f"P-{fecha}-{st.session_state['contador_presupuesto']:03d}"


def incrementar_contador_presupuesto():
    if "contador_presupuesto" not in st.session_state:
        st.session_state["contador_presupuesto"] = 1
    st.session_state["contador_presupuesto"] += 1


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


# =====================================
# 5. EXTRACCIÓN CON GEMINI
# =====================================
def analizar_documento(archivo):
    client = get_gemini_client()

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
# 6. NORMALIZACIÓN
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


def recalcular_dataframe(df):
    filas = []

    for _, row in df.iterrows():
        try:
            descripcion = str(row["Descripción"]).strip()
            cantidad = limpiar_numero(row["Cant"])
            coste_ud = limpiar_numero(row["Coste Ud (€)"])

            if not descripcion or cantidad <= 0 or coste_ud < 0:
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
# 7. PDF COMERCIAL
# =====================================
class PDFPresupuesto(FPDF):
    def header(self):
        if os.path.exists(LOGO_PATH):
            try:
                self.image(LOGO_PATH, 10, 8, 22)
            except Exception:
                pass

        self.set_xy(35, 10)
        self.set_font("Arial", "B", 16)
        self.cell(0, 8, texto_seguro_pdf(EMPRESA_NOMBRE), ln=True)

        self.set_x(35)
        self.set_font("Arial", "", 9)
        self.cell(0, 5, texto_seguro_pdf(EMPRESA_DIRECCION), ln=True)

        self.set_x(35)
        self.cell(0, 5, texto_seguro_pdf(f"{EMPRESA_EMAIL} | {EMPRESA_TELEFONO}"), ln=True)

        self.set_x(35)
        self.cell(0, 5, texto_seguro_pdf(EMPRESA_WEB), ln=True)

        self.ln(8)

        self.set_draw_color(180, 180, 180)
        self.line(10, 35, 200, 35)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Pagina {self.page_no()}", align="C")


def generar_pdf(numero_presupuesto, fecha, nombre_cliente, df, aplicar_iva=False, observaciones=""):
    pdf = PDFPresupuesto()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=18)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, texto_seguro_pdf("PRESUPUESTO"), ln=True)
    pdf.ln(2)

    pdf.set_font("Arial", "", 10)
    pdf.cell(95, 7, texto_seguro_pdf(f"Nº presupuesto: {numero_presupuesto}"), ln=0)
    pdf.cell(95, 7, texto_seguro_pdf(f"Fecha: {fecha}"), ln=1)

    pdf.cell(0, 7, texto_seguro_pdf(f"Cliente: {nombre_cliente}"), ln=1)
    pdf.ln(4)

    pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(90, 8, "Descripcion", border=1, fill=True)
    pdf.cell(20, 8, "Cant", border=1, align="C", fill=True)
    pdf.cell(35, 8, "PVP Ud", border=1, align="C", fill=True)
    pdf.cell(35, 8, "Total", border=1, ln=True, align="C", fill=True)

    pdf.set_font("Arial", "", 8)

    subtotal = 0.0

    for _, row in df.iterrows():
        descripcion = texto_seguro_pdf(str(row["Descripción"])[:52])
        cantidad = str(row["Cant"])
        pvp_ud = f'{float(row["PVP Ud (€)"]):.2f}'
        total_linea = f'{float(row["Total (€)"]):.2f}'

        pdf.cell(90, 8, descripcion, border=1)
        pdf.cell(20, 8, cantidad, border=1, align="C")
        pdf.cell(35, 8, pvp_ud, border=1, align="C")
        pdf.cell(35, 8, total_linea, border=1, ln=True, align="C")

        subtotal += float(row["Total (€)"])

    iva = subtotal * 0.21 if aplicar_iva else 0.0
    total_final = subtotal + iva

    pdf.ln(4)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, texto_seguro_pdf(f"Subtotal: {subtotal:.2f} EUR"), ln=True, align="R")

    if aplicar_iva:
        pdf.cell(0, 7, texto_seguro_pdf(f"IVA 21%: {iva:.2f} EUR"), ln=True, align="R")

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 9, texto_seguro_pdf(f"TOTAL PRESUPUESTO: {total_final:.2f} EUR"), ln=True, align="R")

    if observaciones.strip():
        pdf.ln(8)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 7, "Observaciones:", ln=True)

        pdf.set_font("Arial", "", 9)
        pdf.multi_cell(0, 6, texto_seguro_pdf(observaciones))

    return pdf.output(dest="S").encode("latin-1")


# =====================================
# 8. EXCEL
# =====================================
def generar_excel(numero_presupuesto, fecha, nombre_cliente, df, aplicar_iva, observaciones):
    output = BytesIO()

    subtotal = float(df["Total (€)"].sum())
    iva = round(subtotal * 0.21, 2) if aplicar_iva else 0.0
    total_final = subtotal + iva

    resumen_df = pd.DataFrame([{
        "Presupuesto": numero_presupuesto,
        "Fecha": fecha,
        "Cliente": nombre_cliente,
        "Subtotal (€)": round(subtotal, 2),
        "IVA (€)": round(iva, 2),
        "Total Final (€)": round(total_final, 2),
        "Observaciones": observaciones
    }])

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Lineas")
        resumen_df.to_excel(writer, index=False, sheet_name="Resumen")

    output.seek(0)
    return output.getvalue()


# =====================================
# 9. HISTORIAL
# =====================================
def guardar_historial(numero_presupuesto, fecha, nombre_cliente, df, aplicar_iva, observaciones):
    subtotal = float(df["Total (€)"].sum())
    iva = round(subtotal * 0.21, 2) if aplicar_iva else 0.0
    total_final = subtotal + iva

    fila = pd.DataFrame([{
        "Presupuesto": numero_presupuesto,
        "Fecha": fecha,
        "Cliente": nombre_cliente,
        "Num Lineas": len(df),
        "Subtotal (€)": round(subtotal, 2),
        "IVA (€)": round(iva, 2),
        "Total Final (€)": round(total_final, 2),
        "Observaciones": observaciones
    }])

    if os.path.exists(HISTORIAL_CSV):
        historial = pd.read_csv(HISTORIAL_CSV)
        historial = pd.concat([historial, fila], ignore_index=True)
    else:
        historial = fila

    historial.to_csv(HISTORIAL_CSV, index=False)


# =====================================
# 10. INTERFAZ
# =====================================
st.title("🏗️ Alicantina de Vallas - Gestor de Presupuestos")
st.caption("Versión negocio comercial: PDF, Excel, historial y presentación profesional.")

col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

with col1:
    nombre_cliente = st.text_input("👤 Cliente", value="David")

with col2:
    aplicar_iva = st.checkbox("Añadir IVA 21%", value=False)

with col3:
    numero_presupuesto = st.text_input(
        "🧾 Nº presupuesto",
        value=st.session_state.get("numero_presupuesto", generar_numero_presupuesto())
    )

with col4:
    fecha_presupuesto = st.date_input("📅 Fecha", value=datetime.now().date())

observaciones = st.text_area(
    "📝 Observaciones",
    value="Presupuesto válido salvo error tipográfico. Material sujeto a disponibilidad.",
    height=90
)

if "numero_presupuesto" not in st.session_state:
    st.session_state["numero_presupuesto"] = numero_presupuesto

archivo = st.file_uploader(
    "📄 Sube presupuesto del proveedor o una foto",
    type=["pdf", "jpg", "jpeg", "png"]
)

col_a, col_b = st.columns(2)

with col_a:
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
                st.session_state["numero_presupuesto"] = numero_presupuesto

with col_b:
    if st.button("♻️ Reiniciar", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# =====================================
# 11. RESULTADOS
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
    df_editable = df_inicial[["Descripción", "Cant", "Coste Ud (€)"]].copy()

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

        fecha_str = fecha_presupuesto.strftime("%d/%m/%Y")

        pdf_bytes = generar_pdf(
            numero_presupuesto=numero_presupuesto,
            fecha=fecha_str,
            nombre_cliente=nombre_cliente,
            df=df_final,
            aplicar_iva=aplicar_iva,
            observaciones=observaciones
        )

        excel_bytes = generar_excel(
            numero_presupuesto=numero_presupuesto,
            fecha=fecha_str,
            nombre_cliente=nombre_cliente,
            df=df_final,
            aplicar_iva=aplicar_iva,
            observaciones=observaciones
        )

        col_pdf, col_excel, col_guardar = st.columns(3)

        with col_pdf:
            st.download_button(
                "📥 Descargar PDF",
                data=pdf_bytes,
                file_name=f"{numero_presupuesto}_{nombre_cliente}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

        with col_excel:
            st.download_button(
                "📊 Descargar Excel",
                data=excel_bytes,
                file_name=f"{numero_presupuesto}_{nombre_cliente}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        with col_guardar:
            if st.button("💾 Guardar en historial", use_container_width=True):
                guardar_historial(
                    numero_presupuesto=numero_presupuesto,
                    fecha=fecha_str,
                    nombre_cliente=nombre_cliente,
                    df=df_final,
                    aplicar_iva=aplicar_iva,
                    observaciones=observaciones
                )
                incrementar_contador_presupuesto()
                st.success("Presupuesto guardado en historial.")

        if os.path.exists(HISTORIAL_CSV):
            with st.expander("📚 Ver historial de presupuestos"):
                historial_df = pd.read_csv(HISTORIAL_CSV)
                st.dataframe(historial_df, use_container_width=True)

    else:
        st.warning("No hay líneas válidas para recalcular.")

elif "datos" in st.session_state and not st.session_state["datos"]:
    st.warning("No se pudieron extraer productos válidos del documento.")
