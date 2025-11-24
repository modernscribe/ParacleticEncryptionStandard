#!/usr/bin/env python3
import os
import sys
import time
import math
import argparse
import hashlib
import secrets
import struct
from typing import Optional
import numpy as np

N_DIM = 12
EPS = 1e-12
PRINCIPLES = ["Truth", "Purity", "Law", "Love", "Wisdom", "Life", "Glory"]

def Null_point() -> float:
    return 0.0

def InverseZero_operator(p: float) -> float:
    return -0.0 if p == 0.0 else -0.0

def H_inverse_zero_null() -> float:
    return 1.0

def f_truth(x: np.ndarray) -> np.ndarray:
    return x.copy()

def f_purity(x: np.ndarray) -> np.ndarray:
    abs_x = np.abs(x)
    s = np.sum(abs_x)
    if s < EPS:
        return np.full_like(x, Null_point())
    return abs_x / s

def f_law(x: np.ndarray) -> np.ndarray:
    return np.clip(x, -1.0, 1.0)

def f_love(x: np.ndarray) -> np.ndarray:
    m = np.mean(x)
    result = (x + m) * 0.5
    mask = np.abs(result) < EPS
    result[mask] = InverseZero_operator(0.0)
    return result

def f_wisdom(x: np.ndarray) -> np.ndarray:
    left = np.roll(x, 1)
    right = np.roll(x, -1)
    return (x + 0.5 * (left + right)) * 0.5

def f_life(x: np.ndarray) -> np.ndarray:
    base = np.tanh(x)
    zeta = H_inverse_zero_null()
    return base * zeta

def f_glory(x: np.ndarray) -> np.ndarray:
    v = np.where(x >= 0, x * x, -x * x)
    s = np.sum(np.abs(v))
    if s < EPS:
        return np.full_like(x, Null_point())
    return v / s

PRINCIPLE_MAP = {
    "Truth": f_truth,
    "Purity": f_purity,
    "Law": f_law,
    "Love": f_love,
    "Wisdom": f_wisdom,
    "Life": f_life,
    "Glory": f_glory,
}

def apply_principle(name: str, x: np.ndarray) -> np.ndarray:
    return PRINCIPLE_MAP[name](x)

def step_vector(x: np.ndarray, enabled: np.ndarray) -> np.ndarray:
    x_masked = x * enabled
    for name in PRINCIPLES:
        x_masked = apply_principle(name, x_masked)
    return x_masked

class ParacleticChaosRNG:
    def __init__(self, seed_bytes: Optional[bytes] = None):
        if seed_bytes is None:
            seed_material = b"".join([
                os.urandom(32),
                secrets.token_bytes(32),
                int(time.time_ns()).to_bytes(8, "big"),
                os.getpid().to_bytes(4, "big", signed=False),
            ])
        else:
            if len(seed_bytes) < 32:
                seed_material = hashlib.sha256(seed_bytes).digest()
            else:
                seed_material = seed_bytes
        self.key = hashlib.sha256(seed_material + b"|key").digest()
        base_vec = np.ones(N_DIM, dtype=float) / float(N_DIM)
        noise_src = hashlib.sha512(seed_material + b"|init").digest()
        vals = []
        for i in range(N_DIM):
            chunk = noise_src[(i * 4) % len(noise_src):(i * 4) % len(noise_src) + 4]
            if len(chunk) < 4:
                chunk = (chunk + noise_src)[:4]
            v = int.from_bytes(chunk, "big")
            vals.append(((v / 2**32) * 2.0) - 1.0)
        noise_vec = np.array(vals, dtype=float) * 1e-3
        self.state = base_vec + noise_vec
        self.enabled = np.array([i in (0, 4, 7) for i in range(N_DIM)], dtype=float)
        self.counter = 0

    def _step(self) -> None:
        self.state = step_vector(self.state, self.enabled)
        ctr_bytes = self.counter.to_bytes(16, "big", signed=False)
        mix = hashlib.sha512(self.key + ctr_bytes).digest()
        vals = []
        for i in range(N_DIM):
            chunk = mix[(i * 4) % len(mix):(i * 4) % len(mix) + 4]
            if len(chunk) < 4:
                chunk = (chunk + mix)[:4]
            v = int.from_bytes(chunk, "big")
            vals.append(((v / 2**32) * 2.0) - 1.0)
        jitter = np.array(vals, dtype=float) * 1e-9
        self.state = self.state + jitter
        norm = float(np.sum(np.abs(self.state)))
        if norm > EPS:
            self.state = self.state / norm
        state_bytes = self._vector_to_bytes()
        self.key = hashlib.sha256(self.key + state_bytes + ctr_bytes).digest()
        self.counter += 1

    def _vector_to_bytes(self) -> bytes:
        buf = []
        for v in self.state:
            buf.append(struct.pack("!d", float(v)))
        return b"".join(buf)

    def random_bytes(self, n: int) -> bytes:
        out = b""
        while len(out) < n:
            for _ in range(5):
                self._step()
            ctr_bytes = self.counter.to_bytes(16, "big", signed=False)
            block = hashlib.sha256(self._vector_to_bytes() + self.key + ctr_bytes).digest()
            out += block
            self.counter += 1
        return out[:n]

