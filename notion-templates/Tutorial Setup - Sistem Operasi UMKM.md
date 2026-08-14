# 🛠️ Tutorial Setup — Sistem Operasi UMKM & Solopreneur

**Panduan membangun template dari nol di Notion, langkah demi langkah.**
*Estimasi waktu: 45–60 menit. Tidak perlu skill teknis.*

> 📎 Semua **nama properti** & **kode rumus** mengikuti file `Blueprint - Sistem Operasi UMKM & Solopreneur.md`. Buka berdampingan saat mengerjakan — saat tutorial bilang *"tempel Rumus T-1"*, salin teksnya dari blueprint.

---

## 🎒 Persiapan Awal (5 menit)

1. Buka Notion → buat **halaman baru** kosong.
2. Beri judul: **🏪 Sistem Operasi Toko Saya**. Halaman ini = **Halaman Utama** (dashboard) sekaligus rumah semua database.
3. Urutan pembuatan penting: **Produk & HPP dulu** → lalu **Manajemen Stok** → lalu **Pencatatan Transaksi**. Alasannya: database terakhir mengambil data (relasi) dari yang pertama, jadi sumbernya harus ada lebih dulu.

---

## 📦 TAHAP 1 — Database "Produk & HPP" (10 menit)

### 1.1 Buat database
- Di halaman utama, ketik `/database` → pilih **Database - Full page** (atau Inline bila ingin tampil di halaman).
- Beri nama: **Produk & HPP**.

### 1.2 Susun properti
Kolom pertama `Name` ganti jadi **Nama Produk** (tipe Title sudah otomatis). Lalu tambah properti dengan klik `+` di header tabel. Ikuti tabel di blueprint **Database 1**:

| Tambah properti | Tipe | Catatan setup |
|---|---|---|
| Kode / SKU | Text | — |
| Foto Produk | Files & media | — |
| Kategori | Select | Tambah opsi: Makanan, Minuman, Fashion, Kerajinan, Jasa, Lainnya |
| HPP (Modal) | Number | Edit property → **Number format → Rupiah** |
| Target Harga Jual | Number | Number format → **Rupiah** |

> ⏸️ **Tunda dulu:** properti `Margin Kotor`, `Untung per Unit`, `Status Margin` (Formula), dan relasi `Stok Terkait` / `Riwayat Penjualan`. Kita isi setelah database lain jadi (Tahap 4 & 5).

### 1.3 Isi 2 produk contoh
Tambah 2 baris, mis. "Keripik Pisang 250gr" (HPP 8.000, Target 15.000) dan "Kopi Sachet" (HPP 2.500, Target 5.000). Ini untuk uji rumus nanti.

---

## 📊 TAHAP 2 — Database "Manajemen Stok" (10 menit)

### 2.1 Buat database
- Kembali ke halaman utama → `/database` → **Database - Full page** → nama **Manajemen Stok**.

### 2.2 Susun properti
Ganti Title jadi **Nama Item**, lalu tambah sesuai blueprint **Database 3**:

| Tambah properti | Tipe | Catatan setup |
|---|---|---|
| Jenis Item | Select | Opsi: Bahan Baku, Barang Jadi, Kemasan |
| Stok Saat Ini | Number | Default 0 |
| Satuan | Select | Opsi: Pcs, Kg, Gram, Liter, Lusin, Box |
| Batas Aman (Min) | Number | — |
| HPP Item | Number | Number format → **Rupiah** (dipakai Rumus S-3) |
| Supplier | Text | — |
| Terakhir Diperbarui | Last edited time | — |

> ⏸️ **Tunda:** Formula `Status Stok`, `Perlu Restock?`, `Estimasi Nilai Stok`, dan relasi `Produk Terkait`. → Tahap 4 & 5.

### 2.3 Isi 2–3 item contoh
Mis. "Tepung Terigu" (Stok 3, Batas Aman 5 → harusnya muncul peringatan) dan "Gula Pasir" (Stok 20, Batas Aman 5 → aman).

---

## 🧾 TAHAP 3 — Database "Pencatatan Transaksi" (10 menit)

### 3.1 Buat database
- Halaman utama → `/database` → **Database - Full page** → nama **Pencatatan Transaksi**.

### 3.2 Susun properti dasar
Ganti Title jadi **Nama Transaksi**, lalu tambah sesuai blueprint **Database 2** (kecuali formula & rollup):

