# 🏰 Telegram Strateji Oyun Botu

🌐 **[فارسی](README_FA.md)** | **Türkçe** | **[English](README.md)**

[![MIT Lisansı](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.6+](https://img.shields.io/badge/Python-3.6%2B-brightgreen.svg)](https://www.python.org/)
[![Telegram Bot API](https://img.shields.io/badge/Telegram-Bot%20API-blue.svg?logo=telegram)](https://core.telegram.org/bots/api)
[![SQLite](https://img.shields.io/badge/Database-SQLite-lightgrey.svg?logo=sqlite)](https://www.sqlite.org/)

Telegram grupları için **çok oyunculu stratejik kaynak yönetimi oyun botu**. Oyuncular kendi topraklarının lordları olur — ekonomi yönetimi, bina yükseltme, ordu eğitimi, antlaşma yapma ve rakip lordlara saldırı düzenleme — hepsi Telegram üzerinden.

> 🌍 **Bot artık üç dili destekliyor.** Grubunuza uyan dosyayı çalıştırın: `main.py` (Farsça / فارسی), `main-en.py` (İngilizce) veya `main-tr.py` (Türkçe). Türkçe arayüz için `python main-tr.py` komutunu çalıştırın.

> 🚢 **YENİ — Dünya Ticareti.** Lordlar artık gerçek bir dünya haritası üzerinde deniz ve kara yoluyla birbirleriyle ticaret yapabilir: rotanızı seçin (Süveyş Kanalı geçiş ücretini ödeyin ya da Afrika'yı dolaşın), boğazlara sahip olup geçiş ücretlerini hazinenize aktarın ve sevkiyatınızı canlı izleyin. Bkz. [Dünya Ticareti](#dünya-ticareti).

---

## 📑 İçindekiler

- [Özellikler](#-özellikler)
- [Oyun Mekanikleri](#-oyun-mekanikleri)
- [Yönetim Paneli](#️-yönetim-paneli)
- [Varlık Kataloğu](#-varlık-kataloğu)
- [Başlarken](#-başlarken)
  - [Gereksinimler](#gereksinimler)
  - [Kurulum](#kurulum)
  - [Yapılandırma](#yapılandırma)
- [Kullanım](#-kullanım)
  - [Komutlar](#komutlar)
  - [Menü Seçenekleri](#menü-seçenekleri)
- [Testler](#-testler)
- [Proje Yapısı](#-proje-yapısı)
- [Katkıda Bulunma](#-katkıda-bulunma)
- [Lisans](#-lisans)
- [İletişim](#-iletişim)

---

## ✨ Özellikler

| Kategori | Detaylar |
|---|---|
| 🏗️ **Kaynak Yönetimi** | 8 kaynak türünü yönetin: para, taş, odun, demir, altın, yiyecek, et ve giysi |
| 🏭 **Bina ve Fabrika Yükseltmeleri** | Taş ocağı, kereste fabrikası, demir madeni, altın madeni, çiftlik, hayvan çiftliği, giysi fabrikası ve banka yükseltmeleri |
| ⚔️ **Askeri Sistem** | Kılıçlı asker, tüfekçi, atlı süvari, özel muhafız, top ve deniz kuvvetleri eğitimi |
| 📜 **Diplomasi ve Antlaşmalar** | Oyuncular arasında etkileşimli onaylarla antlaşma oluşturma, gönderme ve onaylama |
| 🔔 **Haftalık Üretim Döngüleri** | Fabrika ve bina çıktılarını haftalık olarak toplama |
| 💬 **Oyun İçi İletişim** | Gruplar arası özel mesaj gönderme ve kanala bildiri yayınlama |
| 🛡️ **Saldırı ve Savunma** | Detaylı saldırı takibi ile askeri seferleri planlama ve kaydetme |
| 🚢 **Dünya Ticareti** | Okyanuslar, boğazlar, kanallar ve İpek Yolu geçitlerinden oluşan dünya haritasında deniz ve kara yoluyla diğer lordlara mal gönderme — rota seçimi, geçiş ücretleri, boğaz sahipliği ve canlı sevkiyat takibi |
| 🛡️ **Yönetim Paneli** | Satır içi `/admin` paneli: oyuncu ve dünya istatistikleri, ekonomi ve askeri özetler, bölüm başına aç/kapat anahtarları, yönetici işlem kaydı, ek yöneticiler, ülke sıfırlama ve sefer/ticaret fotoğrafları |
| 🧩 **Özel Varlık Türleri** | Kaynaklar, birimler ve binalar koda değil veriye dayanır. Okçuları, onları eğiten kampı, haftalık üretimini ve yükseltme maliyetini Telegram içinden ekleyin — Python yok, veritabanı taşıması yok |
| 🔧 **Yönetici Kontrolleri** | Varlık değerlerini ayarlama, haftalık güncellemeleri tetikleme ve konumlar, boğaz sahipliği ile ticaret ayarlarını yönetme |

---

## 🎮 Oyun Mekanikleri

### Kaynaklar

Oyuncular temel kaynak ve askeri birim tedarikiyle başlar. Üretimi artırmak için fabrikaları ve binaları yükseltin:

- **Ekonomi**: Para 💰 · Taş 🪨 · Odun 🪵 · Demir ⛏️ · Altın 🥇 · Yiyecek 🌾 · Et 🥩 · Giysi 👕
- **Askeri**: Kılıçlı Asker ⚔️ · Tüfekçi 🔫 · Atlı Kılıçlı 🐴 · Atlı Tüfekçi 🏇 · Özel Muhafız 🛡️ · Orta Top 💣 · Büyük Top 🎯 · Küçük/Orta/Büyük Gemi 🚢

### Binalar ve Fabrikalar

Her bina birden fazla seviyede yükseltilebilir. Daha yüksek seviyeler haftalık döngü başına daha fazla kaynak üretir:

- Taş Fabrikası · Odun Fabrikası · Demir Fabrikası · Altın Madeni
- Çiftlik · Hayvan Çiftliği · Giysi Fabrikası · Banka
- Her birim türü için askeri kamplar ve tersaneler

### Dünya Ticareti

Lordlar, tamamen cam düğmelerle, iki dünya haritası üzerinden birbirleriyle ticaret yapar:

- **Deniz rotaları** 🚢 — boğazlar ve kanallarla (Süveyş, Panama, Hürmüz, Bab-ül Mendeb, Malakka...) birbirine bağlanan okyanuslar, denizler ve körfezler. Geçiş noktaları ücretlidir; Ümit Burnu ve Horn Burnu üzerinden ücretsiz ama uzun rotalar vardır.
- **Kara rotaları** 🐫 — Hayber, Pamir ve Sahra Yolu gibi ücretli geçitlerle bağlanan İpek Yolu bölgeleri (Pers, Anadolu, Hindistan, Çin...).
- **Rota seçimi** — bot en fazla üç rota (en hızlı / geçiş ücretsiz / en ucuz) için süre, ücret ve geçiş maliyetlerini gösterir; seçimi gönderici yapar.
- **Gemiler ve kervanlar** — deniz ticareti yük kapasiteli gemiler gerektirir (teslimata kadar kilitlenir); kara ticareti kervanlarla yapılır.
- **Teklif ve emanet** — mallar, araçlar ve ücretler teklif gönderilirken düşülür; hedef lord kabul veya reddeder; reddedilen, iptal edilen veya süresi dolan teklifler tamamen iade edilir.
- **Canlı takip** — bot sevkiyatı gerçek zamanlı ilerletir ve her ara noktada takip mesajını düzenler ("sevkiyat Süveyş Kanalı geçişini tamamladı — ücret ödendi"); kalkış ve varışlar oyun kanalına duyurulur.
- **Boğaz sahipliği** 🪙 — yönetici herhangi bir boğaz, kanal veya geçidin sahipliğini bir gruba verebilir: geçiş ücretleri o grubun hazinesine gider ve kendi sevkiyatları ücretsiz geçer. Sahipsiz geçişlerin ücretleri yakılır.
- **Yönetici ayarları** — her grubun deniz/kara konumu ile tüm hız, ücret, geçiş ve kapasite değerleri oyun içinden düzenlenebilir.
- **Ticaret fotoğrafı** 🖼 — bir yönetici ticaret mesajlarına fotoğraf ekleyebilir; teklif kartı, canlı takip mesajı ve kanal duyuruları o zaman altyazılı fotoğraf olarak gönderilir. Telegram'ın 1024 karakterlik altyazı sınırını aşan metinler otomatik olarak düz metne döner.

---

## 🛡️ Yönetim Paneli

Paneli açmak için bir grupta **veya** botun özel sohbetinde `/admin` gönderin. Her düğme kime dokunulduğunu yeniden denetler; bu yüzden grupta açık bırakılmış bir panel yönetici olmayanların işine yaramaz.

| Ekran | İşlevi |
|---|---|
| 📊 **İstatistikler** | Grup ve lord sayıları, toplam servet, toplam asker, toplam bina ve ticaret durumu (etkin / bekleyen / tamamlanan) |
| 💰 **Ekonomi** | Kaynak başına dünya toplamları ve en zengin grup; gruba göre ayrıntıya inilebilir |
| ⚔️ **Askeri durum** | Birim türüne göre dünya toplamları ve en güçlü ordu; gruba göre ayrıntıya inilebilir |
| ⚙️ **Bölümleri aç/kapat** | Her bölüm için bir anahtar — varlıklar, yükseltme, bildiri, özel mesaj, antlaşma, sefer, ticaret, haftalık güncelleme, lord kaydı. Kapatılan bölüm hem `/start` menüsünden kalkar hem de düğmeleri reddedilir; böylece eski bir menüyle atlatılamaz |
| 🧾 **İşlem kaydı** | Her yönetici değişikliği — kim, ne, ne zaman — en yeniden eskiye, sayfa başına 10 kayıt |
| 👑 **Yöneticiler** | *(yalnızca sahip)* Kullanıcının bir mesajını ileterek ya da sayısal kimliğini göndererek yönetici ekleyin ve tekrar çıkarın. Yapılandırmadaki sahip her zaman yöneticidir ve çıkarılamaz |
| 🧩 **Varlıklar ve birimler** | Kaynak, birim ve bina türlerini ekleyin, yeniden adlandırın, ayarlayın veya kaldırın — [Varlık Kataloğu](#-varlık-kataloğu) |
| ♻️ **Ülkeyi sıfırla** | Bir grubun kaynaklarını, askerlerini ve binalarını onay adımının ardından başlangıç değerlerine döndürür. Antlaşmalar ve ticaret konumları değişmez; önceki değerler işlem kaydına yazılır |
| 🖼 **Ticaret fotoğrafı** | Ticaret mesajlarında kullanılan fotoğrafı ayarlayın veya kaldırın |
| 🖼 **Savaş fotoğrafları** | Kara ve deniz seferi duyuruları için ayrı fotoğraflar ayarlayın veya kaldırın |
| 🌍 **Ticaret yönetimi** | Mevcut ticaret yönetimi ekranları — konumlar, boğaz sahipliği, ticaret ayarları |
| 🎮 **Oyun menüsü** | Panelden çıkmadan normal oyuncu menüsünü açar |

### Lord atama

Oyuncular artık kendilerini kaydedemez. Bir yönetici grupta **oyuncunun mesajını yanıtlar** ve `/setlord` gönderir; bot gönderenin yönetici olduğunu doğrular ve yanıtlanan kullanıcıyı o grubun lordu olarak kaydeder.

### Seferler ve savaş kanalı

Genel sefer duyuruları **savaş kanalına** (`WAR_CHANNEL_ID`) gider ve yalnızca komutanı, çıkış noktasını, hedefi ve varış zamanını içerir. Oyuncunun yazdığı ordu bilgileri dahil tam rapor, sahibe ve tüm yöneticilere özel olarak gönderilir.

---

## 🧩 Varlık Kataloğu

Bir ülkenin sahip olabileceği her şey — her kaynak, birim ve bina — Python koduna değil veritabanına yazılıdır. Yönetim panelindeki **🧩 Varlıklar ve birimler** oyunun şeklini belirlediğiniz yerdir.

### Okçu eklemek

1. 🧩 Varlıklar ve birimler → ⚔️ Birimler → ➕ Yeni tür ekle
2. Dahili anahtar: `archers` · Farsça, İngilizce ve Türkçe görünen adlar · başlangıç miktarı
3. 🧩 bölümüne dönün → 🏭 Binalar → ➕ Yeni tür ekle → `archery_range`, ürettiği şey olarak **Okçu**'yu seçin ve seviye başına haftalık üretimi girin
4. Yeni binayı açın → 💸 Yükseltme maliyeti → bir seviyenin her kaynaktan ne kadara mal olduğunu belirleyin

Okçular artık varlıklar ekranında, yükseltme menüsünde, haftalık üretim döngüsünde, askeri özette ve yönetici varlık düzenleyicisinde görünür. Hiçbir şey yeniden derlenmedi.

### Neleri değiştirebilirsiniz

| Alan | Kapsam | Not |
|---|---|---|
| Görünen ad | her şey | Her dil için ayrı ayrı |
| Başlangıç miktarı | her şey | ♻️ *Ülkeyi sıfırla* bunu kullanır |
| Üretim | binalar | Ne ürettiği ve haftalık güncellemede seviye başına ne kadar |
| Yükseltme maliyeti | binalar | Kaynakların herhangi bir birleşimi; sıfır o satırı kaldırır |
| Ticarete açık | kaynaklar | Konvoyların taşıyıp taşıyamayacağını belirler |

### Yerleşik türler ve kaldırma

Oyunla gelen 8 kaynak, 10 birim ve 18 bina **yerleşik** olarak kaydedilir. Yeniden adlandırılabilir ve ayarlanabilirler ama kaldırılamazlar; çünkü ticaret sistemi ve savaş akışı onlara anahtarla atıfta bulunur.

Özel bir türü kaldırmak onu **gizler**: her menüden çıkar ama veritabanı sütunu ve sayıları kalır. Geri getirdiğinizde değerler geri döner. Hiçbir şey yok edilmez ve çalışan hiçbir tablo yeniden oluşturulmaz.

### Bunun düzelttiği bir hata

Yükseltme maliyetleri eskiden üç bot dosyasının her birinde iki kez yazılıydı — biri karşılanabilirliği sınamak, diğeri düşmek için. **Altın madeni, çiftlik, hayvan çiftliği, kılıçlı asker kampı ve özel muhafız kampı** için bu iki liste farklı kaynakları adlandırıyordu; yani bir yükseltme demirinize göre onaylanıp sahip olmadığınız odunla ödenebiliyor ve bakiyeyi eksiye düşürebiliyordu. Artık tek bir maliyet tablosu her ikisini de yürütüyor ve her şey tek bir işlemde uygulanıyor.

---

## 🚀 Başlarken

### Gereksinimler

- **Python** 3.6 veya üzeri
- [@BotFather](https://t.me/BotFather)'dan bir **Telegram Bot Token**
- **SQLite3** (Python ile birlikte gelir)

### Kurulum

1. **Depoyu klonlayın:**

   ```bash
   git clone https://github.com/iliyadindar/Telegram-Strategic-GameBot.git
   cd Telegram-Strategic-GameBot
   ```

2. **Bağımlılıkları yükleyin:**

   ```bash
   pip install pyTelegramBotAPI
   ```

### Yapılandırma

**Hiçbir değer koda gömülmez.** Botu başlatın ve sorulduğunda değerleri terminale yapıştırın:

```bash
python main-tr.py   # Türkçe  (veya: Farsça için python main.py, İngilizce için python main-en.py)
```

```
=== Bot yapılandırması ===
Bu değerler bir kez sorulur ve bot_config.json içinde saklanır.
(Bu dosya .gitignore içindedir — asla commit etmeyin.)

Bot jetonu (@BotFather'dan): 123456:ABC-DEF...
Sahip sayısal kullanıcı kimliği (@userinfobot'tan): 123456789
Haber kanalı kimliği (örn. @mychannel veya -100…): @your_channel
Savaş kanalı kimliği (haber kanalını kullanmak için boş bırakın): @your_war_channel
```

Yanıtlar `bot_config.json` dosyasına yazılır, böylece sonraki çalıştırmalar sessizce başlar. Her değer şu sırayla çözümlenir:

| Ayar | Ortam değişkeni | Amaç |
|---|---|---|
| Bot jetonu | `BOT_TOKEN` | [@BotFather](https://t.me/BotFather)'dan |
| Sahip kimliği | `ADMIN_ID` | Kalıcı sahip; panelden başka yöneticiler ekleyebilir |
| Haber kanalı | `CHANNEL_ID` | Bildiriler ve ticaret duyuruları |
| Savaş kanalı | `WAR_CHANNEL_ID` | Sefer duyuruları. Boş bırakılırsa haber kanalı kullanılır |

Sıra: **ortam değişkeni → `bot_config.json` → terminal sorusu.** Ortam değişkenleri her zaman önceliklidir; bu yüzden bir sunucu kurulumunda dosyaya hiç gerek kalmaz:

```bash
BOT_TOKEN=123456:ABC ADMIN_ID=123456789 CHANNEL_ID=@news python main-tr.py
```

> SQLite veritabanı (`game_bot.db`) ilk çalıştırmada otomatik olarak oluşturulur; mevcut veritabanları yükseltme sırasında yerinde taşınır.

---

## 📖 Kullanım

### Komutlar

| Komut | Açıklama |
|---|---|
| `/setlord` | **Yalnızca yönetici.** Bir oyuncunun mesajını yanıtlayarak onu o grubun lordu yapın |
| `/start` | Ana menüyü açın ve oynamaya başlayın |
| `/admin` | Yönetim panelini açın — grupta veya özel sohbette *(yalnızca yönetici)* |

### Menü Seçenekleri

| Buton | İşlev |
|---|---|
| 💰 **Varlıklar** | Mevcut kaynaklarınızı ve askeri birimlerinizi görüntüleyin |
| 🛠️ **Yükseltme** | Binaları ve fabrikaları yükseltin |
| 🙌 **Bildiri** | Oyun kanalına bir bildiri yayınlayın |
| ✉️ **Özel Mesaj** | Başka bir gruba özel mesaj gönderin |
| 📜 **Antlaşma** | Diğer oyuncularla antlaşma oluşturun, gönderin veya onaylayın |
| ⚔️ **Askeri Sefer** | Saldırı detaylarını planlayın ve kaydedin |
| 🚢 **Dünya Ticareti** | Deniz veya kara yoluyla diğer lordlara ticaret sevkiyatı gönderin |
| 🛡️ **Yönetim Paneli** | Yönetim panelini açın *(yalnızca yönetici)* |
| 🔨 **Haftalık Güncelleme** | Haftalık fabrika çıktılarını toplayın *(yalnızca yönetici)* |
| 🛠️ **Varlık Ayarı** | Varlık değerlerini ayarlayın *(yalnızca yönetici)* |
| 🌍 **Ticaret Yönetimi** | Konumları, boğaz sahipliğini ve ticaret ayarlarını yönetin *(yalnızca yönetici)* |

> Yönetim panelinden kapatılmış bir bölüme ait düğme menüde hiç görünmez.

---

## 🧪 Testler

Test paketi çevrimdışı çalışır — bellek içi bir veritabanı ve sahte bir Telegram istemcisi kullanır, jetona gerek yoktur:

```bash
cd tests
python -m unittest discover -s . -t .
```

Yapılandırma çözümlemesini, erişim denetimini, bölüm anahtarlarını, işlem kaydını, istatistikleri, ülke sıfırlamayı, lord atamayı, sağdan sola ok yönünü, fotoğraf işlemeyi, varlık kataloğunu (ekleme, ayarlama, gizleme, yükseltme muhasebesi) ve üç giriş dosyasının uçtan uca yüklenmesini kapsar — panelden okçu eklemek ve bir oyuncunun onları eğitebildiğini doğrulamak dahil.

---

## 📁 Proje Yapısı

```
Telegram-Strategic-GameBot/
├── main.py           # Bot (Farsça) — mantık, işleyiciler ve veritabanı kurulumu
├── main-en.py        # Bot (İngilizce) — aynı mantık, İngilizce arayüz
├── main-tr.py        # Bot (Türkçe) — aynı mantık, Türkçe arayüz
├── bot_config.py     # Jeton / sahip / kanal kimlikleri: ortam → bot_config.json → terminal sorusu
├── admin_panel.py    # Satır içi /admin paneli: erişim, istatistik, anahtarlar, kayıt, sıfırlama
├── admin_strings.py  # Panelin üç dildeki metinleri
├── asset_catalog.py  # Kaynaklar, birimler ve binalar veri olarak: başlangıç, maliyet, üretim
├── asset_admin.py    # Katalog türlerini eklemek ve ayarlamak için panel ekranları
├── asset_ui.py       # Oyuncu ekranları: varlıklar, yükseltme, haftalık üretim, varlık düzenleyici
├── trade_system.py   # Üç botun paylaştığı dünya ticareti motoru (dünya haritası, rotalama, geçiş ücretleri, canlı takip)
├── tests/            # Çevrimdışı test paketi (sahte bot + bellek içi SQLite)
├── LICENSE           # MIT Lisansı
├── SECURITY.md       # Güvenlik politikası
├── README.md         # Proje dokümantasyonu (İngilizce)
├── README_FA.md      # Proje dokümantasyonu (Farsça)
└── README_TR.md      # Proje dokümantasyonu (Türkçe)
```

---

## 🤝 Katkıda Bulunma

Katkılarınızı bekliyoruz! Başlamak için:

1. Depoyu Fork edin
2. Bir özellik dalı oluşturun (`git checkout -b feature/amazing-feature`)
3. Değişikliklerinizi Commit edin (`git commit -m 'Add amazing feature'`)
4. Dalınıza Push edin (`git push origin feature/amazing-feature`)
5. Bir Pull Request açın

Büyük değişiklikler için, lütfen önce ne değiştirmek istediğinizi tartışmak üzere bir Issue açın.

---

## 📄 Lisans

Bu proje **MIT Lisansı** altında lisanslanmıştır. Ayrıntılar için [LICENSE](LICENSE) dosyasına bakın.

---

## 📬 İletişim

**Iliya Dindar** — Geliştirici ve Proje Sahibi

- Telegram: [@iliyadindar](https://t.me/iliyadindar)
- GitHub: [@iliyadindar](https://github.com/iliyadindar)

<p align="center">
  ⭐ Bu projeyi faydalı bulduysanız, lütfen bir yıldız vermeyi düşünün!
</p>
