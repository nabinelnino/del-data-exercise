#!/usr/bin/env python3


import argparse
import os
import sys
import time

import numpy as np
import pandas as pd

SEED = 42
CSV_CHUNK_ROWS = 100_000

TARGETS = ["OGG1", "CA9", "WDR91", "SETDB1", "BRD4", "MTHFD2"]
TARGET_P = [0.40, 0.14, 0.13, 0.12, 0.11, 0.10]

LIBRARIES = ["LIB-A01", "LIB-A02", "LIB-B07", "LIB-C03", "LIB-D11", "LIB-E09"]

MISSING_FROM_REF = {"LIB-D11", "LIB-E09"}

SMILES_FRAGS_A = ["c1ccccc1", "c1ccncc1",
                  "C1CCNCC1", "c1ccc2[nH]ccc2c1", "C1CCOC1"]
SMILES_FRAGS_B = ["CC(=O)N", "NC(=O)C", "OCC", "N(C)C", "C(F)(F)F"]
SMILES_FRAGS_C = ["CN1CCN(CC1)", "OC(=O)", "S(=O)(=O)N", "NC1CC1", "Cc1ccco1"]


class Progress:
    """Single-line progress bar on a terminal; plain step lines otherwise."""

    WIDTH = 30

    def __init__(self):
        self.start = time.time()
        self.tty = sys.stdout.isatty()
        self.label = None

    def update(self, frac, label):
        elapsed = time.time() - self.start
        if self.tty:
            filled = int(frac * self.WIDTH)
            bar = "█" * filled + "░" * (self.WIDTH - filled)
            sys.stdout.write(f"\r  [{bar}] {frac:6.1%}  {label:<34} {elapsed:5.1f}s")
            sys.stdout.flush()
        elif label != self.label:
            print(f"  {frac:6.1%}  {label}", flush=True)
        self.label = label

    def finish(self):
        self.update(1.0, "Done")
        if self.tty:
            sys.stdout.write("\n")
        return time.time() - self.start


def make_dates(n, rng, progress=None):
    """Random dates in 2026 H1, emitted in three different string formats."""
    step = progress.update if progress else (lambda *_: None)
    base = np.datetime64("2026-01-01")
    offsets = rng.integers(0, 180, size=n)
    dates = base + offsets.astype("timedelta64[D]")
    dts = pd.to_datetime(dates)
    fmt_pick = rng.random(n)
    step(0.14, "Generating screen dates")
    iso = dts.strftime("%Y-%m-%d")
    step(0.30, "Generating screen dates")
    dmy = dts.strftime("%d/%m/%Y")
    step(0.44, "Generating screen dates")
    mon = dts.strftime("%b %d %Y")
    step(0.56, "Generating screen dates")
    out = np.where(fmt_pick < 0.60, iso, np.where(fmt_pick < 0.85, dmy, mon))
    return out


def make_counts(n, rng):

    counts = rng.negative_binomial(2, 0.02, size=n)  #
    hit_mask = rng.random(n) < 0.02
    counts[hit_mask] = rng.integers(1_000, 80_000, size=hit_mask.sum())
    s = counts.astype(str).astype(object)

    junk = rng.random(n)

    s[junk < 0.015] = "N/A"

    mask_comma = (junk >= 0.015) & (junk < 0.315) & (counts >= 1000)
    s[mask_comma] = pd.Series(counts[mask_comma]).map("{:,}".format).values
    mask_pad = (junk >= 0.03) & (junk < 0.05)
    s[mask_pad] = "  " + pd.Series(counts[mask_pad]).astype(str).values + " "
    return s