| Tambah properti | Tipe | Catatan setup |
|---|---|---|
| Tanggal | Date | Aktifkan opsi default **Now** bila ada |
| Jenis | Select | Opsi: 🟢 Pemasukan, 🔴 Pengeluaran |
| Jumlah (Qty) | Number | Default 1 |
| Harga Jual | Number | Number format → **Rupiah** |
| Channel Penjualan | Select | Opsi: Shopee, TikTok Shop, Tokopedia, WhatsApp / Toko Sendiri |
| Promo Ekstra Aktif | Checkbox | — |
| Pakai Payment Gateway | Checkbox | — |
| Biaya Iklan/Ongkir Tambahan | Number | Number format → **Rupiah** |

> ⏸️ **Tunda:** relasi `Produk`, rollup `HPP`, dan 3 Formula (`Potongan Komisi`, `Keuntungan Bersih`, `Status Untung`).

---

## 🔗 TAHAP 4 — Pasang Relasi & Rollup (8 menit)

Relasi menghubungkan database supaya tidak perlu ketik HPP berulang.

### 4.1 Relasi Transaksi → Produk
1. Di **Pencatatan Transaksi**, tambah properti `+` → tipe **Relation**.
2. Beri nama **Produk** → pilih database **Produk & HPP**.
3. (Opsional) aktifkan "Show on Produk & HPP" agar muncul balik sebagai **Riwayat Penjualan** di sisi produk.
4. Set **Limit → 1 page** agar satu transaksi = satu produk.

### 4.2 Rollup HPP di Transaksi
1. Tambah properti → tipe **Rollup**, beri nama **HPP**.
2. **Relation:** `Produk` → **Property:** `HPP (Modal)` → **Calculate:** `Sum`.
3. Hasil: begitu produk dipilih, kolom HPP terisi otomatis. ✅

### 4.3 Relasi Stok → Produk
1. Di **Manajemen Stok**, tambah properti → **Relation** → nama **Produk Terkait** → database **Produk & HPP**.
2. Aktifkan show-back agar muncul sebagai **Stok Terkait** di Produk & HPP.

---

## 🧮 TAHAP 5 — Tempel Semua Rumus (10 menit)

Untuk tiap formula: tambah properti `+` → tipe **Formula** → klik kolomnya → **Edit formula** → tempel kode dari blueprint → **Done**.

> ⚠️ **Aturan emas:** nama di dalam `prop("...")` harus **sama persis** dengan nama kolom Anda (huruf besar/kecil & spasi). Kalau beda, perbaiki nama di rumus atau di kolom.

### 5.1 Di Produk & HPP
| Nama Formula | Sumber kode | Format hasil |
|---|---|---|
| Margin Kotor (%) | Rumus **P-1** | set kolom → **Percent** |
| Untung per Unit | Rumus **P-2** | (sudah teks "Rp …") |
| Status Margin | Rumus **P-3** | — |

### 5.2 Di Manajemen Stok
| Nama Formula | Sumber kode | Catatan |
|---|---|---|
| Status Stok | Rumus **S-1** | badge 🟢🟡🔴 |
| Perlu Restock? | Rumus **S-2** | hasil true/false → dipakai filter dashboard |
| Estimasi Nilai Stok | Rumus **S-3** (versi `HPP Item`) | — |

### 5.3 Di Pencatatan Transaksi
| Nama Formula | Sumber kode | Catatan |
|---|---|---|
| Potongan Komisi Marketplace | Rumus **T-1** | tergantung Channel + checkbox promo |
| Keuntungan Bersih (IDR) | Rumus **T-2** | output "Rp …" rapi |
| Status Untung | Rumus **T-3** | badge 🟢🟡🔴 |

> 🧪 **Cek cepat:** isi 1 transaksi (Produk = Keripik Pisang, Harga 15.000, Qty 1, Channel = Shopee). `Potongan Komisi` harus = **Rp 1.350** (9%), `Keuntungan Bersih` = **Rp 5.650**. Centang "Promo Ekstra" → komisi naik jadi **Rp 1.650** (11%).

---

## 🏠 TAHAP 6 — Bangun Halaman Utama (Dashboard) (10 menit)

Kembali ke halaman **🏪 Sistem Operasi Toko Saya**. Ikuti peta layout di blueprint bagian **Halaman Utama**.

