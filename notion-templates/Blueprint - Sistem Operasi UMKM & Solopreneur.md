# 🏪 Sistem Operasi UMKM & Solopreneur

**Cetak Biru Arsitektur Template Notion Premium**
*Dashboard operasional all-in-one untuk pemilik toko online & pengusaha mikro Indonesia*

> **Dua Pilar Desain:**
> 1. **Kemudahan Penggunaan** — input data minim, navigasi tombol jelas, layout bersih, nol kerumitan visual.
> 2. **100% Bahasa Indonesia** — semua nama properti, badge status, dan instruksi memakai istilah bisnis yang mudah dipahami pedagang tradisional.

---

## 🗺️ Peta Arsitektur Sistem

```
                 ┌─────────────────────────────┐
                 │     🏠 HALAMAN UTAMA        │
                 │   (Dashboard / Pusat Kendali)│
                 └──────────────┬──────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                        │
        ▼                       ▼                        ▼
┌───────────────┐      ┌─────────────────┐      ┌─────────────────┐
│ 📦 PRODUK &   │◄────►│ 🧾 PENCATATAN   │      │ 📊 MANAJEMEN    │
│    HPP        │ relasi│   TRANSAKSI    │ relasi│    STOK         │
│ (Master Data) │      │  (Buku Kas)     │◄────►│  (Gudang)       │
└───────────────┘      └─────────────────┘      └─────────────────┘
   Sumber HPP &           Hitung untung           Pantau stok tipis
   harga jual             otomatis per nota        & isi ulang
```

**Logika hubungan antar-database:**
- **Produk & HPP** adalah *master data*. Database lain mengambil angka HPP & harga dari sini (tidak perlu ketik ulang).
- **Pencatatan Transaksi** menarik HPP via *Relasi + Rollup*, lalu menghitung komisi & laba bersih otomatis.
- **Manajemen Stok** terhubung ke Produk untuk memantau sisa barang dan memicu peringatan stok tipis.

---

## 📦 Database 1 — Produk & HPP

> **Fungsi:** Katalog produk internal, modal pokok (HPP), dan target harga jual. Ini "kamus harga" untuk seluruh sistem.

| Nama Properti | Jenis Properti (Notion Type) | Konfigurasi / Rumus | Tujuan Fitur |
|---|---|---|---|
| **Nama Produk** | Title | — | Nama barang (mis. "Keripik Pisang 250gr") |
| **Kode / SKU** | Text | — | Kode unik produk untuk pencarian cepat |
| **Foto Produk** | Files & media | — | Visual katalog agar mudah dikenali |
| **Kategori** | Select | Opsi: `Makanan`, `Minuman`, `Fashion`, `Kerajinan`, `Jasa`, `Lainnya` | Pengelompokan & filter |
| **HPP (Modal)** | Number | Format: `Rupiah` (Number format → Rupiah) | Harga Pokok Penjualan per unit |
| **Target Harga Jual** | Number | Format: `Rupiah` | Harga jual ideal yang dipasang |
| **Margin Kotor (%)** | Formula | Format hasil: `Percent` — lihat **Rumus P-1** | Persentase untung kotor per produk |
| **Untung per Unit** | Formula | Lihat **Rumus P-2** (format Rupiah) | Selisih harga jual − HPP dalam Rupiah |
| **Status Margin** | Formula | Lihat **Rumus P-3** | Badge cepat: margin sehat / tipis |
| **Stok Terkait** | Relation → *Manajemen Stok* | — | Menghubungkan ke kartu stok barang |
| **Riwayat Penjualan** | Relation → *Pencatatan Transaksi* | — | Melihat semua nota produk ini |
| **Catatan** | Text | — | Catatan supplier / varian / dll |

### Rumus P-1 — Margin Kotor (%)
```javascript
if(
  prop("Target Harga Jual") > 0,
  (prop("Target Harga Jual") - prop("HPP (Modal)")) / prop("Target Harga Jual"),
  0
)
```
*Set format kolom ke **Percent**. Hasil otomatis jadi mis. 45%.*

