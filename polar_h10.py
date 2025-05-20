import asyncio
from typing import Optional, List, Callable
import struct
import logging
from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PolarH10:
    # Polar H10 specific UUIDs
    PMD_SERVICE = "FB005C80-02E7-F387-1CAD-8ACD2D8DF0C8"
    PMD_CONTROL = "FB005C81-02E7-F387-1CAD-8ACD2D8DF0C8"
    PMD_DATA = "FB005C82-02E7-F387-1CAD-8ACD2D8DF0C8"

    # PMD Control Point Commands
    REQUEST_MEASUREMENT_SETTINGS = 0x01
    START_MEASUREMENT = 0x02
    STOP_MEASUREMENT = 0x03

    # Measurement types
    ECG_MEASUREMENT = 0x00
    PPG_MEASUREMENT = 0x01
    ACC_MEASUREMENT = 0x02
    HR_MEASUREMENT = 0x03

    def __init__(self):
        self.device: Optional[BLEDevice] = None
        self.client: Optional[BleakClient] = None
        self.recording = False
        self._data_buffer = bytearray()
        self._notification_callback = None

    def notification_handler(self, sender: int, data: bytearray):
        """Handle incoming notifications from the device."""
        logger.debug(f"Received data: {data.hex()}")
        self._data_buffer.extend(data)
        if self._notification_callback:
            self._notification_callback(data)

    async def scan_for_device(self) -> bool:
        """Scan for Polar H10 device."""
        logger.info("Scanning for Polar H10...")
        
        devices = await BleakScanner.discover()
        for device in devices:
            if device.name and "Polar H10" in device.name:
                self.device = device
                logger.info(f"Found Polar H10: {device.name}")
                return True
        
        logger.warning("No Polar H10 device found")
        return False

    async def connect(self) -> bool:
        """Connect to the Polar H10 device."""
        if not self.device:
            success = await self.scan_for_device()
            if not success:
                return False

        try:
            self.client = BleakClient(self.device)
            await self.client.connect()
            logger.info("Connected to Polar H10")

            # Enable notifications for PMD data
            await self.client.start_notify(
                self.PMD_DATA,
                self.notification_handler
            )
            logger.info("Enabled PMD data notifications")
            return True
        except Exception as e:
            logger.error(f"Error connecting to device: {e}")
            return False

    async def disconnect(self):
        """Disconnect from the device."""
        if self.client and self.client.is_connected:
            try:
                await self.client.stop_notify(self.PMD_DATA)
                await self.client.disconnect()
                logger.info("Disconnected from Polar H10")
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")

    async def _send_command(self, command: int, measurement_type: int):
        """Send a command to the PMD Control Point."""
        command_bytes = struct.pack("<BB", command, measurement_type)
        await self.client.write_gatt_char(self.PMD_CONTROL, command_bytes)

    async def start_recording(self, measurement_type: int = ECG_MEASUREMENT):
        """Start recording an exercise session."""
        if not self.client or not self.client.is_connected:
            raise ConnectionError("Not connected to Polar H10")

        try:
            # Clear the data buffer
            self._data_buffer.clear()
            
            # Request measurement settings first
            await self._send_command(self.REQUEST_MEASUREMENT_SETTINGS, measurement_type)
            await asyncio.sleep(0.1)  # Wait for settings response
            
            # Start the measurement
            await self._send_command(self.START_MEASUREMENT, measurement_type)
            self.recording = True
            logger.info(f"Started recording measurement type: {measurement_type}")
        except Exception as e:
            logger.error(f"Error starting recording: {e}")
            raise

    async def stop_recording(self, measurement_type: int = ECG_MEASUREMENT):
        """Stop recording the exercise session."""
        if not self.client or not self.client.is_connected:
            raise ConnectionError("Not connected to Polar H10")

        try:
            await self._send_command(self.STOP_MEASUREMENT, measurement_type)
            self.recording = False
            logger.info("Stopped recording")
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            raise

    def get_data(self) -> bytes:
        """Get the collected data from the buffer."""
        data = bytes(self._data_buffer)
        self._data_buffer.clear()
        return data

    def set_notification_callback(self, callback: Callable[[bytes], None]):
        """Set a callback function to handle incoming data notifications."""
        self._notification_callback = callback 