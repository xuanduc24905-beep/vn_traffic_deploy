// Sinh HTML cho webview (không phụ thuộc vscode -> test được bằng node thuần).

// Màu cố định theo class_id (bảng màu categorical đã kiểm CVD), không đổi theo số lượng.
const CLASS_COLORS = { motorcycle: "#2a78d6", car: "#eb6834", bus: "#1baf7a", truck: "#eda100" };
const CLASS_ORDER = ["motorcycle", "car", "bus", "truck"];

const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
// JSON nhúng vào <script>: chặn "</script>" và ký tự đóng thẻ
const jsonForScript = (v) => JSON.stringify(v).replace(/</g, "\\u003c");

function nonce() {
  let s = "";
  const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  for (let i = 0; i < 32; i++) s += chars[Math.floor(Math.random() * chars.length)];
  return s;
}

function shell(title, body, n, cspSource) {
  return `<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src ${cspSource} data:; style-src 'unsafe-inline'; script-src 'nonce-${n}';">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${esc(title)}</title>
<style>
  body { font-family: var(--vscode-font-family); color: var(--vscode-foreground); background: var(--vscode-editor-background); padding: 12px 16px; }
  h2 { font-size: 1.15em; margin: 0 0 4px; }
  .meta { color: var(--vscode-descriptionForeground); font-size: 0.92em; margin-bottom: 12px; }
  .tiles { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
  .tile { border: 1px solid var(--vscode-panel-border); border-radius: 6px; padding: 6px 12px; min-width: 92px; }
  .tile .v { font-size: 1.5em; font-weight: 600; }
  .tile .k { color: var(--vscode-descriptionForeground); font-size: 0.85em; display: flex; align-items: center; gap: 6px; }
  .sw { width: 10px; height: 10px; border-radius: 2px; display: inline-block; flex: none; }
  .wrap { position: relative; display: inline-block; max-width: 100%; }
  canvas { max-width: 100%; height: auto; border-radius: 4px; display: block; }
  #tip { position: absolute; pointer-events: none; background: var(--vscode-editorHoverWidget-background); color: var(--vscode-editorHoverWidget-foreground);
         border: 1px solid var(--vscode-editorHoverWidget-border); padding: 4px 8px; border-radius: 4px; font-size: 0.9em; display: none; white-space: nowrap; }
  .controls { margin: 10px 0; display: flex; align-items: center; gap: 10px; }
  table { border-collapse: collapse; margin-top: 8px; font-size: 0.92em; }
  th, td { text-align: left; padding: 3px 10px 3px 0; border-bottom: 1px solid var(--vscode-panel-border); }
  td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
  .bar { height: 10px; border-radius: 0 4px 4px 0; display: inline-block; vertical-align: middle; }
  .err { color: var(--vscode-errorForeground); }
</style>
</head>
<body>${body}</body>
</html>`;
}

function countByClass(dets) {
  const c = Object.fromEntries(CLASS_ORDER.map((k) => [k, 0]));
  for (const d of dets) c[d.class] = (c[d.class] || 0) + 1;
  return c;
}

