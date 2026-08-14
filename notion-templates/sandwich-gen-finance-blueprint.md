# Generasi Sandwich — Finance OS
### Backend Database Architecture & Formula Spec (Notion Formulas 2.0)

> **Audience:** Indonesian *Generasi Sandwich* — professionals funding parents/extended family **and** their own household/kids.
> **Design philosophy:** One entry point (the Ledger). Everything else — wallet balances, category spend, sandwich burden — **rolls up automatically**. The user logs a transaction; the system visualizes the consequences.

---

## 0. Architecture at a Glance

```
                 ┌─────────────────────────────┐
                 │  3. MONTHLY TRANSACTION      │
                 │     LEDGER (single entry pt) │
                 │  Pemasukan / Pengeluaran     │
                 └───────┬───────────────┬──────┘
                         │ Relation      │ Relation
            ┌────────────▼───┐      ┌────▼─────────────────┐
            │ 1. WALLETS &   │      │ 2. ALLOCATION &      │
            │    POCKETS     │      │    EXPENSE CATEGORIES│
            │ (Sisa Saldo)   │      │ (Burden / Progress)  │
            └────────────────┘      └──────────────────────┘

            ┌────────────────────────────────────┐
            │ 4. LOCAL INVESTMENT TRACKER         │
            │ (Bibit / Stockbit / Ajaib / Emas)   │  ← stand-alone, optional link to Wallets
            └────────────────────────────────────┘
```

**Friction-minimizing principle:** The two relation fields on the Ledger (`Dompet`, `Kategori`) are the *only* manual links the user maintains. All balances and budget bars are derived via rollups — zero double-entry.

**Naming note:** Database names in Title Case; this premium build uses Title Case for buyer-facing property names (overrides the internal lowercase dev convention for polish). Indonesian financial terms used where they read naturally: *Pemasukan, Pengeluaran, Dompet, Investasi, Alokasi*.

---

## 1. Multi-Wallet & Pockets DB — *Dompet & Pockets*

Tracks every balance container: BCA, Bank Jago Pockets, GoPay, ShopeePay, cash, gold.

| Property Name | Property Type | Configuration / Relation Details | Purpose |
|---|---|---|---|
| **Nama Dompet** | Title | e.g. `BCA Utama`, `Jago Pocket – Dana Darurat` | Wallet/pocket identifier |
| **Tipe Dompet** | Select | `Rekening Bank` · `E-Wallet` · `Pocket` · `Tunai` · `Emas/Investasi` | Classify container type |
| **Provider** | Select | `BCA` · `Bank Jago` · `GoPay` · `ShopeePay` · `DANA` · `OVO` · `Tunai` | Institution / issuer |
| **Saldo Awal** | Number | Format: Number (IDR baseline) | Opening balance the math builds from |
| **Transaksi** | Relation | → *Monthly Transaction Ledger* (two-way, shows as `Dompet` on Ledger) | Links all txns to this wallet |
| **Total Pemasukan** | Rollup | Relation `Transaksi` · Property `Nominal` · **Filter** `Tipe = Pemasukan` · Calc **Sum** | Money in |
| **Total Pengeluaran** | Rollup | Relation `Transaksi` · Property `Nominal` · **Filter** `Tipe = Pengeluaran` · Calc **Sum** | Money out |
| **Saldo Mentah** | Formula | `prop("Saldo Awal") + prop("Total Pemasukan") - prop("Total Pengeluaran")` | Raw number — used for sorting / net-worth rollups |
| **Sisa Saldo (IDR)** | Formula | **Formula #2** (below) | Display balance, formatted `IDR 5.000.000` |
| **Status** | Select | `Aktif` · `Arsip` | Filter dormant wallets out of views |
| **Ikon / Warna** | Select (or page icon) | Emoji per wallet | Visual scanning in board/gallery views |

> Keep both `Saldo Mentah` (number, for aggregation) and `Sisa Saldo (IDR)` (text, for display). Notion can't sum a formatted-text balance, so the numeric twin powers any net-worth rollup.

---

## 2. Allocation & Expense Categories DB — *Alokasi & Kategori*

The budgeting brain. Holds the specialized buckets and all monthly targets vs. actuals.

