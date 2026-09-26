
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

class FixParserError(Exception):

    """Raised when bytes cannot be parsed as a FIX message."""

    def parse(self, raw: bytes) -> dict[int, str]:
        """Turn one complete FIX message into {tag: value}."""
        fix_message_values = {}
        decoded_message = raw.decode('ascii')

        for pair in decoded_message.split(SOH):

            if not pair:
                continue
            tag, value = pair.split('=',maxsplit=1)

            fix_message_values[int(tag)] = value

        return fix_message_values


#check sum
    def compute_checksum(self, message_without_trailer: bytes) -> bytes:
            value = sum(message_without_trailer) % 256
            return f"{value:03d}".encode('ascii')


    def body_length(self,message_without_trailer: bytes) -> int:
        return len(message_without_trailer)


    def serialize(self, fields: dict[int, str], begin_string: str = "FIX.4.4") -> bytes:
        serialized = bytearray()

        for tag, value in fields.items():

            if tag in (BEGIN_STRING | BODY_LENGTH | CHECKSUM):
                continue

            serialized += f"{tag}={value}".encode('ascii')
            serialized += SOH

        head = b"8=" + begin_string + SOH + b"9=" + str(body_length) + SOH
        checksum = self.compute_checksum(head + serialized)
        full_message = head + serialized + b"10=" + checksum + SOH
        return full_message




class FixFramer:
    """Append data, then extract every complete message available.

           Algorithm:
             1. self.buffer.extend(data)
             2. Loop:
                a. Find b"8=" — if absent, return what you have so far.
                   If it is not at index 0, discard everything before it.
                b. Find the SOH that ends the 9= field. If not present yet,
                   the message is incomplete — stop and wait for more bytes.
                c. Parse the BodyLength value.
                d. Compute where the message ends:

                       end = (index just past the SOH ending 9=)
                             + body_length
                             + len(b"10=xxx\\x01")   # always exactly 7

                e. If len(self.buffer) < end, stop and wait.
                f. Slice out buffer[:end], remove it from the buffer, append to
                   the results list, and loop again.

           Return the list of complete raw messages.
           """



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


