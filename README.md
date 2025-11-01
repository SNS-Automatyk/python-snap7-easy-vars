# Python Snap7 Easy Vars
A Python wrapper for the snap7 PLC communication library with easy variable management

## Quick Start
Install the package via pip:

```bash
pip install python-snap7-easy-vars
```

Import the library and create a data structure:

```python
import snap7_easy_vars

class MyPLCData(snap7_easy_vars.PLCData):
    # Define PLC variables with their data types and offsets
    temperature = snap7_easy_vars.PLCRealField(byte_offset=0) 
    pressure = snap7_easy_vars.PLCWordField(byte_offset=4)

    # By default, fields are read-only; to make a field settable, use the 'settable' parameter
    status = snap7_easy_vars.PLCBoolField(byte_offset=6, bit_offset=0, settable=True)

```

Connect to the PLC and read/write data:

```python
my_plc_data = MyPLCData()
my_plc_connection = snap7_easy_vars.PLCConnection(
    ip_address="192.168.0.1", # PLC IP address
    data_store=my_plc_data,
    db_number=1, # PLC DB number
    rack=0, # PLC rack number
    slot=1, # PLC slot number
    port=102, # PLC port number
)

# Connect to the PLC
my_plc_connection.connect()

# Read data from the PLC
my_plc_connection.read()

# Read variables
print(f"Temperature: {my_plc_data.temperature}")
print(f"Pressure: {my_plc_data.pressure}")
print(f"Status: {my_plc_data.status}")

# Modify a variable and write back to the PLC
my_plc_data.status = True
my_plc_connection.write()
```


# Authors
- [Marvin Ruciński](https://github.com/marvinrucinski)