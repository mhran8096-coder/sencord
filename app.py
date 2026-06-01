
import os
import socket
import threading
import time
import traceback
import webview
import sys # ضيف المكتبة دي فوق
import json

# الدالة دي بتخلي البرنامج يلاقي ملفاته سواء كان كود عادي أو EXE
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
import firebase_admin
from firebase_admin import credentials, db

# --- 1. إعدادات فايربيس ---
# تعديل الكود ليكون آمن للـ EXE
# تأكد إن السطور داخل الـ try داخلة لجوه (سبيس واحدة أو تاب)
try:
    key_path = resource_path('firebase_key.json')
    cred = credentials.Certificate(key_path)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://sencord-99002-default-rtdb.firebaseio.com/' 
    })
    print("Firebase Connected Successfully!")
except Exception as e:
    print("Firebase Error: " + str(e))

app = Flask(__name__, template_folder=resource_path('templates'), static_folder=resource_path('static'))
app.config['SECRET_KEY'] = 'secret_key_bta3_sencord'
# ضيف async_mode='threading' عشان تنهي المشكلة دي للأبد
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*")
# المتغير اللي هيمسك شاشة الويندوز عشان نتحكم فيها بالزراير
window_instance = None 

DATA_DIR = os.getenv('APPDATA') or os.path.expanduser('~')
PROFILE_FILE = os.path.join(DATA_DIR, 'Sencord', 'sencord_user.json')
DEFAULT_PROFILE = {
    'uid': None,
    'username': 'Dev-Mero',
    'avatar': '',
    'status': 'online',
    'mic': 'default'
}
LOG_FILE = os.path.join(DATA_DIR, 'Sencord', 'sencord_debug.log')

def log_debug(message):
    try:
        folder = os.path.dirname(LOG_FILE)
        if folder and not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
    except Exception:
        pass


