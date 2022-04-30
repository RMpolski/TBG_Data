import qcodes as qc
import time
import numpy as np
from datetime import datetime
from qcodes import Parameter


class time_from_start(Parameter):
    """ Only a get command, resets the start when initialized and when
    .reset() is called.
    Returns time from last reset in seconds"""
    def __init__(self, name, **kwargs):
        super().__init__(name, get_parser=float, unit='s', **kwargs)
        self.t0 = time.time()

    def get_raw(self):
        return time.time() - self.t0

    def reset(self):
        self.t0 = time.time()


class time_stamp(Parameter):
    """ Only a get command. Measures time from a set period that python
    can easily interpret into a datetime object or use for interpreting
    into a string date/time"""
    def __init__(self, name, **kwargs):
        super().__init__(name, get_cmd=time.time,
                         get_parser=float, **kwargs)


def output_datetime(values, starttime=[]):
    """ values can be an array of time.time() floats or single time.time()
    floats. Returns a list of python datetime.datetime objects (plottable in
    matplotlib)

    starttime is a list that offsets the time to the given (in integers)
    (year, month, day, hour, minute, second, microsecond).
    if all the values are not provided, only the first few are filled
    and further offset values are 1 for dates and 0 for time"""
    if starttime == []:
        starttimestamp = 0
    else:
        if any(type(x) is float for x in starttime):
            starttime = [int(i) for i in starttime]
            print('starttime must be a list of integers. If not integers, ' +
                  'values will be truncated')
        if len(starttime) < 3:
            starttime.extend([1]*(3-len(starttime)))
        elif len(starttime) > 7:
            starttime = starttime[0:7]
            print('starttime must have a length less than 7 ',
                  'or else it will be truncated')
        starttimestamp = datetime(*starttime).timestamp()
    if type(values) is float or type(values) is int:
        v = float(values) + starttimestamp
        return [datetime.fromtimestamp(v)]
    else:
        if type(values) is np.ndarray or type(values) is qc.data.data_array.DataArray:
                v = np.array(values)
                if all(type(x) is np.float64 for x in v):
                    v += starttimestamp
                else:
                    print('The array must be all ints or floats')
                    return
        elif type(values) is list:
            if all(type(item) is int or type(item) is float for item in values):
                v = np.array(values) + starttimestamp
            else:
                print('input list must be floats or integers')
                return
        dtimearray = []
        for val in v:
            dtimearray.append(datetime.fromtimestamp(val))
        return dtimearray


def output_date_strings(values, fmt='%Y-%m-%d %H:%M:%S:%f', starttime=[]):
    """ values can be an array of time.time() floats or single time.time()
    floats. Returns a list of strings with the date in the format fmt.

    starttime is a list that offsets the time to the given (in integers)
    (year, month, day, hour, minute, second, microsecond).
    if all the values are not provided, only the first few are filled
    and further offset values are 1 for dates and 0 for time"""
    dtimearray = output_datetime(values, starttime)
    stringarray = []
    for val in dtimearray:
        stringarray.append(val.strftime(fmt))
    return stringarray
