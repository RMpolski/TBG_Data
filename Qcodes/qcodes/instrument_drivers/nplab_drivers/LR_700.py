from qcodes import VisaInstrument
import qcodes.utils.validators as vals
from functools import partial
import time
import numpy as np


def R_parser(string_out):
    newstrs = string_out.strip().split(' ')
    try:
        if newstrs[1] == 'KOHM':  # kilo Ohms
            return float(newstrs[0])*10**3
        elif newstrs[1] == 'MOHM':
            return float(newstrs[0])*10**-3  # I think this is probably mOhms
        elif newstrs[1] == 'UOHM':  # micro Ohms
            return float(newstrs[0])*10**-6
        else:
            return float(newstrs[0])
    except (ValueError, IndexError):
        return np.nan


def zfill_parser(num: int, val):
    """Takes a string or integer val and outputs a string filled up to length num
    with zeros"""
    return str(int(val)).zfill(num)


def offset_parser(mtype: str, val):
    """Multiplies val by 2, rounds to an integer, and outputs a value that is
    filled with zeros up to length num. Also adds + or minus sign out front.
    Also accepts a string 'R'. mtypestr is either 'R' or 'X' """
    if val == 'R' or val == 'X':
        return '=R'
    elif type(val) is int or type(val) is float:
        vround = round(val*2000)
        if vround >= 0:
            front = '+'
        else:
            front = '-'
        return mtype + '=' + front + str(abs(vround)).zfill(6)


