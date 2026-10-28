"""
MOTOR DEL COMPARADOR
====================
Acá está la lógica: leer Sodimac, buscar en cada competidor y comparar.
No hace falta tocar este archivo para el uso diario.
"""

import json
import re
import threading
import time
import unicodedata
from urllib.parse import quote, quote_plus, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

SODIMAC_BASE = "https://www.sodimac.com.ar"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
    ),
    "Accept-Language": "es-AR,es;q=0.9",
}

PAUSA_POR_SITIO = 1.0  # segundos entre consultas al mismo sitio (para no saturarlo)
MAX_CANDIDATOS = 6     # cuántos productos revisa por competidor

_ultimo_acceso = {}
_candado = threading.Lock()


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def _esperar_turno(url):
    host = urlparse(url).netloc
    with _candado:
        ahora = time.time()
        siguiente = max(ahora, _ultimo_acceso.get(host, 0) + PAUSA_POR_SITIO)
        _ultimo_acceso[host] = siguiente
    espera = siguiente - time.time()
    if espera > 0:
        time.sleep(espera)


def descargar(url, como_json=False, headers_extra=None):
    """Devuelve (contenido, error). Nunca lanza excepción."""
    _esperar_turno(url)
    headers = dict(HEADERS)
    if headers_extra:
        headers.update(headers_extra)
    if como_json:
        headers["Accept"] = "application/json"
    try:
        r = requests.get(url, headers=headers, timeout=20)
    except requests.RequestException as e:
        return None, f"No se pudo conectar ({type(e).__name__})"
    if r.status_code != 200:
        return None, f"El sitio respondió con código {r.status_code}"
    if como_json:
        try:
            return r.json(), None
        except ValueError:
            return None, "La respuesta no era JSON"
    return r.text, None


def precio_a_numero(valor):
    """Convierte '$ 1.234.567,89', '999.999', 489300 o '999999.00' en número."""
    if valor is None:
        return None
    if isinstance(valor, (int, float)):
        return float(valor) if valor > 0 else None
    if isinstance(valor, list):
        valor = valor[0] if valor else None
        return precio_a_numero(valor)
    s = str(valor)
    s = re.sub(r"[^\d.,]", "", s)
    if not s:
        return None
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", s):
        s = s.replace(".", "")
    try:
        n = float(s)
    except ValueError:
        return None
    return n if n > 0 else None


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", texto.lower()).strip()


PALABRAS_VACIAS = {
    "de", "la", "el", "los", "las", "con", "para", "y", "en", "por", "un", "una",
    "x", "a", "del", "al", "sin", "cm", "mm", "kg", "nuevo", "oferta", "envio", "gratis",
}


def palabras_clave(texto):
    return [p for p in normalizar(texto).split() if p not in PALABRAS_VACIAS and len(p) > 1]


UNIDADES = r"(cm|mm|mts?|m|kg|gr?|lts?|litros?|l|w|watts?|v|volts?|hp|cc|btu|frigorias|pulgadas|pulg|m2|amp|a)"


def medidas(texto):
    """Extrae medidas/potencias del texto: {'91cm', '18v', '1500w', '91x101x94'}."""
    t = normalizar(texto)
    encontradas = set()
    for m in re.finditer(r"\b(\d+(?:\s\d+)?)\s?" + UNIDADES + r"\b", t):
        numero = m.group(1).replace(" ", ".")
        unidad = m.group(2)
        unidad = {"mts": "m", "mt": "m", "lts": "l", "lt": "l", "litros": "l", "litro": "l",
                  "watts": "w", "watt": "w", "volts": "v", "pulg": "pulgadas", "gr": "g"}.get(unidad, unidad)
        encontradas.add(f"{numero}{unidad}")
    for m in re.finditer(r"\b(\d+)\s?x\s?(\d+)(?:\s?x\s?(\d+))?\b", t):
        partes = [g for g in m.groups() if g]
        encontradas.add("x".join(partes))
        encontradas.update(f"{n}cm" for n in partes)  # "91x101x94" también cuenta como 91cm, 101cm, 94cm
    return encontradas


