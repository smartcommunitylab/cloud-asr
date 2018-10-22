from alex_asr import Decoder
import wave
import struct
import os

# Load speech recognition model from "asr_model_dir" directory.
decoder = Decoder("alex-asr/test/asr_model_digits/")

# Load audio frames from input wav file.
data = wave.open("alex-asr/test/eleven.wav")
frames = data.readframes(data.genframes())

# Feed the audio data to the decoder.
decoder.accept_audio(frames)
decoder.decode(data.genframes())
decoder.input_finished()

# Get and print the best hypothesis.
prob, word_ids = decoder.get_best_path()
print " ".join(map(decoder.get_word, word_ids))
