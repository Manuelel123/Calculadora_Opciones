<div align="center">

# Calculadora de Opciones

**Valoración de opciones financieras con árboles binomiales y Black-Scholes-Merton, en una aplicación web ligera hecha con Flask.**

![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1-000000?logo=flask&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-2.2-013243?logo=numpy&logoColor=white)
![Tests](https://img.shields.io/badge/tests-pytest-0A9EDC?logo=pytest&logoColor=white)

### [Abrir la app en vivo →](https://calculadora-opciones.onrender.com/)

[Características](#características) ·
[Inicio rápido](#inicio-rápido) ·
[Modelos](#modelos) ·
[API](#api-rest) ·
[Arquitectura](#arquitectura) ·
[Pruebas](#pruebas)

</div>

---

## Descripción

La Calculadora de Opciones permite valorar opciones call y put, analizar su sensibilidad (griegas) y construir estrategias de varias posiciones desde el navegador. Toda la lógica financiera vive en un paquete de Python puro, independiente de Flask, que la interfaz web consume a través de una API JSON.

Sirve como herramienta de estudio para cursos de derivados y como base reutilizable para quien necesite un motor de valoración pequeño, probado y fácil de leer.

## Características

### Árbol binomial (Cox-Ross-Rubinstein)

- Opciones **europeas y americanas**, con hasta 5 000 pasos.
- Visualización del **árbol nodo a nodo** (los primeros 6 pasos del árbol de N pasos, con los mismos `u`, `d` y `p` que la prima), con precio del subyacente, valor de la opción y nodos de **ejercicio anticipado** resaltados.
- Gráfico de **convergencia** del precio binomial hacia Black-Scholes a medida que crece el número de pasos.
- **Prima por ejercicio anticipado** de la americana frente a la europea equivalente.

### Black-Scholes-Merton

- Precio de call y put europeas, con **d₁, d₂, valor intrínseco y valor temporal**.
- **Griegas** completas: delta, gamma, vega, theta y rho.
- Curva del precio de la opción frente al spot, comparada con su valor intrínseco.

### Constructor de estrategias

- Hasta **4 posiciones** (call, put o el propio subyacente; larga/corta, strike y cantidad). El subyacente entra al precio spot.
- Plantillas listas para usar:
  - **Posiciones sintéticas:** largo y corto call sintético (subyacente ± put), largo y corto put sintético (subyacente ∓ call).
  - **Spreads verticales:** bull call spread, bear call spread, bull put spread y bear put spread.
  - **Butterfly spread** con calls y con puts.
- **Diagrama de pagos** al vencimiento por posición y total, **puntos de equilibrio**, **ganancia y pérdida máximas** (detecta cuándo son ilimitadas) y griegas agregadas.

### Tres tipos de subyacente

| Subyacente | Parámetro `q` | Modelo |
| --- | --- | --- |
| Acción | `q = 0` | Black-Scholes clásico |
| Acción con dividendos | Dividend yield continuo | Merton |
| Divisa | Tasa de interés extranjera | Garman-Kohlhagen |

### Interfaz

- Recalcula al instante mientras se editan los parámetros.
- Gráficos interactivos con Plotly.
- Modo claro y oscuro.
- Validación de entradas con mensajes de error claros, campo por campo.

## Inicio rápido

La app está publicada en **<https://calculadora-opciones.onrender.com/>** y se puede usar desde cualquier navegador, sin instalar nada. Está en el plan gratuito de Render: si lleva un rato sin visitas, la primera carga puede tardar alrededor de un minuto.

Para ejecutarla en tu propio equipo:

### Requisitos

- [Python](https://www.python.org/) 3.12 o superior
- [uv](https://docs.astral.sh/uv/) para gestionar el entorno y las dependencias

### Instalación y ejecución

```bash
git clone https://github.com/Manuelel123/Calculadora_Opciones.git
cd Calculadora_Opciones
uv sync
uv run flask --app wsgi:app run --debug --port 5050
```

Abre <http://127.0.0.1:5050> en el navegador. Esa dirección es local: solo funciona en tu equipo mientras el servidor esté corriendo.

| Página | Ruta |
| --- | --- |
| Inicio | `/` |
| Árbol binomial | `/binomial` |
| Black-Scholes y estrategias | `/black-scholes` |

## Modelos

### Árbol binomial

En cada paso de longitud $\Delta t = T/N$ el subyacente sube o baja según los factores de Cox-Ross-Rubinstein:

$$
u = e^{\sigma\sqrt{\Delta t}}, \qquad d = \frac{1}{u}, \qquad p = \frac{e^{(r-q)\Delta t} - d}{u - d}
$$

La prima se obtiene por inducción hacia atrás desde el vencimiento. En las americanas, cada nodo toma el máximo entre el valor de continuación y el valor intrínseco. La implementación está vectorizada con NumPy y usa memoria $O(N)$.

### Black-Scholes-Merton

$$
d_1 = \frac{\ln(S/K) + (r - q + \tfrac{1}{2}\sigma^2)\,T}{\sigma\sqrt{T}}, \qquad d_2 = d_1 - \sigma\sqrt{T}
$$

$$
C = S e^{-qT} N(d_1) - K e^{-rT} N(d_2), \qquad P = K e^{-rT} N(-d_2) - S e^{-qT} N(-d_1)
$$

> [!NOTE]
> Black-Scholes aparece como referencia en la página del árbol: es el valor exacto de la opción europea y una cota inferior de la americana.

## API REST

Todos los endpoints reciben y devuelven JSON.

| Método | Ruta | Descripción |
| --- | --- | --- |
| `POST` | `/api/binomial` | Prima binomial, parámetros del árbol, árbol nodo a nodo, convergencia y referencia Black-Scholes |
| `POST` | `/api/black-scholes` | Precio, griegas, d₁/d₂, precios de call y put, y curva de precio frente al spot |
| `POST` | `/api/estrategias` | Evaluación completa de una estrategia de varias posiciones |

### Parámetros

| Campo | Descripción | Unidad | Endpoints |
| --- | --- | --- | --- |
| `spot` | Precio actual del subyacente (S₀) | Moneda | Todos |
| `strike` | Precio de ejercicio (K) | Moneda | binomial, black-scholes |
| `rate` | Tasa libre de riesgo (r) | **%** | Todos |
| `volatility` | Volatilidad anual (σ) | **%** | Todos |
| `maturity` | Tiempo al vencimiento (T) | Años | Todos |
| `yield` | Dividend yield o tasa extranjera (q). Opcional, por defecto 0 | **%** | Todos |
| `option_type` | `"call"` o `"put"` | — | binomial, black-scholes |
| `exercise` | `"european"` o `"american"` | — | binomial |
| `steps` | Número de pasos del árbol (1–5 000) | — | binomial |
| `legs` | Lista de posiciones: `option_type` (`"call"`/`"put"`/`"stock"`), `side` (`"long"`/`"short"`), `strike` (no aplica a `"stock"`), `quantity` | — | estrategias |

> [!IMPORTANT]
> Las tasas, la volatilidad y `q` se envían en **porcentaje**: `"rate": 5` equivale a 5 %. Vega y rho se expresan por 1 punto porcentual, y theta por día calendario.

### Ejemplos

**Call europea con Black-Scholes**

```bash
curl -X POST http://127.0.0.1:5050/api/black-scholes \
  -H "Content-Type: application/json" \
  -d '{"spot": 100, "strike": 100, "rate": 5, "volatility": 20, "maturity": 1, "option_type": "call"}'
```

```jsonc
{
  "price": 10.4506,
  "d1": 0.35,
  "d2": 0.15,
  "delta": 0.6368,
  "gamma": 0.0188,
  "vega": 0.3752,
  "theta": -0.0176,
  "rho": 0.5323,
  "call": 10.4506,
  "put": 5.5735,
  "curve": { "spots": [], "prices": [], "intrinsic": [], "delta": [] }
  // ...
}
```

**Put americana con árbol binomial de 500 pasos**

```bash
curl -X POST http://127.0.0.1:5050/api/binomial \
  -H "Content-Type: application/json" \
  -d '{"spot": 100, "strike": 100, "rate": 5, "volatility": 20, "maturity": 1,
       "steps": 500, "option_type": "put", "exercise": "american"}'
```

```jsonc
{
  "price": 6.0888,
  "black_scholes": 5.5735,
  "early_exercise_premium": 0.5153,
  "u": 1.009, "d": 0.9911, "p": 0.5034,
  "convergence": { "steps": [], "prices": [] },
  "tree": { "steps": 6, "total_steps": 500, "truncated": true, "nodes": [] }
  // ...
}
```

**Bull call spread**

```bash
curl -X POST http://127.0.0.1:5050/api/estrategias \
  -H "Content-Type: application/json" \
  -d '{"spot": 100, "rate": 5, "volatility": 20, "maturity": 1,
       "legs": [
         {"option_type": "call", "side": "long",  "strike": 95,  "quantity": 1},
         {"option_type": "call", "side": "short", "strike": 105, "quantity": 1}
       ]}'
```

### Errores

Si un parámetro no es válido, la API responde con `400 Bad Request` e indica el campo afectado:

```json
{ "error": "El precio spot (S₀) debe ser mayor que 0.", "field": "spot" }
```

## Arquitectura

El proyecto separa el cálculo de la presentación: los motores de valoración no dependen de Flask y se pueden importar y probar por sí solos.

```
app/
├── __init__.py          # create_app(): registra blueprints y manejo de errores
├── config.py            # Límites (pasos máximos, posiciones máximas…)
├── validation.py        # Lectura y validación de los parámetros JSON
├── pricing/             # Motores de cálculo puros (sin Flask)
│   ├── binomial.py
│   ├── black_scholes.py
│   └── strategies.py
├── pages/               # Una página = un blueprint (vista HTML + endpoint /api)
│   ├── home.py
│   ├── binomial.py
│   └── black_scholes.py
├── templates/           # base.html, macros.html y una plantilla por página
└── static/
    ├── css/app.css      # Tokens de diseño (modo claro y oscuro)
    └── js/              # common.js + un script por página
tests/                   # Pruebas del motor de cálculo y de la API
wsgi.py                  # Punto de entrada
```

Uso del motor de cálculo desde Python:

```python
from app.pricing import price_binomial, price_black_scholes

price_black_scholes(S=100, K=100, r=0.05, sigma=0.20, T=1, option_type="call").price
# ≈ 10.4506

price_binomial(S=100, K=100, r=0.05, sigma=0.20, T=1, N=500,
               option_type="put", exercise="american").price
# ≈ 6.0888
```

> En el motor de cálculo las tasas y la volatilidad van en forma decimal (`0.05`); la conversión desde porcentaje ocurre en la capa de validación de la API.

## Pruebas

La suite cubre los motores de valoración (paridad put-call, griegas frente a diferencias finitas, convergencia del árbol a Black-Scholes, ejercicio anticipado y métricas de estrategias) y los endpoints de la API, incluida la validación de errores.

```bash
uv run pytest
```

## Tecnologías

| Capa | Herramientas |
| --- | --- |
| Backend | Python, Flask, NumPy |
| Frontend | Jinja2, JavaScript, Plotly.js, CSS |
| Calidad | pytest |
| Entorno | uv |