### Rumus P-2 — Untung per Unit (Rupiah)
```javascript
lets(
  untung, prop("Target Harga Jual") - prop("HPP (Modal)"),
  tanda, if(untung < 0, "-", ""),
  angka, replaceAll(format(abs(round(untung))), "\B(?=(\d{3})+(?!\d))", "."),
  tanda + "Rp " + angka
)
```

### Rumus P-3 — Status Margin (Badge Cepat)
```javascript
ifs(
  prop("Margin Kotor (%)") >= 0.4, "🟢 Margin Sehat",
  prop("Margin Kotor (%)") >= 0.2, "🟡 Margin Tipis",
  prop("Margin Kotor (%)") > 0,   "🟠 Margin Mepet",
  "🔴 Rugi / Cek Harga"
)
```

---

## 🧾 Database 2 — Pencatatan Transaksi

> **Fungsi:** Tempat pedagang mencatat **Pemasukan** & **Pengeluaran** harian secepat mungkin. Inti dari template — semua perhitungan untung terjadi di sini.

| Nama Properti | Jenis Properti (Notion Type) | Konfigurasi / Rumus | Tujuan Fitur |
|---|---|---|---|
| **Nama Transaksi** | Title | — | Label nota (mis. "Penjualan 15 Jun - Bu Sari") |
| **Tanggal** | Date | Default: `Now` / `Today` | Kapan transaksi terjadi |
| **Jenis** | Select | Opsi: `🟢 Pemasukan`, `🔴 Pengeluaran` | Pisahkan uang masuk vs keluar |
| **Produk** | Relation → *Produk & HPP* | Limit 1 (single relation) | Pilih barang yang dijual (auto tarik HPP) |
| **HPP** | Rollup | Relation: `Produk` → Property: `HPP (Modal)` → Calculate: `Sum` | Modal otomatis dari master, tanpa ketik ulang |
| **Jumlah (Qty)** | Number | Default: `1` | Banyak unit terjual |
| **Harga Jual** | Number | Format: `Rupiah` | Harga jual aktual (bisa beda dari target) |
| **Channel Penjualan** | Select | Opsi: `Shopee`, `TikTok Shop`, `Tokopedia`, `WhatsApp / Toko Sendiri` | Penentu potongan komisi marketplace |
| **Promo Ekstra Aktif** | Checkbox | — | Centang bila ikut program promo (+2% Shopee/TikTok) |
| **Pakai Payment Gateway** | Checkbox | — | Centang bila bayar via QRIS/PG (2,5% utk Toko Sendiri) |
| **Biaya Iklan/Ongkir Tambahan** | Number | Format: `Rupiah` | Biaya ads, ongkir nombok, packing, dll |
| **Potongan Komisi Marketplace** | Formula | Lihat **Rumus T-1** | Hitung potongan platform otomatis (tarif 2026) |
| **Keuntungan Bersih (IDR)** | Formula | Lihat **Rumus T-2** | Laba bersih final, format Rupiah rapi |
| **Status Untung** | Formula | Lihat **Rumus T-3** | Badge cepat untung / rugi |

> 💡 **Catatan input cepat:** Pedagang cukup isi 4 hal → **Produk**, **Harga Jual**, **Channel**, **Qty**. Sisanya (HPP, komisi, laba bersih) terisi otomatis.

### Rumus T-1 — Potongan Komisi Marketplace ⭐
> Tarif marketplace 2026: Shopee & TikTok Shop naik ke **9%** admin dasar (+2% opsional promo), Tokopedia **8%** + biaya proses pesanan **Rp1.250**/transaksi, Toko Sendiri **0%** (atau 2,5% bila pakai payment gateway).

```javascript
lets(
  dasar, prop("Harga Jual") * prop("Jumlah (Qty)"),
  komisi, ifs(
    or(prop("Channel Penjualan") == "Shopee", prop("Channel Penjualan") == "TikTok Shop"),
      dasar * (0.09 + if(prop("Promo Ekstra Aktif"), 0.02, 0)),
    prop("Channel Penjualan") == "Tokopedia",
      dasar * 0.08 + 1250,
    prop("Channel Penjualan") == "WhatsApp / Toko Sendiri",
      if(prop("Pakai Payment Gateway"), dasar * 0.025, 0),
    0
  ),
  round(komisi)
)
```

**Rincian logika tarif:**

