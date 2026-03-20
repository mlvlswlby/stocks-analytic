# Panduan Deployment All-in-One (Platform Gratis: Hugging Face Spaces)

Sesuai permintaan Anda, saya telah mengkofigurasi ulang agar **seluruh aplikasi Anda (Backend FastAPI & Tampilan Frontend/Web)** bisa dijalankan sekaligus dalam **1 platform**. 

Kita akan menggunakan **Hugging Face Spaces** yang 100% gratis, memiliki RAM sangat besar (16GB), tanpa batasan hari/jam tertentu, dan dirancang khusus untuk mengakomodasi aplikasi berbasis Python yang berat (seperti `yfinance` & `pandas`). Sistem akan berjalan menggunakan kerangka kerja `Docker`.

---

## Tahap 1: Deploy Aplikasi 

Karena kode *Frontend* saat ini sudah dideteksi secara otomatis dan di-*serve* oleh *Backend* (cek `backend/main.py`), maka Anda hanya perlu melakukan deploy ke satu tempat saja:

1. Buat akun di **[huggingface.co](https://huggingface.co/join)**.
2. Setelah login, klik foto profil Anda di kanan atas -> pilih **New Space**.
3. Isi detail formulir pembuatan ruang server:
   - **Space name**: `stocks-analytic`
   - **License**: `mit` (atau bebas)
   - **Select the Space SDK**: Pilih **Docker** -> **Blank**.
   - **Space Hardware**: Free (2 vCPU - 16GB RAM).
   - **Visibility**: Public (agar aksesnya gratis).
4. Klik **Create Space**.
5. Di halaman server (*Space*) Anda, klik tab **Files**, lalu klik **Add file** -> **Upload files**.
6. **Penting:** Unggah SELURUH struktur proyek ini dari komputer Anda (semua folder: `backend`, `frontend`, dan file `Dockerfile`, `requirements.txt`).
7. Setelah menekan *Commit* pada kotak di bawah (untuk mengonfirmasi unggahan), komputer awan Hugging Face akan secara otomatis membaca `Dockerfile` Anda dan mulai men-*setup* server (Anda bisa mengklik tulisan "Building" di pojok kanan atas untuk melihat prosess *install* `pandas` dll).
8. Setelah statusnya **Running** (bulat hijau), aplikasi web Anda dan API-nya semuanya sudah siap digunakan! 

## Tahap 2: Akses Web Anda
1. Anda bisa langsung menikmati tampilannya yang terpasang di *dashboard* Hugging Face.
2. Jika Anda ingin membagikan Web ini sebagai sebuah situs *standalone* (terpisah dari layout Hugging Face), klik tombol opsi ("Titik tiga" di pojok kanan atas) dan pilih **Embed this Space** lalu klik kolom **Direct URL**.
   URL Anda akan berbentuk seperti: `https://username-stocks-analytic.hf.space`

Tautan inilah tempat di mana web frontend analisis saham Anda bisa diakses secara publik, dan di dalamnya semua pemanggilan data saham otomatis langsung terakses dalam 1 *server environment* yang sama!
