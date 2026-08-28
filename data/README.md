# Data directory — E01-EXP

Nothing in this directory is analyzed until it is pinned. Steps:

## 1. Download (owner action, outside this repo's CI)

**NASA PCoE battery dataset** (preferred; has temperature groups and
EIS impedance):
- Landing page: search "NASA Prognostics Center of Excellence Battery
  Dataset" on data.nasa.gov / the PCoE Data Set Repository page
  (c-mapss/battery). Download the battery `.zip` archives (B0005..B0056
  groups). The room-temperature group (B0005, B0006, B0007, B0018) and
  at least one other temperature group (e.g. 43 C: B0029..B0032, or
  4 C group) are required for the (s, T) chart.

**CALCE** (fallback / second source): CALCE Battery Research Group data
page, CS2/CX2 series.

**Oxford battery degradation dataset** (single temperature; reduced
check only): Oxford Research Archive, "Oxford Battery Degradation
Dataset 1".

## 2. Pin

Place raw archives under `data/raw/` (git-ignored if large; keep at
least the extracted `.mat` files you analyze), then:

```bash
cd data && find raw -type f -exec sha256sum {} \; > MANIFEST.sha256
git add MANIFEST.sha256 && git commit -m "Pin E01-EXP raw data hashes"
```

## 3. Run

```bash
python -m pip install numpy scipy pytest
python campaigns/E01_CELL_CHART_AUDIT/run_e01_exp.py
```

The runner refuses to start if `data/MANIFEST.sha256` is missing or if
any listed file's hash no longer matches — pin first, analyze second.
Everything else (slots, statistics, thresholds, predictions P1–P3) is
locked in `E01_EXP_PREREGISTRATION.md`, committed before this data was
downloaded.
