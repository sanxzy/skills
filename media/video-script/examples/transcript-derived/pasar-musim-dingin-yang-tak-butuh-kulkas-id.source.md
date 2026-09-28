# Pasar Paling Dingin di Dunia — sumber contoh transcript

## Identitas dan status

- Jenis: **penyuntingan transcript yang disediakan pengguna untuk contoh gaya**, bukan naskah original hasil riset menyeluruh.
- Penulis/penerbit video: **Jelajah bumi**. Redaksi dan susunan sumber tetap menjadi dasar contoh; bukan karya yang diklaim dibuat sendiri oleh agen.
- Video: https://www.youtube.com/watch?v=QpHRtRSAg-k
- ID: `QpHRtRSAg-k`; bahasa sumber/output: **id**. Tidak dilakukan terjemahan baru.
- SHA-256 input: `d85efb504157fc48c08d86b5fcabf79423cafcd3d9ebdb5bf488bdea36a12a4e`.
- Metadata ekstraksi yang disediakan mencatat judul, kanal, dan durasi; bukan klaim pemeriksaan ulang halaman YouTube saat ini.
- Tanggal penyuntingan: **26 September 2026**.
- Genre: Dokumenter kehidupan dan tempat.
- Jumlah blok transcript input: 19; hasil SRT yang ditata manual: 114 cue (107 narasi, 7 musik); token kata narasi: 807.
- Timeline terakhir: **08:26.375**; durasi metadata video: 517.0 detik. Caption dapat sedikit melewati angka durasi metadata.

Untuk mempelajari contoh, baca [SRT bundled](pasar-musim-dingin-yang-tak-butuh-kulkas-id.srt) bersama file ini. Identitas video dan hash input mencatat provenance historis; naskah dan catatan yang diperlukan tersedia di dalam bundle. Catatan pemeriksaan merekam pekerjaan saat penyuntingan pada tanggal di atas, bukan pemeriksaan baru pada saat skill digunakan.

## Sumber

| ID | Sumber | URL | Apa yang dibuktikan/dibaca |
| --- | --- | --- | --- |
| R00 | Video asli dan transcript lokal milik pengguna | https://www.youtube.com/watch?v=QpHRtRSAg-k | Seluruh berkas transcript diproses; urutan kata dan struktur diperiksa dari teks yang tersedia. Sumber ini membuktikan asal redaksi, bukan otomatis kebenaran seluruh klaim faktualnya. Tidak dilakukan pemeriksaan frame atau pengukuran audio baru. |
| R01 | 4 Steps to Food Safety — FoodSafety.gov | https://www.foodsafety.gov/keep-food-safe/4-steps-to-food-safety | Bagian Chill dibaca: pembekuan tidak menghancurkan kuman berbahaya. Mendukung koreksi pembusukan lumpuh total; bukan verifikasi seluruh kondisi pasar. |

## Penyuntingan dan timing

Metadata ekstraksi dikeluarkan dari naskah utama. Cue musik di tengah kalimat dan label suara/pembicara yang tidak diucapkan dipindahkan ke konteks sumber; interval musik tersendiri menggunakan `♪ ♪`. Kalimat yang terpotong pada batas caption disambungkan, paragraf panjang dibagi pada akhir kalimat, dan ejaan yang jelas dirapikan. Urutan gagasan, gaya narasi, pembuka, pengembangan dan penutup sumber dipertahankan; tidak diringkas menjadi artikel baru.

Timecode SRT memakai jam:menit:detik,milidetik. Unit ucapan dan waktunya ditulis satu per satu secara manual di dalam rentang editorial sumber, bukan dipotong otomatis atau diukur ulang dari audio. Sesudah perbaikan satu kalimat per shot, validator lulus: 76 cue, 807 kata narasi tetap berurutan, 13,8% waktu tanpa narasi. Peringatan beberapa cue pendek memerlukan pembacaan/audio nyata; `ffprobe` mengenali 76 paket SubRip, tetapi impor editor tertentu belum diuji. Jika dibuat suara baru, retime terhadap rekamannya. Jeda aksi terutama pada dokumenter satwa tidak boleh disalin ke naskah baru tanpa adegan yang sesuai. Minimum delapan menit untuk naskah baru tidak digunakan untuk menambahkan isi atau hening ke adaptasi ini.

## Catatan khusus

- Pembusukan tidak dinyatakan lumpuh total; pembekuan bukan sterilisasi. Keterangan soal tubuh, uap napas, permafrost dan makanan tidak menjadi panduan kesehatan.
- Penyuntingan tidak membuktikan pasar selalu buka, Yakutsk selalu dingin sepanjang tahun, atau semua rumah/jalan/transportasi mengikuti gambaran episode.

**Batas verifikasi:** Populasi, jaringan jalan, jam pasar dan suhu musim panas adalah klaim sumber; jangan menganggap semua kondisi berlangsung sepanjang tahun. Pembekuan tidak mensterilkan makanan. Sumber tambahan, bila tercantum, hanya mendukung koreksi yang dijelaskan, bukan sertifikasi seluruh isi. Klaim yang masih mengikuti video adalah **belum diverifikasi mandiri**. Bacalah contoh untuk mempelajari penulisan; ketika menulis video baru, riset fakta kembali sesuai workflow skill.

## Perubahan redaksi yang dicatat

