#!/usr/bin/env python3


import argparse
import numpy as np
import pandas as pd

SEED = 42

TARGETS = ["OGG1", "CA9", "WDR91", "SETDB1", "BRD4", "MTHFD2"]
TARGET_P = [0.40, 0.14, 0.13, 0.12, 0.11, 0.10]

LIBRARIES = ["LIB-A01", "LIB-A02", "LIB-B07", "LIB-C03", "LIB-D11", "LIB-E09"]

MISSING_FROM_REF = {"LIB-D11", "LIB-E09"}

SMILES_FRAGS_A = ["c1ccccc1", "c1ccncc1",
                  "C1CCNCC1", "c1ccc2[nH]ccc2c1", "C1CCOC1"]
SMILES_FRAGS_B = ["CC(=O)N", "NC(=O)C", "OCC", "N(C)C", "C(F)(F)F"]
SMILES_FRAGS_C = ["CN1CCN(CC1)", "OC(=O)", "S(=O)(=O)N", "NC1CC1", "Cc1ccco1"]


def make_dates(n, rng):
    """Random dates in 2026 H1, emitted in three different string formats."""
    base = np.datetime64("2026-01-01")
    offsets = rng.integers(0, 180, size=n)
    dates = base + offsets.astype("timedelta64[D]")
    dts = pd.to_datetime(dates)
    fmt_pick = rng.random(n)
    iso = dts.strftime("%Y-%m-%d")
    dmy = dts.strftime("%d/%m/%Y")
    mon = dts.strftime("%b %d %Y")
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
    rng = np.random.default_rng(SEED)

    n_base = int(n_rows * 0.95)

    target = rng.choice(TARGETS, size=n_base, p=TARGET_P)
    library = rng.choice(LIBRARIES, size=n_base).astype(object)

    null_mask = rng.random(n_base) < 0.05
    library[null_mask] = None

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

    smiles = (
        pd.Series(rng.choice(SMILES_FRAGS_A, size=n_base))
        + pd.Series(rng.choice(SMILES_FRAGS_B, size=n_base))
        + pd.Series(rng.choice(SMILES_FRAGS_C, size=n_base))
    ).values

    screen_date = make_dates(n_base, rng)
    raw_count = make_counts(n_base, rng)

    enrichment = np.round(rng.gamma(2.0, 1.5, size=n_base), 3)
    neg_mask = rng.random(n_base) < 0.001
    enrichment[neg_mask] = - \
        np.round(rng.uniform(1, 50, size=neg_mask.sum()), 3)

    replicate = rng.integers(1, 4, size=n_base)

    ingested = pd.Timestamp("2026-06-01 00:00:00") + pd.to_timedelta(
        rng.integers(0, 86400 * 30, size=n_base), unit="s"
    )

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

    full = pd.concat([df, dup_rows, corr], ignore_index=True)
    full = full.sample(frac=1.0, random_state=3).reset_index(
        drop=True)  # shuffle
    full.to_csv(out_csv, index=False)

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

    print(f"rows written           : {len(full):,}")
    print(f"exact duplicate rows   : {n_dup:,}")
    print(f"correction records     : {n_corr:,}")
    print(f"null library_id rows   : {full['library_id'].isna().sum():,}")
    print(f"OGG1 share (skew)      : {(full['target'] == 'OGG1').mean():.1%}")
    junk_ct = full["raw_count"].astype(
        str).str.strip().str.replace(",", "").str.isnumeric()
    print(f"non-numeric raw_count  : {(~junk_ct).sum():,}")
    print(f"negative enrichment    : {(full['enrichment_score'] < 0).sum():,}")
    print(f"libraries missing from reference: {sorted(MISSING_FROM_REF)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=3_000_000)
    ap.add_argument("--out", default="del_screening_data.csv")
    ap.add_argument("--ref", default="library_reference.csv")
    args = ap.parse_args()
    generate(args.rows, args.out, args.ref)
