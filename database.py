import sqlite3, json, random, os
from datetime import datetime

DB_PATH = os.environ.get('DB_PATH', '/tmp/lms.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY, parol TEXT NOT NULL, type TEXT NOT NULL,
        ism TEXT, qisqa TEXT, initials TEXT, jins TEXT, guruh TEXT,
        yonalish TEXT, til TEXT DEFAULT 'UZ', daraja TEXT, shakl TEXT,
        kurs INTEGER, murabbiy TEXT, stipendiya TEXT, tugilgan TEXT,
        kafedra TEXT, lavozim TEXT, gpa_history TEXT DEFAULT '[]'
    );
    CREATE TABLE IF NOT EXISTS fanlar (
        id INTEGER PRIMARY KEY, nom TEXT, kod TEXT, kredit INTEGER DEFAULT 6,
        maruza_oquv TEXT, amaliyot_oquv TEXT
    );
    CREATE TABLE IF NOT EXISTS topshiriqlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT, fan_id INTEGER, nom TEXT,
        turi TEXT, muddat TEXT, maks INTEGER,
        mustaqil INTEGER DEFAULT 0, auditoriya INTEGER DEFAULT 0,
        FOREIGN KEY (fan_id) REFERENCES fanlar(id)
    );
    CREATE TABLE IF NOT EXISTS talaba_fanlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT, talaba_id TEXT, fan_id INTEGER,
        davomat_soni INTEGER DEFAULT 0, davomat_limit INTEGER DEFAULT 9,
        UNIQUE(talaba_id, fan_id)
    );
    CREATE TABLE IF NOT EXISTS yuklamalar (
        id INTEGER PRIMARY KEY AUTOINCREMENT, talaba_id TEXT, fan_id INTEGER,
        topshiriq_id INTEGER, holat TEXT DEFAULT 'yuklandi', yuklangan_vaqt TEXT,
        UNIQUE(talaba_id, topshiriq_id)
    );
    CREATE TABLE IF NOT EXISTS baholar (
        id INTEGER PRIMARY KEY AUTOINCREMENT, talaba_id TEXT, fan_id INTEGER,
        topshiriq_id INTEGER, ball REAL, izoh TEXT DEFAULT '',
        oqituvchi_id TEXT, baholangan_vaqt TEXT,
        UNIQUE(talaba_id, topshiriq_id)
    );
    CREATE TABLE IF NOT EXISTS davomatlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT, talaba_id TEXT, fan_id INTEGER,
        sana TEXT, holat TEXT, oqituvchi_id TEXT,
        UNIQUE(talaba_id, fan_id, sana)
    );
    CREATE TABLE IF NOT EXISTS snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT, yaratilgan TEXT, data TEXT
    );
    """)
    conn.commit()
    conn.close()

def seed_db():
    conn = get_db()
    c = conn.cursor()
    if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
        conn.close()
        return

    random.seed(42)

    # 1. OQITUVCHILAR VA ADMIN — birinchi (FK uchun)
    teachers = [
        ("TCH001","tch001","Sadikov R.T.","SR","Dasturiy injiniring","Dotsent"),
        ("TCH002","tch002","Jorayev A.I.","JA","Dasturiy injiniring","Dotsent"),
        ("TCH003","tch003","Djurayev T.B.","DT","Dasturiy injiniring","Dotsent"),
        ("TCH004","tch004","Xudoyberdiyev R.F.","XR","Dasturiy injiniring","Dotsent"),
        ("TCH005","tch005","Atadjanova N.S.","AN","Komp. tarmoqlari","Dotsent"),
        ("TCH006","tch006","Torayeva M.S.","TM","Komp. tarmoqlari","Dotsent"),
        ("TCH007","tch007","Xudazarov R.S.","XR","Matematika","Dotsent"),
        ("TCH008","tch008","Xurramov A.X.","XA","Matematika","Dotsent"),
        ("TCH009","tch009","Karimov N.M.","KN","Axborot texnologiyalari","Dotsent"),
    ]
    for t in teachers:
        c.execute("INSERT OR IGNORE INTO users (id,parol,type,ism,qisqa,initials,kafedra,lavozim) VALUES (?,?,?,?,?,?,?,?)",
                  (t[0],t[1],"oqituvchi",t[2],t[2],t[3],t[4],t[5]))
    c.execute("INSERT OR IGNORE INTO users (id,parol,type,ism,qisqa,initials) VALUES (?,?,?,?,?,?)",
              ("admin","admin123","admin","Administrator","Admin","AD"))
    conn.commit()

    # 2. FANLAR
    fanlar = [
        (1,"Veb ilovalar yaratish","CWA001",6,"Sadikov R.T.","Jorayev A.I."),
        (2,"Malumotlar bazasi","DBM001",6,"Djurayev T.B.","Xudoyberdiyev R.F."),
        (3,"Kompyuter tarmoqlari","NWK003",6,"Atadjanova N.S.","Torayeva M.S."),
        (4,"Ehtimollar va statistika","MTH002",6,"Xudazarov R.S.","Xurramov A.X."),
        (5,"Amaliy dasturiy paketlar","ASP001",6,"Karimov N.M.","Karimov N.M."),
    ]
    c.executemany("INSERT OR IGNORE INTO fanlar VALUES (?,?,?,?,?,?)", fanlar)

    # 3. TOPSHIRIQLAR
    tops = [
        (1,"1-Amaliy ish","Amaliyot","07-03-2025",5,0,0),
        (1,"2-Amaliy ish","Amaliyot","11-04-2025",5,0,0),
        (1,"3-Amaliy ish","Amaliyot","10-05-2025",5,0,0),
        (1,"4-Amaliy ish","Amaliyot","28-05-2025",5,0,0),
        (1,"Mustaqil ish 1","Mustaqil","18-04-2025",10,1,0),
        (1,"Mustaqil ish 2","Mustaqil","20-05-2025",10,1,0),
        (1,"Oraliq nazorat","Oraliq","21-05-2025",10,0,1),
        (2,"1-Laboratoriya","Amaliyot","10-03-2025",5,0,0),
        (2,"2-Laboratoriya","Amaliyot","15-04-2025",5,0,0),
        (2,"3-Laboratoriya","Amaliyot","10-05-2025",5,0,0),
        (2,"4-Laboratoriya","Amaliyot","25-05-2025",5,0,0),
        (2,"Mustaqil ish 1","Mustaqil","20-03-2025",10,1,0),
        (2,"Mustaqil ish 2","Mustaqil","22-05-2025",10,1,0),
        (2,"Oraliq nazorat","Oraliq","25-04-2025",10,0,1),
        (3,"1-Amaliy ish","Amaliyot","05-03-2025",5,0,0),
        (3,"2-Amaliy ish","Amaliyot","10-04-2025",5,0,0),
        (3,"3-Amaliy ish","Amaliyot","25-04-2025",5,0,0),
        (3,"4-Amaliy ish","Amaliyot","20-05-2025",5,0,0),
        (3,"Mustaqil ish 1","Mustaqil","20-04-2025",10,1,0),
        (3,"Mustaqil ish 2","Mustaqil","18-05-2025",10,1,0),
        (3,"Oraliq nazorat","Oraliq","10-05-2025",10,0,1),
        (4,"1-Topshiriq","Amaliyot","08-03-2025",4,0,0),
        (4,"2-Topshiriq","Amaliyot","12-04-2025",4,0,0),
        (4,"3-Topshiriq","Amaliyot","15-05-2025",4,0,0),
        (4,"4-Topshiriq","Amaliyot","26-05-2025",4,0,0),
        (4,"5-Topshiriq","Amaliyot","29-05-2025",4,0,0),
        (4,"Mustaqil ish 1","Mustaqil","22-03-2025",10,1,0),
        (4,"Mustaqil ish 2","Mustaqil","10-05-2025",10,1,0),
        (4,"Oraliq nazorat","Oraliq","26-04-2025",10,0,1),
        (5,"1-Laboratoriya","Amaliyot","06-03-2025",5,0,0),
        (5,"2-Laboratoriya","Amaliyot","20-03-2025",5,0,0),
        (5,"3-Laboratoriya","Amaliyot","20-04-2025",5,0,0),
        (5,"4-Laboratoriya","Amaliyot","20-05-2025",5,0,0),
        (5,"Mustaqil ish 1","Mustaqil","05-04-2025",10,1,0),
        (5,"Mustaqil ish 2","Mustaqil","15-05-2025",10,1,0),
        (5,"Oraliq nazorat","Oraliq","05-05-2025",10,0,1),
    ]
    c.executemany("INSERT OR IGNORE INTO topshiriqlar (fan_id,nom,turi,muddat,maks,mustaqil,auditoriya) VALUES (?,?,?,?,?,?,?)", tops)
    conn.commit()

    # 4. TALABALAR
    ERKAK = ["Jasur","Sardor","Bobur","Sanjar","Ulugbek","Doniyor","Sherzod","Oybek","Nodir","Eldor","Jamshid","Mirzo","Bekzod","Firdavs","Zafar","Alisher","Husan","Lochinbek","Ravshan","Timur"]
    AYOL  = ["Kamola","Dilnoza","Nilufar","Sarvinoz","Muazzam","Zulfiya","Nargiza","Shahlo","Barno","Sitora","Mohira","Feruza","Malika","Gulnora","Ozoda","Maftuna","Umida","Nafisa","Robiya","Nasiba"]
    FAM_E = ["Toshmatov","Karimov","Rahimov","Umarov","Xolmatov","Mirzayev","Hasanov","Yunusov","Ergashev","Qodirov","Abdullayev","Nazarov","Ismoilov","Sobirov","Haydarov","Salimov","Normatov","Xasanov","Tursunov","Jumayev","Baxtiyorov","Otajonov","Pulatov","Sultonov","Razzaqov","Musayev","Holiqov","Zokirov","Fozilov"]
    FAM_A = [f+"a" for f in FAM_E]
    OTA   = ["Alisher","Kamoliddin","Ravshan","Bobur","Jasur","Sherzod","Ulugbek","Doniyor","Mansur","Firdavs","Zafar","Husan","Mirzo","Bekzod","Sardor","Oybek","Sanjar","Nodir"]

    def ota_adi(o, j):
        s = "ovich" if o[-1] not in 'aeiou' else "vich"
        sa = "ovna" if o[-1] not in 'aeiou' else "vna"
        return o + (s if j=="Erkak" else sa)

    all_tops = c.execute("SELECT * FROM topshiriqlar").fetchall()
    sid = 1

    for guruh in ["210-23","211-23"]:
        prefix = "1BK" if guruh=="210-23" else "1CK"
        erkaklar = random.sample(ERKAK,12)
        ayollar  = random.sample(AYOL,8)
        lst = [(i,random.choice(FAM_E),"Erkak",random.choice(OTA)) for i in erkaklar]
        lst += [(i,random.choice(FAM_A),"Ayol",random.choice(OTA)) for i in ayollar]
        random.shuffle(lst)

        for ism,fam,jins,ota_ism in lst:
            tid   = f"{prefix}{28080+sid:05d}"
            parol = str(random.randint(10000,99999))
            ota   = ota_adi(ota_ism,jins)
            tuy   = random.randint(2003,2006)
            tom   = random.randint(1,12)
            tok   = random.randint(1,28)
            gpa_h = json.dumps([round(random.uniform(3.2,4.0),2) for _ in range(4)])
            stip  = "Bor" if random.random()>0.4 else "Yoq"

            c.execute("""INSERT OR IGNORE INTO users
                (id,parol,type,ism,qisqa,initials,jins,guruh,yonalish,til,daraja,shakl,kurs,murabbiy,stipendiya,tugilgan,gpa_history)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (tid,parol,"talaba",f"{fam} {ism} {ota}",f"{fam} {ism[0]}.",fam[0]+ism[0],
                 jins,guruh,"Kompyuter injiniringi","UZ","Bakalavr","Kunduzgi",
                 3,"Muhiddinov Ziyodulla",stip,f"{tok:02d}-{tom:02d}-{tuy}",gpa_h))

            for fan_id in range(1,6):
                c.execute("INSERT OR IGNORE INTO talaba_fanlar (talaba_id,fan_id,davomat_soni,davomat_limit) VALUES (?,?,?,?)",
                          (tid,fan_id,random.randint(0,8),9))

            for t in all_tops:
                mp = t['muddat'].split("-")
                oy,kun = int(mp[1]),int(mp[0])
                if (oy<4 or (oy==4 and kun<=15)) and not t['auditoriya']:
                    ball = round(random.uniform(t['maks']*0.5,t['maks']),1)
                    c.execute("INSERT OR IGNORE INTO yuklamalar (talaba_id,fan_id,topshiriq_id,holat,yuklangan_vaqt) VALUES (?,?,?,?,?)",
                              (tid,t['fan_id'],t['id'],'baholandi','2025-03-20 10:00:00'))
                    c.execute("INSERT OR IGNORE INTO baholar (talaba_id,fan_id,topshiriq_id,ball,izoh,oqituvchi_id,baholangan_vaqt) VALUES (?,?,?,?,?,?,?)",
                              (tid,t['fan_id'],t['id'],ball,'','TCH001','2025-03-25 10:00:00'))
            sid += 1

    conn.commit()
    conn.close()
    print("Database seeded successfully!")

