"""
tests/test_messages.py — comprehensive builder tests. Run: pytest -v

Five kinds of assertion, applied to each builder:

  1. EXACT OUTPUT       the whole dict, for the common cases
  2. TAG PRESENCE       required tags present, optional tags absent when unset
  3. TYPE INVARIANTS    int keys, str values, no ints leaking through
  4. PURITY             fresh dict per call, no shared state
  5. VALIDATION         bad input raises ValueError
"""

import pytest

import fix_messages as msgs
from fix_messages import MSG_TYPE

ALL_BUILDERS = [
    (msgs.logon, (30,)),
    (msgs.heartbeat, ()),
    (msgs.test_request, ("TR-1",)),
    (msgs.resend_request, (4,)),
    (msgs.reject, (5,)),
    (msgs.sequence_reset, (10,)),
    (msgs.logout, ()),
]

HEADER_TAGS = {8, 9, 34, 49, 56, 52, 10}


# ── contract tests applied to every builder ────────────────────────────

class TestBuilderContract:
    @pytest.mark.parametrize("fn,args", ALL_BUILDERS)
    def test_returns_dict(self, fn, args):
        assert isinstance(fn(*args), dict)

    @pytest.mark.parametrize("fn,args", ALL_BUILDERS)
    def test_keys_are_ints(self, fn, args):
        assert all(isinstance(k, int) for k in fn(*args))

    @pytest.mark.parametrize("fn,args", ALL_BUILDERS)
    def test_values_are_strings(self, fn, args):
        """The dict[int, str] contract. An int here would survive
        serialization and fail somewhere far away."""
        assert all(isinstance(v, str) for v in fn(*args).values())

    @pytest.mark.parametrize("fn,args", ALL_BUILDERS)
    def test_includes_msg_type(self, fn, args):
        assert 35 in fn(*args)

    @pytest.mark.parametrize("fn,args", ALL_BUILDERS)
    def test_excludes_header_and_trailer_tags(self, fn, args):
        """Builders must not touch anything the session or codec owns."""
        assert not (set(fn(*args)) & HEADER_TAGS)

    @pytest.mark.parametrize("fn,args", ALL_BUILDERS)
    def test_fresh_dict_each_call(self, fn, args):
        """Equal but not identical. Catches a module-level dict or a mutable
        default argument."""
        a, b = fn(*args), fn(*args)
        assert a == b
        assert a is not b

    @pytest.mark.parametrize("fn,args", ALL_BUILDERS)
    def test_mutating_result_does_not_affect_next_call(self, fn, args):
        first = fn(*args)
        first[9999] = "contaminated"
        assert 9999 not in fn(*args)


# ── logon ──────────────────────────────────────────────────────────────

class TestLogon:
    def test_exact_output(self):
        assert msgs.logon(30) == {35: "A", 98: "0", 108: "30"}

    def test_exact_output_with_reset(self):
        assert msgs.logon(30, reset_seq_num=True) == {
            35: "A", 98: "0", 108: "30", 141: "Y"}

    def test_msg_type_is_A(self):
        assert msgs.logon(30)[35] == MSG_TYPE.LOGON == "A"

    def test_encrypt_method_always_zero(self):
        assert msgs.logon(30)[98] == "0"

    def test_heart_bt_int_stringified(self):
        assert msgs.logon(30)[108] == "30"
        assert isinstance(msgs.logon(30)[108], str)

    def test_reset_flag_omitted_by_default(self):
        """Absent, not 'N'. Both mean the same to a counterparty; every real
        engine omits it."""
        assert 141 not in msgs.logon(30)

    def test_reset_flag_omitted_when_false(self):
        assert 141 not in msgs.logon(30, reset_seq_num=False)

    def test_reset_flag_is_capital_Y(self):
        assert msgs.logon(30, reset_seq_num=True)[141] == "Y"

    def test_zero_heartbeat_is_legal(self):
        """108=0 disables heartbeats. Legal, and not the same as invalid."""
        assert msgs.logon(0)[108] == "0"

    def test_large_heartbeat(self):
        assert msgs.logon(3600)[108] == "3600"

    def test_negative_heartbeat_rejected(self):
        with pytest.raises(ValueError, match="heart_bt_int"):
            msgs.logon(-1)

    def test_reset_is_keyword_friendly(self):
        assert msgs.logon(30, True) == msgs.logon(30, reset_seq_num=True)


