import socket
import time
import tkinter as tk
from os import popen
from tkinter import ttk
from types import NoneType
from typing import Iterable

import pandas as pd
import pyvisa

from libraries.Chamber import ACS_Discovery1200
from libraries.check_sequence import get_data
from libraries.Connection import Charger
from libraries.other_SCPI import CHROMA, HP6032A, ITECH, MSO58B

# if True usa CONNECTION STRING, else open GUI for selection
default = False  
# DEFAULT CONNECTION STRING
ITECH_ADDRESS = "TCPIP0::192.168.0.102::30000::SOCKET"
CHROMA_ADDRESS = "TCPIP0::192.168.0.101::2101::SOCKET"
CHAMBER_ADDRESS = "COM3"
HP6032A_ADDRESS = "GPIB::5::INSTR"
MSO58B_ADDRESS = "TCPIP0::192.168.0.106::inst0::INSTR"
ARM_XL_ADDRESS = {"host": "192.168.0.103",
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
                                width=80,
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
        "".split()
        args = [i.split() if len(i.split()) > 1 else i
                for i in arg_str.split()]

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
    base_cmd = "nohup ./"
    cmd = base_cmd + command + " " + args + " & >/dev/null\n"
    return cmd

# ----- COMMAND DESCRIPTIONS ----- #
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

# HP6032A
# "set_current" <value>
# "set_voltage" <value>
# "set_output" ["on" | "off"]

# MSO58B
# "save_screen" <filepath>


# ----- GET DATA ----- #
lenght, list_of_time, list_of_instr, list_of_command, list_of_args = get_data()

# ----- Connecting ----- #
# ITECH
address = show_options("ITECH", "SCPI") if default is False else ITECH_ADDRESS
if address.startswith(("ASRL", "GPIB", "PXI", "visa", "TCPIP", "USB", "VXI")):
    itech = ITECH()
    itech.connect(address)
else:
    itech = None
# CHROMA
address = show_options("CHROMA", "SCPI") if default is False else CHROMA_ADDRESS
if address.startswith(("ASRL", "GPIB", "PXI", "visa", "TCPIP", "USB", "VXI")):
    chroma = CHROMA()
    chroma.connect(address)
else:
    chroma = None
# HP6032A
address = show_options("HP6032A", "SCPI") if default is False else HP6032A_ADDRESS
if address.startswith(("ASRL", "GPIB", "PXI", "visa", "TCPIP", "USB", "VXI")):
    hp6032a = HP6032A()
    hp6032a.connect(address)
else:
    hp6032a = None
# MSO58B
address = show_options("MSO58B", "SCPI") if default is False else MSO58B_ADDRESS
if address.startswith(("ASRL", "GPIB", "PXI", "visa", "TCPIP", "USB", "VXI")):
    mso58b = MSO58B()
    mso58b.connect(address)
else:
    mso58b = None
# CHAMBER
com_port = show_options("CHAMBER", "COM") if default is False else CHAMBER_ADDRESS
if com_port.startswith(("COM", "tty")):
    chamber = ACS_Discovery1200(com_port)
else:
    chamber = None
# ARM-XL
host = show_options("ARM-XL", "IP") if default is False else ARM_XL_ADDRESS["host"]
try:
    socket.inet_aton(host)
    user = show_options("ARM-XL user", "str") if default is False else ARM_XL_ADDRESS["user"]
    pwd = show_options("ARM-XL pwd", "str") if default is False else ARM_XL_ADDRESS["pwd"]
    arm_xl = Charger(host=host,
                     user=user,
                     pwd=pwd)
except socket.error:
    arm_xl = None

instruments = {
    "dc_source": itech,
    "ac_source": chroma,
    "powersupply": hp6032a,
    "clim_chamber": chamber,
    "armxl": arm_xl,
    "oscilloscope": mso58b,
    "sleep": "sleep",
    }

# ----- EXECUTE COMMAND ----- #
for i in range(lenght):
    now = time.time()
    rel_time = next(list_of_time)
    instr = instruments.get(next(list_of_instr).lower())
    # --- ARMxl command --- #
    if instr == arm_xl:  
        command = next(list_of_command)
        args = next(list_of_args)
        cmd = parse_command(command, args)
        print(instr, cmd)
        instr: Charger
        instr._shell.send(cmd)
    # --- sleep command --- #
    # if instr == "sleep":
    elif instr == "sleep":
        print(f"Wait {rel_time} seconds ")
        _ = next(list_of_command)
        _ = next(list_of_args)
    # --- SCPI or MODBUS command --- #
    # elif instr != "sleep":  # not arm_xl instrument
    elif instr != arm_xl:  # not arm_xl instrument
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
        print("No Instrument found\nPass to next command without wait")
        _ = next(list_of_command)
        _ = next(list_of_args)
        continue
    while time.time() - now < rel_time:
        continue
