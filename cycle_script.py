import logging
import os
import socket
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from logging.handlers import RotatingFileHandler
from tkinter import filedialog, messagebox, scrolledtext
from types import NoneType
from typing import Iterable

import pandas as pd
import pyvisa
import ttkbootstrap as ttk

from libraries.Chamber import ACS_Discovery1200
from libraries.Connection import Charger
from libraries.infer_data import get_data
from libraries.other_SCPI import CHROMA, HP6032A, ITECH, MSO58B

###############################
# ----- LOGGING OPTIONS ----- #
###############################
log_file = (f"{os.path.dirname(os.path.abspath(__file__))}/log.log")
basic_handler = RotatingFileHandler(
    log_file,
    maxBytes=1000000,
    backupCount=2,
    mode="w"
    )
logging.basicConfig(
    encoding='utf-8', level=logging.DEBUG,
    format='%(asctime)-19s %(name)-11s %(levelname)-8s:'
    ' %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    # filename=log_file,
    # filemode="w",
    handlers=[basic_handler]
    )
# create handler console
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(name)-15s %(levelname)-8s:'
                              ' %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)
# change level for 3rd party module
for i in ['pandas', 'PIL', 'pyvisa', "paramiko"]:
    logger = logging.getLogger(i)
    logger.setLevel(logging.INFO)
_logger = logging.getLogger(__name__)
basic_handler.doRollover()

###############################
# ----- DEFAULT OPTIONS ----- #
###############################
# USAGE OPTIONS
ITECH_USAGE = True
CHROMA_USAGE = True
HP6032A_USAGE = True
MSO58B_USAGE = True
CHAMBER_USAGE = True
ARM_XL_USAGE = True

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


###################################
# ----- CLASS and FUNCTIONS ----- #
###################################
class ShowInfo(tk.Toplevel):
    """Info and Skip Toplevel"""

    def __init__(self, parent=None,
                 event: threading.Event = None,
                 data: pd.DataFrame = None,
                 play_event: threading.Event = None):
        super().__init__()
        self.title("Sequence Info")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.geometry("900x280")

        self.skip_event = event
        self.play_event = play_event
        self.pause_state = False

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
        self.skip_btn.grid(row=5, column=0, padx=10, pady=10)
        self.pause_btn = tk.Button(main_frm,
                                   text="  PAUSE  ",
                                   font=("ABBvoice", "20"),
                                   command=self.pause)
        self.skip_btn.grid(row=6, column=0, padx=10, pady=10)

        self.all_command = scrolledtext.ScrolledText(main_frm,
                                                     height=11, width=65)
        with pd.option_context('display.max_rows', None,
                               'display.max_columns', None):
            self.all_command.insert(tk.END, data)
        self.all_command.grid(row=0, rowspan=5, column=2, padx=5)

    def skip(self):
        self.skip_event.set()
        _logger.info("Skipping...")
        self.skip_btn.grid_forget()
        self.update()
        self.after(1000, self.skip_btn.grid(
            row=5, column=0, padx=10, pady=10
            ))

    def pause(self):
        if self.pause_state:
            self.play_event.set()
            _logger.info("Resuming...")
            self.skip_btn.configure(state="normal")
            self.pause_btn.configure(text="  PAUSE  ")
            self.update()
        else:
            self.play_event.clear()
            _logger.info("Pausing...")
            self.skip_btn.configure(state="disabled")
            self.pause_btn.configure(text="  RESUME  ")
            self.update()

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