def texto_cuotas(texto):
    """Busca en el texto de una página la mejor oferta de cuotas sin interés."""
    t = normalizar(texto)
    sin_interes = [int(n) for n in re.findall(r"\b(\d{1,2})\s+cuotas\s+sin\s+interes", t)]
    sin_interes += [int(n) for n in re.findall(r"hasta\s+(\d{1,2})\s+cuotas", t)]
    sin_interes = [n for n in sin_interes if 1 < n <= 36]
    if sin_interes:
        return f"Hasta {max(sin_interes)} cuotas sin interés"
    if "cuotas sin interes" in t:
        return "Cuotas sin interés"
    if "cuotas" in t:
        return "Con cuotas"
    return ""


def producto_vacio(tienda):
    return {
        "tienda": tienda, "nombre": "", "marca": "", "modelo": "",
        "precio_normal": None, "precio_promo": None, "cuotas": "",
        "imagen": "", "link": "", "ficha": {},
    }


def _ordenar_precios(p):
    """Asegura que precio_normal >= precio_promo; si son iguales deja solo el normal."""
    a, b = p.get("precio_normal"), p.get("precio_promo")
    if a and b:
        if b > a:
            a, b = b, a
        if abs(a - b) < 1:
            b = None
    elif b and not a:
        a, b = b, None
    p["precio_normal"], p["precio_promo"] = a, b
    return p


# ---------------------------------------------------------------------------
# Lectura genérica de páginas de producto (JSON-LD, tablas, etc.)
# ---------------------------------------------------------------------------

def _bloques_jsonld(soup):
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or tag.get_text() or "")
        except (ValueError, TypeError):
            continue
        pila = [data]
        while pila:
            d = pila.pop()
            if isinstance(d, list):
                pila.extend(d)
            elif isinstance(d, dict):
                yield d
                if "@graph" in d:
                    pila.append(d["@graph"])


def _jsonld_producto(soup):
    for d in _bloques_jsonld(soup):
        tipo = d.get("@type")
        tipos = tipo if isinstance(tipo, list) else [tipo]
        if "Product" in tipos:
            return d
    return None


def _ficha_desde_html(soup):
    ficha = {}
    for fila in soup.select("table tr"):
        celdas = fila.find_all(["th", "td"])
        if len(celdas) == 2:
            k, v = celdas[0].get_text(" ", strip=True), celdas[1].get_text(" ", strip=True)
            if k and v and len(k) < 60 and len(v) < 200:
                ficha[k] = v
    for dt in soup.find_all("dt"):
        dd = dt.find_next_sibling("dd")
        if dd:
            k, v = dt.get_text(" ", strip=True), dd.get_text(" ", strip=True)
            if k and v and len(k) < 60 and len(v) < 200:
                ficha[k] = v
    return dict(list(ficha.items())[:60])


def _precio_tachado(soup, precio_actual):
    """Busca un precio tachado / 'antes' mayor al precio actual."""
    candidatos = soup.find_all(["del", "s", "strike"])
    for el in soup.find_all(class_=True):
        clases = " ".join(el.get("class", [])).lower()
        if any(k in clases for k in ("list", "old", "before", "tachad", "crossed", "strike", "regular", "previous")):
            candidatos.append(el)
    for el in candidatos:
        texto = el.get_text(" ", strip=True)
        if "$" not in texto and not re.search(r"\d{1,3}\.\d{3}", texto):
            continue
        n = precio_a_numero(re.search(r"[\d.,]+", texto.replace(" ", "")).group(0)) if re.search(r"\d", texto) else None
        if n and precio_actual and n > precio_actual * 1.01 and n < precio_actual * 5:
            return n
    return None


