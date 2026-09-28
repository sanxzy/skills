# Aldrich Ames - SEORANG PENGKHIANAT YANG HAMPIR MEMBUAT AS BUBAR — sumber contoh transcript

## Identitas dan status

- Jenis: **penyuntingan transcript yang disediakan pengguna untuk contoh gaya**, bukan naskah original hasil riset menyeluruh.
- Penulis/penerbit video: **Kamar Film**. Redaksi dan susunan sumber tetap menjadi dasar contoh; bukan karya yang diklaim dibuat sendiri oleh agen.
- Video: https://www.youtube.com/watch?v=RiB4stBa9yU
- ID: `RiB4stBa9yU`; bahasa sumber/output: **id**. Tidak dilakukan terjemahan baru.
- SHA-256 input: `9fc3e8612392b53fac4b1674b4b0adf6565a37cacfbd98a4aa676c3f504a2bbf`.
- Metadata ekstraksi yang disediakan mencatat judul, kanal, dan durasi; bukan klaim pemeriksaan ulang halaman YouTube saat ini.
- Tanggal penyuntingan: **26 September 2026**.
- Genre: Investigasi spionase.
- Jumlah blok input: 40; hasil SRT manual: 673 cue (670 narasi, tiga `♪ ♪`); token kata narasi: 3428.
- Timeline terakhir: **24:38.000**; durasi metadata video: 1505.0 detik. Caption dapat sedikit melewati angka durasi metadata.

Untuk mempelajari contoh, baca [SRT bundled](cia-mencari-pengkhianat-di-dalam-markasnya-sendiri-id.srt) bersama file ini. Identitas video dan hash input mencatat provenance historis; naskah dan catatan yang diperlukan tersedia di dalam bundle. Catatan pemeriksaan merekam pekerjaan saat penyuntingan pada tanggal di atas, bukan pemeriksaan baru pada saat skill digunakan.

## Sumber

| ID | Sumber | URL | Apa yang dibuktikan/dibaca |
| --- | --- | --- | --- |
| R00 | Video asli dan transcript lokal milik pengguna | https://www.youtube.com/watch?v=RiB4stBa9yU | Seluruh berkas transcript diproses; urutan kata dan struktur diperiksa dari teks yang tersedia. Sumber ini membuktikan asal redaksi, bukan otomatis kebenaran seluruh klaim faktualnya. Tidak dilakukan pemeriksaan frame atau pengukuran audio baru. |
| R01 | Aldrich Ames — FBI | https://www.fbi.gov/history/cases-and-criminals/aldrich-ames | Riwayat kasus, pembayaran pertama, penugasan Roma 1986, penangkapan dan hukuman. Catatan penyuntingan 26 September 2026 merekam pembacaan bagian relevan; tidak menyatakan pembacaan baru pada penggunaan skill berikutnya. Tidak membuktikan seluruh uraian psikologi/birokrasi dari video. |
| R02 | Assessment of the Aldrich H. Ames Espionage Case — Senate Select Committee on Intelligence, 1 November 1994 | https://www.intelligence.senate.gov/wp-content/uploads/2024/08/sites-default-filesations-10390.pdf | Bagian pembayaran/penyerahan Juni, penugasan Roma dan kegagalan investigasi dibaca. Digunakan untuk membedakan lebih dari sepuluh sumber dalam penyerahan Juni dari jumlah operasi keseluruhan. |
| R03 | Review of FBI Performance in Uncovering Aldrich Ames — DOJ OIG, April 1997 | https://oig.justice.gov/sites/default/files/legacy/special/9704.htm | Introduction: sedikitnya sepuluh sumber CIA/FBI dieksekusi. Hanya klaim relevan, bukan validasi seluruh transcript. |

## Penyuntingan dan timing

Metadata ekstraksi dikeluarkan dari naskah utama. Cue musik di tengah kalimat dan label suara/pembicara yang tidak diucapkan dipindahkan ke konteks sumber; interval musik tersendiri menggunakan `♪ ♪`. Kalimat yang terpotong pada batas caption disambungkan, paragraf panjang dibagi pada akhir kalimat, dan ejaan yang jelas dirapikan. Urutan gagasan, gaya narasi, pembuka, pengembangan dan penutup sumber dipertahankan; tidak diringkas menjadi artikel baru.

