from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
from functools import wraps
import json
import os

from database import get_db, init_db, seed_db, take_snapshot, restore_snapshot, reset_to_initial

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY', 'tatu-lms-secret-2025')
CORS(app, supports_credentials=True)

# ===== HELPERS =====
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Tizimga kirmagan'}), 401
        return f(*args, **kwargs)
    return decorated

def require_teacher(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Tizimga kirmagan'}), 401
        if session.get('user_type') not in ('oqituvchi', 'admin'):
            return jsonify({'error': 'Ruxsat yoq'}), 403
        return f(*args, **kwargs)
    return decorated

def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('user_type') != 'admin':
            return jsonify({'error': 'Admin ruxsati talab etiladi'}), 403
        return f(*args, **kwargs)
    return decorated

def fmt_ball(val):
    if val is None:
        return None
    return round(val * 10) / 10

def get_fan_data(conn, talaba_id, fan_id):
    """Bitta talabaning bitta fanidagi to'liq ma'lumot"""
    fan = conn.execute("SELECT * FROM fanlar WHERE id=?", (fan_id,)).fetchone()
    tf  = conn.execute("SELECT * FROM talaba_fanlar WHERE talaba_id=? AND fan_id=?",
                       (talaba_id, fan_id)).fetchone()
    tops = conn.execute("SELECT * FROM topshiriqlar WHERE fan_id=? ORDER BY id", (fan_id,)).fetchall()

    topshiriqlar = []
    for t in tops:
        yuk = conn.execute("SELECT * FROM yuklamalar WHERE talaba_id=? AND topshiriq_id=?",
                           (talaba_id, t['id'])).fetchone()
        bah = conn.execute("SELECT * FROM baholar WHERE talaba_id=? AND topshiriq_id=?",
                           (talaba_id, t['id'])).fetchone()
        topshiriqlar.append({
            'id': t['id'],
            'fan_id': t['fan_id'],
            'nom': t['nom'],
            'turi': t['turi'],
            'muddat': t['muddat'],
            'maks': t['maks'],
            'mustaqil': bool(t['mustaqil']),
            'auditoriya': bool(t['auditoriya']),
            'yuklandi': yuk is not None,
            'yuklangan_vaqt': yuk['yuklangan_vaqt'] if yuk else None,
            'ball': fmt_ball(bah['ball']) if bah else None,
            'izoh': bah['izoh'] if bah else '',
            'baholangan_vaqt': bah['baholangan_vaqt'] if bah else None,
            'holat': 'baholandi' if bah else ('yuklandi' if yuk else 'pending'),
        })

    return {
        'id': fan['id'],
        'nom': fan['nom'],
        'kod': fan['kod'],
        'kredit': fan['kredit'],
        'oqituvchi': f"{fan['maruza_oquv']} / {fan['amaliyot_oquv']}",
        'maruza_oquv': fan['maruza_oquv'],
        'amaliyot_oquv': fan['amaliyot_oquv'],
        'davomatSoni': tf['davomat_soni'] if tf else 0,
        'davomatLimit': tf['davomat_limit'] if tf else 9,
        'topshiriqlar': topshiriqlar,
    }

# ===== AUTH =====
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    login_id = data.get('login', '').strip()
    parol    = data.get('parol', '').strip()

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=? AND parol=?", (login_id, parol)).fetchone()
    conn.close()

    if not user:
        return jsonify({'error': "Login yoki parol notoggri!"}), 401

    session['user_id']   = user['id']
    session['user_type'] = user['type']

    return jsonify({'ok': True, 'type': user['type'], 'id': user['id']})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'ok': True})

