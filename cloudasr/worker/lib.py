import audioop
import wave
import json
import zmq
import time
import uuid
from StringIO import StringIO
from asr import create_asr
from cloudasr.messages import RecognitionRequestMessage
from cloudasr.messages.helpers import *
from kafka import KafkaConsumer
from kafka import KafkaProducer
from kafka.errors import KafkaError
import collections



def create_worker(model, recordings_saver_address, kafka_broker_url):
    asr = create_asr()
    audio = AudioUtils()
    orderedHypothesis = collections.OrderedDict()
    saver = RemoteSaver(create_recordings_saver_socket(recordings_saver_address), model)
    id_generator = lambda: uuid.uuid4().int
    run_forever = lambda: True

    return Worker(asr, audio, orderedHypothesis, saver, model, id_generator, run_forever, kafka_broker_url)


def create_recordings_saver_socket(address):
    context = zmq.Context()
    socket = context.socket(zmq.PUSH)
    socket.connect(address)

    return socket


class Worker:

    def __init__(self, asr, audio, orderedHypothesis, saver, model, id_generator, should_continue, kafka_broker_url):
        self.asr = asr
        self.audio = audio
        self.saver = saver
        self.model = model
        self.should_continue = should_continue
        self.id_generator = id_generator
        self.current_request_id = None
        self.current_chunk_id = None
        self.orderedHypothesis = orderedHypothesis
        self.kafka_broker_url = kafka_broker_url

    def run(self):

        while self.should_continue():
            print("Model is ", str(self.model))
            resampledConsumed = KafkaConsumer(str(self.model), group_id='worker' + str(self.model),
                                              bootstrap_servers=self.kafka_broker_url,
                                              auto_commit_interval_ms=5000,
                                              enable_auto_commit=True)
            if resampledConsumed is not None:
                self.handle_request(resampledConsumed)
            else:
                if not self.is_online_recognition_running():
                    print("Worker is Ready")
                else:
                    self.end_recognition()

    def handle_request(self, message):
        for mssg in message:
            request = parseRecognitionRequestMessage(mssg.value)
            if request.type == RecognitionRequestMessage.BATCH:
                self.handle_batch_request(request, mssg.key)
            else:
                if not self.is_online_recognition_running():
                    self.begin_online_recognition(request)

                self.handle_online_request(request, mssg.key)

    def handle_batch_request(self, request, msgKey):
        pcm = self.get_pcm_from_message(request.body)
        resampled_pcm = self.audio.resample_to_default_sample_rate(pcm, request.frame_rate)

        self.asr.change_lm(request.new_lm)
        self.asr.recognize_chunk(resampled_pcm)
        current_chunk_id = self.id_generator()
        final_hypothesis = self.asr.get_final_hypothesis()
        hypotheses = []
        hypotheses.append((current_chunk_id, True, final_hypothesis))
        self.send_hypotheses(hypotheses, msgKey)
        self.end_recognition()
        self.saver.new_recognition(request.id)
        self.saver.add_pcm(pcm)
        self.saver.final_hypothesis(current_chunk_id, final_hypothesis)

    def handle_online_request(self, request, msgKey):
        audio_buffer = request.body
        if request.new_lm:
            self.asr.change_lm(request.new_lm)
        if request.has_next == False or request.new_lm != "":
            is_final = True
            hypotheses = []
            if len(audio_buffer) > 0:
                self.saver.add_pcm(audio_buffer)
                self.asr.recognize_chunk(audio_buffer)
                hypothesis = self.asr.get_final_hypothesis()
                hypotheses.append((self.current_chunk_id, True, hypothesis))
                self.saver.final_hypothesis(self.current_chunk_id, hypothesis)
            elif len(hypotheses) == 0:
                hypotheses.append((self.current_chunk_id, True, [(1.0, "")]))
            self.asr.reset()
            self.send_hypotheses(hypotheses, msgKey)
            return

    def send_hypotheses(self, hypotheses, messageKey):
        producer = KafkaProducer(bootstrap_servers=self.kafka_broker_url)
        try:
            response = createResultsMessage(hypotheses)
            producer.send('result' + str(self.model), key=messageKey, value=response.SerializeToString()).get(timeout=3)
            self.end_recognition()
        except KafkaError:
            print("Kafka error while sending the result back to API for request", messageKey)

    def is_online_recognition_running(self):
        return self.current_request_id is not None

    def is_bad_chunk(self, request):
        return self.current_request_id != request.id

    def begin_online_recognition(self, request):
        self.current_request_id = request.id
        self.current_chunk_id = self.id_generator()
        self.saver.new_recognition(self.current_request_id, request.frame_rate)

    def end_recognition(self):
        self.asr.change_lm("default")
        self.asr.reset()
        self.audio.reset()
        self.current_request_id = None

    def get_pcm_from_message(self, message):
        return self.audio.load_wav_from_string_as_pcm(message)


class AudioUtils:
    def __init__(self, sample_rate=16000, sample_width=2, frame_duration_ms=30):
        self.state = None
        self.original_pcm_buffer = b""
        self.resampled_pcm_buffer = b""
        self.sample_width = sample_width
        self.sample_rate = int(sample_rate)
        self.frame_duration_ms = frame_duration_ms

    def load_wav_from_string_as_pcm(self, string):
        return self.load_wav_from_file_as_pcm(StringIO(string))

    def load_wav_from_file_as_pcm(self, path):
        return self.convert_wav_to_pcm(self.load_wav(path))

    def load_wav(self, path):
        wav = wave.open(path, 'r')
        if wav.getnchannels() != 1:
            raise Exception('Input wave is not in mono')
        if wav.getsampwidth() != self.sample_width:
            raise Exception('Input wave is not in %d Bytes' % self.sample_width)

        return wav

    def convert_wav_to_pcm(self, wav):
        try:
            chunk = 1024
            pcm = b''
            pcmPart = wav.readframes(chunk)

            while pcmPart:
                pcm += str(pcmPart)
                pcmPart = wav.readframes(chunk)

            return self.resample_to_default_sample_rate(pcm, wav.getframerate())
        except EOFError:
            raise Exception('Input PCM is corrupted: End of file.')

    def resample_to_default_sample_rate(self, pcm, sample_rate):
        if sample_rate != self.sample_rate:
            pcm, state = audioop.ratecv(pcm, 2, 1, sample_rate, self.sample_rate, None)

        return pcm

    def reset(self):
        self.state = None
        self.original_pcm_buffer = b""
        self.resampled_pcm_buffer = b""


class RemoteSaver:

    def __init__(self, socket, model):
        self.socket = socket
        self.model = model
        self.id = None
        self.wav = b""

    def new_recognition(self, id, frame_rate=16000):
        print("Inside new recognition saver")
        self.id = uniqId2Int(id)
        self.part = 0
        self.frame_rate = frame_rate

    def add_pcm(self, pcm):
        self.wav += pcm

    def final_hypothesis(self, chunk_id, final_hypothesis):
        if len(self.wav) == 0:
            return
        print("saving final hypothesis")
        self.socket.send(createSaverMessage(self.id, self.part, chunk_id, self.model, self.wav, self.frame_rate,
                                            final_hypothesis).SerializeToString())
        self.wav = b""
        self.part += 1
