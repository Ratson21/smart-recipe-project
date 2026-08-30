# Smart Recipe 🍳

Progressive Web App yang merekomendasikan **resep masakan Indonesia berdasarkan bahan yang kamu punya**. Cukup ketik bahan ("ayam, bawang putih, tomat"), sistem memprosesnya dengan NLP berbasis **Sentence Transformer** dan merekomendasikan resep yang paling relevan **secara makna** - bukan sekadar pencocokan kata.

> Skripsi S1 Informatika - *Implementasi Hybrid Recommendation System dan Natural Language Processing pada Progressive Web App "Smart Recipe"*.

---

## ✨ Fitur

- **Smart search semantik** - pahami maksud bahan (mis. "daging unggas" -> resep ayam), bukan keyword matching.
- **Toleransi typo** - "ayma" otomatis dikoreksi jadi "ayam".
- **Rekomendasi terpersonalisasi** - makin akurat seiring kamu memberi rating & bookmark (hybrid scoring berbasis taste profile).
- **Halaman evaluasi** - Precision@5 / Recall@5 sistem pada 20 query, dengan baseline TF-IDF sebagai pembanding.
- **PWA** - bisa di-*install* dan dipakai seperti aplikasi.

---

## 🧱 Tech Stack

| Bagian | Teknologi |
|---|---|
| Backend | Python 3.11, FastAPI, Uvicorn, Motor (MongoDB async) |
| AI/NLP | `sentence-transformers` (`paraphrase-multilingual-MiniLM-L12-v2`), NumPy, scikit-learn (baseline TF-IDF) |
| Frontend | React 19, Vite, Tailwind CSS, Axios, React Router, vite-plugin-pwa |
| Database | MongoDB (lokal, port 27017) |

---

## ✅ Prasyarat

Pastikan sudah terpasang di komputer kamu:

- **Python 3.11**
- **Node.js 18+** dan npm
- **MongoDB** (jalan di `localhost:27017`)
  - macOS (Homebrew): `brew install mongodb-community && brew services start mongodb-community`
  - atau jalankan `mongod` secara manual

---

## 🚀 Cara Menjalankan

Aplikasi terdiri dari **2 bagian**: backend (port 8000) dan frontend (port 5173). Jalankan MongoDB lebih dulu, lalu backend, lalu frontend.

### 1. Clone repo

```bash
git clone git@github.com:Ratson21/smart-recipe-project.git
cd smart-recipe-project
```

### 2. Backend

```bash
cd backend

# buat virtual environment + install dependency
python3.11 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# buat file .env (lihat template di bawah)
```

Buat file `backend/.env` berisi:

```env
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=smart_recipe_db
JWT_SECRET=ganti-dengan-string-acak-yang-panjang
JWT_EXPIRE_DAYS=7
MODEL_NAME=paraphrase-multilingual-MiniLM-L12-v2
BACKEND_PORT=8000
```

> ⚠️ `.env` **tidak** ikut di-commit (berisi rahasia). Ganti `JWT_SECRET` dengan nilai acak.

### 3. Isi database (ETL) - sekali saja

Pastikan MongoDB sudah jalan, lalu dari folder `backend/`:

```bash
python scripts/etl_recipes.py        # load 14.945 resep dari CSV -> MongoDB
python scripts/verify_data.py        # (opsional) cek kualitas data
```

### 4. Jalankan backend

```bash
# dari folder backend/, venv aktif
uvicorn app.main:app --reload --port 8000
```

> ⏳ **Saat pertama dijalankan**, backend akan:
> 1. mengunduh model Sentence Transformer (~470 MB, sekali saja), lalu
> 2. meng-*encode* 14.945 resep menjadi vektor - ini bisa makan **beberapa menit**.
>
> Hasilnya disimpan ke `data/recipe_vectors.npy`, jadi proses ini **tidak diulang** di run berikutnya.

Cek backend siap: buka **http://localhost:8000/docs** (Swagger UI) atau **http://localhost:8000/health**.

### 5. Frontend

Buka terminal **baru**:

```bash
cd frontend
npm install
npm run dev
```

Buka **http://localhost:5173** di browser. 🎉

> Frontend memanggil API lewat proxy `/api` -> `http://localhost:8000`, jadi **backend harus jalan lebih dulu** di port 8000.

---

## 🧪 Menjalankan Test (backend)

```bash
cd backend
source venv/bin/activate
python -m pytest -q
```

---

## 📁 Struktur Singkat

```
smart-recipe/
├── backend/
│   ├── app/
│   │   ├── main.py            # entry point FastAPI
│   │   ├── core/              # config, database, security (JWT)
│   │   ├── models/            # schema Pydantic
│   │   ├── routes/            # endpoint API (/api/v1/*)
│   │   └── services/          # recommendation engine, weighted encoder
│   ├── scripts/              # ETL & utilitas data
│   ├── data/                # dataset (CSV) + vektor pra-hitung
│   ├── requirements.txt
│   └── tests/
└── frontend/
    ├── src/
    │   ├── pages/            # halaman (Home, Detail, Login, dsb.)
    │   ├── components/       # komponen UI
    │   ├── context/          # AuthContext
    │   └── api/axios.js      # instance Axios
    └── package.json
```

---

## 🔌 Endpoint Utama

Base URL: `http://localhost:8000/api/v1` - dokumentasi lengkap & interaktif di `/docs`.

| Method | Path | Keterangan |
|---|---|---|
| POST | `/recommendations/smart-search` | Pencarian cerdas berbasis bahan (inti AI) |
| GET | `/recommendations/similar/{id}` | Resep mirip |
| GET | `/recipes` · `/recipes/{id}` | Daftar & detail resep |
| POST | `/auth/register` · `/auth/login` | Registrasi & login (JWT) |
| POST | `/ratings` · `/bookmarks` | Rating & bookmark |
| GET | `/evaluation/metrics` | Metrik evaluasi (Precision@5 / Recall@5 + baseline TF-IDF) |

---

## 🛠️ Troubleshooting

- **Backend gagal connect MongoDB** -> pastikan `mongod` jalan di `localhost:27017`.
- **Hasil pencarian kosong / 503** -> database belum di-ETL; jalankan langkah **3**.
- **Run pertama lama** -> wajar, model sedang diunduh & vektor sedang di-*encode* (lihat langkah **4**).
- **Frontend error koneksi** -> pastikan backend jalan di port 8000 sebelum `npm run dev`.
