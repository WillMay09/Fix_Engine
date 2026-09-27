
from __future__ import annotations

from email.quoprimime import body_length

SOH = b"\x01"

BEGIN_STRING = 8
BODY_LENGTH = 9
MSG_TYPE = 35
SENDER_COMP_ID = 49
TARGET_COMP_ID = 56
MSG_SEQ_NUM = 34
SENDING_TIME = 52
CHECKSUM = 10

# class SessionRejectReason:
#     """FIX 4.4 tag 373 values. Only the ones the parser can produce."""
#     INVALID_TAG_NUMBER = 0
#     TAG_SPECIFIED_WITHOUT_VALUE = 4
#     INCORRECT_DATA_FORMAT = 6
#     TAG_APPEARS_MORE_THAN_ONCE = 13
#
#
# class FixParserError(Exception):
#
#     def __init__(self, message, *, tag=None, reason=SessionRejectReason.INCORRECT_DATA_FORMAT, raw=None):
#         super().__init__(message)
#         self.tag = tag
#         self.reason = reason
#         self.raw = raw



class FixParser:

    """Raised when bytes cannot be parsed as a FIX message."""

    def parse(self, raw: bytes) -> dict[int, str]:
        """Turn one complete FIX message into {tag: value}."""
        fix_message_values = {}
        for pair in raw.split(SOH):
            if not pair:
                continue
            tag, value = pair.split(b'=',maxsplit=1)

            fix_message_values[int(tag)] = value.decode("ascii")

        return fix_message_values

#check sum
    def compute_checksum(self, message_without_trailer: bytes) -> str:
            value = sum(message_without_trailer) % 256
            return f"{value:03d}"


    def body_length(self,body: bytes) -> int:
        return len(body)


    def serialize(self, fields: dict[int, str], begin_string: str = "FIX.4.4") -> bytes:
        serialized = bytearray()

        if MSG_TYPE in fields:
            serialized+= f"{MSG_TYPE}={fields[MSG_TYPE]}".encode("ascii") + SOH

        for tag, value in fields.items():

            if tag in (BEGIN_STRING, BODY_LENGTH,CHECKSUM, MSG_TYPE):
                continue

            serialized += f"{tag}={value}".encode('ascii') + SOH

        length_of_message = str(self.body_length(serialized)).encode('ascii')
        #print(f"Length of message method: {length_of_message}")

        #print(f"body={bytes(serialized)!r} len={len(serialized)}")

        head = b"8=" + begin_string.encode("ascii") + SOH + b"9=" + length_of_message + SOH

        checksum = self.compute_checksum(head + serialized).encode('ascii')
        full_message = head + serialized + b"10=" + checksum + SOH
        return full_message





class FixFramer:
    def __init__(self):
        self.buffer = bytearray()

    def feed(self, raw: bytes) -> list[bytes]:
        self.buffer.extend(raw)
        messages = []

        while True:
            #1. Find the beginning of a Fix message
            start_index = self.buffer.find(b'8=')
            #edge case were end of the buffer is begining of new message
            if start_index == -1:
                if self.buffer.endswith(b'8'):
                   self.buffer = bytearray(b'8')
                else:
                    self.buffer.clear()
                break
            #discard everything before 8=
            elif start_index != 0:
                del self.buffer[:start_index]

            #first SOH denotes end of 8= value
            begin_string_end =self.buffer.find(SOH)
            #first SOH hasb't come in yet
            if begin_string_end == -1:
                break

            #second SOH denotes end of 9= value(body length)
            body_length_end = self.buffer.find(SOH, begin_string_end +1)

            if body_length_end == -1:
                break

            body_length_start = begin_string_end + 1
            if self.buffer[body_length_start:body_length_start+2] != b"9=":
                del self.buffer[:2]
                continue

            #parse the length of the body, extract the number
            body_length_bytes = self.buffer[body_length_start+2:body_length_end]

            try:
                body_length = int(body_length_bytes.decode('ascii'))
            except ValueError:
                del self.buffer[:2]
                continue
            #Caculate the expected end of the message
            body_start = body_length_end + 1
            expected_end = body_start + body_length + 7

            if len(self.buffer) < expected_end:
                break
            full_message = bytes(self.buffer[:expected_end])

            #remove the full message
            del self.buffer[:expected_end]

            messages.append(full_message)

        return messages






if __name__=="__main__":
    import doctest

    proto_fix_message = (
    b"8=FIX.4.4\x019=67\x0135=A\x0149=CLIENT\x0156=SERVER\x0134=1\x01"
    b"52=20260910-14:30:00.000\x0198=0\x01108=30\x0110=133\x01"
)
    #136
    check_sum_test = b"8=FIX.4.4\x019=5\x0135=0\x01"

    message_body = b"35=0\x01"
    parser = FixParser()
    parsedMessage = parser.parse(proto_fix_message)
    serializedMessage = parser.serialize({35: "A", 49: "CLIENT", 56: "SERVER", 34: "1"})

    serializedMessage_parsed = parser.parse(serializedMessage)
    length_of_message = serializedMessage_parsed[9]