@app.route('/api/me', methods=['GET'])
@require_auth
def me():
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()

    if user['type'] == 'talaba':
        fanlar = []
        for fan_id in range(1, 6):
            fanlar.append(get_fan_data(conn, user['id'], fan_id))
        result = {
            'id': user['id'], 'type': user['type'],
            'ism': user['ism'], 'qisqa': user['qisqa'], 'initials': user['initials'],
            'jins': user['jins'], 'guruh': user['guruh'], 'yonalish': user['yonalish'],
            'til': user['til'], 'daraja': user['daraja'], 'shakl': user['shakl'],
            'kurs': user['kurs'], 'murabbiy': user['murabbiy'],
            'stipendiya': user['stipendiya'], 'tugilgan': user['tugilgan'],
            'gpaHistory': json.loads(user['gpa_history'] or '[]'),
            'fanlar': fanlar,
        }
    else:
        # Oqituvchi uchun o'z fanlari
        fanlar_list = conn.execute(
            "SELECT * FROM fanlar WHERE maruza_oquv=? OR amaliyot_oquv=?",
            (user['qisqa'], user['qisqa'])
        ).fetchall()
        result = {
            'id': user['id'], 'type': user['type'],
            'ism': user['ism'], 'qisqa': user['qisqa'], 'initials': user['initials'],
            'kafedra': user['kafedra'], 'lavozim': user['lavozim'],
            'fanlar': [{'id': f['id'], 'nom': f['nom'], 'kod': f['kod']} for f in fanlar_list],
        }
    conn.close()
    return jsonify(result)

# ===== TALABA API =====
@app.route('/api/talaba/fanlar', methods=['GET'])
@require_auth
def talaba_fanlar():
    conn = get_db()
    fanlar = []
    for fan_id in range(1, 6):
        fanlar.append(get_fan_data(conn, session['user_id'], fan_id))
    conn.close()
    return jsonify(fanlar)

@app.route('/api/talaba/yuklash', methods=['POST'])
@require_auth
def talaba_yuklash():
    """Talaba topshiriq yuklaydi"""
    data = request.json
    talaba_id    = session['user_id']
    topshiriq_id = data.get('topshiriq_id')
    fan_id       = data.get('fan_id')

    conn = get_db()

    # Topshiriq mavjudligini tekshirish
    top = conn.execute("SELECT * FROM topshiriqlar WHERE id=?", (topshiriq_id,)).fetchone()
    if not top:
        conn.close()
        return jsonify({'error': 'Topshiriq topilmadi'}), 404

    # Auditoriya topshirig'ini yuklab bo'lmaydi
    if top['auditoriya']:
        conn.close()
        return jsonify({'error': 'Bu topshiriq auditoriyada baholanadi'}), 400

    # Allaqachon baholangan bo'lsa
    bah = conn.execute("SELECT * FROM baholar WHERE talaba_id=? AND topshiriq_id=?",
                       (talaba_id, topshiriq_id)).fetchone()
    if bah:
        conn.close()
        return jsonify({'error': 'Bu topshiriq allaqachon baholangan'}), 400

    vaqt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Muddat tekshirish
    muddat_parts = top['muddat'].split("-")
    muddat_date  = datetime(int(muddat_parts[2]), int(muddat_parts[1]), int(muddat_parts[0]))
    holat = 'kechikdi' if datetime.now() > muddat_date else 'yuklandi'

    conn.execute("""INSERT OR REPLACE INTO yuklamalar
        (talaba_id, fan_id, topshiriq_id, holat, yuklangan_vaqt)
        VALUES (?,?,?,?,?)""",
        (talaba_id, fan_id, topshiriq_id, holat, vaqt))
    conn.commit()
    conn.close()

    return jsonify({'ok': True, 'holat': holat, 'yuklangan_vaqt': vaqt})