def get_fan_data(conn, talaba_id, fan_id):
    fan = conn.execute("SELECT * FROM fanlar WHERE id=?", (fan_id,)).fetchone()
    tf  = conn.execute("SELECT * FROM talaba_fanlar WHERE talaba_id=? AND fan_id=?", (talaba_id,fan_id)).fetchone()
    tops = conn.execute("SELECT * FROM topshiriqlar WHERE fan_id=? ORDER BY id", (fan_id,)).fetchall()
    topshiriqlar = []
    for t in tops:
        yuk = conn.execute("SELECT * FROM yuklamalar WHERE talaba_id=? AND topshiriq_id=?", (talaba_id,t['id'])).fetchone()
        bah = conn.execute("SELECT * FROM baholar WHERE talaba_id=? AND topshiriq_id=?", (talaba_id,t['id'])).fetchone()
        ball = round(bah['ball']*10)/10 if bah and bah['ball'] is not None else None
        topshiriqlar.append({
            'id':t['id'],'fan_id':t['fan_id'],'nom':t['nom'],'turi':t['turi'],
            'muddat':t['muddat'],'maks':t['maks'],
            'mustaqil':bool(t['mustaqil']),'auditoriya':bool(t['auditoriya']),
            'yuklandi':yuk is not None,
            'yuklangan_vaqt':yuk['yuklangan_vaqt'] if yuk else None,
            'ball':ball,'izoh':bah['izoh'] if bah else '',
            'holat':'baholandi' if bah else ('yuklandi' if yuk else 'pending'),
        })
    return {
        'id':fan['id'],'nom':fan['nom'],'kod':fan['kod'],'kredit':fan['kredit'],
        'oqituvchi':f"{fan['maruza_oquv']} / {fan['amaliyot_oquv']}",
        'maruza_oquv':fan['maruza_oquv'],'amaliyot_oquv':fan['amaliyot_oquv'],
        'davomatSoni':tf['davomat_soni'] if tf else 0,
        'davomatLimit':tf['davomat_limit'] if tf else 9,
        'topshiriqlar':topshiriqlar,
    }

