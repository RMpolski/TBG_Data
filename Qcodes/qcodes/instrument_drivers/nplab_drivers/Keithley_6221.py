#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan 19 13:32:00 2018

@author: robertpolski
"""

import numpy as np
from typing import Union

from qcodes import VisaInstrument
from qcodes.instrument.parameter import ArrayParameter, MultiParameter
import qcodes.utils.validators as vals
import time
from functools import partial

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


class SweepParameter(ArrayParameter):
    """ Defines the parameters used for delta mode and delta differential
    conductance mode.

    get_cmd: must be a function that outputs an array with the dimensions
             given when setting up the parameter
    """
    def __init__(self, name: str, get_cmd=None, **kwargs):
        super().__init__(name, **kwargs)
        if get_cmd is None:
            print('Needs get_cmd')
        else:
            self.get_cmd = get_cmd

    def get_raw(self):
        # return the parameter by calling get_cmd
        return self.get_cmd()


class SweepTimeParameter(MultiParameter):
    """ Defines the parameters used for delta mode and delta differential
    conductance mode, now with an added time array.

    get_cmd: must be a function that outputs an array with the dimensions
             given when setting up the parameter

    This parameter is meant for when multiple types of data are collected from
    the buffer, such as voltage and time
    """
    def __init__(self, name: str, get_cmd=None, **kwargs):
        super().__init__(name, **kwargs)
        if get_cmd is None:
            print('Needs get_cmd')
        else:
            self.get_cmd = get_cmd

    def get_raw(self):
        # return the parameter by calling get_cmd
        return self.get_cmd()


class Keithley_6221(VisaInstrument):
    """
    Instrument Driver for Keithley 6221 current source
    """
    def __init__(self, name: str, address: str, reset: bool=False, **kwargs):
        """
        Args:
            name: Name to use internally in QCoDeS
            address: VISA ressource address
            reset: Set Keithley to defaults? True or False
        """
        super().__init__(name, address, terminator='\n', **kwargs)

        self._ac_init = False
        self._ac_ampl = False
        self._ac_freq = False

        self.add_parameter('current',
                           label='Current',
                           get_cmd='SOUR:CURR?',
                           set_cmd='SOUR:CURR {}',
                           get_parser=float,
                           unit='A',
                           vals=vals.Numbers())
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

        # Related to attached 2182(a) nanovoltmeter
        self.add_parameter('unit',
                           label='diff conductance unit',
                           get_cmd='UNIT?',
                           set_cmd='UNIT {}',
                           initial_value='OHMS',
                           get_parser=str,
                           vals=vals.Enum('V', 'ohms', 'OHMS', 'S', 'SIEM',
                                          'siem', 'siemens', 'SIEMENS'))
        self.add_parameter('k2182_present',
                           get_cmd='SOUR:DELT:NVPR?',
                           get_parser=int)
        self.add_parameter('delta_arm',
                           get_cmd='SOUR:DELT:ARM?',
                           get_parser=int)
        self.add_parameter('diff_arm',
                           get_cmd='SOUR:DCON:ARM?',
                           get_parser=int)
        self.add_parameter('delta_IV_sweep',  # STILL A WORK IN PROGRESS
                           snapshot_get=False,
                           get_cmd=self.delta_IV_sweep_get,
                           set_cmd=self.delta_IV_sweep_set,
                           get_parser=float,
                           set_parser=float)

        # These are only useable if you have connected to the Keithley 2182
        # Through an RS-232 port. Make sure to check the settings on the 2182
        # at set to GPIB: off, RS-232 on
        self.add_parameter('k2_measure',
                           snapshot_get=False,
                           get_cmd=partial(self.k2_read_cmd,
                                           'SENS:DATA:FRES?'),
                           get_parser=float,
                           unit='V')

        self.add_parameter('k2_range',
                           snapshot_get=False,
                           set_cmd='SYST:COMM:SER:SEND "VOLT:RANG {}"',
                           get_cmd=partial(self.k2_read_cmd, 'VOLT:RANG?'),
                           set_parser=float,
                           get_parser=float,
                           vals=vals.Numbers(0, 120))
        self.add_parameter('k2_nplc',
                           snapshot_get=False,
                           set_cmd='SYST:COMM:SER:SEND "VOLT:NPLC {}"',
                           get_cmd=partial(self.k2_read_cmd, 'VOLT:NPLC?'),
                           set_parser=float,
                           get_parser=float,
                           vals=vals.Numbers(0.01, 60))
        self.add_parameter('k2_line_sync',
                           snapshot_get=False,
                           set_cmd='SYST:COMM:SER:SEND "SYST:LSYN {}"',
                           get_cmd=partial(self.k2_read_cmd, 'SYST:LSYN?'),
                           set_parser=parse_output_bool,
                           get_parser=int,
                           vals=vals.Enum(*boolcheck))
        self.add_parameter('k2_front_autozero',
                           snapshot_get=False,
                           set_cmd='SYST:COMM:SER:SEND "SYST:FAZ {}"',
                           get_cmd=partial(self.k2_read_cmd, 'SYST:FAZ?'),
                           set_parser=parse_output_bool,
                           get_parser=int,
                           vals=vals.Enum(*boolcheck))
        self.add_parameter('k2_autozero',
                           snapshot_get=False,
                           set_cmd='SYST:COMM:SER:SEND "SYST:AZER {}"',
                           get_cmd=partial(self.k2_read_cmd, 'SYST:AZER?'),
                           set_parser=parse_output_bool,
                           get_parser=int,
                           vals=vals.Enum(*boolcheck))
        self.add_parameter('k2_dfilter_count',
                           snapshot_get=False,
                           get_cmd=partial(self.k2_read_cmd,
                                           'SENS:VOLT:DFIL:COUN?'),
                           set_cmd='SYST:COMM:SER:SEND "SENS:VOLT:DFIL:COUN {}"',
                           get_parser=int,
                           set_parser=int,
                           vals=vals.Ints(1, 100))
        self.add_parameter('k2_dfilter_window',
                           snapshot_get=False,
                           get_cmd=partial(self.k2_read_cmd,
                                           'SENS:VOLT:DFIL:WIND?'),
                           set_cmd='SYST:COMM:SER:SEND "SENS:VOLT:DFIL:WIND {}"',
                           get_parser=float,
                           set_parser=float,
                           vals=vals.Numbers(0.01, 10))
        self.add_parameter('k2_dfilter_type',
                           snapshot_get=False,
                           get_cmd=partial(self.k2_read_cmd,
                                           'SENS:VOLT:DFIL:TCON?'),
                           set_cmd='SYST:COMM:SER:SEND "SENS:VOLT:DFIL:TCON {}"',
                           vals=vals.Enum('MOV', 'REP'))

        self.add_function('abort_arm', call_cmd='SOUR:SWE:ABOR')
        self.add_function('reset', call_cmd='*RST')
        # TODO: Getting error messages doesn't work
        self.add_function('get_error', call_cmd='SYST:ERR?')

        if reset:
            self.reset()

        self.connect_message()

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

    def delta_trigger_return(self):
        """ Triggers, waits, parses, and returns the results of a delta sweep.

        Don't use this after a delta_diff_setup or const_delta_setup.
        Use instead deltadcon or constdelta instead

        The array is of shape (points, 1) if _delta_time_meas=False or
        (points, 2) if True. If True, the first column is the
        time between the initial data point and the given data point, and
        the second column is the value"""
        if self.delta_arm() != 1 and self.diff_arm() != 1:
            print('Need to run a delta or differential conductance setup')
            return

        self.write('INIT:IMM')

        time.sleep(self._delta_delay*self._delta_points)
        # reset the timeout to account for possible extra time
        self._old_timeout = self.timeout()
        if self._delta_points/2 > 5:
            self.timeout(self._delta_points/2)
        else:
            self.timeout(5)
        count = 0
        while not int(self.ask('*OPC?')):  # Wait until done. Try if this works
            time.sleep(1)
            if count > 5:
                print('Delta function did not appear to finish')
                break
            count += 1

        self.timeout(self._old_timeout)

        _floatdata = np.fromstring(self.ask('TRAC:DATA?'), sep=',')
        _vals = np.zeros(int(len(_floatdata)/2))

        if self._delta_time_meas:
            _times = np.zeros(int(len(_floatdata)/2))
            for i in range(len(_floatdata)):
                if np.mod(i, 2) == 0:
                    _vals[int(i/2)] = _floatdata[i]
                else:
                    _times[int((i-1)/2)] = _floatdata[i]
            if len(_vals) == self._delta_points + 1:
                _vals = _vals[1:]
            if len(_times) == self._delta_points + 1:
                _times = _times[1:]
            return (_vals, _times)
        else:
            for i in range(len(_floatdata)):
                if np.mod(i, 2) == 0:
                    _vals[int(i/2)] = _floatdata[i]
            if len(_vals) == self._delta_points + 1:
                _vals = _vals[1:]
            return _vals

    def const_delta_setup(self, high: Union[int, float], points: int, delay=0,
                          low: Union[int, float, None]=None, cab: bool=False,
                          timemeas: bool=False):
        """ Sets up (doesn't run yet) the 6221 and 2182(a) into Delta mode
        in which the 6221 current source starts with a current at high (Amps)
        then to low (A) and back, and so on for "points" number of data
        points. If no low is given, it's set to the negative of high. Delay
        is the amount of time (in seconds) to wait before measuring after
        flipping from high to low or vice versa. The argument cab is whether
        or not to abort when compliance is entered.

        After setting up with this command, use constdelta() to return a
        measurement

        high: upper current
        points: number of data points returned
        low: (optional) lower current. If None, low=-high
        cab: True aborts if compliance is crossed. False will just keep running
                at the compliance level and possibly make some nasty
                beeping sounds
        timemeas: False - return value column,
                  True - return time and value columns

        The function checks if the 2182 is connected over the RS-232 port
        and leaves the 6221 in an armed state.

        Lastly, the function creates a gettable array parameter for the setup
        called constdelta, with setpoints as the mean current. The timemeas
        argument determines whether or not the parameter will include time
        in one column or not.
        Note: you have to run the abort_arm() function after you're done
        running sweeps to unarm."""

        if self.delta_arm() == 1:
            print('Delta mode is already armed. Need to abort or run.')
            return
        elif self.diff_arm() == 1:
            print('Differential conductance is armed. Need to abort first.')
            return

        if self.k2182_present() != 1:
            print('2182 is not connected properly through the RS-232 port')
            return

        self.write('SOUR:DELT:HIGH {}'.format(high))

        if low is not None:
            self.write('SOUR:DELT:LOW {}'.format(low))
        else:
            low = -high

        if cab:
            self.write('SOUR:DELT:CAB 1')
        else:
            self.write('SOUR:DELT:CAB 0')

        self.write('SOUR:DELT:DEL {}'.format(delay))
        self.write('SOUR:DELT:COUN {}'.format(points))
        self.write('TRAC:POIN {}'.format(points))
        self.write('SOUR:DELT:ARM')

        self.sweep_current = np.ones(points)*(high-low)/2
        self._delta_delay = delay
        self._delta_points = points

        if 'constdelta' in self.parameters:
            del self.parameters['constdelta']

        if timemeas:  # untested timemeas
            countarray = np.linspace(1, len(self.sweep_current),
                                     len(self.sweep_current))
            self.add_parameter('constdelta', names=('deltaV', 'time'),
                               parameter_class=SweepTimeParameter,
                               labels=('Delta Mode Volgage', 'Time'),
                               shapes=((self._delta_points,),
                                       (self._delta_points,)),
                               units=('V', 's'),
                               setpoints=((tuple(self.sweep_current),),
                                          (tuple(countarray),)),
                               setpoint_names=(('current',), ('number',)),
                               setpoint_labels=(('Current',), ('Number',)),
                               setpoint_units=(('A',), ('',)),
                               get_cmd=self.delta_trigger_return)
            self._delta_time_meas = True
        else:
            self.add_parameter('constdelta', parameter_class=SweepParameter,
                               label='Voltage',
                               shape=(points,),
                               unit='V',
                               setpoints=(tuple(self.sweep_current),),
                               setpoint_names=('Current',),
                               setpoint_units=('A',),
                               get_cmd=self.delta_trigger_return)
            self._delta_time_meas = False

    def delta_diff_setup(self, start: Union[int, float],
                         stop: Union[int, float], step: Union[int, float]=None,
                         num: Union[int, float]=None,
                         delta: Union[int, float]=1e-6,
                         delay=0, cab: bool=False, timemeas: bool=False):
        """ Sets up (doesn't run yet) the 6221 and 2182(a) into Delta
        differential conductance mode. The unit can be configured with .unit()
        to 'OHMS', 'S', 'V'.
        The 6221 current source alternates and sweeps from start to end, with
        step between the two.

        To run after setup and return the array, use deltadcon

        start: starting current (A) for sweep
        stop: end current (A) for sweep
        step: stepsize (A)
        delta: amount the delta mode jumps above and below the step value
                for averaging
        delay: amount of time (in seconds) to wait before measuring after
                changing sweep values.
        cab: True aborts if compliance is crossed. False will just keep running
                at the compliance level and possibly make some nasty
                beeping sounds
        timemeas: False - returns single values column,
                  True - returns time column and values column

        The function checks if the 2182 is connected over the RS-232 port
        and leaves the 6221 in an armed state.

        Lastly, the function creates a gettable array parameter for the setup
        called deltadcon, with setpoints as the mean current. The timemeas
        argument determines whether or not the parameter will include time
        in one column or not.
        Note: you have to run the abort_arm() function after you're done
        running sweeps to unarm."""

        if self.delta_arm() == 1:
            print('Delta mode is armed. Need to abort first.')
            return
        elif self.diff_arm() == 1:
            print('Differential conductance mode is already armed. ' +
                  'Abort or run.')
            return

        if self.k2182_present() != 1:
            print('2182 is not connected properly through the RS-232 port')
            return

        self._dcon_unit = self.unit().lower()

        self.write('SOUR:DCON:STAR {}'.format(start))
        self.write('SOUR:DCON:STOP {}'.format(stop))

        if step is not None:
            self.write('SOUR:DCON:STEP {}'.format(step))
            self._delta_points = int(round(np.abs((stop-start)/step)+1))
        elif step is None and num is not None:
            stepsize = (stop-start)/(num-1)
            self.write('SOUR:DCON:STEP {}'.format(stepsize))
            self._delta_points = num
        elif (step is None and num is None) or (step is not None and num is not None):
            print('Need to provide step or num')
            return
        self.write('SOUR:DCON:DELT {}'.format(delta))
        self.write('SOUR:DCON:DEL {}'.format(delay))

        if cab:
            self.write('SOUR:DCON:CAB ON')
        else:
            self.write('SOUR:DCON:CAB OFF')


        # TODO: Possibly provide checker to see if step divides stop-step

        self.write('TRAC:POIN {}'.format(self._delta_points))
        self.write('SOUR:DCON:ARM')

        self.sweep_current = np.linspace(start, stop, self._delta_points)
        self._delta_delay = delay

        if 'deltadcon' in self.parameters:
            del self.parameters['deltadcon']

        if timemeas:  # untested timemeas
            countarray = np.linspace(1, len(self.sweep_current),
                                     len(self.sweep_current))
            self.add_parameter('deltadcon', names=('dcon', 'time'),
                               parameter_class=SweepTimeParameter,
                               labels=('dVdI/dIdV', 'time'),
                               shapes=((self._delta_points,),
                                       (self._delta_points,)),
                               units=(self._dcon_unit, 's'),
                               setpoints=((tuple(self.sweep_current),),
                                          (tuple(countarray),)),
                               setpoint_names=(('current',), ('number',)),
                               setpoint_labels=(('Current',), ('Number',)),
                               setpoint_units=(('A',), ('',)),
                               get_cmd=self.delta_trigger_return)
            self._delta_time_meas = True
        else:
            self.add_parameter('deltadcon', parameter_class=SweepParameter,
                               label='dVdI/dIdV',
                               shape=(self._delta_points,),
                               unit=self._dcon_unit,
                               setpoints=(tuple(self.sweep_current),),
                               setpoint_names=('Current',),
                               setpoint_units=('A',),
                               get_cmd=self.delta_trigger_return)
            self._delta_time_meas = False

    def delta_IV_sweep_setup(self, delay=0.5, ptsavg=1, cab=False):
        """ Run this before any delta_IV_sweep_set or _get. It configures the
        internal variables that control the delay, amount of points to average,
        and whether or not the sweep should abort when the compliance level is
        crossed.

        delay: the delta delay between when the current value is set and when
                the 2182a measures.
        ptsavg: If 1, delta mode goes high->low. If 2, it goes
                high->low->high, and so on. One data point is taken
                at each point and then averaged at the end.
        cab: True aborts if compliance is crossed. False will just keep running
                at the compliance level and possibly make some nasty
                beeping sounds"""

        if ptsavg < 1:
            print('ptsavg must be greater than 1')

        self._delta_delay = delay
        self._delta_cab = False
        self._sweepsetup = True
        self._deltaptsavg = int(ptsavg)

    def delta_IV_sweep_set(self, high):
        """This arms the delta_IV_sweep and can be run in qcodes like any other
        set command with one parameter to set.
        high: the current amplitude to set for the delta mode run. The low
        value of the delta mode measurement will automatically be -high."""

        if self.delta_arm() == 1:
            print('Delta mode is armed. Need to abort first.')
            return
        elif self.diff_arm() == 1:
            print('Differential conductance is armed. Need to abort first.')
            return
        elif self._sweepsetup is not True:
            print('Run delta_IV_sweep_setup first')

        if self.k2182_present() != 1:
            print('2182 is not connected properly through the RS-232 port')
            return

        self.write('SOUR:DELT:HIGH {}'.format(high))
        self.write('SOUR:DELT:LOW {}'.format(-high))

        if self._delta_cab:
            self.write('SOUR:DELT:CAB 1')
        else:
            self.write('SOUR:DELT:CAB 0')

        self.write('SOUR:DELT:DEL {}'.format(self._delta_delay))
        self.write('SOUR:DELT:COUN {}'.format(self._deltaptsavg+1))
        self.write('TRAC:POIN {}'.format(self._deltaptsavg+1))
        self.write('SOUR:DELT:ARM')

    def delta_IV_sweep_get(self):
        """A simple get command that can be used with qcodes for getting the
        results after running delta_IV_sweep_setup at the beginning and
        using delta_IV_sweep_set for each sweep value."""

        if self.delta_arm() == 0:
            print('Run delta_IV_sweep_set first')
            return
        self.write('INIT:IMM')

        self._old_timeout = self.timeout()
        if self._deltaptsavg > 4:
            self.timeout((self._deltaptsavg+2)*self._delta_delay + 2)
        else:
            self.timeout((self._deltaptsavg+2)*self._delta_delay + 5)
        count = 0
        while not int(self.ask('*OPC?')):  # Wait until done. Try if this works
            time.sleep(.1)
            if count > 50:
                print('Delta function did not appear to finish')
                break
            count += 1

        _floatdata = np.fromstring(self.ask('TRAC:DATA?'), sep=',')
        self.abort_arm()
        _vals = np.zeros(self._deltaptsavg)
        for i in range(len(_floatdata)):
                if np.mod(i, 2) == 0 and i > 0:
                    _vals[int((i-2)/2)] = _floatdata[i]
        return np.average(_vals)

    # Now a function for reading from the k2182 when plugged into the 6221
    # through an RS-232 port

    def k2_read_cmd(self, cmd):
        """ pyvisa seems to requires two read
        commands to get the value of something when it's requested from the
        2182. It seems that first, the ask command returns a newline for the
        first command and then the value afterward"""

        val = self.ask('SYST:COMM:SER:SEND "{}"\nSYST:COMM:SER:ENT?'.format(cmd))
        # nothing = self.visa_handle.read()
        return val
