# 🍃 MongoDB Atlas - Adım Adım Kurulum Rehberi

Bu rehber, CookWise projesi için MongoDB Atlas (bulut veritabanı) kurulumunu anlatır.

---

## 📌 Ne Yapacaksınız?

1. MongoDB Atlas hesabı açıp cluster oluşturacaksınız
2. Veritabanı kullanıcısı ve şifre tanımlayacaksınız
3. Bilgisayarınızın IP adresine erişim izni vereceksiniz
4. Bağlantı adresini `.env` dosyasına yazacaksınız
5. Örnek verileri (kategori + ürün) yükleyeceksiniz

---

## 1️⃣ Atlas Hesabı ve Cluster Oluşturma

### 1.1 Kayıt / Giriş
- **https://cloud.mongodb.com** adresine gidin
- Google veya e-posta ile ücretsiz hesap açın
- Giriş yapın

### 1.2 Yeni Proje
- **"New Project"** → Proje adı: `CookWise` → **Create**

### 1.3 Cluster Oluşturma
- **"Build a Database"** tıklayın
- **M0 FREE** (Shared) planını seçin (ücretsiz)
- Cloud sağlayıcı ve bölge: **AWS** ve size en yakın bölge (örn: `eu-central-1`)
- **Create Cluster** → 1–2 dakika bekleyin

---

## 2️⃣ Kullanıcı ve Şifre Oluşturma

Cluster hazır olunca:

1. **"Database Access"** (sol menü) → **"Add New Database User"**
2. **Authentication Method:** Password
3. **Username:** `cookwise_user` (veya istediğiniz bir isim)
4. **Password:** Güçlü bir şifre (en az 8 karakter, büyük/küçük harf, rakam)
   - İsterseniz **Autogenerate Secure Password** ile otomatik üretin
   - **Şifreyi mutlaka not edin** – `.env` dosyasında kullanacaksınız
5. **Database User Privileges:** `Read and write to any database`
6. **Add User**

---

## 3️⃣ IP Erişim İzni (IP Access List)

Atlas, sadece izin verdiğiniz IP’lerden bağlantı kabul eder.

### 3.1 Bilgisayarınızın IP’sini Öğrenin
- Tarayıcıda **https://whatismyip.com** veya **https://ifconfig.me** açın
- IPv4 adresinizi not edin (örn: `88.238.9.21`)

### 3.2 Atlas’ta IP Ekleme
1. **"Network Access"** (sol menü) → **"Add IP Address"**
2. **"Add Current IP Address"** ile otomatik ekleyebilirsiniz
   - Veya manuel: IP’nizi yazın, sonuna `/32` ekleyin (örn: `88.238.9.21/32`)
3. **Confirm**
4. **Geliştirme için geçici:** Tüm IP’lere izin vermek isterseniz `0.0.0.0/0` kullanın (sadece test amaçlı)

---

## 4️⃣ Bağlantı Adresini (Connection String) Alma

1. Ana sayfada cluster’ınızı görün
2. **"Connect"** butonuna tıklayın
3. **"Drivers"** seçin (uygulama ile bağlan)
4. **Driver:** Python, **Version:** 3.12 veya uyumlu
5. Aşağıdaki metni kopyalayın (şifre kısmı `<password>` olarak görünecek):

```
mongodb+srv://cookwise_user:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
```

### 4.1 Şifreyi Yerleştirin
- `<password>` kısmını kendi şifrenizle değiştirin
- Şifrede `@`, `#`, `$` gibi özel karakterler varsa **URL encode** edin:
  - `@` → `%40`
  - `#` → `%23`
  - `$` → `%24`
  - vb.

### 4.2 Veritabanı Adını Ekleyin (Opsiyonel)
Bağlantı string’ine veritabanı adını ekleyebilirsiniz:

```
mongodb+srv://cookwise_user:ŞİFRENİZ@cluster0.xxxxx.mongodb.net/cookwise?retryWrites=true&w=majority&appName=Cluster0
```

---

## 5️⃣ .env Dosyasını Güncelleme

Proje klasöründe `.env` dosyasını açın ve şu satırları güncelleyin:

```env
# MongoDB Atlas bağlantı adresi (kendi cluster adresinizi yazın)
MONGODB_URL=mongodb+srv://cookwise_user:SİFRENİZ@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0

# Veritabanı adı
MONGODB_DB=cookwise
```

