(function () {
  "use strict";

  const O = window.Opciones;
  const form = document.getElementById("binomial-form");
  const errorBox = document.getElementById("binomial-error");
  const treeSvg = document.getElementById("tree");
  const convergenceEl = document.getElementById("convergence-chart");
  const out = (key) => document.querySelector(`[data-out="${key}"]`);
  const request = O.apiClient("/api/binomial");

  const LABELS = {
    call: "Call", put: "Put", european: "europea", american: "americana",
  };

  let last = null;

  async function calculate() {
    O.clearErrors(form);
    errorBox.hidden = true;
    const payload = O.formData(form);
    try {
      const data = await request(payload);
      if (!data) return;
      last = { data, payload };
      render(data, payload);
    } catch (err) {
      if (!O.showFieldError(form, err.field, err.message)) {
        errorBox.textContent = err.message;
        errorBox.hidden = false;
      }
    }
  }

  function render(data, payload) {
    const american = payload.exercise === "american";
    out("price").textContent = O.fmt(data.price);
    out("price-sub").textContent =
      `${LABELS[payload.option_type]} ${LABELS[payload.exercise]} · N = ${O.fmt(Number(payload.steps), 0)} pasos`;
    out("black_scholes").textContent = O.fmt(data.black_scholes);
    out("bs-sub").textContent = american ? "Europea equivalente (cota inferior)" : "Solución cerrada";

    const diff = data.price - data.black_scholes;
    out("diff-label").textContent = american ? "Prima por ejercicio anticipado" : "Error de discretización";
    out("diff").textContent = O.fmtSigned(diff);
    out("diff-sub").textContent = american
      ? "Americana binomial − europea Black-Scholes"
      : `${O.fmtSigned((diff / data.black_scholes) * 100, 3)} % frente a Black-Scholes`;

    out("dt").textContent = O.fmt(data.dt, 5);
    out("u").textContent = O.fmt(data.u, 5);
    out("d").textContent = O.fmt(data.d, 5);
    out("p").textContent = O.fmt(data.p, 5);
    out("discount").textContent = O.fmt(data.discount, 5);

    const t = data.tree;
    out("tree-note").textContent = t.truncated
      ? `Se muestran los primeros ${t.steps} pasos, recalculados como un árbol de ${t.steps} pasos sobre el mismo vencimiento. El precio principal usa los ${payload.steps} pasos.`
      : "Cada nodo muestra el precio del subyacente (arriba) y el valor de la opción (abajo).";
    drawTree(t.nodes);
    drawConvergence(data);
  }

  // ------------------------------------------------------------ Árbol en SVG
  const SVG_NS = "http://www.w3.org/2000/svg";
  const BOX_W = 86, BOX_H = 40, COL_W = 106, ROW_H = 50, PAD = 12, LABEL_H = 22;

  function el(name, attrs, parent) {
    const node = document.createElementNS(SVG_NS, name);
    for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
    parent?.appendChild(node);
    return node;
  }

  function drawTree(nodes) {
    const N = nodes.length - 1;
    const width = PAD * 2 + N * COL_W + BOX_W;
    const height = PAD * 2 + LABEL_H + N * ROW_H + BOX_H;
    const centerY = PAD + LABEL_H + (N * ROW_H) / 2 + BOX_H / 2;
    const pos = (i, j) => ({ x: PAD + i * COL_W + BOX_W / 2, y: centerY + (j - i / 2) * ROW_H });

    treeSvg.replaceChildren();
    // Se escala al ancho del panel sin crecer más que su tamaño natural.
    treeSvg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    treeSvg.style.maxWidth = `${width}px`;

    const edges = el("g", {}, treeSvg);
    const layer = el("g", {}, treeSvg);

    nodes.forEach((column, i) => {
      el("text", { x: pos(i, 0).x, y: PAD + 10, "text-anchor": "middle", class: "step-label" }, layer)
        .textContent = i === 0 ? "Hoy" : `Paso ${i}`;

      column.forEach((node, j) => {
        const { x, y } = pos(i, j);
        if (i < N) {
          for (const k of [j, j + 1]) {
            const next = pos(i + 1, k);
            el("path", {
              class: "edge",
              d: `M${x + BOX_W / 2} ${y} C${x + BOX_W / 2 + 14} ${y} ${next.x - BOX_W / 2 - 14} ${next.y} ${next.x - BOX_W / 2} ${next.y}`,
            }, edges);
          }
        }
        const g = el("g", { class: `node${node.early ? " early" : ""}${i === 0 ? " root" : ""}` }, layer);
        el("title", {}, g).textContent =
          `Paso ${i}, nodo ${j}\nSubyacente: ${O.fmt(node.stock)}\nOpción: ${O.fmt(node.value)}` +
          (node.early ? "\nConviene ejercer anticipadamente" : "");
        el("rect", { x: x - BOX_W / 2, y: y - BOX_H / 2, width: BOX_W, height: BOX_H, rx: 7 }, g);
        el("text", { x, y: y - 4, "text-anchor": "middle", class: "stock" }, g).textContent = O.fmt(node.stock, 2);
        el("text", { x, y: y + 13, "text-anchor": "middle", class: "value" }, g).textContent = O.fmt(node.value, 3);
      });
    });
  }

  // ------------------------------------------------------------ Convergencia
  function drawConvergence(data) {
    const { steps, prices } = data.convergence;
    O.plot(convergenceEl, [
      {
        x: steps, y: prices, name: "Prima binomial", mode: "lines+markers",
        line: { color: O.css("--chart-1"), width: 2.5 },
        marker: { size: 7, color: O.css("--surface"), line: { color: O.css("--chart-1"), width: 2 } },
        hovertemplate: "%{y:.4f}<extra>Binomial</extra>",
      },
      {
        x: [steps[0], steps[steps.length - 1]], y: [data.black_scholes, data.black_scholes],
        name: "Black-Scholes (europea)", mode: "lines",
        line: { color: O.css("--chart-2"), width: 2, dash: "dash" },
        hovertemplate: "%{y:.4f}<extra>Black-Scholes</extra>",
      },
    ], O.chartLayout({
      xaxis: { type: "log", title: { text: "Número de pasos (escala log)" }, tickmode: "array", tickvals: steps, ticktext: steps.map(String) },
      yaxis: { title: { text: "Prima" }, tickformat: ".3f" },
    }));
  }

  // ------------------------------------------------------------ Eventos
  O.bindYieldField(form, calculate);
  form.addEventListener("submit", (e) => { e.preventDefault(); calculate(); });
  const debounced = O.debounce(calculate, 350);
  form.addEventListener("input", (e) => { if (e.target.type !== "radio") debounced(); });
  // El radio "asset" ya recalcula a través de bindYieldField.
  form.addEventListener("change", (e) => { if (e.target.type === "radio" && e.target.name !== "asset") calculate(); });
  document.addEventListener("themechange", () => last && drawConvergence(last.data));

  calculate();
})();