| Channel | Admin Dasar | Tambahan | Total Potongan |
|---|---|---|---|
| Shopee | 9% | +2% bila Promo Ekstra dicentang | 9% atau 11% |
| TikTok Shop | 9% | +2% bila Promo Ekstra dicentang | 9% atau 11% |
| Tokopedia | 8% | + Rp1.250 flat per transaksi | 8% + Rp1.250 |
| WhatsApp / Toko Sendiri | 0% | 2,5% bila Pakai Payment Gateway | 0% atau 2,5% |

### Rumus T-2 — Keuntungan Bersih (IDR) ⭐
> Rumus: **[Harga Jual × Qty] − [HPP × Qty] − [Potongan Komisi] − [Biaya Iklan/Ongkir]**, tampil rapi format Rupiah (mis. `Rp 45.000`).

```javascript
lets(
  omzet, prop("Harga Jual") * prop("Jumlah (Qty)"),
  modal, prop("HPP") * prop("Jumlah (Qty)"),
  bersih, omzet - modal - prop("Potongan Komisi Marketplace") - prop("Biaya Iklan/Ongkir Tambahan"),
  tanda, if(bersih < 0, "-", ""),
  angka, replaceAll(format(abs(round(bersih))), "\B(?=(\d{3})+(?!\d))", "."),
  tanda + "Rp " + angka
)
```

> 🔎 **Cara kerja format Rupiah:** `replaceAll(... "\B(?=(\d{3})+(?!\d))", ".")` menyisipkan titik setiap 3 digit dari belakang sehingga `45000` → `45.000`. Tanda minus otomatis muncul di depan bila rugi (mis. `-Rp 12.500`).

### Rumus T-3 — Status Untung (Badge Cepat)
```javascript
lets(
  omzet, prop("Harga Jual") * prop("Jumlah (Qty)"),
  modal, prop("HPP") * prop("Jumlah (Qty)"),
  bersih, omzet - modal - prop("Potongan Komisi Marketplace") - prop("Biaya Iklan/Ongkir Tambahan"),
  ifs(
    prop("Jenis") == "🔴 Pengeluaran", "⚪ Biaya",
    bersih > 0, "🟢 Untung",
    bersih == 0, "🟡 Balik Modal",
    "🔴 Rugi"
  )
)
```

---

## 📊 Database 3 — Manajemen Stok

> **Fungsi:** Memantau sisa stok bahan baku (raw) dan barang jadi (finished). Memicu **Peringatan Stok Tipis** otomatis untuk dashboard.

| Nama Properti | Jenis Properti (Notion Type) | Konfigurasi / Rumus | Tujuan Fitur |
|---|---|---|---|
| **Nama Item** | Title | — | Nama bahan/barang (mis. "Tepung Terigu") |
| **Jenis Item** | Select | Opsi: `Bahan Baku`, `Barang Jadi`, `Kemasan` | Bedakan raw material vs produk siap jual |
| **Produk Terkait** | Relation → *Produk & HPP* | — | Hubungkan ke produk yang memakai item ini |
| **Stok Saat Ini** | Number | Default: `0` | Jumlah sisa stok fisik |
| **Satuan** | Select | Opsi: `Pcs`, `Kg`, `Gram`, `Liter`, `Lusin`, `Box` | Satuan hitung agar tidak salah |
| **Batas Aman (Min)** | Number | — | Ambang minimum sebelum harus restock |
| **Status Stok** | Formula | Lihat **Rumus S-1** | Badge otomatis: Aman / Menipis / Habis |
| **Perlu Restock?** | Formula | Lihat **Rumus S-2** | Checkbox logika untuk filter dashboard |
| **Estimasi Nilai Stok** | Formula | Lihat **Rumus S-3** (format Rupiah) | Nilai modal yang "tertahan" di gudang |
| **Supplier** | Text | — | Sumber pembelian ulang |
| **Terakhir Diperbarui** | Last edited time | — | Audit kapan stok terakhir dicek |

### Rumus S-1 — Status Stok (Badge Otomatis) ⭐
```javascript
ifs(
  prop("Stok Saat Ini") <= 0, "🔴 Habis",
  prop("Stok Saat Ini") <= prop("Batas Aman (Min)"), "🟡 Menipis",
  "🟢 Aman"
)
```

