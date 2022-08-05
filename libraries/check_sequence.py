import time
from tkinter import messagebox

import pandas as pd

from .Chamber import ACS_Discovery1200
from .Connection import Charger
from .other_SCPI import CHROMA, HP6032A, ITECH, MSO58B

# instr_list = ["dc_source", "ac_source", "powersupply",
#               "clim_chamber", "armxl", "oscilloscope", "sleep"]
instr_dict = {
    "dc_source": ITECH,
    "ac_source": CHROMA,
    "powersupply": HP6032A,
    "clim_chamber": ACS_Discovery1200,
    "armxl": {"set_voltage_and_power.sh": 2,
              "start_charge_session.sh": 0,
              "stop_charge_session.sh": 0,
              "set_power.sh": 1,
              "set_reactive.sh": 1},
    "oscilloscope": MSO58B,
    "sleep": ["sleep", "-"]
    }


def get_data():
    now = time.time()  # XXX debug read excel
    try:
        df = pd.read_excel("./command_debug.xlsx",
                           engine="openpyxl",
                        #    sheet_name="HOLD_SequenceConfig",  # XXX debug
                           sheet_name="Foglio1",
                           usecols=["Time", "Instrument", "Command", "Argument"],
                           header=0,
                           dtype={"Time": int,
                                  "Instrument": str,
                                  "Command": str,
                                  "Argument": str}
                           )
    except Exception as e:
        title = "Errore lettura FILE"
        message = "Errore sui 'tipi' dei valori sulle colonne"
        show_error(title, message, e)
    else:
        print(time.time()-now)  # XXX debug read excel
        check_sequence(df)
        _time = iter(df.Time)
        instr = iter(df.Instrument)
        command = iter(df.Command)
        args = iter(df.Argument)
        lenght = df.__len__()
        return lenght, _time, instr, command, args


def check_sequence(df: pd.DataFrame):
    # return
    try:
        _time = df.Time.copy()
        assert (_time >= 0).all(), (
            f"All value in 'Time' must be positive or equal to 0\n"
            f"Check index {(_time.index[(_time < 0)]+2).tolist()}")
        instr = df.Instrument.str.lower().copy()
        instr_check = instr.isin(instr_dict)
        assert (instr_check).all(), (
            f"All value in 'Instrument' must be in {instr_dict.keys()}\n"
            f"Check index {(instr.index[~instr_check]+2).tolist()}")
        command = df.Command.copy()
        command_err = []
        for i in range(command.__len__()):
            if instr[i] == "sleep":
                continue
            elif instr[i] == "armxl":
                if command[i] not in instr_dict.get(instr[i]):
                    command_err.append(i+2)
            elif command[i] not in instr_dict.get(instr[i]).COMMAND:
                command_err.append(i+2)
        if len(command_err) > 0:
            raise AssertionError("Instrument and Command do not match\n"
                                 f"Check index {command_err}")
        args = df.Argument.copy()
        args_err = []
        for i in range(args.__len__()):
            if instr[i] == "sleep":
                continue
            len_args = len(args[i].split()) if args[i] != "-" else 0
            if instr[i] == "armxl":
                if len_args != instr_dict.get(instr[i])[command[i]]:
                    args_err.append(i+2)
                continue
            f = getattr(instr_dict.get(instr[i]), command[i])
            len_d = len(f.__defaults__) if f.__defaults__ != None else 0
            if not f.__code__.co_argcount - len_d - 1 <= len_args <= f.__code__.co_argcount - 1:
                args_err.append(i+2)
  
    except Exception as e:
        title = "Errore FILE"
        message = "Errore colonne del file di comando"
        show_error(title, message, e)
    # TODO creare dizionario strumento, comando, parametro e fare check
    # df.v.apply(float.is_integer).all()
    pass


def show_error(title: str, message: str, e: Exception):
    messagebox.showerror(title, message + f"\n{str(e)}")


def to_json(df):
    return
    with open("sample.json", "w") as outfile:
        # sample_records
        df.to_json(outfile, orient='records', indent=4)
        # records value
        df.to_json(outfile, orient='values',indent=4)


if __name__ == "__main__":
    get_data()