| Bagian sumber | Hasil penyuntingan |
| --- | --- |
| landscape | lanskap |
| proses pembusukan lumpuh total | proses pembusukan melambat ketika makanan tetap beku |

## Pemetaan hasil ke transcript asal

Peta ini mencakup setiap cue SRT dalam rentang nomor berurutan, termasuk musik. `Tnnn` adalah urutan blok transcript input yang dicatat sebelumnya, bukan nomor cue SRT. Beberapa cue merujuk rantai input yang sama karena paragraf asal ditata menjadi unit ucapan pendek secara manual. Untuk mempelajari redaksi dan susunan, baca SRT bundled dan catatan penyuntingannya. Hash input hanya mencatat asal historis; tidak diperlukan berkas ekstraksi asli. Rentang video mencatat konteks audiovisual asal, bukan bukti bahwa footage sudah diperiksa ulang. Pemetaan **bukan** klaim bahwa setiap fakta sudah dikonfirmasi oleh sumber primer.

| Cue SRT | Rentang editorial cue | Blok transcript input | Rentang input yang tercakup | Status |
| --- | --- | --- | --- | --- |
| 1 | 00:00:03,274–00:00:05,294 | T001 | 00:03.274–00:05.294 | Musik/cue `♪ ♪` |
| 2 | 00:00:09,170–00:00:11,190 | T002 | 00:09.170–00:11.190 | Musik/cue `♪ ♪` |
| 3–19 | 00:00:11,500–00:01:26,000 | T003, T004 | 00:13.755–01:18.720 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| 20–36 | 00:01:26,000–00:02:31,600 | T005 | 01:20.565–02:02.600 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| 37–41 | 00:02:31,600–00:02:54,200 | T006 | 01:59.880–02:39.876 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| 42–64 | 00:02:54,200–00:04:23,500 | T007–T009 | 02:42.599–04:52.160 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| 65–69 | 00:04:23,500–00:04:39,500 | T007–T009 | 02:42.599–04:52.160 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| 70–73 | 00:04:39,500–00:04:54,400 | T007–T009 | 02:42.599–04:52.160 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| 74–76 | 00:04:54,400–00:05:04,700 | T010, T011 | 04:50.360–05:41.313 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| 77–96 | 00:05:04,700–00:06:25,700 | T012–T014 | 05:42.880–07:36.595 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| 97–109 | 00:06:25,700–00:07:22,900 | T012–T014 | 05:42.880–07:36.595 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| 110 | 00:07:50,950–00:07:52,970 | T015 | 07:50.950–07:52.970 | Musik/cue `♪ ♪` |
| 111 | 00:07:58,155–00:08:00,175 | T016 | 07:58.155–08:00.175 | Musik/cue `♪ ♪` |
| 112 | 00:08:07,325–00:08:09,345 | T017 | 08:07.325–08:09.345 | Musik/cue `♪ ♪` |
| 113 | 00:08:16,495–00:08:18,515 | T018 | 08:16.495–08:18.515 | Musik/cue `♪ ♪` |
| 114 | 00:08:24,355–00:08:26,375 | T019 | 08:24.355–08:26.375 | Musik/cue `♪ ♪` |

## Penggunaan sebagai contoh

Pola yang bisa dipelajari: **Pasar sebagai gambaran konkret iklim; deskripsi indrawi, barang dagangan, makanan dan penutup reflektif.** Fokus pada urutan kejadian/gagasan, hubungan antarkalimat, detail yang bisa divisualkan, dan ruang bagi gambar. Jangan menyalin nama kanal, identitas pembicara, kalimat khas, fakta, atau timecode secara mekanis ke karya baru.

## Pemeriksaan akhir

Setiap cue SRT tercakup dalam pemetaan provenance, termasuk tujuh cue musik. Revisi 28 September 2026 memecah kalimat panjang menjadi unit pendek (maksimal dua baris visual, ≤40 karakter per baris, ≤80 karakter per cue, ≤15 displayed CPS) **tanpa menghapus kata**; 107 cue narasi di-pace manual pada sekitar 13 displayed CPS agar tetap mengikuti laju bicara video asli, dan ketujuh jeda musik mempertahankan waktu aslinya. Pemeriksaan struktural: **PASS, 114 cue, 807 token, 506,4 detik, tanpa peringatan panjang baris/cue atau CPS**; `ffprobe` mengenali 114 paket SubRip dan Remotion mengimpor SRT tanpa mengubah teks, pemenggalan baris, maupun milidetik. Klaim tentang produk beku dan Carab Driver Convention adalah bahan contoh, bukan verifikasi lapangan. Pemeriksaan ini tidak membuktikan fakta atau durasi rekaman baru.

## Title and thumbnail concept

- Selected editorial title: **Pasar Musim Dingin yang Tak Butuh Kulkas**. Original brief/video titles remain recorded for provenance.
- Audience: Penonton kebutuhan sehari-hari dalam iklim ekstrem
- Curiosity loop: Daging dan ikan dipajang di udara terbuka karena dingin musimnya.
- Script payoff: Jelaskan kondisi pasar pada musim dingin; pembekuan tidak berarti sterilisasi.
- Proposed thumbnail: Barang dagangan beku di pasar terbuka; kondisi musim harus terlihat. This is an asset concept, not a supplied or generated image.
- Performance status: untested editorial candidate. No comparative outlier data, reach/views results, or audience-test results were supplied; this title is not claimed to be a proven winner.
