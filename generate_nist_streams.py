#!/usr/bin/env python3
import argparse
import importlib
import os
import sys

# = load RNG class =
def load_rng(module_name, class_name, seed_bytes):
    mod = importlib.import_module(module_name)
    cls = getattr(mod, class_name)
    return cls(seed_bytes)

# = bytes → bitstring =
def bytes_to_bitstring(data, n_bits):
    bits = []
    needed = n_bits
    for b in data:
        for i in range(8):
            if needed == 0:
                return "".join(bits)
            bit = (b >> (7 - i)) & 1
            bits.append("1" if bit else "0")
            needed -= 1
    return "".join(bits)

# = progress bar =
def progress(current, total):
    width = 40
    filled = int(width * (current / total))
    bar = "#" * filled + "-" * (width - filled)
    pct = (current / total) * 100
    sys.stdout.write(f"\r[{bar}] {pct:6.2f}%  ({current}/{total})")
    sys.stdout.flush()

# = main =
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", default="chaos")
    parser.add_argument("--cls", default="ParacleticChaosRNG")
    parser.add_argument("--streams", type=int, default=100)
    parser.add_argument("--bits", type=int, default=1_000_000)
    parser.add_argument("--out-dir", default="data")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    total = args.streams
    for i in range(1, total + 1):
        rng = load_rng(args.module, args.cls, None)
        n_bytes = (args.bits + 7) // 8
        raw = rng.random_bytes(n_bytes)
        bitstr = bytes_to_bitstring(raw, args.bits)
        fname = os.path.join(args.out_dir, f"chaos_{i:03d}.bin")

        with open(fname, "w", encoding="ascii") as f:
            f.write(bitstr)

        progress(i, total)

    print()

if __name__ == "__main__":
    main()
