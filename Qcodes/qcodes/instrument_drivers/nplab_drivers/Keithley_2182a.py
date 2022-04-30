#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan 19 08:11:41 2018

Keithley_2182a attempt from scratch. Mostly derived from the
Keithley_2600_channels script. Some from Keithley_2000
@author: robertpolski
"""


import numpy as np
from functools import partial

from qcodes import VisaInstrument
import qcodes.utils.validators as vals


def parse_output_string(s):
    """ Used for mode parsing since Keithley 2812 adds an unnecessary :DC """
    s = s.strip('" ')
    if s[-3:] == ':DC':
        s = s[:-3]
    return s


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


class Keithley_2182a(VisaInstrument):
    """
    The Instrument driver for the Keithley 2182a nanovoltmeter
    """
    def __init__(self, name: str, address: str, reset: bool=False, **kwargs):
        """
        Args:
            name: Name to use internally in QCoDeS
            address: VISA ressource address
            reset: Set Keithley to defaults? True or False
        """
        super().__init__(name, address, terminator='\n', **kwargs)

        # The limits of the range function. There's a separate function for
        # autorange
        self.vranges = [[0.01, 0.1, 1., 10., 100.], [0.1, 1, 10]]  # not used
        self.tempranges = []  # not used at the moment
        self.trigreadstart = False

        self.add_parameter('mode',
                           get_cmd='SENS:FUNC?',
                           set_cmd='SENS:FUNC {}',
                           get_parser=parse_output_string,
                           vals=vals.Enum('VOLT', 'TEMP'))
        self.add_parameter('channel',
                           get_cmd='SENS:CHAN?',
                           set_cmd='SENS:CHAN {}',
                           vals=vals.Ints(0, 2))
        # TODO: Possibly connect range to _mode_range through an enum to
        # distinguish between temp and voltage modes.
        self.add_parameter('range',
                           unit='V',
                           get_cmd=partial(self._get_mode_param_chan, 'RANG'),
                           set_cmd=partial(self._set_mode_param_chan, 'RANG'),
                           get_parser=float,
                           set_parser=float,
                           vals=vals.Numbers(0, 120))
        self.add_parameter('auto_range',
                           get_cmd=partial(self._get_mode_param, 'RANG:AUTO'),
                           set_cmd=partial(self._set_mode_param, 'RANG:AUTO'),
                           get_parser=int,
                           set_parser=parse_output_bool,
                           vals=vals.Enum(*boolcheck))
# TODO: Change measure to get unit from the measurement type and measure temp
        self.add_parameter('measure',
                           label='Voltage',
                           get_cmd='SENS:DATA:FRES?',
                           get_parser=float,
                           vals=vals.Numbers(),
                           unit='V')
        self.add_parameter('trigread',
                           label='Voltage',
                           snapshot_get=False,
                           get_cmd=self._trigread_get,
                           get_parser=float,
                           unit='V')
        self.add_parameter('read',
                           label='Voltage',
                           get_cmd=':READ?',
                           get_parser=float,
                           snapshot_get=False,
                           unit='V')
        self.add_parameter('nplc',
                           get_cmd=partial(self._get_mode_param, 'NPLC',),
                           set_cmd=partial(self._set_mode_param, 'NPLC'),
                           get_parser=float,
                           set_parser=float,
                           vals=vals.Numbers(0.01, 60))
        self.add_parameter('line_sync',
                           get_cmd='SYST:LSYN?',
                           set_cmd='SYST:LSYN {}',
                           get_parser=int,
                           set_parser=parse_output_bool,
                           vals=vals.Enum(*boolcheck))
        self.add_parameter('front_autozero',
                           get_cmd='SYST:FAZ?',
                           set_cmd='SYST:FAZ {}',
                           get_parser=int,
                           set_parser=parse_output_bool,
                           vals=vals.Enum(*boolcheck))
        self.add_parameter('autozero',
                           get_cmd='SYST:AZER?',
                           set_cmd='SYST:AZER {}',
                           get_parser=int,
                           set_parser=parse_output_bool,
                           vals=vals.Enum(*boolcheck))
        self.add_parameter('temp_unit',
                           get_cmd='UNIT:TEMP?',
                           set_cmd='UNIT:TEMP {}',
                           get_parser=parse_output_string,
                           vals=vals.Enum('C', 'F', 'K'))
        self.add_parameter('display',
                           get_cmd='DISP:ENAB?',
                           set_cmd='DISP:ENAB {}',
                           get_parser=int,
                           set_parser=parse_output_bool,
                           vals=vals.Enum(*boolcheck))
        self.add_parameter('beeper',
                           get_cmd='SYST:BEEP?',
                           set_cmd='SYST:BEEP {}',
                           set_parser=parse_output_bool,
                           get_parser=int,
                           vals=vals.Enum(*boolcheck))
        self.add_parameter('dfilter',
                           get_cmd=partial(self._get_mode_param_chan, 'DFIL'),
                           set_cmd=partial(self._set_mode_param_chan, 'DFIL'),
                           get_parser=int,
                           set_parser=parse_output_bool,
                           vals=vals.Enum(*boolcheck))
        self.add_parameter('dfilter_count',
                           get_cmd=partial(self._get_mode_param_chan,
                                           'DFIL:COUN'),
                           set_cmd=partial(self._set_mode_param_chan,
                                           'DFIL:COUN'),
                           get_parser=int,
                           set_parser=int,
                           vals=vals.Ints(1, 100))
        self.add_parameter('dfilter_window',
                           get_cmd=partial(self._get_mode_param_chan,
                                           'DFIL:WIND'),
                           set_cmd=partial(self._set_mode_param_chan,
                                           'DFIL:WIND'),
                           get_parser=float,
                           set_parser=float,
                           vals=vals.Numbers(0.01, 10))
        self.add_parameter('dfilter_type',
                           get_cmd=partial(self._get_mode_param_chan,
                                           'DFIL:TCON'),
                           set_cmd=partial(self._set_mode_param_chan,
                                           'DFIL:TCON'),
                           vals=vals.Enum('MOV', 'REP'))

        self.add_function('reset', call_cmd='*RST')
        self.add_function('get_error', call_cmd='SYST:ERR?')

        if reset:
            self.reset()

        self.connect_message()

    def autocalibrate(self):
        """Initializes calibration, asks if you want to continue, and
        does low-level calibration. It's recommended if the
        temperature difference is above 1 deg C.
        Takes about 5 minutes if you continue"""
        self.write('CAL:UNPR:ACAL:INIT')
        prevtemp = parse_output_string(self.ask('CAL:UNPR:ACAL:TEMP?'))
        currtemp = parse_output_string(self.ask('SENS:TEMP:RTEM?'))

        answer = input('The last time ACAL was run,' +
                       'the temp was {} C\n'.format(prevtemp) +
                       'Now the temp is {} C\n'.format(currtemp) +
                       'Do you want to proceed with low-level calibration?' +
                       ' [y/n] ')
        b = (answer == 'y' and
             parse_output_string(self.mode()).lower() == 'volt')
        b = b and float(parse_output_string(self.range())) == 0.01
        if b:
            self.write('CAL:UNPR:ACAL:STEP2')
            self.write('CAL:UNPR:ACAL:DONE')
        elif answer == 'n':
            self.write('CAL:UNPR:ACAL:DONE')
        else:
            print('Must be in voltage mode, range 10mV')
            self.write('CAL:UNPR:ACAL:DONE')

    def _get_mode_param(self, parameter: str):
        """ Read the current Keithley mode and ask for a parameter """
        mode = parse_output_string(self.mode())
        cmd = 'SENS:{}:{}?'.format(mode, parameter)

        return self.ask(cmd).strip('" ')

    def _get_mode_param_chan(self, parameter: str, chan=None):
        """ Read the current Keithley mode and ask for a parameter """
        mode = parse_output_string(self.mode())
        if chan is None:
            chan = parse_output_string(self.channel())
        cstring = 'CHAN{}'.format(chan)
        cmd = 'SENS:{}:{}:{}?'.format(mode, cstring, parameter)

        return self.ask(cmd).strip('" ')

    def _set_mode_param(self, parameter: str, value):
        """ Read the current Keithley mode and set a parameter """
        if isinstance(value, bool):
            value = int(value)

        mode = parse_output_string(self.mode())
        cmd = 'SENS:{}:{} {}'.format(mode, parameter, value)
        self.write(cmd)

    def _set_mode_param_chan(self, parameter: str, value, chan=None):
        """ Read the current Keithley mode and set a parameter """
        if isinstance(value, bool):
            value = int(value)

        mode = parse_output_string(self.mode())
        if chan is None:
            chan = parse_output_string(self.channel())
        cstring = 'CHAN{}'.format(chan)
        cmd = 'SENS:{}:{}:{} {}'.format(mode, cstring, parameter, value)
        self.write(cmd)

    def _mode_range(self):
        """ Returns the different range settings for a given mode """
        if self.channel() == 0:
            raise ValueError('Needs to be set on channel 1 or 2')
        if self.mode() == 'VOLT':
            return self.vranges[self.channel()-1]
        elif self.mode() == 'TEMP':
            return self.tempranges[self.channel()-1]
        else:
            raise ValueError('Not VOLT or TEMP in _mode_range')

    def _digit_range(self):
        """ Feeds number of digit min and max to Enum validator"""
        if self.mode() == 'VOLT':
            return np.arange(3.5, 8, 0.5)
        elif self.mode() == 'TEMP':
            return np.arange(4, 8, 1)
        else:
            raise ValueError('Must be VOLT or TEMP in _digit_range')

    def _get_unit(self):
        """ Returns the unit for the current measurement mode"""
        if self.mode() == 'VOLT':
            return 'V'
        elif self.mode() == 'TEMP':
            return self.ask('UNIT:TEMP?')
        else:
            raise ValueError('Mode must be VOLT or TEMP')

    def _trigread_get(self):
        """ Returns the result of a triggered acquisition (starts trigger
         sequence if not initiated already)"""
        if self.trigreadstart is False:
            self.write('TRIG:SOUR BUS')
            self.write('INIT:CONT OFF')
            self.write('INIT')

        self.write('*TRG')
        return self.ask('SENS:DATA:FRES?')

    def trigabort(self):
        """ Aborts a triggered read sequence (see _trigread_get() function) """
        if self.trigreadstart is True or self.ask('TRIG:SOUR?') == 'BUS':
            self.write('ABORT')
            self.write('TRIG:SOUR IMM')
            self.write('INIT:CONT ON')
            self.trigreadstart = False
        else:
            print('Not in a triggered measurement state')
