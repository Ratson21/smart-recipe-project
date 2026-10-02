# Smart Recipe

Aplikasi web (PWA) rekomendasi resep masakan Indonesia berdasarkan bahan yang dimiliki. Backend FastAPI + MongoDB, frontend React + Vite.

## Yang dibutuhkan

- Python 3.11
- Node.js 18+ dan npm
- MongoDB berjalan di `localhost:27017`

MongoDB di macOS:

```bash
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community
```

## Menjalankan

### 1. Clone

```bash
git clone https://github.com/Ratson21/smart-recipe-project.git
cd smart-recipe-project
```

### 2. Backend

```bash
cd backend
python3.11 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Buat file `backend/.env`:

```env
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=smart_recipe_db
JWT_SECRET=isi-dengan-string-acak
JWT_EXPIRE_DAYS=7
MODEL_NAME=paraphrase-multilingual-MiniLM-L12-v2
BACKEND_PORT=8000
```

Isi database dengan resep dari CSV (cukup sekali, dijalankan dari folder `backend/`):

```bash
python scripts/etl_recipes.py
```

Jalankan server:

```bash
uvicorn app.main:app --reload --port 8000
```

Saat pertama kali jalan, server mengunduh model (~470 MB) dan membuat vektor untuk semua resep, jadi bisa makan beberapa menit. Vektor disimpan di `backend/data/recipe_vectors.npy` dan tidak dibuat ulang di run berikutnya. Server siap kalau http://localhost:8000/health merespons.

### 3. Frontend

Di terminal baru:

```bash
cd frontend
npm install
npm run dev
```

Buka http://localhost:5173. Backend harus sudah jalan di port 8000, karena request `/api` di-proxy ke sana.

## Test (opsional)

```bash
cd backend
source venv/bin/activate
python -m pytest -q
```

## Masalah umum

- Backend gagal start dengan error koneksi: MongoDB belum jalan.
- Hasil pencarian kosong atau error 503: langkah ETL belum dijalankan.
- Frontend tidak bisa ambil data: backend belum jalan di port 8000.