- `cluster0.xxxxx` kısmını kendi cluster adresinizle değiştirin
- `SİFRENİZ` kısmını gerçek şifrenizle değiştirin

---

## 6️⃣ DNS Sorunu Yaşarsanız

Hata: *"The resolution lifetime expired"* veya *"DNS operation timed out"*

### Olası Nedenler
- Yerel DNS sunucunuz MongoDB Atlas SRV kayıtlarını çözümleyemiyor
- Ağ (VPN, hotspot, kurumsal ağ) DNS’i engelliyor olabilir

### Çözümler

**A) DNS’i Değiştirin**
- Windows: Ayarlar → Ağ → DNS → `8.8.8.8` (Google) veya `1.1.1.1` (Cloudflare)

**B) `serverSelectionTimeoutMS` Süresini Artırın**
- `app/core/database.py` içinde `serverSelectionTimeoutMS=2000` değerini `10000` (10 saniye) yapın

**C) SRV Yerine Doğrudan Host Kullanın**
- Atlas → Connect → Drivers → Python
- Bazen “Use a connection string without SRV” veya benzeri seçenek olur
- Veya [Cluster Overview] → **Connect** → **Connect your application** → **Drivers** altında bazen hem SRV hem de standart format gösterilir
- Standart format: `mongodb://cluster0-shard-00-00.xxxxx.mongodb.net:27017,...` gibi bir adres olabilir (Atlas arayüzünden kontrol edin)

---

## 7️⃣ Bağlantıyı Test Etme

### Terminal’den
```bash
# venv aktif olsun
source venv/Scripts/activate   # Windows Git Bash
# veya: venv\Scripts\activate  # Windows CMD

# Bağlantı testi
python -c "
from pymongo import MongoClient
from app.core.config import settings
client = MongoClient(settings.MONGODB_URL, serverSelectionTimeoutMS=5000)
client.admin.command('ping')
print('✅ MongoDB bağlantısı başarılı!')
"
```

Başarılı ise `✅ MongoDB bağlantısı başarılı!` göreceksiniz.

---

## 8️⃣ Örnek Verileri Yükleme (Seed Data)

Bağlantı çalışıyorsa:

```bash
python scripts/seed_data.py
```

Bu script:
- **5 kategori** ekler (Meyve & Sebze, İçecek, Atıştırmalık, Temizlik, Süt Ürünleri)
- **19 ürün** ekler (domates, su, çikolata vb.)

Çıktı örneği:
```
==================================================
CookWise - Seed Data
==================================================
DB: cookwise

1. Kategoriler
   [ok] Kategori eklendi: Meyve & Sebze (meyve-sebze)
   ...

2. Ürünler
   [ok] Ürün eklendi: Domates 1 kg (19.99 TL)
   ...

==================================================
Seed tamamlandı.
==================================================
```

Aynı script’i birden fazla kez çalıştırabilirsiniz; aynı `slug` varsa tekrar eklenmez.

---

## 9️⃣ Uygulamayı Başlatma

```bash
source venv/Scripts/activate
uvicorn app.main:app --reload
```

Başarılı bağlantıda log’da şunu görmelisiniz:
```
📡 MongoDB'ye bağlanılıyor...
✅ MongoDB bağlantısı başarılı!
```

---

## 📋 Özet Kontrol Listesi

| Adım | Yapıldı mı? |
|------|-------------|
| Atlas hesabı + cluster oluşturuldu | ☐ |
| DB kullanıcısı (örn: cookwise_user) oluşturuldu | ☐ |
| IP Access List’e IP eklendi | ☐ |
| Connection string kopyalandı | ☐ |
| Şifre connection string’e yazıldı | ☐ |
| .env dosyası güncellendi | ☐ |
| Bağlantı testi başarılı | ☐ |
| seed_data.py çalıştırıldı | ☐ |

---

## 🔒 Güvenlik Notları

- `.env` dosyasını asla Git’e eklemeyin (`.gitignore`’da olmalı)
- Şifreleri kod içine yazmayın
- Production’da `0.0.0.0/0` IP iznini kullanmayın; sadece sunucu IP’sini ekleyin
