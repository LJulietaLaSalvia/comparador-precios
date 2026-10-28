"""
DISEÑO DE LA PANTALLA
=====================
Estilos (colores, tarjetas) y la tabla de resultados con una columna por competidor.
"""

from html import escape

AZUL = "#0072CE"
ROJO = "#E4002B"

CSS = f"""
<style>
.block-container {{ padding-top: 1.2rem; max-width: 1600px; }}
header[data-testid="stHeader"] {{ background: transparent; }}

/* Encabezado */
.cab {{ display:flex; align-items:center; gap:24px; background:linear-gradient(90deg,#fff 0%,#F3F6FA 100%);
        border:1px solid #E3E8EF; border-radius:14px; padding:16px 24px; margin-bottom:18px; }}
.cab-marca {{ font-weight:900; font-size:30px; letter-spacing:.5px; color:{ROJO}; border-right:1px solid #E3E8EF;
              padding-right:24px; line-height:1; }}
.cab-marca span {{ color:{AZUL}; }}
.cab h1 {{ font-size:30px; margin:0; padding:0; color:#0B2A4A; font-weight:800; }}
.cab p {{ margin:2px 0 0; color:#5B6B7F; font-size:15px; }}

/* Tarjetas de pasos */
div[data-testid="stVerticalBlockBorderWrapper"] {{ border-radius:14px !important; border-color:#E3E8EF !important;
        background:#fff; }}
.paso {{ display:flex; gap:12px; align-items:flex-start; margin-bottom:6px; }}
.paso-num {{ flex:0 0 34px; height:34px; border-radius:50%; background:{AZUL}; color:#fff; font-weight:700;
             display:flex; align-items:center; justify-content:center; font-size:17px; }}
.paso-tit {{ font-weight:700; font-size:18px; color:#0B2A4A; line-height:1.2; }}
.paso-sub {{ color:#5B6B7F; font-size:13.5px; margin-top:3px; }}

/* Botón principal grande y azul */
div.stButton > button[kind="primary"], div[data-testid="stButton"] > button[kind="primary"] {{
    background:{AZUL}; border-color:{AZUL}; font-size:18px; font-weight:700; padding:14px 10px; border-radius:10px; }}
div.stButton > button[kind="primary"]:hover {{ background:#005BB0; border-color:#005BB0; }}

/* Tabla de resultados */
.res-cab {{ background:#EAF2FB; border:1px solid #D5E3F3; border-radius:12px 12px 0 0; padding:14px 18px;
            font-size:22px; font-weight:800; color:#0B2A4A; }}
.tabla-wrap {{ overflow-x:auto; border:1px solid #E3E8EF; border-top:none; border-radius:0 0 12px 12px; background:#fff; }}
table.comp {{ border-collapse:collapse; width:100%; font-size:13px; color:#1F2D3D; }}
table.comp th, table.comp td {{ border:1px solid #EDF1F5; padding:8px 10px; vertical-align:middle; }}
table.comp thead th {{ background:#F7F9FC; font-weight:700; text-align:center; white-space:nowrap; }}
table.comp thead tr.sub th {{ font-weight:500; color:#5B6B7F; font-size:11.5px; }}
.logo {{ display:inline-flex; align-items:center; justify-content:center; width:30px; height:30px; border-radius:50%;
         font-weight:800; font-size:11px; margin-right:8px; vertical-align:middle; }}
td.sku {{ font-size:15px; text-align:center; white-space:nowrap; }}
td.prod {{ min-width:270px; }}
.prod-box {{ display:flex; gap:12px; align-items:center; }}
.prod-box img {{ width:84px; height:84px; object-fit:contain; }}
.prod-nom {{ font-weight:700; font-size:14px; line-height:1.25; }}
.prod-meta {{ color:#5B6B7F; font-size:11.5px; margin-top:4px; line-height:1.4; }}
td.celda {{ min-width:170px; text-align:center; }}
.precios {{ display:flex; justify-content:space-between; gap:10px; }}
.pn {{ color:#3B4A5C; white-space:nowrap; }}
.pp {{ color:{ROJO}; font-weight:700; white-space:nowrap; }}
.badge {{ display:inline-block; background:#FDE4E7; color:{ROJO}; font-weight:700; border-radius:4px;
          padding:2px 7px; margin-top:4px; font-size:12px; }}
.sinpromo {{ display:inline-block; background:#EEF1F4; color:#8A97A6; border-radius:4px; padding:2px 10px; margin-top:4px; }}
.medio {{ display:flex; align-items:center; justify-content:space-between; gap:8px; margin-top:6px; }}
.medio img {{ width:62px; height:62px; object-fit:contain; }}
.cuotas {{ color:#3B4A5C; font-size:12px; text-align:center; flex:1; }}
.ver {{ display:inline-block; margin-top:6px; color:{AZUL}; text-decoration:underline; font-size:12px; }}
.chip {{ display:inline-block; border-radius:10px; padding:1px 8px; font-size:10.5px; margin-left:4px; }}
.chip-ok {{ background:#E3F4E8; color:#1B7A3A; }} .chip-med {{ background:#FFF4D6; color:#8A6100; }}
.chip-rev {{ background:#FDE4E7; color:#A1001E; }}
.vacio {{ color:#8A97A6; font-style:italic; }}
tr.var td {{ background:#FAFBFC; font-weight:700; text-align:center; font-size:13.5px; }}
tr.var td.var-tit {{ text-align:left; font-weight:500; color:#3B4A5C; }}
td.sube {{ background:#FDECEE !important; color:#C8102E; }}
td.baja {{ background:#E7F6EC !important; color:#1B7A3A; }}
.leyenda {{ color:#5B6B7F; font-size:12.5px; margin-top:8px; }}
</style>
"""


