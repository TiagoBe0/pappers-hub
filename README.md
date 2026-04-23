# pappers-hub

Interfaz visual estilo mapa conceptual para organizar y abrir resúmenes HTML de pappers.

## Estructura

- `index.html`: vista principal con el nodo central **resumenes**.
- `assets/styles.css`: estilo "revista científica" con animaciones.
- `assets/app.js`: descubrimiento de pappers y generación automática de hipervínculos.
- `pappers_html/`: carpeta donde se guardan tus resúmenes (`papper_id.html`).

## Cómo agregar nuevos resúmenes

1. Copia cada resumen HTML dentro de `pappers_html/` con nombre `papper_id.html`.
2. (Recomendado) Actualiza `pappers_html/index.json` agregando el archivo.
3. Recarga la página principal.

## Ejecución local

```bash
python -m http.server 8000
```

Luego abre `http://localhost:8000`.