| Property Name | Property Type | Configuration / Relation Details | Purpose |
|---|---|---|---|
| **Nama Kategori** | Title | e.g. `Dana Orang Tua`, `Dana Anak`, `Listrik & Air` | Category identifier |
| **Bucket** | Select | `Fixed Expenses` · `Dana Orang Tua` · `Dana Anak` · `Lifestyle` · `Dana Darurat` · `Pemasukan` | Top-level specialized buckets |
| **Tipe Alokasi** | Select | `Kebutuhan` · `Keinginan` · `Tabungan/Investasi` · `Kewajiban Keluarga` | 50/30/20-style lens |
| **Beban Sandwich** | Checkbox | ✅ for `Dana Orang Tua` & `Dana Anak` | Flags rows that feed the Sandwich ratio |
| **Target Alokasi** | Number | Monthly budget ceiling (IDR) | Planned spend per bucket |
| **Transaksi** | Relation | → *Monthly Transaction Ledger* (two-way, shows as `Kategori` on Ledger) | Links txns to bucket |
| **Aktual Terpakai** | Rollup | Relation `Transaksi` · Property `Nominal` · **Filter** `Tipe = Pengeluaran` · Calc **Sum** | Actual spend this period |
| **Sisa Anggaran** | Formula | `prop("Target Alokasi") - prop("Aktual Terpakai")` | Budget remaining |
| **Progress Alokasi** | Formula | **Formula #3** (below) | Visual progress bar |
| **Total Pemasukan Bulanan** | Rollup | *(see Architect's Note)* total income for the active month | Denominator for burden ratio |
| **Dana Sandwich Gabungan** | Rollup / Number | *(see Architect's Note)* `Dana Orang Tua` actual + `Dana Anak` actual | Numerator for burden ratio |
| **Sandwich Burden Ratio** | Formula | **Formula #1** (below) | KPI with visual warning |

---

## 3. Monthly Transaction Ledger DB — *Buku Transaksi Bulanan*

The **single point of data entry.** Optimize this for speed: a saved template/button per common transaction kills friction.

| Property Name | Property Type | Configuration / Relation Details | Purpose |
|---|---|---|---|
| **Deskripsi** | Title | e.g. `Belanja Indomaret`, `Gaji Juni` | What the transaction was |
| **Tanggal** | Date | Default = today | When it happened |
| **Tipe** | Select | `Pemasukan` · `Pengeluaran` · `Transfer` | Direction of money |
| **Nominal** | Number | Always **positive** (sign handled by formula) | Amount, low-friction entry |
| **Dompet** | Relation | → *Multi-Wallet & Pockets* (single-select behavior) | Which wallet moved |
| **Kategori** | Relation | → *Allocation & Expense Categories* (single-select) | Which bucket it hits |
| **Bulan** | Formula | `formatDate(prop("Tanggal"), "MMMM YYYY")` | Group/filter views by month |
| **Nominal Bersih** | Formula | `if(prop("Tipe") == "Pemasukan", prop("Nominal"), -prop("Nominal"))` | Signed value for net rollups |
| **Metode** | Select | `QRIS` · `Transfer` · `Tunai` · `Auto-debit` | Optional analytics/visualization |
| **Recurring?** | Checkbox | flag fixed monthly items | Drives recurring-entry buttons |

> **Friction killer:** Build Ledger *buttons* ("➕ Pengeluaran QRIS", "➕ Gaji") that pre-fill `Tipe`, `Kategori`, and `Metode`. The user touches only `Nominal` and `Dompet`.

---

## 4. Local Investment Tracker DB — *Investasi Lokal*

Manual portfolio for platforms without API access. Update `Harga Sekarang` periodically; everything else computes.

| Property Name | Property Type | Configuration / Relation Details | Purpose |
|---|---|---|---|
| **Nama Aset** | Title | e.g. `Reksadana Pasar Uang`, `BBCA`, `Antam 5gr` | Asset name |
| **Platform** | Select | `Bibit` · `Stockbit` · `Ajaib` · `Pluang` · `Pegadaian (Emas)` · `Lainnya` | Where it's held |
| **Jenis Aset** | Select | `Reksadana` · `Saham` · `SBN/Obligasi` · `Emas` · `Kripto` | Asset class |
| **Modal Investasi** | Number | Total cost basis (IDR) | Capital invested |
| **Jumlah Unit/Lot/Gram** | Number | Quantity held | Holdings size |
| **Harga Sekarang** | Number | Manual per-unit current price | The one field the user updates |
| **Nilai Sekarang** | Formula | `prop("Jumlah Unit/Lot/Gram") * prop("Harga Sekarang")` | Current market value |
| **Untung/Rugi (IDR)** | Formula | `prop("Nilai Sekarang") - prop("Modal Investasi")` | Absolute P/L |
| **Return %** | Formula | `if(prop("Modal Investasi") == 0, 0, (prop("Nilai Sekarang") - prop("Modal Investasi")) / prop("Modal Investasi"))` · format as Percent | Percentage return |
| **Status P/L** | Formula | `if(prop("Untung/Rugi (IDR)") >= 0, "🟢 Profit", "🔴 Loss")` | At-a-glance health |
| **Dompet Sumber** | Relation | → *Multi-Wallet & Pockets* (optional) | Trace funding source |
| **Terakhir Update** | Date | Manual | Price freshness |

---

# CRITICAL FORMULAS — Notion Formulas 2.0

All three are verified against the iteration/string logic Notion 2.0 actually runs (`lets`, `map`, `split`, `repeat`, `%`).

### Formula #1 — `Sandwich Burden Ratio` *(Allocation & Expense Categories DB)*

Shows what % of monthly income is consumed by **Dana Orang Tua + Dana Anak**, with a red warning above the 30% safe threshold.

```notion
lets(
  beban,   prop("Dana Sandwich Gabungan"),
  income,  prop("Total Pemasukan Bulanan"),
  ratio,   if(income == 0, 0, beban / income),
  persen,  format(round(ratio * 100)),
  if(
    ratio > 0.3,
    "🔴 WASPADA — Beban Sandwich " + persen + "% dari pemasukan (di atas batas aman 30%)",
    "🟢 Aman — Beban Sandwich " + persen + "% dari pemasukan"
  )
)
```

**Verified output:** `Rp1.5jt / Rp5jt → 🟢 Aman 30%` · `Rp2jt / Rp5jt → 🔴 WASPADA 40%`.

> **Architect's Note (read this).** A single formula property computes **per row** — it can't natively sum two *sibling* rows (`Dana Orang Tua` + `Dana Anak`) or reach "total income" on its own. Two clean ways to feed `beban` and `income`:
> 1. **Recommended — place this KPI on the template Dashboard**, not on every category row (putting an identical global number on all rows is redundant). On the Dashboard, source `Dana Sandwich Gabungan` and `Total Pemasukan Bulanan` from **Ledger rollups filtered by `Bucket` and `Tipe`**.
> 2. **Stay inside this DB** by adding a one-row `📊 Ringkasan Bulanan` entry whose two number/rollup inputs aggregate the month, and run the formula there.
> Either way the formula code is unchanged — only where its two inputs come from differs.

---

### Formula #2 — `Sisa Saldo (IDR)` *(Multi-Wallet & Pockets DB)*

Live remaining balance = opening + income − expense, formatted as Indonesian Rupiah with `.` thousand separators.

```notion
lets(
  saldo,   prop("Saldo Awal") + prop("Total Pemasukan") - prop("Total Pengeluaran"),
  angka,   format(abs(round(saldo))),
  panjang, length(angka),
  ribuan,  map(
             split(angka, ""),
             if(and(index != 0, (panjang - index) % 3 == 0), "." + current, current)
           ).join(""),
  if(saldo < 0, "- IDR ", "IDR ") + ribuan
)
```

**Verified output:** `5000000 → IDR 5.000.000` · `12345678 → IDR 12.345.678` · `-2500000 → - IDR 2.500.000` · `0 → IDR 0`.

> Logic: convert the absolute balance to text, then walk each digit and prepend `.` wherever the distance from the right is a multiple of 3 (skipping position 0). Handles negatives and any magnitude.

---

### Formula #3 — `Progress Alokasi` *(Allocation & Expense Categories DB)*

Modern 10-segment progress bar toward the monthly target — ideal for **Dana Orang Tua** (works for any category). Color shifts green → yellow → red as the bucket fills.

```notion
lets(
  target,    prop("Target Alokasi"),
  aktual,    prop("Aktual Terpakai"),
  rasio,     if(target == 0, 0, aktual / target),
  kapasitas, min(rasio, 1),
  isi,       floor(kapasitas * 10),
  bar,       repeat("▓", isi) + repeat("░", 10 - isi),
  warna,     if(rasio >= 1, "🔴", if(rasio >= 0.8, "🟡", "🟢")),
  warna + " " + bar + " " + format(round(rasio * 100)) + "%"
)
```

**Verified output:**
`Rp1.4jt / Rp2jt → 🟢 ▓▓▓▓▓▓▓░░░ 70%` · `Rp1.7jt / Rp2jt → 🟡 ▓▓▓▓▓▓▓▓░░ 85%` · `Rp2jt / Rp2jt → 🔴 ▓▓▓▓▓▓▓▓▓▓ 100%` · `over budget → 🔴 ▓▓▓▓▓▓▓▓▓▓ 115%`.

> The bar caps visually at 10 blocks (`min(rasio,1)`) but the **percentage keeps counting past 100%**, so overspend stays loud and red.

---

## 5. Relation & Rollup Map (build order)

1. Build **Ledger** first (it's the hub). Add `Dompet` and `Kategori` relations — Notion auto-creates the two-way fields on the other DBs.
2. On **Wallets**, add the two filtered rollups (`Total Pemasukan`, `Total Pengeluaran`) → then Formula #2.
3. On **Categories**, add `Aktual Terpakai` rollup → then Formulas #3 and #1 (wire the two ratio inputs per the Architect's Note).
4. **Investments** stands alone; optional `Dompet Sumber` relation only if you want fund-source tracing.

| From | Relation | To | Rollups it powers |
|---|---|---|---|
| Ledger | `Dompet` | Wallets | Total Pemasukan, Total Pengeluaran |
| Ledger | `Kategori` | Categories | Aktual Terpakai, Dana Sandwich Gabungan |
| Investments | `Dompet Sumber` (opt.) | Wallets | — |

---

## 6. Recommended Views (max visualization, min effort)

- **Ledger:** default = current-month filter, grouped by `Tipe`; a "Quick Add" gallery of buttons.
- **Wallets:** Board grouped by `Tipe Dompet`, card shows `Sisa Saldo (IDR)`.
- **Categories:** Table grouped by `Bucket`, showing `Progress Alokasi` + `Sisa Anggaran`.
- **Dashboard page:** callouts for `Sandwich Burden Ratio`, total net worth (sum of `Saldo Mentah`), and total portfolio value (sum of `Nilai Sekarang`).

---

*Blueprint v1 · Generasi Sandwich Finance OS · Notion Template Dev workstation*
