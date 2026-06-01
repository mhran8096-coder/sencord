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

# مهم جداً لـ Render
application = app 

if __name__ == '__main__':
    socketio.run(app, debug=False)