@app.route('/api/talaba/reyting/<int:fan_id>', methods=['GET'])
@require_auth
def talaba_reyting(fan_id):
    """Guruh reytingi"""
    talaba_id = session['user_id']
    conn = get_db()
    user = conn.execute("SELECT guruh FROM users WHERE id=?", (talaba_id,)).fetchone()
    guruh = user['guruh']

    guruh_talabalar = conn.execute(
        "SELECT id, qisqa FROM users WHERE type='talaba' AND guruh=?", (guruh,)
    ).fetchall()

    result = []
    for t in guruh_talabalar:
        if fan_id == 0:  # GPA
            # Hamma fanlardan ball hisoblash
            total_ball = 0; total_maks = 0
            for fid in range(1, 6):
                tops = conn.execute("SELECT t.maks, b.ball FROM topshiriqlar t "
                    "LEFT JOIN baholar b ON b.topshiriq_id=t.id AND b.talaba_id=? "
                    "WHERE t.fan_id=?", (t['id'], fid)).fetchall()
                for row in tops:
                    total_maks += row['maks']
                    if row['ball'] is not None:
                        total_ball += row['ball']
            pct = total_ball / total_maks * 100 if total_maks > 0 else 0
            baho = 5 if pct>=90 else 4 if pct>=70 else 3 if pct>=60 else 2
            result.append({'id': t['id'], 'ism': t['qisqa'], 'val': round(baho, 2), 'men': t['id']==talaba_id})
        else:
            tops = conn.execute("SELECT t.maks, b.ball FROM topshiriqlar t "
                "LEFT JOIN baholar b ON b.topshiriq_id=t.id AND b.talaba_id=? "
                "WHERE t.fan_id=?", (t['id'], fan_id)).fetchall()
            ball = sum(r['ball'] for r in tops if r['ball'] is not None)
            result.append({'id': t['id'], 'ism': t['qisqa'], 'val': fmt_ball(ball), 'men': t['id']==talaba_id})

    result.sort(key=lambda x: -x['val'])
    for i, r in enumerate(result):
        r['rank'] = i + 1

    conn.close()
    return jsonify(result)

# ===== OQITUVCHI API =====
@app.route('/api/teacher/talabalar', methods=['GET'])
@require_teacher
def teacher_talabalar():
    """Oqituvchining talabalar ro'yxati"""
    guruh = request.args.get('guruh')
    conn  = get_db()
    teacher = conn.execute("SELECT qisqa FROM users WHERE id=?", (session['user_id'],)).fetchone()
    tch_nom = teacher['qisqa']

    # Oqituvchi fanlarini topish
    my_fans = conn.execute(
        "SELECT id FROM fanlar WHERE maruza_oquv=? OR amaliyot_oquv=?", (tch_nom, tch_nom)
    ).fetchall()
    fan_ids = [f['id'] for f in my_fans]

    query = "SELECT * FROM users WHERE type='talaba'"
    params = []
    if guruh and guruh != 'all':
        query += " AND guruh=?"
        params.append(guruh)

    talabalar = conn.execute(query, params).fetchall()

    result = []
    for t in talabalar:
        fan_data = []
        for fid in fan_ids:
            fd = get_fan_data(conn, t['id'], fid)
            joriy = sum(tp['ball'] for tp in fd['topshiriqlar'] if tp['ball'] is not None)
            total = sum(tp['maks'] for tp in fd['topshiriqlar'])
            fan_data.append({
                'fan_id': fid,
                'joriy': fmt_ball(joriy),
                'totalMaks': total,
                'oz': round(joriy/total*100) if total > 0 else 0,
                'davomat': fd['davomatSoni'],
                'davomatLimit': fd['davomatLimit'],
            })
        result.append({
            'id': t['id'], 'ism': t['qisqa'], 'guruh': t['guruh'],
            'fanlar': fan_data,
        })

    conn.close()
    return jsonify(result)

