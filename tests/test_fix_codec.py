
import pytest

from fix_codec import (
SOH,
FixFramer,
FixParser,
)

parser = FixParser()
LOGON = (
    b"8=FIX.4.4\x019=67\x0135=A\x0149=CLIENT\x0156=SERVER\x0134=1\x01"
    b"52=20260910-14:30:00.000\x0198=0\x01108=30\x0110=133\x01"
)
HEARTBEAT = b"8=FIX.4.4\x019=5\x0135=0\x0110=163\x01"

class TestParse:
    def test_parses_heartbeat(self):
        assert parser.parse(HEARTBEAT) == {8: "FIX.4.4", 9: "5", 35: "0", 10: "163"}

    def test_parses_logon_fields(self):
        assert parser.parse(LOGON) == {
            8: "FIX.4.4",
            9: "67",
            35: "A",
            49: "CLIENT",
            56: "SERVER",
            34: "1",
            52: "20260910-14:30:00.000",
            98: "0",
            108: "30",
            10: "133",
        }

    def test_tags_are_ints(self):
        parsed_dictionary = parser.parse(LOGON)

        for key, value in parsed_dictionary.items():
            assert isinstance(key, int)

    def test_value_may_contain_equals(self):
        # Split on the FIRST '=' only.
        raw = b"8=FIX.4.4\x019=12\x0135=D\x0158=a=b\x0110=144\x01"
        assert parser.parse(raw)[58] == "a=b"

    # def test_rejects_field_without_equals(self):
    #     with pytest.raises(FixParserError):
    #         parser.parse(b"8=FIX.4.4\x01garbage\x0110=000\x01")
    #
    # def test_rejects_non_integer_tag(self):
    #     with pytest.raises(FixParserError):
    #         parser.parse(b"8=FIX.4.4\x01abc=1\x0110=000\x01")

class TestChecksum:

   def test_known_value(self):
        assert parser.compute_checksum(b"8=FIX.4.4\x019=5\x0135=0\x01") =='163'

   def test_is_three_chars(self):

       checksum = parser.compute_checksum(b"8=FIX.4.4\x01")
       assert len(checksum) == 3

   def test_wraps_256(self):

      assert parser.compute_checksum(b"\x01" * 256) == '000'

   def test_zero_padded(self):
       assert parser.compute_checksum(b"\x01\x01") == '002'

class TestBodyLength:
    def test_counts_bytes(self):
        body = b"35=0\x01"
        assert parser.body_length(body) == 5


class TestSerialize:
    def test_round_trips_heartbeat(self):
        assert parser.serialize({35: "0"}, begin_string="FIX.4.4") == HEARTBEAT

    def test_field_order(self):
        out = parser.serialize({56: "SERVER", 49: "CLIENT", 35: "A", 34: "1"})
        # 8= first, 9= second, 35= third, 10= last.
        assert out.startswith(b"8=FIX.4.4\x019=")
        body_start = out.index(SOH, out.index(b"9=")) + 1
        assert out[body_start:body_start + 5] == b"35=A\x01"
        assert out.rstrip(SOH).split(SOH)[-1].startswith(b"10=")

    def test_parse_of_serialize_is_identity(self):
        fields = {35: "D", 49: "ME", 56: "YOU", 34: "7", 55: "CL", 54: "1"}
        out = parser.parse(parser.serialize(fields))
        for tag, value in fields.items():
            assert out[tag] == value

    def test_body_length_is_correct(self):
        out = parser.serialize({35: "A", 49: "CLIENT", 56: "SERVER", 34: "1"})
        m = parser.parse(out)
        declared = int(m[9])
        start = out.index(SOH, out.index(b"9=")) + 1
        end = out.index(b"10=")
        assert declared == end - start

    def test_checksum_is_correct(self):
        out = parser.serialize({35: "A", 49: "CLIENT", 34: "1"})
        end = out.index(b"10=")
        assert parser.parse(out)[10] == parser.compute_checksum(out[:end])