def encabezado():
    return """
    <div class="cab">
      <div class="cab-marca">SODI<span>MAC</span></div>
      <div>
        <h1>Comparador Competitivo Sodimac</h1>
        <p>Encontrá productos equivalentes en las principales tiendas online y compará precios, promociones y condiciones.</p>
      </div>
    </div>"""


def titulo_paso(numero, titulo, subtitulo):
    return f"""<div class="paso"><div class="paso-num">{numero}</div>
      <div><div class="paso-tit">{escape(titulo)}</div><div class="paso-sub">{escape(subtitulo)}</div></div></div>"""


def pesos(valor):
    if valor is None or valor != valor:  # None o NaN
        return ""
    return "$ " + f"{int(round(valor)):,}".replace(",", ".")


def _texto_oscuro(hexa):
    h = hexa.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (0.299 * r + 0.587 * g + 0.114 * b) > 170


def logo(nombre, config):
    color = config.get("color", "#888888")
    texto = "#222" if _texto_oscuro(color) else "#fff"
    sigla = escape(config.get("sigla", nombre[:1]))
    return f'<span class="logo" style="background:{color};color:{texto}">{sigla}</span>{escape(nombre)}'


def _cuotas_corto(texto):
    t = (texto or "").replace("Hasta ", "")
    return escape(t).replace(" sin interés", "<br>sin interés").replace(" (con interés)", "<br>con interés")


def _chip(etiqueta):
    clase = {"Mismo modelo": "chip-ok", "Muy similar": "chip-ok", "Similar": "chip-med"}.get(etiqueta, "chip-rev")
    return f'<span class="chip {clase}">{escape(etiqueta)}</span>'


def _celda_precio(normal, promo, imagen, cuotas, link=None, etiqueta=None):
    """Una celda: precio normal | precio promo + % descuento, imagen, cuotas, link."""
    if promo and normal:
        desc = round((normal - promo) / normal * 100)
        bloque_promo = f'<div class="pp">{pesos(promo)}</div><span class="badge">-{desc}%</span>'
    else:
        bloque_promo = '<span class="sinpromo">-</span>'
    img = f'<img src="{escape(imagen)}" loading="lazy">' if imagen else ""
    html = (f'<div class="precios"><div class="pn">{pesos(normal or promo)}</div><div>{bloque_promo}</div></div>'
            f'<div class="medio">{img}<div class="cuotas">{_cuotas_corto(cuotas)}</div></div>')
    if link:
        html += f'<a class="ver" href="{escape(link)}" target="_blank">Ver producto ↗</a>'
    if etiqueta:
        html += _chip(etiqueta)
    return html