@app.route('/api/teacher/baholanmaganlar', methods=['GET'])
@require_teacher
def teacher_baholanmaganlar():
    """Baholanmagan yuklamalar (deadline + 3 kun)"""
    conn = get_db()
    teacher = conn.execute("SELECT qisqa FROM users WHERE id=?", (session['user_id'],)).fetchone()
    tch_nom = teacher['qisqa']

    # Oqituvchi fanlari
    my_fans = conn.execute(
        "SELECT id FROM fanlar WHERE maruza_oquv=? OR amaliyot_oquv=?", (tch_nom, tch_nom)
    ).fetchall()
    fan_ids = [f['id'] for f in my_fans]

    result = []
    now = datetime.now()

    for fan_id in fan_ids:
        tops = conn.execute("SELECT * FROM topshiriqlar WHERE fan_id=? AND auditoriya=0", (fan_id,)).fetchall()
        for t in tops:
            muddat_parts = t['muddat'].split("-")
            muddat_date  = datetime(int(muddat_parts[2]), int(muddat_parts[1]), int(muddat_parts[0]))
            deadline_plus3 = muddat_date + timedelta(days=3)

            # Baholash oynasi: deadline dan 3 kun ichida
            if now > deadline_plus3:
                continue

            # Bu topshiriqni yuklagan lekin baholanmagan talabalar
            yuklamalar = conn.execute("""
                SELECT y.*, u.qisqa as talaba_ism, u.guruh
                FROM yuklamalar y
                JOIN users u ON u.id = y.talaba_id
                WHERE y.topshiriq_id=?
                AND NOT EXISTS (SELECT 1 FROM baholar b WHERE b.talaba_id=y.talaba_id AND b.topshiriq_id=y.topshiriq_id)
            """, (t['id'],)).fetchall()

            for y in yuklamalar:
                kun_qoldi = (deadline_plus3 - now).days
                result.append({
                    'talaba_id': y['talaba_id'],
                    'talaba': y['talaba_ism'],
                    'guruh': y['guruh'],
                    'fan_id': fan_id,
                    'topshiriq_id': t['id'],
                    'topshiriq': t['nom'],
                    'maks': t['maks'],
                    'muddat': t['muddat'],
                    'yuklangan': y['yuklangan_vaqt'],
                    'kun_qoldi': kun_qoldi,
                })

        # Auditoriya topshiriqlari — barcha talabalar uchun baholash
        audit_tops = conn.execute(
            "SELECT * FROM topshiriqlar WHERE fan_id=? AND auditoriya=1", (fan_id,)
        ).fetchall()
        for t in audit_tops:
            muddat_parts = t['muddat'].split("-")
            muddat_date  = datetime(int(muddat_parts[2]), int(muddat_parts[1]), int(muddat_parts[0]))
            deadline_plus3 = muddat_date + timedelta(days=3)
            if now > deadline_plus3:
                continue

            talabalar = conn.execute("SELECT id, qisqa, guruh FROM users WHERE type='talaba'").fetchall()
            for tal in talabalar:
                bah = conn.execute("SELECT * FROM baholar WHERE talaba_id=? AND topshiriq_id=?",
                                   (tal['id'], t['id'])).fetchone()
                if not bah:
                    kun_qoldi = (deadline_plus3 - now).days
                    result.append({
                        'talaba_id': tal['id'],
                        'talaba': tal['qisqa'],
                        'guruh': tal['guruh'],
                        'fan_id': fan_id,
                        'topshiriq_id': t['id'],
                        'topshiriq': t['nom'],
                        'maks': t['maks'],
                        'muddat': t['muddat'],
                        'yuklangan': None,
                        'kun_qoldi': kun_qoldi,
                        'auditoriya': True,
                    })

    result.sort(key=lambda x: x['kun_qoldi'])
    conn.close()
    return jsonify(result)

@app.route('/api/teacher/baho', methods=['POST'])
@require_teacher
def teacher_baho():
    """Ball qo'yish va izoh"""
    data         = request.json
    talaba_id    = data.get('talaba_id')
    topshiriq_id = data.get('topshiriq_id')
    fan_id       = data.get('fan_id')
    ball         = data.get('ball')
    izoh         = data.get('izoh', '')
    oqituvchi_id = session['user_id']

    conn = get_db()

    # Topshiriq mavjudligini tekshirish
    top = conn.execute("SELECT * FROM topshiriqlar WHERE id=?", (topshiriq_id,)).fetchone()
    if not top:
        conn.close()
        return jsonify({'error': 'Topshiriq topilmadi'}), 404

    # Ball chegarasi
    if ball is None or ball < 0 or ball > top['maks']:
        conn.close()
        return jsonify({'error': f"Ball 0 dan {top['maks']} gacha bolishi kerak"}), 400

    # Baholash muddati (deadline + 3 kun)
    muddat_parts   = top['muddat'].split("-")
    muddat_date    = datetime(int(muddat_parts[2]), int(muddat_parts[1]), int(muddat_parts[0]))
    deadline_plus3 = muddat_date + timedelta(days=3)

    # Agar allaqachon baho bor bo'lsa — tekshirish
    existing = conn.execute("SELECT * FROM baholar WHERE talaba_id=? AND topshiriq_id=?",
                            (talaba_id, topshiriq_id)).fetchone()
    if existing:
        bah_date = datetime.strptime(existing['baholangan_vaqt'], "%Y-%m-%d %H:%M:%S")
        if datetime.now() > deadline_plus3:
            conn.close()
            return jsonify({'error': 'Baholash muddati tugagan (deadline + 3 kun)'}), 400

    ball_rounded = round(float(ball) * 10) / 10
    vaqt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn.execute("""INSERT OR REPLACE INTO baholar
        (talaba_id, fan_id, topshiriq_id, ball, izoh, oqituvchi_id, baholangan_vaqt)
        VALUES (?,?,?,?,?,?,?)""",
        (talaba_id, fan_id, topshiriq_id, ball_rounded, izoh, oqituvchi_id, vaqt))
    conn.commit()
    conn.close()

    return jsonify({'ok': True, 'ball': ball_rounded, 'baholangan_vaqt': vaqt})

