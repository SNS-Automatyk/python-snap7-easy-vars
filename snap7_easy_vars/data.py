import asyncio
from collections import OrderedDict
from datetime import datetime
from typing import Dict, List, Optional
from .fields import PLCField
import logging

logger = logging.getLogger(__name__)

class PLCDataMeta(type):
    """
    Metaclass collecting PLC field descriptors in definition order.
    """

    def __new__(mcls, name, bases, namespace):
        fields = OrderedDict()

        for base in bases:
            base_fields = getattr(base, "_fields", None)
            if base_fields:
                fields.update(base_fields)

        for attr_name, attr_value in list(namespace.items()):
            if isinstance(attr_value, PLCField):
                attr_value.name = attr_name
                fields[attr_name] = attr_value

        namespace["_fields"] = fields
        return super().__new__(mcls, name, bases, namespace)


class PLCData(metaclass=PLCDataMeta):
    """
    Base class handling automatic serialization/deserialization for PLC fields.
    """

    def __init__(self, **initial_values):
        self._values: Dict[str, object] = {
            name: field.coerce(field.default) for name, field in self._fields.items()
        }
        self._subscribers: List[asyncio.Queue] = []

        for key, value in initial_values.items():
            if key in self._fields:
                setattr(self, key, value)

    IS_CONNECTED_TIMEOUT = 2  # seconds

    _last_connected: Optional[datetime] = None

    @property
    def is_connected(self) -> bool:
        if self._last_connected is None:
            return False
        return (
            datetime.now() - self._last_connected
        ).total_seconds() <= self.IS_CONNECTED_TIMEOUT

    def last_connected_setter(self, value):
        self.old_is_connected = self.is_connected
        self._last_connected = value
        if self.old_is_connected != self.is_connected:
            self.notify_subscribers()

        # check connection status after timeout
        self._last_connected_timeout = asyncio.get_event_loop().call_later(
            self.IS_CONNECTED_TIMEOUT, self._on_connection_timeout
        )

    last_connected = property(lambda self: self._last_connected, last_connected_setter)

    def _on_connection_timeout(self):
        if self.old_is_connected != self.is_connected:
            self.notify_subscribers()
            self.old_is_connected = self.is_connected

    @classmethod
    def buffer_size(cls) -> int:
        if not cls._fields:
            return 0
        return max(field.byte_offset + field.size for field in cls._fields.values())

    def set_data(self, **kwargs):
        processed = False
        for key, value in kwargs.items():
            field = self._fields.get(key)
            if field is None or not field.settable:
                continue
            if getattr(self, key) == field.coerce(value):
                continue
            setattr(self, key, value)
            processed = True

        if processed:
            self.notify_subscribers()

    def dict(self):
        data = {name: getattr(self, name) for name in self._fields}
        data["is_connected"] = self.is_connected
        return data

    def from_bytes(self, raw: bytes):
        for name, field in self._fields.items():
            current = self._values.get(name, field.default)
            self._values[name] = field.read(raw, current)
        self.notify_subscribers()

    def to_bytes(self) -> bytes:
        buffer = bytearray(self.buffer_size())
        for name, field in self._fields.items():
            field.write(buffer, getattr(self, name))
        return bytes(buffer)

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        if q in self._subscribers:
            self._subscribers.remove(q)

    def notify_subscribers(self):
        for q in self._subscribers:
            try:
                q.put_nowait(self)
            except asyncio.QueueFull:
                pass

