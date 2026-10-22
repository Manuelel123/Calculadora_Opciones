(function () {
  "use strict";

  const O = window.Opciones;
  const marketForm = document.getElementById("market-form");
  const singleForm = document.getElementById("single-form");
  const errorBox = document.getElementById("bs-error");
  const legsBox = document.getElementById("legs");
  const legTemplate = document.getElementById("leg-template");
  const addLegBtn = document.getElementById("add-leg");
  const presetSelect = document.getElementById("preset");
  const PRESETS = JSON.parse(document.getElementById("presets-data").textContent);
  const { maxLegs } = JSON.parse(document.getElementById("config-data").textContent);

  const out = (key) => document.querySelector(`[data-out="${key}"]`);
  const requestSingle = O.apiClient("/api/black-scholes");
  const requestStrategy = O.apiClient("/api/estrategias");
  const GREEKS = ["delta", "gamma", "vega", "theta", "rho"];

  let activeTab = "single";
  const lastResult = { single: null, strategy: null };

  function showError(err, scopes) {
    if (scopes.some((scope) => O.showFieldError(scope, err.field, err.message))) return;
    errorBox.textContent = err.message;
    errorBox.hidden = false;
  }

  function resetErrors() {
    errorBox.hidden = true;
    [marketForm, singleForm].forEach(O.clearErrors);
    legsBox.querySelectorAll(".leg.invalid").forEach((l) => l.classList.remove("invalid"));
  }

  // ================================================================ Opción individual
  async function calculateSingle() {
    resetErrors();
    const payload = { ...O.formData(marketForm), ...O.formData(singleForm) };
    try {
      const data = await requestSingle(payload);
      if (!data) return;
      lastResult.single = { data, payload };
      renderSingle(data, payload);
    } catch (err) {
      showError(err, [marketForm, singleForm]);
    }
  }

  function moneyness(type, S, K) {
    const ratio = S / K;
    if (Math.abs(ratio - 1) < 0.005) return "En el dinero (ATM)";
    const itm = type === "call" ? S > K : S < K;
    return itm ? "Dentro del dinero (ITM)" : "Fuera del dinero (OTM)";
  }

  function renderSingle(data, payload) {
    const type = payload.option_type;
    out("price-label").textContent = `Prima ${type === "call" ? "call" : "put"} europea`;
    out("price").textContent = O.fmt(data.price);
    out("price-sub").textContent = `${O.fmtPct(data.price / Number(payload.spot))} del spot`;
    out("intrinsic").textContent = O.fmt(data.intrinsic);
    out("moneyness").textContent = moneyness(type, Number(payload.spot), Number(payload.strike));
    out("time_value").textContent = O.fmt(data.time_value);
    GREEKS.forEach((g) => (out(g).textContent = O.fmtSigned(data[g], 4)));
    out("d1").textContent = O.fmt(data.d1);
    out("d2").textContent = O.fmt(data.d2);
    out("call").textContent = O.fmt(data.call);
    out("put").textContent = O.fmt(data.put);
    out("parity").textContent = O.fmtSigned(data.call - data.put);
    drawPriceChart(data, payload);
  }

  function drawPriceChart(data, payload) {
    const { spots, prices, intrinsic } = data.curve;
    const spot = Number(payload.spot);
    O.plot(document.getElementById("price-chart"), [
      {
        x: spots, y: intrinsic, name: "Valor intrínseco", mode: "lines",
        line: { color: O.css("--muted"), width: 1.5, dash: "dot" },
        hovertemplate: "%{y:.4f}<extra>Intrínseco</extra>",
      },
      {
        x: spots, y: prices, name: "Prima Black-Scholes", mode: "lines",
        line: { color: O.css("--chart-1"), width: 2.5 },
        fill: "tonexty", fillcolor: hexToRgba(O.css("--chart-1"), 0.08),
        hovertemplate: "%{y:.4f}<extra>Prima</extra>",
      },
      {
        x: [spot], y: [data.price], name: "Spot actual", mode: "markers",
        marker: { size: 10, color: O.css("--chart-2"), line: { color: O.css("--surface"), width: 2 } },
        hovertemplate: "S₀ = %{x:.2f}<br>Prima = %{y:.4f}<extra></extra>",
      },
    ], O.chartLayout({
      xaxis: { title: { text: "Precio del subyacente" } },
      yaxis: { title: { text: "Valor de la opción" } },
      shapes: [vline(Number(payload.strike), O.css("--border-strong"))],
      annotations: [vlabel(Number(payload.strike), "K")],
    }));
  }

  // ================================================================ Estrategias
  function addLeg(leg = { side: "long", option_type: "call", strike: Number(marketForm.spot.value) || 100, quantity: 1 }) {
    if (legsBox.children.length >= maxLegs) return;
    const row = legTemplate.content.firstElementChild.cloneNode(true);
    row.querySelector('[name="side"]').value = leg.side;
    row.querySelector('[name="option_type"]').value = leg.option_type;
    row.querySelector('[name="strike"]').value = leg.strike;
    row.querySelector('[name="quantity"]').value = leg.quantity;
    row.dataset.side = leg.side;
    legsBox.appendChild(row);
    syncLegControls();
  }

  function syncLegControls() {
    const count = legsBox.children.length;
    addLegBtn.disabled = count >= maxLegs;
    legsBox.querySelectorAll("[data-remove]").forEach((b) => (b.disabled = count <= 1));
  }

  function applyPreset(key) {
    const preset = PRESETS[key];
    if (!preset) return;
    const spot = Number(marketForm.spot.value) || 100;
    legsBox.replaceChildren();
    for (const [option_type, side, mult] of preset.legs) {
      addLeg({ option_type, side, strike: Math.round(spot * mult * 100) / 100, quantity: 1 });
    }
  }

  function readLegs() {
    return [...legsBox.children].map((row) => ({
      side: row.querySelector('[name="side"]').value,
      option_type: row.querySelector('[name="option_type"]').value,
      strike: row.querySelector('[name="strike"]').value,
      quantity: row.querySelector('[name="quantity"]').value,
    }));
  }

  async function calculateStrategy() {
    resetErrors();
    const payload = { ...O.formData(marketForm), legs: readLegs() };
    try {
      const data = await requestStrategy(payload);
      if (!data) return;
      lastResult.strategy = { data, payload };
      renderStrategy(data, payload);
    } catch (err) {
      const match = /posición (\d+)/.exec(err.message);
      if (match) legsBox.children[Number(match[1]) - 1]?.classList.add("invalid");
      showError(err, [marketForm]);
    }
  }

  function renderStrategy(data, payload) {
    [...legsBox.children].forEach((row, i) => {
      const leg = data.legs[i];
      if (leg) row.querySelector("[data-premium]").textContent = O.fmt(leg.price);
    });

    const debit = data.net_premium >= 0;
    out("net-label").textContent = debit ? "Débito neto" : "Crédito neto";
    const net = out("net");
    net.textContent = O.fmt(Math.abs(data.net_premium));
    net.className = `kpi-value ${debit ? "negative" : "positive"}`;
    out("net-sub").textContent = debit ? "Prima total pagada" : "Prima total recibida";

    out("max_profit").textContent = data.max_profit === null ? "Ilimitada" : O.fmt(data.max_profit);
    out("max_loss").textContent = data.max_loss === null ? "Ilimitada" : O.fmt(data.max_loss);
    out("breakevens").textContent = data.breakevens.length
      ? data.breakevens.map((b) => O.fmt(b, 2)).join(" · ")
      : "Ninguno";
    GREEKS.forEach((g) => (out(`s-${g}`).textContent = O.fmtSigned(data.greeks[g], 4)));

    drawPayoff(data, payload);
  }

  function drawPayoff(data, payload) {
    const x = data.prices;
    const total = data.total_payoff;
    const legColors = ["--chart-3", "--chart-4", "--chart-5", "--chart-2"].map(O.css);
    const sideText = { long: "Compra", short: "Venta" };

    const traces = data.legs.map((leg, i) => ({
      x, y: data.leg_payoffs[i], mode: "lines", opacity: 0.85,
      name: `${sideText[leg.side]} ${leg.option_type} K=${O.fmt(leg.strike, 2)}${leg.quantity > 1 ? ` ×${leg.quantity}` : ""}`,
      line: { color: legColors[i % legColors.length], width: 1.5, dash: "dot" },
      hovertemplate: "%{y:.2f}",
    }));

    traces.push(
      {
        x, y: total.map((v) => Math.max(v, 0)), mode: "lines", showlegend: false, hoverinfo: "skip",
        line: { width: 0 }, fill: "tozeroy", fillcolor: hexToRgba(O.css("--positive"), 0.12),
      },
      {
        x, y: total.map((v) => Math.min(v, 0)), mode: "lines", showlegend: false, hoverinfo: "skip",
        line: { width: 0 }, fill: "tozeroy", fillcolor: hexToRgba(O.css("--negative"), 0.12),
      },
      {
        x, y: total, mode: "lines", name: "P&L total",
        line: { color: O.css("--text"), width: 2.75 },
        hovertemplate: "<b>%{y:.2f}</b>",
      }
    );

    const spot = Number(payload.spot);
    O.plot(document.getElementById("payoff-chart"), traces, O.chartLayout({
      xaxis: { title: { text: "Precio del subyacente al vencimiento" }, hoverformat: ".2f" },
      yaxis: { title: { text: "Ganancia / pérdida" }, zeroline: true, zerolinewidth: 1.5 },
      shapes: [
        vline(spot, O.css("--chart-2"), "dash"),
        ...data.breakevens.map((b) => vline(b, O.css("--border-strong"), "dot")),
      ],
      annotations: [vlabel(spot, "S₀")],
    }));
  }

  // ================================================================ Utilidades de gráficos
  function vline(x, color, dash = "dot") {
    return { type: "line", xref: "x", yref: "paper", x0: x, x1: x, y0: 0, y1: 1, line: { color, width: 1.25, dash } };
  }

  function vlabel(x, text) {
    return {
      x, y: 1, xref: "x", yref: "paper", text, showarrow: false, yanchor: "bottom",
      font: { family: "JetBrains Mono, monospace", size: 11, color: O.css("--text-2") },
    };
  }

  function hexToRgba(hex, alpha) {
    const h = hex.replace("#", "");
    const n = parseInt(h.length === 3 ? h.replace(/./g, "$&$&") : h, 16);
    return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`;
  }

  // ================================================================ Pestañas
  function setTab(tab) {
    activeTab = tab;
    document.querySelectorAll(".tab").forEach((b) => {
      const on = b.dataset.tab === tab;
      b.classList.toggle("active", on);
      b.setAttribute("aria-selected", on);
    });
    document.querySelectorAll(".tab-panel").forEach((p) => (p.hidden = p.dataset.panel !== tab));
    errorBox.hidden = true;
    history.replaceState(null, "", tab === "strategy" ? "#estrategias" : location.pathname);
    // Se recalcula al mostrarse: Plotly no puede medir un panel oculto.
    (tab === "single" ? calculateSingle : calculateStrategy)();
  }

  const calculateActive = () => (activeTab === "single" ? calculateSingle() : calculateStrategy());

  // ================================================================ Eventos
  document.querySelectorAll(".tab").forEach((b) => b.addEventListener("click", () => setTab(b.dataset.tab)));

  O.bindYieldField(marketForm, calculateActive);
  marketForm.addEventListener("submit", (e) => e.preventDefault());
  singleForm.addEventListener("submit", (e) => e.preventDefault());

  const debouncedActive = O.debounce(calculateActive, 300);
  marketForm.addEventListener("input", (e) => { if (e.target.type !== "radio") debouncedActive(); });

  const debouncedSingle = O.debounce(calculateSingle, 300);
  singleForm.addEventListener("input", (e) => { if (e.target.type !== "radio") debouncedSingle(); });
  singleForm.addEventListener("change", (e) => { if (e.target.type === "radio") calculateSingle(); });

  const debouncedStrategy = O.debounce(calculateStrategy, 300);
  legsBox.addEventListener("input", (e) => {
    const row = e.target.closest(".leg");
    if (e.target.name === "side") row.dataset.side = e.target.value;
    presetSelect.value = "";
    debouncedStrategy();
  });
  legsBox.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-remove]");
    if (!btn) return;
    btn.closest(".leg").remove();
    syncLegControls();
    presetSelect.value = "";
    calculateStrategy();
  });
  addLegBtn.addEventListener("click", () => {
    addLeg();
    presetSelect.value = "";
    calculateStrategy();
  });
  presetSelect.addEventListener("change", () => {
    if (!presetSelect.value) return;
    applyPreset(presetSelect.value);
    calculateStrategy();
  });

  document.addEventListener("themechange", () => {
    if (lastResult.single) drawPriceChart(lastResult.single.data, lastResult.single.payload);
    if (lastResult.strategy) drawPayoff(lastResult.strategy.data, lastResult.strategy.payload);
  });

  presetSelect.value = "bull_call_spread";
  applyPreset("bull_call_spread");
  setTab(location.hash === "#estrategias" ? "strategy" : "single");
})();