def generate(n_rows: int, out_csv: str, ref_csv: str):
    print(f"Generating {n_rows:,} rows -> {out_csv} (seed {SEED})")
    progress = Progress()
    progress.update(0.0, "Starting")

    rng = np.random.default_rng(SEED)

    n_base = int(n_rows * 0.95)

    progress.update(0.005, "Generating targets and libraries")
    target = rng.choice(TARGETS, size=n_base, p=TARGET_P)
    library = rng.choice(LIBRARIES, size=n_base).astype(object)

    null_mask = rng.random(n_base) < 0.05
    library[null_mask] = None

    progress.update(0.01, "Generating compounds")
    bb1 = rng.integers(1, 401, size=n_base)
    bb2 = rng.integers(1, 401, size=n_base)
    bb3 = rng.integers(1, 401, size=n_base)

    compound_id = np.char.add(
        "DEL-",
        np.char.add(
            np.char.zfill(bb1.astype(str), 3),
            np.char.add(np.char.zfill(bb2.astype(str), 3),
                        np.char.zfill(bb3.astype(str), 3)),
        ),
    )

    progress.update(0.05, "Generating structures")
    smiles = (
        pd.Series(rng.choice(SMILES_FRAGS_A, size=n_base))
        + pd.Series(rng.choice(SMILES_FRAGS_B, size=n_base))
        + pd.Series(rng.choice(SMILES_FRAGS_C, size=n_base))
    ).values

    progress.update(0.10, "Generating screen dates")
    screen_date = make_dates(n_base, rng, progress)
    progress.update(0.58, "Generating read counts")
    raw_count = make_counts(n_base, rng)

    progress.update(0.61, "Generating scores and timestamps")
    enrichment =np.round(rng.gamma(2.0, 1.5, size=n_base), 3)
    neg_mask = rng.random(n_base) < 0.001
    enrichment[neg_mask] = - \
        np.round(rng.uniform(1, 50, size=neg_mask.sum()), 3)

    replicate = rng.integers(1, 4, size=n_base)

    ingested = pd.Timestamp("2026-06-01 00:00:00") + pd.to_timedelta(
        rng.integers(0, 86400 * 30, size=n_base), unit="s"
    )

    progress.update(0.63, "Assembling records")
    df = pd.DataFrame(
        {
            "read_id": np.arange(1, n_base + 1),
            "compound_id": compound_id,
            "smiles": smiles,
            "library_id": library,
            "bb1_id": bb1,
            "bb2_id": bb2,
            "bb3_id": bb3,
            "target": target,
            "replicate": replicate,
            "screen_date": screen_date,
            "raw_count": raw_count,
            "enrichment_score": enrichment,
            "ingested_at": ingested.strftime("%Y-%m-%d %H:%M:%S"),
        }
    )

    n_dup = int(n_rows * 0.02)
    dup_rows = df.sample(n=n_dup, random_state=1)

    n_corr = n_rows - n_base - n_dup
    corr = df.sample(n=n_corr, random_state=2).copy()
    corr["read_id"] = np.arange(n_base + 1, n_base + 1 + n_corr)
    corr["raw_count"] = make_counts(n_corr, np.random.default_rng(7))
    corr["enrichment_score"] = np.round(
        np.random.default_rng(8).gamma(2.0, 1.5, size=n_corr), 3
    )
    corr["ingested_at"] = (
        pd.to_datetime(corr["ingested_at"])
        + pd.to_timedelta(np.random.default_rng(9).integers(3600,
                          86400 * 5, size=n_corr), unit="s")
    ).dt.strftime("%Y-%m-%d %H:%M:%S")

    progress.update(0.67, "Shuffling records")
    full = pd.concat([df, dup_rows, corr], ignore_index=True)
    full = full.sample(frac=1.0, random_state=3).reset_index(
        drop=True)  # shuffle

    # Write in chunks so the bar can move while the file is written (the
    # slowest step). Output is byte-identical to a single to_csv call.
    write_start, write_end = 0.72, 0.99
    with open(out_csv, "w", newline="") as f:
        for start in range(0, len(full), CSV_CHUNK_ROWS):
            full.iloc[start:start + CSV_CHUNK_ROWS].to_csv(
                f, index=False, header=(start == 0))
            done = min(start + CSV_CHUNK_ROWS, len(full)) / len(full)
            progress.update(write_start + (write_end - write_start) * done,
                            f"Writing {os.path.basename(out_csv)}")

    progress.update(0.995, f"Writing {os.path.basename(ref_csv)}")
    ref_rows = []
    for lib in LIBRARIES:
        if lib in MISSING_FROM_REF:
            continue
        ref_rows.append(
            {
                "library_id": lib,
                "library_name": f"Library {lib.split('-')[1]}",
                "num_cycles": int(rng.integers(2, 4)),
                "vendor": rng.choice(["ChemSpace", "WuXi", "InHouse"]),
                "theoretical_size": int(rng.integers(1, 60)) * 1_000_000,
            }
        )
    ref_rows.append(
        {
            "library_id": "LIB-Z99",
            "library_name": "Library Z99",
            "num_cycles": 3,
            "vendor": "InHouse",
            "theoretical_size": 8_000_000,
        }
    )
    pd.DataFrame(ref_rows).to_csv(ref_csv, index=False)

    elapsed = progress.finish()
    size_mb = os.path.getsize(out_csv) / 1024 ** 2
    print(f"Finished in {elapsed:.1f}s")
    print(f"rows written           : {len(full):,}")
    print(f"  {out_csv} ({size_mb:,.0f} MB)")
    print(f"  {ref_csv}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=3_000_000)
    ap.add_argument("--out", default="del_screening_data.csv")
    ap.add_argument("--ref", default="library_reference.csv")
    args = ap.parse_args()
    generate(args.rows, args.out, args.ref)
