# Tristan Da Cunha, Pulau Berpenghuni Paling Terisolasi di Dunia — sumber contoh transcript

## Identitas dan status

- Jenis: **penyuntingan transcript yang disediakan pengguna untuk contoh gaya**, bukan naskah original hasil riset menyeluruh.
- Penulis/penerbit video: **VanDjen Media**. Redaksi dan susunan sumber tetap menjadi dasar contoh; bukan karya yang diklaim dibuat sendiri oleh agen.
- Video: https://www.youtube.com/watch?v=sKlN8EMhbw4
- ID: `sKlN8EMhbw4`; bahasa sumber/output: **id**. Tidak dilakukan terjemahan baru.
- SHA-256 input: `66a471e968ca97933bc7e38b24ab0446c23517219f0cea96894da3815e4afc84`.
- Metadata ekstraksi yang disediakan mencatat judul, kanal, dan durasi; bukan klaim pemeriksaan ulang halaman YouTube saat ini.
- Tanggal penyuntingan: **26 September 2026**.
- Genre: Dokumenter kehidupan dan tempat.
- Jumlah blok input: 33; hasil editorial lama: 32; hasil SRT manual: 436 cue (435 narasi, satu `♪ ♪`); token kata narasi: 2542.
- Timeline terakhir: **21:14.400**; durasi metadata video: 1275.0 detik. Caption dapat sedikit melewati angka durasi metadata.

Untuk mempelajari contoh, baca [SRT bundled](pulau-tanpa-bandara-bagaimana-warganya-bertahan-id.srt) bersama file ini. Identitas video dan hash input mencatat provenance historis; naskah dan catatan yang diperlukan tersedia di dalam bundle. Catatan pemeriksaan merekam pekerjaan saat penyuntingan pada tanggal di atas, bukan pemeriksaan baru pada saat skill digunakan.

## Sumber

| ID | Sumber | URL | Apa yang dibuktikan/dibaca |
| --- | --- | --- | --- |
| R00 | Video asli dan transcript lokal milik pengguna | https://www.youtube.com/watch?v=sKlN8EMhbw4 | Seluruh berkas transcript diproses; urutan kata dan struktur diperiksa dari teks yang tersedia. Sumber ini membuktikan asal redaksi, bukan otomatis kebenaran seluruh klaim faktualnya. Tidak dilakukan pemeriksaan frame atau pengukuran audio baru. |
| R01 | First evidence of mouse attacks on Gough adult albatrosses — pemerintah/asosiasi Tristan, 2019 | https://www.tristandc.com/news-2019-01-09-micegough.php | Uraian dibaca: tikus rumah Mus musculus menyerang burung. Koreksi tikus Norwegia dan klaim insting perlindungan yang tidak disokong; tidak mengklaim membaca paper lengkap. |

## Penyuntingan dan timing

Metadata ekstraksi dikeluarkan dari naskah utama. Cue musik di tengah kalimat dan label suara/pembicara yang tidak diucapkan dipindahkan ke konteks sumber; interval musik tersendiri menggunakan `♪ ♪`. Kalimat yang terpotong pada batas caption disambungkan, paragraf panjang dibagi pada akhir kalimat, dan ejaan yang jelas dirapikan. Urutan gagasan, gaya narasi, pembuka, pengembangan dan penutup sumber dipertahankan; tidak diringkas menjadi artikel baru.

Ke-436 cue SRT ditulis dan ditiming manual dalam window editorial asal tanpa memotong atau me-retime lewat kode. Sebanyak 2.542 token kata narasi tetap dalam urutan asal, satu cue `♪ ♪` tetap terlihat pada track subtitle. Cues mempunyai satu kalimat maksimal dalam satu/dua baris visual; validasi, perbandingan urutan kata dan `ffprobe` (436 paket SubRip) lulus. Timecode adalah **perkiraan editorial**, bukan timecode yang diukur ulang pada rekaman; keterbacaan, suara terrekam, dan impor editor video masih perlu diuji. Jika contoh diproduksi ulang dengan suara baru, retime terhadap pembacaan baru. Jeda aksi terutama pada dokumenter satwa tidak boleh disalin ke naskah baru tanpa adegan yang sesuai. Minimum delapan menit untuk naskah baru tidak digunakan untuk menambahkan isi atau hening ke adaptasi ini.