def leer_ficha_generica(html, url, tienda):
    soup = BeautifulSoup(html, "html.parser")
    p = producto_vacio(tienda)
    p["link"] = url
    ld = _jsonld_producto(soup)
    if ld:
        p["nombre"] = ld.get("name") or ""
        marca = ld.get("brand")
        p["marca"] = (marca.get("name") if isinstance(marca, dict) else marca) or ""
        p["modelo"] = ld.get("model") if isinstance(ld.get("model"), str) else ""
        img = ld.get("image")
        if isinstance(img, list):
            img = img[0] if img else ""
        if isinstance(img, dict):
            img = img.get("url", "")
        p["imagen"] = img or ""
        ofertas = ld.get("offers") or {}
        if isinstance(ofertas, list):
            ofertas = ofertas[0] if ofertas else {}
        if isinstance(ofertas, dict) and isinstance(ofertas.get("offers"), list) and ofertas["offers"]:
            ofertas = {**ofertas["offers"][0], **{k: v for k, v in ofertas.items() if k != "offers"}}
        precio = precio_a_numero(ofertas.get("price") or ofertas.get("lowPrice"))
        p["precio_promo"] = precio
        for prop in ld.get("additionalProperty") or []:
            if isinstance(prop, dict) and prop.get("name") and prop.get("value"):
                p["ficha"][str(prop["name"])] = str(prop["value"])
    if not p["nombre"]:
        og = soup.find("meta", property="og:title")
        h1 = soup.find("h1")
        p["nombre"] = (og.get("content") if og else "") or (h1.get_text(strip=True) if h1 else "")
    if not p["imagen"]:
        og = soup.find("meta", property="og:image")
        p["imagen"] = og.get("content") if og else ""
    if not p["precio_promo"]:
        meta = soup.find("meta", property="product:price:amount") or soup.find("meta", itemprop="price")
        if meta:
            p["precio_promo"] = precio_a_numero(meta.get("content"))
    p["precio_normal"] = _precio_tachado(soup, p["precio_promo"])
    p["ficha"].update(_ficha_desde_html(soup))
    if not p["modelo"]:
        for k, v in p["ficha"].items():
            if "modelo" in normalizar(k):
                p["modelo"] = v
                break
    p["cuotas"] = texto_cuotas(soup.get_text(" ", strip=True)[:200000])
    return _ordenar_precios(p)


def _links_de_productos(html, base):
    """Encuentra links a fichas de producto dentro de una página de resultados."""
    soup = BeautifulSoup(html, "html.parser")
    host = urlparse(base).netloc.replace("www.", "")
    patrones = re.compile(r"(/p/?$|/p/|/p\?|/producto|/product/|/articulo/|/prod/|/item/|-\d{5,}\.html|\.html$)", re.I)
    vistos, links = set(), []
    for d in _bloques_jsonld(soup):
        if d.get("@type") == "ItemList":
            for el in d.get("itemListElement") or []:
                u = el.get("url") if isinstance(el, dict) else None
                if not u and isinstance(el, dict) and isinstance(el.get("item"), dict):
                    u = el["item"].get("url")
                if u and u not in vistos:
                    vistos.add(u)
                    links.append(urljoin(base, u))
    for a in soup.find_all("a", href=True):
        u = urljoin(base, a["href"].split("#")[0])
        if host not in urlparse(u).netloc:
            continue
        if patrones.search(urlparse(u).path + ("?" + urlparse(u).query if urlparse(u).query else "")) and u not in vistos:
            vistos.add(u)
            links.append(u)
    return links


# ---------------------------------------------------------------------------
# SODIMAC
# ---------------------------------------------------------------------------

def _recorrer(obj):
    pila = [obj]
    while pila:
        o = pila.pop()
        if isinstance(o, dict):
            yield o
            pila.extend(o.values())
        elif isinstance(o, list):
            pila.extend(o)


def _datos_next(soup):
    tag = soup.find("script", id="__NEXT_DATA__")
    if not tag:
        return None
    try:
        return json.loads(tag.string or tag.get_text())
    except (ValueError, TypeError):
        return None


