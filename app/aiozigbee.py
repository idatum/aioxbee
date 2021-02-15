import logging
import logging.handlers
import struct
import asyncio
import serial_asyncio
import xbee

# Logging
Log = logging.getLogger("aioxbee")

class ZigbeeAsyncSerialBase(asyncio.Protocol):

    def __init__(self):
        super().__init__()
        self.seen_addreses = set()
        self.address_data = {}

    """ Override this method """
    async def handle_rx_data(self, address, rx_data):
        Log.debug(f"rx_data: {rx_data}")
        Log.warning(f"No override for handle_rx_data: address = 0x{self.hex_address(address)}")

    """ Override this method """
    async def handle_samples(self, address, samples):
        Log.debug(f"IO sampling: {samples}")
        Log.warning(f"No override for handle_samples: address = 0x{self.hex_address(address)}")

    async def process_frame(self, next_frame):
        if "id" not in next_frame or ("source_addr_long" not in next_frame and "dest_addr" not in next_frame):
            Log.warning("unknown frame: {}".format(next_frame))
            return
        frame_id = next_frame["id"]
        if "source_addr_long" in next_frame:
            source_address = next_frame["source_addr_long"]
            if source_address not in self.seen_addreses:
                self.seen_addreses.add(source_address)
                Log.info("seen address: 0x{}".format(self.hex_address(source_address)))
            if frame_id == "rx":
                rf_data = next_frame["rf_data"]
                # Process frame type 0x17 as remote_at command.
                if len(rf_data) > 3 and 0x17 == rf_data[3]:
                    await self.handle_remote_at(source_address, rf_data)
                else:
                    Log.info("handling data")
                    await self.handle_rx_data(source_address, rf_data)
            elif frame_id == "rx_io_data_long_addr":
                Log.info("handling samples")
                await self.handle_samples(source_address, next_frame["samples"])
        elif "dest_addr" in next_frame and frame_id == "tx_status":
            dest_addr = next_frame["dest_addr"]
            # short address
            addr = struct.unpack(">H", dest_addr)[0]
            Log.info("Handled tx_status for 0x%x deliver status : %s" % (addr, next_frame["deliver_status"]))
        else:
            Log.warning("unknown frame: {}".format(next_frame))

    async def send_remote_command(self, cmd, **kwargs):
        data = self.zigbee._build_command(cmd, **kwargs)
        frame = xbee.frame.APIFrame(data, False).output()
        self.transport.write(frame)
        Log.debug('sent {}'.format(frame))

    async def handle_remote_at(self, src_address, rf_data):
        # expecting 17 bytes between length field (2 bytes) and checksum:
        length = (rf_data[1] >> 8) + rf_data[2]
        if length < 0x11:
            Log.error('remote_at length ({}) is unexpected: {}'.format(length, rf_data))
            return
        opt = rf_data[15]
        if opt != 2:
            Log.error("remote_at option ({}) is unexpected: {}".format(opt, rf_data))
            return
        pin = rf_data[16:18].decode('utf-8')
        if pin[0].upper() != 'D':
            Log.error("remote_at command ({}) is unexpected: {}".format(pin, rf_data))
            return
        dest_address = rf_data[5:13]
        arg = rf_data[18:20]
        Log.info("{} remote_at {}, {}, {}, {}".format(self.hex_address(src_address),
                                                   self.hex_address(dest_address),
                                                   opt, pin, arg[1]))
        await self.send_remote_command(cmd='remote_at',
                            dest_addr_long=dest_address,
                            command=pin,
                            parameter=arg)

    async def send_remote_pin(self, dest, pin, param):
        await self.send_remote_command(cmd='remote_at',
                            dest_addr_long=dest,
                            command=pin,
                            parameter=param)

    async def send_transmit_request(self, dest, data):
        await self.send_remote_command(cmd='tx',
                            dest_addr_long=dest,
                            data=data)

    def hex_address(self, address):
        """ Unpack as hex string """
        if len(address) == 0:
            return None
        return '%x' % (struct.unpack(">Q", address)[0])

    def split_frame(self, frame):
        next_frame = self.zigbee._split_response(frame.data)
        return next_frame

    def on_data_received(self, data):
        for d in data:
            byte = struct.pack('B', d)
            try:
                if byte == xbee.frame.APIFrame.START_BYTE:
                    Log.debug('Start byte read')
                    if len(self.frame.raw_data) > 0:
                        Log.warning('Partial frame read; resetting. {}'.format(self.frame.raw_data))
                        self.frame = xbee.frame.APIFrame(escaped=True)

                self.frame.fill(byte)

                if self.frame.remaining_bytes() == 0:
                    Log.debug('Parsing frame.')
                    self.frame.parse()
                    next_frame = self.split_frame(self.frame)
                    asyncio.create_task(self.process_frame(next_frame))
                    self.frame = xbee.frame.APIFrame(escaped=True)
            except ValueError as e:
                Log.exception(e)
                self.frame = xbee.frame.APIFrame(escaped=True)

    def write_frame(self, frame):
        self.transport.write(frame)

    # asyncio.Protocol
    """ Setup """
    def connection_made(self, transport):
        self.transport = transport
        self.frame = xbee.frame.APIFrame(escaped=True)
        self.zigbee = xbee.ZigBee(ser=None)
        Log.info('port opened {}'.format(transport))
        transport.serial.rts = False  # You can manipulate Serial object via transport

    # asyncio.Protocol
    def data_received(self, data):
        Log.debug('data received {}'.format(repr(data)))
        self.on_data_received(data)

    # asyncio.Protocol
    def connection_lost(self, exc):
        Log.info('port closed')
        self.transport.loop.stop()

    # asyncio.Protocol
    def pause_writing(self):
        Log.info('pause writing')
        print(self.transport.get_write_buffer_size())
    
    # asyncio.Protocol
    def resume_writing(self):
        Log.info(self.transport.get_write_buffer_size())
        Log.info('resume writing')


if __name__ == '__main__':
    # Test with debug tracing
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
                        datefmt='%m-%d-%Y %H:%M:%S')

    loop = asyncio.get_event_loop()
    # Include asyncio debug tracing
    loop.set_debug(True)

    coro = serial_asyncio.create_serial_connection(loop, ZigbeeAsyncSerialBase, "/dev/ttyUSB0", baudrate=115200)

    loop.run_until_complete(coro)
    loop.run_forever()
    loop.close()
