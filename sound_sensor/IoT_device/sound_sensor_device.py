#!/usr/bin/env python3
'''
python sound_sensor/IoT_device/sound_sensor_device.py \
  --device plughw:2,0 \
  --threshold_db -63 \
  --hysteresis_db 6 \
  --debounce_on 2 \
  --debounce_off 4 \
  --chunk_ms 300 \
  --http_port 8787
'''
import argparse
import json
import math
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from typing import Optional, Dict, Any

try:
    import numpy as np
except ImportError:
    np = None


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class AudioState:
    def __init__(self):
        self.lock = threading.Lock()
        self.ts = 0.0
        self.rms = 0.0
        self.db = -120.0
        self.trigger = 0

    def snapshot(self) -> Dict[str, Any]:
        with self.lock:
            return {"ts": self.ts, "rms": self.rms, "db": self.db, "trigger": self.trigger}

    def update(self, ts: float, rms: float, db: float, trigger: int):
        with self.lock:
            self.ts = ts
            self.rms = rms
            self.db = db
            self.trigger = trigger


def rms_to_db(rms: float, ref: float) -> float:
    eps = 1e-12
    return 20.0 * math.log10(max(rms, eps) / max(ref, eps))


def build_arecord_cmd(device: str, rate: int, buffer_size: int, period_size: int) -> list:
    cmd = [
        "arecord",
        "-D", device,
        "-f", "S16_LE",
        "-r", str(rate),
        "-c", "1",
        "-t", "raw",
        "-q",
    ]
    if buffer_size and buffer_size > 0:
        cmd.insert(-1, f"--buffer-size={buffer_size}")
    if period_size and period_size > 0:
        cmd.insert(-1, f"--period-size={period_size}")
    return cmd


def read_exact(stdout, nbytes: int) -> Optional[bytes]:
    buf = bytearray()
    while len(buf) < nbytes:
        chunk = stdout.read(nbytes - len(buf))
        if not chunk:
            return None
        buf.extend(chunk)
    return bytes(buf)


def audio_loop(
    state: AudioState,
    stop_evt: threading.Event,
    device: str,
    rate: int,
    chunk_ms: int,
    ref: float,
    threshold_db: float,
    hysteresis_db: float,
    debounce_on: int,
    debounce_off: int,
    buffer_size: int,
    period_size: int,
):
    if np is None:
        raise RuntimeError("numpy not installed. Install: sudo apt install -y python3-numpy")

    bytes_per_sample = 2
    samples_per_chunk = int(rate * chunk_ms / 1000)
    bytes_per_chunk = samples_per_chunk * bytes_per_sample

    on_th = threshold_db
    off_th = threshold_db - hysteresis_db

    cmd = build_arecord_cmd(device, rate, buffer_size, period_size)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)

    state_on = False
    on_count = 0
    off_count = 0

    try:
        while not stop_evt.is_set():
            raw = read_exact(p.stdout, bytes_per_chunk)
            if raw is None:
                time.sleep(0.05)
                continue

            x = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
            x /= 32768.0
            rms = float(np.sqrt(np.mean(x * x)))
            db = rms_to_db(rms, ref)

            if not state_on:
                if db >= on_th:
                    on_count += 1
                else:
                    on_count = 0
                off_count = 0
                if on_count >= debounce_on:
                    state_on = True
                    on_count = 0
            else:
                if db < off_th:
                    off_count += 1
                else:
                    off_count = 0
                on_count = 0
                if off_count >= debounce_off:
                    state_on = False
                    off_count = 0

            state.update(time.time(), rms, db, 1 if state_on else 0)
    finally:
        try:
            p.terminate()
        except Exception:
            pass


def make_handler(audio_state: AudioState):
    class Handler(BaseHTTPRequestHandler):
        server_version = "PiSoundSensor/0.1"

        def log_message(self, fmt, *args):
            return

        def _send_json(self, code: int, obj: Dict[str, Any]):
            b = json.dumps(obj).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            if self.path == "/health":
                self._send_json(200, {"ok": True})
                return

            if self.path == "/state":
                snap = audio_state.snapshot()
                # IMPORTANT: root-level db/trigger for Edge driver v1
                self._send_json(200, {
                    "ts": snap["ts"],
                    "rms": snap["rms"],
                    "db": snap["db"],
                    "trigger": snap["trigger"],
                })
                return

            self._send_json(404, {"error": "not found"})

    return Handler


def parse_args():
    ap = argparse.ArgumentParser(description="Pi USB mic sound sensor (HTTP polling server for SmartThings Edge v1).")
    ap.add_argument("--device", default="plughw:2,0")
    ap.add_argument("--rate", type=int, default=44100)
    ap.add_argument("--chunk_ms", type=int, default=300)
    ap.add_argument("--ref", type=float, default=1.0)
    ap.add_argument("--threshold_db", type=float, default=-60.0)
    ap.add_argument("--hysteresis_db", type=float, default=6.0)
    ap.add_argument("--debounce_on", type=int, default=2)
    ap.add_argument("--debounce_off", type=int, default=4)
    ap.add_argument("--buffer_size", type=int, default=32768)
    ap.add_argument("--period_size", type=int, default=8192)
    ap.add_argument("--http_port", type=int, default=8787)
    return ap.parse_args()


def main():
    args = parse_args()
    audio_state = AudioState()
    stop_evt = threading.Event()

    t_audio = threading.Thread(
        target=audio_loop,
        args=(
            audio_state, stop_evt,
            args.device, args.rate, args.chunk_ms, args.ref,
            args.threshold_db, args.hysteresis_db,
            args.debounce_on, args.debounce_off,
            args.buffer_size, args.period_size,
        ),
        daemon=True,
    )
    t_audio.start()

    server = ThreadedHTTPServer(("0.0.0.0", args.http_port), make_handler(audio_state))

    print(f"[pi] http://0.0.0.0:{args.http_port}  GET /health, GET /state")
    print(f"[pi] mic={args.device} chunk_ms={args.chunk_ms} th={args.threshold_db} hyst={args.hysteresis_db} "
          f"debounce_on={args.debounce_on} debounce_off={args.debounce_off}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop_evt.set()
        try:
            server.shutdown()
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
