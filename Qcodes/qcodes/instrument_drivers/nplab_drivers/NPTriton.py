""" Copied from the triton model in the Oxford instrument folder, with
some variations and restrictions specifically applicable to our Triton.

This has an extra magnetic field sweep protection that disallows sweeping when
the temperature is too high"""

import configparser
import re
from functools import partial
import logging
from traceback import format_exc

from qcodes import IPInstrument
from qcodes.utils.validators import Enum, Ints, Numbers

from time import sleep
import numpy as np


def parse_outp_bool(value):
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


def parse_inp_bool(value):
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


boolcheck = (0, 1, 'on', 'off', 'ON', 'OFF', False, True)


class Triton(IPInstrument):
    r"""
    Triton Driver

    Args:
        address: IP or host address for the ethernet connection
        port: the connection port number

        TODO:
        fetch registry directly from fridge-computer
    """

    def __init__(self, name, address, port, timeout=20, **kwargs):
        super().__init__(name, address=address, port=port,
                         terminator='\r\n', timeout=timeout, **kwargs)

        self._heater_range_auto = False
        self._heater_range_temp = [0.03, 0.1, 0.3, 1, 12, 40]
        self._heater_range_curr = [0.316, 1, 3.16, 10, 31.6, 100]
        self._control_channel = 5
        self._first_magnet_use = False

        self.add_parameter(name='time',
                           label='System Time',
                           get_cmd='READ:SYS:TIME',
                           get_parser=self._parse_time)

        self.add_parameter(name='action',
                           label='Current action',
                           get_cmd='READ:SYS:DR:ACTN',
                           get_parser=self._parse_action)

        self.add_parameter(name='status',
                           label='Status',
                           get_cmd='READ:SYS:DR:STATUS',
                           get_parser=self._parse_status)

        self.add_parameter(name='pid_control_channel',
                           label='PID control channel',
                           get_cmd=self._get_control_channel,
                           set_cmd=self._set_control_channel,
                           vals=Ints(1, 16))

        self.add_parameter(name='pid_mode',
                           label='PID Mode',
                           get_cmd=partial(self._get_control_param, 'MODE'),
                           get_parser=parse_outp_bool,
                           set_cmd=partial(self._set_control_param, 'MODE'),
                           set_parser=parse_inp_bool,
                           vals=Enum(*boolcheck))

        self.add_parameter(name='pid_ramp',
                           label='PID ramp enabled',
                           get_cmd=partial(self._get_control_param,
                                           'RAMP:ENAB'),
                           get_parser=parse_outp_bool,
                           set_cmd=partial(self._set_control_param,
                                           'RAMP:ENAB'),
                           set_parser=parse_inp_bool,
                           vals=Enum(*boolcheck))

        self.add_parameter(name='pid_setpoint',
                           label='PID temperature setpoint',
                           unit='K',
                           get_cmd=partial(self._get_control_param, 'TSET'),
                           set_cmd=partial(self._set_control_param, 'TSET'))

        self.add_parameter(name='pid_rate',
                           label='PID ramp rate',
                           unit='K/min',
                           get_cmd=partial(self._get_control_param,
                                           'RAMP:RATE'),
                           set_cmd=partial(self._set_control_param,
                                           'RAMP:RATE'))

        self.add_parameter(name='pid_range',
                           label='PID heater range',
                           # TODO: The units in the software are mA, how to
                           # do this correctly?
                           unit='mA',
                           get_cmd=partial(self._get_control_param, 'RANGE'),
                           set_cmd=partial(self._set_control_param, 'RANGE'),
                           vals=Enum(*self._heater_range_curr))

        self.add_parameter(name='magnet_status',
                           label='Magnet status',
                           get_cmd=partial(self._get_control_B_param, 'ACTN'))

        self.add_parameter(name='magnet_sweeprate',
                           label='Magnet sweep rate',
                           unit='T/min',
                           get_cmd=partial(
                               self._get_control_B_param, 'RVST:RATE'),
                           set_cmd=partial(self._set_control_magnet_sweeprate_param))

        self.add_parameter(name='magnet_sweeprate_insta',
                           label='Instantaneous magnet sweep rate',
                           unit='T/min',
                           get_cmd=partial(self._get_control_B_param, 'RFST'))

        self.add_parameter(name='magnet_swh',
                           lable='Magnet persistent switch heater',
                           set_cmd=self._set_swh,
                           get_cmd='READ:SYS:VRM:SWHT',
                           get_parser=self._parse_swh,
                           vals=Enum(*boolcheck))

        self.add_parameter(name='magnet_POC',
                           label='Persistent after completing sweep?',
                           set_cmd='SET:SYS:VRM:POC:{}',
                           set_parser=parse_inp_bool,
                           get_cmd='READ:SYS:VRM:POC',
                           get_parser=self._parse_state,
                           vals=Enum(*boolcheck))

        self.add_parameter(name='B',
                           label='Magnetic field',
                           unit='T',
                           get_cmd=partial(self._get_control_B_param, 'VECT'))

        # self.add_parameter(name='Bx',
        #                    label='Magnetic field x-component',
        #                    unit='T',
        #                    get_cmd=partial(
        #                        self._get_control_Bcomp_param, 'VECTBx'),
        #                    set_cmd=partial(self._set_control_Bx_param))
        #
        # self.add_parameter(name='By',
        #                    label='Magnetic field y-component',
        #                    unit='T',
        #                    get_cmd=partial(
        #                        self._get_control_Bcomp_param, 'VECTBy'),
        #                    set_cmd=partial(self._set_control_By_param))

        self.add_parameter(name='field',
                           label='B',
                           unit='T',
                           get_cmd=self._get_field,
                           set_cmd=partial(self._set_field_return))

        self.add_parameter(name='field_set_stable',
                           label='B',
                           unit='T',
                           get_cmd=self._get_field,
                           set_cmd=partial(self._set_field_stable))

        self.add_parameter(name='magnet_sweep_time',
                           label='Magnet sweep time',
                           unit='T/min',
                           get_cmd=partial(self._get_control_B_param, 'RVST:TIME'))

        self.add_parameter(name='MC_heater',
                           label='Mixing chamber heater power',
                           unit='uW',
                           get_cmd='READ:DEV:H1:HTR:SIG:POWR',
                           set_cmd='SET:DEV:H1:HTR:SIG:POWR:{}',
                           get_parser=self._parse_htr,
                           set_parser=float,
                           vals=Numbers(0, 300000))

        self.add_parameter(name='still_heater',
                           label='Still heater power',
                           unit='uW',
                           get_cmd='READ:DEV:H2:HTR:SIG:POWR',
                           set_cmd='SET:DEV:H2:HTR:SIG:POWR:{}',
                           get_parser=self._parse_htr,
                           set_parser=float,
                           vals=Numbers(0, 300000))

        self.add_parameter(name='turbo_speed',
                           unit='Hz',
                           get_cmd='READ:DEV:TURB1:PUMP:SIG:SPD',
                           get_parser=self._parse_pump_speed)

        self.chan_alias = {'MC': 'T8', 'MC_cernox': 'T5', 'still': 'T3',
                           'cold_plate': 'T4', 'magnet': 'T13', 'PT2h': 'T1',
                           'PT2p': 'T2', 'PT1h': 'T6', 'PT1p': 'T7'}
        self._get_named_temp_channels()
        self._get_temp_channels()
        self._get_pressure_channels()
        self._get_valve_channels()
        self._get_pump_channels()

        self.connect_message()

    # def set_B(self, x, y, z, s):
    #     if 0 < s <= 0.205:
    #         self.write('SET:SYS:VRM:COO:CART:RVST:MODE:RATE:RATE:' + str(s) +
    #                    ':VSET:[' + str(x) + ' ' + str(y) + ' ' + str(z) + ']\r\n')
    #         self.write('SET:SYS:VRM:ACTN:RTOS\r\n')
    #         t_wait = self.magnet_sweep_time() * 60 + 10
    #         print('Please wait ' + str(t_wait) +
    #               ' seconds for the field sweep...')
    #         sleep(t_wait)
    #     else:
    #         print('Warning: set magnet sweep rate in range (0 , 0.205] T/min')

    def read_valves(self):
        for i in range(1, 10):
            print('V{}:  {}'.format(i, getattr(self, 'V%d' % i)()))

    def read_pumps(self):
        print('Turbo: {},  speed: {} Hz'.format(self.turbo(), self.turbo_speed()))
        print('KNF: {}'.format(self.knf()))
        print('Forepump: {}'.format(self.forepump()))

    def read_temps(self):
        for i in self.chan_alias:
            stat = 'off'
            if getattr(self, i+'_temp_enable')() == 0:
                stat = 'off'
            elif getattr(self, i+'_temp_enable')() == 1:
                stat = 'on'
            else:
                print('Temp reading status not determined')
            print('{} - {}:  {} K'.format(i, stat, getattr(self, self.chan_alias[i])()))

    def read_pressures(self):
        for i in range(1,6):
            print('P{}:  {}'.format(i, getattr(self, 'P'+str(i))()))

        print('POVC:  {}'.format(getattr(self, 'POVC')()))

    def tempdisable_excMC_magnet(self):
        for i in self.chan_alias:
            if i not in ('MC', 'magnet'):
                getattr(self, i + '_temp_enable')('off')

    def tempdisable_excMC(self):
        for i in self.chan_alias:
            if i != 'MC':
                getattr(self, i + '_temp_enable')('off')

    def alltempsenable(self):
        for i in self.chan_alias:
            getattr(self, i + '_temp_enable')('on')

    def magnet_hold(self):
        """Stop any sweeps"""
        self.write('SET:SYS:VRM:ACTN:HOLD')

    def _get_control_B_param(self, param):
        cmd = 'READ:SYS:VRM:{}'.format(param)
        return self._get_response_value(self.ask(cmd))

    # def _get_control_Bcomp_param(self, param):
    #     cmd = 'READ:SYS:VRM:{}'.format(param)
    #     return self._get_response_value(self.ask(cmd[:-2]) + cmd[-2:])

    def _get_field(self):
        return float(self.ask('READ:SYS:VRM:VECT').split(' ')[-1].strip('T]'))

    def _get_response(self, msg):
        return msg.split(':')[-1]

    def _get_response_value(self, msg):  #TODO need to correct this to make it more readable and include NPERS and PERS, HOLD, SAFE, etc.
        msg = self._get_response(msg)
        if msg.endswith('NOT_FOUND'):
            return None
        elif msg.endswith('IDLE'):
            return 'IDLE'
        elif msg.endswith('RTOS'):
            return 'RTOS'
        # elif msg.endswith('Bx'):
        #     return float(re.findall(r"[-+]?\d*\.\d+|\d+", msg)[0])
        # elif msg.endswith('By'):
        #     return float(re.findall(r"[-+]?\d*\.\d+|\d+", msg)[1])
        # elif msg.endswith('Bz'):
        #     return float(re.findall(r"[-+]?\d*\.\d+|\d+", msg)[2])
        elif len(re.findall(r"[-+]?\d*\.\d+|\d+", msg)) > 1:
            return [float(re.findall(r"[-+]?\d*\.\d+|\d+", msg)[0]), float(re.findall(r"[-+]?\d*\.\d+|\d+", msg)[1]), float(re.findall(r"[-+]?\d*\.\d+|\d+", msg)[2])]
        try:
            return float(re.findall(r"[-+]?\d*\.\d+|\d+", msg)[0])
        except Exception:
            return msg

    def get_idn(self):
        """ Return the Instrument Identifier Message """
        idstr = self.ask('*IDN?')
        idparts = [p.strip() for p in idstr.split(':', 4)][1:]

        return dict(zip(('vendor', 'model', 'serial', 'firmware'), idparts))

    def _get_control_channel(self, force_get=False):

        # verify current channel
        if self._control_channel and not force_get:
            tempval = self.ask(
                'READ:DEV:T{}:TEMP:LOOP:MODE'.format(self._control_channel))
            if not tempval.endswith('NOT_FOUND'):
                return self._control_channel

        # either _control_channel is not set or wrong
        for i in range(1, 17):
            tempval = self.ask('READ:DEV:T{}:TEMP:LOOP:MODE'.format(i))
            if not tempval.endswith('NOT_FOUND'):
                self._control_channel = i
                break
        return self._control_channel

    def _set_control_channel(self, channel):
        self._control_channel = channel
        self.write('SET:DEV:T{}:TEMP:LOOP:HTR:H1'.format(channel))

    def _get_control_param(self, param):
        chan = self._get_control_channel()
        cmd = 'READ:DEV:T{}:TEMP:LOOP:{}'.format(chan, param)
        return self._get_response_value(self.ask(cmd))

    def _set_control_param(self, param, value):
        chan = self._get_control_channel()
        cmd = 'SET:DEV:T{}:TEMP:LOOP:{}:{}'.format(chan, param, value)
        self.write(cmd)

    def _set_control_magnet_sweeprate_param(self, s):
        if 0 < s <= 0.205:
            x = 0
            y = 0
            z = round(self.field(), 4)
            self.write('SET:SYS:VRM:COO:CART:RVST:MODE:RATE:RATE:' + str(s) +
                       ':VSET:[' + str(x) + ' ' + str(y) + ' ' + str(z) + ']\r\n')
        else:
            print(
                'Warning: set sweeprate in range (0 , 0.205] T/min, not setting sweeprate')

