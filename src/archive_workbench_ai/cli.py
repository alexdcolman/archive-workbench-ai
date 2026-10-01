from __future__ import annotations

import argparse
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import PHASE, PROTOCOL_VERSION, __version__
from .benchmark import run_benchmark
from .benchmark_job import extracted_benchmark_job, prepare_benchmark_job
from .bridge import (
    bridge_status,
    cleanup_bridge_jobs,
    initialize_bridge,
    serve_bridge,
    start_bridge,
    stop_bridge,
)
from .complete_analysis import analyze_exp01
from .catalog import BOOTSTRAP_MODEL, MODEL_CATALOG, PROFILE_DEFAULT_MODELS, get_model_spec
from .errors import InvalidInputError, PluginError, RuntimeUnavailableError
from .exp01 import load_selected_assets
from .handoff import build_handoff_bundle, inspect_handoff_bundle
from .model_store import inspect_model, pull_model
from .protocol import load_request
from .result_bundle import build_result_bundle
from .runtime import PINNED_LLAMA_BUILD, PINNED_LLAMA_COMMIT, PINNED_LLAMA_TAG, detect_runtime_detailed, gpu_info
from .runtime_manager import install_runtime, runtime_installation_report
from .setup_app import serve_setup, setup_status
from .managed_paths import default_bridge_root, managed_executable_candidates


def _print_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def _runtime_payload() -> dict[str, object]:
    detection = detect_runtime_detailed()
    failures = [
        {
            "executable": failure.executable,
            "mode": failure.mode,
            "returncode": failure.returncode,
            "detail": failure.detail,
        }
        for failure in detection.failures
    ]
    runtime = detection.runtime
    if runtime is None:
        return {
            "available": False,
            "id": "llama.cpp",
            "probe_failures": failures,
            "expected_tag": PINNED_LLAMA_TAG,
            "expected_build": PINNED_LLAMA_BUILD,
            "expected_commit": PINNED_LLAMA_COMMIT,
        }
    return {
        "available": True,
        "id": "llama.cpp",
        "mode": runtime.mode,
        "executable": runtime.executable,
        "argv_prefix": list(runtime.argv_prefix),
        "build_number": runtime.build_number,
        "revision": runtime.revision,
        "validation_status": runtime.status,
        "version_text": runtime.version_text,
        "probe_failures": failures,
        "expected_tag": PINNED_LLAMA_TAG,
        "expected_build": PINNED_LLAMA_BUILD,
        "expected_commit": PINNED_LLAMA_COMMIT,
    }


def _models_payload(*, verify: bool = False) -> list[dict[str, object]]:
    return [inspect_model(spec, verify=verify) for spec in MODEL_CATALOG]


def _doctor() -> dict[str, object]:
    runtime = _runtime_payload()
    models = _models_payload(verify=False)
    installed = [item["model_id"] for item in models if item["installed"]]
    real_ready = bool(runtime["available"] and installed)
    return {
        "plugin": "archive-workbench-ai",
        "version": __version__,
        "phase": PHASE,
        "protocols": [PROTOCOL_VERSION],
        "python": platform.python_version(),
        "platform": platform.platform(),
        "backends": {
            "mock": {"available": True},
            "llama_cpp": {
                "available": real_ready,
                "runtime": runtime,
                "installed_models": installed,
            },
        },
        "gpus": gpu_info(),
        "network_required_for_run": False,
        "network_required_for_models_pull": True,
        "status": "ok" if real_ready else "setup_required",
    }