class LR_700(VisaInstrument):
    """Instrument driver for the Lakeshore LR_700 AC resistance bridge.
    Currently only has the ability to get resistance, set and get the
    full-scale resistance measurement range, autorange (on 1, off 0), set and
    get the offset for delta R, set and get the excitation voltage and percent,
    set and get the digital filter, turn on/off and get the x10 mode for delta
    R and delta x, measure x and delta x, set the analog filter (time constant
    in s) and whether its input is delX or delR

    Note: You need to input the exact excitation voltage (in V) and range
    (in ohms). You can find the allowed values in the parameters
    self.range_vals and self.excitation_vals.

    exc_pct: selects a value for the percent of the full excitation to output
    exc_pct_on: 0 sets to 100 pct excitation. 1 sets to the exc_pct value
    """
    def __init__(self, name: str, address: str, **kwargs):
        super().__init__(name, address, terminator='\n', **kwargs)

        self.range_vals = {2e-3: 0, 20e-3: 1, 200e-3: 2, 2: 3,
                           20: 4, 200: 5, 2e3: 6, 20e3: 7, 200e3: 8,
                           2e6: 9, np.nan: np.nan}
        self.excitation_vals = {20e-6: 0, 60e-6: 1, 200e-6: 2,
                                600e-6: 3, 2e-3: 4, 6e-3: 5, 20e-3: 6,
                                np.nan: np.nan}
        self.dfilter_vals = {0.2: '00', 0.4: '01', 0.6: '02', 0.8: '03',
                             1.0: '04', 1.6: '05', 2.0: '06', 3.0: '07',
                             5.0: '08', 7.0: '09', 10.0: '10', 15.0: '11',
                             20.0: '12', 30.0: '13', 45.0: '14', 60.0: '15',
                             90.0: '16', 120.0: '17', 180.0: '18', 300.0: '19',
                             420.0: '20', 600.0: '21', 900.0: '22',
                             1200.0: '23', 1800.0: '24', np.nan: np.nan}
        self.afilter_vals = {0.01: 0, 0.1: 1, 0.3: 2, 1.0: 3, 3.0: 4, 10.0: 5,
                             30.0: 6}

        self.add_parameter('range',
                           set_cmd='Range {}',
                           val_mapping=self.range_vals,
                           get_cmd=partial(self.get_string_repeat, 'Get 6'),
                           get_parser=partial(self.get6parser, 'range'),
                           unit='Ohms')
        self.add_parameter('autorange',
                           set_cmd='Autorange {}',
                           vals=vals.Ints(0, 1))
        self.add_parameter('excitation',
                           set_cmd='Excitation {}',
                           get_cmd=partial(self.get_string_repeat, 'Get 6'),
                           get_parser=partial(self.get6parser, 'excitation'),
                           val_mapping=self.excitation_vals,
                           unit='V')
        self.add_parameter('exc_pct',
                           set_cmd='Varexc ={}',
                           set_parser=partial(zfill_parser, 2),
                           get_cmd=partial(self.get_string_repeat, 'Get 6'),
                           get_parser=partial(self.get6parser, 'exc_pct'),
                           vals=vals.Ints(5, 99))
        self.add_parameter('exc_pct_on',
                           set_cmd='Varexc {}',
                           vals=vals.Ints(0, 1))
        self.add_parameter('R_measure',
                           get_cmd=partial(self.get_string_repeat, 'Get 0'),
                           unit='Ohms',
                           get_parser=R_parser)
        self.add_parameter('DelR_measure',
                           get_cmd=partial(self.get_string_repeat, 'Get 2'),
                           get_parser=R_parser,
                           unit='Ohms')
        self.add_parameter('X_measure',
                           get_cmd=partial(self.get_string_repeat, 'Get 1'),
                           get_parser=R_parser)
        self.add_parameter('DelX_measure',
                           get_cmd=partial(self.get_string_repeat, 'Get 3'),
                           get_parser=R_parser)
        self.add_parameter('x10mode',
                           set_cmd='Mode {}',
                           get_cmd=partial(self.get_string_repeat, 'Get 6'),
                           get_parser=partial(self.get6parser, 'x10mode'),
                           vals=vals.Ints(0, 1))
        self.add_parameter('dfilter',
                           set_cmd=self.dfilter_set,
                           get_cmd=partial(self.get_string_repeat, 'Get 6'),
                           get_parser=partial(self.get6parser, 'dfilter'),
                           val_mapping=self.dfilter_vals,
                           unit='s')
        self.add_parameter('afilter',
                           set_cmd='Noise F={}',
                           val_mapping=self.afilter_vals,
                           unit='s')
        self.add_parameter('afilter_input',
                           set_cmd='Noise I={}',
                           val_mapping={'delR': 0, 'delX': 1})
        self.add_parameter('R_offset',
                           label='LR Resistance',
                           set_cmd='Offset {}',
                           set_parser=partial(offset_parser, 'R'),
                           get_cmd=partial(self.get_string_repeat, 'Get 4'),
                           get_parser=R_parser,
                           unit='Ohms',
                           vals=vals.MultiType(vals.Numbers(-99.9995, 99.9995),
                                               vals.Enum('R', 'X')))
        self.add_parameter('X_offset',
                           set_cmd='Offset {}',
                           set_parser=partial(offset_parser, 'X'),
                           get_cmd=partial(self.get_string_repeat, 'Get 5'),
                           get_parser=R_parser,
                           vals=vals.MultiType(vals.Numbers(-99.9995, 99.9995),
                                               vals.Enum('R', 'X')))

    def dfilter_set(self, val):
        self.write('Filter 3')
        self.write('Filter ={}'.format(val))

    def get_string_repeat(self, getstring):
        """ Since sometimes the value of the returned string is '', repeat up
        to 40 times every quarter of a second"""
        string_out = self.ask(getstring)
        if string_out == '':  # Sometimes the instrument returns nothing
            not_ready = True
        else:
            not_ready = False
            return string_out
        count = 0
        while not_ready:
            time.sleep(0.25)
            string_out = self.ask(getstring)
            if string_out != '':
                not_ready = False
            elif count >= 40:
                not_ready = False
                print('Get command "' + getstring+'" timed out')
            count += 1
        return string_out

    def get6parser(self, param, string_out):
        """Converts the string with all possible values of param into the
        values needed in the parameter.

        Possible params are: range, excitation, exc_pct, dfilter, x10mode"""

        pstring = string_out.strip().split(',')
        try:
            if len(pstring) != 7:
                return np.nan

            if param == 'range':
                return int(pstring[0].strip()[0])
            elif param == 'excitation':
                return int(pstring[1].strip()[0])
            elif param == 'exc_pct':
                return int(pstring[2].strip()[:3])
            elif param == 'dfilter':
                v0 = pstring[3].strip()
                v1 = int(v0[0])
                if v1 == 0:
                    return '04'
                elif v1 == 1:
                    return '07'
                elif v1 == 2:
                    return '10'
                elif v1 == 3:
                    filtstrings = v0[3:len(v0)-1].split(' ')
                    if filtstrings[1] == 's':
                        return self.dfilter_vals[float(filtstrings[0])]
                    elif filtstrings[1] == 'M':
                        return self.dfilter_vals[float(filtstrings[0]*60)]
                    else:
                        print('Problem with filter string')
            elif param == 'x10mode':
                return int(pstring[4].strip()[0])
            else:
                print('Needs one of the following: range, excitation, ' +
                      'exc_pct, dfilter, x10')
        except (ValueError, IndexError):
            return np.nan