## Catatan khusus

- Gough: tikus rumah, bukan tikus Norwegia. Satuan kawasan laut dirapikan menjadi km². Kata wind di akhir paragraf dihapus sebagai artefak.
- Tinggi keseluruhan gunung 13.000 meter dan dasar laut 11.000 meter tampak bermasalah dan belum terverifikasi. Jangan menyalinnya sebagai fakta. Klaim tidak mungkin ada bandara, kesehatan, genetika, Starlink dan tata pemerintahan juga perlu pemeriksaan sendiri.

**Batas verifikasi:** Tinggi gunung dari dasar laut, persentase satwa, genetika/asthma, kapasitas medis, tata pemerintahan dan kondisi mutakhir tidak seluruhnya diverifikasi ulang. Sumber tambahan, bila tercantum, hanya mendukung koreksi yang dijelaskan, bukan sertifikasi seluruh isi. Klaim yang masih mengikuti video adalah **belum diverifikasi mandiri**. Bacalah contoh untuk mempelajari penulisan; ketika menulis video baru, riset fakta kembali sesuai workflow skill.

## Perubahan redaksi yang dicatat

| Bagian sumber | Hasil penyuntingan |
| --- | --- |
| Tikus Norwegia invasif sengaja terbawa ke Pulau Gough | Tikus rumah invasif terbawa ke Pulau Gough |
| Burung albatros Tristan memiliki insting alamiah untuk melindungi anak-anak mereka dari serangan tikus yang bergerak di kegelapan malam. | Burung-burung ini menghadapi ancaman dari tikus yang menyerang anak-anak mereka di sarang. |
| seluas lebih dari 687.000 km | seluas lebih dari 687.000 km² |
| pemukiman | permukiman |

## Pemetaan hasil ke transcript asal

Peta ini mencakup seluruh cue SRT 1–436, termasuk musik pada cue 1. `E001`–`E032` menunjukkan unit editorial asal; `Tnnn` adalah urutan blok input Markdown historis, bukan nomor subtitle. Semua rentang cue baru berurutan dan mempertahankan interval luar unit asal. Untuk mempelajari redaksi dan susunan, baca SRT bundled beserta catatan penyuntingannya. Hash input hanya mencatat asal historis; tidak diperlukan berkas ekstraksi asli. Rentang video mencatat konteks audiovisual asal, bukan bukti bahwa footage sudah diperiksa ulang. Pemetaan **bukan** klaim bahwa setiap fakta sudah dikonfirmasi oleh sumber primer.

