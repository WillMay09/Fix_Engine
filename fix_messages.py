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



    #Builders
    def logon(heart_bt_int: int, reset_seq_no: bool = False) -> dict[int, str]:
        """35=A, 98=0, no encryption"""
        #108 tag states timeout interval for generating heartbeats
        fields = {35: MSG_TYPE.LOGON,98:"0", 108: str(heart_bt_int)}
        #if request was sent again, add 141 tag
        if reset_seq_no:
            fields[141] = "Y"
        return fields

    def heartbeat(test_req_id: str | None=None) -> dict[int, str]:
        #heartbeat 35=0, test_req_id = occurs when force heartbeat request
        fields ={35: MSG_TYPE.HEARTBEAT}
        if test_req_id is not None:
            fields[112] = test_req_id
        return fields


    def test_request(test_req_id: str) -> dict[int, str]:
        """1 = test_request, verifies communication / tests sequence numbers"""
        if not test_req_id:
            raise ValueError("test_req_id is required, must be a non-empty string")

        fields = {35: MSG_TYPE.TEST_REQUEST,112: str(test_req_id) }

        return fields



    def resend_request(begin_seq_no: int, end_seq_no: int) -> dict[int, str]:
        """sent by recieving application, initiate retransmission of messages
        7=BeginSeqNo, 16=EndSeqNo. **0 means infinity.** 35: '2', 7: '4', 16: '0'}"""
        if begin_seq_no < 1:
            raise ValueError(f"begin_seq_no must be >= 1, got {begin_seq_no}")
        if end_seq_no < 0:
            raise ValueError(f"end_seq_no must be >= 0, got {end_seq_no}")
        if end_seq_no >= 0 and end_seq_no < begin_seq_no:
            raise ValueError(f"end_seq_no {end_seq_no} is before begin_seq_no {begin_seq_no}, for open-ended request, use 0")

        fields = {35: MSG_TYPE.RESEND_REQUEST, 7: str(begin_seq_no), 16: str(end_seq_no)}
        return fields


    def reject(ref_seq_num: str,reason: str | None=None,ref_tag_id: int | None=None, ref_msg_type:str|None=None, text: str | None=None ) -> dict[int, str]:
        """Reject <3> message should be issued when a message is received
        but cannot be properly processed due to a session-level rule violation"""

        if ref_seq_num < 1:
            raise ValueError(f"ref_seq_num must be >=1, got {ref_seq_num}")
        fields = {35: MSG_TYPE.REJECT,45:str(ref_seq_num)}
        if reason is not None:
            fields[373] = str(reason)
        if ref_tag_id is not None:
            fields[371] = str(ref_tag_id)
        if ref_msg_type is not None:
            fields[372] = str(ref_msg_type)
        if text is not None:
            fields[58] = str(text)

        return fields

    def sequence_reset(new_seq_no: int, gap_fill_flag: bool) -> dict[int, str]:

        if new_seq_no < 1:
            raise ValueError(f"new_seq_no must be greater than 1, got {new_seq_no}")

        fields ={35:MSG_TYPE.SEQUENCE_RESET, 36:str(new_seq_no), 123: 'Y' if gap_fill_flag else 'N'}
        return fields

    def logout(text:str | None = None) -> dict[int, str]:

        fields = {35:MSG_TYPE.LOGOUT}
        if text is not None:
            fields[58] = text
            return fields


    if __name__ == "__main__":
        import doctest
        doctest.testmod(verbose=True)















