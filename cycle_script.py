import logging
import os
import socket
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, scrolledtext, ttk
from types import NoneType
from typing import Iterable

import pandas as pd
import pyvisa

from libraries.Chamber import ACS_Discovery1200
from libraries.Connection import Charger
from libraries.infer_data import get_data
from libraries.other_SCPI import CHROMA, HP6032A, ITECH, MSO58B

###############################
# ----- LOGGING OPTIONS ----- #
###############################
log_file = (f"{os.path.dirname(os.path.abspath(__file__))}/log.log")
logging.basicConfig(
    encoding='utf-8', level=logging.DEBUG,
    format='%(asctime)-19s %(name)-11s %(levelname)-8s:'
    ' %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    filename=log_file,
    filemode='w',
    )
# create handler console
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(name)-15s %(levelname)-8s:'
                              ' %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)
# change level for 3rd party module
for i in ['pandas', 'PIL', 'pyvisa']:
    logger = logging.getLogger(i)
    logger.setLevel(logging.INFO)
_logger = logging.getLogger(__name__)

###############################
# ----- DEFAULT OPTIONS ----- #
###############################
# DEFAULT CONNECTION STRING
ITECH_ADDRESS = "TCPIP0::192.168.0.102::30000::SOCKET"
CHROMA_ADDRESS = "TCPIP0::192.168.0.101::2101::SOCKET"
CHAMBER_ADDRESS = "COM3"
HP6032A_ADDRESS = "GPIB::5::INSTR"
MSO58B_ADDRESS = "TCPIP0::192.168.0.107::inst0::INSTR"
ARM_XL_ADDRESS = {"host": "192.168.0.103",
                  "user": "root",
                  "pwd": "ABB"}

FILENAME = "command.xlsx"

# if True usa CONNECTION STRING, else open GUI for selection
if messagebox.askyesno("Configuration",
                       "Use DEFAULT configuration?"):
    default = True
    _logger.info("Use default configuration")
else:
    default = False
    fileoption = dict(
        title="Please select a file:",
        defaultextension="*.xlsx",
        filetypes=[
            ("Tutti i file", "*.*"),
            ("Sequenza Comandi", "*.xlsx"),
            ("File di configigurazione", "*.json"),
            ("Tutti i File Excel", "*.xl*")
            ],
        )
    _logger.debug("Selecting sequence file")
    FILENAME = filedialog.askopenfilename(**fileoption)
    _logger.info(f"Select {FILENAME}")


rm = pyvisa.ResourceManager()


