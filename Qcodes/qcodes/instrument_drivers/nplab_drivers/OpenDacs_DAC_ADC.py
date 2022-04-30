#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 30 16:38:38 2018
DAC_ADC driver for QCodes, modeled after the do_DAC_ADC driver for qtlab
@author: robertpolski
"""


from qcodes import Instrument
import qcodes.utils.validators as vals
from qcodes.utils.helpers import strip_attrs
from functools import partial
import serial
import time

# Helper functions ##########################


def ch_convert(DAC_ADC, ch):
    """Converts from the written channel names to the internal
    channel names according to the Arduino"""
    DAC_dict = {'A': '1',
                'B': '3',
                'C': '0',
                'D': '2'}
    ADC_dict = {0: '2',
                1: '0',
                2: '3',
                3: '1'}
    con_ch = ''
    if DAC_ADC == 'DAC':
        con_ch = DAC_dict[ch]
    elif DAC_ADC == 'ADC':
        con_ch = ADC_dict[ch]
    else:
        raise ValueError('Must choose either DAC or ADC')
    return con_ch


def DAC_setvolt(ser, ch, volt):
    con_ch = ch_convert('DAC', ch)
    s = 'SET,' + con_ch + ',' + str(volt) + '\r'
    ser.write(s.encode('utf-8'))
    mes = ser.readline().decode('utf-8')
    # TODO: Calibrate and remove printed statements
    # print(mes)  # Uncomment this to bring back printed statements
    # set_ch = mes.split(' ')[1]  # Uncomment to get the set channel
    set_volt = mes.split(' ')[4].split('V')[0]
    return float(set_volt)  # can include channel with , set_ch


def ADC_getvolt(ser, ch):
    con_ch = ch_convert('ADC', ch)
    s = 'GET_ADC,' + con_ch + '\r'
    ser.write(s.encode('utf-8'))
    mes = ser.readline().decode('utf-8')
    return float(mes)


##########################################

class DAC_ADC(Instrument):
    """
    The OpenDac DAC_ADC instrument. Initialize with
    address: the address of the Arduino Due ('COM5', for example).
    reset=True sets all DAC voltages to 0. Timout is the arduino's timeout
    """
    def __init__(self, name: str, address: str, timeout=None,
                 reset: bool=False, **kwargs):
        """
        Args:
            name: Name to use internally in QCoDeS
            address: VISA resource address
            timeout: Serial connection timeout
            reset: Set all DAC values to 0? True or False
        """
        super().__init__(name, **kwargs)

        self.address = address
        self._open_serial_connection(timeout)
        self.dac_vals = {'A': None,
                         'B': None,
                         'C': None,
                         'D': None}
                         
        self.adc_ctimes = {0: None, 1: None, 2: None, 3: None}

        self.add_parameter('DAC_A', set_cmd=partial(self.DAC_set, 'A'),
                           unit='V', vals=vals.Numbers(-10, 10))
        self.add_parameter('DAC_B', set_cmd=partial(self.DAC_set, 'B'),
                           unit='V', vals=vals.Numbers(-10, 10))
        self.add_parameter('DAC_C', set_cmd=partial(self.DAC_set, 'C'),
                           unit='V', vals=vals.Numbers(-10, 10))
        self.add_parameter('DAC_D', set_cmd=partial(self.DAC_set, 'D'),
                           unit='V', vals=vals.Numbers(-10, 10))
        self.add_parameter('ADC_0', get_cmd=partial(self.ADC_get, 0),
                           unit='V')
        self.add_parameter('ADC_1', get_cmd=partial(self.ADC_get, 1),
                           unit='V')
        self.add_parameter('ADC_2', get_cmd=partial(self.ADC_get, 2),
                           unit='V')
        self.add_parameter('ADC_3', get_cmd=partial(self.ADC_get, 3),
                           unit='V')
        self.add_parameter('ADC_0_convert_time', set_cmd=partial(self.ADC_setctime, 0),
                           unit='us', vals=vals.Ints(82, 2682))
        self.add_parameter('ADC_1_convert_time', set_cmd=partial(self.ADC_setctime, 1),
                           unit='us', vals=vals.Ints(82, 2682))
        self.add_parameter('ADC_2_convert_time', set_cmd=partial(self.ADC_setctime, 2),
                           unit='us', vals=vals.Ints(82, 2682))
        self.add_parameter('ADC_3_convert_time', set_cmd=partial(self.ADC_setctime, 3),
                           unit='us', vals=vals.Ints(82, 2682))

        if reset:
            self.reset()

    def _open_serial_connection(self, timeout=None):
        if timeout is None:
            ser = serial.Serial(self.address, 115200)
        else:
            ser = serial.Serial(self.address, 115200, timeout=timeout)
        print(ser.isOpen())
        if not (ser.isOpen()):
            ser.open()
        self._ser = ser
        print('Connected to ', self.address)
        # print(self.get_idn())  # for some reason get_idn() doesn't work as
        # the first command, but it works after using other commands.
        # It doesn't work even after waiting like 2 seconds

    def reset(self):
        """Set all DAC voltages to 0"""
        self.DAC_set('A', 0)
        self.DAC_set('B', 0)
        self.DAC_set('C', 0)
        self.DAC_set('D', 0)

    def get_idn(self):
        """ The idn for this instrument also comes from the *IDN command, but
        it needs a \r endline character, and it only returns the instrument
        name"""
        idstr = ''
        self._ser.write('*IDN?\r'.encode('utf-8'))
        idstr = self._ser.readline().decode('utf-8')
        if idstr == '':
            idstr = 'Not connected properly. Cannot find IDN'
        return idstr

    def close(self):
        """Irreversibly stop this instrument and free its resources.
        Closes the serial connection too"""
        if hasattr(self, 'connection') and hasattr(self.connection, 'close'):
            self.connection.close()
        ser = self._ser
        ser.close()

        strip_attrs(self, whitelist=['name'])
        self.remove_instance(self)

    def DAC_set(self, ch, volt):
        """ Sets the given DAC channel ch to voltage volt.
        ch can be an uppercase single-letter string from A to D"""
        dac_val = DAC_setvolt(self._ser, ch, volt)
        self.dac_vals[ch] = dac_val

    def ADC_get(self, ch):
        """ Gets the current value in volts at the given ADC channel ch
        ch can be an integer from 0 to 3"""
        return ADC_getvolt(self._ser, ch)

    def ADC_setctime(self, ch, t):
        con_ch = ch_convert('ADC', ch)
        s = 'CONVERT_TIME,' + con_ch + ',' + str(int(t)) + '\r'
        _ret = self._ser.write(s.encode('utf-8'))
        mes = self._ser.readline().decode('utf-8')
        self.adc_ctimes[ch] = int(mes.strip())
        

    def if_ready(self):
        """ Returns True if DAC-ADC is ready for the next command and False
        if not"""
        self._ser.write('*RDY?\r'.encode('utf-8'))
        if self._ser.readline().decode('utf-8') == 'READY\r\n':
            return True
        else:
            return False