def leer_sodimac(sku):
    """Devuelve (producto, error) para un SKU de sodimac.com.ar."""
    sku = str(sku).strip()
    url = f"{SODIMAC_BASE}/sodimac-ar/product/{sku}/"
    html, error = descargar(url)
    if not html:
        # Plan B: usar el buscador de Sodimac
        html_busqueda, error2 = descargar(f"{SODIMAC_BASE}/sodimac-ar/search?Ntt={quote_plus(sku)}")
        if html_busqueda:
            m = re.search(rf'href="([^"]*/product/{re.escape(sku)}/[^"]*)"', html_busqueda)
            if m:
                url = urljoin(SODIMAC_BASE, m.group(1))
                html, error = descargar(url)
        if not html:
            return None, f"No pude abrir el SKU {sku} en Sodimac: {error or error2}"

    p = leer_ficha_generica(html, url, "Sodimac")
    p["sku"] = sku
    soup = BeautifulSoup(html, "html.parser")
    canonical = soup.find("link", rel="canonical")
    if canonical and canonical.get("href"):
        p["link"] = canonical["href"]

    datos = _datos_next(soup)
    if datos:
        tachados, vigentes = [], []
        for d in _recorrer(datos):
            # Precios (formato de los sitios de Falabella/Sodimac)
            if isinstance(d.get("prices"), list):
                for pr in d["prices"]:
                    if not isinstance(pr, dict):
                        continue
                    valor = precio_a_numero(pr.get("price"))
                    if not valor:
                        continue
                    if pr.get("crossed") or pr.get("type") in ("normalPrice", "NORMAL_PRICE"):
                        tachados.append(valor)
                    else:
                        vigentes.append(valor)
            # Ficha técnica: listas de {name, value}
            for clave in ("specifications", "attributes", "specs", "features"):
                lista = d.get(clave)
                if isinstance(lista, list):
                    for s in lista:
                        if isinstance(s, dict):
                            k = s.get("name") or s.get("label") or s.get("key")
                            v = s.get("value") or s.get("values")
                            if isinstance(v, list):
                                v = ", ".join(str(x) for x in v)
                            if k and v and len(str(k)) < 60 and len(str(v)) < 200:
                                p["ficha"].setdefault(str(k), str(v))
        if vigentes:
            menor = min(vigentes)
            if tachados and max(tachados) > menor:
                p["precio_normal"], p["precio_promo"] = max(tachados), menor
            else:
                p["precio_normal"], p["precio_promo"] = menor, None

    if not p["modelo"]:
        for k, v in p["ficha"].items():
            if normalizar(k) == "modelo":
                p["modelo"] = v
                break
    if not p["modelo"]:
        m = re.search(r"Modelo\s*</?[^>]*>?\s*([A-Z0-9][A-Z0-9\-\./]{3,})", html)
        if m:
            p["modelo"] = m.group(1)
    if not p["nombre"]:
        return None, f"Abrí la página del SKU {sku} pero no encontré el producto (¿está publicado?)"
    return _ordenar_precios(p), None


# ---------------------------------------------------------------------------
# COMPETIDORES: VTEX
# ---------------------------------------------------------------------------

def _producto_desde_vtex(item, base, tienda):
    p = producto_vacio(tienda)
    p["nombre"] = item.get("productName") or item.get("productTitle") or ""
    p["marca"] = item.get("brand") or ""
    link = item.get("link") or ""
    if not link and item.get("linkText"):
        link = f"{base}/{item['linkText']}/p"
    p["link"] = urljoin(base, link)
    for nombre in item.get("allSpecifications") or []:
        valor = item.get(nombre)
        if isinstance(valor, list):
            valor = ", ".join(str(v) for v in valor)
        if valor:
            p["ficha"][nombre] = str(valor)
    for grupo in item.get("specificationGroups") or []:
        for s in grupo.get("specifications") or []:
            if s.get("name") and s.get("values"):
                p["ficha"].setdefault(s["name"], ", ".join(str(v) for v in s["values"]))
    for k, v in p["ficha"].items():
        if "modelo" in normalizar(k):
            p["modelo"] = v
            break

    items = item.get("items") or []
    mejor = None
    for sku in items:
        for vendedor in sku.get("sellers") or []:
            oferta = vendedor.get("commertialOffer") or vendedor.get("commercialOffer") or {}
            if not oferta.get("Price"):
                continue
            disponible = (oferta.get("AvailableQuantity") or 0) > 0 or oferta.get("IsAvailable")
            if mejor is None or (disponible and not mejor[2]):
                mejor = (sku, oferta, disponible)
    if mejor:
        sku, oferta, _ = mejor
        imgs = sku.get("images") or []
        if imgs:
            p["imagen"] = imgs[0].get("imageUrl", "")
        p["precio_promo"] = precio_a_numero(oferta.get("Price"))
        p["precio_normal"] = precio_a_numero(oferta.get("ListPrice") or oferta.get("PriceWithoutDiscount"))
        cuotas = oferta.get("Installments") or []
        sin_interes = [c.get("NumberOfInstallments", 0) for c in cuotas
                       if (c.get("InterestRate") in (0, 0.0, None)) and c.get("NumberOfInstallments", 0) > 1]
        con_interes = [c.get("NumberOfInstallments", 0) for c in cuotas if c.get("NumberOfInstallments", 0) > 1]
        if sin_interes:
            p["cuotas"] = f"Hasta {max(sin_interes)} cuotas sin interés"
        elif con_interes:
            p["cuotas"] = f"Hasta {max(con_interes)} cuotas (con interés)"
    return _ordenar_precios(p)