Ke-673 cue SRT ditulis dan diberi timecode **manual** dalam jendela editorial asal, bukan dihasilkan lewat pemisahan atau retiming kode. Seluruh 3.428 token kata narasi berurutan sama persis dengan versi arsip dan ketiga jendela `♪ ♪` tidak bergeser. Validator struktur lulus (142,4 active WPM; 2,28% unspoken); `ffprobe` mengenali 673 paket SubRip. Namun **458 cue melebihi target nyaman 15 karakter/detik**, meski tidak ada baris >40 karakter atau cue >80 karakter; perlu retiming/penilaian layar manual sebelum ini digunakan untuk delivery. Catatan ini bukan pengukuran rekaman atau bukti impor track subtitle editor; jika direkam ulang, timecode harus diselaraskan dengan pembacaan baru.

## Catatan khusus

- Koreksi jumlah minimal sumber yang dieksekusi dan jumlah sumber dalam penyerahan Juni mengikuti R02/R03. Klaim bahwa bantuan AS langsung mendanai pembayaran SVR tidak dipertahankan.
- Banyak uraian mengenai kebohongan kelembagaan, motif, arus pembayaran, perilaku istri dan rincian korban tetap berasal dari video. Lihat [contoh hasil riset Ames](../pengkhianat-cia-yang-lolos-hampir-9-tahun.srt) dan [peta buktinya](../pengkhianat-cia-yang-lolos-hampir-9-tahun.source.md) untuk mempelajari dukungan fakta yang lebih lengkap; keduanya bukan pengganti riset baru.

**Batas verifikasi:** Pembayaran, jumlah aset/operasi, motivasi, penilaian kelembagaan, motif istri, dan hubungan bantuan AS dengan pendanaan SVR tidak semuanya dibuktikan oleh transkrip. Sumber tambahan, bila tercantum, hanya mendukung koreksi yang dijelaskan, bukan sertifikasi seluruh isi. Klaim yang masih mengikuti video adalah **belum diverifikasi mandiri**. Bacalah contoh untuk mempelajari penulisan; ketika menulis video baru, riset fakta kembali sesuai workflow skill.

## Perubahan redaksi yang dicatat

| Bagian sumber | Hasil penyuntingan |
| --- | --- |
| Ada 12 agen yang dieksekusi mati di Moskow | Sedikitnya sepuluh sumber CIA dan FBI dieksekusi |
| seluruh dokumen berisi identitas para agen ganda | dokumen berisi identitas sumber-sumber intelijen |
| lebih dari 25 aset manusia utama AS | lebih dari sepuluh sumber penting CIA dan FBI |
| Roma, tempat Aldrich ditempatkan oleh CIA dari tahun 1989 hingga 1991 | Roma, tempat Aldrich ditugaskan dari 1986 hingga 1989 |
| SVR yang didanai oleh bantuan itu juga tetap membayar Aldrich | SVR juga tetap membayar Aldrich |
| pemukiman | permukiman |

## Pemetaan hasil ke transcript asal

Peta ini mencakup cue SRT 1–673, termasuk tiga cue musik 1, 2, dan 23. `Tnnn` adalah urutan blok input Markdown historis, bukan nomor SRT. Beberapa unit editorial hasil menunjuk rantai input yang sama; jendela editorial asal tidak membuktikan bahwa footage diperiksa ulang. Baca SRT bersama catatan penyuntingan ini. Hash input hanya mencatat asal historis; tidak diperlukan berkas ekstraksi asli. Rentang video mencatat konteks audiovisual asal, bukan bukti bahwa footage sudah diperiksa ulang. Pemetaan **bukan** klaim bahwa setiap fakta sudah dikonfirmasi oleh sumber primer.

