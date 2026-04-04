# TATU LMS Backend

## Lokal ishga tushirish

```bash
pip install -r requirements.txt
python app.py
```

## Railway deploy

1. GitHub ga push qiling
2. railway.app da yangi loyiha yarating
3. GitHub repo ni ulang
4. Avtomatik deploy bo'ladi

## Demo loginlar

- Admin: `admin` / `admin123`
- O'qituvchi: `TCH001` / `tch001`
- Talaba: birinchi talaba logini DB dan ko'ring

## API Endpoints

- `POST /api/login` — kirish
- `POST /api/logout` — chiqish
- `GET /api/me` — joriy foydalanuvchi
- `GET /api/talaba/fanlar` — talaba fanlari
- `POST /api/talaba/yuklash` — topshiriq yuklash
- `GET /api/teacher/talabalar` — o'qituvchi talabalari
- `POST /api/teacher/baho` — ball qo'yish
- `POST /api/teacher/davomat` — davomat
- `GET /api/teacher/baholanmaganlar` — baholanmagan ishlar
- `GET /api/poll` — real-time yangilanish (polling)
- `POST /api/admin/reset` — tizimni reset qilish
- `POST /api/admin/snapshot` — holat saqlash
- `GET /api/admin/snapshots` — snapshotlar
- `POST /api/admin/restore/<id>` — tiklash
