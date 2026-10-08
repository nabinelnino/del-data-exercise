#!/usr/bin/env python3
"""
DEL screening summary report.  (CANDIDATE-FACING — looks fine, ran green.)

Produces the monthly screening report:
  1. total sequencing reads per target
  2. top 5 compounds by total reads
  3. screens per calendar month

Inputs: del_screening_data.csv, library_reference.csv, qc_runs.csv
"""

import pandas as pd


def main():
    df = pd.read_csv("del_screening_data.csv")
    ref = pd.read_csv("library_reference.csv")
    qc = pd.read_csv("qc_runs.csv")

    df["screen_date"] = pd.to_datetime(df["screen_date"], format="mixed",
                                       errors="coerce")
    df["raw_count"] = pd.to_numeric(df["raw_count"], errors="coerce")

    # deduplicate re-sequenced records
    df = df.drop_duplicates(subset=["compound_id", "target", "replicate"],
                            keep="first")

    # enrich with library metadata and QC
    df = df.merge(ref, on="library_id", how="inner")
    df = df.merge(qc, on="library_id", how="left")

    # 1) total reads per target
    per_target = (df.groupby("target")["raw_count"].sum()
                    .sort_values(ascending=False).astype("Int64"))
    print("=== total reads per target ===")
    print(per_target.to_string())

    # 2) top 5 compounds by total reads
    top5 = (df.groupby("compound_id")["raw_count"].sum()
              .sort_values(ascending=False).head(5).astype("Int64"))
    print("\n=== top 5 compounds ===")
    print(top5.to_string())

    # 3) screens per month
    monthly = df.groupby(df["screen_date"].dt.to_period("M")).size()
    print("\n=== screens per month ===")
    print(monthly.to_string())


if __name__ == "__main__":
    main()
