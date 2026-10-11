from __future__ import annotations



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
    def is_admin(cls, msg_type)->str:


        return msg_type in cls.ADMIN

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