| Blok asal → cue SRT | Jendela editorial asal (MM:SS.mmm) | Blok input | Rentang input yang tercakup | Status |
| --- | --- | --- | --- | --- |
| E001 (cue 1, `♪ ♪`) | 00:01.964–00:03.984 | T001 | 00:01.964–00:03.984 | Musik/cue |
| E002 (cue 2, `♪ ♪`) | 00:09.824–00:11.844 | T002 | 00:09.824–00:11.844 | Musik/cue |
| E003 (cue 3–22) | 00:16.100–01:10.300 | T003, T004 | 00:16.119–01:06.865 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E004 (cue 23, `♪ ♪`) | 01:12.705–01:14.725 | T005 | 01:12.705–01:14.725 | Musik/cue |
| E005 (cue 24–44) | 01:19.900–02:17.900 | T006, T007, T008, T009, T010 | 01:19.920–04:52.160 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E006 (cue 45–65) | 02:17.900–03:12.000 | T006, T007, T008, T009, T010 | 01:19.920–04:52.160 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E007 (cue 66–86) | 03:12.000–04:03.800 | T006, T007, T008, T009, T010 | 01:19.920–04:52.160 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E008 (cue 87–107) | 04:03.800–04:57.400 | T006, T007, T008, T009, T010 | 01:19.920–04:52.160 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E009 (cue 108–118) | 04:57.400–05:26.300 | T006, T007, T008, T009, T010 | 01:19.920–04:52.160 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E010 (cue 119–140) | 05:26.300–06:17.200 | T011, T012, T013, T014, T015, T016, T017, T018 | 04:51.478–10:27.079 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E011 (cue 141–155) | 06:17.200–06:52.700 | T011, T012, T013, T014, T015, T016, T017, T018 | 04:51.478–10:27.079 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E012 (cue 156–169) | 06:52.700–07:36.000 | T011, T012, T013, T014, T015, T016, T017, T018 | 04:51.478–10:27.079 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E013 (cue 170–183) | 07:36.000–08:14.200 | T011, T012, T013, T014, T015, T016, T017, T018 | 04:51.478–10:27.079 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E014 (cue 184–204) | 08:14.200–09:05.800 | T011, T012, T013, T014, T015, T016, T017, T018 | 04:51.478–10:27.079 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E015 (cue 205–224) | 09:05.800–09:53.200 | T011, T012, T013, T014, T015, T016, T017, T018 | 04:51.478–10:27.079 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E016 (cue 225–247) | 09:53.200–10:47.300 | T011, T012, T013, T014, T015, T016, T017, T018 | 04:51.478–10:27.079 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E017 (cue 248–264) | 10:47.300–11:31.200 | T011, T012, T013, T014, T015, T016, T017, T018 | 04:51.478–10:27.079 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E018 (cue 265–272) | 11:31.200–11:50.000 | T011, T012, T013, T014, T015, T016, T017, T018 | 04:51.478–10:27.079 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E019 (cue 273–290) | 11:50.000–12:44.800 | T019, T020, T021 | 10:25.000–12:04.493 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E020 (cue 291–308) | 12:44.800–13:34.000 | T019, T020, T021 | 10:25.000–12:04.493 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E021 (cue 309–315) | 13:34.000–13:51.200 | T019, T020, T021 | 10:25.000–12:04.493 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E022 (cue 316–334) | 13:51.200–14:40.500 | T022, T023, T024 | 12:06.279–14:11.720 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E023 (cue 335–352) | 14:40.500–15:32.500 | T022, T023, T024 | 12:06.279–14:11.720 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E024 (cue 353–372) | 15:32.500–16:22.000 | T022, T023, T024 | 12:06.279–14:11.720 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E025 (cue 373–394) | 16:22.000–17:18.400 | T025, T026, T027, T028, T029 | 14:10.519–17:22.000 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E026 (cue 395–414) | 17:18.400–18:08.700 | T025, T026, T027, T028, T029 | 14:10.519–17:22.000 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E027 (cue 415–434) | 18:08.700–19:01.000 | T025, T026, T027, T028, T029 | 14:10.519–17:22.000 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E028 (cue 435–451) | 19:01.000–19:45.700 | T025, T026, T027, T028, T029 | 14:10.519–17:22.000 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E029 (cue 452–466) | 19:45.700–20:24.400 | T025, T026, T027, T028, T029 | 14:10.519–17:22.000 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E030 (cue 467–486) | 20:24.400–21:13.700 | T030, T031, T032, T033, T034, T035, T036, T037, T038, T039, T040 | 17:24.520–24:38.000 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E031 (cue 487–506) | 21:13.700–22:06.300 | T030, T031, T032, T033, T034, T035, T036, T037, T038, T039, T040 | 17:24.520–24:38.000 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E032 (cue 507–525) | 22:06.300–22:53.400 | T030, T031, T032, T033, T034, T035, T036, T037, T038, T039, T040 | 17:24.520–24:38.000 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E033 (cue 526–541) | 22:53.400–23:35.800 | T030, T031, T032, T033, T034, T035, T036, T037, T038, T039, T040 | 17:24.520–24:38.000 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E034 (cue 542–558) | 23:35.800–24:20.700 | T030, T031, T032, T033, T034, T035, T036, T037, T038, T039, T040 | 17:24.520–24:38.000 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E035 (cue 559–575) | 24:20.700–25:07.500 | T030, T031, T032, T033, T034, T035, T036, T037, T038, T039, T040 | 17:24.520–24:38.000 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E036 (cue 576–596) | 25:07.500–26:04.700 | T030, T031, T032, T033, T034, T035, T036, T037, T038, T039, T040 | 17:24.520–24:38.000 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E037 (cue 597–615) | 26:04.700–26:55.800 | T030, T031, T032, T033, T034, T035, T036, T037, T038, T039, T040 | 17:24.520–24:38.000 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E038 (cue 616–635) | 26:55.800–27:47.200 | T030, T031, T032, T033, T034, T035, T036, T037, T038, T039, T040 | 17:24.520–24:38.000 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E039 (cue 636–655) | 27:47.200–28:39.300 | T030, T031, T032, T033, T034, T035, T036, T037, T038, T039, T040 | 17:24.520–24:38.000 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E040 (cue 656–673) | 28:39.300–29:24.500 | T030, T031, T032, T033, T034, T035, T036, T037, T038, T039, T040 | 17:24.520–24:38.000 | Redaksi bersumber R00; koreksi terbatas lihat catatan |

