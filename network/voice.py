import queue
import array
import struct

import numpy as np
import sounddevice as sd


# ── Jitter Buffer ──────────────────────────────────────


class JitterBuffer:
    def __init__(self, max_frames: int = 8, prefill: int = 2):
        self._buffer: dict[int, bytes] = {}
        self._expected_seq: int = 0
        self._max: int = max_frames
        self._prefill: int = prefill
        self._prefilled: bool = False
        self._window: int = 1000

    def add(self, seq: int, payload: bytes):
        if seq < self._expected_seq - self._window:
            return
        if seq > self._expected_seq + self._window * 2:
            return
        self._buffer[seq] = payload
        threshold = self._expected_seq - self._window
        for key in list(self._buffer.keys()):
            if key < threshold:
                del self._buffer[key]

    def pop(self) -> bytes | None:
        if not self._prefilled:
            if len(self._buffer) < self._prefill:
                return None
            keys = sorted(self._buffer.keys())
            self._expected_seq = keys[0]
            self._prefilled = True

        pkt = self._buffer.pop(self._expected_seq, None)
        if pkt is not None:
            self._expected_seq += 1
            return pkt

        next_keys = [k for k in self._buffer.keys() if k >= self._expected_seq]
        if next_keys:
            next_key = min(next_keys)
            self._expected_seq = next_key
            pkt = self._buffer.pop(next_key)
            self._expected_seq = next_key + 1
            return pkt
        return None

    def reset(self):
        self._buffer.clear()
        self._expected_seq = 0
        self._prefilled = False


# ── Voice Engine ─────────────────────────────────────


class VoiceEngine:
    SAMPLERATE = 16000
    FRAME_SIZE = 320
    CHANNELS = 1
    VAD_THRESHOLD = 500

    def __init__(self):
        self.input_queue: queue.Queue = queue.Queue(maxsize=5)
        self.output_queue: queue.Queue = queue.Queue(maxsize=3)
        self.input_stream: sd.InputStream | None = None
        self.output_stream: sd.OutputStream | None = None
        self._muted = False
        self._running = False
        self.last_frame: array.array | None = None

    @property
    def muted(self) -> bool:
        return self._muted

    @muted.setter
    def muted(self, value: bool):
        self._muted = value

    def _input_callback(self, indata, frames, time_info, status):
        try:
            if not self._muted:
                try:
                    self.input_queue.put_nowait(indata.copy().tobytes())
                except queue.Full:
                    pass
        except Exception:
            pass

    def _output_callback(self, outdata, frames, time_info, status):
        try:
            try:
                arr = self.output_queue.get_nowait()
            except queue.Empty:
                arr = None

            if arr is not None and len(arr) == frames:
                self.last_frame = arr
                outdata[:, 0] = arr
            elif self.last_frame is not None:
                decayed = array.array('h', (
                    int(s * 0.6) for s in self.last_frame
                ))
                self.last_frame = decayed
                outdata[:, 0] = decayed
            else:
                outdata.fill(0)
        except Exception:
            outdata.fill(0)

    def start(self):
        if self._running:
            return
        self.input_stream = sd.InputStream(
            samplerate=self.SAMPLERATE, channels=self.CHANNELS,
            blocksize=self.FRAME_SIZE, dtype='int16',
            callback=self._input_callback
        )
        self.output_stream = sd.OutputStream(
            samplerate=self.SAMPLERATE, channels=self.CHANNELS,
            blocksize=self.FRAME_SIZE, dtype='int16',
            callback=self._output_callback
        )
        self.input_stream.start()
        self.output_stream.start()
        self._running = True

    def stop(self):
        self._running = False
        self.last_frame = None
        if self.input_stream:
            self.input_stream.stop()
            self.input_stream.close()
            self.input_stream = None
        if self.output_stream:
            self.output_stream.stop()
            self.output_stream.close()
            self.output_stream = None
        for q in (self.input_queue, self.output_queue):
            while True:
                try:
                    q.get_nowait()
                except queue.Empty:
                    break

    def warmup(self):
        pass

    def get_encoded_frame(self) -> bytes:
        return self.input_queue.get()

    def get_encoded_frame_nowait(self) -> bytes | None:
        try:
            return self.input_queue.get_nowait()
        except queue.Empty:
            return None

    def put_pcm_frame(self, pcm: array.array):
        try:
            self.output_queue.put_nowait(pcm)
        except queue.Full:
            pass

    def put_pcm_bytes(self, data: bytes):
        arr = array.array('h')
        arr.frombytes(data)
        try:
            self.output_queue.put_nowait(arr)
        except queue.Full:
            pass

    @staticmethod
    def is_silence(frame: bytes, threshold: int = VAD_THRESHOLD) -> bool:
        if not frame:
            return True
        count = len(frame) // 2
        if count == 0:
            return True
        samples = struct.unpack(f'{count}h', frame)
        energy = sum(abs(s) for s in samples) / count
        return energy < threshold
