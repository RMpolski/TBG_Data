#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan 24 07:59:32 2018
Integrating an already-developed QDInstrument script
@author: robertpolski
"""

import win32com.client
import pythoncom

import numpy as np
from typing import Union
import qcodes as qc
from qcodes import Instrument
import qcodes.utils.validators as vals
import time


class QDInstrument:
    """ The instrument class that calls on the PPMS through MultiVu. Don't
    use these commands for QCoDeS unless you want the error codes and
    status codes and such.

    It has the
    following functions:
        set_temperature(temp, rate, mode): returns error code.
                Mode 0 is fast settle.
                Mode 1 is No Overshoot
        get_temperature(): returns error code, temp, status
        set_field(field, rate, approach, mode): returns error.
                Approach 0 is linear,
                Approach 1 is No Overshoot
                Approach 2 is Oscillate
                Mode 0 works. Not sure if other modes do anything
        get_field(): returns error, field, status
            Status 0: Magnet Unknown (just still needs to be initialized
                                to some value)
            1: Stable Persistent (This magnet doesn't
                                    have a persistent function)
            2: Warming Switch (not applicable)
            3: Cooling Switch (not applicable)
            4: Stable Driven (This is the stable function for this magnet)
            5: Iterating (means it's almost there)
            6: Charging (means it's ramping)
            7: Discharging (also ramping)
            8: Current Error
            15: Magnet Failure
        set_chamber(code): Returns error. Not sure how the codes work here.
        get_chamber(): returns error, status
            Status 0: undefined
            1: Purged
            2: ?
            3: Vented
            4: Purging
            5: ?
            6: Pre-HiVac
            7: HiVac
            8: pumping (from pump continuous)
            9: Flooding (venting)
        """
    def __init__(self, instrument_type):
        instrument_type = instrument_type.upper()
        if instrument_type == 'DYNACOOL':
            self._class_id = 'QD.MULTIVU.DYNACOOL.1'
        elif instrument_type == 'PPMS':
            self._class_id = 'QD.MULTIVU.PPMS.1'
        elif instrument_type == 'VERSALAB':
            self._class_id = 'QD.MULTIVU.VERSALAB.1'
        elif instrument_type == 'MPMS3':
            self._class_id = 'QD.MULTIVU.MPMS3.1'
        else:
            raise Exception('Unrecognized instrument type: ' +
                            '{0}'.format(instrument_type))
        self._mvu = win32com.client.Dispatch(self._class_id)

    def set_temperature(self, temperature, rate, mode):
        """Sets temperature and returns MultiVu error code.
        Mode 0 is Fast Settle
        Mode 1 is No Overshoot"""
        err = self._mvu.SetTemperature(temperature, rate, mode)
        return err

    def get_temperature(self):
        """Gets and returns temperature info as (MultiVu error, temperature, status)
        Status codes:
            0: Temperature Unknown
            1: Stable
            2: Tracking
            5: Near
            6: Chasing
            7: Filling
            10: Standby
            13: Disabled
            14: Impedance Not Function
            15: Temp Failure"""
        arg0 = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_R8,
                                       0.0)
        arg1 = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
        err = self._mvu.GetTemperature(arg0, arg1)
        # win32com reverses the arguments, so:
        return err, arg1.value, arg0.value

    def set_field(self, field, rate, approach, mode):
        """Sets field and returns MultiVu error code.
        Approach 0 is Linear
        Approach 1 is No Overshoot
        Approach 2 is Oscillate

        Mode 0 works. Not sure what mode means"""
        err = self._mvu.SetField(field, rate, approach, mode)
        return err

    def get_field(self):
        """Gets and returns field info as (MultiVu error, field, status)
        Status Codes:
            0: Magnet Unknown (just still needs to be initialized
                                to some value)
            1: Stable Persistent (This magnet doesn't
                                    have a persistent function)
            2: Warming Switch (not applicable)
            3: Cooling Switch (not applicable)
            4: Stable Driven (This is the stable function for this magnet)
            5: Iterating (means it's almost there)
            6: Charging (means it's ramping)
            7: Discharging (also ramping)
            8: Current Error
            15: Magnet Failure"""
        arg0 = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_R8,
                                       0.0)
        arg1 = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
        err = self._mvu.GetField(arg0, arg1)
        # win32com reverses the arguments, so:
        return err, arg1.value, arg0.value

    def set_chamber(self, code):
        """Sets chamber and returns MultiVu error code"""
        err = self._mvu.SetChamber(code)
        return err

    def get_chamber(self):
        """Gets chamber status and returns (MultiVu error, status)
        0: undefined
        1: Purged
        2: ?
        3: Vented
        4: Purging
        5: ?
        6: Pre-HiVac
        7: HiVac
        8: pumping (from pump continuous)
        9: Flooding (venting)"""
        arg0 = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
        err = self._mvu.GetChamber(arg0)
        return err, arg0.value


class QD(Instrument, QDInstrument):
    """
    The actual instrument class to be used by QCoDeS.
    Note: This uses mT units for magnetic field
    instead of Oersteds.
    """
    def __init__(self, name: str, instrument_type='DYNACOOL',
                 **kwargs):
        """ name: name to use internally in QCodes,
        instrument_type: passed to the previously made QDInstrument script"""
        QDInstrument.__init__(self, instrument_type)
        super().__init__(name, **kwargs)

        self.add_parameter('temperature',
                           label='Temperature',
                           unit='K',
                           get_cmd=self.temperature_get_cmd,
                           set_cmd=self.temperature_set_release,
                           vals=vals.Numbers(1.6, 400))
        self.add_parameter('temperature_set_stable',
                           label='Temperature',
                           unit='K',
                           get_cmd=self.temperature_get_cmd,
                           set_cmd=self.temperature_stable,
                           vals=vals.Numbers(1.6, 400))
        self.add_parameter('field',
                           label='Magnetic Field',
                           unit='mT',
                           get_cmd=self.field_get_cmd,
                           set_cmd=self.field_set_release,
                           vals=vals.Numbers(-9000, 9000))
        self.add_parameter('field_set_stable',
                           label='Magnetic Field', unit='mT',
                           get_cmd=self.field_get_cmd,
                           set_cmd=self.field_stable,
                           vals=vals.Numbers(-9000, 9000))

        self.field_rate = 15  # mT/s
        self.temperature_rate = 10  # K/min
        print('Note this uses mT units for getting and setting fields with' +
              ' field() and field_set_stable(). Just divide Oe by ' +
              '10 to get mT')

    def temperature_stable(self, temperature: Union[int, float],
                           slightlyfaster: bool=False):
        """ temperature:  in Kelvin.
        slightlyfaster=True just moves on when the temperature status
        is near instead of requiring it to be stable"""
        err_init, temp_init, status_init = self.get_temperature()
        temp_init = float(temp_init)
        self.set_temperature(temperature, self.temperature_rate, 0)
        waiting = True
        startwaittime = time.time()
        timeout = 60*(np.abs(temp_init-temperature)/self.temperature_rate)*2 +\
            240
        time.sleep(60*(np.abs(temp_init-temperature)/self.temperature_rate)+1)
        # in seconds
        while waiting:
            err, tval, status = self.get_temperature()
            if slightlyfaster:
                if status == 5:
                    break
            if status == 1:
                break
            else:
                if time.time() - startwaittime > timeout:
                    waiting = False
                    print('Temperature timeout')
            qc.Wait(0.5)
        return

    def temperature_set_release(self, temperature: Union[int, float]):
        """ set temperature in Kelvin and don't wait until stable """
        self.set_temperature(temperature, self.temperature_rate, 0)
        return

    def temperature_get_cmd(self):
        err, temp, status = self.get_temperature()
        return float(temp)

    def field_stable(self, field: Union[int, float]):
        """ field: magnetic field in milliTesla"""
        err_init, bval_init, status_init = self.get_field()
        bval_init = float(bval_init)/10  # convert from Oe to mT
        self.set_field(field*10, self.field_rate*10, 1, 0)  # convert to Oe
        waiting = True
        startwaittime = time.time()
        timeout = (np.abs(bval_init-field))/(self.field_rate)*3 + 120
        time.sleep((np.abs(bval_init-field))/(self.field_rate)+1)
        # in seconds
        while waiting:
            err, bval, status = self.get_field()
            if status == 4:
                break
            else:
                if time.time() - startwaittime > timeout:
                    waiting = False
                    print('Field timeout')
            time.sleep(0.25)
        return

    def field_set_release(self, field: Union[int, float]):
        """ field: magnetic field in milliTesla.
        Set and don't wait until stable """
        self.set_field(field*10, self.field_rate*10, 1, 0)  # convert to Oe

    def field_get_cmd(self):
        err, bval, status = self.get_field()
        return float(bval/10)  # convert from Oe
