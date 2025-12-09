# Modul Analisis Logistik - Dokumentasi Sistem

## Latar Belakang

Dalam dunia logistik dan transportasi, efisiensi penugasan armada kendaraan sangat menentukan keberhasilan operasional. Proses manual dalam menentukan penugasan unit kendaraan ke rute dan jadwal tertentu seringkali memakan waktu, rentan terhadap kesalahan, dan tidak optimal dalam penggunaan sumber daya. 

Dengan meningkatnya kompleksitas jaringan transportasi dan permintaan layanan yang semakin bervariasi, dibutuhkan solusi otomatisasi yang mampu:
- Mengoptimalkan alokasi unit kendaraan
- Meminimalkan biaya operasional
- Memaksimalkan cakupan layanan
- Memastikan efisiensi penggunaan sumber daya

Modul Analisis Logistik ini hadir sebagai solusi berbasis teknologi informasi untuk menangani permasalahan kompleks dalam pengelolaan armada transportasi.

## Tujuan Sistem

Sistem ini bertujuan untuk:

1. **Meningkatkan Efisiensi Operasional**: Mengoptimalkan penugasan unit kendaraan ke jadwal dan rute tertentu berdasarkan berbagai parameter operasional.

2. **Optimasi Biaya**: Meminimalkan biaya operasional termasuk biaya bahan bakar, waktu operasional, dan pemeliharaan armada.

3. **Peningkatan Kualitas Layanan**: Memaksimalkan cakupan layanan dan memastikan ketersediaan unit untuk setiap rute yang dijadwalkan.

4. **Pengambilan Keputusan Berbasis Data**: Menyediakan sistem analisis dan metrik kinerja untuk pengambilan keputusan yang lebih baik.

5. **Manajemen Sumber Daya**: Meningkatkan utilisasi armada dan memastikan distribusi tugas yang merata.

## Pemetaan Rumusan Masalah

### Masalah Utama:
- Penugasan manual yang tidak efisien dan rentan kesalahan
- Keterbatasan dalam mengoptimalkan alokasi sumber daya
- Kesulitan dalam memprediksi dan menghitung metrik kinerja secara real-time
- Kurangnya wawasan analitis terhadap kinerja operasional

### Sub-masalah:
1. **Optimasi Penugasan Unit**: Bagaimana menetapkan unit kendaraan yang tepat ke rute dan jadwal tertentu?
2. **Keseimbangan Beban Kerja**: Bagaimana mendistribusikan beban kerja secara merata di seluruh armada?
3. **Pengelolaan Kapasitas**: Bagaimana memastikan kapasitas unit sesuai dengan kebutuhan rute?
4. **Pemantauan Kinerja**: Bagaimana mengukur efisiensi dan efektivitas dari penugasan yang dilakukan?

## Metode yang Digunakan

### 1. Algoritma Optimasi Penugasan

Sistem menggunakan pendekatan berbasis skoring yang mempertimbangkan berbagai parameter:

#### Fungsi Skoring Komposit:
```
Skor Total = w₁ × Skor Kapasitas + w₂ × Skor Jarak + w₃ × Skor Ketersediaan + w₄ × Skor Biaya
```

Dimana:
- `w₁ + w₂ + w₃ + w₄ = 1` (bobot normalisasi)
- `w₁`: Bobot kapasitas unit
- `w₂`: Bobot jarak dan waktu tempuh
- `w₃`: Bobot ketersediaan dan status unit
- `w₄`: Bobot biaya operasional

#### Perhitungan Skor Individual:

**a. Skor Kapasitas (Capacity Score):**
```
Skor_Kapasitas = min(1.0, kapasitas_unit / kebutuhan_rute)
```

**b. Skor Jarak (Distance Score):**
```
Skor_Jarak = 1 - (jarak_rute / max_jarak_rute)
```

**c. Skor Ketersediaan (Availability Score):**
```
Skor_Ketersediaan = {
  1.0 jika status_unit = "Available",
  0.0 jika status_unit = "Maintenance"
}
```

**d. Skor Biaya (Cost Score):**
```
Skor_Biaya = 1 / (1 + biaya_operasional_per_km)
```

### 2. Algoritma Penjadwalan

Sistem menggunakan pendekatan greedy dengan prioritas berdasarkan parameter operasional:

#### Algoritma Penugasan:
```
1. Urutkan jadwal berdasarkan prioritas (tinggi ke rendah)
2. Urutkan unit berdasarkan kriteria penilaian
3. Untuk setiap jadwal aktif:
   a. Filter unit yang memenuhi kriteria (rute, kapasitas, waktu)
   b. Hitung skor komposit untuk setiap unit yang memungkinkan
   c. Pilih unit dengan skor tertinggi
   d. Tandai unit sebagai terpakai untuk periode tertentu
4. Ulangi hingga semua jadwal diproses atau unit habis
```

### 3. Metrik Kinerja

Sistem menghitung berbagai metrik untuk mengevaluasi kinerja:

**a. Tingkat Cakupan (Coverage Rate):**
```
Coverage_Rate = (Jumlah_jadwal_terlayani / Total_jadwal) × 100%
```

**b. Utilisasi Unit (Utilization Rate):**
```
Utilization_Rate = (Jumlah_unit_digunakan / Total_unit) × 100%
```

**c. Rata-rata Skor Penugasan:**
```
Avg_Score = Σ(Skor_penugasan) / Jumlah_penugasan
```

**d. Biaya Operasional Total:**
```
Total_Cost = Σ(biaya_bbm_penugasan_i) untuk i = 1 sampai n
```