def buscar_vtex(base, consulta, tienda):
    """Devuelve (lista de productos, error)."""
    q = quote(consulta)
    url = f"{base}/api/catalog_system/pub/products/search?ft={q}&_from=0&_to={MAX_CANDIDATOS - 1}"
    datos, error = descargar(url, como_json=True)
    if isinstance(datos, list) and datos:
        return [_producto_desde_vtex(d, base, tienda) for d in datos], None
    # Buscador nuevo de VTEX ("intelligent search")
    url2 = f"{base}/api/io/_v/api/intelligent-search/product_search/?query={q}&count={MAX_CANDIDATOS}"
    datos2, error2 = descargar(url2, como_json=True)
    if isinstance(datos2, dict) and datos2.get("products"):
        return [_producto_desde_vtex(d, base, tienda) for d in datos2["products"][:MAX_CANDIDATOS]], None
    if isinstance(datos, list) or (isinstance(datos2, dict) and "products" in datos2):
        return [], None  # el sitio es VTEX pero no encontró nada
    return None, error or error2 or "No respondió como VTEX"


# ---------------------------------------------------------------------------
# COMPETIDORES: MERCADO LIBRE
# ---------------------------------------------------------------------------

def buscar_mercadolibre(consulta, tienda, token=None):
    url = f"https://api.mercadolibre.com/sites/MLA/search?q={quote(consulta)}&limit={MAX_CANDIDATOS}"
    extra = {"Authorization": f"Bearer {token}"} if token else None
    datos, error = descargar(url, como_json=True, headers_extra=extra)
    if isinstance(datos, dict) and "results" in datos:
        productos = []
        for r in datos["results"][:MAX_CANDIDATOS]:
            p = producto_vacio(tienda)
            p["nombre"] = r.get("title", "")
            p["link"] = r.get("permalink", "")
            p["imagen"] = (r.get("thumbnail") or "").replace("-I.jpg", "-O.jpg")
            p["precio_promo"] = precio_a_numero(r.get("price"))
            p["precio_normal"] = precio_a_numero(r.get("original_price"))
            for a in r.get("attributes") or []:
                if a.get("name") and a.get("value_name"):
                    p["ficha"][a["name"]] = a["value_name"]
                if a.get("id") == "BRAND":
                    p["marca"] = a.get("value_name") or ""
                if a.get("id") == "MODEL":
                    p["modelo"] = a.get("value_name") or ""
            cuotas = r.get("installments") or {}
            if cuotas.get("quantity"):
                tipo = "sin interés" if not cuotas.get("rate") else "con interés"
                p["cuotas"] = f"{cuotas['quantity']} cuotas {tipo}"
            if r.get("official_store_id"):
                p["ficha"]["Tienda oficial"] = "Sí"
            productos.append(_ordenar_precios(p))
        return productos, None
    # Plan B: leer la página pública de resultados
    slug = re.sub(r"\s+", "-", normalizar(consulta))
    html, error2 = descargar(f"https://listado.mercadolibre.com.ar/{slug}")
    if not html:
        return None, f"Mercado Libre no respondió ({error or error2}). Ver guía: token de Mercado Libre."
    soup = BeautifulSoup(html, "html.parser")
    productos = []
    for tarjeta in soup.select("li.ui-search-layout__item, div.poly-card")[:MAX_CANDIDATOS]:
        a = tarjeta.select_one("a.poly-component__title, h2 a, a.ui-search-link")
        if not a:
            continue
        p = producto_vacio(tienda)
        p["nombre"] = a.get_text(" ", strip=True)
        p["link"] = a.get("href", "").split("#")[0]
        img = tarjeta.find("img")
        if img:
            p["imagen"] = img.get("data-src") or img.get("src") or ""
        anterior = tarjeta.select_one("s .andes-money-amount__fraction, .andes-money-amount--previous .andes-money-amount__fraction")
        actual = tarjeta.select_one(".poly-price__current .andes-money-amount__fraction, .ui-search-price__second-line .andes-money-amount__fraction")
        p["precio_promo"] = precio_a_numero(actual.get_text() if actual else None)
        p["precio_normal"] = precio_a_numero(anterior.get_text() if anterior else None)
        p["cuotas"] = texto_cuotas(tarjeta.get_text(" ", strip=True))
        productos.append(_ordenar_precios(p))
    return productos, None


