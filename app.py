from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
from functools import wraps
import json, os

from database import get_db, init_db, seed_db, get_fan_data, take_snapshot, restore_snapshot, reset_to_initial

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY', 'tatu-lms-2025')
CORS(app, supports_credentials=True)

# DB ni ishga tushirishda yaratamiz
with app.app_context():
    init_db()
    seed_db()

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
            return jsonify({'error': 'Admin ruxsati kerak'}), 403
        return f(*args, **kwargs)
    return decorated

def fmt(val):
    if val is None: return None
    return round(val * 10) / 10

# ===== AUTH =====
@app.route('/api/login', methods=['POST'])
def login():
    d = request.json or {}
    login_id = d.get('login', '').strip()
    parol    = d.get('parol', '').strip()
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=? AND parol=?", (login_id, parol)).fetchone()
    conn.close()
    if not user:
        return jsonify({'error': "Login yoki parol notogri!"}), 401
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
    if not user:
        conn.close()
        return jsonify({'error': 'Foydalanuvchi topilmadi'}), 404

    if user['type'] == 'talaba':
        fanlar = [get_fan_data(conn, user['id'], fid) for fid in range(1, 6)]
        result = {
            'id':user['id'], 'type':'talaba',
            'ism':user['ism'], 'qisqa':user['qisqa'], 'initials':user['initials'],
            'jins':user['jins'], 'guruh':user['guruh'], 'yonalish':user['yonalish'],
            'til':user['til'], 'daraja':user['daraja'], 'shakl':user['shakl'],
            'kurs':user['kurs'], 'murabbiy':user['murabbiy'],
            'stipendiya':user['stipendiya'], 'tugilgan':user['tugilgan'],
            'gpaHistory':json.loads(user['gpa_history'] or '[]'),
            'fanlar':fanlar,
        }
    elif user['type'] == 'oqituvchi':
        my_fans = conn.execute("SELECT * FROM fanlar WHERE maruza_oquv=? OR amaliyot_oquv=?",
                               (user['qisqa'], user['qisqa'])).fetchall()
        result = {
            'id':user['id'], 'type':'oqituvchi',
            'ism':user['ism'], 'qisqa':user['qisqa'], 'initials':user['initials'],
            'kafedra':user['kafedra'], 'lavozim':user['lavozim'],
            'fanlar':[{'id':f['id'],'nom':f['nom'],'kod':f['kod']} for f in my_fans],
        }
    else:
        result = {
            'id':user['id'], 'type':'admin',
            'ism':user['ism'], 'qisqa':user['qisqa'], 'initials':user['initials'],
        }
    conn.close()
    return jsonify(result)

# ===== TALABA =====
@app.route('/api/talaba/yuklash', methods=['POST'])
@require_auth
def talaba_yuklash():
    d = request.json or {}
    tid = session['user_id']
    top_id = d.get('topshiriq_id')
    fan_id = d.get('fan_id')
    conn = get_db()
    top = conn.execute("SELECT * FROM topshiriqlar WHERE id=?", (top_id,)).fetchone()
    if not top:
        conn.close(); return jsonify({'error': 'Topshiriq topilmadi'}), 404
    if top['auditoriya']:
        conn.close(); return jsonify({'error': 'Auditoriyada baholanadi'}), 400
    bah = conn.execute("SELECT 1 FROM baholar WHERE talaba_id=? AND topshiriq_id=?", (tid, top_id)).fetchone()
    if bah:
        conn.close(); return jsonify({'error': 'Allaqachon baholangan'}), 400
    mp = top['muddat'].split("-")
    muddat = datetime(int(mp[2]), int(mp[1]), int(mp[0]))
    holat = 'kechikdi' if datetime.now() > muddat else 'yuklandi'
    vaqt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("INSERT OR REPLACE INTO yuklamalar (talaba_id,fan_id,topshiriq_id,holat,yuklangan_vaqt) VALUES (?,?,?,?,?)",
                 (tid, fan_id, top_id, holat, vaqt))
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'holat': holat})

