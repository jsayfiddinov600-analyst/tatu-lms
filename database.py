import sqlite3
import json
import random
import os

DB_PATH = os.environ.get('DB_PATH', 'lms.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        parol TEXT NOT NULL,
        type TEXT NOT NULL,  -- 'talaba' | 'oqituvchi' | 'admin'
        ism TEXT NOT NULL,
        qisqa TEXT,
        initials TEXT,
        jins TEXT,
        guruh TEXT,
        yonalish TEXT,
        til TEXT DEFAULT 'UZ',
        daraja TEXT,
        shakl TEXT,
        kurs INTEGER,
        murabbiy TEXT,
        stipendiya TEXT,
        tugilgan TEXT,
        kafedra TEXT,
        lavozim TEXT,
        gpa_history TEXT DEFAULT '[]'
    );

    CREATE TABLE IF NOT EXISTS fanlar (
        id INTEGER PRIMARY KEY,
        nom TEXT NOT NULL,
        kod TEXT NOT NULL,
        kredit INTEGER DEFAULT 6,
        maruza_oquv TEXT,
        amaliyot_oquv TEXT
    );

    CREATE TABLE IF NOT EXISTS topshiriqlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fan_id INTEGER NOT NULL,
        nom TEXT NOT NULL,
        turi TEXT NOT NULL,  -- 'Amaliyot' | 'Mustaqil' | 'Oraliq'
        muddat TEXT NOT NULL,
        maks INTEGER NOT NULL,
        mustaqil INTEGER DEFAULT 0,
        auditoriya INTEGER DEFAULT 0,
        FOREIGN KEY (fan_id) REFERENCES fanlar(id)
    );

    CREATE TABLE IF NOT EXISTS talaba_fanlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        talaba_id TEXT NOT NULL,
        fan_id INTEGER NOT NULL,
        davomat_soni INTEGER DEFAULT 0,
        davomat_limit INTEGER DEFAULT 9,
        UNIQUE(talaba_id, fan_id),
        FOREIGN KEY (talaba_id) REFERENCES users(id),
        FOREIGN KEY (fan_id) REFERENCES fanlar(id)
    );

    CREATE TABLE IF NOT EXISTS yuklamalar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        talaba_id TEXT NOT NULL,
        fan_id INTEGER NOT NULL,
        topshiriq_id INTEGER NOT NULL,
        holat TEXT DEFAULT 'yuklandi',  -- 'yuklandi' | 'baholandi' | 'kechikdi'
        yuklangan_vaqt TEXT NOT NULL,
        UNIQUE(talaba_id, topshiriq_id),
        FOREIGN KEY (talaba_id) REFERENCES users(id),
        FOREIGN KEY (topshiriq_id) REFERENCES topshiriqlar(id)
    );

    CREATE TABLE IF NOT EXISTS baholar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        talaba_id TEXT NOT NULL,
        fan_id INTEGER NOT NULL,
        topshiriq_id INTEGER NOT NULL,
        ball REAL,
        izoh TEXT DEFAULT '',
        oqituvchi_id TEXT NOT NULL,
        baholangan_vaqt TEXT NOT NULL,
        UNIQUE(talaba_id, topshiriq_id),
        FOREIGN KEY (talaba_id) REFERENCES users(id),
        FOREIGN KEY (topshiriq_id) REFERENCES topshiriqlar(id),
        FOREIGN KEY (oqituvchi_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS davomatlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        talaba_id TEXT NOT NULL,
        fan_id INTEGER NOT NULL,
        sana TEXT NOT NULL,
        holat TEXT NOT NULL,  -- 'keldi' | 'kelmadi' | 'sababli'
        oqituvchi_id TEXT NOT NULL,
        UNIQUE(talaba_id, fan_id, sana),
        FOREIGN KEY (talaba_id) REFERENCES users(id),
        FOREIGN KEY (fan_id) REFERENCES fanlar(id)
    );

    CREATE TABLE IF NOT EXISTS snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL,
        yaratilgan TEXT NOT NULL,
        data TEXT NOT NULL
    );
    """)

    conn.commit()
    conn.close()

def seed_db():
    """Bazaga boshlang'ich ma'lumotlar kiritish"""
    conn = get_db()
    c = conn.cursor()

    # Agar allaqachon ma'lumot bo'lsa, qayta yuklamaslik
    existing = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if existing > 0:
        conn.close()
        return

    random.seed(42)

    # ===== OQITUVCHILAR — avval (baholar FK uchun) =====
    teachers_early = [
        ("TCH001","tch001","Sadikov R.T.","SR","Dasturiy injiniring","Dotsent"),
        ("TCH002","tch002","Jorayev A.I.","JA","Dasturiy injiniring","Dotsent"),
        ("TCH003","tch003","Djurayev T.B.","DT","Dasturiy injiniring","Dotsent"),
        ("TCH004","tch004","Xudoyberdiyev R.F.","XR","Dasturiy injiniring","Dotsent"),
        ("TCH005","tch005","Atadjanova N.S.","AN","Kompyuter tarmoqlari","Dotsent"),
        ("TCH006","tch006","Torayeva M.S.","TM","Kompyuter tarmoqlari","Dotsent"),
        ("TCH007","tch007","Xudazarov R.S.","XR","Matematika","Dotsent"),
        ("TCH008","tch008","Xurramov A.X.","XA","Matematika","Dotsent"),
        ("TCH009","tch009","Karimov N.M.","KN","Axborot texnologiyalari","Dotsent"),
    ]
    for t in teachers_early:
        c.execute("INSERT OR IGNORE INTO users (id,parol,type,ism,qisqa,initials,kafedra,lavozim) VALUES (?,?,?,?,?,?,?,?)",
                  (t[0],t[1],"oqituvchi",t[2],t[2],t[3],t[4],t[5]))
    c.execute("INSERT OR IGNORE INTO users (id,parol,type,ism,qisqa,initials) VALUES (?,?,?,?,?,?)",
              ("admin","admin123","admin","Administrator","Admin","AD"))
    conn.commit()

    # ===== FANLAR =====
    fanlar = [
        (1, "Veb ilovalar yaratish", "CWA001", 6, "Sadikov R.T.", "Jorayev A.I."),
        (2, "Malumotlar bazasi", "DBM001", 6, "Djurayev T.B.", "Xudoyberdiyev R.F."),
        (3, "Kompyuter tarmoqlari", "NWK003", 6, "Atadjanova N.S.", "Torayeva M.S."),
        (4, "Ehtimollar va statistika", "MTH002", 6, "Xudazarov R.S.", "Xurramov A.X."),
        (5, "Amaliy dasturiy paketlar", "ASP001", 6, "Karimov N.M.", "Karimov N.M."),
    ]
    c.executemany(
        "INSERT OR IGNORE INTO fanlar (id,nom,kod,kredit,maruza_oquv,amaliyot_oquv) VALUES (?,?,?,?,?,?)",
        fanlar
    )

    # ===== TOPSHIRIQLAR =====
    # (fan_id, nom, turi, muddat, maks, mustaqil, auditoriya)
    tops = [
        # Fan 1
        (1,"1-Amaliy ish","Amaliyot","07-03-2025",5,0,0),
        (1,"2-Amaliy ish","Amaliyot","11-04-2025",5,0,0),
        (1,"3-Amaliy ish","Amaliyot","10-05-2025",5,0,0),
        (1,"4-Amaliy ish","Amaliyot","28-05-2025",5,0,0),
        (1,"Mustaqil ish №1","Mustaqil","18-04-2025",10,1,0),
        (1,"Mustaqil ish №2 — Vue.js ilovasi","Mustaqil","20-05-2025",10,1,0),
        (1,"Oraliq nazorat","Oraliq","21-05-2025",10,0,1),
        # Fan 2
        (2,"1-Laboratoriya ishi","Amaliyot","10-03-2025",5,0,0),
        (2,"2-Laboratoriya ishi","Amaliyot","15-04-2025",5,0,0),
        (2,"3-Laboratoriya ishi","Amaliyot","10-05-2025",5,0,0),
        (2,"4-Laboratoriya ishi","Amaliyot","25-05-2025",5,0,0),
        (2,"Mustaqil ish №1 — SQL sorovlari","Mustaqil","20-03-2025",10,1,0),
        (2,"Mustaqil ish №2 — Normalizatsiya","Mustaqil","22-05-2025",10,1,0),
        (2,"Oraliq nazorat","Oraliq","25-04-2025",10,0,1),
        # Fan 3
        (3,"1-Amaliy ish","Amaliyot","05-03-2025",5,0,0),
        (3,"2-Amaliy ish","Amaliyot","10-04-2025",5,0,0),
        (3,"3-Amaliy ish","Amaliyot","25-04-2025",5,0,0),
        (3,"4-Amaliy ish","Amaliyot","20-05-2025",5,0,0),
        (3,"Mustaqil ish №1 — OSI modeli","Mustaqil","20-04-2025",10,1,0),
        (3,"Mustaqil ish №2 — Tarmoq protokollari","Mustaqil","18-05-2025",10,1,0),
        (3,"Oraliq nazorat","Oraliq","10-05-2025",10,0,1),
        # Fan 4
        (4,"1-Mustaqil topshiriq","Amaliyot","08-03-2025",4,0,0),
        (4,"2-Mustaqil topshiriq","Amaliyot","12-04-2025",4,0,0),
        (4,"3-Mustaqil topshiriq","Amaliyot","15-05-2025",4,0,0),
        (4,"4-Mustaqil topshiriq","Amaliyot","26-05-2025",4,0,0),
        (4,"5-Mustaqil topshiriq","Amaliyot","29-05-2025",4,0,0),
        (4,"Mustaqil ish №1 — Ehtimollar nazariyasi","Mustaqil","22-03-2025",10,1,0),
        (4,"Mustaqil ish №2 — Statistik tahlil","Mustaqil","10-05-2025",10,1,0),
        (4,"Oraliq nazorat","Oraliq","26-04-2025",10,0,1),
        # Fan 5
        (5,"1-Laboratoriya","Amaliyot","06-03-2025",5,0,0),
        (5,"2-Laboratoriya","Amaliyot","20-03-2025",5,0,0),
        (5,"3-Laboratoriya","Amaliyot","20-04-2025",5,0,0),
        (5,"4-Laboratoriya","Amaliyot","20-05-2025",5,0,0),
        (5,"Mustaqil ish — Excel makrolari","Mustaqil","05-04-2025",10,1,0),
        (5,"Mustaqil ish — PowerPoint dizayn","Mustaqil","15-05-2025",10,1,0),
        (5,"Oraliq nazorat","Oraliq","05-05-2025",10,0,1),
    ]
    c.executemany(
        "INSERT OR IGNORE INTO topshiriqlar (fan_id,nom,turi,muddat,maks,mustaqil,auditoriya) VALUES (?,?,?,?,?,?,?)",
        tops
    )

    # ===== TALABALAR =====
    ERKAK = ["Jasur","Sardor","Bobur","Sanjar","Ulugbek","Doniyor","Sherzod","Oybek","Nodir","Eldor",
             "Jamshid","Mirzo","Bekzod","Firdavs","Zafar","Alisher","Husan","Lochinbek","Ravshan","Timur"]
    AYOL  = ["Kamola","Dilnoza","Nilufar","Sarvinoz","Muazzam","Zulfiya","Nargiza","Shahlo","Barno","Sitora",
             "Mohira","Feruza","Malika","Gulnora","Ozoda","Maftuna","Umida","Nafisa","Robiya","Nasiba"]
    FAM_E = ["Toshmatov","Karimov","Rahimov","Umarov","Xolmatov","Mirzayev","Hasanov","Yunusov",
             "Ergashev","Qodirov","Abdullayev","Nazarov","Ismoilov","Sobirov","Haydarov",
             "Salimov","Normatov","Xasanov","Tursunov","Jumayev","Baxtiyorov","Otajonov",
             "Pulatov","Sultonov","Razzaqov","Musayev","Holiqov","Zokirov","Fozilov"]
    FAM_A = [f+"a" for f in FAM_E]
    OTA   = ["Alisher","Kamoliddin","Ravshan","Bobur","Jasur","Sherzod","Ulugbek","Doniyor",
             "Mansur","Firdavs","Zafar","Husan","Mirzo","Bekzod","Sardor","Oybek","Sanjar","Nodir"]

    def ota_adi(ota_ism, jins):
        suf = "ovich" if ota_ism[-1] not in 'aeiou' else "vich"
        suf_a = "ovna" if ota_ism[-1] not in 'aeiou' else "vna"
        return ota_ism + (suf if jins == "Erkak" else suf_a)

    sid = 1
    for guruh in ["210-23", "211-23"]:
        prefix = "1BK" if guruh == "210-23" else "1CK"
        erkaklar = random.sample(ERKAK, 12)
        ayollar  = random.sample(AYOL, 8)
        lst = [(i, random.choice(FAM_E), "Erkak", random.choice(OTA)) for i in erkaklar]
        lst += [(i, random.choice(FAM_A), "Ayol", random.choice(OTA)) for i in ayollar]
        random.shuffle(lst)

        for ism, fam, jins, ota_ism in lst:
            tid   = f"{prefix}{28080+sid:05d}"
            parol = str(random.randint(10000, 99999))
            ota   = ota_adi(ota_ism, jins)
            tuy   = random.randint(2003, 2006)
            tom   = random.randint(1, 12)
            tok   = random.randint(1, 28)
            gpa_h = json.dumps([round(random.uniform(3.2, 4.0), 2) for _ in range(4)])

            c.execute("""INSERT OR IGNORE INTO users
                (id,parol,type,ism,qisqa,initials,jins,guruh,yonalish,til,daraja,shakl,kurs,murabbiy,stipendiya,tugilgan,gpa_history)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (tid, parol, "talaba",
                 f"{fam} {ism} {ota}", f"{fam} {ism[0]}.", fam[0]+ism[0],
                 jins, guruh, "Kompyuter injiniringi", "UZ", "Bakalavr", "Kunduzgi",
                 3, "Muhiddinov Ziyodulla",
                 "Bor" if random.random() > 0.4 else "Yoq",
                 f"{tok:02d}-{tom:02d}-{tuy}", gpa_h))

            # Talaba-fan bog'lanishi va boshlang'ich davomat
            for fan_id in range(1, 6):
                davomat = random.randint(0, 8)
                c.execute("""INSERT OR IGNORE INTO talaba_fanlar (talaba_id, fan_id, davomat_soni, davomat_limit)
                             VALUES (?,?,?,?)""", (tid, fan_id, davomat, 9))

            # Boshlang'ich baholar — 15-aprelgacha bo'lgan ishlar
            all_tops = c.execute("SELECT * FROM topshiriqlar").fetchall()
            for t in all_tops:
                muddat_parts = t['muddat'].split("-")
                oy  = int(muddat_parts[1])
                kun = int(muddat_parts[0])
                # 15-aprelgacha bo'lgan amaliyot va mustaqil ishlar baholangan
                if (oy < 4 or (oy == 4 and kun <= 15)) and not t['auditoriya']:
                    ball = round(random.uniform(t['maks'] * 0.5, t['maks']), 1)
                    # Yuklama qo'shish
                    c.execute("""INSERT OR IGNORE INTO yuklamalar
                        (talaba_id, fan_id, topshiriq_id, holat, yuklangan_vaqt)
                        VALUES (?,?,?,?,?)""",
                        (tid, t['fan_id'], t['id'], 'baholandi', '2025-03-20 10:00:00'))
                    # Baho qo'shish
                    c.execute("""INSERT OR IGNORE INTO baholar
                        (talaba_id, fan_id, topshiriq_id, ball, izoh, oqituvchi_id, baholangan_vaqt)
                        VALUES (?,?,?,?,?,?,?)""",
                        (tid, t['fan_id'], t['id'], ball, '', 'TCH001', '2025-03-25 10:00:00'))
            sid += 1

    conn.commit()
    conn.close()
    print("Database seeded successfully!")

