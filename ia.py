"""
IA PARA COMPARAR PRODUCTOS (Google Gemini, versión gratuita)
=============================================================
La IA hace dos cosas:
  1. Inventa buenas búsquedas para cada producto, con sinónimos
     (ej.: "sillón reclinable" -> también "berger", "poltrona", "sillón relax").
  2. Lee la ficha de Sodimac y la de cada candidato, y elige el equivalente real
     en cada competidor (o dice que no hay ninguno).

Necesita una clave gratuita de Google AI Studio cargada en los "Secrets" de
Streamlit como GEMINI_API_KEY. Sin clave, el programa usa el método simple.
"""

import json
import re
import time

import requests

URL_BASE = "https://generativelanguage.googleapis.com/v1beta"
_modelo_elegido = {}


def _elegir_modelo(clave, preferido=None):
    """Elige automáticamente el mejor modelo 'Flash-Lite' disponible (el de más consultas gratis)."""
    if preferido:
        return preferido
    if clave in _modelo_elegido:
        return _modelo_elegido[clave]
    try:
        r = requests.get(f"{URL_BASE}/models", params={"key": clave, "pageSize": 200}, timeout=20)
        modelos = [m["name"].split("/")[-1] for m in r.json().get("models", [])
                   if "generateContent" in m.get("supportedGenerationMethods", [])]
    except Exception:
        modelos = []
    def version(nombre):
        m = re.search(r"gemini-(\d+(?:\.\d+)?)", nombre)
        return float(m.group(1)) if m else 0
    excluir = ("preview", "tts", "live", "image", "audio", "exp", "embedding", "transcribe", "translate")
    limpios = [m for m in modelos if not any(x in m for x in excluir)]
    lite = sorted([m for m in limpios if "flash-lite" in m], key=version, reverse=True)
    flash = sorted([m for m in limpios if "flash" in m and "lite" not in m], key=version, reverse=True)
    elegido = (lite or flash or ["gemini-flash-lite-latest"])[0]
    _modelo_elegido[clave] = elegido
    return elegido


def _preguntar(clave, prompt, modelo=None):
    """Manda el pedido a Gemini y devuelve (json_respuesta, error)."""
    nombre = _elegir_modelo(clave, modelo)
    cuerpo = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
    }
    for intento in range(3):
        try:
            r = requests.post(f"{URL_BASE}/models/{nombre}:generateContent", params={"key": clave},
                              json=cuerpo, timeout=90)
        except requests.RequestException as e:
            return None, f"IA: no se pudo conectar ({type(e).__name__})"
        if r.status_code == 429:  # demasiadas consultas: esperar y reintentar
            time.sleep(15 * (intento + 1))
            continue
        if r.status_code != 200:
            return None, f"IA ({nombre}) respondió código {r.status_code}: {r.text[:200]}"
        try:
            texto = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            texto = re.sub(r"^```(?:json)?|```$", "", texto.strip()).strip()
            return json.loads(texto), None
        except (KeyError, IndexError, ValueError) as e:
            return None, f"IA: respuesta inesperada ({type(e).__name__})"
    return None, "IA: se alcanzó el límite de consultas gratuitas (probá en un rato o mañana)"


def _ficha_corta(ficha, maximo=25):
    return "; ".join(f"{k}: {v}" for k, v in list((ficha or {}).items())[:maximo])


