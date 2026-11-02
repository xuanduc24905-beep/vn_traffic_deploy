// Client HTTP cho API (không phụ thuộc vscode -> test được bằng node thuần).
// Dùng fetch/FormData/Blob có sẵn trong Node 18+ (extension host của VS Code).

const USER_AGENT = "vscode-vn-traffic/0.1.0";

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(url, init = {}, timeoutMs = 30000) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(url, {
      ...init,
      headers: { "User-Agent": USER_AGENT, ...(init.headers || {}) },
      signal: ctrl.signal,
    });
    const text = await res.text();
    let body;
    try {
      body = JSON.parse(text);
    } catch {
      body = { error: text.slice(0, 200) };
    }
    return { res, body };
  } catch (e) {
    if (e.name === "AbortError") throw new ApiError(`Hết thời gian chờ (${timeoutMs} ms): ${url}`, 0);
    throw new ApiError(`Không kết nối được ${url}: ${e.cause?.code || e.message}`, 0);
  } finally {
    clearTimeout(timer);
  }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/**
 * Gửi ảnh lên POST /predict.
 * Server trả 503 + Retry-After khi quá tải (backpressure) -> chờ rồi thử lại tối đa maxRetries lần.
 */
async function predict(baseUrl, bytes, filename, { conf = 0.25, timeoutMs = 30000, maxRetries = 3, onRetry } = {}) {
  const url = `${baseUrl.replace(/\/$/, "")}/predict?conf=${encodeURIComponent(conf)}`;
  for (let attempt = 0; ; attempt++) {
    const form = new FormData();
    form.append("file", new Blob([bytes]), filename);
    const t0 = Date.now();
    const { res, body } = await request(url, { method: "POST", body: form }, timeoutMs);
    if (res.ok) return { ...body, round_trip_ms: Date.now() - t0, attempts: attempt + 1 };
    if (res.status === 503 && attempt < maxRetries) {
      const waitS = Number(res.headers.get("retry-after")) || 1;
      onRetry?.(attempt + 1, waitS);
      await sleep(waitS * 1000);
      continue;
    }
    throw new ApiError(`HTTP ${res.status}: ${body.error || "lỗi không rõ"}`, res.status);
  }
}

async function getJson(baseUrl, path, timeoutMs = 10000) {
  const { res, body } = await request(`${baseUrl.replace(/\/$/, "")}${path}`, {}, timeoutMs);
  if (!res.ok) throw new ApiError(`HTTP ${res.status}: ${body.error || "lỗi không rõ"}`, res.status);
  return body;
}

const health = (baseUrl, timeoutMs) => getJson(baseUrl, "/health", timeoutMs);
const history = (baseUrl, limit = 30) => getJson(baseUrl, `/history?limit=${limit}`);
const stats = (baseUrl) => getJson(baseUrl, "/stats");

module.exports = { ApiError, predict, health, history, stats, USER_AGENT };
