// node --test test/   (VN_TRAFFIC_URL=http://localhost:8088 để chạy thêm test gọi API thật)
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const api = require("../src/api");
const { renderResult, renderHistory } = require("../src/webview");

const RESULT = {
  detections: [
    { bbox: [10, 20, 110, 220], class: "car", class_id: 1, confidence: 0.91 },
    { bbox: [5, 5, 50, 80], class: "motorcycle", class_id: 0, confidence: 0.4 },
  ],
  count: 2, image_size: [640, 480], inference_ms: 170.2, served_by: "pod-a", id: 7, round_trip_ms: 200, attempts: 1,
};

test("predict thử lại khi 503 + Retry-After rồi thành công", async () => {
  const realFetch = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async () => {
    calls++;
    if (calls < 3) return new Response(JSON.stringify({ error: "quá tải" }), { status: 503, headers: { "Retry-After": "0" } });
    return new Response(JSON.stringify({ ...RESULT }), { status: 200 });
  };
  try {
    const retries = [];
    const r = await api.predict("http://x", new Uint8Array([1, 2]), "a.jpg", { onRetry: (n) => retries.push(n) });
    assert.strictEqual(r.attempts, 3);
    assert.deepStrictEqual(retries, [1, 2]);
  } finally {
    globalThis.fetch = realFetch;
  }
});

test("predict báo lỗi rõ khi hết lượt thử", async () => {
  const realFetch = globalThis.fetch;
  globalThis.fetch = async () => new Response(JSON.stringify({ error: "quá tải" }), { status: 503, headers: { "Retry-After": "0" } });
  try {
    await assert.rejects(api.predict("http://x", new Uint8Array([1]), "a.jpg", { maxRetries: 1 }), /HTTP 503: quá tải/);
  } finally {
    globalThis.fetch = realFetch;
  }
});

test("renderResult escape tên file và không để JSON phá thẻ script", () => {
  const evil = { ...RESULT, detections: [{ ...RESULT.detections[0], class: "car" }], served_by: "</script><b>x" };
  const html = renderResult({ filename: '<img src=x onerror=alert(1)>.jpg', imageDataUri: "data:image/jpeg;base64,AA==", result: evil, target: "production", baseUrl: "http://h" });
  assert.ok(!html.includes("<img src=x"));
  assert.ok(!html.includes("</script><b>"));
  assert.match(html, /Content-Security-Policy/);
  assert.match(html, /lưu DB #7/);
});

test("renderHistory hiển thị thống kê và bảng", () => {
  const html = renderHistory({
    items: [{ id: 1, created_at: "2026-11-02T10:00:00+00:00", filename: "a.jpg", n_detections: 2, counts: { car: 2 }, inference_ms: 170, served_by: "pod-a", client: "vscode" }],
    stats: { predictions: 1, detections: 2, avg_inference_ms: 170, by_class: { car: 2 }, by_pod: { "pod-a": 1 } },
    target: "production", baseUrl: "http://h",
  });
  assert.match(html, /pod-a/);
  assert.match(html, /Số lần dự đoán/);
});

const LIVE = process.env.VN_TRAFFIC_URL;
const IMG_DIR = "/home/xuand/vn_traffic_ai/data/merged_v5/images/test";

test("gọi API thật: health, predict, history", { skip: !LIVE && "chưa đặt VN_TRAFFIC_URL" }, async () => {
  const h = await api.health(LIVE);
  assert.strictEqual(h.status, "ok");
  const file = fs.readdirSync(IMG_DIR).find((f) => f.endsWith(".jpg"));
  const r = await api.predict(LIVE, fs.readFileSync(path.join(IMG_DIR, file)), file);
  assert.ok(r.count > 0 && r.served_by);
  if (h.database) {
    const hist = await api.history(LIVE, 5);
    assert.strictEqual(hist.items[0].id, r.id);
    assert.strictEqual(hist.items[0].client, api.USER_AGENT);
  }
});
