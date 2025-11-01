import snap7
from datetime import datetime
import socket
import logging

logger = logging.getLogger(__name__)


class PLCConnection:
    """
    A class to talk with S7 PLC.
    """

    def __init__(
        self,
        ip_address,
        data_store,
        db_number=1,
        rack=0,
        slot=1,
        port=102,
        connect_timeout: float = 1.5,
        **kwargs,
    ):
        self.ip_address = ip_address
        self.db_number = db_number
        self.rack = rack
        self.slot = slot
        self.port = port
        self.connect_timeout = float(connect_timeout)
        self.client = snap7.client.Client()
        self.data_store = data_store

    def notify_subscribers(self):
        """Forward notifications to the underlying data store subscribers."""
        try:
            self.data_store.notify_subscribers()
        except Exception:
            # Keep defensive; notification should never block connection flow
            pass

    def connect(self):
        """
        Ensure client is connected. Returns True when connected, False otherwise.
        Uses a preflight TCP connect with timeout to avoid indefinite blocking.
        """
        try:
            if self.client.get_connected():
                return True
        except Exception as e:
            # Defensive: some native failures may bubble up here
            logger.error(f"Error while checking PLC connection state: {e}")
            return False

        # Preflight TCP connection with timeout to avoid hanging in snap7.connect
        try:
            with socket.create_connection(
                (self.ip_address, self.port), timeout=self.connect_timeout
            ) as s:
                # Successful low-level TCP connect; proceed with snap7 handshake
                pass
        except Exception as e:
            logger.error(
                f"Timeout/error while establishing TCP connection to PLC {self.ip_address}:{self.port} within {self.connect_timeout:.1f}s: {e}"
            )
            return False

        try:
            self.client.connect(self.ip_address, self.rack, self.slot, self.port)
        except Exception as e:
            logger.error(f"PLC connection error: {e}")
            return False

        self.data_store.last_connected = datetime.now()
        logger.info("Connected to PLC.")
        return True

    def read(self):
        """
        Reads the data from the PLC.
        """
        # Establish connection if needed; avoid db_read on disconnected client
        try:
            connected = self.client.get_connected()
        except Exception as e:
            logger.error(f"Error while checking PLC connection state: {e}")
            connected = False

        if not connected:
            if not self.connect():
                self.connect()
                # Not connected, skip read this cycle
                return False
        try:
            byte_amount = self.data_store.buffer_size()
            data = self.client.db_read(self.db_number, 0, byte_amount)
        except Exception as e:
            logger.error(f"Error reading data from PLC: {e}")
            return False

        self.data_store.from_bytes(data)
        self.data_store.last_connected = datetime.now()

        return True

    def write(self):
        """
        Writes the result and finished back to the PLC.
        """
        new_bytes = self.data_store.to_bytes()
        # Establish connection if needed; avoid db_write on disconnected client
        try:
            connected = self.client.get_connected()
        except Exception as e:
            logger.error(f"Error while checking PLC connection state: {e}")
            connected = False
            return False

        if not connected:
            if not self.connect():
                return False

        try:
            self.client.db_write(self.db_number, 0, new_bytes)
        except Exception as e:
            logger.error(f"Error writing data to PLC: {e}")
            return False

        self.data_store.last_connected = datetime.now()

        return True
