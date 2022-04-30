import serial
import time
from qcodes import Instrument
from qcodes.utils.helpers import strip_attrs
from functools import partial
from qcodes.utils.validators import Enum, Ints

boolcheck = (0, 1, 'on', 'off', 'ON', 'OFF', False, True)

def parse_inp_bool(value):
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

class Lakeshore211(Instrument):
    """ Driver for the lakeshore 211 temperature sensor, using its DB9
    RS-232 interface. (On the lab computer 'COM4')"""

    def __init__(self, name, address, timeout=8, terminator='\r\n', **kwargs):
        super().__init__(name, **kwargs)

        self.address = address
        self.terminator = terminator
        self._open_serial_connection(timeout)

        self.add_parameter('temperature', get_cmd='KRDG?',
                           get_parser=float)
        self.add_parameter('temperature_C', get_cmd='CRDG?',
                           get_parser=float)
        self.add_parameter('temperature_F', get_cmd='FRDG?',
                           get_parser=float)
        self.add_parameter('display', get_cmd='DISPON?',
                           set_cmd='DISPON {}',
                           get_parser=int,
                           set_parser=parse_inp_bool,
                           vals=Enum(*boolcheck))
        self.add_parameter('display_brightness',
                           get_cmd='BRIGT?',
                           set_cmd='BRIGT {}',
                           get_parser=int,
                           set_parser=int,
                           vals=Ints(1, 15))

        self.connect_message()


    def _open_serial_connection(self, timeout=None):
        if timeout is None:
            ser = serial.Serial(self.address, 9600, parity='O', bytesize=7)
        else:
            ser = serial.Serial(self.address, 9600, timeout=timeout, parity='O', bytesize=7)
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

    def get_idn(self):
        """ The idn for this instrument also comes from the *IDN command, but
        the sequence is a bit different due to it being a serial instrument"""
        idstr = ''  # in case self.ask fails
        try:
            self._ser.write('*IDN?\r\n'.encode('ascii'))
            idstr = self._ser.readline().decode().strip()
            # form is supposed to be comma-separated, but we've seen
            # other separators occasionally
            idparts: List[Optional[str]]
            for separator in ',;:':
                # split into no more than 4 parts, so we don't lose info
                idparts = [p.strip() for p in idstr.split(separator, 3)]
                if len(idparts) > 1:
                    break
            # in case parts at the end are missing, fill in None
            if len(idparts) < 4:
                idparts += [None] * (4 - len(idparts))
        except:
            self.log.debug('Error getting or interpreting *IDN?: '
                           + repr(idstr))
            idparts = [None, self.name, None, None]

        # some strings include the word 'model' at the front of model
        if str(idparts[1]).lower().startswith('model'):
            idparts[1] = str(idparts[1])[5:].strip()

        return dict(zip(('vendor', 'model', 'serial', 'firmware'), idparts))

    def ask_raw(self, cmd):
        cmd += self.terminator
        self._ser.write(cmd.encode('ascii'))
        return self._ser.readline().decode().strip()

    def write_raw(self, cmd):
        cmd += self.terminator
        self._ser.write(cmd.encode('ascii'))
