#!/usr/bin/env python3
import argparse
import math
import subprocess
import sys
import time
from typing import Optional, Tuple

import numpy as np


def parse_args():
    ap = argparse.ArgumentParser(description="Realtime mic RMS->dB monitor with debounce + hysteresis.")
    ap.add_argument("--device", default="plughw:2,0", help="ALSA capture device, e.g., plughw:2,0")
    ap.add_argument("--rate", type=int, default=44100, help="Sample rate")
    ap.add_argument("--chunk_ms", type=int, default=500, help="Window size in ms (larger = smoother, more latency)")
    ap.add_argument("--ref", type=float, default=1.0, help="Reference RMS for dB (relative dBFS-like)")
    ap.add_argument("--threshold_db", type=float, default=-60.0, help="ON threshold in dB (relative to ref)")
    ap.add_argument("--hysteresis_db", type=float, default=6.0, help="OFF threshold = threshold_db - hysteresis_db")

    # Debounce: require N consecutive windows to switch
    ap.add_argument("--debounce_on", type=int, default=3, help="Consecutive windows >= ON threshold to turn ON")
    ap.add_argument("--debounce_off", type=int, default=3, help="Consecutive windows < OFF threshold to turn OFF")

    # arecord buffering (helps with occasional USB jitter)
    ap.add_argument("--buffer_size", type=int, default=32768, help="arecord --buffer-size (0 to disable)")
    ap.add_argument("--period_size", type=int, default=8192, help="arecord --period-size (0 to disable)")

    # Output formatting
    ap.add_argument("--print_header", action="store_true", help="Print CSV header first")
    ap.add_argument("--print_every", type=int, default=1, help="Print every N windows (>=1)")

    return ap.parse_args()


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
    """
    Blocking read of exactly nbytes unless EOF.
    """
    buf = bytearray()
    while len(buf) < nbytes:
        chunk = stdout.read(nbytes - len(buf))
        if not chunk:
            return None
        buf.extend(chunk)
    return bytes(buf)


def main():
    args = parse_args()

    if args.debounce_on < 1 or args.debounce_off < 1:
        print("debounce_on/off must be >= 1", file=sys.stderr)
        return 2
    if args.print_every < 1:
        print("print_every must be >= 1", file=sys.stderr)
        return 2

    bytes_per_sample = 2  # S16_LE mono
    samples_per_chunk = int(args.rate * args.chunk_ms / 1000)
    bytes_per_chunk = samples_per_chunk * bytes_per_sample

    on_th = args.threshold_db
    off_th = args.threshold_db - args.hysteresis_db

    cmd = build_arecord_cmd(args.device, args.rate, args.buffer_size, args.period_size)

    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
    except FileNotFoundError:
        print("arecord not found. Install alsa-utils.", file=sys.stderr)
        return 1

    # Debounce counters
    on_count = 0
    off_count = 0
    state_on = False

    if args.print_header:
        print("ts,rms,db,on_count,off_count,trigger", flush=True)

    i = 0
    try:
        while True:
            raw = read_exact(p.stdout, bytes_per_chunk)
            if raw is None:
                # arecord ended or pipe broken
                time.sleep(0.05)
                continue

            x = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
            x /= 32768.0
            rms = float(np.sqrt(np.mean(x * x)))
            db = rms_to_db(rms, args.ref)

            # Debounced hysteresis switching:
            # - To turn ON: need db >= on_th for debounce_on consecutive windows
            # - To turn OFF: need db < off_th for debounce_off consecutive windows
            if not state_on:
                if db >= on_th:
                    on_count += 1
                else:
                    on_count = 0
                # while off, we don't accumulate off_count meaningfully
                off_count = 0

                if on_count >= args.debounce_on:
                    state_on = True
                    on_count = 0  # reset after switching
            else:
                if db < off_th:
                    off_count += 1
                else:
                    off_count = 0
                on_count = 0

                if off_count >= args.debounce_off:
                    state_on = False
                    off_count = 0  # reset after switching

            i += 1
            if i % args.print_every == 0:
                print(
                    f"{time.time():.3f},{rms:.6f},{db:.2f},{on_count},{off_count},{int(state_on)}",
                    flush=True
                )

    except KeyboardInterrupt:
        pass
    finally:
        try:
            p.terminate()
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

