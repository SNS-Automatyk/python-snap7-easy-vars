import struct

class PLCField:
    """
    Base descriptor representing a single PLC variable.
    """

    def __init__(
        self, byte_offset: int, *, size: int, default=0, settable: bool = False
    ):
        self.byte_offset = byte_offset
        self.size = size
        self.default = default
        self.settable = settable
        self.name: str | None = None

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return instance._values.get(self.name, self.default)

    def __set__(self, instance, value):
        instance._values[self.name] = self.coerce(value)

    def coerce(self, value):
        return value

    def read(self, data: bytes, current):
        return current

    def write(self, buffer: bytearray, value):
        raise NotImplementedError


class PLCBoolField(PLCField):
    """
    Field representing a boolean stored as a single bit.
    """

    def __init__(
        self,
        byte_offset: int,
        bit_offset: int,
        *,
        default: int = 0,
        settable: bool = False,
    ):
        super().__init__(
            byte_offset, size=1, default=int(bool(default)), settable=settable
        )
        self.bit_offset = bit_offset

    def coerce(self, value):
        return 1 if bool(value) else 0

    def read(self, data: bytes, current):
        if len(data) <= self.byte_offset:
            return current
        byte_value = data[self.byte_offset]
        return (byte_value >> self.bit_offset) & 0x01

    def write(self, buffer: bytearray, value):
        value = self.coerce(value)
        mask = 1 << self.bit_offset
        if value:
            buffer[self.byte_offset] |= mask
        else:
            buffer[self.byte_offset] &= (~mask) & 0xFF


class PLCWordField(PLCField):
    """
    Field representing a 16-bit integer value (WORD).
    """

    def __init__(
        self,
        byte_offset: int,
        *,
        default: int = 0,
        signed: bool = False,
        settable: bool = False,
    ):
        super().__init__(byte_offset, size=2, default=int(default), settable=settable)
        self.signed = signed

    def _clamp(self, value: int) -> int:
        value = int(value)
        if self.signed:
            return max(min(value, 32767), -32768)
        return max(min(value, 0xFFFF), 0)

    def coerce(self, value):
        return self._clamp(value)

    def read(self, data: bytes, current):
        slice_ = data[self.byte_offset : self.byte_offset + self.size]
        if len(slice_) < self.size:
            return current
        return int.from_bytes(slice_, byteorder="big", signed=self.signed)

    def write(self, buffer: bytearray, value):
        value = self.coerce(value)
        buffer[self.byte_offset : self.byte_offset + self.size] = value.to_bytes(
            self.size, byteorder="big", signed=self.signed
        )


class PLCRealField(PLCField):
    """
    Field representing a 32-bit IEEE-754 floating point value (REAL).
    """

    def __init__(
        self, byte_offset: int, *, default: float = 0.0, settable: bool = False
    ):
        super().__init__(byte_offset, size=4, default=float(default), settable=settable)

    def coerce(self, value):
        return float(value)

    def read(self, data: bytes, current):
        slice_ = data[self.byte_offset : self.byte_offset + self.size]
        if len(slice_) < self.size:
            return current
        try:
            return struct.unpack(">f", slice_)[0]
        except struct.error:
            return current

    def write(self, buffer: bytearray, value):
        buffer[self.byte_offset : self.byte_offset + self.size] = struct.pack(
            ">f", float(value)
        )