# ── heartbeat ──────────────────────────────────────────────────────────

class TestHeartbeat:
    def test_exact_output_unprompted(self):
        assert msgs.heartbeat() == {35: "0"}

    def test_exact_output_as_reply(self):
        assert msgs.heartbeat("TR-123") == {35: "0", 112: "TR-123"}

    def test_msg_type_is_zero_string(self):
        """'0' the character, not 0 the int."""
        assert msgs.heartbeat()[35] == "0"
        assert isinstance(msgs.heartbeat()[35], str)

    def test_test_req_id_omitted_when_none(self):
        assert 112 not in msgs.heartbeat()
        assert 112 not in msgs.heartbeat(None)

    def test_empty_string_test_req_id_is_still_echoed(self):
        """`is not None`, not truthiness. An empty TestReqID is legal and
        must come back."""
        assert msgs.heartbeat("")[112] == ""

    def test_echo_is_verbatim(self):
        for tid in ["TR-1", "a b c", "123", "!@#$", "x" * 100]:
            assert msgs.heartbeat(tid)[112] == tid


# ── test_request ───────────────────────────────────────────────────────

class TestTestRequest:
    def test_exact_output(self):
        assert msgs.test_request("TR-1") == {35: "1", 112: "TR-1"}

    def test_msg_type_is_one(self):
        assert msgs.test_request("x")[35] == MSG_TYPE.TEST_REQUEST == "1"

    def test_test_req_id_required_and_preserved(self):
        assert msgs.test_request("abc123")[112] == "abc123"

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="test_req_id"):
            msgs.test_request("")

    def test_none_rejected(self):
        with pytest.raises(ValueError):
            msgs.test_request(None)

    def test_round_trips_with_heartbeat(self):
        """The reply protocol: a Heartbeat must echo the request's 112."""
        req = msgs.test_request("TR-99")
        reply = msgs.heartbeat(req[112])
        assert reply[112] == req[112]


# ── resend_request ─────────────────────────────────────────────────────

class TestResendRequest:
    def test_exact_output_bounded(self):
        assert msgs.resend_request(4, 9) == {35: "2", 7: "4", 16: "9"}

    def test_exact_output_open_ended(self):
        assert msgs.resend_request(4) == {35: "2", 7: "4", 16: "0"}

    def test_msg_type_is_two(self):
        assert msgs.resend_request(1)[35] == MSG_TYPE.RESEND_REQUEST == "2"

    def test_ints_converted_to_strings(self):
        """Callers pass ints — sequence numbers are ints everywhere else in
        the system. The builder stringifies."""
        r = msgs.resend_request(4, 9)
        assert r[7] == "4" and r[16] == "9"
        assert all(isinstance(v, str) for v in r.values())

    def test_zero_end_means_infinity(self):
        assert msgs.resend_request(7, 0)[16] == "0"

    def test_zero_is_the_default(self):
        assert msgs.resend_request(7) == msgs.resend_request(7, 0)

    def test_single_message_range(self):
        assert msgs.resend_request(5, 5) == {35: "2", 7: "5", 16: "5"}

    def test_begin_below_one_rejected(self):
        """Sequence numbers start at 1. 0 is never a valid BeginSeqNo."""
        with pytest.raises(ValueError, match="begin_seq_no"):
            msgs.resend_request(0)
        with pytest.raises(ValueError, match="begin_seq_no"):
            msgs.resend_request(-3)

    def test_negative_end_rejected(self):
        with pytest.raises(ValueError, match="end_seq_no"):
            msgs.resend_request(4, -1)

    def test_inverted_range_rejected(self):
        with pytest.raises(ValueError, match="before"):
            msgs.resend_request(9, 4)

    def test_large_sequence_numbers(self):
        assert msgs.resend_request(999999, 1000000)[7] == "999999"


