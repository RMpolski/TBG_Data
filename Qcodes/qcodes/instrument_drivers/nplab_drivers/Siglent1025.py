#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Friday Nov 23, 2021

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
        return 'ON'
    elif value in {0, 'off', False}:
        return 'OFF'
    else:
        print(value)
        raise ValueError('Must be boolean, on or off, 0 or 1, True or False')

def amp_parse(msg):
    m = msg.split(',')
    for i in range(len(m)):
        if 'AMP' in m[i]:
            return float(m[i+1].strip(' V'))

def freq_parse(msg):
    m = msg.split(',')
    for i in range(len(m)):
        if 'FRQ' in m[i]:
            return float(m[i+1].strip(' HZ'))

def phase_parse(msg):
    m = msg.split(',')
    for i in range(len(m)):
        if 'PHSE' in m[i]:
            return float(m[i+1].strip())

def output_parse(msg):
    return msg.split(',')[0].split()[1]


boolcheck = (0, 1, 'on', 'off', 'ON', 'OFF', False, True)

class Siglent1025(VisaInstrument):
    """For any of Sigment1025 AC source two channels. Parameters are as
    Initialized Parameters:
            voltage: sets voltage (in volts)
            current: sets current (in amperes)
            output: turns the output on or off (takes 0 or 1)
            volt_max: the max voltage that is allowed to be set on the
                instrument (for sensitive samples)
            volt_protection
        The output satisfies the limiting criterion. If current is the limiting
        factor, the set voltage level will be output, and vice versa.
    """

    def __init__(self, name: str, address: str, reset: bool=False, **kwargs):
        """
        Args:
            name: Name to use internally in QCoDeS
            address: VISA ressource address
            reset: Set Keithley to defaults? True or False
        """
        super().__init__(name, address, terminator='\n', **kwargs)

        
        self.add_parameter('C1_output', set_cmd='C1: OUTP {}',
                           get_cmd='C1: OUTP?', set_parser=parse_bool, get_parser=output_parse,
                           vals=vals.Enum(*boolcheck))
        self.add_parameter('C2_output', set_cmd='C2: OUTP {}',
                           get_cmd='C2: OUTP?', set_parser=parse_bool, get_parser=output_parse,
                           vals=vals.Enum(*boolcheck))
       
       
        self.add_parameter('C1_volt', set_cmd='C1:BSWV AMP, {}',
                           get_cmd='C1:BSWV?', unit='V', get_parser=amp_parse,
                           vals=vals.Numbers(0.002, 10))
        self.add_parameter('C2_volt', set_cmd='C2:BSWV AMP, {}',
                           get_cmd='C2:BSWV?', unit='V', get_parser=amp_parse,
                           vals=vals.Numbers(0.002, 10))

        self.add_parameter('C1_freq', set_cmd='C1:BSWV FRQ, {}',
                           get_cmd='C1:BSWV?', unit='Hz', get_parser=freq_parse,
                           vals=vals.Numbers(1e-6, 25e6))
        self.add_parameter('C2_freq', set_cmd='C2:BSWV FRQ, {}',
                           get_cmd='C2:BSWV?', unit='Hz', get_parser=freq_parse,
                           vals=vals.Numbers(1e-6, 25e6))
                
        self.add_parameter('C1_phase', set_cmd='C1:BSWV PHSE, {}',
                           get_cmd='C1:BSWV?', unit='degree', get_parser=phase_parse,
                           vals=vals.Numbers(-360, 360))
        self.add_parameter('C2_phase', set_cmd='C2:BSWV PHSE, {}',
                           get_cmd='C2:BSWV?', unit='degree', get_parser=phase_parse,
                           vals=vals.Numbers(-360, 360))

        self.add_function('reset', call_cmd='*RST')

        if reset:
            self.reset()

        self.connect_message()