### 6.1 Callout sapaan (paling atas)
- Ketik `/callout` → tulis: *"Selamat datang! Kelola toko Anda dengan mudah."* Pilih ikon 🏪.

### 6.2 ⚡ Tombol Cepat (3 Button sejajar)
1. Ketik `/button` → **Edit**.
2. Tombol 1 **➕ Catat Pemasukan**: Add step → **Add page to** → `Pencatatan Transaksi` → **Edit property values** → set `Jenis = 🟢 Pemasukan`, `Tanggal = Now` → tambah step **Open page**.
3. Ulangi untuk **➖ Catat Pengeluaran** (`Jenis = 🔴 Pengeluaran`) dan **📦 Tambah Stok Baru** (Add page to `Manajemen Stok`, `Jenis Item = Bahan Baku`).
4. **Susun sejajar:** seret tombol 2 ke kanan tombol 1 hingga muncul garis biru vertikal → jadi 3 kolom. Di HP otomatis menumpuk rapi.

### 6.3 💚 Kesehatan Finansial Hari Ini
1. Ketik `/linked` → **Create linked database** → pilih `Pencatatan Transaksi`.
2. Buat **3 view** (atau 3 linked view sejajar):
   - **Pemasukan Hari Ini** — Filter `Jenis = 🟢 Pemasukan` **dan** `Tanggal → is → Today`. Di footer kolom `Harga Jual` pilih **Sum**.
   - **Pengeluaran Hari Ini** — Filter `Jenis = 🔴 Pengeluaran` **dan** `Tanggal = Today` → **Sum** `Harga Jual`.
   - **Laba Bersih Hari Ini** — Filter `Tanggal = Today` → **Sum** kolom `Keuntungan Bersih`.
3. Sembunyikan properti yang tidak perlu (Properties → toggle off) agar tampak seperti widget bersih.

### 6.4 ⚠️ Peringatan Stok Tipis (toggle otomatis)
1. Ketik `/toggle` → judul **⚠️ Peringatan Stok Tipis**.
2. Di dalam toggle: `/linked` → pilih `Manajemen Stok`.
3. **Filter:** `Perlu Restock? → is → ✅ (checked/true)`.
4. **Sort:** `Stok Saat Ini` → Ascending.
5. **Properties:** tampilkan hanya `Nama Item`, `Stok Saat Ini`, `Satuan`, `Status Stok`.
6. Biarkan toggle **tertutup** secara default → layout tetap bersih, isi muncul hanya saat diklik.

### 6.5 📂 Navigasi database
Di bawah, ketik `/link` → buat link ke ketiga database (Produk & HPP, Transaksi, Stok) agar mudah dibuka penuh.

---

## ✅ TAHAP 7 — Uji & Finishing (5 menit)

1. **Tes alur lengkap:** klik **➕ Catat Pemasukan** → form terbuka → pilih produk, isi harga & channel → simpan. Cek angka `Keuntungan Bersih`.
2. **Tes peringatan stok:** ubah satu item jadi di bawah Batas Aman → pastikan muncul di toggle peringatan.
3. **Rapikan:** hapus data contoh bila template mau dijual/dibagikan, sisakan 1 contoh per database sebagai panduan.
4. **Kunci tampilan:** sembunyikan kolom teknis (rollup, formula pembantu) dari view utama agar bersih untuk pengguna awam.

---

## 🧯 Solusi Masalah Umum

| Gejala | Penyebab & Solusi |
|---|---|
| Formula error "Property not found" | Nama di `prop("...")` ≠ nama kolom. Samakan persis. |
| HPP tidak muncul di transaksi | Rollup belum nunjuk relasi `Produk` / property `HPP (Modal)`. Cek Tahap 4.2. |
| Komisi salah hitung | Pastikan opsi `Channel Penjualan` ditulis identik ("TikTok Shop", bukan "Tiktok"). |
| Rupiah tampil tanpa titik | Pastikan rumus pakai `replaceAll(... "\B(?=(\d{3})+(?!\d))", ".")` utuh. |
| Toggle stok kosong padahal stok sedikit | `Batas Aman (Min)` belum diisi (kosong = 0). Isi angkanya. |

---

*Selesai. Setelah Tahap 7, semua perhitungan berjalan otomatis. Tombol & rumus hanya dipasang sekali — pemakaian harian cukup 1 klik.*