def take_snapshot(nom):
    """Hozirgi holatni saqlash"""
    conn = get_db()
    data = {
        'baholar': [dict(r) for r in conn.execute("SELECT * FROM baholar").fetchall()],
        'yuklamalar': [dict(r) for r in conn.execute("SELECT * FROM yuklamalar").fetchall()],
        'davomatlar': [dict(r) for r in conn.execute("SELECT * FROM davomatlar").fetchall()],
        'talaba_fanlar': [dict(r) for r in conn.execute("SELECT * FROM talaba_fanlar").fetchall()],
    }
    from datetime import datetime
    yaratilgan = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("INSERT INTO snapshots (nom, yaratilgan, data) VALUES (?,?,?)",
                 (nom, yaratilgan, json.dumps(data, ensure_ascii=False)))
    conn.commit()
    conn.close()
    return yaratilgan

def restore_snapshot(snap_id):
    """Snapshotdan tiklash"""
    conn = get_db()
    snap = conn.execute("SELECT * FROM snapshots WHERE id=?", (snap_id,)).fetchone()
    if not snap:
        conn.close()
        return False
    data = json.loads(snap['data'])

    # Eski ma'lumotlarni o'chirish
    conn.execute("DELETE FROM baholar")
    conn.execute("DELETE FROM yuklamalar")
    conn.execute("DELETE FROM davomatlar")

    # Qayta yuklash
    for row in data['baholar']:
        conn.execute("""INSERT OR IGNORE INTO baholar
            (talaba_id,fan_id,topshiriq_id,ball,izoh,oqituvchi_id,baholangan_vaqt)
            VALUES (?,?,?,?,?,?,?)""",
            (row['talaba_id'],row['fan_id'],row['topshiriq_id'],
             row['ball'],row['izoh'],row['oqituvchi_id'],row['baholangan_vaqt']))
    for row in data['yuklamalar']:
        conn.execute("""INSERT OR IGNORE INTO yuklamalar
            (talaba_id,fan_id,topshiriq_id,holat,yuklangan_vaqt)
            VALUES (?,?,?,?,?)""",
            (row['talaba_id'],row['fan_id'],row['topshiriq_id'],row['holat'],row['yuklangan_vaqt']))
    for row in data['davomatlar']:
        conn.execute("""INSERT OR IGNORE INTO davomatlar
            (talaba_id,fan_id,sana,holat,oqituvchi_id)
            VALUES (?,?,?,?,?)""",
            (row['talaba_id'],row['fan_id'],row['sana'],row['holat'],row['oqituvchi_id']))
    for row in data['talaba_fanlar']:
        conn.execute("""UPDATE talaba_fanlar SET davomat_soni=?
            WHERE talaba_id=? AND fan_id=?""",
            (row['davomat_soni'], row['talaba_id'], row['fan_id']))

    conn.commit()
    conn.close()
    return True