### Rumus S-2 — Perlu Restock? (Pemicu Peringatan)
```javascript
prop("Stok Saat Ini") <= prop("Batas Aman (Min)")
```
*Hasil `true`/`false`. Inilah filter yang dipakai toggle "Peringatan Stok Tipis" di dashboard.*

### Rumus S-3 — Estimasi Nilai Stok (Rupiah)
> **Disarankan (paling ramah pemula):** tambah satu kolom **Number** bernama `HPP Item` (format Rupiah), isi modal per unit, lalu pakai rumus berikut:
```javascript
lets(
  nilai, prop("Stok Saat Ini") * prop("HPP Item"),
  "Rp " + replaceAll(format(round(nilai)), "\B(?=(\d{3})+(?!\d))", ".")
)
```
> **Alternatif via Relasi (tanpa kolom baru):** buat **Rollup** bernama `HPP dari Produk` (Relation `Produk Terkait` → Property `HPP (Modal)` → Calculate `Sum`), lalu ganti `prop("HPP Item")` di rumus atas dengan `prop("HPP dari Produk")`. *Hindari mengakses properti database lain langsung di dalam formula — Notion 2.0 mewajibkan lewat Rollup.*

---

## 🏠 Halaman Utama (Dashboard) — Tata Letak UX

> Prinsip: begitu dibuka di **HP atau laptop**, pedagang langsung melihat 3 hal penting tanpa scroll panjang. Bersih, tombol besar, nol kebingungan.

### Peta Visual Layout (atas → bawah)

```
╔══════════════════════════════════════════════════╗
║   🏪  SISTEM OPERASI TOKO SAYA                    ║   ← Judul + tanggal hari ini
║   Selamat datang! Hari ini: Senin, 15 Juni 2026   ║      (callout sapaan)
╠══════════════════════════════════════════════════╣
║                                                    ║
║   ⚡ TOMBOL CEPAT                                  ║   ← Baris Notion Buttons
║  ┌────────────┐ ┌────────────┐ ┌──────────────┐  ║      (3 kolom, 1 klik)
║  │ ➕ Catat   │ │ ➖ Catat   │ │ 📦 Tambah    │  ║
║  │  Pemasukan │ │ Pengeluaran│ │   Stok Baru  │  ║
║  └────────────┘ └────────────┘ └──────────────┘  ║
║                                                    ║
╠══════════════════════════════════════════════════╣
║   💚 KESEHATAN FINANSIAL HARI INI                 ║   ← 3 kartu metrik
║  ┌──────────────┬──────────────┬───────────────┐ ║      (linked DB +
║  │ Pemasukan    │ Pengeluaran  │ Laba Bersih   │ ║       rollup Sum)
║  │  Rp 850.000  │  Rp 320.000  │  Rp 530.000 🟢│ ║
║  └──────────────┴──────────────┴───────────────┘ ║
╠══════════════════════════════════════════════════╣
║   ⚠️ ▸ Peringatan Stok Tipis  (3 item) [Toggle]  ║   ← Toggle tertutup;
║       └ hanya muncul item yang perlu restock      ║      isi = linked view
╠══════════════════════════════════════════════════╣
║   📂 Buka Database Lengkap                        ║   ← Link navigasi
║   📦 Produk & HPP   🧾 Transaksi   📊 Stok        ║
╚══════════════════════════════════════════════════╝
```

### Komponen 1 — ⚡ Tombol Cepat (Notion Buttons)

Pakai blok **Button** Notion, susun dalam **3 kolom** agar muat di layar HP. Setiap tombol = 1 klik langsung buat entri baru.

| Tombol | Aksi Button | Pre-isi Otomatis |
|---|---|---|
| **➕ Catat Pemasukan** | *Add page to* → `Pencatatan Transaksi` | `Jenis = 🟢 Pemasukan`, `Tanggal = Now`, lalu **Open page** |
| **➖ Catat Pengeluaran** | *Add page to* → `Pencatatan Transaksi` | `Jenis = 🔴 Pengeluaran`, `Tanggal = Now`, lalu **Open page** |
| **📦 Tambah Stok Baru** | *Add page to* → `Manajemen Stok` | `Jenis Item = Bahan Baku`, lalu **Open page** |

