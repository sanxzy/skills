# Exploring Indo-Pacific Snakes (Full Episode) | World's Deadliest Snakes | Nat Geo Animals — sumber contoh transcript

## Identitas dan status

- Jenis: **penyuntingan transcript yang disediakan pengguna untuk contoh gaya**, bukan naskah original hasil riset menyeluruh.
- Penulis/penerbit video: **Nat Geo Animals**. Redaksi dan susunan sumber tetap menjadi dasar contoh; bukan karya yang diklaim dibuat sendiri oleh agen.
- Video: https://www.youtube.com/watch?v=WGvH11I6Rnk
- ID: `WGvH11I6Rnk`; bahasa sumber/output: **en**. Tidak dilakukan terjemahan baru.
- SHA-256 input: `0b287b1f19607149088e0990da835ee7e5d6787aef93311d4017d42969658438`.
- Metadata ekstraksi yang disediakan mencatat judul, kanal, dan durasi; bukan klaim pemeriksaan ulang halaman YouTube saat ini.
- Tanggal penyuntingan: **26 September 2026**.
- Genre: Dokumenter satwa dan perbandingan.
- Jumlah blok input: 135; hasil editorial lama: 129; hasil SRT manual: 611 cue (603 narasi, delapan `♪ ♪`); token kata narasi: 3542.
- Timeline terakhir: **44:06.632**; durasi metadata video: 2664.0 detik. Caption dapat sedikit melewati angka durasi metadata.

Untuk mempelajari contoh, baca [SRT bundled](which-snake-is-actually-the-most-dangerous-en.srt) bersama file ini. Identitas video dan hash input mencatat provenance historis; naskah dan catatan yang diperlukan tersedia di dalam bundle. Catatan pemeriksaan merekam pekerjaan saat penyuntingan pada tanggal di atas, bukan pemeriksaan baru pada saat skill digunakan.

## Sumber

| ID | Sumber | URL | Apa yang dibuktikan/dibaca |
| --- | --- | --- | --- |
| R00 | Video asli dan transcript lokal milik pengguna | https://www.youtube.com/watch?v=WGvH11I6Rnk | Seluruh berkas transcript diproses; urutan kata dan struktur diperiksa dari teks yang tersedia. Sumber ini membuktikan asal redaksi, bukan otomatis kebenaran seluruh klaim faktualnya. Tidak dilakukan pemeriksaan frame atau pengukuran audio baru. |
| R01 | Sneaky Snake Facts — Australian Venom Research Unit, University of Melbourne | https://biomedicalsciences.unimelb.edu.au/departments/department-of-biochemistry-and-pharmacology/engage/avru/blog/sneaky-snake-facts | Bagian anatomi rahang dibaca: tulang dan ligamen fleksibel memungkinkan peregangan, dengan gerak sisi kiri/kanan yang independen. Koreksi klaim rahang dilepas; bukan dukungan angka gigitan, dosis bisa atau prognosis medis dalam episode. |

## Penyuntingan dan timing

Metadata ekstraksi dikeluarkan dari naskah utama. Cue musik di tengah kalimat dan label suara/pembicara yang tidak diucapkan dipindahkan ke konteks sumber; interval musik tersendiri menggunakan `♪ ♪`. Kalimat yang terpotong pada batas caption disambungkan, paragraf panjang dibagi pada akhir kalimat, dan ejaan yang jelas dirapikan. Urutan gagasan, gaya narasi, pembuka, pengembangan dan penutup sumber dipertahankan; tidak diringkas menjadi artikel baru.

