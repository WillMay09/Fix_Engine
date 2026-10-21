from __future__ import annotations


# ── MsgType: tag 35 values ─────────────────────────────────────────────
# PEP 8 names classes in CapWords. MSG_TYPE reads as a module constant,
# which this is not — it is a namespace. Renaming to MsgType is optional
# but it is what the rest of the project expects.

class MSG_TYPE:
    HEARTBEAT = "0"
    TEST_REQUEST = "1"
    RESEND_REQUEST = "2"
    REJECT = "3"
    SEQUENCE_RESET = "4"
    LOGOUT = "5"
    LOGON = "A"

    NEW_ORDER_SINGLE = "D"
    EXECUTION_REPORT = "8"
    ORDER_CANCEL_REQUEST = "F"
    ORDER_CANCEL_REJECT = "9"

    ADMIN = {HEARTBEAT, TEST_REQUEST, RESEND_REQUEST, REJECT,
             SEQUENCE_RESET, LOGOUT, LOGON}

    @classmethod
    def is_admin(cls, msg_type: str) -> bool:  # was -> str; returns a bool
        """Admin messages are NOT resent on a ResendRequest — they are
        collapsed into a SequenceReset-GapFill instead."""
        return msg_type in cls.ADMIN


# ── SessionRejectReason: tag 373 values ────────────────────────────────
# Module level, not inside MSG_TYPE. test_reason_constants_usable imports
# this by name.

class SessionRejectReason:
    INVALID_TAG_NUMBER = 0
    REQUIRED_TAG_MISSING = 1
    TAG_NOT_DEFINED_FOR_MSG_TYPE = 2
    UNDEFINED_TAG = 3
    TAG_WITHOUT_VALUE = 4
    VALUE_IS_INCORRECT = 5
    INCORRECT_DATA_FORMAT = 6
    COMP_ID_PROBLEM = 9
    SENDING_TIME_ACCURACY = 10
    INVALID_MSG_TYPE = 11
    TAG_APPEARS_MORE_THAN_ONCE = 13
    TAG_OUT_OF_ORDER = 14
    OTHER = 99


# ── Tag constants ──────────────────────────────────────────────────────
# These are module level too. Inside MSG_TYPE they would be MSG_TYPE.TEXT,
# which reads as a message type rather than a tag number.

BEGIN_SEQ_NO = 7
END_SEQ_NO = 16
NEW_SEQ_NO = 36
POSS_DUP_FLAG = 43
REF_SEQ_NUM = 45
TEXT = 58
ENCRYPT_METHOD = 98
HEART_BT_INT = 108
TEST_REQ_ID = 112
ORIG_SENDING_TIME = 122
GAP_FILL_FLAG = 123
RESET_SEQ_NUM_FLAG = 141
REF_TAG_ID = 371
REF_MSG_TYPE = 372
SESSION_REJECT_REASON = 373


# ── Builders ───────────────────────────────────────────────────────────
# ALL AT MODULE LEVEL, zero indentation. Indented under the class they
# became MSG_TYPE.logon and msgs.logon raised AttributeError.

def logon(heart_bt_int: int, reset_seq_num: bool = False) -> dict[int, str]:
    """35=A, 98=0 no encryption.
    """
    if heart_bt_int < 0:
        raise ValueError(f"heart_bt_int must be >= 0, got {heart_bt_int}")

    fields = {35: MSG_TYPE.LOGON, 98: "0", 108: str(heart_bt_int)}
    if reset_seq_num:
        fields[141] = "Y"
    return fields


def heartbeat(test_req_id: str | None = None) -> dict[int, str]:
    """35=0. 112 present only when replying to a TestRequest.
    """
    fields = {35: MSG_TYPE.HEARTBEAT}
    if test_req_id is not None:
        fields[112] = test_req_id
    return fields


def test_request(test_req_id: str) -> dict[int, str]:
    """35=1, verifies communication and tests sequence numbers.
    """
    if not test_req_id:
        raise ValueError("test_req_id is required, must be a non-empty string")

    return {35: MSG_TYPE.TEST_REQUEST, 112: str(test_req_id)}


# This builder's name matches pytest's test-discovery pattern, so pytest
# would try to collect the builder itself as a test and fail on the missing
# argument. __test__ = False is pytest's documented opt-out. Must sit at
# module level, after the def.
test_request.__test__ = False


def resend_request(begin_seq_no: int, end_seq_no: int = 0) -> dict[int, str]:
    """Sent by the receiving application to initiate retransmission.
    """
    if begin_seq_no < 1:
        raise ValueError(f"begin_seq_no must be >= 1, got {begin_seq_no}")
    if end_seq_no < 0:
        raise ValueError(f"end_seq_no must be >= 0, got {end_seq_no}")
    # `end_seq_no != 0`, NOT `>= 0`. With >= 0 the guard fires for 0, which
    # rejects every legal open-ended request.
    if end_seq_no != 0 and end_seq_no < begin_seq_no:
        raise ValueError(
            f"end_seq_no {end_seq_no} is before begin_seq_no {begin_seq_no}, "
            "for an open-ended request use 0")

    return {35: MSG_TYPE.RESEND_REQUEST,
            7: str(begin_seq_no),
            16: str(end_seq_no)}


def reject(ref_seq_num: int,
           reason: int | None = None,
           ref_tag_id: int | None = None,
           ref_msg_type: str | None = None,
           text: str | None = None) -> dict[int, str]:
    """A Reject <3> is issued when a message is received but cannot be
    processed due to a session-level rule violation. Informational — the
    session continues.
    """
    # Annotated int, not str — the comparison below needs a number.
    if ref_seq_num < 1:
        raise ValueError(f"ref_seq_num must be >= 1, got {ref_seq_num}")

    fields = {35: MSG_TYPE.REJECT, 45: str(ref_seq_num)}
    if reason is not None:
        fields[373] = str(reason)
    if ref_tag_id is not None:
        fields[371] = str(ref_tag_id)
    if ref_msg_type is not None:
        fields[372] = str(ref_msg_type)
    if text is not None:
        fields[58] = str(text)
    return fields


def sequence_reset(new_seq_no: int, gap_fill: bool = True) -> dict[int, str]:
    """One MsgType, two different messages, split by tag 123.

    """
    if new_seq_no < 1:
        raise ValueError(f"new_seq_no must be >= 1, got {new_seq_no}")

    return {35: MSG_TYPE.SEQUENCE_RESET,
            36: str(new_seq_no),
            123: "Y" if gap_fill else "N"}


def logout(text: str | None = None) -> dict[int, str]:
    """35=5. Graceful shutdown: send, await the echo, close the socket.
    """
    fields = {35: MSG_TYPE.LOGOUT}
    if text is not None:
        fields[58] = text
    return fields


# Module level, so it actually runs under `python fix_messages.py`.
if __name__ == "__main__":
    import doctest

    doctest.testmod(verbose=True)