## We don't have the vector magnet option.
    # def _set_control_Bx_param(self, x):
    #     s = self.magnet_sweeprate()
    #     y = round(self.By(), 4)
    #     z = round(self.Bz(), 4)
    #     self.write('SET:SYS:VRM:COO:CART:RVST:MODE:RATE:RATE:' + str(s) +
    #                ':VSET:[' + str(x) + ' ' + str(y) + ' ' + str(z) + ']\r\n')
    #     self.write('SET:SYS:VRM:ACTN:RTOS\r\n')
    #     # just to give an time estimate, +10s for overhead
    #     t_wait = self.magnet_sweep_time() * 60 + 10
    #     print('Please wait ' + str(t_wait) + ' seconds for the field sweep...')
    #     while self.magnet_status() != 'IDLE':
    #         pass
    #
    # def _set_control_By_param(self, y):
    #     s = self.magnet_sweeprate()
    #     x = round(self.Bx(), 4)
    #     z = round(self.Bz(), 4)
    #     self.write('SET:SYS:VRM:COO:CART:RVST:MODE:RATE:RATE:' + str(s) +
    #                ':VSET:[' + str(x) + ' ' + str(y) + ' ' + str(z) + ']\r\n')
    #     self.write('SET:SYS:VRM:ACTN:RTOS\r\n')
    #     # just to give an time estimate, +10s for overhead
    #     t_wait = self.magnet_sweep_time() * 60 + 10
    #     print('Please wait ' + str(t_wait) + ' seconds for the field sweep...')
    #     while self.magnet_status() != 'IDLE':
    #         pass

    def _set_field_stable(self, z):
        if self._first_magnet_use is False:
            usecheck = input('Are you sure you want to use the magnet? [y/n]: ')
            if usecheck.lower() == 'y':
                self._first_magnet_use = True
                pass
            else:
                print('Magnet will not be used')
                return

        ## Turn this off for now. Just be cautious when using the magnet
        # maxtempHon8T = 4.87
        # maxtempHon0T = 4.6
        # maxtempHoff8T = 4.7
        # maxtempHoff0T = 4.3
        # magtemp = self.magnet_temp()
        # if self.magnet_swh():
        #     f = np.abs(self.field())
        #     if f < 0.4:
        #         condit_temp = maxtempHon0T + np.sqrt(0.02*f)
        #     else:
        #         p4temp = maxtempHon0T + np.sqrt(0.02*0.4)
        #         sl = (maxtempHon8T - p4temp)/(8-0.4)
        #         interc = p4temp - sl*0.4
        #         condit_temp = sl*f + interc
        # else:
        #     f = np.abs(self.field())
        #     if f < 0.4:
        #         condit_temp = maxtempHoff0T + np.sqrt(0.02*f)
        #     else:
        #         p4temp = maxtempHoff0T + np.sqrt(0.02*0.4)
        #         sl = (maxtempHoff8T - p4temp)/(8-0.4)
        #         interc = p4temp - sl*0.4
        #         condit_temp = sl*f + interc

        # while magtemp >= condit_temp:
        #     print('The magnet temperature is {:.4f} K. '.format(magtemp) +
        #           'Waiting for it to drop < {:.4f} K'.format(condit_temp))
        #     sleep(15)
        #     magtemp = self.magnet_temp()

        s = self.magnet_sweeprate()
        x = 0
        y = 0
        self.write('SET:SYS:VRM:COO:CART:RVST:MODE:RATE:RATE:' + str(s) +
                   ':VSET:[' + str(x) + ' ' + str(y) + ' ' + str(z) + ']')
        self.write('SET:SYS:VRM:ACTN:RTOS')
        # just to give an time estimate, +10s for overhead
        # t_wait = self.magnet_sweep_time() * 60 + 10
        # print('Please wait ' + str(t_wait) + ' seconds for the field sweep, ' +
        #       'plus the time required for operating the switch...')
        while self.magnet_status() != 'IDLE':
            pass

    def _set_field_return(self, z):
        if self._first_magnet_use is False:
            usecheck = input('Are you sure you want to use the magnet? [y/n]: ')
            if usecheck.lower() == 'y':
                self._first_magnet_use = True
                pass
            else:
                print('Magnet will not be used')
                return

        ## Turn this off for now. Just be cautious when using the magnet
        # maxtempHon8T = 4.87
        # maxtempHon0T = 4.6
        # maxtempHoff8T = 4.7
        # maxtempHoff0T = 4.3
        # magtemp = self.magnet_temp()
        # if self.magnet_swh():
        #     f = np.abs(self.field())
        #     if f < 0.4:
        #         condit_temp = maxtempHon0T + np.sqrt(0.02*f)
        #     else:
        #         p4temp = maxtempHon0T + np.sqrt(0.02*0.4)
        #         sl = (maxtempHon8T - p4temp)/(8-0.4)
        #         interc = p4temp - sl*0.4
        #         condit_temp = sl*f + interc
        # else:
        #     f = np.abs(self.field())
        #     if f < 0.4:
        #         condit_temp = maxtempHoff0T + np.sqrt(0.02*f)
        #     else:
        #         p4temp = maxtempHoff0T + np.sqrt(0.02*0.4)
        #         sl = (maxtempHoff8T - p4temp)/(8-0.4)
        #         interc = p4temp - sl*0.4
        #         condit_temp = sl*f + interc

        # while magtemp >= condit_temp:
        #     print('The magnet temperature is {:.4f} K. '.format(magtemp) +
        #           'Waiting for it to drop < {:.4f} K'.format(condit_temp))
        #     sleep(15)
        #     magtemp = self.magnet_temp()

        s = self.magnet_sweeprate()
        x = 0
        y = 0
        self.write('SET:SYS:VRM:COO:CART:RVST:MODE:RATE:RATE:' + str(s) +
                   ':VSET:[' + str(x) + ' ' + str(y) + ' ' + str(z) + ']')
        self.write('SET:SYS:VRM:ACTN:RTOS')
        # just to give an time estimate, +10s for overhead
        # t_wait = self.magnet_sweep_time() * 60 + 10
        # print('Sweep time approximately ' + str(t_wait) + ' seconds')
        return

    def _set_swh(self, val):
        val = parse_inp_bool(val)
        if val == 'ON':
            self.write('SET:SYS:VRM:ACTN:NPERS')
            print('Wait 5 min for the switch to warm')
            sleep(10)
            while self.magnet_status() != 'IDLE':
                pass
        elif val == 'OFF':
            self.write('SET:SYS:VRM:ACTN:PERS')
            print('Wait 5 min for the switch to cool')
            sleep(10)
            while self.magnet_status() != 'IDLE':
                pass
        else:
            raise ValueError('Should be a boolean value (ON, OFF)')

    def _get_named_temp_channels(self):
        for al in tuple(self.chan_alias):
            chan = self.chan_alias[al]
            self.add_parameter(name=al+'_temp',
                               unit='K',
                               get_cmd='READ:DEV:%s:TEMP:SIG:TEMP' % chan,
                               get_parser=self._parse_temp)
            self.add_parameter(name=al+'_temp_enable',
                               get_cmd='READ:DEV:%s:TEMP:MEAS:ENAB' % chan,
                               get_parser=self._parse_state,
                               set_cmd='SET:DEV:%s:TEMP:MEAS:ENAB:{}' % chan,
                               set_parser=parse_inp_bool,
                               vals=Enum(*boolcheck))
            if al == 'MC':
                self.add_parameter(name='MC_Res',
                                   unit='Ohms',
                                   get_cmd='READ:DEV:%s:TEMP:SIG:RES' % chan,
                                   get_parser=self._parse_res)

    def _get_pressure_channels(self):
        self.chan_pressure = []
        for i in range(1, 6):
            chan = 'P%d' % i
            self.chan_pressure.append(chan)
            self.add_parameter(name=chan,
                               unit='mbar',
                               get_cmd='READ:DEV:%s:PRES:SIG:PRES' % chan,
                               get_parser=self._parse_pres)

        chan = 'P6'
        self.chan_pressure.append('POVC')
        self.add_parameter(name='POVC',
                           unit='mbar',
                           get_cmd='READ:DEV:%s:PRES:SIG:PRES' % chan,
                           get_parser=self._parse_pres)
        self.chan_pressure = set(self.chan_pressure)

    def _get_valve_channels(self):
        self.chan_valves = []
        for i in range(1, 10):
            chan = 'V%d' % i
            self.chan_valves.append(chan)
            self.add_parameter(name=chan,
                               get_cmd='READ:DEV:%s:VALV:SIG:STATE' % chan,
                               set_cmd='SET:DEV:%s:VALV:SIG:STATE:{}' % chan,
                               get_parser=self._parse_valve_state,
                               vals=Enum('OPEN', 'CLOSE', 'TOGGLE'))
        self.chan_valves = set(self.chan_valves)

    def _get_pump_channels(self):
        self.chan_pumps = ['turbo', 'knf', 'forepump']
        self.add_parameter(name='turbo',
                           get_cmd='READ:DEV:TURB1:PUMP:SIG:STATE',
                           set_cmd='SET:DEV:TURB1:PUMP:SIG:STATE:{}',
                           get_parser=self._parse_state,
                           set_parser=parse_inp_bool,
                           vals=Enum(*boolcheck))
        self.add_parameter(name='knf',
                           get_cmd='READ:DEV:COMP:PUMP:SIG:STATE',
                           set_cmd='SET:DEV:COMP:PUMP:SIG:STATE:{}',
                           get_parser=self._parse_state,
                           set_parser=parse_inp_bool,
                           vals=Enum(*boolcheck))
        self.add_parameter(name='forepump',
                           get_cmd='READ:DEV:FP:PUMP:SIG:STATE',
                           set_cmd='SET:DEV:FP:PUMP:SIG:STATE:{}',
                           get_parser=self._parse_state,
                           set_parser=parse_inp_bool,
                           vals=Enum(*boolcheck))
        self.chan_pumps = set(self.chan_pumps)

    def _get_temp_channels(self):
        self.chan_temps = []
        for i in range(1, 17):
            chan = 'T%d' % i
            self.chan_temps.append(chan)
            self.add_parameter(name=chan,
                               unit='K',
                               get_cmd='READ:DEV:%s:TEMP:SIG:TEMP' % chan,
                               get_parser=self._parse_temp)
            self.add_parameter(name=chan+'_enable',
                               get_cmd='READ:DEV:%s:TEMP:MEAS:ENAB' % chan,
                               get_parser=self._parse_state,
                               set_cmd='SET:DEV:%s:TEMP:MEAS:ENAB:{}' % chan,
                               set_parser=parse_inp_bool,
                               vals=Enum(*boolcheck))
        self.chan_temps = set(self.chan_temps)

    def fullcooldown(self):
        "Starts the full cooldown automation"
        self.write('SET:SYS:DR:ACTN:CLDN')

    def condense(self):
        "Starts condensing (use only if < about 15K)"
        self.write('SET:SYS:DR:ACTN:COND')

    def mixture_collect(self):
        "Starts collecting the mixture into the tank"
        self.write('SET:SYS:DR:ACTN:COLL')

    def precool(self):
        "Starts a pre-cool (doesn't continue to the next step automatically)"
        self.write('SET:SYS:DR:ACTN:PCL')

    def pause_precool(self):
        "Pauses the pre-cool automation"
        self.write('SET:SYS:DR:ACTN:PCOND')

    def resume_precool(self):
        "Resumes the pre-cool automation"
        self.write('SET:SYS:DR:ACTN:RCOND')

    def stopcool(self):
        "Stops any running automation"
        self.write('SET:SYS:ACTN:STOP')

    def _parse_action(self, msg):
        """ Parse message and return action as a string

        Args:
            msg (str): message string
        Returns
            action (str): string describing the action
        """
        action = msg[17:]
        if action == 'PCL':
            action = 'Precooling'
        elif action == 'EPCL':
            action = 'Empty precool loop'
        elif action == 'COND':
            action = 'Condensing'
        elif action == 'NONE':
            if self.MC_temp.get() < 2:
                action = 'Circulating'
            else:
                action = 'Idle'
        elif action == 'COLL':
            action = 'Collecting mixture'
        else:
            action = 'Unknown'
        return action

    def _parse_status(self, msg):
        return msg[19:]

    def _parse_time(self, msg):
        return msg[14:]

    def _parse_temp(self, msg):
        if 'NOT_FOUND' in msg:
            return None
        return float(msg.split('SIG:TEMP:')[-1].strip('K'))

    def _parse_pres(self, msg):
        if 'NOT_FOUND' in msg:
            return None
        return float(msg.split('SIG:PRES:')[-1].strip('mB'))

    def _parse_state(self, msg):
        if 'NOT_FOUND' in msg:
            return None
        state = msg.split(':')[-1].strip()
        return parse_outp_bool(state)

    def _parse_valve_state(self, msg):
        if 'NOT_FOUND' in msg:
            return None
        state = msg.split(':')[-1].strip()
        return state

    def _parse_pump_speed(self, msg):
        if 'NOT_FOUND' in msg:
            return None
        return float(msg.split('SIG:SPD:')[-1].strip('Hz'))

    def _parse_res(self, msg):
        if 'NOT_FOUND' in msg:
            return None
        return float(msg.split(':')[-1].strip('Ohm'))

    def _parse_swh(self, msg):
        if 'NOT_FOUND' in msg:
            return None
        elif msg.split(' ')[-1].strip(']') == 'ON':
            return 1
        elif msg.split(' ')[-1].strip(']') == 'OFF':
            return 0
        else:
            print('unknown switch heater state')
            return msg

    def _parse_htr(self, msg):
        if 'NOT_FOUND' in msg:
            return None
        return float(msg.split('SIG:POWR:')[-1].strip('uW'))

    def _recv(self):
        return super()._recv().rstrip()