# ── MsgType namespace ──────────────────────────────────────────────────

class TestMsgType:
    def test_admin_set_membership(self):
        for t in ["0", "1", "2", "3", "4", "5", "A"]:
            assert MSG_TYPE.is_admin(t), t

    def test_application_messages_are_not_admin(self):
        for t in [MSG_TYPE.NEW_ORDER_SINGLE, MSG_TYPE.EXECUTION_REPORT,
                  MSG_TYPE.ORDER_CANCEL_REQUEST]:
            assert not MSG_TYPE.is_admin(t), t

    def test_unknown_msg_type_is_not_admin(self):
        assert not MSG_TYPE.is_admin("ZZ")

    def test_all_values_are_strings(self):
        for name in ["HEARTBEAT", "TEST_REQUEST", "RESEND_REQUEST", "REJECT",
                     "SEQUENCE_RESET", "LOGOUT", "LOGON"]:
            assert isinstance(getattr(MSG_TYPE, name), str)


# ── integration: builders feed the codec ───────────────────────────────

class TestCodecIntegration:
    """Builders are only useful if their output serializes. These are the
    tests that would have caught the resend_request int bug."""

    @pytest.mark.parametrize("fn,args", ALL_BUILDERS)
    def test_output_survives_stamp_and_serialize(self, fn, args):
        from fix_codec import FixParser
        parser = FixParser()

        body = fn(*args)
        stamped = {35: body[35], 49: "ME", 56: "YOU", 34: "1",
                   52: "20260927-14:30:00.000"}
        stamped.update({t: v for t, v in body.items() if t != 35})

        raw = parser.serialize(stamped)
        round_tripped = parser.parse(raw)

        # every field the builder produced survives the trip unchanged
        for tag, value in stamped.items():
            assert round_tripped[tag] == value, f"tag {tag} did not round-trip"

        # and the codec added its own three
        assert round_tripped[8] == "FIX.4.4"
        assert 9 in round_tripped and 10 in round_tripped

    @pytest.mark.parametrize("fn,args", ALL_BUILDERS)
    def test_every_value_is_ascii_encodable(self, fn, args):
        """FIX is ASCII on the wire. A non-ASCII value would break
        serialize's .encode('ascii')."""
        for value in fn(*args).values():
            value.encode("ascii")


# ── reject ─────────────────────────────────────────────────────────────

class TestReject:
    def test_minimal_output(self):
        assert msgs.reject(5) == {35: "3", 45: "5"}

    def test_full_output(self):
        assert msgs.reject(5, reason=13, ref_tag_id=35,
                           ref_msg_type="D", text="duplicate tag") == {
            35: "3", 45: "5", 373: "13", 371: "35", 372: "D",
            58: "duplicate tag"}

    def test_msg_type_is_three(self):
        assert msgs.reject(1)[35] == MSG_TYPE.REJECT == "3"

    def test_uses_tag_45_not_34(self):
        """45=RefSeqNum. Tag 34 is MsgSeqNum and belongs to the session —
        a builder that sets 34 corrupts the outbound sequence."""
        r = msgs.reject(5)
        assert r[45] == "5"
        assert 34 not in r

    def test_ref_seq_num_stringified(self):
        assert msgs.reject(5)[45] == "5"
        assert isinstance(msgs.reject(5)[45], str)

    def test_optional_fields_omitted(self):
        r = msgs.reject(5)
        for tag in (373, 371, 372, 58):
            assert tag not in r

    def test_reason_zero_is_included(self):
        """373=0 is INVALID_TAG_NUMBER, a real value. A truthiness check
        would silently drop it."""
        assert msgs.reject(5, reason=0)[373] == "0"

    def test_ref_tag_id_zero_is_included(self):
        assert msgs.reject(5, ref_tag_id=0)[371] == "0"

    def test_empty_text_is_included(self):
        assert msgs.reject(5, text="")[58] == ""

    def test_each_optional_independently(self):
        assert msgs.reject(5, reason=6) == {35: "3", 45: "5", 373: "6"}
        assert msgs.reject(5, ref_tag_id=9) == {35: "3", 45: "5", 371: "9"}
        assert msgs.reject(5, ref_msg_type="A") == {35: "3", 45: "5", 372: "A"}
        assert msgs.reject(5, text="x") == {35: "3", 45: "5", 58: "x"}

    def test_ref_seq_num_below_one_rejected(self):
        with pytest.raises(ValueError, match="ref_seq_num"):
            msgs.reject(0)

    def test_reason_constants_usable(self):
        from fix_messages import SessionRejectReason as R
        r = msgs.reject(5, reason=R.TAG_APPEARS_MORE_THAN_ONCE)
        assert r[373] == "13"

    def test_carries_fix_parse_error_context(self):
        """The intended wiring: FixParseError.tag and .reason feed a Reject."""
        tag, reason = 35, 13
        r = msgs.reject(ref_seq_num=7, reason=reason, ref_tag_id=tag)
        assert r[45] == "7" and r[373] == "13" and r[371] == "35"


