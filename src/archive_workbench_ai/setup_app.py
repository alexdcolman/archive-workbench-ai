from __future__ import annotations

from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import secrets
import shutil
import threading
import time
from typing import Any
import urllib.parse
import webbrowser

from . import __version__
from .bridge import bridge_status, start_bridge
from .catalog import PROFILE_DEFAULT_MODELS, data_root
from .managed_paths import default_bridge_root, managed_executable_candidates
from .model_store import inspect_model, pull_model
from .runtime import gpu_info
from .runtime_manager import install_runtime, runtime_installation_report

_SETUP_TITLE = "Archive Workbench AI Setup"
_DEFAULT_IDLE_SECONDS = 30 * 60


def _data_root_free_bytes() -> int | None:
    target = data_root()
    probe = target
    while not probe.exists() and probe.parent != probe:
        probe = probe.parent
    try:
        return int(shutil.disk_usage(probe).free)
    except OSError:
        return None


def _suggested_profile(gpus: list[dict[str, object]]) -> str:
    for gpu in gpus:
        memory = gpu.get("memory_total_mib")
        if isinstance(memory, int) and memory >= 20 * 1024:
            return "H24"
    return "L12"


def setup_status() -> dict[str, Any]:
    gpus = gpu_info()
    runtime = runtime_installation_report()
    models: dict[str, dict[str, object]] = {}
    for profile, spec in PROFILE_DEFAULT_MODELS.items():
        models[profile] = inspect_model(spec, verify=False)
    bridge = bridge_status(default_bridge_root())
    free = _data_root_free_bytes()
    return {
        "application": "archive-workbench-ai",
        "version": __version__,
        "data_root": str(data_root()),
        "bridge_root": str(default_bridge_root()),
        "managed_executable_candidates": [str(path) for path in managed_executable_candidates()],
        "runtime": runtime,
        "models": models,
        "gpus": gpus,
        "suggested_profile": _suggested_profile(gpus),
        "free_bytes": free,
        "bridge": bridge,
        "network_required_for_setup": True,
        "network_required_for_inference": False,
    }


@dataclass(slots=True)
class SetupOperation:
    state: str = "idle"
    action: str | None = None
    profile: str | None = None
    message: str = ""
    error: str | None = None
    started_at: float | None = None
    finished_at: float | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def payload(self) -> dict[str, Any]:
        with self._lock:
            return {
                "state": self.state,
                "action": self.action,
                "profile": self.profile,
                "message": self.message,
                "error": self.error,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
            }

    def start(self, action: str, profile: str | None = None) -> bool:
        with self._lock:
            if self.state == "running":
                return False
            self.state = "running"
            self.action = action
            self.profile = profile
            self.message = "Preparando…"
            self.error = None
            self.started_at = time.time()
            self.finished_at = None
        thread = threading.Thread(
            target=self._run,
            args=(action, profile),
            name="aw-ai-setup-operation",
            daemon=True,
        )
        thread.start()
        return True

    def _set_message(self, message: str) -> None:
        with self._lock:
            self.message = message

    def _run(self, action: str, profile: str | None) -> None:
        try:
            if action == "prepare_profile":
                if profile not in PROFILE_DEFAULT_MODELS:
                    raise ValueError("Perfil desconocido")
                self._set_message("Instalando o comprobando el runtime local…")
                install_runtime(variant="auto", force=False, allow_source_build=False)
                self._set_message(f"Descargando o comprobando el modelo {profile}…")
                pull_model(PROFILE_DEFAULT_MODELS[profile])
                self._set_message("Activando el compañero local de Archive Workbench…")
                start_bridge(default_bridge_root())
                result = f"Perfil {profile} preparado."
            elif action == "install_runtime":
                self._set_message("Instalando o comprobando el runtime local…")
                install_runtime(variant="auto", force=False, allow_source_build=False)
                result = "Runtime preparado."
            elif action == "repair_runtime":
                self._set_message("Reinstalando el runtime local…")
                install_runtime(variant="auto", force=True, allow_source_build=False)
                result = "Runtime reparado."
            elif action == "install_model":
                if profile not in PROFILE_DEFAULT_MODELS:
                    raise ValueError("Perfil desconocido")
                self._set_message(f"Descargando o comprobando el modelo {profile}…")
                pull_model(PROFILE_DEFAULT_MODELS[profile])
                result = f"Modelo {profile} preparado."
            elif action == "start_bridge":
                self._set_message("Activando el compañero local…")
                start_bridge(default_bridge_root())
                result = "Compañero local activo."
            else:
                raise ValueError(f"Acción desconocida: {action}")
            with self._lock:
                self.state = "complete"
                self.message = result
                self.finished_at = time.time()
        except Exception as exc:  # UI boundary; surfaced as controlled text
            with self._lock:
                self.state = "error"
                self.message = "No se pudo completar la operación."
                self.error = str(exc)
                self.finished_at = time.time()