def load_profile():
    try:
        if not os.path.exists(PROFILE_FILE):
            save_profile(DEFAULT_PROFILE)
            return DEFAULT_PROFILE.copy()
        with open(PROFILE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            profile = DEFAULT_PROFILE.copy()
            profile.update(data or {})
            return profile
    except Exception:
        return DEFAULT_PROFILE.copy()


def save_profile(profile):
    try:
        profile_data = DEFAULT_PROFILE.copy()
        profile_data.update(profile or {})
        folder = os.path.dirname(PROFILE_FILE)
        if folder and not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        with open(PROFILE_FILE, 'w', encoding='utf-8') as f:
            json.dump(profile_data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

@app.route('/profile', methods=['GET'])
def get_profile():
    return jsonify(load_profile())

@app.route('/profile', methods=['POST'])
def post_profile():
    data = request.get_json(silent=True) or {}
    profile = load_profile()
    allowed = ['uid', 'username', 'avatar', 'status', 'mic']
    for key in allowed:
        if key in data:
            profile[key] = data[key]
    if not profile.get('uid'):
        profile['uid'] = data.get('uid') or f"uid_{int(time.time() * 1000)}_{os.getpid()}"
    save_profile(profile)
    return jsonify(profile)

# --- دوال التعامل مع فايربيس ---
def get_db_data():
    try:
        ref = db.reference('/')
        data = ref.get()
        if data is None:
            default_data = {
                'chat_history': { 'general-chat': [] },
                'channels_db': { 'text': ['general-chat', 'coding-help'], 'voice': ['General Voice'] }
            }
            ref.set(default_data)
            return default_data
        return data
    except:
        return {'chat_history': {}, 'channels_db': {'text': [], 'voice': []}}

def update_channel_in_firebase(c_type, c_name):
    try:
        ref = db.reference(f'/channels_db/{c_type}')
        current_channels = ref.get() or []
        if c_name not in current_channels:
            current_channels.append(c_name)
            ref.set(current_channels)
    except: pass

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def on_connect():
    db_data = get_db_data()
    emit('load_channels', db_data.get('channels_db', {'text': [], 'voice': []}))

@socketio.on('join')
def on_join(data):
    room = data['room']
    join_room(room)
    db_data = get_db_data()
    history = db_data.get('chat_history', {}).get(room, [])
    emit('load_history', history)

@socketio.on('create_channel')
def handle_create_channel(data):
    update_channel_in_firebase(data['type'], data['name'])
    emit('channel_created', data, broadcast=True)

@socketio.on('message')
def handleMessage(data):
    msg = data['msg']
    room = data['room']
    action = msg.get('action')
    
    ref = db.reference(f'/chat_history/{room}')
    current_history = ref.get() or []

    if action == 'new': 
        current_history.append(msg)
    elif action == 'edit':
        for m in current_history:
            if m.get('id') == msg['id']:
                m['text'] = msg['text']
                m['edited'] = True
                break
    elif action == 'delete':
        current_history = [m for m in current_history if m.get('id') != msg['id']]
    elif action in ['react', 'unreact']:
        for m in current_history:
            if m.get('id') == msg['id']:
                if 'reactions' not in m: m['reactions'] = {}
                if action == 'react': m['reactions'][msg['emoji']] = m['reactions'].get(msg['emoji'], 0) + 1
                elif action == 'unreact':
                    if msg['emoji'] in m['reactions'] and m['reactions'][msg['emoji']] > 0:
                        m['reactions'][msg['emoji']] -= 1
                break
                
    ref.set(current_history)
    emit('message', msg, to=room, broadcast=True)

@socketio.on('leave')
def on_leave(data):
    leave_room(data['room'])

# WebRTC Signaling للفويس والشير سكرين
# استبدل دوال الـ WebRTC القديمة بدول:
@socketio.on('offer')
def handle_offer(data):
    # data دلوقتي شايلة الـ offer والـ senderId والـ targetId
    emit('offer', {'offer': data['offer'], 'senderId': data['senderId']}, to=data['targetId'])

@socketio.on('answer')
def handle_answer(data):
    emit('answer', {'answer': data['answer'], 'senderId': data['senderId']}, to=data['targetId'])

@socketio.on('ice_candidate')
def handle_ice_candidate(data):
    emit('ice_candidate', {'candidate': data['candidate'], 'senderId': data['senderId']}, to=data['targetId'])

# ضيف الدالة دي كمان عشان السيرفر يعرف يربط الناس ببعض جوه الروم
@socketio.on('join_voice_room')
def handle_join_voice_room(data):
    join_room(data['room'])
@socketio.on('ping_server')
def handle_ping(): emit('pong_client')

# --- تشغيل زراير الويندوز (التصغير، التكبير، الإغلاق) ---
@socketio.on('app_control')
def handle_app_control(data):
    global window_instance
    action = data.get('action')
    if window_instance:
        if action == 'minimize':
            window_instance.minimize()
        elif action == 'maximize':
            window_instance.toggle_fullscreen()
        elif action == 'close':
            window_instance.destroy()
            os._exit(0)

def wait_for_server(host='127.0.0.1', port=5000, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def start_server():
    try:
        socketio.run(app, host='127.0.0.1', port=5000, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)
    except Exception as e:
        log_debug('Server failed: ' + str(e))
        log_debug(traceback.format_exc())
        raise

if __name__ == '__main__':
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    if not wait_for_server():
        log_debug('Error: Flask server did not start in time.')
        print('Error: Flask server did not start in time.')
        sys.exit(1)
    
    # هنا ربطنا الشاشة بالمتغير عشان الزراير تعرف تتحكم فيها
    window_instance = webview.create_window(
        'Sencord', 
        'http://127.0.0.1:5000', 
        width=1280, 
        height=720, 
        background_color='#313338',
        frameless=True, 
        easy_drag=False 
    )
    webview.start(private_mode=False)