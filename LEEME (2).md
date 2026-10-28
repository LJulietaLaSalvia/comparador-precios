# Comparador de precios Sodimac vs competencia

Programa web gratuito: cargás SKUs de Sodimac, tildás competidores y te devuelve
el producto igual o más parecido de cada uno, con precio normal, promo, ahorro,
cuotas, imagen, link y variación contra Sodimac. Se descarga en Excel.

## Archivos

| Archivo | Para qué sirve | ¿Lo toco? |
|---|---|---|
| `app.py` | La pantalla del programa | No hace falta |
| `motor.py` | Lee Sodimac, busca en competidores y compara | No hace falta |
| `vista.py` | El diseño: colores, tarjetas y tabla de resultados | Solo si querés cambiar colores |
| `competidores.py` | **La lista de competidores** | Sí, para sumar o sacar sitios |
| `requirements.txt` | Lista de piezas que necesita el programa | No |

---

## Cómo publicarlo gratis con un link (unos 15 minutos, una sola vez)

### Paso 1 — Crear una cuenta en GitHub
1. Entrá a **github.com** y tocá **Sign up**. Usá tu mail personal.
2. Confirmá el mail.

GitHub es donde se guardan los archivos del programa.

### Paso 2 — Subir los archivos
1. Ya con sesión iniciada, arriba a la derecha tocá **+** → **New repository**.
2. En **Repository name** poné `comparador-precios`.
3. Elegí **Private** (así nadie ve el código).
4. Tocá **Create repository**.
5. En la página que aparece, tocá el link **uploading an existing file**.
6. Arrastrá los 6 archivos (`app.py`, `motor.py`, `vista.py`, `competidores.py`,
   `requirements.txt`, `LEEME.md`) y tocá **Commit changes**.

> Si ya habías subido la versión anterior: entrá al repositorio, tocá
> **Add file → Upload files**, arrastrá los 6 archivos nuevos y **Commit changes**.
> Se reemplazan solos y la app se actualiza en un minuto.

### Paso 3 — Publicarlo en Streamlit Community Cloud
1. Entrá a **share.streamlit.io** y tocá **Continue with GitHub**. Aceptá los permisos.
2. Tocá **Create app** → **Deploy a public app from GitHub**
   (o "Yup, I have an app").
3. Completá:
   - **Repository**: `tu-usuario/comparador-precios`
   - **Branch**: `main`
   - **Main file path**: `app.py`
   - **App URL**: elegí un nombre, por ejemplo `comparador-sodimac`
4. Tocá **Deploy**. Tarda 2 o 3 minutos la primera vez.

Listo: vas a tener un link tipo `https://comparador-sodimac.streamlit.app`.

> **Privacidad:** por defecto cualquiera con el link puede entrar. Para que solo
> entren personas invitadas: en share.streamlit.io, en tu app → **⋮** →
> **Settings** → **Sharing** → "Only specific people can view this app" y
> agregá los mails.

---

## Cómo usarlo
1. **Paso 1:** subí un Excel con los SKUs en la primera columna (podés bajar la
   plantilla de ejemplo) o escribilos a mano en "Ingresar SKUs manualmente".
2. **Paso 2:** tildá los competidores.
3. **Paso 3:** tocá **Buscar productos comparables**.
4. Revisá la tabla: una columna por competidor. Debajo del link de cada producto
   hay una etiqueta que dice qué tan seguro está el programa:
   - **Mismo modelo**: encontró exactamente el mismo modelo.
   - **Muy similar / Similar**: producto equivalente, verificá con el link.
   - **Revisar**: no está seguro; probablemente no hay equivalente.
5. **Fila de variación**: ↓ verde = el competidor está más barato que Sodimac;
   ↑ rojo = está más caro.
6. Tocá **Exportar a Excel** para bajar todo el detalle.

## "Diagnóstico de competidores" (usalo la primera vez, está al final de la página)
Hace una búsqueda de prueba en cada competidor tildado y te dice cuáles
funcionan. **Mandale una captura a Claude** con el resultado: los que den
error se arreglan ajustando su "receta".

## Sumar un competidor
En GitHub abrí `competidores.py`, tocá el lápiz ✏️ (editar), copiá una línea
de las existentes, cambiá el nombre y el sitio, y tocá **Commit changes**.
La app se actualiza sola en un minuto.

## Cosas a tener en cuenta
- El programa consulta despacio (1 segundo entre pedidos al mismo sitio) para
  no saturar a nadie. 10 SKUs x 11 competidores pueden tardar varios minutos.
- Los sitios cambian su diseño cada tanto; si un competidor deja de andar, se
  ajusta su receta.
- Streamlit Cloud corre en servidores fuera de Argentina: algunos sitios podrían
  bloquear o mostrar otro precio. El Diagnóstico lo muestra.
- Si la app no se usa por varios días, "se duerme": al entrar, tocá el botón
  para despertarla y esperá un minuto.
