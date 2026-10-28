"""
COMPARADOR COMPETITIVO SODIMAC
Pantalla principal (hecha con Streamlit).
"""

import io
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import streamlit as st

import motor
import vista
from competidores import COMPETIDORES

st.set_page_config(page_title="Comparador Competitivo Sodimac", page_icon="🏠", layout="wide",
                   initial_sidebar_state="collapsed")
st.markdown(vista.CSS, unsafe_allow_html=True)


def secreto(nombre):
    try:
        return st.secrets.get(nombre)
    except Exception:
        return None


def clave_ia():
    return secreto("GEMINI_API_KEY")


# ---------------------------------------------------------------------------
# Búsquedas (con memoria de 1 hora para no repetir consultas)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def comparar_sku(sku, competidores_elegidos, clave):
    """Devuelve (sodimac, error, filas, aviso)."""
    sodimac, error = motor.leer_sodimac(sku)
    if error:
        return None, error, {}, ""
    if clave:
        filas, aviso = motor.comparar_con_ia(sodimac, list(competidores_elegidos), COMPETIDORES, clave)
        return sodimac, None, filas, aviso

    def tarea(nombre):
        try:
            res, err, nota = motor.mejores_equivalentes(sodimac, nombre, COMPETIDORES[nombre], None, 1)
        except Exception as e:  # que un sitio roto no frene a los demás
            res, err, nota = None, f"Error inesperado: {type(e).__name__}", ""
        if err:
            return nombre, motor.fila_resultado(sodimac, nombre, error=err)
        return nombre, motor.fila_resultado(sodimac, nombre, res[0] if res else None, nota=nota)

    with ThreadPoolExecutor(max_workers=6) as pool:
        filas = dict(pool.map(tarea, competidores_elegidos))
    return sodimac, None, filas, ""


# ---------------------------------------------------------------------------
# Archivos
# ---------------------------------------------------------------------------

def leer_skus(archivo, texto):
    valores = []
    if archivo is not None:
        try:
            if archivo.name.lower().endswith(".csv"):
                df = pd.read_csv(archivo, dtype=str, header=None, sep=None, engine="python")
            else:
                df = pd.read_excel(archivo, dtype=str, header=None)
            valores += df.iloc[:, 0].dropna().tolist()
        except Exception:
            st.error("No pude leer el archivo. Usá la plantilla de ejemplo.")
    valores += (texto or "").replace(",", "\n").replace(";", "\n").split()
    skus = []
    for v in valores:
        v = str(v).strip().split(".")[0]  # Excel a veces guarda 8993300 como 8993300.0
        if v.isdigit() and v not in skus:
            skus.append(v)
    return skus


@st.cache_data
def plantilla_excel():
    salida = io.BytesIO()
    pd.DataFrame({"SKU": ["8993300", "9207228"],
                  "Descripción (opcional)": ["Sillón individual reclinable negro", ""],
                  "Categoría (opcional)": ["Living > Sillones", ""]}).to_excel(salida, index=False)
    return salida.getvalue()