## Matematika dalam Sistem

### 1. Fungsi Objektif Optimasi
```
Maksimalkan: f(x) = Σ(w_k × s_ik) untuk semua i,j
Dimana:
- x_ij = 1 jika unit i ditugaskan ke jadwal j, 0 jika tidak
- s_ik = skor dari unit i berdasarkan kriteria k
- w_k = bobot dari kriteria k
```

### 2. Kendala (Constraints)
```
a. Σ(x_ij) ≤ 1 untuk setiap unit i (unit hanya ditugaskan sekali)
b. Σ(x_ij) ≤ 1 untuk setiap jadwal j (jadwal hanya ditugaskan satu unit)
c. kapasitas_unit_i ≥ kebutuhan_rute_j (ketersediaan kapasitas)
d. waktu_berangkat + waktu_tempuh + waktu_turnaround ≤ batas_waktu
```

### 3. Perhitungan Waktu dan Rute
```
Waktu_kembali = Waktu_berangkat + Waktu_tempuh_rute + Waktu_turnaround
```

### 4. Model Biaya BBM (Bahan Bakar Minyak)
```
BBM_digunakan_per_jam = Jarak_rute / Efisiensi_BBM_unit
Biaya_BBM = BBM_digunakan_per_jam × Harga_BBM_per_liter
```

Dimana:
- Jarak_rute = jarak satu arah dari data rute (dalam km)
- Efisiensi_BBM_unit = efisiensi bahan bakar unit (dalam km/L)
- Harga_BBM_per_liter = parameter harga BBM per liter (dalam Rupiah)

### 5. Perhitungan Waktu Idle/Rest Unit
```
Waktu_Idle_Unit = Total_jam_operasional - Σ(Waktu_penugasan_per_unit)
Rata-rata_Idle_Time = Σ(Waktu_Idle_Unit_i) / Jumlah_total_unit
```

Dimana:
- Total_jam_operasional = jam kerja maksimum yang diperbolehkan per hari
- Waktu_penugasan_per_unit = jumlah waktu yang dihabiskan unit untuk semua penugasan dalam satu hari
- Waktu_penugasan = Σ(Waktu_tempuh_rute_j + Waktu_turnaround) untuk semua rute j yang ditugaskan ke unit i

atau dalam bentuk lain:
```
Total_Idle_Time = (Jumlah_unit × Jam_kerja_maksimum) - Σ(Waktu_beroperasi_per_unit)
```

Dimana:
- Waktu_beroperasi_per_unit = Σ(Waktu_tempuh_rute + Waktu_turnaround) untuk semua jadwal yang ditugaskan ke unit tersebut

### 6. Indikator Kinerja BBM
Sistem juga menghitung beberapa metrik terkait BBM:
- Total BBM (liter): Jumlah total bahan bakar yang digunakan
- Biaya BBM per penugasan: Rata-rata biaya BBM per penugasan
- Biaya BBM per km: Efisiensi biaya BBM per kilometer

## Arsitektur Sistem

### Komponen Utama:
1. **Database**: SQLite untuk menyimpan unit, rute, jadwal, dan penugasan
2. **Engine Optimasi**: Algoritma penugasan berbasis skoring
3. **Antarmuka Pengguna**: Streamlit untuk visualisasi dan kontrol
4. **Modul Analisis**: Perhitungan metrik dan statistik

### Struktur Data:
- **Unit**: ID, nama, kapasitas, efisiensi BBM, biaya operasional, status, rute yang diizinkan
- **Rute**: ID, nama, asal, tujuan, jarak, waktu tempuh, tipe rute, kapasitas yang dibutuhkan
- **Jadwal**: ID, rute, waktu berangkat, hari operasi, prioritas
- **Penugasan**: Tanggal, jadwal, unit, waktu, skor, biaya

## Fitur Utama Sistem

1. **Manajemen Data**: Pengelolaan unit, rute, dan jadwal
2. **Manajemen Lokasi**: Pengelolaan data lokasi terminal dan fasilitas lainnya
3. **Optimasi Penugasan**: Algoritma otomatis untuk penugasan optimal
4. **Monitoring Real-time**: Pemantauan status dan kinerja operasional
5. **Analisis dan Laporan**: Visualisasi dan metrik kinerja
6. **Pengaturan Parameter**: Konfigurasi bobot dan parameter operasional
7. **Audit Trail**: Riwayat perubahan dan aktivitas sistem
8. **Analisis Waktu Idle Unit**: Perhitungan dan visualisasi waktu istirahat/idle kendaraan untuk optimalisasi penggunaan armada
9. **Halaman Analisis Idle Time**: Tampilan khusus untuk menganalisis distribusi waktu idle unit, tingkat utilisasi, dan rekomendasi penugasan

## Teknologi yang Digunakan

- **Bahasa Pemrograman**: Python
- **Framework Web**: Streamlit
- **Database**: SQLite
- **Visualisasi**: Plotly, Pandas
- **ORM**: SQLAlchemy
- **Algoritma**: Pendekatan greedy berbasis skoring

## Manfaat Sistem

Sistem ini memberikan manfaat seperti:
- Pengurangan waktu dalam proses penugasan
- Peningkatan efisiensi operasional
- Pengambilan keputusan yang lebih baik berbasis data
- Pengurangan biaya operasional
- Peningkatan kualitas layanan
- Dokumentasi dan audit trail yang komprehensif

Sistem ini dirancang untuk memenuhi kebutuhan organisasi transportasi dalam mengelola armada secara efisien dan efektif dengan pendekatan berbasis teknologi dan data.