def reset_to_initial():
    """Bazani boshlang'ich holatga qaytarish"""
    conn = get_db()
    conn.execute("DELETE FROM baholar")
    conn.execute("DELETE FROM yuklamalar")
    conn.execute("DELETE FROM davomatlar")
    conn.execute("UPDATE talaba_fanlar SET davomat_soni=0")
    conn.commit()

    # Boshlang'ich baholarni qayta seed qilish
    random.seed(42)
    # Re-seed baholar only
    talabalar = conn.execute("SELECT id FROM users WHERE type='talaba'").fetchall()
    tops = conn.execute("SELECT * FROM topshiriqlar").fetchall()

    for t_row in talabalar:
        tid = t_row['id']
        random.seed(hash(tid) % 10000)
        for t in tops:
            muddat_parts = t['muddat'].split("-")
            oy  = int(muddat_parts[1])
            kun = int(muddat_parts[0])
            if (oy < 4 or (oy == 4 and kun <= 15)) and not t['auditoriya']:
                ball = round(random.uniform(t['maks'] * 0.5, t['maks']), 1)
                conn.execute("""INSERT OR IGNORE INTO yuklamalar
                    (talaba_id,fan_id,topshiriq_id,holat,yuklangan_vaqt)
                    VALUES (?,?,?,?,?)""",
                    (tid, t['fan_id'], t['id'], 'baholandi', '2025-03-20 10:00:00'))
                conn.execute("""INSERT OR IGNORE INTO baholar
                    (talaba_id,fan_id,topshiriq_id,ball,izoh,oqituvchi_id,baholangan_vaqt)
                    VALUES (?,?,?,?,?,?,?)""",
                    (tid, t['fan_id'], t['id'], ball, '', 'TCH001', '2025-03-25 10:00:00'))

    # Boshlang'ich davomatni qayta o'rnatish
    random.seed(42)
    for t_row in talabalar:
        tid = t_row['id']
        for fan_id in range(1, 6):
            davomat = random.randint(0, 8)
            conn.execute("UPDATE talaba_fanlar SET davomat_soni=? WHERE talaba_id=? AND fan_id=?",
                        (davomat, tid, fan_id))

    conn.commit()
    conn.close()
    print("Database reset to initial state!")

if __name__ == "__main__":
    init_db()
    seed_db()
    print("Done!")
