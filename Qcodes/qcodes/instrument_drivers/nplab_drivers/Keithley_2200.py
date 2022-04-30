#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 5, 2018

Keithley_2200 voltage/current DC source driver
@author: robertpolski
"""


from qcodes import VisaInstrument
import qcodes.utils.validators as vals


class Keithley_2200(VisaInstrument):
    """For any of Keithley2200 DC voltage/current sources. Parameters are as
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

        self.add_parameter('voltage', set_cmd='VOLT {}',
                           get_cmd='FETC:VOLT?', unit='V', get_parser=float,
                           vals=vals.Numbers(0, 72))
        self.add_parameter('current', set_cmd='CURR:LEV {}',
                           get_cmd='FETC:CURR?', unit='A',
                           vals=vals.Numbers(0, 1.2))
        self.add_parameter('output', set_cmd='OUTP {}',
                           get_cmd='OUTP?', vals=vals.Ints(0, 1))
        self.add_parameter('volt_max', set_cmd='VOLT:RANG {}',
                           get_cmd='VOLT:RANG?', unit='V',
                           vals=vals.Numbers(1, 71))
        self.add_parameter('volt_protection', set_cmd='VOLT:PROT:STAT {}',
                           get_cmd='VOLT:PROT:STAT?', vals=vals.Ints(0, 1))

        self.add_function('reset', call_cmd='*RST')

        if reset:
            self.reset()

        self.connect_message()