_HTML = r'''<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Archive Workbench AI Setup</title>
<style>
:root { color-scheme: light dark; font-family: system-ui, sans-serif; }
body { margin: 0; background: Canvas; color: CanvasText; }
main { max-width: 900px; margin: 0 auto; padding: 32px 20px 64px; }
h1 { font-size: 1.8rem; margin: 0 0 8px; }
p { line-height: 1.5; }
.grid { display: grid; grid-template-columns: repeat(auto-fit,minmax(260px,1fr)); gap: 14px; margin: 22px 0; }
.card { border: 1px solid color-mix(in srgb, CanvasText 20%, transparent); border-radius: 12px; padding: 16px; }
.card h2 { font-size: 1.05rem; margin-top: 0; }
.small { font-size: .9rem; opacity: .8; }
.good { font-weight: 650; }
.warn { font-weight: 650; }
button { padding: 10px 14px; border-radius: 8px; border: 1px solid color-mix(in srgb, CanvasText 30%, transparent); cursor: pointer; margin: 4px 6px 4px 0; }
button.primary { font-weight: 700; }
button:disabled { opacity: .5; cursor: default; }
#op { white-space: pre-wrap; border-left: 4px solid color-mix(in srgb, CanvasText 35%, transparent); padding: 10px 12px; margin: 18px 0; }
code { overflow-wrap: anywhere; }
footer { margin-top: 28px; opacity: .75; font-size: .9rem; }
</style>
</head>
<body><main>
<h1>Archive Workbench AI Setup</h1>
<p>Prepará el motor local de análisis asistido. Runtime y modelos se descargan sólo cuando elegís una acción. Después de instalarlos, la inferencia funciona localmente.</p>
<div id="summary" class="grid"></div>
<div class="card">
<h2>Preparar un perfil</h2>
<p class="small">L12 usa menos memoria. H24 está pensado para equipos con mayor memoria disponible. La sugerencia automática es orientativa.</p>
<button class="primary" onclick="act('prepare_profile','L12')">Preparar L12</button>
<button class="primary" onclick="act('prepare_profile','H24')">Preparar H24</button>
</div>
<div class="card">
<h2>Mantenimiento</h2>
<button onclick="act('install_runtime')">Comprobar runtime</button>
<button onclick="act('repair_runtime')">Reparar runtime</button>
<button onclick="act('start_bridge')">Activar compañero local</button>
<a href="/diagnostics.json" download><button>Descargar diagnóstico</button></a>
</div>
<div id="op">Sin operaciones en curso.</div>
<button onclick="closeSetup()">Cerrar Setup</button>
<footer>Archive Workbench AI <span id="version"></span>. El Setup sólo escucha en esta computadora.</footer>
</main>
<script>
const TOKEN = "__TOKEN__";
async function getJSON(path){ const r=await fetch(path,{cache:'no-store'}); return await r.json(); }
function fmtGiB(n){ return n==null?'No disponible':(n/1073741824).toFixed(1)+' GiB'; }
async function refresh(){
  const s=await getJSON('/api/status'); document.getElementById('version').textContent=s.version;
  const rt=s.runtime; const bridge=s.bridge;
  const modelL=s.models.L12; const modelH=s.models.H24;
  document.getElementById('summary').innerHTML = `
    <div class="card"><h2>Equipo</h2><p>Perfil sugerido: <strong>${s.suggested_profile}</strong></p><p class="small">GPU: ${s.gpus.length ? s.gpus.map(g=>g.name).join(', ') : 'sin NVIDIA detectada'}</p><p class="small">Espacio libre: ${fmtGiB(s.free_bytes)}</p></div>
    <div class="card"><h2>Runtime</h2><p class="${rt.installed?'good':'warn'}">${rt.installed?'Instalado':'Pendiente'}</p><p class="small">Variante sugerida: ${rt.recommended_variant}</p></div>
    <div class="card"><h2>Modelos</h2><p>L12: <strong>${modelL.installed?'instalado':'pendiente'}</strong></p><p>H24: <strong>${modelH.installed?'instalado':'pendiente'}</strong></p></div>
    <div class="card"><h2>Integración con Archive Workbench</h2><p class="${bridge.running?'good':'warn'}">${bridge.running?'Compañero activo':'Compañero detenido'}</p><p class="small">${s.bridge_root}</p></div>`;
  const op=await getJSON('/api/operation');
  const el=document.getElementById('op');
  if(op.state==='running') el.textContent=op.message;
  else if(op.state==='error') el.textContent=op.message+'\n\n'+(op.error||'');
  else if(op.state==='complete') el.textContent=op.message;
  else el.textContent='Sin operaciones en curso.';
  document.querySelectorAll('button').forEach(b=>{ if(!b.textContent.includes('Cerrar Setup')) b.disabled=(op.state==='running'); });
}
async function act(action,profile=null){
  const r=await fetch('/api/action',{method:'POST',headers:{'Content-Type':'application/json','X-AWAI-Token':TOKEN},body:JSON.stringify({action,profile})});
  if(!r.ok){ const t=await r.text(); alert(t||'No se pudo iniciar la operación.'); }
  await refresh();
}
async function closeSetup(){ await fetch('/api/exit',{method:'POST',headers:{'X-AWAI-Token':TOKEN}}); window.close(); }
refresh(); setInterval(refresh,1500);
</script></body></html>'''