class User_Options(ttk.Window):

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        
        self.filename = tk.StringVar(value=FILENAME)
        self.bool_var = {
            "ITECH": tk.BooleanVar(value=ITECH_USAGE),
            "CHROMA": tk.BooleanVar(value=CHROMA_USAGE),
            "HP6032A": tk.BooleanVar(value=HP6032A_USAGE),
            "MSO58B": tk.BooleanVar(value=MSO58B_USAGE),
            "CHAMBER": tk.BooleanVar(value=CHAMBER_USAGE),
            "ARM_XL": tk.BooleanVar(value=ARM_XL_USAGE),
        }
        self.string_var = {
            "ITECH": tk.StringVar(value=ITECH_ADDRESS),
            "CHROMA": tk.StringVar(value=CHROMA_ADDRESS),
            "HP6032A": tk.StringVar(value=HP6032A_ADDRESS),
            "MSO58B": tk.StringVar(value=MSO58B_ADDRESS),
            "CHAMBER": tk.StringVar(value=CHAMBER_ADDRESS),
            "ARM_XL": {
                "host": tk.StringVar(value=ARM_XL_ADDRESS["host"]),
                "user": tk.StringVar(value=ARM_XL_ADDRESS["user"]),
                "pwd": tk.StringVar(value=ARM_XL_ADDRESS["pwd"])
            }
        }
        self.__create_user_widget()

    def __create_user_widget(self):
        user_frm = ttk.Frame(self)
        user_frm.pack()

        file_frm = ttk.Labelframe(user_frm, text="COMMAND FILE", padding=2)
        file_frm.pack(fill="both")
        ttk.Entry(file_frm, textvariable=self.filename, width=40).pack(fill="x", expand=1, side="left", padx=2)
        fileoption = dict(
            title="Please select a file:",
            defaultextension="*.xlsx",
            filetypes=[
                ("Tutti i file", "*.*"),
                ("Sequenza Comandi", "*.xlsx"),
                # ("File di configigurazione", "*.json"),
                ("Tutti i File Excel", "*.xl*"),
                ],
            )
        btn = ttk.Button(file_frm, text="SELECT", command=lambda opt=fileoption: self.filename.set(filedialog.askopenfilename(**opt)))
        btn.pack(side="left", padx=2)
        
        scpi_frm = ttk.Labelframe(user_frm, text="SCPI/ModBus Instrument", padding=2)
        scpi_frm.pack(fill="both")
        ttk.Label(scpi_frm, text="USE").grid(row=0, column=1)
        ttk.Label(scpi_frm, text="ADDRESS").grid(row=0, column=2)
        for i, (lbl, var) in enumerate(self.string_var.items()):
            if lbl == "ARM_XL":
                continue
            ttk.Label(scpi_frm, text=lbl, anchor="w").grid(row=i+1, column=0, padx=(5, 0), pady=2)
            check = ttk.Checkbutton(scpi_frm, variable=self.bool_var[lbl], bootstyle="round-toggle")
            check.grid(row=i+1, column=1, padx=(5, 0), pady=2)
            ent = ttk.Entry(scpi_frm, textvariable=var, width=40)
            ent.grid(row=i+1, column=2, padx=(5, 2), pady=2)
            check.configure(command=lambda wd=ent, var=self.bool_var[lbl]: wd.configure(state="normal") if var.get() else wd.configure(state="disabled"))

        armxl_frm = ttk.Labelframe(user_frm, text="ARM_XL", padding=2)
        armxl_frm.pack(fill="both")
        ttk.Label(armxl_frm, text="USE", anchor="w").grid(row=0, column=0, padx=(5, 0), pady=2)
        check = ttk.Checkbutton(armxl_frm, variable=self.bool_var["ARM_XL"], bootstyle="round-toggle")
        check.grid(row=0, column=1, padx=(5, 0), pady=2)
        ent_l = []
        for i, (lbl, var) in enumerate(self.string_var["ARM_XL"].items()):
            ttk.Label(armxl_frm, text=lbl, anchor="w").grid(row=i+1, column=0, padx=(5, 0), pady=2)
            ent = ttk.Entry(armxl_frm, textvariable=var, width=20)
            ent.grid(row=i+1, column=1, padx=(5, 2), pady=2)
            ent_l.append(ent)

        def on_off(var, wds):
            if var.get():
                s = "normal"
            else:
                s = "disabled"
            for wd in wds:
                wd.configure(state=s)

        check.configure(command=lambda wds=ent_l, var=self.bool_var["ARM_XL"]:  on_off(var, wds))


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

