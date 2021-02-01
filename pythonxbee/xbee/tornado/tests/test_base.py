#! /usr/bin/python
"""
test_base.py

By Paul Malmsten, 2010
pmalmsten@gmail.com

Tests the XBeeBase superclass module for XBee API conformance.
"""

import unittest
try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock

from xbee.tornado import has_tornado

if not has_tornado:
    raise unittest.SkipTest("Requires Tornado")

from tornado import ioloop # noqa
from tornado.testing import AsyncTestCase, gen_test  # noqa
from tornado.test.util import unittest  # noqa
from xbee.tornado.base import XBeeBase  # noqa
from xbee.tests.Fake import Serial  # noqa


class TestReadFromDevice(AsyncTestCase):
    """
    XBeeBase class should properly read and extract data from a valid
    API frame
    """

    def setUp(self):
        super(TestReadFromDevice, self).setUp()
        self._patch_io = ioloop.IOLoop.current()
        self._patch_io.add_handler = Mock()

    @gen_test
    def test_read(self):
        """
        _wait_for_frame should properly read a frame of data
        """
        device = Serial()
        device.set_read_data(b'\x7E\x00\x01\x00\xFF')
        xbee = XBeeBase(device, io_loop=self._patch_io)

        xbee._process_input(None, None)
        frame = yield xbee._get_frame()
        self.assertEqual(frame.data, b'\x00')

    @gen_test
    def test_read_invalid_followed_by_valid(self):
        """
        _wait_for_frame should skip invalid data
        """
        device = Serial()
        device.set_read_data(b'\x7E\x00\x01\x00\xFA' + b'\x7E\x00\x01\x05\xFA')
        xbee = XBeeBase(device, io_loop=self._patch_io)

        xbee._process_input(None, None)
        # First process ends with no good frame, process next
        xbee._process_input(None, None)
        frame = yield xbee._get_frame()
        self.assertEqual(frame.data, b'\x05')

    @gen_test
    def test_read_escaped(self):
        """
        _wait_for_frame should properly read a frame of data
        Verify that API mode 2 escaped bytes are read correctly
        """
        device = Serial()
        device.set_read_data(
            b'\x7E\x00\x04\x7D\x5E\x7D\x5D\x7D\x31\x7D\x33\xE0')

        xbee = XBeeBase(device, escaped=True, io_loop=self._patch_io)

        xbee._process_input(None, None)
        frame = yield xbee._get_frame()
        self.assertEqual(frame.data, b'\x7E\x7D\x11\x13')


if __name__ == '__main__':
    unittest.main()
