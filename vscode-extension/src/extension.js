// VS Code extension: client của sơ đồ "VS Code -> Extension -> Proxy (Nginx) -> K8s".
const path = require("path");
const vscode = require("vscode");
const api = require("./api");
const { renderResult, renderHistory } = require("./webview");

const MIME = { ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".bmp": "image/bmp", ".webp": "image/webp" };

let statusItem;
let output;

function config() {
  const c = vscode.workspace.getConfiguration("vnTraffic");
  const target = c.get("target");
  return {
    target,
    baseUrl: target === "local" ? c.get("localUrl") : c.get("productionUrl"),
    conf: c.get("confidence"),
    timeoutMs: c.get("timeoutMs"),
    maxRetries: c.get("maxRetries"),
  };
}

async function refreshStatus() {
  const { target, baseUrl } = config();
  statusItem.text = `$(sync~spin) VN Traffic: ${target}`;
  try {
    const h = await api.health(baseUrl, 3000);
    statusItem.text = `$(pass) VN Traffic: ${target}`;
    statusItem.tooltip = `${baseUrl}\npod: ${h.served_by}\ndatabase: ${h.database ? "có" : "không"}\nBấm để đổi server`;
  } catch (e) {
    statusItem.text = `$(error) VN Traffic: ${target}`;
    statusItem.tooltip = `${baseUrl}\n${e.message}\nBấm để đổi server`;
  }
}

/** Ảnh cần gửi: từ menu chuột phải, từ tab xem ảnh đang mở, hoặc chọn file. */
async function pickImage(uri) {
  if (uri instanceof vscode.Uri) return uri;
  const tabInput = vscode.window.tabGroups.activeTabGroup.activeTab?.input;
  if (tabInput?.uri && MIME[path.extname(tabInput.uri.path).toLowerCase()]) return tabInput.uri;
  const picked = await vscode.window.showOpenDialog({
    canSelectMany: false,
    openLabel: "Phát hiện phương tiện",
    filters: { "Ảnh": Object.keys(MIME).map((e) => e.slice(1)) },
  });
  return picked?.[0];
}

async function detectImage(uri) {
  const imgUri = await pickImage(uri);
  if (!imgUri) return;
  const cfg = config();
  const filename = path.basename(imgUri.path);
  const mime = MIME[path.extname(filename).toLowerCase()] || "image/jpeg";
  const bytes = await vscode.workspace.fs.readFile(imgUri);

  let result;
  try {
    result = await vscode.window.withProgress(
      { location: vscode.ProgressLocation.Notification, title: `VN Traffic: gửi ${filename} tới ${cfg.target}` },
      (progress) =>
        api.predict(cfg.baseUrl, bytes, filename, {
          conf: cfg.conf,
          timeoutMs: cfg.timeoutMs,
          maxRetries: cfg.maxRetries,
          onRetry: (n, waitS) => progress.report({ message: `server quá tải (503), thử lại lần ${n} sau ${waitS}s…` }),
        }),
    );
  } catch (e) {
    output.appendLine(`[predict] ${filename}: ${e.message}`);
    vscode.window.showErrorMessage(`VN Traffic: ${e.message}`, "Đổi server").then((a) => a && switchTarget());
    return;
  }
  output.appendLine(
    `[predict] ${filename}: ${result.count} box, pod=${result.served_by}, inference=${result.inference_ms}ms, rtt=${result.round_trip_ms}ms, id=${result.id}`,
  );

  const panel = vscode.window.createWebviewPanel("vnTrafficResult", `🚦 ${filename}`, vscode.ViewColumn.Beside, {
    enableScripts: true,
  });
  panel.webview.html = renderResult({
    filename,
    imageDataUri: `data:${mime};base64,${Buffer.from(bytes).toString("base64")}`,
    result,
    target: cfg.target,
    baseUrl: cfg.baseUrl,
    cspSource: panel.webview.cspSource,
  });
}

async function showHistory() {
  const cfg = config();
  try {
    const [h, s] = await Promise.all([api.history(cfg.baseUrl, 30), api.stats(cfg.baseUrl)]);
    const panel = vscode.window.createWebviewPanel("vnTrafficHistory", "🚦 Lịch sử dự đoán", vscode.ViewColumn.Active, {});
    panel.webview.html = renderHistory({ items: h.items, stats: s, target: cfg.target, baseUrl: cfg.baseUrl, cspSource: panel.webview.cspSource });
  } catch (e) {
    vscode.window.showErrorMessage(`VN Traffic: không lấy được lịch sử — ${e.message}`);
  }
}

async function checkHealth() {
  const cfg = config();
  try {
    const h = await api.health(cfg.baseUrl, 5000);
    vscode.window.showInformationMessage(
      `VN Traffic (${cfg.target}): OK · pod ${h.served_by} · database ${h.database ? "có" : "không"} · classes ${h.classes.join(", ")}`,
    );
  } catch (e) {
    vscode.window.showErrorMessage(`VN Traffic (${cfg.target}): ${e.message}`);
  }
  refreshStatus();
}

async function switchTarget() {
  const c = vscode.workspace.getConfiguration("vnTraffic");
  const pick = await vscode.window.showQuickPick(
    [
      { label: "production", description: c.get("productionUrl"), detail: "Cụm Kubernetes sau Nginx proxy (ML Production Model)" },
      { label: "local", description: c.get("localUrl"), detail: "docker-compose trên máy (ML Local Model)" },
    ],
    { placeHolder: `Đang dùng: ${c.get("target")}` },
  );
  if (pick) await c.update("target", pick.label, vscode.ConfigurationTarget.Global);
}

function activate(context) {
  output = vscode.window.createOutputChannel("VN Traffic");
  statusItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  statusItem.command = "vnTraffic.switchTarget";
  statusItem.show();
  context.subscriptions.push(
    output,
    statusItem,
    vscode.commands.registerCommand("vnTraffic.detectImage", detectImage),
    vscode.commands.registerCommand("vnTraffic.showHistory", showHistory),
    vscode.commands.registerCommand("vnTraffic.checkHealth", checkHealth),
    vscode.commands.registerCommand("vnTraffic.switchTarget", switchTarget),
    vscode.workspace.onDidChangeConfiguration((e) => e.affectsConfiguration("vnTraffic") && refreshStatus()),
  );
  refreshStatus();
}

function deactivate() {}

module.exports = { activate, deactivate };
