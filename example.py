import asyncio
import logging
from polar_h10 import PolarH10
import datetime
import os

def data_callback(data: bytes):
    """Callback function to handle incoming data."""
    # For now, just print the length of data received
    print(f"Received {len(data)} bytes of data")

async def main():
    # Create a Polar H10 instance
    polar = PolarH10()

    try:
        # Connect to the device
        connected = await polar.connect()
        if not connected:
            print("Could not connect to Polar H10")
            return

        # Set up data callback
        polar.set_notification_callback(data_callback)

        # Start recording ECG data
        print("Starting ECG recording... Press Enter to stop")
        await polar.start_recording(measurement_type=PolarH10.ECG_MEASUREMENT)

        # Wait for user input to stop recording
        await asyncio.get_event_loop().run_in_executor(None, input)

        # Stop recording
        await polar.stop_recording(measurement_type=PolarH10.ECG_MEASUREMENT)

        # Get all collected data
        data = polar.get_data()
        
        # Save the data to a file
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"polar_h10_data_{timestamp}.bin"
        
        with open(filename, "wb") as f:
            f.write(data)
        
        print(f"Saved {len(data)} bytes of data to {filename}")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Always disconnect
        await polar.disconnect()

if __name__ == "__main__":
    asyncio.run(main()) 