Seluruh 611 cue SRT ditulis dan diberi waktu secara manual; bukan hasil pemotongan atau retiming dengan kode. Ke-3.542 token narasi sama persis urutan katanya dengan arsip, delapan `♪ ♪` tetap tampak pada jendela musik semula. Di E031, awal cue 148 dimajukan **400 ms** dari awal jendela arsip (11:05.632 → 11:05.232) untuk mempertahankan semua 15 kata yang rapat tanpa melanggar kecepatan/overlap; ada jeda 4.166 detik dari narasi sebelumnya. Di E115, cue 513 dimajukan **100 ms** (37:46.166 → 37:46.066) karena tuntutan tiga cue yang rapat, dengan jeda sebelumnya lebih dari tiga detik. Keduanya perkiraan editorial, **bukan** pengukuran ulang audio. Short wildlife beats sengaja mengakhiri subtitle sebelum footage selesai; validasi hanya lulus dengan override archival `--max-unspoken-fraction 0.60` (24.5% tanpa ucapan; 106.4 WPM aktif). `ffprobe` membaca 611 paket SubRip. Setelah retiming manual, tidak ada baris >40 karakter, cue >80 karakter, atau peringatan CPS >15; ini masih bukan bukti kenyamanan playback/editor import. Jika direkam ulang, sinkronkan dengan suara baru.

## Catatan khusus

- Label pembicara NARRATOR/BOY dihapus, ucapan tetap ada. Bunyi tidak diubah menjadi dialog; cue musik berdiri sendiri menjadi ♪ ♪.
- Klaim rahang dilepas diperbaiki sesuai R01. Jumlah orang yang bisa dibunuh satu gigitan, prognosis antivenom, ukuran India, dan total kematian per spesies belum terverifikasi; beberapa tampak terlalu mutlak. Jangan menggunakannya untuk memberi informasi medis atau peringkat ilmiah tanpa riset sendiri.

**Batas verifikasi:** Peringkat adalah bingkai editorial episode, bukan indeks ilmiah universal. Angka gigitan/kematian, ekuivalensi dosis bisa, prognosis serta klaim antivenom memerlukan audit medis mandiri. Sumber tambahan, bila tercantum, hanya mendukung koreksi yang dijelaskan, bukan sertifikasi seluruh isi. Klaim yang masih mengikuti video adalah **belum diverifikasi mandiri**. Bacalah contoh untuk mempelajari penulisan; ketika menulis video baru, riset fakta kembali sesuai workflow skill.

## Perubahan redaksi yang dicatat

| Bagian sumber | Hasil penyuntingan |
| --- | --- |
| By detaching its lower jaw, the python can spread its mouth wider than its skull. | Flexible bones and ligaments allow the python to spread its mouth wider than its skull. |

## Pemetaan hasil ke transcript asal

Peta ini mencakup semua cue SRT 1–611 termasuk delapan musik; E031 dan E115 memiliki dua awal cue yang dimajukan secara editorial seperti dicatat di atas. `Tnnn` adalah blok input Markdown historis, bukan nomor SRT. Beberapa unit editorial menunjukkan rantai input yang sama. Baca SRT bundled dan catatan ini untuk redaksinya. Hash input hanya mencatat asal historis; tidak diperlukan berkas ekstraksi asli. Rentang video mencatat konteks audiovisual asal, bukan bukti bahwa footage sudah diperiksa ulang. Pemetaan **bukan** klaim bahwa setiap fakta sudah dikonfirmasi oleh sumber primer.

