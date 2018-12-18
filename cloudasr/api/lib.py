import base64
import re
import uuid
from cloudasr.messages import MasterResponseMessage
from vad import create_vad
from AudioUtils import *
from cloudasr.messages.helpers import *
from kafka import KafkaProducer
from kafka import KafkaConsumer
import pickle
import collections
from kafka.errors import KafkaError
from kafka.structs import OffsetAndMetadata, TopicPartition



def create_frontend_worker(kafka_broker_url):
    vad = create_vad()
    audio = AudioUtils()
    decoder = Decoder()
    silenceDetected = False
    resampledpcm_buffer_map = collections.OrderedDict()
    id_generator = lambda: uuid.uuid4().int
    model = None

    return FrontendWorker(vad, audio, decoder, silenceDetected, resampledpcm_buffer_map,
                          id_generator, model, kafka_broker_url)


class FrontendWorker:
    def __init__(self, vad, audio, decoder, silenceDetected, resampledpcm_buffer_map,
                 id_generator, model, kafka_broker_url):
        self.vad = vad
        self.audio = audio
        self.decoder = decoder
        self.silenceDetected = silenceDetected
        self.id_generator = id_generator
        self.id = None
        self.resampledpcm_buffer_map = resampledpcm_buffer_map
        self.model = model
        self.kafka_broker_url = kafka_broker_url

    def recognize_batch(self, data, headers, requestKey):
        self.validate_headers(headers)
        self.connect_to_worker(data["model"])

        frame_rate = self.extract_frame_rate_from_headers(headers)
        response = self.recognize_batch_on_worker(data, frame_rate, requestKey)

        return response

    def connect_to_worker(self, model):
        self.id = self.id_generator()
        self.model = model

    def recognize_chunk(self, data, frame_rate):
        # print("Inside API LIB recognize chunk")
        chunk = self.decoder.decode(data)
        return chunk, frame_rate

    def format_response(self, results, formatter):
        if any([result.status == ResultsMessage.ERROR for result in results]):
            raise WorkerInternalError

        return [formatter(result) for result in results]

    def change_lm(self, request, keyList, lm):
        pass
        # strkey = str(request)
        # key = strkey[-12:]
        # keyList.add(key)
        # self.send_request_to_worker_change_LM(key, b"", "ONLINE", frame_rate=44100, has_next=True, new_lm=lm)

    def end_recognition(self, keyList, requestKey, eventType, frame_rate=16000):
        strkey = str(requestKey)
        key = strkey[-12:]
        print("Silence Detected or Speech Finished , End Recognition for key", key)
        vad_total_buffer_map = self.prepare_vad_buffer(keyList, "", requestKey, eventType, frame_rate=16000)
        vad_total_buffer = vad_total_buffer_map[key]
        self.invoke_worker_with_vad_data(vad_total_buffer, requestKey, frame_rate=16000)
        response = self.read_response_from_worker(keyList, requestKey)
        self.silenceDetected = False
        self.resampledpcm_buffer_map[key] = b""
        self.vad.reset()
        if response is not None:
            return self.format_response(response.results, self.format_online_recognition_response)

    def validate_headers(self, headers):
        if "Content-Type" not in headers:
            raise MissingHeaderError()

        if not re.match("audio/x-wav; rate=\d+;", headers["Content-Type"]):
            raise MissingHeaderError()

    def extract_frame_rate_from_headers(self, headers):
        return int(re.search("audio/x-wav; rate=(\d+);", headers["Content-Type"]).group(1))

    def recognize_batch_on_worker(self, data, frame_rate, requestKey):
        self.invoke_worker_with_batch_data(data["wav"], "BATCH", requestKey, frame_rate, has_next=False,
                                           new_lm=data["lm"])
        response = self.read_response_from_worker("", requestKey)
        # self.worker_socket.disconnect(self.worker_address)

        return self.format_response(response.results, self.format_batch_recognition_response)

    def send_request_to_worker_change_LM(self, requestLMKey, data, type, frame_rate=None, has_next=False, new_lm=""):
        requestLM = createRecognitionRequestMessage(type, data, has_next, self.id, frame_rate, new_lm)
        try:
            producer = KafkaProducer(bootstrap_servers=self.kafka_broker_url)
            producer.send(str(self.model), key=requestLMKey, value=requestLM.SerializeToString()).get(timeout=2)
        except KafkaError:
            producer.close()
            print("Kafka error when sending to Worker")

    def send_request_to_vad_system(self, keyList, requestKey, data, type, eventType, frame_rate=None, has_next=True,
                                   new_lm=""):
        request = createRecognitionRequestMessage(type, data, has_next, self.id, frame_rate, new_lm)
        vad_buffer_map, self.silenceDetected = self.prepare_vad_buffer(keyList, request, requestKey, eventType,
                                                                       frame_rate)
        if vad_buffer_map is not None:
            # print("Created vad_buffer_map")
            return vad_buffer_map, self.silenceDetected

    def read_response_from_worker(self, keyList, requestKey):

        print(" Model of the returned worker is ", self.model)
        strkey = str(requestKey)
        key = strkey[-12:]
        try:
            results = KafkaConsumer(bootstrap_servers=self.kafka_broker_url,
                                     enable_auto_commit=False,auto_offset_reset="latest",group_id='',consumer_timeout_ms=2500)
            tp = TopicPartition('result'+str(self.model), 0)
            results.assign([tp])
            #results.subscribe(['result' + str(self.model)])
        except KafkaError:
            print("Kafka error while reading response from worker", key)
        if results is not None:
            for result in results:
                print("Result Keys inside Kafka to be read are " ,result.key)
                print("Total results returned from kafka is ", resultCount, key, result.key)
                if key == result.key:
                    response = parseResultsMessage(result.value)
                    offsets = {tp: OffsetAndMetadata(result.offset+1, None)}
                    results.commit(offsets=offsets)
                    return response

    def format_batch_recognition_response(self, response):
        return {
            "result": [
                {
                    "alternative": [{"confidence": a.confidence, "transcript": a.transcript} for a in
                                    response.alternatives],
                    "final": response.final,
                },
            ],
            "result_index": 0,
            "chunk_id": str(uniqId2Int(response.id)),
            "request_id": str(self.id)
        }

    def format_online_recognition_response(self, response):
        return {
            'status': 0,
            'result': {
                'hypotheses': [{"confidence": a.confidence, "transcript": a.transcript} for a in response.alternatives],
            },
            'final': response.final,
            'chunk_id': str(uniqId2Int(response.id)),
            'request_id': str(self.id)
        }

    def prepare_vad_buffer(self, keyList, request, requestKey, eventType, frame_rate):
        strkey = str(requestKey)
        Key = strkey[-12:]
        d = keyList
        d.add(Key)
        resampledpcm_buffer_map = self.resampledpcm_buffer_map
        if eventType == "End":
            return resampledpcm_buffer_map
        pcm_buffer = b""
        if resampledpcm_buffer_map.get(Key) != None:
            resampledpcm_buffer = resampledpcm_buffer_map[Key]
        else:
            resampledpcm_buffer = b""

        for original_pcm, resampled_pcm in self.audio.chunks(request.body, request.frame_rate):
            is_speech, change, original_pcm, resampled_pcm = self.vad.decide(original_pcm, resampled_pcm)
            pcm_buffer = pcm_buffer + original_pcm

            if is_speech:
                resampledpcm_buffer = resampledpcm_buffer + resampled_pcm
                resampledpcm_buffer_map[Key] = resampledpcm_buffer

            if change == "non-speech":
                print("Non Speech Detected for key", Key)
                self.silenceDetected = True
                return resampledpcm_buffer, self.silenceDetected
        return resampledpcm_buffer_map, self.silenceDetected

    def invoke_worker_with_vad_data(self, request, requestKey, frame_rate=None):
        strkey = str(requestKey)
        key = strkey[-12:]
        print("Sending VAD Data with Key to worker ", key)
        reSampledrequest = createRecognitionRequestMessage("ONLINE", request, False, self.id, frame_rate, "")
        producer = KafkaProducer(bootstrap_servers=self.kafka_broker_url)
        try:
            producer.send(str(self.model), key=key, value=reSampledrequest.SerializeToString()).get(timeout=2)
        except KafkaError:
            producer.close()
            print("Kafka Error when sending to worker for the request", key)

    def invoke_worker_with_batch_data(self, request, type, requestKey, frame_rate=None, has_next=False, new_lm=""):
        strkey = str(requestKey)
        key = strkey[-12:]
        batchrequest = createRecognitionRequestMessage("BATCH", request, has_next, self.id, frame_rate, new_lm)
        producer = KafkaProducer(bootstrap_servers=self.kafka_broker_url)
        try:
            producer.send(str(self.model), key=key, value=batchrequest.SerializeToString()).get(timeout=2)
        except KafkaError:
            producer.close()
            print("Kafka Error when sending to worker for the request")


class Decoder:

    def decode(self, data):
        return base64.b64decode(data)


class NoWorkerAvailableError(Exception):
    pass


class MissingHeaderError(Exception):
    pass


class WorkerInternalError(Exception):
    pass
