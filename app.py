# from flask import Flask, render_template

# app = Flask(__name__)

# # Route to serve the HTML page
# @app.route('/')
# def index():
#     return render_template('index.html')

# if __name__ == '__main__':
#     app.run(debug=True)


# app.py

# from flask import Flask, render_template, request
# import subprocess

# app = Flask(__name__)

# @app.route('/', methods=['GET', 'POST'])
# def index():
#     if request.method == 'POST':
#         # Extract data from form
#         img_size = request.form['img']
#         batch_size = 16  # Assuming this is constant for now
#         epochs = request.form['epochs']
#         data_file = 'coco128.yaml'  # Assuming this is constant for now
#         weights = ''  # Assuming you have no initial weights
#         cfg = request.form['cfg']
        
#         # Construct the command with the form inputs
#         command = [
#             'python', 'yolov5/train.py',
#             '--img', img_size,
#             '--batch', str(batch_size),
#             '--epochs', epochs,
#             '--data', data_file,
#             '--weights', weights,
#             '--cfg', cfg
#         ]
        
#         # Execute the command
#         process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
#         out, err = process.communicate()
        
#         # For simplicity, we are just printing the output and error to the console
#         print(out)
#         if err:
#             print(f"Error: {err}")
        
#         # Here you can return a template with the process output or confirmation
#         return render_template('index.html', message='Training started!')
    
#     # If it's a GET request, just render the form
#     return render_template('index.html')

# if __name__ == '__main__':
#     app.run(debug=True)

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import subprocess
import shlex
import threading
import os


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

output = ""  # This variable holds the command output

def run_command(command, user_sid):

    global output
    """ Run a command and emit its output line by line to the client through SocketIO. """
    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    # Read the command's output line by line and emit to the client
    for line in iter(process.stdout.readline, ''):
            output += line
            socketio.emit('cmd_output', {'data': line}, to=user_sid)
    process.stdout.close()
    process.wait()
    socketio.emit('cmd_output', {'data': '*** Command finished ***'}, to=user_sid)

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')

@app.route('/get-directories')
def get_directories():
    parent_directory = './dataset'  # Assuming parent directory; modify as needed
    directories = [d for d in os.listdir(parent_directory) 
                   if os.path.isdir(os.path.join(parent_directory, d))]
    return {'directories': directories}


UPLOAD_FOLDER = './dataset'  # Set your server upload folder path here

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part'
    file = request.files['file']
    if file.filename == '':
        return 'No selected file'

    # Create directories as necessary
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    file.save(file_path)
    return f'Uploaded {file.filename}'



@socketio.on('request_output_update')
def handle_request_output_update():
    emit('cmd_output', {'data': output})

    
@socketio.on('run_command')
def handle_run_command(json):
    """ SocketIO event handler to run a command sent from the client. """
    img_size = json['img']
    epochs = json['epochs']
    cfg = json['cfg']
    data_set = json['directory']
    command = f"python train.py --img {img_size} --batch 16 --epochs {epochs} --data dataset/{data_set}/data.yaml --weights '' --cfg {cfg}"
    
    # Run the command in a separate thread to avoid blocking the main thread
    thread = threading.Thread(target=run_command, args=(command, request.sid))
    thread.start()

if __name__ == '__main__':
    socketio.run(app, debug=True)
