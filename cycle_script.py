import time
from types import NoneType
from typing import Iterable

import pandas as pd

from Chamber import ACS_Discovery1200
from Connection import Charger
from other_SCPI import CHROMA, ITECH

# CONNECTION STRING
ITECH_ADDRESS = "TCPIP0::192.168.0.102::inst0::INSTR"
CHROMA_ADDRESS = "TCPIP0::192.168.0.101::2101::SOCKET"
CHAMBER_ADDRESS = "COM8"
ARM_XL_ADDRESS = {"host": "192.168.0.101",
                  "user": "root",
                  "pwd": "ABB"}


def get_data():
    df = pd.read_excel("command.xlsx")
    _time = iter(df.Time)
    instr = iter(df.Instrument)
    command = iter(df.Command)
    args = iter(df.Argument)
    lenght = df.__len__()
    return lenght, _time, instr, command, args


def arg_parse(arg_str):
    import ast
    if isinstance(arg_str, pd._libs.missing.NAType | NoneType):
        return None
    elif arg_str == "":
        return None
    elif arg_str == "-":
        return None
    elif isinstance(arg_str, int) or isinstance(arg_str, float):
        return [arg_str]
    else:
        args = [i.split() if len(i.split()) > 1 else i
                for i in arg_str.split(" ")]

    def tryeval(val):
        if isinstance(val, Iterable) and not isinstance(val, str):
            val = [tryeval(i) for i in val]
        try:
            val = ast.literal_eval(val)
        except ValueError:
            pass
        return val

    args = [tryeval(i) for i in args]
    return args


def parse_command(command: str, args: str):
    if not isinstance(args, str):
        args = str(args)
    base_cmd = "./"
    cmd = base_cmd + command + " " + args
    return cmd

# CHAMBER command
# 'start_temp' no param
# 'stop_temp' no param
# 'start_hum' no param
# 'stop_hum' no param
# 'start_temp_hum' no param
# 'stop' no param
# 'write_setpoint' ["Temp" | "Hum"], <value>, <time_to_set>=None

# ITECH command
# "set_output" ["on" | "off"]
# "set_function"  ["voltage" | "current"]
# "set_current" <value>
# "set_v_limit" <value>, <value>
# "set_voltage" <value>
# "set_c_limit" <value>, <value>

# CHROMA command
# "set_output" ["on" | "off"]
# "set_frequency"  <value>
# "set_voltage"  <value>, ["ac" | "dc"]="ac"
# "europe_grip" no param
# "usa_grid" no param

# CHARGER command
# "command on the SSH client without ./" "additional param"


itech = ITECH()
itech.connect(ITECH_ADDRESS)
chroma = CHROMA()
chroma.connect(CHROMA_ADDRESS)
chamber = ACS_Discovery1200(CHAMBER_ADDRESS)
arm_xl = Charger(**ARM_XL_ADDRESS)
instruments = {
    "itech": itech,
    "chroma": chroma,
    "chamber": chamber,
    "arm_xl": arm_xl
    }

lenght, list_of_time, list_of_instr, list_of_command, list_of_args = get_data()

for i in range(lenght):
    now = time.time()
    rel_time = next(list_of_time)
    instr = instruments.get(next(list_of_instr))
    if instr != arm_xl:  # not arm_xl instrument
        command = getattr(instr, next(list_of_command))
        args = arg_parse(next(list_of_args))
        print(instr, command, args)
        if args is None:
            command()
        elif isinstance(args, tuple):
            command(args)
        else:
            command(*args)
    else:
        command = next(list_of_command)
        args = next(list_of_args)
        cmd = parse_command(command, args)
        instr: Charger
        instr._client.exec_command(cmd)
    while time.time() - now < rel_time:
        continue
