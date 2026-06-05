# Firebase ile Kullanıcı Yönetimi Kurulumu

CookWise projesinde kullanıcıları Firebase'de tutmak için adımlar.

---

## 1. Firebase Projesi Oluşturma

1. [Firebase Console](https://console.firebase.google.com/) → **Add project**
2. Proje adı verin (örn: `cookwise`)
3. Google Analytics isteğe bağlı
4. **Create project**

---

## 2. Authentication Etkinleştirme

1. Sol menü **Build** → **Authentication** → **Get started**
2. **Sign-in method** → **Email/Password** → **Enable** → **Save**

---

## 3. Firestore Oluşturma

1. Sol menü **Build** → **Firestore Database** → **Create database**
2. **Production mode** seçin (veya test için **Test mode**)
3. Region seçin → **Enable**

---

## 4. Service Account JSON İndirme

1. Proje ayarları (dişli ikon) → **Project settings**
2. **Service accounts** sekmesi
3. **Generate new private key** → **Generate key**
4. İnen JSON dosyasını proje köküne kopyalayın: `firebase-credentials.json`
5. `.gitignore`'a ekleyin:
   ```
   firebase-credentials.json
   ```

---

## 5. Web API Key Alma

1. **Project settings** → **General** sekmesi
2. **Your apps** altında **Web API Key** değerini kopyalayın  
   (veya **Add app** → Web → Config'deki `apiKey`)

---

## 6. `.env` Ayarları

.env dosyaniza su satirlari ekleyin (yorum isaretlerini kaldirin):

```env
# Firebase'i etkinlestir
USE_FIREBASE_AUTH=True

# Service Account JSON yolu (4. adimda indirdiginiz dosya)
FIREBASE_CREDENTIALS_PATH=firebase-credentials.json

# Proje ID (Firebase Console -> Project settings -> Project ID)
FIREBASE_PROJECT_ID=cookewise

# Web API Key (5. adimda aldiniz)
FIREBASE_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

**Not:** Tum 4 degisken zorunludur. Eksik olursa Firebase calismaz.

---

## 7. Paket Kurulumu

```bash
pip install firebase-admin
# veya
pip install -r requirements.txt
```

---

## 8. Yapı Özeti

| Bileşen | Kullanım |
|---------|----------|
| **Firebase Auth** | Kayıt, giriş (email/şifre) |
| **Firestore** | Profil (full_name, phone, is_admin, is_active) |

**Koleksiyon:** `users`  
**Belge ID:** Firebase UID (Auth'dan)

---

## 9. Admin Kullanıcı Oluşturma

Firebase kullanırken admin için Firestore'da `is_admin: true` ayarlayın:

1. Firebase Console → **Firestore Database**
2. `users` koleksiyonu → ilgili belge
3. `is_admin` alanı ekleyin/değiştirin: `true`

Veya bir script ile (Firebase Admin SDK):

```python
from firebase_admin import firestore
db = firestore.client()
db.collection("users").document("FIREBASE_UID").update({"is_admin": True})
```

---

## 10. Kapatma (MongoDB'ye Dönüş)

`.env` içinde:

```env
USE_FIREBASE_AUTH=False
```

veya ilgili Firebase değişkenlerini kaldırın.

---

## Sorun Giderme

| Hata | Çözüm |
|------|-------|
| `Credentials file not found` | `FIREBASE_CREDENTIALS_PATH` doğru mu kontrol edin |
| `FIREBASE_API_KEY tanimli olmali` | Web API Key `.env`'e eklendi mi kontrol edin |
| `Invalid API key` | API Key Firebase Console'dan doğru kopyalandı mı kontrol edin |
