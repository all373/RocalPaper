"""Private local inference service for the desktop application."""

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import time
from process_job import ProcessJob
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener


ROOT = Path(__file__).resolve().parent
MODELS = {
    "Qwen3-0.6B": "Qwen3-0.6B-Q8_0.gguf",
}


def model_catalog():
    catalog_path = ROOT / "model_catalog.json"
    if not catalog_path.is_file():
        return MODELS, None
    catalog = json.loads(catalog_path.read_text(encoding="utf-8-sig"))
    models = catalog.get("models")
    if not isinstance(models, dict) or not models:
        raise RuntimeError("model_catalog.json must contain a nonempty models object.")
    for name, filename in models.items():
        if not isinstance(name, str) or not name or any(c in name for c in "[]\r\n"):
            raise RuntimeError("Invalid model name in model_catalog.json.")
        if (not isinstance(filename, str) or not filename.endswith(".gguf")
                or any(c in filename for c in "/\\\r\n") or filename in (".", "..")):
            raise RuntimeError("Model filenames must be GGUF filenames inside models.")
    default = catalog.get("default")
    if default is not None and default not in models:
        raise RuntimeError("The default model must be present in models.")
    return models, default


def runtime_config():
    path = ROOT / "runtime_config.json"
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.is_file() else {}


def write_model_preset(port):
    config = runtime_config()
    models, default = model_catalog()
    available = {name: ROOT / "models" / filename for name, filename in models.items()
                 if (ROOT / "models" / filename).is_file()}
    if not available:
        raise RuntimeError("No GGUF models found in the models directory.")
    cache = ROOT / "cache"
    cache.mkdir(exist_ok=True)
    preset = cache / f"web-models-{port}.ini"
    defaults = {"ctx-size": 4096, "threads": 4, "parallel": 1, "reasoning": "off"}
    defaults.update(config.get("defaults", {}))
    entries = ["version = 1", "", "[*]"]
    entries.extend(f"{key} = {value}" for key, value in defaults.items())
    entries.append("")
    for name, path in available.items():
        entries.extend([f"[{name}]", f"model = {path.as_posix()}"])
        for key, value in config.get("model_options", {}).get(name, {}).items():
            if any(c in str(key) + str(value) for c in "\r\n"):
                raise RuntimeError("Model options must not contain newlines.")
            entries.append(f"{key} = {value}")
        if name == default and config.get("preload_default", False):
            entries.append("load-on-startup = true")
        entries.append("")
    preset.write_text("\n".join(entries), encoding="utf-8")
    return preset


@contextmanager
def running_server(port, server=None, hidden=False):
    config = runtime_config()
    server = server or ROOT / config.get("server", "llama/llama-server.exe")
    if not server.is_file():
        raise RuntimeError(f"llama-server not found: {server}")
    with socket.socket() as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            raise RuntimeError(f"Port {port} is busy. Close the previous launcher or use --port.")

    preset = write_model_preset(port)
    cache = ROOT / "cache"
    log_path = cache / f"web-play-{port}.log"
    url = f"http://127.0.0.1:{port}"
    command = [
        str(server.resolve()), "--models-preset", str(preset), "--models-max", "1",
        "--host", "127.0.0.1", "--port", str(port),
        "--webui-config-file", str(ROOT / "webui.json"),
        "--cors-origins", url,
    ]
    options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    if hidden and os.name == "nt":
        options["creationflags"] |= subprocess.CREATE_NO_WINDOW
    opener = build_opener(ProxyHandler({}))
    with log_path.open("wb") as log:
        process = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=log, **options)
        try:
            job = ProcessJob(process)
        except Exception:
            process.kill()
            process.wait(timeout=10)
            raise
        try:
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError(f"Server exited. See {log_path}")
                try:
                    with opener.open(url + "/health", timeout=1) as response:
                        if json.load(response).get("status") == "ok":
                            break
                except (URLError, TimeoutError):
                    pass
                time.sleep(0.15)
            else:
                raise RuntimeError(f"Startup timed out. See {log_path}")
            yield url, process
        finally:
            job.close()
            if process.poll() is None:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=10)


def main():
    parser = argparse.ArgumentParser(description="Refresh models in the running desktop app.")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("Port must be between 1 and 65535.")
    write_model_preset(args.port)
    opener = build_opener(ProxyHandler({}))
    with opener.open(f"http://127.0.0.1:{args.port}/models?reload=1", timeout=60) as response:
        result = json.load(response)
    print(json.dumps([model["id"] for model in result["data"]], ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError) as error:
        raise SystemExit(str(error))