@app.route('/api/talaba/reyting/<int:fan_id>', methods=['GET'])
@require_auth
def talaba_reyting(fan_id):
    tid = session['user_id']
    conn = get_db()
    user = conn.execute("SELECT guruh FROM users WHERE id=?", (tid,)).fetchone()
    talabalar = conn.execute("SELECT id,qisqa FROM users WHERE type='talaba' AND guruh=?", (user['guruh'],)).fetchall()
    result = []
    for t in talabalar:
        if fan_id == 0:
            total_b, total_m = 0, 0
            for fid in range(1, 6):
                rows = conn.execute("SELECT t.maks, b.ball FROM topshiriqlar t LEFT JOIN baholar b ON b.topshiriq_id=t.id AND b.talaba_id=? WHERE t.fan_id=?", (t['id'],fid)).fetchall()
                for r in rows:
                    total_m += r['maks']
                    if r['ball']: total_b += r['ball']
            pct = total_b/total_m*100 if total_m else 0
            val = 5 if pct>=90 else 4 if pct>=70 else 3 if pct>=60 else 2
        else:
            rows = conn.execute("SELECT t.maks, b.ball FROM topshiriqlar t LEFT JOIN baholar b ON b.topshiriq_id=t.id AND b.talaba_id=? WHERE t.fan_id=?", (t['id'],fan_id)).fetchall()
            val = sum(r['ball'] for r in rows if r['ball'])
        result.append({'id':t['id'],'ism':t['qisqa'],'val':round(val,2),'men':t['id']==tid})
    result.sort(key=lambda x: -x['val'])
    for i,r in enumerate(result): r['rank'] = i+1
    conn.close()
    return jsonify(result)

# ===== OQITUVCHI =====
@app.route('/api/teacher/talabalar', methods=['GET'])
@require_teacher
def teacher_talabalar():
    guruh = request.args.get('guruh')
    conn = get_db()
    teacher = conn.execute("SELECT qisqa FROM users WHERE id=?", (session['user_id'],)).fetchone()
    my_fans = conn.execute("SELECT id FROM fanlar WHERE maruza_oquv=? OR amaliyot_oquv=?",
                           (teacher['qisqa'], teacher['qisqa'])).fetchall()
    fan_ids = [f['id'] for f in my_fans]
    q = "SELECT * FROM users WHERE type='talaba'"
    params = []
    if guruh and guruh != 'all':
        q += " AND guruh=?"; params.append(guruh)
    talabalar = conn.execute(q, params).fetchall()
    result = []
    for t in talabalar:
        fan_data = []
        for fid in fan_ids:
            fd = get_fan_data(conn, t['id'], fid)
            joriy = sum(tp['ball'] for tp in fd['topshiriqlar'] if tp['ball'] is not None)
            total = sum(tp['maks'] for tp in fd['topshiriqlar'])
            fan_data.append({'fan_id':fid,'joriy':fmt(joriy),'totalMaks':total,
                             'oz':round(joriy/total*100) if total else 0,
                             'davomat':fd['davomatSoni'],'davomatLimit':fd['davomatLimit']})
        result.append({'id':t['id'],'ism':t['qisqa'],'guruh':t['guruh'],'fanlar':fan_data})
    conn.close()
    return jsonify(result)

