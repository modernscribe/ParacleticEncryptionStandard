#!/usr/bin/env python3
import argparse
import os
import sys
import time
from chaos import ParacleticChaosRNG

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--words", type=int, default=50_000_000)
    parser.add_argument("--out", default="chaos_bigcrush_u32.bin")
    args = parser.parse_args()

    rng = ParacleticChaosRNG(None)
    total = args.words
    out_path = args.out

    print(f"Generating {total} uint32 words into {os.path.abspath(out_path)}", flush=True)

    chunk = 1_000_000
    written = 0
    start = time.time()

    try:
        with open(out_path, "wb") as f:
            while written < total:
                k = chunk if (total - written) >= chunk else (total - written)
                raw = rng.random_bytes(4 * k)
                f.write(raw)
                written += k

                elapsed = time.time() - start
                pct = (written / total) * 100.0 if total > 0 else 0.0
                rate = written / elapsed if elapsed > 0 else 0.0
                eta = (total - written) / rate if rate > 0 else 0.0

                print(
                    f"progress: {written}/{total} ({pct:6.2f}%)  "
                    f"elapsed:{elapsed:8.1f}s  "
                    f"rate:{rate:10.0f} words/s  "
                    f"eta:{eta:8.1f}s",
                    flush=True
                )
    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        raise

    total_elapsed = time.time() - start
    print(f"Done. Total elapsed: {total_elapsed:8.2f}s", flush=True)

if __name__ == "__main__":
    main()