## Penggunaan sebagai contoh

Pola yang bisa dipelajari: **Dampak pengkhianatan membuka cerita; uang dan akses mengantar keputusan; kekayaan menjadi petunjuk.** Fokus pada urutan kejadian/gagasan, hubungan antarkalimat, detail yang bisa divisualkan, dan ruang bagi gambar. Jangan menyalin nama kanal, identitas pembicara, kalimat khas, fakta, atau timecode secara mekanis ke karya baru.

## Pemeriksaan akhir

Seluruh 673 cue berada dalam 40 jendela editorial asal dan dapat ditelusuri ke rantai input T001–T040; waktu ketiga musik tetap sama. Validator memeriksa struktur SRT, nomor, interval positif, tanpa tumpang tindih, satu kalimat paling banyak per cue, dua baris visual paling banyak, tanpa metadata/URL. **458 peringatan kecepatan tampilan belum diselesaikan**; hasil ini tidak membuktikan fakta arsip (terutama tanggal wafat, rincian korban, dan putusan/kebijakan), kenyamanan playback, atau impor editor.

## Title and thumbnail concept

- Selected editorial title: **CIA Mencari Pengkhianat di Dalam Markasnya Sendiri**. Original brief/video titles remain recorded for provenance.
- Audience: Penonton spionase dan kegagalan keamanan
- Curiosity loop: Orang yang memiliki akses sah justru menjadi sumber kebocoran.
- Script payoff: Ikuti akses, pembayaran, petunjuk yang terlewat, penyelidikan, dan penangkapan.
- Proposed thumbnail: Ames dan lambang CIA; satu petunjuk keuangan dapat melengkapi judul. This is an asset concept, not a supplied or generated image.
- Performance status: untested editorial candidate. No comparative outlier data, reach/views results, or audience-test results were supplied; this title is not claimed to be a proven winner.