def excel_resultados(resultados):
    filas = [f for r in resultados for f in r["filas"].values()]
    df = pd.DataFrame(filas).drop(columns=["Imagen"], errors="ignore")
    salida = io.BytesIO()
    with pd.ExcelWriter(salida, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Comparación")
        hoja = writer.sheets["Comparación"]
        for columna in hoja.columns:
            ancho = max(len(str(c.value or "")) for c in columna[:50])
            hoja.column_dimensions[columna[0].column_letter].width = min(max(ancho + 2, 10), 60)
    return salida.getvalue()


# ---------------------------------------------------------------------------
# Pantalla
# ---------------------------------------------------------------------------

st.markdown(vista.encabezado(), unsafe_allow_html=True)

for n in COMPETIDORES:
    st.session_state.setdefault(f"comp_{n}", n in ("Easy", "Fravega"))

col1, col2, col3 = st.columns([1, 1.35, 1], gap="medium")

with col1, st.container(border=True):
    st.markdown(vista.titulo_paso(1, "Cargar SKUs de Sodimac",
                                  "Subí un archivo con los SKUs o ingresalos manualmente."), unsafe_allow_html=True)
    archivo = st.file_uploader("Arrastrá un archivo Excel o CSV", type=["xlsx", "xls", "csv"],
                               help="Formato: SKU | Descripción (opcional) | Categoría (opcional)")
    st.download_button("⬇ Descargar plantilla de ejemplo", plantilla_excel(), file_name="plantilla_skus.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with st.expander("✏️ Ingresar SKUs manualmente"):
        texto = st.text_area("Un SKU por línea", placeholder="8993300\n9207228", label_visibility="collapsed")
    skus = leer_skus(archivo, texto)
    if skus:
        a, b = st.columns([3, 1])
        a.markdown(f"✅ **{len(skus)} SKU{'s' if len(skus) != 1 else ''} cargado{'s' if len(skus) != 1 else ''} "
                   f"correctamente**")
        with b.popover("Ver lista"):
            st.write(", ".join(skus))

with col2, st.container(border=True):
    st.markdown(vista.titulo_paso(2, "Seleccionar competidores",
                                  "Elegí en qué tiendas online buscar productos comparables."), unsafe_allow_html=True)
    nombres = list(COMPETIDORES)
    grilla = st.columns(3)
    for i, n in enumerate(nombres):
        color = COMPETIDORES[n].get("color_casilla", "gray")
        grilla[i % 3].checkbox(f":{color}[●] {n}", key=f"comp_{n}")
    elegidos = [n for n in nombres if st.session_state[f"comp_{n}"]]
    def marcar_todos(valor):
        for nom in nombres:
            st.session_state[f"comp_{nom}"] = valor

    t1, t2 = st.columns(2)
    t1.button("Tildar todos", use_container_width=True, on_click=marcar_todos, args=(True,))
    t2.button("Destildar todos", use_container_width=True, on_click=marcar_todos, args=(False,))

with col3, st.container(border=True):
    st.markdown(vista.titulo_paso(3, "Buscar productos comparables",
                                  "La herramienta buscará productos equivalentes en las tiendas seleccionadas "
                                  "según la ficha técnica."), unsafe_allow_html=True)
    st.write("")
    buscar = st.button("🔍  Buscar productos comparables", type="primary", use_container_width=True,
                       disabled=not (skus and elegidos))
    if clave_ia():
        st.caption("🤖 Comparación inteligente con IA: **activada**")
    else:
        st.caption("⚠️ IA desactivada: la comparación es solo por nombre. Ver LEEME para activarla.")
    if not skus:
        st.caption("Cargá al menos un SKU para empezar.")
    elif not elegidos:
        st.caption("Tildá al menos un competidor.")
    zona_progreso = st.empty()

if buscar:
    resultados, errores = [], []
    barra = zona_progreso.progress(0.0, text="Arrancando…")
    for i, sku in enumerate(skus):
        barra.progress(i / len(skus), text=f"SKU {sku} ({i + 1} de {len(skus)})…")
        sodimac, error, filas, aviso = comparar_sku(sku, tuple(elegidos), clave_ia())
        if error:
            errores.append(error)
        else:
            resultados.append({"sodimac": sodimac, "filas": filas})
            if aviso and aviso not in errores:
                errores.append(f"Aviso de la IA (SKU {sku}): {aviso}. Se usó el método simple donde hizo falta.")
    barra.progress(1.0, text="¡Listo!")
    st.session_state["resultados"] = resultados
    st.session_state["columnas"] = list(elegidos)
    st.session_state["errores"] = errores

resultados = st.session_state.get("resultados")
if resultados is not None:
    st.write("")
    for e in st.session_state.get("errores", []):
        st.warning(e)
    if resultados:
        izq, der = st.columns([5, 1])
        izq.markdown(f'<div class="res-cab">Resultados ({len(resultados)} SKU{"s" if len(resultados) != 1 else ""})</div>',
                     unsafe_allow_html=True)
        der.download_button("📗 Exportar a Excel", excel_resultados(resultados), file_name="comparacion_precios.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True)
        st.markdown(vista.tabla_resultados(resultados, st.session_state["columnas"], COMPETIDORES),
                    unsafe_allow_html=True)

st.write("")
with st.expander("🛠 Diagnóstico de competidores (usalo si algún sitio no trae resultados)"):
    st.write("Hace la búsqueda completa de un SKU en los competidores tildados y genera un **detalle técnico** "
             "que podés copiar y mandarle a Claude para ajustar los sitios que fallen.")
    d1, d2 = st.columns([1, 1])
    sku_prueba = d1.text_input("SKU de prueba", value=skus[0] if skus else "8993300")
    if d2.button("🧹 Borrar resultados guardados",
                 help="El programa guarda los resultados 1 hora. Tocá acá para forzar una búsqueda nueva."):
        st.cache_data.clear()
        st.session_state.pop("resultados", None)
        st.success("Listo, la próxima búsqueda va a consultar todo de nuevo.")
    if st.button("Probar competidores tildados"):
        motor.REGISTRO.clear()
        with st.spinner("Leyendo Sodimac…"):
            p, err = motor.leer_sodimac(sku_prueba)
        if err:
            st.error(f"Sodimac: {err}")
        else:
            st.success(f"Sodimac: {p['nombre']} — normal {vista.pesos(p['precio_normal']) or '?'} / promo "
                       f"{vista.pesos(p['precio_promo']) or '-'} — marca {p['marca'] or '?'} — "
                       f"modelo {p['modelo'] or '?'} — {len(p['ficha'])} datos de ficha técnica")
            with st.spinner("Buscando en los competidores…"):
                if clave_ia():
                    filas, aviso = motor.comparar_con_ia(p, elegidos, COMPETIDORES, clave_ia())
                    if aviso:
                        st.warning(f"IA: {aviso}")
                else:
                    filas = {}
                    for nombre in elegidos:
                        res, err, nota = motor.mejores_equivalentes(p, nombre, COMPETIDORES[nombre], None, 1)
                        filas[nombre] = (motor.fila_resultado(p, nombre, error=err) if err else
                                         motor.fila_resultado(p, nombre, res[0] if res else None, nota=nota))
            for nombre, f in filas.items():
                if f["Coincidencia"] == "Error":
                    st.error(f"{nombre}: no funciona — {f['Por qué']}")
                elif f["Puntaje"] is None:
                    st.warning(f"{nombre}: sin equivalente — {f['Por qué']}")
                else:
                    st.success(f"{nombre}: {f['Producto competidor']} — "
                               f"{vista.pesos(f['Precio promo'] or f['Precio normal'])} — {f['Coincidencia']} "
                               f"({f['Puntaje']}) — {f['Por qué']}")
        st.caption("Detalle técnico (copialo con el botón de la esquina y pegáselo a Claude):")
        st.code("\n".join(motor.REGISTRO) or "(vacío)", language=None)
