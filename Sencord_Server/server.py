import eventlet
eventlet.monkey_patch()

import os
import time
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
import firebase_admin
from firebase_admin import credentials, db

# --- 1. إعدادات فايربيس ---
try:
    if not firebase_admin._apps:
        cred = credentials.Certificate('firebase_key.json')
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://sencord-99002-default-rtdb.firebaseio.com/' 
        })
        print("Firebase Connected Successfully!")
except Exception as e:
    print("Firebase Error: " + str(e))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key_bta3_sencord'
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/profile', methods=['GET', 'POST'])
def handle_profile():
    return jsonify({
        'uid': f"uid_{int(time.time() * 1000)}",
        'username': 'Dev-Mero',
        'avatar': '',
        'status': 'online',
        'mic': 'default'
    })

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

@socketio.on('offer')
def handle_offer(data):
    emit('offer', {'offer': data['offer'], 'senderId': data['senderId']}, to=data['targetId'])

@socketio.on('answer')
def handle_answer(data):
    emit('answer', {'answer': data['answer'], 'senderId': data['senderId']}, to=data['targetId'])

@socketio.on('ice_candidate')
def handle_ice_candidate(data):
    emit('ice_candidate', {'candidate': data['candidate'], 'senderId': data['senderId']}, to=data['targetId'])

@socketio.on('join_voice_room')
def handle_join_voice_room(data):
    join_room(data['room'])

@socketio.on('ping_server')
def handle_ping(): 
    emit('pong_client')

application = app 

if __name__ == '__main__':
    socketio.run(app, debug=False)
