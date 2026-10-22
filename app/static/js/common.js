/* Utilidades compartidas por todas las páginas. Expone window.Opciones. */
(function () {
  "use strict";

  const root = document.documentElement;

  // ---------------------------------------------------------------- Tema
  function currentTheme() {
    if (root.dataset.theme) return root.dataset.theme;
    return matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function setTheme(theme) {
    root.dataset.theme = theme;
    try { localStorage.setItem("theme", theme); } catch (e) { /* sin almacenamiento */ }
    document.dispatchEvent(new CustomEvent("themechange"));
  }

  document.getElementById("theme-toggle")?.addEventListener("click", () => {
    setTheme(currentTheme() === "dark" ? "light" : "dark");
  });
  // Fija el atributo para que el icono refleje el tema del sistema.
  if (!root.dataset.theme) root.dataset.theme = currentTheme();

  // ---------------------------------------------------------------- Formato
  const nf = (digits) => new Intl.NumberFormat("es-CO", { minimumFractionDigits: digits, maximumFractionDigits: digits });

  function fmt(value, digits = 4) {
    if (value === null || value === undefined || !Number.isFinite(value)) return "—";
    return nf(digits).format(Math.abs(value) < 0.5 * 10 ** -digits ? 0 : value);
  }

  function fmtSigned(value, digits = 4) {
    if (!Number.isFinite(value)) return "—";
    const text = fmt(value, digits);
    return value > 0 && text !== fmt(0, digits) ? `+${text}` : text;
  }

  const fmtPct = (value, digits = 2) => `${fmt(value * 100, digits)} %`;

  // ---------------------------------------------------------------- Formularios
  /** Convierte un formulario en un objeto plano (los radios aportan solo el marcado). */
  function formData(form) {
    const data = {};
    for (const el of form.elements) {
      if (!el.name || el.disabled) continue;
      if (el.type === "radio" && !el.checked) continue;
      if (el.closest("[hidden]")) continue;
      data[el.name] = el.value;
    }
    return data;
  }

  function clearErrors(scope) {
    scope.querySelectorAll(".field.invalid").forEach((f) => f.classList.remove("invalid"));
    scope.querySelectorAll(".field-error").forEach((e) => (e.textContent = ""));
  }

  /** Marca el campo con error; devuelve true si lo encontró en `scope`. */
  function showFieldError(scope, field, message) {
    const wrap = field && scope.querySelector(`.field[data-field="${field}"]`);
    if (!wrap) return false;
    wrap.classList.add("invalid");
    wrap.querySelector(".field-error").textContent = message;
    return true;
  }

  /** Muestra u oculta el campo q según el subyacente y ajusta su etiqueta. */
  function bindYieldField(form, onChange) {
    const box = form.querySelector("[data-yield-field]");
    const label = box.querySelector(".field-label");
    const input = box.querySelector("input");
    const config = {
      stock: null,
      dividend: { text: "Dividend yield", value: 3 },
      currency: { text: "Tasa extranjera", value: 2 },
    };
    function apply(changed) {
      const asset = form.querySelector('input[name="asset"]:checked').value;
      const cfg = config[asset];
      box.hidden = !cfg;
      if (cfg) {
        label.firstChild.textContent = cfg.text + " ";
        if (changed) input.value = cfg.value;
      }
    }
    form.querySelectorAll('input[name="asset"]').forEach((r) =>
      r.addEventListener("change", () => { apply(true); onChange?.(); })
    );
    apply(false);
  }

  function debounce(fn, wait = 250) {
    let timer;
    return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), wait); };
  }

  // ---------------------------------------------------------------- API
  class ApiError extends Error {
    constructor(message, field) { super(message); this.field = field; }
  }

  /** POST JSON; descarta respuestas de peticiones anteriores que lleguen tarde. */
  function apiClient(url) {
    let seq = 0;
    return async function (payload) {
      const id = ++seq;
      let res;
      try {
        res = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
      } catch (e) {
        throw new ApiError("No se pudo conectar con el servidor.");
      }
      const body = await res.json().catch(() => ({}));
      if (id !== seq) return null;
      if (!res.ok) throw new ApiError(body.error || "Error inesperado en el cálculo.", body.field);
      return body;
    };
  }

  // ---------------------------------------------------------------- Gráficos
  const css = (name) => getComputedStyle(root).getPropertyValue(name).trim();

  function chartLayout(extra = {}) {
    const axis = {
      gridcolor: css("--chart-grid"),
      linecolor: css("--border"),
      zerolinecolor: css("--border-strong"),
      tickfont: { family: "JetBrains Mono, monospace", size: 11, color: css("--muted") },
      title: { font: { size: 12, color: css("--text-2") } },
      automargin: true,
    };
    return {
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      font: { family: "Inter, sans-serif", color: css("--text-2"), size: 12 },
      margin: { l: 8, r: 8, t: 24, b: 8 },
      hovermode: "x unified",
      hoverlabel: { bgcolor: css("--surface"), bordercolor: css("--border-strong"), font: { color: css("--text"), family: "JetBrains Mono, monospace" } },
      legend: { orientation: "h", y: -0.18, x: 0, font: { size: 12 } },
      ...extra,
      xaxis: { ...axis, ...(extra.xaxis || {}), title: { ...axis.title, ...(extra.xaxis?.title || {}) } },
      yaxis: { ...axis, ...(extra.yaxis || {}), title: { ...axis.title, ...(extra.yaxis?.title || {}) } },
    };
  }

  function plot(el, traces, layout) {
    if (!window.Plotly) return;
    Plotly.react(el, traces, layout, { responsive: true, displaylogo: false, modeBarButtonsToRemove: ["lasso2d", "select2d"] });
  }

  window.Opciones = {
    fmt, fmtSigned, fmtPct, formData, clearErrors, showFieldError, bindYieldField,
    debounce, apiClient, css, chartLayout, plot,
  };
})();
