"""Daftar konstituen LQ45 — saham paling likuid di Bursa Efek Indonesia.

Sumber: Wikipedia Indonesia (`id.wikipedia.org/wiki/Indeks_LQ45`)
  Halaman per 3 Juli 2026, periode "Efektif Mei-Juli 2026".

PERINGATAN — ini sumber SEKUNDER, BUKAN publikasi resmi IDX.
IDX (idx.co.id) tidak menyediakan API publik (terverifikasi 403 di Sesi 28 & 35).
Daftar ini WAJIB diverifikasi ulang setiap evaluasi LQ45 6-bulanan
(Februari & Agustus). Update berikutnya ~Agustus 2026.

Setiap entri: (kode_IDX, nama_perusahaan, sektor, kode_Yahoo)
Sektor diisi manual dari publikasi IDX / referensi terbuka.
"""
from __future__ import annotations

LQ45_CONSTITUENTS: list[tuple[str, str, str | None, str]] = [
    ("AADI",  "Adaro Andalan Indonesia Tbk.",          "Energi",          "AADI.JK"),
    ("ADMR",  "Alamtri Minerals Indonesia Tbk.",        "Energi",          "ADMR.JK"),
    ("ADRO",  "Alamtri Resources Indonesia Tbk.",       "Energi",          "ADRO.JK"),
    ("AKRA",  "AKR Corporindo Tbk.",                   "Energi",          "AKRA.JK"),
    ("AMMN",  "Amman Mineral Internasional Tbk.",       "Energi",          "AMMN.JK"),
    ("AMRT",  "Sumber Alfaria Trijaya Tbk.",            "Consumer Cyclicals", "AMRT.JK"),
    ("ANTM",  "Aneka Tambang Tbk.",                     "Bahan Baku",      "ANTM.JK"),
    ("ASII",  "Astra International Tbk.",               "Consumer Cyclicals", "ASII.JK"),
    ("BBCA",  "Bank Central Asia Tbk.",                 "Keuangan",        "BBCA.JK"),
    ("BBNI",  "Bank Negara Indonesia (Persero) Tbk.",   "Keuangan",        "BBNI.JK"),
    ("BBRI",  "Bank Rakyat Indonesia (Persero) Tbk.",   "Keuangan",        "BBRI.JK"),
    ("BBTN",  "Bank Tabungan Negara (Persero) Tbk.",    "Keuangan",        "BBTN.JK"),
    ("BMRI",  "Bank Mandiri (Persero) Tbk.",            "Keuangan",        "BMRI.JK"),
    ("BRPT",  "Barito Pacific Tbk.",                   "Energi",          "BRPT.JK"),
    ("BUMI",  "Bumi Resources Tbk.",                    "Energi",          "BUMI.JK"),
    ("CPIN",  "Charoen Pokphand Indonesia Tbk.",        "Consumer Non-Cyclicals", "CPIN.JK"),
    ("CUAN",  "Petrindo Jaya Kreasi Tbk.",              "Energi",          "CUAN.JK"),
    ("DEWA",  "Darma Henwa Tbk.",                       "Energi",          "DEWA.JK"),
    ("EMTK",  "Elang Mahkota Teknologi Tbk.",           "Teknologi",       "EMTK.JK"),
    ("ESSA",  "ESSA Industries Indonesia Tbk.",         "Energi",          "ESSA.JK"),
    ("EXCL",  "XLSMART Telecom Sejahtera Tbk.",         "Telekomunikasi",  "EXCL.JK"),
    ("GOTO",  "GoTo Gojek Tokopedia Tbk.",              "Teknologi",       "GOTO.JK"),
    ("HRTA",  "Hartadinata Abadi Tbk.",                 "Consumer Cyclicals", "HRTA.JK"),
    ("ICBP",  "Indofood CBP Sukses Makmur Tbk.",        "Consumer Non-Cyclicals", "ICBP.JK"),
    ("INCO",  "Vale Indonesia Tbk.",                    "Bahan Baku",      "INCO.JK"),
    ("INDF",  "Indofood Sukses Makmur Tbk.",            "Consumer Non-Cyclicals", "INDF.JK"),
    ("INKP",  "Indah Kiat Pulp & Paper Tbk.",           "Bahan Baku",      "INKP.JK"),
    ("ISAT",  "Indosat Ooredoo Hutchison Tbk.",          "Telekomunikasi",  "ISAT.JK"),
    ("ITMG",  "Indo Tambangraya Megah Tbk.",            "Energi",          "ITMG.JK"),
    ("JPFA",  "Japfa Comfeed Indonesia Tbk.",           "Consumer Non-Cyclicals", "JPFA.JK"),
    ("KLBF",  "Kalbe Farma Tbk.",                       "Kesehatan",       "KLBF.JK"),
    ("MAPI",  "Mitra Adiperkasa Tbk.",                  "Consumer Cyclicals", "MAPI.JK"),
    ("MBMA",  "Merdeka Battery Materials Tbk.",          "Bahan Baku",      "MBMA.JK"),
    ("MDKA",  "Merdeka Copper Gold Tbk.",               "Bahan Baku",      "MDKA.JK"),
    ("MEDC",  "Medco Energi Internasional Tbk.",         "Energi",          "MEDC.JK"),
    ("PGAS",  "Pertamina Gas Negara Tbk.",              "Energi",          "PGAS.JK"),
    ("PGEO",  "Pertamina Geothermal Energy Tbk.",        "Energi",          "PGEO.JK"),
    ("PTBA",  "Bukit Asam Tbk.",                        "Energi",          "PTBA.JK"),
    ("SCMA",  "Surya Citra Media Tbk.",                 "Teknologi",       "SCMA.JK"),
    ("SMGR",  "Semen Indonesia (Persero) Tbk.",          "Bahan Baku",      "SMGR.JK"),
    ("TLKM",  "Telkom Indonesia (Persero) Tbk.",         "Telekomunikasi",  "TLKM.JK"),
    ("TOWR",  "Sarana Menara Nusantara Tbk.",            "Telekomunikasi",  "TOWR.JK"),
    ("UNTR",  "United Tractors Tbk.",                    "Energi",          "UNTR.JK"),
    ("UNVR",  "Unilever Indonesia Tbk.",                 "Consumer Non-Cyclicals", "UNVR.JK"),
    ("WIFI",  "Solusi Sinergi Digital Tbk.",             "Teknologi",       "WIFI.JK"),
]