| Blok asal → cue SRT | Jendela editorial asal (MM:SS.mmm) | Blok input | Rentang input yang tercakup | Status |
| --- | --- | --- | --- | --- |
| E001 (cue 1–3) | 00:01.966–00:13.566 | T001 | 00:01.966–00:13.566 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E002 (cue 4–6) | 00:17.566–00:26.133 | T002 | 00:17.566–00:26.133 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E003 (cue 7–10) | 00:29.632–00:40.799 | T003 | 00:29.632–00:40.799 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E004 (cue 11) | 00:43.132–00:45.300 | T004 | 00:43.132–00:45.300 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E005 (cue 12–15) | 00:48.832–01:02.665 | T005 | 00:48.832–01:02.665 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E006 (cue 16) | 01:08.133–01:12.166 | T006 | 01:08.133–01:12.166 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E007 (cue 17–18) | 01:14.032–01:19.333 | T007 | 01:14.032–01:19.333 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E008 (cue 19, `♪ ♪`) | 01:21.032–01:24.865 | T008 | 01:21.032–01:24.865 | Musik/cue |
| E009 (cue 20–23) | 01:30.899–01:47.266 | T009 | 01:30.899–01:47.266 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E010 (cue 24–29) | 01:54.133–02:23.532 | T010 | 01:54.133–02:23.532 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E011 (cue 30) | 02:26.865–02:32.467 | T011 | 02:26.865–02:32.467 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E012 (cue 31–33) | 02:35.965–02:49.933 | T012 | 02:35.965–02:49.933 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E013 (cue 34–42) | 02:52.433–03:37.032 | T013 | 02:52.433–03:37.032 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E014 (cue 43–46) | 03:37.032–03:55.832 | T014 | 03:37.032–03:55.832 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E015 (cue 47, `♪ ♪`) | 04:01.999–04:10.166 | T015 | 04:01.999–04:10.166 | Musik/cue |
| E016 (cue 48–53) | 04:13.732–04:38.132 | T016 | 04:13.732–04:38.132 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E017 (cue 54) | 04:43.765–04:47.599 | T017 | 04:43.765–04:47.599 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E018 (cue 55–60) | 04:49.832–05:18.266 | T018 | 04:49.832–05:18.266 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E019 (cue 61–72) | 05:21.866–06:13.000 | T019, T020 | 05:21.866–06:13.000 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E020 (cue 73, `♪ ♪`) | 06:15.932–06:17.966 | T021 | 06:15.932–06:17.966 | Musik/cue |
| E021 (cue 74–75) | 06:20.699–06:27.899 | T022 | 06:20.699–06:27.899 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E022 (cue 76–84) | 06:30.732–06:56.133 | T023 | 06:30.732–06:56.133 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E023 (cue 85–92) | 06:57.965–07:26.467 | T024 | 06:57.965–07:26.467 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E024 (cue 93–111) | 07:28.799–08:33.193 | T025, T026, T027 | 07:28.799–08:57.266 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E025 (cue 112–118) | 08:33.193–08:57.266 | T025, T026, T027 | 07:28.799–08:57.266 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E026 (cue 119–128) | 08:58.966–09:30.400 | T028 | 08:58.966–09:30.400 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E027 (cue 129–140) | 09:33.799–10:18.333 | T029 | 09:33.799–10:18.333 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E028 (cue 141) | 10:18.333–10:24.566 | T030 | 10:18.333–10:24.566 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E029 (cue 142–146) | 10:29.132–10:49.132 | T031 | 10:29.132–10:49.132 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E030 (cue 147) | 10:56.132–11:01.066 | T032 | 10:56.132–11:01.066 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E031 (cue 148–150; cue 148 mulai 400 ms lebih awal) | 11:05.632–11:10.699 | T033 | 11:05.632–11:10.699 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E032 (cue 151–153) | 11:13.133–11:23.666 | T034 | 11:13.133–11:23.666 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E033 (cue 154–156) | 11:25.599–11:35.400 | T035 | 11:25.599–11:35.400 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E034 (cue 157–159) | 11:38.799–11:49.300 | T036 | 11:38.799–11:49.300 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E035 (cue 160) | 11:52.999–11:56.100 | T037 | 11:52.999–11:56.100 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E036 (cue 161–167) | 11:59.632–12:18.366 | T038 | 11:59.632–12:18.366 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E037 (cue 168–170) | 12:24.632–12:36.433 | T039 | 12:24.632–12:36.433 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E038 (cue 171–186) | 12:43.066–13:43.166 | T040, T041 | 12:43.066–13:43.166 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E039 (cue 187) | 13:44.999–13:53.466 | T042 | 13:44.999–13:53.466 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E040 (cue 188–190) | 14:07.300–14:14.367 | T043 | 14:07.300–14:14.367 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E041 (cue 191–192) | 14:16.598–14:28.999 | T044, T045 | 14:16.598–14:28.999 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E042 (cue 193–204) | 14:35.333–15:20.099 | T046 | 14:35.333–15:20.099 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E043 (cue 205–216) | 15:20.099–15:57.599 | T047 | 15:20.099–15:57.599 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E044 (cue 217–222) | 15:59.199–16:21.566 | T048 | 15:59.199–16:21.566 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E045 (cue 223–228) | 16:25.698–16:43.599 | T049 | 16:25.698–16:43.599 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E046 (cue 229–232) | 16:47.033–17:04.666 | T050 | 16:47.033–17:04.666 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E047 (cue 233–237) | 17:06.299–17:21.532 | T051 | 17:06.299–17:21.532 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E048 (cue 238–239) | 17:24.932–17:36.500 | T052 | 17:24.932–17:36.500 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E049 (cue 240–243) | 17:40.099–17:51.966 | T053 | 17:40.099–17:51.966 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E050 (cue 244–246) | 18:05.732–18:17.166 | T054 | 18:05.732–18:17.166 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E051 (cue 247) | 18:23.932–18:30.933 | T055 | 18:23.932–18:30.933 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E052 (cue 248–252) | 18:33.332–18:46.500 | T056 | 18:33.332–18:46.500 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E053 (cue 253–256) | 18:48.632–19:10.166 | T057 | 18:48.632–19:10.166 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E054 (cue 257–263) | 19:14.433–19:35.966 | T058 | 19:14.433–19:35.966 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E055 (cue 264–267) | 19:39.233–19:49.500 | T059 | 19:39.233–19:49.500 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E056 (cue 268–270) | 19:53.566–20:04.565 | T060 | 19:53.566–20:04.565 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E057 (cue 271–277) | 20:10.765–20:36.066 | T061 | 20:10.765–20:36.066 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E058 (cue 278) | 20:56.199–21:00.733 | T062 | 20:56.199–21:00.733 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E059 (cue 279, `♪ ♪`) | 21:03.333–21:08.100 | T063 | 21:03.333–21:08.100 | Musik/cue |
| E060 (cue 280–291) | 21:11.933–21:49.665 | T064 | 21:11.933–21:49.665 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E061 (cue 292–304) | 21:55.565–22:33.966 | T065 | 21:55.565–22:33.966 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E062 (cue 305–308) | 22:38.233–22:54.467 | T066 | 22:38.233–22:54.467 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E063 (cue 309–310) | 22:56.799–23:04.032 | T067 | 22:56.799–23:04.032 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E064 (cue 311) | 23:08.999–23:11.799 | T068 | 23:08.999–23:11.799 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E065 (cue 312–316) | 23:15.332–23:34.032 | T069 | 23:15.332–23:34.032 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E066 (cue 317–319) | 23:41.033–23:49.233 | T070 | 23:41.033–23:49.233 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E067 (cue 320, `♪ ♪`) | 23:52.400–23:54.833 | T071 | 23:52.400–23:54.833 | Musik/cue |
| E068 (cue 321, `♪ ♪`) | 23:58.433–24:00.367 | T072 | 23:58.433–24:00.367 | Musik/cue |
| E069 (cue 322–328) | 24:03.532–24:22.599 | T073 | 24:03.532–24:22.599 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E070 (cue 329) | 24:25.532–24:30.666 | T074 | 24:25.532–24:30.666 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E071 (cue 330–342) | 24:33.933–25:17.500 | T075 | 24:33.933–25:17.500 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E072 (cue 343–355) | 25:17.500–26:01.367 | T076 | 25:17.500–26:01.367 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E073 (cue 356–358) | 26:04.499–26:13.699 | T077 | 26:04.499–26:13.699 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E074 (cue 359–360) | 26:17.366–26:22.933 | T078 | 26:17.366–26:22.933 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E075 (cue 361, `♪ ♪`) | 26:33.299–26:35.732 | T079 | 26:33.299–26:35.732 | Musik/cue |
| E076 (cue 362–363) | 26:40.932–26:45.500 | T080 | 26:40.932–26:45.500 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E077 (cue 364–365) | 26:48.799–26:55.100 | T081 | 26:48.799–26:55.100 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E078 (cue 366–367) | 26:57.466–27:04.532 | T082 | 26:57.466–27:04.532 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E079 (cue 368–369) | 27:06.299–27:19.433 | T083 | 27:06.299–27:19.433 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E080 (cue 370–376) | 27:32.466–28:03.100 | T084 | 27:32.466–28:03.100 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E081 (cue 377–380) | 28:05.699–28:15.966 | T085 | 28:05.699–28:15.966 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E082 (cue 381) | 28:19.865–28:27.266 | T086 | 28:19.865–28:27.266 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E083 (cue 382–385) | 28:39.032–28:57.466 | T087 | 28:39.032–28:57.466 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E084 (cue 386–388) | 29:03.965–29:13.899 | T088 | 29:03.965–29:13.899 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E085 (cue 389–390) | 29:20.032–29:24.266 | T089 | 29:20.032–29:24.266 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E086 (cue 391–392) | 29:27.099–29:31.200 | T090 | 29:27.099–29:31.200 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E087 (cue 393–395) | 29:33.300–29:42.966 | T091 | 29:33.300–29:42.966 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E088 (cue 396–400) | 29:46.032–30:03.866 | T092 | 29:46.032–30:03.866 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E089 (cue 401–402) | 30:05.598–30:14.466 | T093 | 30:05.598–30:14.466 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E090 (cue 403–404) | 30:21.366–30:26.733 | T094 | 30:21.366–30:26.733 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E091 (cue 405–406) | 30:28.832–30:36.066 | T095 | 30:28.832–30:36.066 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E092 (cue 407–416) | 30:39.166–31:13.233 | T096 | 30:39.166–31:13.233 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E093 (cue 417–418) | 31:16.199–31:23.699 | T097 | 31:16.199–31:23.699 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E094 (cue 419–425) | 31:25.400–31:45.632 | T098 | 31:25.400–31:45.632 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E095 (cue 426–430) | 31:48.899–32:06.500 | T099 | 31:48.899–32:06.500 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E096 (cue 431–432) | 32:08.865–32:12.400 | T100 | 32:08.865–32:12.400 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E097 (cue 433–436) | 32:14.166–32:27.166 | T101 | 32:14.166–32:27.166 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E098 (cue 437–438) | 32:31.199–32:36.866 | T102 | 32:31.199–32:36.866 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E099 (cue 439–441) | 32:39.698–32:49.099 | T103 | 32:39.698–32:49.099 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E100 (cue 442–443) | 32:54.765–33:00.500 | T104 | 32:54.765–33:00.500 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E101 (cue 444–450) | 33:04.798–33:32.899 | T105 | 33:04.798–33:32.899 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E102 (cue 451–456) | 33:39.032–34:09.166 | T106 | 33:39.032–34:09.166 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E103 (cue 457–459) | 34:12.665–34:20.333 | T107 | 34:12.665–34:20.333 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E104 (cue 460, `♪ ♪`) | 34:22.666–34:25.666 | T108 | 34:22.666–34:25.666 | Musik/cue |
| E105 (cue 461–464) | 34:28.133–34:38.000 | T109 | 34:28.133–34:38.000 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E106 (cue 465–477) | 34:40.999–35:18.100 | T110 | 34:40.999–35:18.100 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E107 (cue 478–484) | 35:20.299–35:39.066 | T111 | 35:20.299–35:39.066 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E108 (cue 485–486) | 35:41.899–35:46.000 | T112 | 35:41.899–35:46.000 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E109 (cue 487–490) | 35:48.599–35:59.000 | T113 | 35:48.599–35:59.000 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E110 (cue 491–492) | 36:02.933–36:08.599 | T114 | 36:02.933–36:08.599 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E111 (cue 493–494) | 36:10.732–36:17.166 | T115 | 36:10.732–36:17.166 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E112 (cue 495–496) | 36:20.699–36:29.099 | T116 | 36:20.699–36:29.099 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E113 (cue 497–502) | 36:34.132–36:55.399 | T117 | 36:34.132–36:55.399 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E114 (cue 503–512) | 37:01.299–37:46.166 | T118 | 37:01.299–37:46.166 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E115 (cue 513–526; cue 513 mulai 100 ms lebih awal) | 37:46.166–38:33.599 | T119, T120 | 37:46.166–38:33.599 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E116 (cue 527–528) | 38:37.765–38:45.433 | T121 | 38:37.765–38:45.433 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E117 (cue 529) | 38:48.665–38:52.532 | T122 | 38:48.665–38:52.532 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E118 (cue 530–537) | 38:54.532–39:22.833 | T123 | 38:54.532–39:22.833 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E119 (cue 538–545) | 39:25.066–39:54.766 | T124 | 39:25.066–39:54.766 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E120 (cue 546–552) | 39:58.332–40:16.733 | T125 | 39:58.332–40:16.733 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E121 (cue 553) | 40:18.799–40:26.100 | T126 | 40:18.799–40:26.100 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E122 (cue 554–562) | 40:27.732–40:57.433 | T127 | 40:27.732–40:57.433 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E123 (cue 563–564) | 40:59.333–41:08.699 | T128 | 40:59.333–41:08.699 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E124 (cue 565–571) | 41:10.932–41:29.666 | T129 | 41:10.932–41:29.666 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E125 (cue 572–581) | 41:31.399–42:11.333 | T130 | 41:31.399–42:11.333 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E126 (cue 582) | 42:17.932–42:19.467 | T131 | 42:17.932–42:19.467 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E127 (cue 583–596) | 42:23.299–43:09.966 | T132, T133 | 42:23.299–43:09.966 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E128 (cue 597–608) | 43:14.898–43:51.033 | T134 | 43:14.898–43:51.033 | Redaksi bersumber R00; koreksi terbatas lihat catatan |
| E129 (cue 609–611) | 43:53.500–44:06.632 | T135 | 43:53.500–44:06.632 | Redaksi bersumber R00; koreksi terbatas lihat catatan |