def _capabilities() -> dict[str, object]:
    return {
        "plugin": "archive-workbench-ai",
        "version": __version__,
        "protocols": [PROTOCOL_VERSION],
        "tasks": [
            {
                "id": "vision_describe",
                "version": "0.1",
                "input_bundle_types": ["exp01"],
                "target_types": ["page", "region", "figure"],
                "max_targets": 3,
                "output_schema_ids": ["vision_describe/0.1"],
            }
        ],
        "backends": ["llama_cpp", "mock"],
        "handoff_schema_ids": ["archive_workbench_ai_result_handoff/0.1"],
        "workflows": {
            "complete_exp01": {
                "command": "analyze",
                "internal_request_max_targets": 3,
                "consolidated_result": True,
                "consolidated_handoff": True,
            }
        },
        "network_policies": ["offline_required"],
        "phase": PHASE,
        "default_model": BOOTSTRAP_MODEL.model_id,
        "default_model_role": "bootstrap_baseline",
        "profile_default_models": {
            profile: spec.model_id for profile, spec in PROFILE_DEFAULT_MODELS.items()
        },
        "model_catalog": [
            {
                "model_id": spec.model_id,
                "status": spec.status,
                "hardware_profiles": list(spec.hardware_profiles),
            }
            for spec in MODEL_CATALOG
        ],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aw-ai", description="Archive Workbench AI external engine")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="Diagnostica la instalación")
    doctor.add_argument("--json", action="store_true")

    capabilities = sub.add_parser("capabilities", help="Declara capacidades del plugin")
    capabilities.add_argument("--json", action="store_true")

    runtime = sub.add_parser("runtime", help="Consulta el runtime externo")
    runtime_sub = runtime.add_subparsers(dest="runtime_command", required=True)
    runtime_inspect = runtime_sub.add_parser("inspect")
    runtime_inspect.add_argument("--json", action="store_true")
    runtime_install = runtime_sub.add_parser("install", help="Instala el runtime llama.cpp fijado para este sistema")
    runtime_install.add_argument("--variant", choices=["auto", "cpu", "nvidia", "metal"], default="auto")
    runtime_install.add_argument("--force", action="store_true")
    runtime_install.add_argument("--json", action="store_true")

    bridge = sub.add_parser("bridge", help="Administra el puente local con Archive Workbench en Docker")
    bridge_sub = bridge.add_subparsers(dest="bridge_command", required=True)
    bridge_path = bridge_sub.add_parser("path", help="Muestra la ruta administrada del puente")
    bridge_path.add_argument("--json", action="store_true")
    bridge_init = bridge_sub.add_parser("init", help="Inicializa el buzón local compartido")
    bridge_init.add_argument("--root", type=Path, default=None)
    bridge_init.add_argument("--json", action="store_true")
    bridge_status_cmd = bridge_sub.add_parser("status", help="Consulta el estado del compañero local")
    bridge_status_cmd.add_argument("--root", type=Path, default=None)
    bridge_status_cmd.add_argument("--json", action="store_true")
    bridge_start = bridge_sub.add_parser("start", help="Inicia el compañero local en segundo plano")
    bridge_start.add_argument("--root", type=Path, default=None)
    bridge_start.add_argument("--json", action="store_true")
    bridge_stop = bridge_sub.add_parser("stop", help="Detiene el compañero local")
    bridge_stop.add_argument("--root", type=Path, default=None)
    bridge_stop.add_argument("--json", action="store_true")
    bridge_cleanup = bridge_sub.add_parser("cleanup", help="Limpia trabajos consumidos o vencidos")
    bridge_cleanup.add_argument("--root", type=Path, default=None)
    bridge_cleanup.add_argument("--json", action="store_true")
    bridge_serve = bridge_sub.add_parser("serve", help="Ejecuta el compañero local en primer plano")
    bridge_serve.add_argument("--root", type=Path, default=None)
    bridge_serve.add_argument("--poll-seconds", type=float, default=0.5)
    bridge_serve.add_argument("--once", action="store_true")


    managed = sub.add_parser("managed", help="Consulta rutas de la distribución administrada")
    managed_sub = managed.add_subparsers(dest="managed_command", required=True)
    managed_paths = managed_sub.add_parser("paths")
    managed_paths.add_argument("--json", action="store_true")

    setup = sub.add_parser("setup", help="Abre Archive Workbench AI Setup")
    setup.add_argument("--no-browser", action="store_true")
    setup.add_argument("--status-json", action="store_true")

    models = sub.add_parser("models", help="Administra/consulta modelos")
    models_sub = models.add_subparsers(dest="models_command", required=True)
    models_list = models_sub.add_parser("list")
    models_list.add_argument("--verify", action="store_true")
    models_list.add_argument("--json", action="store_true")
    models_inspect = models_sub.add_parser("inspect")
    models_inspect.add_argument("model_id")
    models_inspect.add_argument("--verify", action="store_true")
    models_inspect.add_argument("--json", action="store_true")
    models_pull = models_sub.add_parser("pull")
    models_pull.add_argument("model_id")

    run = sub.add_parser("run", help="Ejecuta una solicitud")
    run.add_argument("--request", required=True, type=Path)
    run.add_argument("--input", required=True, type=Path)
    run.add_argument("--output", required=True, type=Path)
    run.add_argument("--backend", choices=["llama_cpp", "mock"], default="llama_cpp")
    run.add_argument("--model", default=BOOTSTRAP_MODEL.model_id)

    analyze = sub.add_parser(
        "analyze",
        help="Analiza un EXP-01 completo y produce un único handoff para Archive Workbench",
    )
    analyze.add_argument("--input", required=True, type=Path, help="EXP-01 de Archive Workbench")
    analyze.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Handoff ZIP consolidado; por defecto se crea en ~/Downloads",
    )
    analyze.add_argument(
        "--result-output",
        type=Path,
        default=None,
        help="Ruta opcional del result ZIP consolidado; por defecto se crea junto al handoff",
    )
    analyze.add_argument("--profile", choices=["L12", "H24"], required=True)
    analyze.add_argument("--backend", choices=["llama_cpp", "mock"], default="llama_cpp")
    analyze.add_argument(
        "--model",
        default=None,
        help="Modelo del catálogo; si se omite usa el default del perfil",
    )
    analyze.add_argument(
        "--target-type",
        action="append",
        choices=["page", "region", "figure"],
        default=None,
        help="Tipo de asset a analizar; puede repetirse. Por defecto: page",
    )
    analyze.add_argument("--max-output-tokens", type=int, default=512)
    analyze.add_argument("--temperature", type=float, default=0.0)
    analyze.add_argument("--seed", type=int, default=0)

    benchmark = sub.add_parser("benchmark", help="Ejecuta comparaciones P2 secuenciales")
    benchmark_sub = benchmark.add_subparsers(dest="benchmark_command", required=True)
    benchmark_prepare = benchmark_sub.add_parser("prepare", help="Prepara un job reproducible desde 1-3 imágenes locales")
    benchmark_prepare.add_argument("--images", nargs="+", required=True, type=Path)
    benchmark_prepare.add_argument("--profile", choices=["L12", "H24"], required=True)
    benchmark_prepare.add_argument("--max-output-tokens", type=int, default=512)
    benchmark_prepare.add_argument("--output", type=Path, default=None)

    benchmark_run = benchmark_sub.add_parser("run")
    benchmark_run.add_argument("--request", type=Path)
    benchmark_run.add_argument("--input", type=Path)
    benchmark_run.add_argument("--job", type=Path)
    benchmark_run.add_argument("--models", nargs="*", default=None)
    benchmark_run.add_argument("--output", type=Path, default=None)

    handoff = sub.add_parser("handoff", help="Construye/inspecciona paquetes de resultados propuestos para Archive Workbench")
    handoff_sub = handoff.add_subparsers(dest="handoff_command", required=True)
    handoff_build = handoff_sub.add_parser("build")
    handoff_build.add_argument("--input", required=True, type=Path, help="EXP-01 original")
    handoff_build.add_argument("--result", required=True, type=Path, help="result.zip de AI-01")
    handoff_build.add_argument("--output", required=True, type=Path)
    handoff_inspect = handoff_sub.add_parser("inspect")
    handoff_inspect.add_argument("--bundle", required=True, type=Path)
    handoff_inspect.add_argument("--json", action="store_true")
    return parser


