#!/usr/bin/env python3
"""Watch opencode/Ollama Qwen flows and react when the runner stalls or goes cold."""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import signal
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any


QWEN_RE = re.compile(r"qwen", re.IGNORECASE)
RUNNER_RE = re.compile(r"ollama runner|llama-server|vllm", re.IGNORECASE)


def now() -> float:
    return time.time()


def log_event(path: Path, event: str, **fields: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"ts": now(), "event": event, **fields}
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


def run(args: list[str], timeout: float = 5) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except Exception as exc:  # noqa: BLE001 - diagnostic failures are logged.
        return {"ok": False, "error": str(exc), "stdout": "", "stderr": ""}


def run_hook(command: str, timeout: float = 10) -> dict[str, Any]:
    if not command:
        return {"ok": False, "error": "no command configured"}
    return run(shlex.split(command), timeout=timeout)


def http_json(host: str, path: str, timeout: float = 5) -> dict[str, Any]:
    with urllib.request.urlopen(f"{host.rstrip('/')}{path}", timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def http_post_json(host: str, path: str, payload: dict[str, Any], timeout: float = 30) -> Any:
    request = urllib.request.Request(
        f"{host.rstrip('/')}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return body[-1000:]


def proc_cmdline(pid: int) -> str:
    try:
        data = Path(f"/proc/{pid}/cmdline").read_bytes()
        return data.replace(b"\0", b" ").decode("utf-8", errors="replace").strip()
    except OSError:
        return ""


def proc_cpu_ticks(pid: int) -> int | None:
    try:
        fields = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").split()
        return int(fields[13]) + int(fields[14])
    except (OSError, ValueError, IndexError):
        return None


def matching_pids(pattern: re.Pattern[str]) -> list[dict[str, Any]]:
    pids: list[dict[str, Any]] = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        cmd = proc_cmdline(pid)
        if cmd and pattern.search(cmd):
            pids.append({"pid": pid, "cmd": cmd, "cpu_ticks": proc_cpu_ticks(pid)})
    return pids


def qwen_loaded(ps_payload: dict[str, Any]) -> bool:
    return any(QWEN_RE.search(model.get("name", "") or model.get("model", "")) for model in ps_payload.get("models", []))


def snapshot(host: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "opencode": matching_pids(re.compile(r"(^| )opencode( |$)", re.IGNORECASE)),
        "runners": matching_pids(RUNNER_RE),
        "ollama_ps": None,
    }
    try:
        payload["ollama_ps"] = http_json(host, "/api/ps")
    except Exception as exc:  # noqa: BLE001 - diagnostic failures are data.
        payload["ollama_ps_error"] = str(exc)
    ss = run(["ss", "-tnp"], timeout=5)
    if ss["ok"]:
        interesting = [
            line for line in ss["stdout"].splitlines() if "11435" in line or "11434" in line
        ]
        payload["tcp"] = interesting[-20:]
    return payload


def loaded_qwen_models(snap: dict[str, Any]) -> list[str]:
    ps_payload = snap.get("ollama_ps")
    if not isinstance(ps_payload, dict):
        return []
    names = []
    for model in ps_payload.get("models", []):
        name = model.get("name") or model.get("model") or ""
        if QWEN_RE.search(name):
            names.append(name)
    return names


def cpu_progress(previous: dict[int, int], runners: list[dict[str, Any]]) -> tuple[bool, dict[int, int]]:
    current: dict[int, int] = {}
    progressed = False
    for runner in runners:
        pid = runner["pid"]
        ticks = runner.get("cpu_ticks")
        if ticks is None:
            continue
        current[pid] = ticks
        if pid in previous and ticks > previous[pid]:
            progressed = True
    return progressed, current


def nudge(args: argparse.Namespace, snap: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {"action": args.action}
    if args.action == "none":
        return result

    if args.action in {"metadata", "both"}:
        result["api_ps"] = safe_call(lambda: http_json(args.host, "/api/ps"))
        result["api_tags"] = safe_call(lambda: http_json(args.host, "/api/tags"))

    if args.action in {"sigcont", "both"}:
        pids = {proc["pid"] for proc in snap.get("opencode", []) + snap.get("runners", [])}
        sent: list[int] = []
        for pid in sorted(pids):
            try:
                os.kill(pid, signal.SIGCONT)
                sent.append(pid)
            except OSError:
                pass
        result["sigcont_pids"] = sent

    if args.action == "generate":
        result["generate"] = tiny_generate(args)

    return result


def safe_call(fn: Any) -> dict[str, Any]:
    try:
        return {"ok": True, "value": fn()}
    except Exception as exc:  # noqa: BLE001 - nudge errors are diagnostic.
        return {"ok": False, "error": str(exc)}


def tiny_generate(args: argparse.Namespace) -> dict[str, Any]:
    payload = {
        "model": args.model,
        "prompt": args.nudge_prompt,
        "stream": False,
        "keep_alive": args.keep_alive,
        "options": {"num_predict": args.nudge_tokens, "num_ctx": args.nudge_ctx},
    }
    return safe_call(lambda: http_post_json(args.host, "/api/generate", payload, args.nudge_timeout))


def is_candidate_stall(snap: dict[str, Any], require_opencode: bool) -> bool:
    if require_opencode and not snap.get("opencode"):
        return False
    if snap.get("runners"):
        return True
    ps_payload = snap.get("ollama_ps")
    return isinstance(ps_payload, dict) and qwen_loaded(ps_payload)


def main_loop(args: argparse.Namespace) -> int:
    log_path = Path(args.log)
    previous_ticks: dict[int, int] = {}
    idle_since: float | None = None
    last_nudge_at = 0.0
    had_active_qwen = False
    cold_since: float | None = None
    last_cold_hook_at = 0.0

    log_event(
        log_path,
        "start",
        host=args.host,
        model=args.model,
        action=args.action,
        interval=args.interval,
        idle_seconds=args.idle_seconds,
        cold_seconds=args.cold_seconds,
        on_cold_command=args.on_cold_command,
    )

    while True:
        snap = snapshot(args.host)
        progressed, previous_ticks = cpu_progress(previous_ticks, snap.get("runners", []))
        candidate = is_candidate_stall(snap, args.require_opencode)
        opencode_alive = bool(snap.get("opencode"))
        qwen_models = loaded_qwen_models(snap)
        qwen_active = bool(qwen_models or snap.get("runners"))

        if qwen_active:
            had_active_qwen = True
            cold_since = None
        elif had_active_qwen and (opencode_alive or not args.require_opencode):
            if cold_since is None:
                cold_since = now()
        else:
            cold_since = None

        if not candidate or progressed:
            idle_since = None
        elif idle_since is None:
            idle_since = now()

        idle_for = 0.0 if idle_since is None else now() - idle_since
        cold_for = 0.0 if cold_since is None else now() - cold_since
        event = {
            "candidate": candidate,
            "qwen_active": qwen_active,
            "had_active_qwen": had_active_qwen,
            "progressed": progressed,
            "idle_for": round(idle_for, 3),
            "cold_for": round(cold_for, 3),
            "opencode_pids": [proc["pid"] for proc in snap.get("opencode", [])],
            "runner_pids": [proc["pid"] for proc in snap.get("runners", [])],
            "runner_ticks": {proc["pid"]: proc.get("cpu_ticks") for proc in snap.get("runners", [])},
            "ollama_models": qwen_models,
            "tcp": snap.get("tcp", []),
        }

        should_nudge = (
            candidate
            and idle_for >= args.idle_seconds
            and now() - last_nudge_at >= args.cooldown_seconds
        )
        should_cold_hook = (
            had_active_qwen
            and not qwen_active
            and cold_for >= args.cold_seconds
            and now() - last_cold_hook_at >= args.cold_cooldown_seconds
        )
        if should_cold_hook:
            event["hook"] = run_hook(args.on_cold_command, args.hook_timeout)
            last_cold_hook_at = now()
            cold_since = None
            log_event(log_path, "cold", **event)
            if args.once:
                return 0
        elif should_nudge:
            event["nudge"] = nudge(args, snap)
            last_nudge_at = now()
            idle_since = None
            log_event(log_path, "nudge", **event)
            if args.once:
                return 0
        else:
            log_event(log_path, "sample", **event)

        if args.once:
            return 0
        time.sleep(args.interval)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Monitor opencode/Ollama Qwen liveness and react to stalls or cold exits."
    )
    parser.add_argument("--host", default="http://127.0.0.1:11435")
    parser.add_argument("--model", default="qwen3.6-240k-coding:latest")
    parser.add_argument("--log", default="logs/qwen-nudger.jsonl")
    parser.add_argument("--interval", type=float, default=15)
    parser.add_argument("--idle-seconds", type=float, default=120)
    parser.add_argument("--cooldown-seconds", type=float, default=180)
    parser.add_argument("--cold-seconds", type=float, default=30)
    parser.add_argument("--cold-cooldown-seconds", type=float, default=180)
    parser.add_argument("--on-cold-command", default="")
    parser.add_argument("--hook-timeout", type=float, default=10)
    parser.add_argument(
        "--action",
        choices=["none", "metadata", "sigcont", "both", "generate"],
        default="metadata",
    )
    parser.add_argument("--no-require-opencode", dest="require_opencode", action="store_false")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--nudge-prompt", default="ping")
    parser.add_argument("--nudge-tokens", type=int, default=1)
    parser.add_argument("--nudge-ctx", type=int, default=2048)
    parser.add_argument("--nudge-timeout", type=float, default=20)
    parser.add_argument("--keep-alive", default="5m")
    parser.set_defaults(require_opencode=True)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main_loop(parse_args()))
