# Panduan Deployment (Full di Netlify)

Sesuai permintaan Anda, aplikasi ini telah dikonfigurasi ulang agar **Frontend dan Backend dapat di-deploy sekaligus dalam satu tempat** di Netlify, memanfaatkan fitur *Netlify Serverless Functions*. Adapter yang digunakan untuk menghubungkan FastAPI dengan server API Netlify adalah `Mangum`.

> **PERINGATAN BATASAN NETLIFY** ⚠️  
> Netlify memiliki batasan ketat untuk *Serverless Functions* di akun gratis, yaitu **ukuran file kompresi maksimal 50MB** dan **timeout eksekusi 10 detik**.  
> Berhubung aplikasi analisis saham Anda menggunakan pustaka komputasi berat (`pandas`, `numpy`, `scipy`) dan sistem unduh riwayat saham (`yfinance`), ukuran total fungsinya bisa melampaui batasan ini dan *timeout* saat mengambil data saham hingga 5 tahun ke belakang. Jika proses *deploy* gagal atau *API error timeout* ketika Anda mengakses website, hal tersebut murni karena limitasi *free tier* Netlify. Maka disarankan kembali ke arsitektur sebelumnya (Backend di platform Render/Railway/VPS).

---

## Tahap 1: Deploy ke Netlify

1. Commit dan Push seluruh perubahan baru ini ke akun **GitHub** Anda. Pastikan folder `functions/` masuk.
2. Buka [Netlify.com](https://netlify.com) dan login dengan akun GitHub Anda.
3. Klik menu **Add new site** > **Import an existing project**.
4. Pilih provider **GitHub** dan berikan izin jika diminta.
5. Pilih repository `stocks-analytic` milik Anda.
6. Pada halaman *Site settings*, biarkan semuanya *default* karena file `netlify.toml` di dalam repository sudah mengatur semuanya secara otomatis:
   - **Base directory**: (kosongkan)
   - **Build command**: `pip install -r requirements.txt -t functions`
   - **Publish directory**: `frontend`
   - **Functions directory**: `functions`
7. Klik **Deploy site**.

## Tahap 2: Menunggu Siklus Build (Kompilasi)

1. Proses kompilasi akan otomatis berjalan. Netlify akan mulai mengunduh semua pustaka dari `requirements.txt` ke dalam folder functions.
2. Tunggu proses kompilasi selesai (mungkin memakan waktu sekitar 2-3 menit untuk mengemas `pandas`).
3. Netlify akan memberikan URL aplikasinya jika sudah selesai (contoh: `https://my-stock-analyzer.netlify.app`).
4. **Selesai!** Jika serverless function mulus dan tidak terpotong batasan *size limit*, aplikasi penuh (Tampilan + API Data Saham) akan dapat diakses dari satu URL saja. Selamat mencoba!