# ---------------------------------------------------------------------------
# COMPETIDORES: MÉTODO AUTOMÁTICO
# ---------------------------------------------------------------------------

def buscar_auto(config, consulta, tienda):
    base = config["sitio"].rstrip("/")
    productos, error_vtex = buscar_vtex(base, consulta, tienda)
    if productos is not None:
        return productos, None
    q = quote_plus(consulta)
    direcciones = []
    if config.get("busqueda"):
        direcciones.append(config["busqueda"].replace("{q}", q))
    direcciones += [f"{base}/search?q={q}", f"{base}/buscar?q={q}", f"{base}/busqueda?q={q}"]
    ultimo_error = error_vtex
    for direccion in direcciones:
        html, error = descargar(direccion)
        if not html:
            ultimo_error = error
            continue
        links = _links_de_productos(html, base)[:MAX_CANDIDATOS]
        if not links:
            ultimo_error = "Abrí el buscador pero no encontré links a productos (puede cargar con JavaScript)"
            continue
        productos = []
        for link in links:
            ficha_html, _ = descargar(link)
            if ficha_html:
                p = leer_ficha_generica(ficha_html, link, tienda)
                if p["nombre"] and p["precio_promo"]:
                    productos.append(p)
        if productos:
            return productos, None
        ultimo_error = "Encontré productos pero no pude leer sus precios"
    return None, ultimo_error


def buscar_en_competidor(nombre, config, consulta, ml_token=None):
    metodo = config.get("metodo", "auto")
    if metodo == "mercadolibre":
        return buscar_mercadolibre(consulta, nombre, ml_token)
    if metodo == "vtex":
        productos, error = buscar_vtex(config["sitio"].rstrip("/"), consulta, nombre)
        if productos is None:
            return buscar_auto(config, consulta, nombre)
        return productos, error
    return buscar_auto(config, consulta, nombre)


# ---------------------------------------------------------------------------
# COMPARACIÓN
# ---------------------------------------------------------------------------

def _texto_producto(p):
    return " ".join([p.get("nombre", ""), p.get("marca", ""), p.get("modelo", "")]
                    + [f"{k} {v}" for k, v in (p.get("ficha") or {}).items()])


def puntaje_similitud(sodimac, candidato):
    """Devuelve (puntaje 0-100, etiqueta, explicación)."""
    modelo = normalizar(sodimac.get("modelo", "")).replace(" ", "")
    texto_cand = normalizar(_texto_producto(candidato)).replace(" ", "")
    if len(modelo) >= 4 and modelo in texto_cand:
        return 100, "Mismo modelo", f"Coincide el modelo {sodimac.get('modelo')}"

    clave_sod = set(palabras_clave(sodimac.get("nombre", "")))
    clave_cand = set(palabras_clave(candidato.get("nombre", "") + " " + " ".join((candidato.get("ficha") or {}).values())))
    coincide_nombre = len(clave_sod & clave_cand) / len(clave_sod) if clave_sod else 0

    med_sod = medidas(_texto_producto(sodimac))
    med_cand = medidas(_texto_producto(candidato))
    coincide_medidas = len(med_sod & med_cand) / len(med_sod) if med_sod else None

    misma_marca = bool(sodimac.get("marca")) and normalizar(sodimac["marca"]) == normalizar(candidato.get("marca", ""))

    if coincide_medidas is None:
        puntaje = coincide_nombre * 85
    else:
        puntaje = coincide_nombre * 60 + coincide_medidas * 25
    if misma_marca:
        puntaje += 15
    puntaje = round(min(puntaje, 99))

    partes = [f"{len(clave_sod & clave_cand)}/{len(clave_sod)} palabras clave"]
    if med_sod:
        partes.append(f"{len(med_sod & med_cand)}/{len(med_sod)} medidas")
    if misma_marca:
        partes.append("misma marca")
    etiqueta = "Muy similar" if puntaje >= 75 else "Similar" if puntaje >= 50 else "Revisar"
    return puntaje, etiqueta, ", ".join(partes)