def selftest() -> bool:
    seed = hashlib.sha256(b"paracletic_selftest_seed").digest()
    rng1 = ParacleticChaosRNG(seed)
    rng2 = ParacleticChaosRNG(seed)
    a = rng1.random_bytes(64)
    b = rng2.random_bytes(64)
    if a != b:
        print("SELFTEST FAIL: determinism check failed")
        return False
    rng3 = ParacleticChaosRNG(os.urandom(32))
    rng4 = ParacleticChaosRNG(os.urandom(32))
    c = rng3.random_bytes(64)
    d = rng4.random_bytes(64)
    if c == d:
        print("SELFTEST FAIL: distinct seeds produced identical streams")
        return False
    sample_bits = 131072
    sample_bytes = sample_bits // 8
    rng_stat = ParacleticChaosRNG(os.urandom(32))
    stream = rng_stat.random_bytes(sample_bytes)
    ones = 0
    for byte in stream:
        ones += bin(byte).count("1")
    prop_ones = ones / float(sample_bits)
    if not (0.49 <= prop_ones <= 0.51):
        print(f"SELFTEST FAIL: monobit frequency out of range: {prop_ones:.6f}")
        return False
    freq_stream = rng_stat.random_bytes(65536)
    counts = [0] * 256
    for byte in freq_stream:
        counts[byte] += 1
    expected = len(freq_stream) / 256.0
    low = expected * 0.4
    high = expected * 2.6
    for i, ccount in enumerate(counts):
        if ccount < low or ccount > high:
            print(f"SELFTEST FAIL: byte frequency for {i} out of range: {ccount}")
            return False
    print("SELFTEST PASS")
    return True

def main() -> None:
    parser = argparse.ArgumentParser(description="Paracletic chaos-based random byte generator")
    parser.add_argument("-n", "--bytes", type=int, default=32, help="Number of random bytes to output")
    parser.add_argument("--seed", type=str, default=None, help="Hex-encoded seed (optional)")
    parser.add_argument("--selftest", action="store_true", help="Run internal self-test suite")
    args = parser.parse_args()
    if args.selftest:
        ok = selftest()
        sys.exit(0 if ok else 1)
    seed_bytes = None
    if args.seed is not None:
        try:
            seed_bytes = bytes.fromhex(args.seed.strip())
        except Exception:
            print("Invalid seed hex string", file=sys.stderr)
            sys.exit(1)
    rng = ParacleticChaosRNG(seed_bytes)
    data = rng.random_bytes(args.bytes)
    print(data.hex())

if __name__ == "__main__":
    main()