def generar_busquedas(clave, sodimac, modelo=None):
    prompt = f"""Sos comprador de una cadena de mejoramiento del hogar en Argentina.
Producto de Sodimac Argentina:
- Nombre: {sodimac.get('nombre')}
- Marca: {sodimac.get('marca')}
- Modelo: {sodimac.get('modelo')}
- Ficha técnica: {_ficha_corta(sodimac.get('ficha'))}

Escribí 4 búsquedas cortas (2 a 4 palabras) para encontrar este producto o uno equivalente en el buscador
de tiendas online argentinas (Easy, Frávega, Carrefour, etc.). Usá cómo lo llaman los argentinos y sinónimos
comerciales (ej.: sillón reclinable -> "berger reclinable", "sillón relax", "poltrona reclinable").
Incluí las características que lo definen (ej.: "1 cuerpo", "13 mm", "2 plazas", "4 hornallas").
No uses colores ni la marca de Sodimac. Sin tildes.
Respondé solo JSON: {{"busquedas": ["...", "...", "...", "..."]}}"""
    datos, error = _preguntar(clave, prompt, modelo)
    if error:
        return [], error
    busquedas = [str(b).strip() for b in (datos or {}).get("busquedas", []) if str(b).strip()]
    return busquedas[:4], None


def elegir_equivalentes(clave, sodimac, candidatos_por_tienda, modelo=None):
    """
    candidatos_por_tienda: {"Easy": [producto, ...], ...}
    Devuelve ({"Easy": {"indice": 2, "puntaje": 85, "motivo": "..."}, ...}, error)
    """
    bloques = []
    for tienda, lista in candidatos_por_tienda.items():
        if not lista:
            continue
        lineas = []
        for i, c in enumerate(lista):
            precio = c.get("precio_promo") or c.get("precio_normal")
            lineas.append(f"  [{i}] {c.get('nombre')} | marca: {c.get('marca') or '?'} | precio: {precio:.0f}"
                          f" | ficha: {_ficha_corta(c.get('ficha'), 12) or '-'}")
        bloques.append(f"TIENDA: {tienda}\n" + "\n".join(lineas))
    if not bloques:
        return {}, None
    precio_sod = sodimac.get("precio_promo") or sodimac.get("precio_normal") or 0
    prompt = f"""Sos analista de precios de Sodimac Argentina. Tenés que encontrar, en cada tienda de la competencia,
el producto EQUIVALENTE al de Sodimac para comparar precios.

PRODUCTO SODIMAC:
- Nombre: {sodimac.get('nombre')}
- Marca: {sodimac.get('marca')} | Modelo: {sodimac.get('modelo')} | Precio: {precio_sod:.0f}
- Ficha técnica: {_ficha_corta(sodimac.get('ficha'), 40)}

CANDIDATOS ENCONTRADOS:
{chr(10).join(bloques)}

Reglas:
- Equivalente = mismo tipo de producto, misma función y uso, tamaño/capacidad parecidos (ej.: mismo número de
  cuerpos, plazas, potencia, medidas aproximadas) y gama de precio razonable. La marca puede ser distinta.
- El nombre comercial puede variar (berger, poltrona, sillón relax pueden ser un sillón reclinable).
- Descartá lo que sea otro producto aunque comparta palabras (una reposera de jardín NO es un sillón reclinable
  de living; un sofá de 2 cuerpos NO es un sillón individual; un accesorio NO es el producto).
- Si las funciones clave difieren (ej.: con masaje vs sin masaje) podés elegirlo igual pero con puntaje menor
  y aclarándolo en el motivo.
- Si ningún candidato es razonablemente equivalente, usá indice -1.
- puntaje: 100 = mismo modelo; 80-99 = equivalente muy cercano; 60-79 = equivalente con diferencias;
  40-59 = parecido, conviene revisar.
- motivo: una frase corta en español explicando la elección o por qué no hay equivalente.

Respondé solo JSON, una entrada por cada tienda:
{{"tiendas": [{{"tienda": "Easy", "indice": 0, "puntaje": 85, "motivo": "..."}}]}}"""
    datos, error = _preguntar(clave, prompt, modelo)
    if error:
        return {}, error
    salida = {}
    for t in (datos or {}).get("tiendas", []):
        if isinstance(t, dict) and t.get("tienda") in candidatos_por_tienda:
            try:
                salida[t["tienda"]] = {"indice": int(t.get("indice", -1)), "puntaje": int(t.get("puntaje", 0)),
                                       "motivo": str(t.get("motivo", ""))[:200]}
            except (TypeError, ValueError):
                continue
    return salida, None