def take_snapshot(nom):
    conn = get_db()
    data = {
        'baholar':[dict(r) for r in conn.execute("SELECT * FROM baholar").fetchall()],
        'yuklamalar':[dict(r) for r in conn.execute("SELECT * FROM yuklamalar").fetchall()],
        'davomatlar':[dict(r) for r in conn.execute("SELECT * FROM davomatlar").fetchall()],
        'talaba_fanlar':[dict(r) for r in conn.execute("SELECT * FROM talaba_fanlar").fetchall()],
    }
    t = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("INSERT INTO snapshots (nom,yaratilgan,data) VALUES (?,?,?)",
                 (nom,t,json.dumps(data,ensure_ascii=False)))
    conn.commit(); conn.close()
    return t

def restore_snapshot(snap_id):
    conn = get_db()
    snap = conn.execute("SELECT * FROM snapshots WHERE id=?", (snap_id,)).fetchone()
    if not snap: conn.close(); return False
    data = json.loads(snap['data'])
    conn.execute("DELETE FROM baholar")
    conn.execute("DELETE FROM yuklamalar")
    conn.execute("DELETE FROM davomatlar")
    for r in data['baholar']:
        conn.execute("INSERT OR IGNORE INTO baholar (talaba_id,fan_id,topshiriq_id,ball,izoh,oqituvchi_id,baholangan_vaqt) VALUES (?,?,?,?,?,?,?)",
                     (r['talaba_id'],r['fan_id'],r['topshiriq_id'],r['ball'],r['izoh'],r['oqituvchi_id'],r['baholangan_vaqt']))
    for r in data['yuklamalar']:
        conn.execute("INSERT OR IGNORE INTO yuklamalar (talaba_id,fan_id,topshiriq_id,holat,yuklangan_vaqt) VALUES (?,?,?,?,?)",
                     (r['talaba_id'],r['fan_id'],r['topshiriq_id'],r['holat'],r['yuklangan_vaqt']))
    for r in data['davomatlar']:
        conn.execute("INSERT OR IGNORE INTO davomatlar (talaba_id,fan_id,sana,holat,oqituvchi_id) VALUES (?,?,?,?,?)",
                     (r['talaba_id'],r['fan_id'],r['sana'],r['holat'],r['oqituvchi_id']))
    conn.commit(); conn.close()
    return True

def reset_to_initial():
    conn = get_db()
    conn.execute("DELETE FROM baholar")
    conn.execute("DELETE FROM yuklamalar")
    conn.execute("DELETE FROM davomatlar")
    conn.execute("UPDATE talaba_fanlar SET davomat_soni=0")
    conn.commit(); conn.close()
    seed_db()

if __name__ == "__main__":
    init_db(); seed_db()
