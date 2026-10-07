# DEL Screening Data: Hands-On Data Engineering Exercise

Welcome, and thanks for taking the time. Please read this whole document
before you write any code. It explains the context, how to set up, what
we'll ask you to do, and what we care about. Most questions you might have
are answered here. Anything that isn't is a good question to ask us during
the session.

---

## 1. Context

You've joined a drug-discovery data team. Our chemists run **DEL screens**
(DNA-encoded library screens): millions of small-molecule compounds, each
tagged with a unique DNA barcode, are exposed to a protein **target**.
Compounds that bind the target are pulled out and their barcodes are
sequenced. The number of sequencing **reads** for a compound tells us how
strongly it was enriched, so a high read count means a potentially
interesting compound (a "hit").

Sequencing results come to us from vendors as CSV files. Scientists rely on
the reports we build from them to decide which compounds to follow up on,
so **numbers that are wrong but look right are worse than a crash**.

You don't need any chemistry or biology knowledge. Everything you need is
in the data and in this document.

---

## 2. Setup (do this before the session)

### 2.1 Requirements

- Python **3.11 or newer**
- About **1 GB free disk space** and **4 GB RAM** (the main file is ~325 MB)
- Install the libraries:

```bash
pip install -r requirements.txt
```

We recommend using the pinned versions so your results are comparable with
ours. If you use a different version, tell us which one (`pd.__version__`).

**Prefer PySpark?** That's fine. Uncomment the `pyspark` line in
`requirements.txt` and make sure Java 17+ is installed. **Check that a
local Spark session starts before the interview**, because setup time comes
out of your exercise time.

### 2.2 Generate the main dataset

The main dataset is too large to send, so you generate it locally. From
this folder, run:

```bash
python generate_del_data.py --rows 3000000 --out del_screening_data.csv
```