def _spec_for(model_id: str):
    try:
        return get_model_spec(model_id)
    except KeyError as exc:
        raise InvalidInputError(str(exc)) from exc


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "doctor":
            payload = _doctor()
            if args.json:
                _print_json(payload)
            else:
                print(f"Archive Workbench AI {__version__}: {payload['status']} ({PHASE})")
            return 0

        if args.command == "capabilities":
            payload = _capabilities()
            if args.json:
                _print_json(payload)
            else:
                print("vision_describe/0.1; exp01; page|region|figure; backends=llama_cpp|mock")
            return 0

        if args.command == "runtime" and args.runtime_command == "inspect":
            payload = {**_runtime_payload(), "managed_installation": runtime_installation_report()}
            if args.json:
                _print_json(payload)
            else:
                print(json.dumps(payload, ensure_ascii=False))
            return 0

        if args.command == "runtime" and args.runtime_command == "install":
            payload = install_runtime(variant=args.variant, force=args.force)
            if args.json:
                _print_json(payload)
            else:
                print(f"Runtime {payload['status']}: {payload['root']}")
            return 0

        if args.command == "bridge":
            if args.bridge_command == "path":
                root = default_bridge_root()
                if args.json:
                    _print_json({"root": str(root)})
                else:
                    print(root)
                return 0
            if args.bridge_command == "init":
                payload = initialize_bridge(args.root)
            elif args.bridge_command == "status":
                payload = bridge_status(args.root)
            elif args.bridge_command == "start":
                payload = start_bridge(args.root)
            elif args.bridge_command == "stop":
                payload = stop_bridge(args.root)
            elif args.bridge_command == "cleanup":
                root = args.root or default_bridge_root()
                payload = {"root": str(root), "removed": cleanup_bridge_jobs(root)}
            elif args.bridge_command == "serve":
                return serve_bridge(args.root, poll_seconds=args.poll_seconds, once=args.once)
            else:
                return 2
            if args.json:
                _print_json(payload)
            else:
                print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            return 0

        if args.command == "managed" and args.managed_command == "paths":
            payload = {
                "bridge_root": str(default_bridge_root()),
                "executable_candidates": [str(path) for path in managed_executable_candidates()],
            }
            if args.json:
                _print_json(payload)
            else:
                print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            return 0

        if args.command == "setup":
            if args.status_json:
                _print_json(setup_status())
                return 0
            return serve_setup(open_browser=not args.no_browser)

        if args.command == "models":
            if args.models_command == "list":
                payload = _models_payload(verify=args.verify)
                if args.json:
                    _print_json({"models": payload})
                else:
                    for item in payload:
                        print(f"{item['model_id']}\tinstalled={item['installed']}\tstatus={item['status']}")
                return 0
            if args.models_command == "inspect":
                spec = _spec_for(args.model_id)
                payload = inspect_model(spec, verify=args.verify)
                if args.json:
                    _print_json(payload)
                else:
                    print(f"{payload['model_id']}: installed={payload['installed']}")
                return 0
            if args.models_command == "pull":
                spec = _spec_for(args.model_id)
                payload = pull_model(spec)
                _print_json(payload)
                return 0

        if args.command == "run":
            spec = _spec_for(args.model)
            request = load_request(args.request)
            _manifest, assets = load_selected_assets(args.input, request)
            manifest = build_result_bundle(
                request=request,
                input_path=args.input,
                selected_assets=assets,
                output_path=args.output,
                backend=args.backend,
                model_spec=spec,
            )
            print(
                json.dumps(
                    {
                        "status": manifest["status"],
                        "request_id": manifest["request_id"],
                        "output": str(args.output),
                        "targets": manifest["target_count"],
                        "backend": args.backend,
                        "model": manifest["model"]["model_id"],
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            return 0

        if args.command == "analyze":
            spec = (
                _spec_for(args.model)
                if args.model
                else PROFILE_DEFAULT_MODELS[args.profile]
            )
            target_types = tuple(dict.fromkeys(args.target_type or ["page"]))
            handoff_output = args.output
            result_output = args.result_output
            if handoff_output is None:
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                downloads = Path.home() / "Downloads"
                handoff_output = downloads / f"AWAI_HANDOFF_{stamp}.zip"
                if result_output is None:
                    result_output = downloads / f"AWAI_RESULT_{stamp}.zip"
            payload = analyze_exp01(
                input_path=args.input,
                handoff_output_path=handoff_output,
                result_output_path=result_output,
                model_spec=spec,
                hardware_profile=args.profile,
                backend=args.backend,
                target_types=target_types,
                seed=args.seed,
                max_output_tokens=args.max_output_tokens,
                temperature=args.temperature,
            )
            _print_json(payload)
            return 0

        if args.command == "handoff" and args.handoff_command == "build":
            manifest = build_handoff_bundle(input_path=args.input, result_path=args.result, output_path=args.output)
            _print_json({
                "status": "ok",
                "output": str(args.output),
                "schema_version": manifest["schema_version"],
                "proposal_count": manifest["proposal_count"],
                "automatic_apply": manifest["policy"]["automatic_apply"],
            })
            return 0

        if args.command == "handoff" and args.handoff_command == "inspect":
            payload = inspect_handoff_bundle(args.bundle)
            if args.json:
                _print_json(payload)
            else:
                print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            return 0

        if args.command == "benchmark" and args.benchmark_command == "prepare":
            payload = prepare_benchmark_job(
                image_paths=args.images,
                hardware_profile=args.profile,
                max_output_tokens=args.max_output_tokens,
                output_path=args.output,
            )
            _print_json(payload)
            return 0

        if args.command == "benchmark" and args.benchmark_command == "run":
            if args.models:
                specs = [_spec_for(model_id) for model_id in args.models]
            else:
                specs = [spec for spec in MODEL_CATALOG if inspect_model(spec, verify=False)["installed"]]
                if not specs:
                    raise RuntimeUnavailableError("No hay modelos P2 instalados para benchmark")

            if args.job is not None:
                if args.request is not None or args.input is not None:
                    raise InvalidInputError("Usá --job o el par --request/--input, no ambos")
                with extracted_benchmark_job(args.job) as (request_path, input_path):
                    payload = run_benchmark(
                        request_path=request_path,
                        input_path=input_path,
                        model_specs=specs,
                        output_path=args.output,
                    )
                payload["job"] = str(args.job)
            else:
                if args.request is None or args.input is None:
                    raise InvalidInputError("benchmark run requiere --job o ambos --request y --input")
                payload = run_benchmark(
                    request_path=args.request,
                    input_path=args.input,
                    model_specs=specs,
                    output_path=args.output,
                )
            _print_json(payload)
            return 0

        return 2
    except PluginError as exc:
        print(json.dumps({"error": exc.code, "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return exc.exit_code
    except KeyboardInterrupt:
        print(json.dumps({"error": "interrupted", "message": "Interrumpido por el usuario"}, ensure_ascii=False), file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
