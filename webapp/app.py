from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
import json
from pathlib import Path
import subprocess
import sys
import uuid
import os
import threading
import time

# Look for config.json in project root (one level up from this webapp folder)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config.json"

app = Flask(__name__)
app.secret_key = "dev-secret-change-me"


def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_config(data):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# Simple job manager for running `smartlink_opener.py` as a subprocess
JOBS = {}
LOG_DIR = PROJECT_ROOT / "webapp_logs"
LOG_DIR.mkdir(exist_ok=True)


def _tail_file(path, lines=50):
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            block = -1
            data = b""
            while size + block > 0 and data.count(b"\n") <= lines:
                step = 1024
                if size + block - step < 0:
                    step = size + block
                f.seek(block * step, os.SEEK_END)
                data = f.read()
                block -= 1
            return b"\n".join(data.splitlines()[-lines:]).decode(
                "utf-8", errors="replace"
            )
    except Exception:
        return ""


def start_smartlink_run(extra_args=None):
    """Start smartlink_opener.py either by importing and running its main() in a
    background thread (preferred) or fall back to launching a subprocess.
    """
    job_id = str(uuid.uuid4())
    log_path = LOG_DIR / f"job_{job_id}.log"
    cmd = [sys.executable, str(PROJECT_ROOT / "smartlink_opener.py")]
    if extra_args:
        cmd += extra_args

    # Try direct import & run to allow tighter integration
    try:
        import importlib

        smart_mod = importlib.import_module("smartlink_opener")

        def _target():
            import contextlib
            import asyncio

            try:
                with open(log_path, "w", encoding="utf-8", errors="replace") as logf:
                    with contextlib.redirect_stdout(logf), contextlib.redirect_stderr(
                        logf
                    ):
                        main = getattr(smart_mod, "main", None)
                        if main and asyncio.iscoroutinefunction(main):
                            asyncio.run(main())
                        elif callable(main):
                            main()
                        else:
                            # Fallback: attempt to execute module as script
                            smart_mod.__main__ = True
            except Exception as e:
                with open(log_path, "a", encoding="utf-8", errors="replace") as logf:
                    print(f"[ERROR] Exception in smartlink run: {e}", file=logf)

        thread = threading.Thread(target=_target, daemon=True)
        thread.start()

        JOBS[job_id] = {
            "pid": None,
            "thread": thread,
            "start_time": time.time(),
            "status": "running",
            "log": str(log_path),
        }

        # Start a watcher to update status when thread ends (poll log for completion)
        def _watch_thread():
            thread.join()
            JOBS[job_id]["status"] = "finished"

        watcher = threading.Thread(target=_watch_thread, daemon=True)
        watcher.start()
        return job_id
    except Exception:
        # Fallback to launching a subprocess and logging stdout/stderr
        with open(log_path, "wb") as logf:
            popen = subprocess.Popen(cmd, stdout=logf, stderr=subprocess.STDOUT)

        JOBS[job_id] = {
            "pid": popen.pid,
            "popen": popen,
            "start_time": time.time(),
            "status": "running",
            "log": str(log_path),
        }

        # Start a watcher thread to update status when process ends
        def _watch():
            popen.wait()
            JOBS[job_id]["status"] = "finished" if popen.returncode == 0 else "failed"
            JOBS[job_id]["returncode"] = popen.returncode

        t = threading.Thread(target=_watch, daemon=True)
        t.start()
        return job_id


def stop_job(job_id):
    j = JOBS.get(job_id)
    if not j:
        return False
    p = j.get("popen")
    if p and p.poll() is None:
        try:
            p.terminate()
            # wait briefly
            try:
                p.wait(timeout=5)
            except Exception:
                p.kill()
        except Exception:
            pass
    j["status"] = "stopped"
    return True


@app.route("/", methods=["GET", "POST"])
def index():
    cfg = load_config()
    if request.method == "POST":
        # Update existing keys from the form
        for key in request.form:
            if key in ("new_key", "new_value"):
                continue
            val = request.form.get(key)
            # Try to interpret JSON values (so arrays, objects, numbers, booleans work)
            try:
                parsed = json.loads(val)
                cfg[key] = parsed
            except Exception:
                cfg[key] = val

        # Handle adding a new key/value pair
        new_key = request.form.get("new_key", "").strip()
        new_value = request.form.get("new_value", "")
        if new_key:
            try:
                parsed = json.loads(new_value)
                cfg[new_key] = parsed
            except Exception:
                cfg[new_key] = new_value

        save_config(cfg)
        flash("Configuration saved.")
        return redirect(url_for("index"))

    return render_template("index.html", config=cfg)


@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    if request.method == "GET":
        return jsonify(load_config())
    payload = request.get_json() or {}
    save_config(payload)
    return jsonify({"status": "ok", "saved": True})


@app.route("/api/run", methods=["POST"])
def api_run():
    data = request.get_json() or {}
    args = data.get("args") or []
    job_id = start_smartlink_run(extra_args=args)
    return jsonify({"status": "started", "job_id": job_id})


@app.route("/api/run/<job_id>", methods=["GET", "POST"])
def api_run_status(job_id):
    j = JOBS.get(job_id)
    if not j:
        return jsonify({"error": "not found"}), 404
    if request.method == "POST":
        # allow stop
        action = request.get_json().get("action")
        if action == "stop":
            stop_job(job_id)
    log_tail = _tail_file(j["log"], lines=200)
    return jsonify(
        {
            "job_id": job_id,
            "pid": j.get("pid"),
            "status": j.get("status"),
            "start_time": j.get("start_time"),
            "returncode": j.get("returncode") if "returncode" in j else None,
            "log_tail": log_tail,
        }
    )


@app.route("/api/runs", methods=["GET"])
def api_runs():
    out = []
    for jid, j in JOBS.items():
        out.append(
            {
                "job_id": jid,
                "pid": j.get("pid"),
                "status": j.get("status"),
                "start_time": j.get("start_time"),
            }
        )
    return jsonify(out)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
