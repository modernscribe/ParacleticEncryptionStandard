# Paracletic Chaos RNG (`chaos.py`)

## Overview

`chaos.py` implements the **Paracletic Chaos RNG**, a deterministic random generator built on your 12-dimensional paracletic harmonic fixed-point model. It is designed as a **high-quality entropy source** suitable for:

* General application randomness (IDs, tokens, shuffling, simulations)
* Feeding other PRNGs or crypto systems as an entropy source
* Research and experimentation with the paracletic model

You also have separate tooling (`validate.py`, `generate_nist_streams.py`, NIST STS harness, BigCrush harness) used to **statistically test** the RNG. This README focuses on **normal use**, not the test harness.

> ⚠️ Note: While the generator passes strong statistical tests (NIST STS, etc.), formal cryptographic review is still recommended before deploying it as the sole RNG in high-stakes production cryptography.

---

## Files

* `chaos.py`
  Core implementation of `ParacleticChaosRNG`. This is the only file needed for normal use.

* `validate.py`, `generate_nist_streams.py`, `setupandrunnistchecks.ps1`, `generate_big_crush.py`, NIST STS sources, etc.
  **Optional**. These are for testing and validation only.

For day-to-day use, you only need:

```text
chaos/
  chaos.py
```

or just `chaos.py` somewhere on your Python path.

---

## Requirements

* **Python**: 3.10+ recommended
* **Dependencies**: `chaos.py` is written to use only the Python standard library (no external pip requirements).

If you ever add external imports to `chaos.py`, list them here and install via:

```bash
pip install <package>
```

---

## Installation

### Option 1: Drop-in module

1. Copy `chaos.py` into your project:

   ```text
   your_project/
     app.py
     chaos.py
   ```

2. Import it in your code:

   ```python
   from chaos import ParacleticChaosRNG
   ```

### Option 2: Package directory

If you prefer a package:

```text
your_project/
  chaos/
    __init__.py
    chaos.py
  app.py
```

Inside `chaos/__init__.py`:

```python
from .chaos import ParacleticChaosRNG
```

Then:

```python
from chaos import ParacleticChaosRNG
```

---

## Basic Usage

### Creating an RNG instance

```python
from chaos import ParacleticChaosRNG

# Unseeded / internally seeded instance
rng = ParacleticChaosRNG(None)

# Or: explicitly seeded with bytes
seed = b"your_app_specific_seed_material"
rng = ParacleticChaosRNG(seed)
```

If you pass `None`, the implementation can derive its own seed (e.g., from OS entropy and paracletic state). If you want reproducibility, always pass **explicit seed bytes**.

### Getting random bytes

`generate_nist_streams.py` uses:

```python
raw = rng.random_bytes(n_bytes)
```

You can use the same API in normal code:

```python
# 32 random bytes
buf = rng.random_bytes(32)
print(buf.hex())
```

---

## Higher-level Random Values

If `chaos.py` exposes additional helpers (e.g. `random_u64`, `rand_float`, `randint`), you can build normal random APIs on top. If not, you can derive them yourself from `random_bytes`.

### Example: 64-bit unsigned integers

```python
import struct
from chaos import ParacleticChaosRNG

rng = ParacleticChaosRNG(None)

def random_u64(rng: ParacleticChaosRNG) -> int:
    b = rng.random_bytes(8)
    return struct.unpack(">Q", b)[0]  # big-endian 64-bit

value = random_u64(rng)
print(value)
```

### Example: Uniform float in [0, 1)

```python
import struct

def random_float01(rng: ParacleticChaosRNG) -> float:
    # Use 53 bits of randomness for IEEE-754 double mantissa
    b = rng.random_bytes(8)
    x = struct.unpack(">Q", b)[0] & ((1 << 53) - 1)
    return x / float(1 << 53)
```

### Example: Integer in [low, high]

```python
def randint_range(rng: ParacleticChaosRNG, low: int, high: int) -> int:
    if low > high:
        raise ValueError("low must be <= high")
    span = high - low + 1
    # Rejection sampling to avoid modulo bias
    while True:
        b = rng.random_bytes(8)
        x = int.from_bytes(b, "big", signed=False)
        limit = (1 << 64) - ((1 << 64) % span)
        if x < limit:
            return low + (x % span)
```

---

## Seeding Strategy

Recommended patterns:

* **Non-reproducible / production randomness**
  Pass `None` and let `ParacleticChaosRNG` derive entropy from the environment (if implemented that way).

* **Reproducible experiments / simulations**
  Hash any structured seed into bytes and pass that:

  ```python
  import hashlib, json
  seed_obj = {"experiment": "run_01", "param": 42}
  seed_bytes = hashlib.sha256(json.dumps(seed_obj, sort_keys=True).encode("utf-8")).digest()
  rng = ParacleticChaosRNG(seed_bytes)
  ```

* **Per-session RNGs**
  Derive a seed from a master key plus context and instantiate new RNGs per request, user, or subsystem.

---

## Using `chaos.py` as an App-Level RNG

Examples of normal usage:

### Generating tokens / IDs

```python
def generate_token(rng: ParacleticChaosRNG, length=32) -> str:
    return rng.random_bytes(length).hex()

rng = ParacleticChaosRNG(None)
token = generate_token(rng, 32)
print("Session token:", token)
```

### Shuffling a list

```python
def shuffle_in_place(rng: ParacleticChaosRNG, items):
    for i in range(len(items) - 1, 0, -1):
        j = randint_range(rng, 0, i)
        items[i], items[j] = items[j], items[i]

rng = ParacleticChaosRNG(None)
data = [1, 2, 3, 4, 5]
shuffle_in_place(rng, data)
print(data)
```

---

## Optional: Validation / Test Harness (NIST STS)

You already have a PowerShell harness like:

* `setupandrunnistchecks.ps1` (compiles NIST STS, generates bitstreams from `chaos.py`, runs the battery)
* `generate_nist_streams.py` (uses `ParacleticChaosRNG.random_bytes` to generate files under `./data`)
* `validate.py` (local statistical sanity checks)

These are **not required** in normal usage. They exist to:

* Verify the generator’s statistical properties (monobit, runs, chi², etc.)
* Produce NIST-style reports showing pass rates across multiple tests

If you want, you can keep a short note here:

> For detailed statistical testing (NIST STS), see `setupandrunnistchecks.ps1` and `generate_nist_streams.py`. These tools are separate from normal application usage.

---

## Security Notes

* The Paracletic Chaos RNG is **designed** with cryptographic strength in mind and has passed demanding statistical tests (NIST STS, and optionally more).
* Statistical tests **do not prove** cryptographic security; they only show that outputs look indistinguishable from random for those tests.
* Before using as a core RNG in **high-risk cryptographic protocols**, independent cryptographic review and side-channel analysis are recommended.

For most **application-level randomness needs** (tokens, IDs, shuffling, simulations, internal protocols), `ParacleticChaosRNG` is already usable as a high-quality, deterministic, seedable random source via `chaos.py`.

---

## Quick Summary

* Use `chaos.py` in your app by importing `ParacleticChaosRNG`.
* Instantiate with `None` (environment-derived seed) or explicit `seed_bytes`.
* Call `random_bytes(n)` as your foundational primitive.
* Build any needed abstractions (u64, floats, ranges, shuffles) on top.
* Keep the NIST/BigCrush harness around for validation, not for everyday use.
