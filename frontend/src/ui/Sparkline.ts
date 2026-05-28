export function renderSparkline(
  values: number[],
  width = 120,
  height = 26,
  fillBelow = false,
): SVGElement {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", String(width));
  svg.setAttribute("height", String(height));
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.style.display = "block";

  if (values.length < 2) return svg;

  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const step = width / (values.length - 1);

  const points = values.map((v, i) => ({
    x: i * step,
    y: height - ((v - min) / range) * height,
  }));

  const d = points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");

  if (fillBelow) {
    const fill = document.createElementNS("http://www.w3.org/2000/svg", "path");
    fill.setAttribute("d", `${d} L${width},${height} L0,${height} Z`);
    fill.setAttribute("fill", "var(--accent)");
    fill.setAttribute("opacity", "0.10");
    svg.appendChild(fill);
  }

  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", d);
  path.setAttribute("fill", "none");
  path.setAttribute("stroke", "var(--accent)");
  path.setAttribute("stroke-width", "1.4");
  path.setAttribute("stroke-linejoin", "round");
  path.setAttribute("stroke-linecap", "round");
  svg.appendChild(path);

  const last = points[points.length - 1];
  const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
  dot.setAttribute("cx", last.x.toFixed(1));
  dot.setAttribute("cy", last.y.toFixed(1));
  dot.setAttribute("r", "2");
  dot.setAttribute("fill", "var(--accent)");
  svg.appendChild(dot);

  return svg;
}
