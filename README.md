# Calculadora de Opciones

Aplicación web en Flask para valorar opciones financieras con dos modelos:

- **Árbol binomial (Cox-Ross-Rubinstein):** opciones europeas y americanas, con el árbol nodo a nodo, los nodos de ejercicio anticipado y la convergencia hacia Black-Scholes.
- **Black-Scholes-Merton:** precio y griegas de opciones europeas, y un constructor de estrategias de hasta 4 posiciones (con plantillas) que muestra el diagrama de pagos, los puntos de equilibrio y la ganancia y pérdida máximas.

Ambos modelos admiten tres tipos de subyacente: acción, acción con dividendos (dividend yield `q`) y divisa (tasa extranjera, Garman-Kohlhagen).

## Ejecutar

Requiere [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run flask --app wsgi:app run --debug --port 5050
```

Abre <http://127.0.0.1:5050>.

## Pruebas

```bash
uv run pytest
```

## Estructura

```
app/
├── __init__.py          # create_app(): registra blueprints y manejo de errores
├── config.py            # límites (pasos máximos, patas máximas…)
├── validation.py        # lectura y validación de parámetros JSON
├── pricing/             # motores de cálculo puros (sin Flask)
│   ├── binomial.py
│   ├── black_scholes.py
│   └── strategies.py
├── pages/               # una página = un blueprint (vista HTML + endpoint /api)
│   ├── home.py
│   ├── binomial.py
│   └── black_scholes.py
├── templates/           # base.html, macros.html y una plantilla por página
└── static/
    ├── css/app.css      # tokens de diseño (modo claro y oscuro)
    └── js/              # common.js + un script por página
tests/                   # pruebas del motor y de la API
wsgi.py                  # punto de entrada
```

## API

| Método | Ruta | Descripción |
| --- | --- | --- |
| POST | `/api/binomial` | Prima binomial, parámetros del árbol, árbol (hasta 6 pasos), convergencia y referencia BS |
| POST | `/api/black-scholes` | Precio, griegas, d₁/d₂, call y put, y curva de precio frente al spot |
| POST | `/api/estrategias` | Evaluación de una estrategia de varias posiciones |

Las tasas, la volatilidad y `q` se envían en **porcentaje** (`"rate": 5` = 5 %). `maturity` va en años. Vega y rho se expresan por 1 punto porcentual y theta por día calendario.

Basado en [calculadora-de-opciones-](https://github.com/jdzapata2004-eng/calculadora-de-opciones-) (versión en Streamlit).
