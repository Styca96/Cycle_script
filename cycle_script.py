import time
import tkinter as tk
from os import popen
from tkinter import ttk
from types import NoneType
from typing import Iterable

import pandas as pd
import pyvisa

from Chamber import ACS_Discovery1200
from Connection import Charger
from other_SCPI import CHROMA, ITECH

# TODO wait function, power supply
# CONNECTION STRING
ITECH_ADDRESS = "TCPIP0::192.168.0.102::inst0::INSTR"
CHROMA_ADDRESS = "TCPIP0::192.168.0.101::2101::SOCKET"
CHAMBER_ADDRESS = "COM8"
ARM_XL_ADDRESS = {"host": "192.168.0.101",
                  "user": "root",
                  "pwd": "ABB"}


rm = pyvisa.ResourceManager()


class Select_GUI(tk.Tk):
    def __init__(self, title: str, mode="SCPI"):
        super().__init__()
        self.title(title + " ADDRESS")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.mode = mode
        self.val = tk.StringVar(value=title + " Address")
        self.cmb = ttk.Combobox(self,
                                values=self.refresh_instr(rm),
                                textvariable=self.val)
        self.cmb.pack()
        self.refresh_btn = tk.Button(self,
                                     text="Refresh",
                                     command=lambda: self.cmb.config(
                                         values=self.refresh_instr(rm)
                                         )
                                     )
        self.refresh_btn.pack()
        self.mainloop()

    def refresh_instr(self, rm):
        """Riaggiorna la lista strumenti VISA\n
        Returns:
            Tuple[str,...]: lista strumenti
        """
        if self.mode == "SCPI":
            instrument_list = rm.list_resources()
        elif self.mode == "COM":
            import serial.tools.list_ports

            com_list = [comport.device
                        for comport in serial.tools.list_ports.comports()]
            instrument_list = com_list
        elif self.mode == "IP":
            result = popen("arp -a")
            instrument_list = [j for i in result.read().splitlines()
                               for j in (i.split(" ")) if j != "" and "." in j]
        elif self.mode == "str":
            instrument_list = []

        return instrument_list

    def on_closing(self):
        self.destroy()


def show_options(name: str, mode: str):
    root = Select_GUI(name, mode)
    # root.mainloop()
    return root.val.get()


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
chroma = CHROMA()
# ----- default value in script
# itech.connect(ITECH_ADDRESS)
# chroma.connect(CHROMA_ADDRESS)
# chamber = ACS_Discovery1200(CHAMBER_ADDRESS)
# arm_xl = Charger(**ARM_XL_ADDRESS)
# ----- select value
itech.connect(show_options("ITECH", "SCPI"))
chroma.connect(show_options("CHROMA", "SCPI"))
chamber = ACS_Discovery1200(show_options("CHAMBER", "COM"))
arm_xl = Charger(host=show_options("ARM-XL", "IP"),
                 user=show_options("ARM-XL user", "str"),
                 pwd=show_options("ARM-XL pwd", "str"))
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
