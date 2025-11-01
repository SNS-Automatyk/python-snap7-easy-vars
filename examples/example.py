import snap7_easy_vars


class MyPLCData(snap7_easy_vars.PLCData):
    temperature = snap7_easy_vars.PLCRealField(0)
    pressure = snap7_easy_vars.PLCWordField(4)
    status = snap7_easy_vars.PLCBoolField(6, 0, settable=True)


def start_fake_plc():
    """
    This function would start a fake PLC for testing purposes.
    In a real scenario, you would connect to an actual PLC.
    """
    import snap7
    import asyncio

    loop = asyncio.get_event_loop()

    def loop_in_thread(loop):
        asyncio.set_event_loop(loop)
        loop.run_until_complete(snap7.server.mainloop(102, init_standard_values=True))

    import threading

    t = threading.Thread(target=loop_in_thread, args=(loop,))
    t.start()


def main():
    start_fake_plc()

    my_plc_data = MyPLCData()
    my_plc_connection = snap7_easy_vars.PLCConnection(
        ip_address="127.0.0.1", data_store=my_plc_data, rack=0, slot=1
    )

    success = my_plc_connection.connect()
    print(f"Connection success: {success}")

    success = my_plc_connection.read()
    print(f"Read success: {success}")

    print(f"Temperature: {my_plc_data.temperature}")
    print(f"Pressure: {my_plc_data.pressure}")
    print(f"Status: {my_plc_data.status}")

    my_plc_data.status = not my_plc_data.status
    success = my_plc_connection.write()
    print(f"Write success: {success}")
    if success:
        print(f"Updated status to {my_plc_data.status} and wrote back to PLC.")

    # Check if updated correctly
    success = my_plc_connection.read()
    print(f"Read success: {success}")
    if success:
        print(f"Updated Status: {my_plc_data.status}")

    # Clean up
    import os

    os._exit(0)


if __name__ == "__main__":
    main()
