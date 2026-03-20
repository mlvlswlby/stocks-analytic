# Panduan Deployment All-in-One (Platform Gratis: Hugging Face Spaces)

Sesuai permintaan Anda, saya telah mengkofigurasi ulang agar **seluruh aplikasi Anda (Backend FastAPI & Tampilan Frontend/Web)** bisa dijalankan sekaligus dalam **1 platform**. 

Kita akan menggunakan **Hugging Face Spaces** yang 100% gratis, memiliki RAM sangat besar (16GB), tanpa batasan hari/jam tertentu, dan dirancang khusus untuk mengakomodasi aplikasi berbasis Python yang berat (seperti `yfinance` & `pandas`). Sistem akan berjalan menggunakan kerangka kerja `Docker`.

---

## Tahap 1: Membuat Ruang Server (Space)

1. Buat akun di **[huggingface.co](https://huggingface.co/join)**.
2. Setelah login, klik foto profil Anda di kanan atas -> pilih **New Space**.
3. Isi detail formulir pembuatan ruang server:
   - **Space name**: `stocks-analytic`
   - **License**: `mit` (atau bebas)
   - **Select the Space SDK**: Pilih **Docker** -> **Blank**.
   - **Space Hardware**: Free (2 vCPU - 16GB RAM).
   - **Visibility**: Public (agar aksesnya gratis).
4. Klik **Create Space**.

---

## Tahap 2: Menghubungkan GitHub ke Hugging Face (Piliha Salah Satu Cara)

Agar setiap kali Anda menge-push kode ke GitHub, aplikasi di Hugging Face otomatis diperbarui, lakukan salah satu dari cara berikut:

### Cara 1: Sinkronisasi Otomatis via GitHub Actions (Dianjurkan)
Dengan cara ini, GitHub akan bertugas menyalin kode Anda persis ke Hugging Face secara otomatis di latar belakang.

1. Buka akun **Hugging Face** Anda. Pergi ke **Settings -> Access Tokens**.
2. Buat Token baru (klik *New Token*), beri nama bebas (misal: "GithubDeploy"), lalu pilih **Role: Write**. *Copy token tersebut.*
3. Buka repository **GitHub** Anda di web, lalu masuk ke tab **Settings -> Secrets and variables -> Actions**.
4. Klik tombol **New repository secret**.
   - Kolom Name isi dengan: **`HF_TOKEN`**
   - Kolom Secret *Paste* Token dari Hugging Face tadi. Klik *Add secret*.
5. Buka kembali editor kode komputer Anda. Buka file `.github/workflows/huggingface.yml`.
6. Pada baris ke-20 terdapat baris:
   `run: git push --force https://USERNAME:$HF_TOKEN@huggingface.co/spaces/USERNAME/stocks-analytic main`
   ➜ Ubah kata `USERNAME` menjadi *username* Hugging Face Anda, dan pastikan `stocks-analytic` sesuai dengan nama *Space* Anda.
7. Simpan (Save) file tersebut! Kini setiap kali Anda men-*commit* dan nge-*push* kode ke Github, sistem otomatis akan mengerjakannya.

### Cara 2: Menyambungkan secara Manual via Terminal (Git Remote)
Bila Anda tidak ingin menggunakan sinkronisasi Token otomatis di atas, Anda bisa mem-push langsung dari komputer Anda ke Hugging Face menggunakan terminal.

1. Buka terminal proyek Anda dan ketikkan perintah berikut sekali saja untuk mendaftarkan Hugging Face:
   ```bash
   git remote add hf https://huggingface.co/spaces/USERNAME/stocks-analytic
   ```
   *(Ganti `USERNAME` dan `stocks-analytic` dengan detail Space Anda).*
2. Mulai saat ini, setiap Anda ingin mengunggah kode, Anda wajib mengetikkan perintah deploy ke Hugging face juga:
   - Ke Github: `git push origin main`
   - Ke Hugging Face: `git push hf main`
*(Anda cukup memasukkan kredensial akun HF Anda saat diminta oleh terminal).*

---

## Tahap 3: Akses Web Anda
1. Anda bisa melihat proses *build* aplikasinya (saat ia menginstal library) dengan mengklik tulisan "Building" di pojok kanan atas layar dashboard Hugging Face Anda.
2. Saat status berganti **Running** (bulat hijau), Web sudah aktif!
3. Jika Anda ingin membagikan Web ini sebagai sebuah situs *standalone* (terpisah dari layout web Hugging Face), klik opsi ("Titik tiga" di pojok kanan atas) dan pilih **Embed this Space** lalu klik kolom **Direct URL**.
   URL Anda akan berbentuk seperti: `https://username-stocks-analytic.hf.space`

Tautan inilah tempat di mana web frontend analisis saham Anda bisa diakses secara publik, dan di dalamnya semua pemanggilan data saham otomatis langsung terakses dalam 1 *server environment* yang 100% gratis!

