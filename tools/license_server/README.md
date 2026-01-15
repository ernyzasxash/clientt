# License Key Server

Bu küçük Flask uygulaması VPS üzerinde çalışıp APK'den gelen lisans anahtarlarını doğrular ve yönetilebilir bir `authorized_keys.json` dosyası kullanır.

Özellikler
- `GET /check?key=...` veya `POST /` ile anahtar doğrulama (JSON `{"key":"..."}` veya header `X-License-Key`).
- `POST /admin/add` ile anahtar ekleme (JSON `{"key":"..."}`), `X-Admin-Token` header ile korunur.
- `POST /admin/remove` ile silme.
- `GET /admin/list` ile mevcut anahtarları listeler.

Kurulum (Ubuntu VPS)
1. Klasörü kopyalayın, örneğin `/root/tools/license_server`.
2. Python virtualenv oluşturun:

```
python3 -m venv /root/tools/license_server/venv
source /root/tools/license_server/venv/bin/activate
pip install -r requirements.txt
```

3. `ADMIN_TOKEN` için güçlü bir değer atayın (ör. rastgele 32 karakter) ve systemd servisinde veya ortamda ayarlayın.
4. `authorized_keys.json` boş bir dizi içerir. Yönetici token ile `curl` kullanarak anahtar ekleyebilirsiniz:

```
cURL örneği:

```
curl -X POST -H "Content-Type: application/json" -H "X-Admin-Token: your_admin_token" \
  -d '{"key":"SOME-LICENSE-KEY"}' http://5.22.215.107:5000/admin/add
```
```

Basit test (HTTP, local):

```
export ADMIN_TOKEN=your_admin_token
python3 server.py
# test check (local)
curl "http://127.0.0.1:5000/check?key=SOME-LICENSE-KEY"
```

Systemd servisi yüklemek için (örnek `/root/tools/license_server` kullanıldığında):

```
# düzenleyin: /root/tools/license_server/license_server.service içinde ADMIN_TOKEN ve yolları kontrol edin
sudo cp /root/tools/license_server/license_server.service /etc/systemd/system/license_server.service
sudo systemctl daemon-reload
sudo systemctl enable --now license_server
sudo journalctl -u license_server -f
```

Yerel anahtar yönetimi (VPS üzerinde doğrudan):

```
# tools/license_server/manage_keys.py script ile
python3 /root/tools/license_server/manage_keys.py add SOME-LICENSE-KEY
python3 /root/tools/license_server/manage_keys.py list
python3 /root/tools/license_server/manage_keys.py remove SOME-LICENSE-KEY
```

Güvenlik ve Production notları
- Trafik için mutlaka HTTPS kullanın (nginx reverse proxy + certbot önerilir).
- `ADMIN_TOKEN`'ı güçlü ve gizli tutun.
- Daha ileri güvenlik isterseniz IP kısıtlama, rate-limit, logging ve DB kullanımı ekleyin.

Android (APK) örneği için `android_example.md` dosyasına bakın.