| Blok editorial asal → cue SRT | Rentang editorial cue (MM:SS.mmm) | Blok input | Rentang input yang tercakup | Status |
| --- | --- | --- | --- | --- |
| E001 (cue 1, `♪ ♪`) | 00:11.135–00:13.155 | T001 | 00:11.135–00:13.155 | Musik/cue |
| E002 (cue 2–12) | 00:13.500–00:56.100 | T002, T003 | 00:16.920–01:42.280 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E003 (cue 13–16) | 00:56.100–01:10.000 | T002, T003 | 00:16.920–01:42.280 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E004 (cue 17–22) | 01:10.000–01:33.400 | T004 | 01:39.240–02:10.880 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E005 (cue 23–35) | 01:33.400–02:29.300 | T005 | 02:21.160–03:04.680 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E006 (cue 36–52) | 02:29.300–03:28.200 | T006, T007 | 03:02.840–04:28.000 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E007 (cue 53–64) | 03:28.200–04:08.600 | T006, T007 | 03:02.840–04:28.000 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E008 (cue 65–78) | 04:08.600–04:52.400 | T008, T009, T010 | 04:26.000–06:14.280 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E009 (cue 79–96) | 04:52.400–05:50.800 | T008, T009, T010 | 04:26.000–06:14.280 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E010 (cue 97–106) | 05:50.800–06:22.600 | T008, T009, T010 | 04:26.000–06:14.280 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E011 (cue 107–120) | 06:22.600–07:04.700 | T011 | 06:15.840–06:56.639 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E012 (cue 121–135) | 07:04.700–07:52.900 | T012 | 06:57.759–07:39.080 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E013 (cue 136–148) | 07:52.900–08:32.800 | T013 | 07:40.319–08:24.720 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E014 (cue 149–157) | 08:32.800–09:07.500 | T014 | 08:22.720–08:53.886 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E015 (cue 158–176) | 09:07.500–10:07.200 | T015, T016, T017, T018 | 08:56.279–11:47.160 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E016 (cue 177–193) | 10:07.200–10:59.100 | T015, T016, T017, T018 | 08:56.279–11:47.160 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E017 (cue 194–213) | 10:59.100–12:03.500 | T015, T016, T017, T018 | 08:56.279–11:47.160 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E018 (cue 214–226) | 12:03.500–12:40.900 | T015, T016, T017, T018 | 08:56.279–11:47.160 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E019 (cue 227–245) | 12:40.900–13:39.300 | T019, T020 | 11:44.680–13:06.160 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E020 (cue 246–257) | 13:39.300–14:13.900 | T019, T020 | 11:44.680–13:06.160 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E021 (cue 258–279) | 14:13.900–15:27.900 | T021, T022 | 13:07.800–14:08.240 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E022 (cue 280–285) | 15:27.900–15:47.000 | T023 | 14:11.240–14:29.800 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E023 (cue 286–302) | 15:47.000–16:42.100 | T024, T025, T026 | 14:32.839–16:18.120 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E024 (cue 303–321) | 16:42.100–17:37.900 | T024, T025, T026 | 14:32.839–16:18.120 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E025 (cue 322–327) | 17:37.900–17:56.700 | T024, T025, T026 | 14:32.839–16:18.120 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E026 (cue 328–341) | 17:56.700–18:49.900 | T027 | 16:20.000–16:56.399 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E027 (cue 342–353) | 18:49.900–19:27.100 | T028 | 16:58.319–17:27.120 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E028 (cue 354–368) | 19:27.100–20:08.200 | T029 | 17:36.760–18:18.240 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E029 (cue 369–388) | 20:08.200–21:07.200 | T030, T031 | 18:20.360–19:44.960 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E030 (cue 389–402) | 21:07.200–21:49.900 | T030, T031 | 18:20.360–19:44.960 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E031 (cue 403–420) | 21:49.900–22:42.900 | T032 | 19:46.400–20:30.120 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E032 (cue 421–436) | 22:42.900–23:28.800 | T033 | 20:30.559–21:14.400 | Redaksi bersumber R00; koreksi terbatas lihat catatan |

## Penggunaan sebagai contoh

Pola yang bisa dipelajari: **Isolasi dijelaskan melalui medan, pelayaran, sejarah, sekolah, layanan kesehatan dan pekerjaan.** Fokus pada urutan kejadian/gagasan, hubungan antarkalimat, detail yang bisa divisualkan, dan ruang bagi gambar. Jangan menyalin nama kanal, identitas pembicara, kalimat khas, fakta, atau timecode secara mekanis ke karya baru.

## Pemeriksaan akhir

Seluruh 436 cue terpetakan ke 32 unit asal dengan rentang waktu yang cocok persis, termasuk `♪ ♪` yang tidak diucapkan. Validator lulus: nomor berurutan, interval positif/tidak tumpang tindih, satu kalimat maksimal dalam satu/dua baris visual, serta tanpa metadata/URL di subtitle. `ffprobe` membaca 436 paket SubRip; ini belum membuktikan impor editor, fakta, keterbacaan semua cue, atau durasi suara baru.

## Title and thumbnail concept

- Selected editorial title: **Pulau Tanpa Bandara: Bagaimana Warganya Bertahan?**. Original brief/video titles remain recorded for provenance.
- Audience: Penonton kehidupan terpencil
- Curiosity loop: Kebutuhan sehari-hari tetap harus terpenuhi ketika akses bergantung pada laut.
- Script payoff: Ikuti pelayaran, pasokan, layanan kesehatan, pekerjaan, dan kehidupan komunitas.
- Proposed thumbnail: Permukiman kecil di tengah laut dengan kapal sebagai fokus pendukung. This is an asset concept, not a supplied or generated image.
- Performance status: untested editorial candidate. No comparative outlier data, reach/views results, or audience-test results were supplied; this title is not claimed to be a proven winner.
