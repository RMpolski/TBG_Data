#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Friday April 26, 2019

@author: robertpolski
"""

import numpy as np
from typing import Union

from qcodes import VisaInstrument
from qcodes.instrument.parameter import ArrayParameter, MultiParameter
import qcodes.utils.validators as vals
import time
from functools import partial


def parse_bool(value):
    if type(value) is float:
        value = int(value)
    elif type(value) is str:
        value = value.lower()

    if value in {1, 'on', True}:
        return 1
    elif value in {0, 'off', False}:
        return 0
    else:
        print(value)
        raise ValueError('Must be boolean, on or off, 0 or 1, True or False')


# def parse_inp_bool(value):
#     if type(value) is float:
#         value = int(value)
#     elif type(value) is str:
#         value = value.lower()
#
#     if value in {1, 'on', True}:
#         return 'ON'
#     elif value in {0, 'off', False}:
#         return 'OFF'
#     else:
#         print(value)
#         raise ValueError('Must be boolean, on or off, 0 or 1, True or False')


boolcheck = (0, 1, 'on', 'off', 'ON', 'OFF', False, True)


class SIM900_stick(VisaInstrument):
    """
    Instrument Driver for the SRS Frame SIM900. Configure this class if you
    change the instruments and their port orders in the rack. Note that you
    must reset or write the escape string if you connect to any single port
    (using "CONN p,'escapestring'")
    """
    def __init__(self, name: str, address: str, reset: bool=False, **kwargs):
        """
        Args:
            name: Name to use internally in QCoDeS
            address: VISA ressource address
            reset: Reset SIM900, reset voltage sources (set to zero and output
               off)
        """
        super().__init__(name, address, terminator='\n', **kwargs)

        self.add_parameter('volt_p1', label='Port 1 Voltage', unit='V',
                           set_cmd=partial(self.setvolt, 1, 'VOLT'),
                           get_cmd=partial(self.get_from_port, 1, 'VOLT?'),
                           get_parser=float,
                           vals=vals.Numbers(-20, 20))

        self.add_parameter('volt_p2', label='Port 2 Voltage', unit='V',
                           set_cmd=partial(self.setvolt, 2, 'VOLT'),
                           get_cmd=partial(self.get_from_port, 2, 'VOLT?'),
                           get_parser=float,
                           vals=vals.Numbers(-20, 20))

        self.add_parameter('output_p1',
                           set_cmd=partial(self.write_to_port, 1, 'EXON'),
                           get_cmd=partial(self.get_from_port, 1, 'EXON?'),
                           set_parser=parse_bool,
                           get_parser=int,
                           vals=vals.Enum(*boolcheck))

        self.add_parameter('output_p2',
                           set_cmd=partial(self.write_to_port, 2, 'EXON'),
                           get_cmd=partial(self.get_from_port, 2, 'EXON?'),
                           set_parser=parse_bool,
                           get_parser=int,
                           vals=vals.Enum(*boolcheck))
                           
        # self.sum_port = 8
        
        # for i in range(4):
        #     channel = i + 1
        #     self.add_parameter('sum_chan'+str(channel),
        #                        set_cmd=partial(self.write_to_port, self.sum_port, 'CHAN {},'.format(channel)),
        #                        get_cmd=partial(self.get_from_port, self.sum_port, 'CHAN? '+str(channel)),
        #                        set_parser=self.parse_sum_chan,
        #                        get_parser=int,
        #                        vals=vals.Enum(0, 1, -1, 'off', 'OFF', False, 'invert', 'INVERT'))
        
        # ## this parameter doesn't work too well yet...
        # self.add_parameter('sum_read',
        #                    get_cmd=self._sum_volt_read,
        #                    get_parser=float)
                           

        
        self.write('FLSH 1')
        time.sleep(0.05)
        self.write('FLSH 2')
        time.sleep(0.05)
        # self.write('FLSH 8')
        # time.sleep(0.05)
        self.write_to_port(1, 'TERM', 2)
        time.sleep(0.05)
        self.write_to_port(5, 'TERM', 2)
        time.sleep(0.05)
        # self.write_to_port(8, 'TERM', 2)
        # time.sleep(0.05)
        
        # self.sum_read_averageT = 1000
        if reset:
            self.reset()

        time.sleep(0.25)
        self.connect_message()


    def reset(self):
        self.write_to_port(1, '*RST', '')
        time.sleep(0.05)
        self.write_to_port(2, '*RST', '')
        time.sleep(0.05)
        self.write('*RST')
        time.sleep(0.05)

    def write_to_port(self, port, message, val):
        sendmess = message + ' {}'.format(val)
        s = 'SNDT {},'.format(int(port)) + '"{}"'.format(sendmess)
        self.write(s)
        time.sleep(0.05)

    def get_from_port(self, port, message):
        self.write('FLOQ')
        time.sleep(0.05)
        s = 'SNDT {},'.format(int(port)) + '"{}"'.format(message)
        self.write(s)
        time.sleep(0.1)
        ans = self.ask('GETN? {},20'.format(int(port)))[5:]
        time.sleep(0.05)
        return ans

    def setvolt(self, port, message, val):
        self.write_to_port(port, message, np.round(val, 3))
        
    # def parse_sum_chan(self, value):
    #     if type(value) is str:
    #         value = str.lower()
    #     elif type(value) is float:
    #         value = int(value)
        
    #     if value in (0, 'off', False):
    #         return 0
    #     elif value in (-1, 'invert'):
    #         return -1
    #     elif value == 1:
    #         return 1
    #     else:
    #         raise ValueError('Value must be in (-1, 1, 0, "invert", "off", False)')
            
    # def _sum_volt_read(self):
    #     if self.sum_read_averageT < 10:
    #         self.sum_read_averageT = 10
    #     elif self.sum_read_averageT > 10000:
    #         self.sum_read_averageT = 10000
        
    #     self.write('FLOQ')
    #     time.sleep(0.05)
    #     self.write('SNDT {}, "READ? {}"'.format(int(self.sum_port), int(self.sum_read_averageT)))
    #     time.sleep(self.sum_read_averageT/1000 + 0.1)
    #     ans = self.ask('GETN? {},20'.format(int(self.sum_port)))[5:]
    #     time.sleep(0.05)
    #     return ans
            
