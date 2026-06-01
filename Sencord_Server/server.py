import os
from flask import Flask, render_template
from flask_socketio import SocketIO, emit, join_room
import firebase_admin
from firebase_admin import credentials

# إعدادات فايربيس
try:
    cred = credentials.Certificate('firebase_key.json')
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://sencord-99002-default-rtdb.firebaseio.com/' 
    })
    print("Firebase Connected!")
except Exception as e:
    print("Firebase Error: ", e)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sencord_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('join_voice_room')
def handle_join(data):
    join_room(data['room'])

@socketio.on('offer')
def handle_offer(data):
    emit('offer', {'offer': data['offer'], 'senderId': data['senderId']}, to=data['targetId'])

@socketio.on('answer')
def handle_answer(data):
    emit('answer', {'answer': data['answer'], 'senderId': data['senderId']}, to=data['targetId'])

@socketio.on('ice_candidate')
def handle_ice(data):
    emit('ice_candidate', {'candidate': data['candidate'], 'senderId': data['senderId']}, to=data['targetId'])
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
# مهم جداً لـ Render
application = app 

if __name__ == '__main__':
    socketio.run(app, debug=False)