# ── sequence_reset ─────────────────────────────────────────────────────

class TestSequenceReset:
    def test_gapfill_is_the_default(self):
        assert msgs.sequence_reset(10) == {35: "4", 36: "10", 123: "Y"}

    def test_explicit_reset(self):
        assert msgs.sequence_reset(10, gap_fill=False) == {
            35: "4", 36: "10", 123: "N"}

    def test_msg_type_is_four(self):
        assert msgs.sequence_reset(1)[35] == MSG_TYPE.SEQUENCE_RESET == "4"

    def test_gap_fill_flag_always_present(self):
        """Unlike most optional flags, 123 is always emitted — its absence
        means Reset, and silently defaulting to the dangerous mode is bad."""
        assert 123 in msgs.sequence_reset(5)
        assert 123 in msgs.sequence_reset(5, gap_fill=False)

    def test_new_seq_no_stringified(self):
        assert msgs.sequence_reset(10)[36] == "10"
        assert isinstance(msgs.sequence_reset(10)[36], str)

    def test_does_not_set_header_tags(self):
        """A GapFill needs 34 and 43=Y, but those are the session's job —
        Session._gapfill() adds them, because a GapFill must NOT consume a
        new sequence number via _stamp()."""
        r = msgs.sequence_reset(10)
        assert 34 not in r and 43 not in r

    def test_new_seq_no_below_one_rejected(self):
        with pytest.raises(ValueError, match="new_seq_no"):
            msgs.sequence_reset(0)
        with pytest.raises(ValueError, match="new_seq_no"):
            msgs.sequence_reset(-5)

    def test_large_new_seq_no(self):
        assert msgs.sequence_reset(999999)[36] == "999999"


# ── logout ─────────────────────────────────────────────────────────────

class TestLogout:
    def test_bare_output(self):
        assert msgs.logout() == {35: "5"}

    def test_with_text(self):
        assert msgs.logout("MsgSeqNum too low") == {
            35: "5", 58: "MsgSeqNum too low"}

    def test_msg_type_is_five(self):
        assert msgs.logout()[35] == MSG_TYPE.LOGOUT == "5"

    def test_uses_tag_58_not_encoded_text(self):
        """58=Text, not 355=EncodedText. EncodedText is for non-ASCII and
        is a length-prefixed data field whose value may contain SOH."""
        r = msgs.logout("bye")
        assert r[58] == "bye"
        assert 355 not in r and 354 not in r

    def test_text_omitted_when_none(self):
        assert 58 not in msgs.logout()
        assert 58 not in msgs.logout(None)

    def test_empty_text_is_included(self):
        assert msgs.logout("")[58] == ""

    def test_text_preserved_verbatim(self):
        for t in ["bye", "a b c", "seq 5 < 10", "x" * 200]:
            assert msgs.logout(t)[58] == t