#################################
# ----- # USER OPTIONS #  ----- #
#################################
root = User_Options()
root.mainloop()
usage_cfg = root.bool_var
string_cfg = root.string_var
# TODO add you sure?
rm = pyvisa.ResourceManager()


########################
# ----- GET DATA ----- #
########################
_logger.debug("Getting data, check new sequence, add basic sequence")
df, list_of_time, list_of_instr, list_of_command, list_of_args = get_data(filename=FILENAME, logger=_logger)  # noqa: E501
lenght = df.__len__()

##########################
# ----- Connecting ----- #
##########################
_logger.debug("Connecting all item...")
try:
    # ITECH
    address = string_cfg["ITECH"].get()
    if address.startswith(("ASRL", "GPIB", "PXI", "visa", "TCPIP", "USB", "VXI")) and usage_cfg["ITECH"].get() is True:  # noqa: E501
        itech = ITECH()
        itech.connect(address)
        itech.config()
    else:
        itech = None
    # CHROMA
    address = string_cfg["CHROMA"].get()
    if address.startswith(("ASRL", "GPIB", "PXI", "visa", "TCPIP", "USB", "VXI")) and usage_cfg["CHROMA"].get() is True:  # noqa: E501
        chroma = CHROMA()
        chroma.connect(address)
    else:
        chroma = None
    # HP6032A
    address = string_cfg["HP6032A"].get()
    if address.startswith(("ASRL", "GPIB", "PXI", "visa", "TCPIP", "USB", "VXI")) and usage_cfg["HP6032A"].get() is True:  # noqa: E501
        hp6032a = HP6032A()
        hp6032a.connect(address)
    else:
        hp6032a = None
    # MSO58B
    address = string_cfg["MSO58B"].get()
    if address.startswith(("ASRL", "GPIB", "PXI", "visa", "TCPIP", "USB", "VXI")) and usage_cfg["MSO58B"].get() is True:  # noqa: E501
        mso58b = MSO58B()
        mso58b.connect(address)
    else:
        mso58b = None
    # CHAMBER
    com_port = string_cfg["CHAMBER"].get()
    if com_port.startswith(("COM", "tty")) and usage_cfg["CHAMBER"].get() is True:  # noqa: E501
        chamber = ACS_Discovery1200(com_port)
    else:
        chamber = None
    # ARM-XL
    if usage_cfg["ARM_XL"].get() is True:
        host = string_cfg["ARM_XL"]["host"].get()
        socket.inet_aton(host)
        user = string_cfg["ARM_XL"]["user"].get()
        pwd = string_cfg["ARM_XL"]["pwd"].get()
        arm_xl = Charger(host=host,
                         user=user,
                         pwd=pwd)
    else:
        arm_xl = None
except socket.error as e:
    _logger.exception("SSH connection Error")
    raise e
except Exception as e:
    _logger.exception("Connection Error")
    raise e

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
    for i in range(lenght):
        try:
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
                info_box.update_text(
                    instr, f"Wait {rel_time} seconds ", time_, i
                    )
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
        except Exception:
            # FIXME Not Exception, but SSH or PYVISA or PYMODBUS EXCEPTION
            _logger.critical("Error during sequence execution", exc_info=1)
            # _ = next(list_of_command)
            # _ = next(list_of_args)
            # continue
            sys.exit(1)  # TODO safe exit
        else:
            while time.time() - now < rel_time and not skip_event.is_set():
                if not play_event.is_set():
                    passed_time = time.time() - now
                    rel_time = rel_time - passed_time
                    play_event.wait()
                    now = time.time()

    info_box.master.destroy()


###############################
# ----- INFO TK and RUN ----- #
###############################
skip_event = threading.Event()
play_event = threading.Event()
play_event.set()
info_box = ShowInfo(event=skip_event, data=df, play_event=play_event)
t = threading.Thread(target=run_test, daemon=True)
t.start()
info_box.mainloop()
t.join()
