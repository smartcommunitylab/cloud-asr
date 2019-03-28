import os
import json
from flask import Flask, Response, request, jsonify, stream_with_context
from flask.ext.cors import CORS
from flask.ext.socketio import SocketIO, emit, session
from lib import create_frontend_worker, MissingHeaderError, NoWorkerAvailableError, WorkerInternalError
from cloudasr.schema import db
from cloudasr.models import UsersModel, RecordingsModel, WorkerTypesModel

app = Flask(__name__)
if 'CONNECTION_STRING' in os.environ:
    app.config.update(
        SECRET_KEY = '12345',
        DEBUG = 'DEBUG' in os.environ,
        SQLALCHEMY_DATABASE_URI = os.environ['CONNECTION_STRING']
    )
elif 'CONNECTION_STRING_FILE' in os.environ:
    scrfilepath = os.environ['CONNECTION_STRING_FILE']
    fl = open(scrfilepath,"r")
    app.config.update(
        SECRET_KEY = '12345',
        DEBUG = 'DEBUG' in os.environ,
        SQLALCHEMY_DATABASE_URI = fl.readline().replace('\n', '')
    )
    fl.close()
else:
    print("No connection string set in environ")
cors = CORS(app)
socketio = SocketIO(app)
db.init_app(app)
worker_types_model = WorkerTypesModel(db.session)
recordings_model = RecordingsModel(db.session, worker_types_model)
keyList = set([])

@app.route("/recognize", methods=['POST'])
def recognize_batch():
    data = {
        "model": request.args.get("lang", "en-GB"),
        "lm": request.args.get("lm", "default"),
        "wav": request.data
    }

    def generate(response):
        for result in response:
            yield json.dumps(result)

    try:
        #os.environ['kafka_broker_url']="172.17.0.1:9092"
        worker = create_frontend_worker(os.environ['kafka_broker_url'])
        response = worker.recognize_batch(data, request.headers,request)

        return Response(stream_with_context(generate(response)))
    except MissingHeaderError:
        return jsonify({"status": "error", "message": "Missing header Content-Type"}), 400
    except Exception as exception:
        return jsonify({"status": "error", "message": "No worker available"}), 503


@app.route("/transcribe", methods=['POST'])
def transcribe():
    try:
        data = request.get_json(force=True)
        user_id = data.get("user_id", None)
        recording_id = data["recording_id"]
        transcription = data["transcription"]

        result = recordings_model.add_transcription(user_id, recording_id, transcription)
        if result == True:
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "error", "message": "Recording with id %s not found" % str(recording_id)}), 404
    except KeyError as e:
        return jsonify({"status": "error", "message": "Missing item %s" % e.args[0]}), 400


@socketio.on('begin')
def begin_online_recognition(message):
    try:
        print("**************INSIDE BEGIN ONLINE RECOGNITION RUN.PY for request****************", request)
        print("Worker model that will be used is ", message["model"])
        #os.environ['kafka_broker_url']="172.17.0.1:9092"
        #kafka_broker_url=os.environ['kafka_broker_url']
        worker = create_frontend_worker(os.environ['kafka_broker_url'])
        worker.connect_to_worker(message["model"])
        session["connected"] = True
        session["worker"] = worker
    except Exception as exception:
        emit('server_error', {"status": "error", "message": "Internal Error"})
        print(exception)


@socketio.on('chunk')
def recognize_chunk(message):
    try:
        if not session.get("connected", False):
            emit('server_error', {"status": "error", "message": "No worker available"})
            return
        eventType = "chunk"
        chunk, frame_rate = session["worker"].recognize_chunk(message["chunk"], message["frame_rate"])
        bufferMap, silenceDetected = session["worker"].send_request_to_vad_system(keyList, request, chunk, "ONLINE",
                                                                                  eventType, frame_rate, has_next=True)
        if silenceDetected:
            eventType = "End"
            results = session["worker"].end_recognition(keyList, request, eventType, 16000)
            if results is not None:
                for result in results:
                    emit('result', result)
                    print("*****************Finishing recognition for request*******************", request)
    except Exception as exception:
        emit('server_error', {"status": "error", "message": "Internal error"})
        print(exception)
        del session["worker"]


@socketio.on('change_lm')
def change_lm(message):
    try:
        if not session.get("connected", False):
            emit('server_error', {"status": "error", "message": "No worker available"})
            return

        session["worker"].change_lm(request, keyList, str(message["new_lm"]))
    except Exception as exception:
        emit('server_error', {"status": "error", "message": "Internal error"})
        del session["worker"]
        print(exception)


@socketio.on('end')
def end_recognition(message):
    session["connected"] = False
    del session["worker"]


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=80)