/** Kết quả 1 ảnh: ảnh + bbox (canvas), ô đếm theo class, lọc theo confidence, bảng chi tiết. */
function renderResult({ filename, imageDataUri, result, target, baseUrl, cspSource = "" }) {
  const n = nonce();
  const counts = countByClass(result.detections);
  const tiles = CLASS_ORDER.map(
    (k) => `<div class="tile"><div class="k"><span class="sw" style="background:${CLASS_COLORS[k]}"></span>${k}</div><div class="v" data-count="${k}">${counts[k]}</div></div>`,
  ).join("");
  const minConf = Math.min(...result.detections.map((d) => d.confidence), 1);
  const body = `
<h2>${esc(filename)} — ${result.count} phương tiện</h2>
<div class="meta">
  Server <b>${esc(target)}</b> (${esc(baseUrl)}) · pod <b>${esc(result.served_by || "?")}</b> ·
  inference ${result.inference_ms} ms · round-trip ${result.round_trip_ms} ms${result.attempts > 1 ? ` · thử ${result.attempts} lần (503)` : ""} ·
  ${result.id != null ? `lưu DB #${result.id}` : "không lưu DB"} · ảnh ${result.image_size[0]}×${result.image_size[1]}
</div>
<div class="tiles">${tiles}</div>
<div class="controls">
  <label for="conf">Chỉ hiện confidence ≥ <b id="confv">${minConf.toFixed(2)}</b></label>
  <input id="conf" type="range" min="${Math.floor(minConf * 100) / 100}" max="1" step="0.01" value="${Math.floor(minConf * 100) / 100}">
</div>
<div class="wrap"><canvas id="cv"></canvas><div id="tip"></div></div>
<table>
  <thead><tr><th>#</th><th>Class</th><th class="num">Confidence</th><th class="num">x1</th><th class="num">y1</th><th class="num">x2</th><th class="num">y2</th></tr></thead>
  <tbody>${result.detections
    .map(
      (d, i) =>
        `<tr data-i="${i}"><td>${i + 1}</td><td><span class="sw" style="background:${CLASS_COLORS[d.class]}"></span> ${esc(d.class)}</td><td class="num">${d.confidence.toFixed(3)}</td>${d.bbox
          .map((v) => `<td class="num">${v}</td>`)
          .join("")}</tr>`,
    )
    .join("")}</tbody>
</table>
<script nonce="${n}">
const DETS = ${jsonForScript(result.detections)};
const COLORS = ${jsonForScript(CLASS_COLORS)};
const cv = document.getElementById("cv"), ctx = cv.getContext("2d"), tip = document.getElementById("tip");
const slider = document.getElementById("conf"), confv = document.getElementById("confv");
const img = new Image();
let hover = -1;
function visible() { const t = +slider.value; return DETS.map((d, i) => [d, i]).filter(([d]) => d.confidence >= t); }
function draw() {
  ctx.drawImage(img, 0, 0);
  const lw = Math.max(2, Math.round(img.width / 640));
  const counts = {};
  for (const [d, i] of visible()) {
    counts[d.class] = (counts[d.class] || 0) + 1;
    const [x1, y1, x2, y2] = d.bbox;
    ctx.lineWidth = lw + 2; ctx.strokeStyle = "rgba(0,0,0,0.55)"; ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
    ctx.lineWidth = i === hover ? lw * 2 : lw; ctx.strokeStyle = COLORS[d.class]; ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
  }
  document.querySelectorAll("[data-count]").forEach((el) => (el.textContent = counts[el.dataset.count] || 0));
  document.querySelectorAll("tbody tr").forEach((tr) => (tr.style.opacity = DETS[+tr.dataset.i].confidence >= +slider.value ? 1 : 0.35));
}
img.onload = () => { cv.width = img.width; cv.height = img.height; draw(); };
img.src = ${jsonForScript(imageDataUri)};
slider.addEventListener("input", () => { confv.textContent = (+slider.value).toFixed(2); draw(); });
cv.addEventListener("mousemove", (e) => {
  const r = cv.getBoundingClientRect(), sx = cv.width / r.width, x = (e.clientX - r.left) * sx, y = (e.clientY - r.top) * sx;
  // box nhỏ nhất chứa con trỏ (vùng hover lớn hơn box 6px để dễ trỏ)
  let best = -1, area = Infinity;
  for (const [d, i] of visible()) {
    const [x1, y1, x2, y2] = d.bbox, pad = 6 * sx;
    if (x >= x1 - pad && x <= x2 + pad && y >= y1 - pad && y <= y2 + pad && (x2 - x1) * (y2 - y1) < area) { best = i; area = (x2 - x1) * (y2 - y1); }
  }
  if (best !== hover) { hover = best; draw(); }
  if (best >= 0) {
    const d = DETS[best];
    tip.textContent = d.class + " · " + (d.confidence * 100).toFixed(1) + "% · [" + d.bbox.join(", ") + "]";
    tip.style.display = "block"; tip.style.left = (e.clientX - r.left + 12) + "px"; tip.style.top = (e.clientY - r.top + 12) + "px";
  } else tip.style.display = "none";
});
cv.addEventListener("mouseleave", () => { hover = -1; tip.style.display = "none"; draw(); });
</script>`;
  return shell(`VN Traffic — ${filename}`, body, n, cspSource);
}

/** Lịch sử: thống kê tổng (từ /stats) + bảng các lần dự đoán gần nhất (từ /history). */
function renderHistory({ items, stats, target, baseUrl, cspSource = "" }) {
  const n = nonce();
  const maxClass = Math.max(1, ...Object.values(stats.by_class || {}));
  const classRows = CLASS_ORDER.map((k) => {
    const v = stats.by_class?.[k] || 0;
    return `<tr><td><span class="sw" style="background:${CLASS_COLORS[k]}"></span> ${k}</td><td class="num">${v}</td>
      <td><span class="bar" style="width:${Math.round((v / maxClass) * 220)}px;background:${CLASS_COLORS[k]}"></span></td></tr>`;
  }).join("");
  const podRows = Object.entries(stats.by_pod || {})
    .map(([pod, c]) => `<tr><td>${esc(pod)}</td><td class="num">${c}</td></tr>`)
    .join("");
  const rows = items
    .map((it) => {
      const counts = CLASS_ORDER.map((k) => `<td class="num">${it.counts?.[k] || 0}</td>`).join("");
      return `<tr><td class="num">${it.id}</td><td>${esc(new Date(it.created_at).toLocaleString("vi-VN"))}</td><td>${esc(it.filename)}</td>
        <td class="num">${it.n_detections}</td>${counts}<td class="num">${it.inference_ms?.toFixed(1)}</td><td>${esc(it.served_by)}</td><td>${esc(it.client)}</td></tr>`;
    })
    .join("");
  const body = `
<h2>Lịch sử dự đoán</h2>
<div class="meta">Server <b>${esc(target)}</b> (${esc(baseUrl)}) · PostgreSQL</div>
<div class="tiles">
  <div class="tile"><div class="k">Số lần dự đoán</div><div class="v">${stats.predictions}</div></div>
  <div class="tile"><div class="k">Phương tiện phát hiện</div><div class="v">${stats.detections}</div></div>
  <div class="tile"><div class="k">Inference TB</div><div class="v">${stats.avg_inference_ms ?? "–"} ms</div></div>
</div>
<div style="display:flex;flex-wrap:wrap;gap:32px">
  <div><b>Theo class</b><table><tbody>${classRows}</tbody></table></div>
  <div><b>Theo pod xử lý</b><table><thead><tr><th>Pod</th><th class="num">Lần</th></tr></thead><tbody>${podRows || "<tr><td>–</td></tr>"}</tbody></table></div>
</div>
<p><b>${items.length} lần gần nhất</b></p>
<table>
  <thead><tr><th class="num">ID</th><th>Thời gian</th><th>File</th><th class="num">Tổng</th>${CLASS_ORDER.map((k) => `<th class="num">${k}</th>`).join("")}
  <th class="num">Inference (ms)</th><th>Pod</th><th>Client</th></tr></thead>
  <tbody>${rows || `<tr><td colspan="11">Chưa có dữ liệu</td></tr>`}</tbody>
</table>`;
  return shell("VN Traffic — Lịch sử", body, n, cspSource);
}

module.exports = { renderResult, renderHistory, CLASS_COLORS, esc };