class _SetupServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, server_address, handler_class, *, token: str, operation: SetupOperation):
        super().__init__(server_address, handler_class)
        self.token = token
        self.operation = operation
        self.last_activity = time.monotonic()


class _Handler(BaseHTTPRequestHandler):
    server: _SetupServer

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def _touch(self) -> None:
        self.server.last_activity = time.monotonic()

    def _headers(self, status: int, content_type: str, length: int) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'none'")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()

    def _json(self, payload: object, status: int = HTTPStatus.OK) -> None:
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self._headers(status, "application/json; charset=utf-8", len(raw))
        self.wfile.write(raw)

    def _text(self, text: str, status: int = HTTPStatus.OK) -> None:
        raw = text.encode("utf-8")
        self._headers(status, "text/plain; charset=utf-8", len(raw))
        self.wfile.write(raw)

    def _authorized(self) -> bool:
        return secrets.compare_digest(self.headers.get("X-AWAI-Token", ""), self.server.token)

    def do_GET(self) -> None:  # noqa: N802
        self._touch()
        path = urllib.parse.urlsplit(self.path).path
        if path == "/":
            raw = _HTML.replace("__TOKEN__", self.server.token).encode("utf-8")
            self._headers(HTTPStatus.OK, "text/html; charset=utf-8", len(raw))
            self.wfile.write(raw)
            return
        if path == "/api/status":
            self._json(setup_status())
            return
        if path == "/api/operation":
            self._json(self.server.operation.payload())
            return
        if path == "/diagnostics.json":
            self._json({"setup": setup_status(), "operation": self.server.operation.payload()})
            return
        self._text("No encontrado", HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        self._touch()
        if not self._authorized():
            self._text("Solicitud no autorizada", HTTPStatus.FORBIDDEN)
            return
        path = urllib.parse.urlsplit(self.path).path
        if path == "/api/exit":
            self._json({"status": "closing"})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        if path != "/api/action":
            self._text("No encontrado", HTTPStatus.NOT_FOUND)
            return
        try:
            length = min(int(self.headers.get("Content-Length", "0")), 4096)
            payload = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._text("Solicitud inválida", HTTPStatus.BAD_REQUEST)
            return
        if not isinstance(payload, dict):
            self._text("Solicitud inválida", HTTPStatus.BAD_REQUEST)
            return
        action = str(payload.get("action") or "")
        profile_raw = payload.get("profile")
        profile = str(profile_raw) if profile_raw is not None else None
        allowed = {"prepare_profile", "install_runtime", "repair_runtime", "install_model", "start_bridge"}
        if action not in allowed or (profile is not None and profile not in {"L12", "H24"}):
            self._text("Acción inválida", HTTPStatus.BAD_REQUEST)
            return
        if not self.server.operation.start(action, profile):
            self._text("Ya hay una operación en curso", HTTPStatus.CONFLICT)
            return
        self._json({"status": "started", "action": action, "profile": profile}, HTTPStatus.ACCEPTED)


def serve_setup(*, open_browser: bool = True, idle_seconds: int = _DEFAULT_IDLE_SECONDS) -> int:
    token = secrets.token_urlsafe(32)
    operation = SetupOperation()
    server = _SetupServer(("127.0.0.1", 0), _Handler, token=token, operation=operation)
    host, port = server.server_address[:2]
    url = f"http://{host}:{port}/"

    def idle_watch() -> None:
        while True:
            time.sleep(5)
            if operation.payload()["state"] == "running":
                continue
            if time.monotonic() - server.last_activity >= max(60, idle_seconds):
                server.shutdown()
                return

    threading.Thread(target=idle_watch, name="aw-ai-setup-idle", daemon=True).start()
    if open_browser:
        webbrowser.open(url, new=1, autoraise=True)
    try:
        server.serve_forever(poll_interval=0.25)
    finally:
        server.server_close()
    return 0