@app.route('/api/teacher/davomat', methods=['POST'])
@require_teacher
def teacher_davomat():
    """Davomat belgilash"""
    data         = request.json
    fan_id       = data.get('fan_id')
    sana         = data.get('sana')  # "15-04-2025" formatida
    davomatlar   = data.get('davomatlar', [])  # [{talaba_id, holat}]
    oqituvchi_id = session['user_id']

    conn = get_db()
    for d in davomatlar:
        talaba_id = d['talaba_id']
        holat     = d['holat']  # 'keldi' | 'kelmadi' | 'sababli'

        conn.execute("""INSERT OR REPLACE INTO davomatlar
            (talaba_id, fan_id, sana, holat, oqituvchi_id)
            VALUES (?,?,?,?,?)""",
            (talaba_id, fan_id, sana, holat, oqituvchi_id))

        # Davomat sonini yangilash (faqat 'kelmadi' va 'sababli')
        if holat in ('kelmadi', 'sababli'):
            conn.execute("""UPDATE talaba_fanlar
                SET davomat_soni = davomat_soni + 1
                WHERE talaba_id=? AND fan_id=?
                AND davomat_soni < davomat_limit""",
                (talaba_id, fan_id))
        elif holat == 'keldi':
            # Agar avval kelmadi deb belgilangan bo'lsa, bir kamaytirish
            prev = conn.execute("SELECT holat FROM davomatlar WHERE talaba_id=? AND fan_id=? AND sana=?",
                               (talaba_id, fan_id, sana)).fetchone()
            if prev and prev['holat'] in ('kelmadi', 'sababli'):
                conn.execute("""UPDATE talaba_fanlar
                    SET davomat_soni = MAX(0, davomat_soni - 1)
                    WHERE talaba_id=? AND fan_id=?""",
                    (talaba_id, fan_id))

    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'saqlanganlar': len(davomatlar)})

@app.route('/api/teacher/topshiriqlar/<int:fan_id>', methods=['GET'])
@require_teacher
def teacher_topshiriqlar(fan_id):
    """Fan topshiriqlari va barcha talabalar holati"""
    conn    = get_db()
    tops    = conn.execute("SELECT * FROM topshiriqlar WHERE fan_id=? ORDER BY id", (fan_id,)).fetchall()
    result  = []
    for t in tops:
        talabalar = conn.execute("SELECT id, qisqa, guruh FROM users WHERE type='talaba'").fetchall()
        talaba_data = []
        for tal in talabalar:
            yuk = conn.execute("SELECT * FROM yuklamalar WHERE talaba_id=? AND topshiriq_id=?",
                               (tal['id'], t['id'])).fetchone()
            bah = conn.execute("SELECT * FROM baholar WHERE talaba_id=? AND topshiriq_id=?",
                               (tal['id'], t['id'])).fetchone()
            talaba_data.append({
                'id': tal['id'], 'ism': tal['qisqa'], 'guruh': tal['guruh'],
                'yuklandi': yuk is not None,
                'ball': fmt_ball(bah['ball']) if bah else None,
                'izoh': bah['izoh'] if bah else '',
            })
        result.append({
            'id': t['id'], 'nom': t['nom'], 'turi': t['turi'],
            'muddat': t['muddat'], 'maks': t['maks'],
            'auditoriya': bool(t['auditoriya']),
            'talabalar': talaba_data,
        })
    conn.close()
    return jsonify(result)

