# pappers_html

Coloca aquí tus resúmenes en formato HTML con el patrón:

- `papper_id.html`

Opcionalmente, mantén `index.json` con un arreglo de nombres para descubrimiento estable en hosts que no permiten listar carpetas:

```json
[
  "papper_001.html",
  "papper_transformers_2025.html"
]
```

La interfaz combina `index.json` con los archivos detectados en el índice del directorio (`pappers_html/`) cuando el servidor lo permite.
