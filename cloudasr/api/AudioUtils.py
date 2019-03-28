import audioop
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

    def chunks(self, pcm, sample_rate):
        if len(pcm) == 0:
            yield b"", b""
        else:
            original_pcm = self.original_pcm_buffer + pcm
            resampled_pcm = self.resampled_pcm_buffer + self.resample_to_default_sample_rate(pcm, sample_rate)
            original_buffer_size = int(sample_rate * (self.frame_duration_ms / 1000.) * self.sample_width)
            resampled_buffer_size = int(self.sample_rate * (self.frame_duration_ms / 1000.) * self.sample_width)

            num_chunks = int(float(len(resampled_pcm)) / resampled_buffer_size)
            for i in xrange(num_chunks):
                yield (
                    original_pcm[i * original_buffer_size:(i + 1) * original_buffer_size],
                    resampled_pcm[i * resampled_buffer_size:(i + 1) * resampled_buffer_size]
                )

            self.original_pcm_buffer = original_pcm[num_chunks * original_buffer_size:]
            self.resampled_pcm_buffer = resampled_pcm[num_chunks * resampled_buffer_size:]

    def resample_to_default_sample_rate(self, pcm, sample_rate):
        if sample_rate != self.sample_rate:
            pcm, state = audioop.ratecv(pcm, 2, 1, sample_rate, self.sample_rate, None)

        return pcm

    def reset(self):
        self.state = None
        self.original_pcm_buffer = b""
        self.resampled_pcm_buffer = b""
