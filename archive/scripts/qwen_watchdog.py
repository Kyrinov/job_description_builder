#!/usr/bin/env python3
"""Run an Ollama/Qwen prompt with stream diagnostics and stall detection."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def now() -> float:
    return time.time()


def write_event(log_file: Path, event: str, **fields: Any) -> None:
    record = {"ts": now(), "event": event, **fields}
    with log_file.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


def run_command(args: list[str], timeout: float = 5) -> dict[str, Any]:
    if shutil.which(args[0]) is None:
        return {"ok": False, "error": f"{args[0]} not found"}
    try:
        completed = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except Exception as exc:  # noqa: BLE001 - diagnostic command failures are data.
        return {"ok": False, "error": str(exc)}
    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
    }


def ollama_json(host: str, path: str, timeout: float = 5) -> dict[str, Any]:
    url = f"{host.rstrip('/')}{path}"
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def monitor(
    host: str,
    log_file: Path,
    stop_event: threading.Event,
    last_chunk_at: list[float],
    interval: float,
) -> None:
    while not stop_event.wait(interval):
        payload: dict[str, Any] = {
            "idle_seconds": round(now() - last_chunk_at[0], 3),
            "ollama_ps": None,
            "free": run_command(["free", "-h"]),
            "pgrep": run_command(["pgrep", "-af", "ollama|qwen|llama|vllm"]),
        }
        try:
            payload["ollama_ps"] = ollama_json(host, "/api/ps")
        except Exception as exc:  # noqa: BLE001 - logged for diagnosis.
            payload["ollama_ps_error"] = str(exc)
        gpu = run_command(
            [
                "nvidia-smi",
                "--query-gpu=timestamp,name,memory.used,memory.total,utilization.gpu",
                "--format=csv,noheader,nounits",
            ]
        )
        if gpu["ok"] or "not found" not in gpu.get("error", ""):
            payload["nvidia_smi"] = gpu
        write_event(log_file, "heartbeat", **payload)


def build_prompt(args: argparse.Namespace) -> str:
    if args.prompt_file:
        return Path(args.prompt_file).read_text(encoding="utf-8")
    if args.prompt:
        return args.prompt
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise SystemExit("Provide --prompt, --prompt-file, or pipe a prompt on stdin.")


def stream_generate(args: argparse.Namespace, prompt: str, log_file: Path) -> int:
    last_chunk_at = [now()]
    stop_event = threading.Event()
    thread = threading.Thread(
        target=monitor,
        args=(args.host, log_file, stop_event, last_chunk_at, args.monitor_interval),
        daemon=True,
    )
    thread.start()

    request_payload: dict[str, Any] = {
        "model": args.model,
        "prompt": prompt,
        "stream": True,
        "keep_alive": args.keep_alive,
        "options": {},
    }
    if args.num_ctx:
        request_payload["options"]["num_ctx"] = args.num_ctx
    if args.num_predict:
        request_payload["options"]["num_predict"] = args.num_predict

    write_event(
        log_file,
        "start",
        host=args.host,
        model=args.model,
        prompt_chars=len(prompt),
        options=request_payload["options"],
        keep_alive=args.keep_alive,
        stall_timeout=args.stall_timeout,
    )

    request = urllib.request.Request(
        f"{args.host.rstrip('/')}/api/generate",
        data=json.dumps(request_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    response_chars = 0
    thinking_chars = 0
    started_at = now()
    try:
        with urllib.request.urlopen(request, timeout=args.stall_timeout) as response:
            for raw_line in response:
                last_chunk_at[0] = now()
                if not raw_line.strip():
                    continue
                chunk = json.loads(raw_line.decode("utf-8"))
                text = chunk.get("response", "")
                thinking = chunk.get("thinking", "")
                if text:
                    response_chars += len(text)
                    print(text, end="", flush=True)
                if thinking:
                    thinking_chars += len(thinking)
                    if args.show_thinking:
                        print(thinking, end="", file=sys.stderr, flush=True)
                if chunk.get("done"):
                    print()
                    write_event(
                        log_file,
                        "done",
                        response_chars=response_chars,
                        thinking_chars=thinking_chars,
                        elapsed_seconds=round(now() - started_at, 3),
                        done_reason=chunk.get("done_reason"),
                        eval_count=chunk.get("eval_count"),
                        eval_duration=chunk.get("eval_duration"),
                        load_duration=chunk.get("load_duration"),
                        prompt_eval_count=chunk.get("prompt_eval_count"),
                    )
                    return 0
    except TimeoutError as exc:
        idle = now() - last_chunk_at[0]
        write_event(log_file, "stall_timeout", idle_seconds=round(idle, 3), error=str(exc))
        return 3
    except urllib.error.URLError as exc:
        idle = now() - last_chunk_at[0]
        write_event(log_file, "connection_error", idle_seconds=round(idle, 3), error=str(exc))
        return 4
    except KeyboardInterrupt:
        write_event(
            log_file,
            "interrupted",
            response_chars=response_chars,
            thinking_chars=thinking_chars,
        )
        return 130
    finally:
        stop_event.set()
        thread.join(timeout=2)

    write_event(
        log_file,
        "ended_without_done",
        response_chars=response_chars,
        thinking_chars=thinking_chars,
    )
    return 5


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a Qwen/Ollama prompt with a lightweight watchdog trace."
    )
    parser.add_argument("--host", default="http://127.0.0.1:11434")
    parser.add_argument("--model", default="qwen3.6-240k-coding:latest")
    parser.add_argument("--prompt")
    parser.add_argument("--prompt-file")
    parser.add_argument("--log", default="logs/qwen-watchdog.jsonl")
    parser.add_argument("--num-ctx", type=int, default=32768)
    parser.add_argument("--num-predict", type=int)
    parser.add_argument("--keep-alive", default="5m")
    parser.add_argument("--stall-timeout", type=float, default=180)
    parser.add_argument("--monitor-interval", type=float, default=15)
    parser.add_argument("--show-thinking", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    log_file = Path(args.log)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    prompt = build_prompt(args)
    return stream_generate(args, prompt, log_file)


if __name__ == "__main__":
    raise SystemExit(main())