@app.route('/api/teacher/baholanmaganlar', methods=['GET'])
@require_teacher
def teacher_baholanmaganlar():
    conn = get_db()
    teacher = conn.execute("SELECT qisqa FROM users WHERE id=?", (session['user_id'],)).fetchone()
    my_fans = conn.execute("SELECT id FROM fanlar WHERE maruza_oquv=? OR amaliyot_oquv=?",
                           (teacher['qisqa'], teacher['qisqa'])).fetchall()
    fan_ids = [f['id'] for f in my_fans]
    result = []
    now = datetime.now()
    for fan_id in fan_ids:
        fan = conn.execute("SELECT nom FROM fanlar WHERE id=?", (fan_id,)).fetchone()
        tops = conn.execute("SELECT * FROM topshiriqlar WHERE fan_id=?", (fan_id,)).fetchall()
        for t in tops:
            mp = t['muddat'].split("-")
            muddat = datetime(int(mp[2]), int(mp[1]), int(mp[0]))
            deadline3 = muddat + timedelta(days=3)
            if now > deadline3: continue
            if t['auditoriya']:
                talabalar = conn.execute("SELECT id,qisqa,guruh FROM users WHERE type='talaba'").fetchall()
                for tal in talabalar:
                    bah = conn.execute("SELECT 1 FROM baholar WHERE talaba_id=? AND topshiriq_id=?", (tal['id'],t['id'])).fetchone()
                    if not bah:
                        result.append({'talaba_id':tal['id'],'talaba':tal['qisqa'],'guruh':tal['guruh'],
                                       'fan_id':fan_id,'fan_nom':fan['nom'],'topshiriq_id':t['id'],
                                       'topshiriq':t['nom'],'maks':t['maks'],'muddat':t['muddat'],
                                       'kun_qoldi':(deadline3-now).days,'auditoriya':True})
            else:
                yuklamalar = conn.execute("""SELECT y.*,u.qisqa as ism,u.guruh FROM yuklamalar y
                    JOIN users u ON u.id=y.talaba_id WHERE y.topshiriq_id=?
                    AND NOT EXISTS (SELECT 1 FROM baholar b WHERE b.talaba_id=y.talaba_id AND b.topshiriq_id=y.topshiriq_id)""",
                    (t['id'],)).fetchall()
                for y in yuklamalar:
                    result.append({'talaba_id':y['talaba_id'],'talaba':y['ism'],'guruh':y['guruh'],
                                   'fan_id':fan_id,'fan_nom':fan['nom'],'topshiriq_id':t['id'],
                                   'topshiriq':t['nom'],'maks':t['maks'],'muddat':t['muddat'],
                                   'kun_qoldi':(deadline3-now).days})
    result.sort(key=lambda x: x['kun_qoldi'])
    conn.close()
    return jsonify(result)

@app.route('/api/teacher/baho', methods=['POST'])
@require_teacher
def teacher_baho():
    d = request.json or {}
    talaba_id = d.get('talaba_id')
    top_id    = d.get('topshiriq_id')
    fan_id    = d.get('fan_id')
    ball      = d.get('ball')
    izoh      = d.get('izoh', '')
    oquv_id   = session['user_id']
    conn = get_db()
    top = conn.execute("SELECT * FROM topshiriqlar WHERE id=?", (top_id,)).fetchone()
    if not top:
        conn.close(); return jsonify({'error': 'Topshiriq topilmadi'}), 404
    if ball is None or float(ball) < 0 or float(ball) > top['maks']:
        conn.close(); return jsonify({'error': f"Ball 0-{top['maks']} orasida bolsin"}), 400
    mp = top['muddat'].split("-")
    muddat = datetime(int(mp[2]), int(mp[1]), int(mp[0]))
    if datetime.now() > muddat + timedelta(days=3):
        conn.close(); return jsonify({'error': 'Baholash muddati tugagan'}), 400
    ball_r = round(float(ball)*10)/10
    vaqt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("INSERT OR REPLACE INTO baholar (talaba_id,fan_id,topshiriq_id,ball,izoh,oqituvchi_id,baholangan_vaqt) VALUES (?,?,?,?,?,?,?)",
                 (talaba_id, fan_id, top_id, ball_r, izoh, oquv_id, vaqt))
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'ball': ball_r})

@app.route('/api/teacher/davomat', methods=['POST'])
@require_teacher
def teacher_davomat():
    d = request.json or {}
    fan_id     = d.get('fan_id')
    sana       = d.get('sana')
    davomatlar = d.get('davomatlar', [])
    oquv_id    = session['user_id']
    conn = get_db()
    for item in davomatlar:
        tid   = item['talaba_id']
        holat = item['holat']
        old = conn.execute("SELECT holat FROM davomatlar WHERE talaba_id=? AND fan_id=? AND sana=?", (tid,fan_id,sana)).fetchone()
        conn.execute("INSERT OR REPLACE INTO davomatlar (talaba_id,fan_id,sana,holat,oqituvchi_id) VALUES (?,?,?,?,?)",
                     (tid, fan_id, sana, holat, oquv_id))
        if holat in ('kelmadi','sababli') and (not old or old['holat'] == 'keldi'):
            conn.execute("UPDATE talaba_fanlar SET davomat_soni=MIN(davomat_limit, davomat_soni+1) WHERE talaba_id=? AND fan_id=?", (tid,fan_id))
        elif holat == 'keldi' and old and old['holat'] in ('kelmadi','sababli'):
            conn.execute("UPDATE talaba_fanlar SET davomat_soni=MAX(0, davomat_soni-1) WHERE talaba_id=? AND fan_id=?", (tid,fan_id))
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'saqlanganlar': len(davomatlar)})