## Penggunaan sebagai contoh

Pola yang bisa dipelajari: **Perbandingan bahaya melalui kemampuan ular, paparan manusia dan akses pertolongan.** Fokus pada urutan kejadian/gagasan, hubungan antarkalimat, detail yang bisa divisualkan, dan ruang bagi gambar. Jangan menyalin nama kanal, identitas pembicara, kalimat khas, fakta, atau timecode secara mekanis ke karya baru.

## Pemeriksaan akhir

Setiap cue 1–611 terpetakan ke 129 unit asal; delapan cue musik punya waktu yang persis sama dengan sumber. Semua cue narasi kecuali dua awal terdokumentasi E031/E115 berada dalam jendela editorialnya. Validator memeriksa nomor/timecode/format SubRip, maksimal dua baris dan satu kalimat, tanpa tumpang tindih/metadata/URL. Tes dan angka CPS bukan uji layar sesungguhnya, bukan bukti impor editor, bukan pengesahan angka kematian/bisa, prognosis maupun pedoman medis.

## Title and thumbnail concept

- Selected editorial title: **Which Snake Is Actually the Most Dangerous?**. Original brief/video titles remain recorded for provenance.
- Audience: Viewers interested in wildlife risk and comparisons
- Curiosity loop: Venom alone does not settle practical danger.
- Script payoff: Compare the episode’s criteria, exposure, and outcomes without claiming a universal scientific ranking.
- Proposed thumbnail: One or two identifiable snakes; avoid a fake strike or exaggerated size. This is an asset concept, not a supplied or generated image.
- Performance status: untested editorial candidate. No comparative outlier data, reach/views results, or audience-test results were supplied; this title is not claimed to be a proven winner.