###################################
# ----- CLASS and FUNCTIONS ----- #
###################################
class ShowInfo(tk.Toplevel):
    """Info and Skip Toplevel"""

    def __init__(self, parent=None,
                 event: threading.Event = None,
                 data: pd.DataFrame = None):
        super().__init__()
        self.title("Sequence Info")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.geometry("900x280")

        self.skip_event = event

        main_frm = tk.Frame(self)
        main_frm.pack(expand=1, fill="both")

        tk.Label(main_frm, text="INFO"
                 ).grid(row=0, column=0, columnspan=2, padx=10, pady=10)
        tk.Label(main_frm, text="Index:\t\t"
                 ).grid(row=1, column=0, padx=5, pady=10)
        tk.Label(main_frm, text="Instrument:\t"
                 ).grid(row=2, column=0, padx=5, pady=10)
        tk.Label(main_frm, text="Command:\t"
                 ).grid(row=3, column=0, padx=5, pady=10)
        tk.Label(main_frm, text="Time:\t\t"
                 ).grid(row=4, column=0, padx=5, pady=10)

        self.index_lbl = tk.Label(main_frm, text="None", justify="left")
        self.index_lbl.grid(row=1, column=1, padx=5)
        self.instr_lbl = tk.Label(main_frm, text="None", justify="left")
        self.instr_lbl.grid(row=2, column=1, padx=5)
        self.command_lbl = tk.Label(main_frm, text="None", justify="left")
        self.command_lbl.grid(row=3, column=1, padx=5)
        self.time_lbl = tk.Label(main_frm, text="None", justify="left")
        self.time_lbl.grid(row=4, column=1, padx=5)

        self.skip_btn = tk.Button(main_frm,
                                  text="  SKIP  ",
                                  font=("ABBvoice", "20"),
                                  command=self.skip)
        self.skip_btn.grid(row=5, column=0, columnspan=2, padx=10, pady=10)
        
        self.all_command = scrolledtext.ScrolledText(main_frm, height=11, width=65)
        for i in range(data.__len__()//60 + 1):
            self.all_command.insert(tk.END, data.iloc[60*(i):60*(i+1)])
            self.all_command.insert(tk.END, "\n")
        self.all_command.grid(row=0, rowspan=5, column=2, padx=5)

    def skip(self):
        self.skip_event.set()
        _logger.info("Skipping...")
        self.skip_btn.grid_forget()
        self.update()
        self.after(1000, self.skip_btn.grid(
            row=5, column=0, columnspan=2, padx=10, pady=10
            ))

    def update_text(self, instr: str, command: str, time_: str, index: int):
        self.index_lbl.configure(text=str(index))
        self.instr_lbl.configure(text=instr)
        self.command_lbl.configure(text=command)
        self.time_lbl.configure(text=time_)
        _logger.debug(f"{instr} - {command}")

    def mainloop(self):
        self.master.iconify()
        super().mainloop()

    def on_closing(self):
        if messagebox.askyesno("Closing", "Are you sure?"):
            self.destroy()
            self.master.destroy()
            sys.exit()
        else:
            return


class Select_GUI(tk.Tk):
    """Address Selection"""

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
            result = os.popen("arp -a")
            instrument_list = [j for i in result.read().splitlines()
                               for j in (i.split(" ")) if j != "" and "." in j]
        elif self.mode == "str":
            instrument_list = []

        return instrument_list

    def on_closing(self):
        self.destroy()


def show_options(name: str, mode: str):
    """Show options and get result"""
    _logger.debug(f"Getting {name} address")
    root = Select_GUI(name, mode)
    add = root.val.get()
    _logger.info(f"{name} address = {add}")
    return add


def arg_parse(arg_str):
    """Parsing argument from str type"""
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
    """Parse command for ARMxl"""
    if not isinstance(args, str):
        args = str(args)
    base_cmd = "nohup ./"
    cmd = base_cmd + command + " " + args + " & >/dev/null\n"
    return cmd


########################
# ----- GET DATA ----- #
########################
_logger.debug("Getting data, check new sequence, add basic sequence")
df, list_of_time, list_of_instr, list_of_command, list_of_args = get_data(filename=FILENAME, logger=_logger)
lenght = df.__len__()

##########################
# ----- Connecting ----- #
##########################
_logger.debug("Connecting all item...")
# ITECH
address = show_options("ITECH", "SCPI") if default is False else ITECH_ADDRESS
if address.startswith(("ASRL", "GPIB", "PXI", "visa", "TCPIP", "USB", "VXI")):
    itech = ITECH()
    itech.connect(address)
    itech.config()
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

_logger.info("All items connected")
instruments = {
    "dc_source": itech,
    "ac_source": chroma,
    "powersupply": hp6032a,
    "clim_chamber": chamber,
    "armxl": arm_xl,
    "oscilloscope": mso58b,
    "sleep": "sleep",
    }


###############################
# ----- EXECUTE COMMAND ----- #
###############################
def run_test():
    _logger.info("Start sequence test")
    # TODO safe exit
    for i in range(lenght):
        # TODO pause_event
        now = time.time()
        time_ = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        skip_event.clear()
        rel_time = next(list_of_time)
        instr = instruments.get(next(list_of_instr).lower())
        # --- ARMxl command --- #
        if instr == arm_xl:
            command = next(list_of_command)
            args = next(list_of_args)
            cmd = parse_command(command, args)
            info_box.update_text(instr, f"{command} - {args}", time_, i)
            instr: Charger
            instr._shell.send(cmd)
        # --- sleep command --- #
        elif instr == "sleep":
            info_box.update_text(instr, f"Wait {rel_time} seconds ", time_, i)
            _ = next(list_of_command)
            _ = next(list_of_args)
        # --- SCPI or MODBUS command --- #
        elif instr != arm_xl:  # not arm_xl instrument
            func_ = next(list_of_command).strip()
            command = getattr(instr, func_)
            args = arg_parse(next(list_of_args))
            info_box.update_text(instr, f"{func_} - {args}", time_, i)
            if args is None:
                command()
            elif isinstance(args, tuple):
                command(args)
            else:
                command(*args)
        else:
            _logger.warning("No Instrument found "
                            "- pass to next command without wait")
            _ = next(list_of_command)
            _ = next(list_of_args)
            continue
        while time.time() - now < rel_time and not skip_event.is_set():
            continue
    info_box.master.destroy()


###############################
# ----- INFO TK and RUN ----- #
###############################
skip_event = threading.Event()
info_box = ShowInfo(event=skip_event, data=df)
t = threading.Thread(target=run_test, daemon=True)
t.start()
info_box.mainloop()
t.join()
