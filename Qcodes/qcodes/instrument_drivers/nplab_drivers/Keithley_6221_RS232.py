#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan 19 13:32:00 2018

@author: robertpolski
"""

import numpy as np
from typing import Union

from qcodes import Instrument
from qcodes.instrument.parameter import ArrayParameter, MultiParameter
import qcodes.utils.validators as vals
import time
from functools import partial
import serial
from qcodes.utils.helpers import strip_attrs

boolcheck = (0, 1, 'on', 'off', 'ON', 'OFF', False, True)


def parse_output_bool(value):
    if int(value) == 1 or int(value) == 0:
        return int(value)
    elif value is True or value is False:
        return int(value)
    elif value == 'on' or value == 'ON':
        return 1
    elif value == 'off' or value == 'OFF':
        return 0
    else:
        raise ValueError('Must be boolean, 0 or 1, True or False')

class Keithley_6221_rs232(Instrument):
    """
    We made this since we don't have GPIB cables that reach out to the magnet. So the RS-232-usb cable
    can reach, although you need to make sure to have the null-modem adapter on it.
    """

    def __init__(self, name: str, address: str, timeout=8, **kwargs):
        """
        Args:
            name: Name to use internally in QCoDeS
            address: VISA ressource address COM4 is the currently connected usb port)
            timeout: for the serial communication
        """
        super().__init__(name, **kwargs)

        self.address = address
        self.terminator = '\n'
        self._open_serial_connection(timeout)

        self._ac_init = False
        self._ac_ampl = False
        self._ac_freq = False

        self.add_parameter('current',
                           label='Current',
                           get_cmd='SOUR:CURR?',
                           set_cmd='SOUR:CURR {}',
                           get_parser=float,
                           unit='A',
                           vals=vals.Numbers(-105e-3, 105e-3))
        self.add_parameter('output',
                           get_cmd='OUTP:STAT?',
                           set_cmd='OUTP:STAT {}',
                           get_parser=int,
                           set_parser=parse_output_bool,
                           vals=vals.Enum(*boolcheck))
        self.add_parameter('range',
                           get_cmd='CURR:RANG?',
                           set_cmd='CURR:RANG {}',
                           get_parser=float,
                           unit='A',
                           vals=vals.Numbers(-105e-3, 105e-3))
        self.add_parameter('auto_range',
                           get_cmd='CURR:RANG:AUTO?',
                           set_cmd='CURR:RANG:AUTO {}',
                           get_parser=int,
                           set_parser=parse_output_bool,
                           vals=vals.Enum(*boolcheck))
        self.add_parameter('compliance',
                           get_cmd='CURR:COMP?',
                           set_cmd='CURR:COMP {}',
                           unit='V',
                           get_parser=float,
                           vals=vals.Numbers(-.1, 105))
        self.add_parameter('delay',
                           unit='s',
                           get_cmd='SOUR:DEL?',
                           set_cmd='SOUR:DEL {}',
                           get_parser=float,
                           vals=vals.Numbers(0.001, 999999.999))
        self.add_parameter('filter',
                           get_cmd='CURR:FILT?',
                           set_cmd='CURR:FILT {}',
                           get_parser=int,
                           set_parser=parse_output_bool,
                           vals=vals.Enum(*boolcheck))
        self.add_parameter('speed',
                           get_cmd='OUTP:RESP?',
                           set_cmd='OUTP:RESP {}',
                           get_parser=str,
                           vals=vals.Enum('slow', 'fast', 'SLOW', 'FAST'))
        self.add_parameter('display',
                           snapshot_get=False,
                           get_cmd='DISP:ENAB?',
                           set_cmd='DISP:ENAB {}',
                           get_parser=int,
                           set_parser=parse_output_bool,
                           vals=vals.Enum(*boolcheck))
        self.add_parameter('beeper',
                           snapshot_get=False,
                           get_cmd='SYST:BEEP?',
                           set_cmd='SYST:BEEP {}',
                           get_parser=int,
                           set_parser=parse_output_bool,
                           vals=vals.Enum(*boolcheck))

        self.add_parameter('AC_amplitude',
                           get_cmd='SOUR:WAVE:AMPL?',
                           set_cmd=self._setac_amplitude,
                           get_parser=float,
                           unit='A',
                           vals=vals.Numbers(2e-12, 0.105))
        self.add_parameter('AC_frequency',
                           get_cmd='SOUR:WAVE:FREQ?',
                           set_cmd=self._setac_frequency,
                           get_parser=float,
                           unit='Hz',
                           vals=vals.Numbers(0, 1e5))
        self.add_parameter('AC_offset',
                           get_cmd='SOUR:WAVE:OFFS?',
                           set_cmd='SOUR:WAVE:OFFS {}',
                           get_parser=float,
                           unit='A',
                           vals=vals.Numbers(-0.105, 0.105))
        self.add_parameter('AC_duration_time',
                           get_cmd='SOUR:WAVE:DUR:TIME?',
                           set_cmd='SOUR:WAVE:DUR:TIME {}',
                           get_parser=float,
                           unit='s',
                           vals=vals.MultiType(vals.Enum('INF'),
                                               vals.Numbers(100e-9,
                                                            999999.999)))
        self.add_parameter('AC_duration_cycles',
                           get_cmd='SOUR:WAVE:DUR:CYCL?',
                           set_cmd='SOUR:WAVE:DUR:CYCL {}',
                           get_parser=float,
                           unit='cycles',
                           vals=vals.MultiType(vals.Enum('INF'),
                                               vals.Numbers(0.001,
                                                            99999999900)))
        self.add_parameter('AC_phasemark',
                           get_cmd='SOUR:WAVE:PMAR:STAT?',
                           set_cmd='SOUR:WAVE:PMAR:STAT {}',
                           get_parser=int,
                           set_parser=parse_output_bool,
                           vals=vals.Enum(*boolcheck))
        self.add_parameter('AC_phasemark_offset',
                           get_cmd='SOUR:WAVE:PMAR?',
                           set_cmd='SOUR:WAVE:PMAR {}',
                           get_parser=float,
                           unit='degrees',
                           vals=vals.Numbers(0, 360))
        self.add_parameter('AC_ranging',
                           get_cmd='SOUR:WAVE:RANG?',
                           set_cmd='SOUR:WAVE:RANG {}',
                           get_parser=str,
                           vals=vals.Enum('BEST', 'best', 'FIX', 'fix',
                                          'FIXED', 'fixed'))

        self.connect_message()

    def _open_serial_connection(self, timeout=None):
        if timeout is None:
            ser = serial.Serial(self.address, 115200, rtscts=True)
        else:
            ser = serial.Serial(self.address, 115200, timeout=timeout, rtscts=True)
        if not (ser.isOpen()):
            ser.open()
        self._ser = ser

    def close(self):
        """Irreversibly stop this instrument and free its resources.
        Closes the serial connection too"""
        if hasattr(self, 'connection') and hasattr(self.connection, 'close'):
            self.connection.close()
        ser = self._ser
        ser.close()

        strip_attrs(self, whitelist=['name'])
        self.remove_instance(self)

    def reset(self):
        self._ser.write('*RST'+self.terminator)

    def ask_raw(self, cmd):
        cmd += self.terminator
        self._ser.write(cmd.encode('utf-8'))
        time.sleep(0.01)
        ans = self._ser.readline().decode('utf-8').strip()
        return ans

    def write_raw(self, cmd):
        cmd += self.terminator
        self._ser.write(cmd.encode('utf-8'))

    def _setac_amplitude(self, amp):
        """This is just the helper function for the AC_amplitude parameter"""
        if self._ac_freq is False:
            print('Must enter frequency')
        if self._ac_init is False:
            self.write('SOUR:WAVE:FUNC SIN')
            self.write('SOUR:WAVE:AMPL {}'.format(amp))
        else:
            self.write('SOUR:WAVE:AMPL {}'.format(amp))
        self._ac_ampl = True

    def _setac_frequency(self, freq):
        """This is just the helper function for the AC_frequency parameter"""
        if self._ac_ampl is False:
            print('Must enter amplitude')
        if self._ac_init is False:
            self.write('SOUR:WAVE:FUNC SIN')
            self.write('SOUR:WAVE:FREQ {}'.format(freq))
        else:
            self.write('SOUR:WAVE:FREQ {}'.format(freq))
        self._ac_freq = True

    def AC_init(self):
        if self._ac_freq is False:
            print('Must enter frequency')
        if self._ac_ampl is False:
            print('Must enter amplitude')
        self.write('SOUR:WAVE:ARM')
        self.write('SOUR:WAVE:INIT')
        self._ac_init = True

    def abort_AC(self):
        if self._ac_init is False:
            print('Already aborted')
        else:
            self.write('SOUR:WAVE:ABOR')
            self._ac_init = False