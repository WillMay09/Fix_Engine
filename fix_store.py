from __future__ import annotations


import json
from abc import ABC, abstractmethod
from pathlib import Path


class MessageStore(ABC):

   @abstractmethod
   def get(self, start_seq, end_seq, messages):
      pass
   @abstractmethod
   def save(self, seq_num: int, raw: bytes) -> None:
       """Persist an outbound message by its MsgSeqNum."""

   @abstractmethod
   def get_range(self, begin: int, end: int) -> list[tuple[int, bytes]]:
       """Messages with begin <= seq <= end, ascending by seq.

               end == 0 means "through the highest sequence stored" (FIX's infinity).
               Gaps are possible — return what exists, let the caller gap-fill.
               """

   @abstractmethod
   def next_send_seq(self) -> int:
    """Return the next outbound MsgSeqNum and increment. Starts at 1."""

   @abstractmethod
   def peek_sender_seq(self):
    """What next_sender_seq() would return, without consuming it."""

   @abstractmethod
   def expected_target_seq(self) -> int:
    """The inbound MsgSeqNum we expect next. Starts at 1."""

   @abstractmethod
   def set_expected_target_seq(self, seq_num: int) ->None:
       """Advance the inbound counter after accepting a message, or after a
               SequenceReset."""

   @abstractmethod
   def reset(self) -> None:
       """Wipe messages and set both counters to 1. This is Logon 141=Y."""







class InMemoryStore(MessageStore):

     def __init__(self):
         self.messages = dict[int, bytes] = {}
         self._sender_seq = 1
         self._target_seq = 1

     def save(self, seq_num: int, raw: bytes) -> None:
         self.messages[seq_num] = raw

     def get_range(self, begin: int, end: int) -> list[tuple[int, bytes]]:
         range = []
         for seq_num in range(begin, end):
             if seq_num not in self.messages:
                 continue
             range.append((seq_num, self.messages[seq_num]))




