# aioxbee
Read rx_data and rx_io_data_long_addr frames using pyserial-asyncio and python-xbee with an XBee ZigBee module acting as coordinator.

Assume an XBee ZigBee Coordinator is attached to /dev/ttyUSB0.

To implement a custom protocol, create a new class that overrides <code>ZigbeeAsyncSerialBase.handle_rx_data</code>.

To process IO sampling frames override <code>ZigbeeAsyncSerialBase.handle_samples</code>.

Check out the [xbee3-laundry aioxbee-laundry example](https://github.com/idatum/xbee3-laundry/tree/main/examples/aioxbee-laundry) for how to create a customer coordinator.