> **Setup Button (manual di Notion):** klik `+` → `Button` → **Edit** → *Add step* → **Add page to** → pilih database → **Edit property values** untuk mengisi default → tambah step **Open page** agar form langsung terbuka. *(Button & isian default ini tidak bisa dibuat via API — wajib disusun manual sekali.)*

### Komponen 2 — 💚 Kesehatan Finansial Hari Ini

Tiga kartu ringkas dari **Linked view** database `Pencatatan Transaksi`:

- **Pemasukan Hari Ini** — Linked view, filter `Jenis = 🟢 Pemasukan` **AND** `Tanggal = Today` → kalkulasi kolom `Harga Jual` = **Sum**.
- **Pengeluaran Hari Ini** — filter `Jenis = 🔴 Pengeluaran` **AND** `Tanggal = Today` → **Sum**.
- **Laba Bersih Hari Ini** — filter `Tanggal = Today` → kalkulasi `Keuntungan Bersih` = **Sum**, badge 🟢/🔴 dari hasil.

> 💡 Sembunyikan semua properti kecuali angka utama. Gunakan tampilan **Board** atau **Table** ringkas, atau callout berwarna agar mirip "widget".

### Komponen 3 — ⚠️ Peringatan Stok Tipis (Toggle Otomatis)

Sebuah **Toggle block** (default tertutup agar layout bersih) berisi **Linked view** dari `Manajemen Stok`:

- **Filter:** `Perlu Restock? = ✅ (true)` — otomatis dari **Rumus S-2**.
- **Hasil:** hanya item dengan `Stok Saat Ini ≤ Batas Aman` yang muncul. Bila semua aman → toggle kosong (tidak ada yang perlu dilihat).
- **Tampilan:** kolom yang ditampilkan cukup `Nama Item`, `Stok Saat Ini`, `Satuan`, `Status Stok`. Urutkan (Sort) `Stok Saat Ini` **ascending** agar yang paling kritis di atas.

> Inilah inti "minimalist UX": pedagang tidak melihat daftar stok penuh — hanya notifikasi yang benar-benar butuh tindakan.

---

## 🚀 Urutan Pemasangan (Workflow Setup)

1. **Buat 3 database** sesuai tabel properti di atas (mulai dari *Produk & HPP* karena jadi sumber relasi).
2. **Pasang Relasi** Transaksi→Produk dan Stok→Produk, lalu tambahkan **Rollup HPP** di Transaksi.
3. **Tempel rumus** (P-1…P-3, T-1…T-3, S-1…S-3) ke kolom Formula masing-masing. *Pastikan nama properti di rumus sama persis dengan nama kolom Anda.*
4. **Set format Rupiah/Percent** pada kolom Number & Formula terkait.
5. **Bangun Halaman Utama**: tambah Buttons → linked views → toggle stok tipis.
6. **Isi 2-3 data contoh** untuk menguji apakah komisi & laba bersih sudah benar.

> ⚠️ **Catatan teknis:** Kolom **Formula** dan **Button** tidak dapat dibuat lewat Notion API/MCP — semua rumus & tombol di atas dirancang untuk **copy-paste manual** sekali pasang. Setelah terpasang, semua perhitungan berjalan otomatis selamanya.

---

## ✅ Checklist Kualitas (Dua Pilar)

**Kemudahan Penggunaan**
- [ ] Input transaksi cukup 4 isian (Produk, Harga, Channel, Qty)
- [ ] Tombol cepat 1 klik di paling atas dashboard
- [ ] Stok tipis tersembunyi di toggle sampai benar-benar perlu
- [ ] Tidak ada kolom teknis yang membingungkan di tampilan utama

**100% Bahasa Indonesia**
- [ ] Semua nama properti, opsi select, dan badge berbahasa Indonesia
- [ ] Istilah bisnis familiar (Pemasukan, Pengeluaran, HPP, Stok)
- [ ] Instruksi & label tombol mudah dipahami pedagang non-teknis

---

*Cetak biru ini siap dijadikan template Notion. Semua rumus memakai sintaks Notion Formula 2.0 (`lets`, `ifs`, `prop`).*
