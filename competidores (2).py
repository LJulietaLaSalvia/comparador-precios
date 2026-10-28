"""
LISTA DE COMPETIDORES
=====================

Este es el único archivo que vas a necesitar tocar para sumar o sacar competidores.

Cada competidor es una "receta" con estos datos:

  "sitio":    la dirección principal de la tienda online.
  "metodo":   cómo se lee ese sitio:
                - "vtex"          -> tiendas armadas con VTEX (traen precio, precio
                                     de lista y cuotas de forma ordenada).
                - "mercadolibre"  -> usa la API oficial de Mercado Libre.
                - "auto"          -> prueba VTEX primero; si no funciona, usa el
                                     buscador del sitio y lee cada ficha de producto.
  "color" / "sigla" / "color_casilla": cómo se ve el competidor en la pantalla.
  "busqueda": (opcional) la dirección del buscador del sitio, con {q} donde va
              lo que se busca. Solo se usa con el método "auto".

Para sumar un competidor nuevo, copiá una línea, cambiale el nombre y el sitio,
y dejá "metodo": "auto". En la pestaña "Diagnóstico" del programa vas a ver si
funciona.
"""

COMPETIDORES = {
    "Easy": {
        "color": "#E30613",
        "sigla": "E",
        "color_casilla": "red",
        "sitio": "https://www.easy.com.ar",
        "metodo": "vtex",
    },
    "Fravega": {
        "color": "#6A1B9A",
        "sigla": "F",
        "color_casilla": "violet",
        "sitio": "https://www.fravega.com",
        "metodo": "auto",
        "busqueda": "https://www.fravega.com/l/?keyword={q}",
    },
    "On City": {
        "color": "#F28C00",
        "sigla": "OC",
        "color_casilla": "orange",
        "sitio": "https://www.oncity.com",
        "metodo": "auto",
    },
    "Blaisten": {
        "color": "#D71920",
        "sigla": "B",
        "color_casilla": "red",
        "sitio": "https://www.blaisten.com.ar",
        "metodo": "auto",
    },
    "Carrefour": {
        "color": "#1E4FA1",
        "sigla": "C",
        "color_casilla": "blue",
        "sitio": "https://www.carrefour.com.ar",
        "metodo": "vtex",
    },
    "Coto": {
        "color": "#C8102E",
        "sigla": "CO",
        "color_casilla": "red",
        "sitio": "https://www.cotodigital.com.ar",
        "metodo": "auto",
    },
    "Cetrogar": {
        "color": "#F05A22",
        "sigla": "CE",
        "color_casilla": "orange",
        "sitio": "https://www.cetrogar.com.ar",
        "metodo": "auto",
        "busqueda": "https://www.cetrogar.com.ar/catalogsearch/result/?q={q}",
    },
    "Megatone": {
        "color": "#FF6A13",
        "sigla": "M",
        "color_casilla": "orange",
        "sitio": "https://www.megatone.net",
        "metodo": "auto",
    },
    "Pinturerías Prestigio": {
        "color": "#111111",
        "sigla": "P",
        "color_casilla": "gray",
        "sitio": "https://www.prestigio.com.ar",
        "metodo": "auto",
    },
    "Pinturerías Rex": {
        "color": "#E2001A",
        "sigla": "R",
        "color_casilla": "red",
        "sitio": "https://www.pintureriasrex.com",
        "metodo": "auto",
    },
}
