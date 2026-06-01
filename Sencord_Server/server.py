import os
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit, join_room
import firebase_admin
from firebase_admin import credentials, db

# 1. إعدادات فايربيس
try:
    if not firebase_admin._apps:
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

# 2. مسار فتح الصفحة الأساسية
@app.route('/')
def index():
    return render_template('index.html')

# 3. مسار جلب الداتا (الشانلات والشات القديم)
@app.route('/get_db_data')
def get_db_data():
    try:
        ref = db.reference('/')
        data = ref.get()
        if data is None:
            data = {}
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)})

# 4. دوال الصوت (WebRTC)
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

# 5. دوال الرسايل الجديدة
@socketio.on('send_message')
def handle_message(data):
    emit('receive_message', data, broadcast=True)

# 6. تعريف التطبيق لـ Render
application = app 

if __name__ == '__main__':
    socketio.run(app, debug=False)