(Use `python3` if that's how Python is named on your machine.)

This takes **about one minute** and writes two files:

| File | What it is |
|---|---|
| `del_screening_data.csv` | 3,000,000 rows of screening results (~325 MB) |
| `library_reference.csv` | Metadata for each compound library (regenerated, same content) |

Please run it with exactly these arguments. A different `--rows` value
produces a different dataset, and we won't be able to compare numbers.

**Confirm it worked:** the script prints `rows written : 3,000,000` at the
end, and `del_screening_data.csv` should be around 323 MB.

`del_sample.csv` (50,000 rows) is already included, so you can look at
the data shape before generating the full file.

---

## 3. The data

### 3.1 `del_screening_data.csv`: one row per sequencing result

| Column | Meaning |
|---|---|
| `read_id` | Identifier of the sequencing record |
| `compound_id` | Compound identifier (derived from its three building blocks) |
| `smiles` | Chemical structure of the compound as text (you can treat it as an opaque string) |
| `library_id` | Which compound library the compound came from |
| `bb1_id`, `bb2_id`, `bb3_id` | The three building blocks the compound was assembled from |
| `target` | The protein the compound was screened against |
| `replicate` | Replicate number of the screen (1–3) |
| `screen_date` | Date the screen was run |
| `raw_count` | Number of sequencing reads for this compound in this screen |
| `enrichment_score` | Vendor-computed enrichment of the compound against background |
| `ingested_at` | When this record was received into our system |

A **screening result** is identified by the combination
**`(compound_id, target, replicate)`**. The vendor sometimes re-sends
results for the same combination. When that happens, **the record with the
latest `ingested_at` is the correct one**.

### 3.2 `library_reference.csv`: one row per library

| Column | Meaning |
|---|---|
| `library_id` | Library identifier (join key to the screening data) |
| `library_name` | Human-readable name |
| `num_cycles` | Number of chemistry cycles used to build the library |
| `vendor` | Who built the library |
| `theoretical_size` | Number of distinct compounds the library could contain |

### 3.3 Other files (used in the later parts)

| File | Used in |
|---|---|
| `qc_runs.csv` | Part 2, Challenge A: quality-control runs per library |
| `buggy_pipeline.py` | Part 2, Challenge A |
| `day1.csv`, `day2.csv`, `day3.csv` | Part 2, Challenge B |

**Treat every file as real vendor data that you're seeing for the first time.**

---

## 4. What you'll do

The session has a **core exercise (Part 1)**. Depending on time, we'll
continue with one of the **advanced challenges (Part 2)**. We'll tell you
during the session when to move from one part to the next. **Please don't
start the tasks in advance**: setup and reading the data dictionary are
all we ask beforehand.

### Part 1: Core exercise (~45 minutes, plus discussion)

Part 1 is in stages. Each stage builds on the previous one.

**Stage 1: Load and summarise (~15 min)**

Load `del_screening_data.csv` and answer:

1. How many **valid** records are there?
2. What is the **total number of reads per target**?

What counts as "valid" is part of the exercise. Decide, tell us your
definition, and be ready to justify it. You're welcome to ask us what the
business wants.

**Stage 2: Deduplicate and enrich (~15 min)**

1. Make sure each screening result `(compound_id, target, replicate)`
   appears **once**, keeping the **latest** version by `ingested_at`.
2. Join the result to `library_reference.csv` so each row carries its
   library metadata.
3. Recompute the totals from Stage 1 and **report anything that looks
   suspicious** in the data or the results.

**Stage 3: Requirement change (~15 min)**

We'll give you a change to the requirements at this point. Expect to adapt
the code you've written, not start over.

**Stage 4: Scale discussion (verbal, if time allows)**

A conversation, no code: how would your approach change if the data were
much larger?

### Part 2: Advanced challenges (30–40 minutes)

After Part 1, you'll do **one** of the two challenges below. The interviewer
chooses which one and tells you when to start. If you finish early, we may
move on to the other one or discuss it verbally.

Both challenges are independent of your Part 1 code. You start fresh, in
the same folder.

---

#### Challenge A: The report that ran green

**Files:** `buggy_pipeline.py`, `del_screening_data.csv`,
`library_reference.csv`, `qc_runs.csv`

**The situation**

`buggy_pipeline.py` produces our monthly screening report. It prints three
things:

1. total sequencing reads per target
2. the top 5 compounds by total reads
3. the number of screens per calendar month

It has been running in production for two months **without a single
error**. Last week a scientist emailed:

> *"The OGG1 read totals look roughly 40% higher than our sequencing depth
> allows, and the top-compound list doesn't match what we see in the raw
> data."*

**Your task**

Find **every** defect in this pipeline, not only the one behind the
scientist's complaint. There is more than one, and we won't tell you when
you've found them all.

For **each** defect you find, tell us:

1. **What's wrong**: which line or step, and what it does incorrectly.
2. **How you proved it**: evidence from the data or the output, not only
   from reading the code.
3. **How big the impact is**: roughly how many rows or reads are affected,
   or how much a reported number changes.

Then **fix the script**. Save your fixed version as `fixed_pipeline.py`
(keep the original so the two can be compared).

**How to run it**

```bash
python buggy_pipeline.py
```

It reads the files from the current folder and prints the report. It takes
less than a minute on the full dataset.

**What to hand in**

- `fixed_pipeline.py`
- A short list of defects with the three points above for each. This can
  be notes in a text file, comments, or a notebook. You'll walk us through
  it verbally.
- The report numbers **before and after** your fix.

---

#### Challenge B: The daily loader

**Files:** `day1.csv`, `day2.csv`, `day3.csv`

**The situation**

These are three daily data drops from a sequencing vendor, one file per
day. Each row is a screening result. The rules are:

- The **business key** is `(compound_id, target, replicate)`.
- When the same key appears again (in a later file, or even within the same
  file), **the record with the latest `ingested_at` is the truth**.
- Vendors send corrections and late data whenever they like, and they
  **change their file format without telling anyone**.

**Your task**

Build a loader that can be run as:

```bash
python loader.py day1.csv
python loader.py day2.csv
python loader.py day3.csv
```

Each run reads one file and updates a **current-state table**: one row per
business key, holding the latest version of that record. Store the state
however you like (Parquet, SQLite, CSV, DuckDB, ...), in the current folder.

**Requirements**

1. **Correct in order:** running day 1, then day 2, then day 3 produces the
   correct current state.
2. **Safe to re-run:** re-running **any** file, any number of times, in any
   order after the initial load, changes **nothing** in the state.
3. **Day 3 must load.** Look at it before you promise anything.
4. **Report after every run:** print the number of rows in the state and
   the total reads (sum of the read count) across the state. Be ready to
   explain every change in those numbers between runs.

**How we'll check it**

When you're done, we'll delete your state, run the three days in order,
then **re-run one of the days ourselves and compare the state** before and
after. Make sure a fresh start is easy (for example, tell us which file to
delete).

**What to hand in**

- `loader.py`
- The output of running day 1, day 2, day 3, and one re-run
- A short explanation of how your loader decides which record wins, and
  why re-running is safe

---

## 5. What we're looking for

There's no single "correct" number we're waiting for. We're interested in
**how you work** and **whether you can stand behind your results**:

- **You can explain every number you report**: what you counted, what you
  excluded, and why.
- **You state your decisions and assumptions out loud.** If a decision
  affects the result and the business should make it, ask us rather than
  quietly choosing.
- **You check your own work.** Tell us how you know a result is right, not
  only what it is.
- **Your code is readable and re-runnable.** It doesn't need to be
  production-polished, but someone else should be able to run it and get
  the same answer.
- **You communicate as you go.** Think aloud. A clear explanation of a
  partial solution beats a silent complete one.

At the end we'll ask you for a **~10-minute walkthrough**: what you did,
the numbers you got, the decisions behind them, and what you'd do next with
more time.

---

## 6. Ground rules

- **Tools:** Python with pandas is the default. PySpark, DuckDB, SQL or
  any other tool you're comfortable with is fine. Pick what you'd use at
  work and tell us why.
- **Documentation and web search:** allowed. Looking things up is allowed
- **AI coding assistants:** *[not allowed here]*
- **Questions:** encouraged, at any point. Asking about requirements is
  part of the job, not a weakness.
- **Running things:** run anything you like, as often as you like.
- **Don't modify the input files.** Your code should read them as delivered.

---

## 7. Checklist before the session

- [ ] Python 3.11+ installed, `pip install -r requirements.txt` done
- [ ] `python generate_del_data.py --rows 3000000 --out del_screening_data.csv` ran and printed `rows written : 3,000,000`
- [ ] (PySpark users only) A local Spark session starts successfully
- [ ] Your editor or notebook of choice is ready
- [ ] You've read this README to the end