def consultas_para(sodimac):
    """Arma qué buscar en los competidores: primero el modelo, después el nombre."""
    consultas = []
    modelo = (sodimac.get("modelo") or "").strip()
    if len(modelo) >= 4:
        consultas.append(modelo)
    claves = palabras_clave(sodimac.get("nombre", ""))
    if claves:
        consultas.append(" ".join(claves[:6]))
    return consultas


def mejores_equivalentes(sodimac, nombre, config, ml_token=None, cuantos=1):
    """Busca en un competidor y devuelve (lista de (producto, puntaje, etiqueta, explicación), error)."""
    vistos, resultados, ultimo_error = set(), [], None
    for consulta in consultas_para(sodimac):
        productos, error = buscar_en_competidor(nombre, config, consulta, ml_token)
        if productos is None:
            ultimo_error = error
            continue
        for p in productos:
            if not p.get("link") or p["link"] in vistos or not p.get("precio_promo"):
                continue
            vistos.add(p["link"])
            resultados.append((p, *puntaje_similitud(sodimac, p)))
        if any(r[1] == 100 for r in resultados):
            break  # ya encontramos el mismo modelo
    resultados.sort(key=lambda r: r[1], reverse=True)
    if not resultados and ultimo_error:
        return None, ultimo_error
    return resultados[:cuantos], None


def precio_final(p):
    return p.get("precio_promo") or p.get("precio_normal")


def fila_resultado(sodimac, nombre_comp, resultado=None, error=None):
    fila = {
        "SKU": sodimac["sku"],
        "Producto Sodimac": sodimac["nombre"],
        "Precio Sodimac": sodimac.get("precio_normal"),
        "Promo Sodimac": sodimac.get("precio_promo"),
        "Cuotas Sodimac": sodimac.get("cuotas", ""),
        "Link Sodimac": sodimac.get("link", ""),
        "Competidor": nombre_comp,
        "Imagen": "", "Producto competidor": "", "Coincidencia": "", "Puntaje": None,
        "Por qué": "", "Precio normal": None, "Precio promo": None, "Ahorro $": None,
        "Ahorro %": None, "Cuotas": "", "Link": "", "Variación vs Sodimac %": None,
    }
    if error:
        fila["Coincidencia"] = "Error"
        fila["Por qué"] = error
        return fila
    if not resultado:
        fila["Coincidencia"] = "Sin resultados"
        return fila
    p, puntaje, etiqueta, explicacion = resultado
    fila.update({
        "Imagen": p.get("imagen", ""),
        "Producto competidor": p.get("nombre", ""),
        "Coincidencia": etiqueta,
        "Puntaje": puntaje,
        "Por qué": explicacion,
        "Precio normal": p.get("precio_normal") or p.get("precio_promo"),
        "Precio promo": p.get("precio_promo") if p.get("precio_normal") else None,
        "Cuotas": p.get("cuotas", ""),
        "Link": p.get("link", ""),
    })
    if p.get("precio_normal") and p.get("precio_promo"):
        fila["Ahorro $"] = round(p["precio_normal"] - p["precio_promo"])
        fila["Ahorro %"] = round((p["precio_normal"] - p["precio_promo"]) / p["precio_normal"] * 100, 1)
    pf_s, pf_c = precio_final(sodimac), precio_final(p)
    if pf_s and pf_c:
        fila["Variación vs Sodimac %"] = round((pf_c - pf_s) / pf_s * 100, 1)
    return fila