def _celda_variacion(variacion):
    if variacion is None or variacion != variacion:
        return '<td>-</td>'
    if variacion > 0.5:
        return f'<td class="sube">↑ +{variacion:.0f}%</td>'
    if variacion < -0.5:
        return f'<td class="baja">↓ {variacion:.0f}%</td>'
    return '<td>0%</td>'


def tabla_resultados(resultados, competidores, config_competidores):
    """
    resultados: lista de {"sodimac": producto, "filas": {competidor: fila}}
    competidores: nombres de las columnas, en orden.
    """
    cab1 = ('<tr><th rowspan="2">SKU<br>Sodimac</th><th rowspan="2" style="text-align:left">Producto Sodimac<br>'
            '<span style="font-weight:400;color:#5B6B7F">(Ficha técnica)</span></th>'
            f'<th>{logo("Sodimac", {"color": AZUL, "sigla": "S"})}</th>')
    cab2 = '<tr class="sub"><th>Precio normal &nbsp;·&nbsp; Precio promo</th>'
    for c in competidores:
        cab1 += f'<th>{logo(c, config_competidores.get(c, {}))}</th>'
        cab2 += '<th>Precio normal &nbsp;·&nbsp; Precio promo</th>'
    cab1 += "</tr>"
    cab2 += "</tr>"

    cuerpo = ""
    for r in resultados:
        s = r["sodimac"]
        meta = []
        if s.get("marca"):
            meta.append(f"Marca: {escape(s['marca'])}")
        if s.get("modelo"):
            meta.append(f"Modelo: {escape(s['modelo'])}")
        img = f'<img src="{escape(s["imagen"])}" loading="lazy">' if s.get("imagen") else ""
        link_ficha = f'<a class="ver" href="{escape(s.get("link", ""))}" target="_blank">Ver ficha ↗</a>' if s.get("link") else ""
        prod = (f'<div class="prod-box">{img}<div><div class="prod-nom">{escape(s["nombre"])}</div>'
                f'<div class="prod-meta">{"<br>".join(meta)}</div>{link_ficha}</div></div>')
        fila = (f'<tr><td class="sku" rowspan="2">{escape(str(s["sku"]))}</td><td class="prod">{prod}</td>'
                f'<td class="celda">{_celda_precio(s.get("precio_normal"), s.get("precio_promo"), s.get("imagen"), s.get("cuotas"))}</td>')
        fila_var = '<tr class="var"><td class="var-tit">Variación vs. Sodimac (precio final)</td><td>-</td>'
        for c in competidores:
            f = r["filas"].get(c)
            if not f or f.get("Puntaje") is None:
                motivo = (f or {}).get("Coincidencia") or "Sin resultados"
                detalle = escape((f or {}).get("Por qué") or "")
                texto = "Sin equivalente" if motivo == "Sin resultados" else "No se pudo consultar"
                fila += f'<td class="celda vacio" title="{detalle}">{texto}</td>'
                fila_var += "<td>-</td>"
            else:
                normal = f.get("Precio normal")
                promo = f.get("Precio promo")
                fila += (f'<td class="celda">{_celda_precio(normal, promo, f.get("Imagen"), f.get("Cuotas"), f.get("Link"), f.get("Coincidencia"))}</td>')
                fila_var += _celda_variacion(f.get("Variación vs Sodimac %"))
        cuerpo += fila + "</tr>" + fila_var + "</tr>"

    return (f'<div class="tabla-wrap"><table class="comp"><thead>{cab1}{cab2}</thead>'
            f'<tbody>{cuerpo}</tbody></table></div>'
            '<div class="leyenda">↑ rojo = el competidor está más caro que Sodimac · ↓ verde = está más barato. '
            'Etiquetas: <b>Mismo modelo</b> / <b>Muy similar</b> / <b>Similar</b> / <b>Revisar</b> (verificá con el link). '
            'Pasá el mouse sobre "No se pudo consultar" para ver el motivo.</div>')
