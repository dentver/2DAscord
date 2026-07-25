import struct


# ── Voice Protocol ───────────────────────────────────


class VoiceProtocol:
    MAGIC = 0xAD
    TYPE_VOICE = 1
    HEADER_SIZE = 15

    @staticmethod
    def encode(payload: bytes, seq: int, timestamp: int, ptype: int = TYPE_VOICE) -> bytes:
        header = struct.pack('!HBIQ', VoiceProtocol.MAGIC, ptype, seq, timestamp)
        return header + payload

    @staticmethod
    def decode(data: bytes) -> dict:
        magic, ptype, seq, timestamp = struct.unpack(
            '!HBIQ', data[:VoiceProtocol.HEADER_SIZE]
        )
        return {
            'magic': magic,
            'type': ptype,
            'seq': seq,
            'timestamp': timestamp,
            'payload': data[VoiceProtocol.HEADER_SIZE:]
        }