@app.route('/api/teacher/topshiriqlar/<int:fan_id>', methods=['GET'])
@require_teacher
def teacher_topshiriqlar(fan_id):
    conn = get_db()
    tops = conn.execute("SELECT * FROM topshiriqlar WHERE fan_id=? ORDER BY id", (fan_id,)).fetchall()
    talabalar = conn.execute("SELECT id,qisqa,guruh FROM users WHERE type='talaba'").fetchall()
    result = []
    for t in tops:
        tdata = []
        for tal in talabalar:
            yuk = conn.execute("SELECT 1 FROM yuklamalar WHERE talaba_id=? AND topshiriq_id=?", (tal['id'],t['id'])).fetchone()
            bah = conn.execute("SELECT ball,izoh FROM baholar WHERE talaba_id=? AND topshiriq_id=?", (tal['id'],t['id'])).fetchone()
            tdata.append({'id':tal['id'],'ism':tal['qisqa'],'guruh':tal['guruh'],
                          'yuklandi':yuk is not None,'ball':fmt(bah['ball']) if bah else None,
                          'izoh':bah['izoh'] if bah else ''})
        result.append({'id':t['id'],'nom':t['nom'],'turi':t['turi'],'muddat':t['muddat'],
                       'maks':t['maks'],'auditoriya':bool(t['auditoriya']),'talabalar':tdata})
    conn.close()
    return jsonify(result)

# ===== POLL =====
@app.route('/api/poll', methods=['GET'])
@require_auth
def poll():
    since = request.args.get('since', '')
    conn  = get_db()
    uid   = session['user_id']
    utype = session.get('user_type')
    changes = {'changed': False, 'data': {}}
    if utype == 'talaba' and since:
        new_b = conn.execute("SELECT * FROM baholar WHERE talaba_id=? AND baholangan_vaqt>?", (uid,since)).fetchall()
        if new_b:
            changes['changed'] = True
            changes['data']['new_baholar'] = [dict(b) for b in new_b]
    elif utype == 'oqituvchi' and since:
        teacher = conn.execute("SELECT qisqa FROM users WHERE id=?", (uid,)).fetchone()
        my_fans = conn.execute("SELECT id FROM fanlar WHERE maruza_oquv=? OR amaliyot_oquv=?",
                               (teacher['qisqa'],teacher['qisqa'])).fetchall()
        fan_ids = [f['id'] for f in my_fans]
        if fan_ids:
            ph = ','.join('?'*len(fan_ids))
            new_y = conn.execute(f"SELECT y.*,u.qisqa as ism FROM yuklamalar y JOIN users u ON u.id=y.talaba_id WHERE y.fan_id IN ({ph}) AND y.yuklangan_vaqt>?",
                                 fan_ids+[since]).fetchall()
            if new_y:
                changes['changed'] = True
                changes['data']['new_yuklamalar'] = [dict(y) for y in new_y]
    changes['server_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.close()
    return jsonify(changes)

# ===== ADMIN =====
@app.route('/api/admin/snapshot', methods=['POST'])
@require_admin
def admin_snapshot():
    nom = (request.json or {}).get('nom', f"Snapshot {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    t = take_snapshot(nom)
    return jsonify({'ok': True, 'yaratilgan': t, 'nom': nom})

@app.route('/api/admin/snapshots', methods=['GET'])
@require_admin
def admin_snapshots():
    conn = get_db()
    snaps = conn.execute("SELECT id,nom,yaratilgan FROM snapshots ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(s) for s in snaps])

@app.route('/api/admin/restore/<int:snap_id>', methods=['POST'])
@require_admin
def admin_restore(snap_id):
    ok = restore_snapshot(snap_id)
    return jsonify({'ok': True}) if ok else jsonify({'error': 'Topilmadi'}), 404

@app.route('/api/admin/reset', methods=['POST'])
@require_admin
def admin_reset():
    take_snapshot(f"Reset oldidan {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    reset_to_initial()
    return jsonify({'ok': True})

@app.route('/api/admin/users', methods=['GET'])
@require_admin
def admin_users():
    conn = get_db()
    users = conn.execute("SELECT id,type,ism,qisqa,guruh,parol FROM users ORDER BY type,id").fetchall()
    conn.close()
    return jsonify([dict(u) for u in users])

# ===== STATIC =====
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