# ===== ADMIN API =====
@app.route('/api/admin/snapshot', methods=['POST'])
@require_admin
def admin_snapshot():
    nom = request.json.get('nom', f"Snapshot {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    yaratilgan = take_snapshot(nom)
    return jsonify({'ok': True, 'yaratilgan': yaratilgan, 'nom': nom})

@app.route('/api/admin/snapshots', methods=['GET'])
@require_admin
def admin_snapshots():
    conn = get_db()
    snaps = conn.execute("SELECT id, nom, yaratilgan FROM snapshots ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(s) for s in snaps])

@app.route('/api/admin/restore/<int:snap_id>', methods=['POST'])
@require_admin
def admin_restore(snap_id):
    ok = restore_snapshot(snap_id)
    if ok:
        return jsonify({'ok': True})
    return jsonify({'error': 'Snapshot topilmadi'}), 404

@app.route('/api/admin/reset', methods=['POST'])
@require_admin
def admin_reset():
    # Avval snapshot olamiz
    take_snapshot(f"Reset oldidan — {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    reset_to_initial()
    return jsonify({'ok': True})

@app.route('/api/admin/users', methods=['GET'])
@require_admin
def admin_users():
    conn = get_db()
    users = conn.execute("SELECT id, type, ism, qisqa, guruh, parol FROM users ORDER BY type, id").fetchall()
    conn.close()
    return jsonify([dict(u) for u in users])

# ===== POLLING — real-time yangilash uchun =====
@app.route('/api/poll', methods=['GET'])
@require_auth
def poll():
    """Har 5 sekundda chaqiriladi — yangiliklar bormi?"""
    since = request.args.get('since', '')  # ISO timestamp
    conn  = get_db()
    uid   = session['user_id']
    utype = session.get('user_type')

    changes = {'changed': False, 'data': {}}

    if utype == 'talaba':
        # Yangi baholar bormi?
        if since:
            new_bahos = conn.execute("""
                SELECT b.*, t.nom as top_nom, t.fan_id
                FROM baholar b
                JOIN topshiriqlar t ON t.id = b.topshiriq_id
                WHERE b.talaba_id=? AND b.baholangan_vaqt > ?
            """, (uid, since)).fetchall()
        else:
            new_bahos = []

        if new_bahos:
            changes['changed'] = True
            changes['data']['new_baholar'] = [dict(b) for b in new_bahos]

        # Davomat o'zgardimi?
        if since:
            new_dav = conn.execute("""
                SELECT * FROM davomatlar
                WHERE talaba_id=?
            """, (uid,)).fetchall()
            if new_dav:
                changes['data']['davomatlar'] = [dict(d) for d in new_dav]

    elif utype == 'oqituvchi':
        # Yangi yuklamalar bormi?
        teacher = conn.execute("SELECT qisqa FROM users WHERE id=?", (uid,)).fetchone()
        tch_nom = teacher['qisqa']
        my_fans = conn.execute(
            "SELECT id FROM fanlar WHERE maruza_oquv=? OR amaliyot_oquv=?",
            (tch_nom, tch_nom)
        ).fetchall()
        fan_ids = [f['id'] for f in my_fans]

        if since and fan_ids:
            placeholders = ','.join('?' * len(fan_ids))
            new_yuklamalar = conn.execute(f"""
                SELECT y.*, u.qisqa as talaba_ism, t.nom as top_nom
                FROM yuklamalar y
                JOIN users u ON u.id = y.talaba_id
                JOIN topshiriqlar t ON t.id = y.topshiriq_id
                WHERE y.fan_id IN ({placeholders})
                AND y.yuklangan_vaqt > ?
            """, fan_ids + [since]).fetchall()

            if new_yuklamalar:
                changes['changed'] = True
                changes['data']['new_yuklamalar'] = [dict(y) for y in new_yuklamalar]

    conn.close()
    changes['server_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return jsonify(changes)

# ===== STATIC FILES =====
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

# ===== STARTUP =====
if __name__ == '__main__':
    init_db()
    seed_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
