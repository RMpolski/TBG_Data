import numpy as np
from typing import Union

from qcodes import VisaInstrument
import logging

import pyvisa as visa
import pyvisa.constants as vi_const
import pyvisa.resources

import qcodes.utils.validators as vals
import time
from functools import partial


class SR560(VisaInstrument):
    """
    Our version of the stanford research SR560 driver. This one allows you
    to set the parameters on the pre-amp, but it doesn't automatically change
    the readings from other measurement devices
    """

    def __init__(self, name, address, timeout=10, **kwargs):
        super().__init__(name, address, timeout, terminator='\r\n', **kwargs)

        def write_raw(self, cmd):
            """ Need to redefine the write command since the RS-232 port
            normally responds and stores a value in the query"""
            response = self.visa_handle.query(cmd)

        self.gain_map = {1: '0', 2: '1', 5: '2', 10: '3', 20: '4', 50: '5', 100: '6',
                         200: '7', 500: '8', 1000: '9', 2000: '10', 5000: '11',
                         10000: '12', 20000: '13', 50000: '14'}

        self.highpass_map = {0.03: '0', 0.1: '1', 0.3: '2', 1: '3', 3: '4',
                             10: '5', 30: '6', 100: '7', 300: '8', 1000: '9',
                             3000: '10', 10000: '11'}
        self.lowpass_map = {0.03: '0', 0.1: '1', 0.3: '2', 1: '3', 3: '4',
                            10: '5', 30: '6', 100: '7', 300: '8', 1000: '9',
                            3000: '10', 10000: '11', 30000: '12', 100000: '13',
                            300000: '14', 1e6: '15'}
        self.filtermode_map = {'bypass': '0', 'lowpass': '1', 'lowpassX2': '2',
                               'highpass': '3', 'highpassX2': '4',
                               'bandpass': '5'}
        self.dynamic_reserve_map = {'low_noise': '0', 'high_DR': '1',
                                    'calibration': '2'}
        self.coupling_map = {'ground': '0', 'DC': '1', 'AC': '2'}
        self.source_map = {'A': '0', 'A-B': '1', 'B': '2'}

        self.add_parameter(name='gain',
                           set_cmd='GAIN {}',
                           val_mapping=self.gain_map)
        self.add_parameter(name='filter_mode',
                           set_cmd='FLTM {}',
                           val_mapping=self.filtermode_map)
        self.add_parameter(name='HPfilt_freq',
                           set_cmd='HFRQ{}',
                           val_mapping=self.highpass_map)
        self.add_parameter(name='LPfilt_freq',
                           set_cmd='LFRQ {}',
                           val_mapping=self.lowpass_map)
        self.add_parameter('invert',
                           set_cmd='INVRT {}',
                           set_parser=int,
                           vals=vals.Enum(0, 1))
        self.add_parameter('dynamic_reserve',
                           set_cmd='DYNR {}',
                           val_mapping=self.dynamic_reserve_map)
        self.add_parameter('coupling',
                           set_cmd='CPLG{}',
                           val_mapping=self.coupling_map)
        self.add_parameter('source',
                           set_cmd='SRCE {}',
                           val_mapping=self.source_map)

        self.write('LISN 3')
