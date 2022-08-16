import sys
import time
from os import path
from tkinter import messagebox

import pandas as pd
import yaml

from .Chamber import ACS_Discovery1200
# from .Connection import Charger
from .other_SCPI import CHROMA, HP6032A, ITECH, MSO58B

USER_SEQUENCE_DIR = (f"{path.abspath(__file__).split('api')[0]}"
                     "api/predefine_sequence/")
instr_dict = {
    "dc_source": ITECH,
    "ac_source": CHROMA,
    "powersupply": HP6032A,
    "clim_chamber": ACS_Discovery1200,
    # FIXME default command for ARES, not based on library or Charger class
    "armxl": {"set_voltage_and_power.sh": 2,
              "start_charge_session.sh": 0,
              "stop_charge_session.sh": 0,
              "set_power.sh": 1,
              "set_reactive.sh": 1},
    "oscilloscope": MSO58B,
    "sleep": ["sleep", "-"],
    "sequence": USER_SEQUENCE_DIR
    }


def get_data(all_data=False, filename: str = "command.xlsx", logger=None):
    now = time.time()  # XXX debug read excel
    filepath = path.dirname(path.dirname(path.realpath(__file__)))
    try:
        if filename.endswith(".xlsx"):
            df = pd.read_excel(
                        f"{filepath}/{filename}",  # real file
                        # f"{filepath}/command_debug.xlsx",  # XXX debug, change to real file_name # noqa: E501
                        engine="openpyxl",
                        sheet_name="SequenceConfig",
                        usecols=["Time", "Instrument", "Command", "Argument"],
                        header=0,
                        dtype={"Time": int,
                               "Instrument": str,
                               "Command": str,
                               "Argument": str}
                        )
        elif filename.endswith(".json"):
            raise NotImplementedError  # TODO read json
        df.Command = df.Command.str.strip()
    except Exception as e:
        title = "Errore lettura FILE EXCEL"
        message = "Errore sui 'tipi' dei valori sulle colonne"
        if logger:
            logger.error(message)
        show_error(title, message, e)
        sys.exit()
    else:
        print(time.time()-now)  # XXX debug read excel
        if logger:
            logger.debug("Checking sequence")
        check_sequence(df, logger)  # check new write test sequence
        if logger:
            logger.debug("Adding basic sequence")
        df = add_sequence(df, logger)  # add base sequence
        _time = iter(df.Time)
        instr = iter(df.Instrument)
        command = iter(df.Command)
        args = iter(df.Argument)
        if all_data:
            return df
        else:
            return df, _time, instr, command, args


def add_sequence(df: pd.DataFrame, logger) -> pd.DataFrame:
    try:
        sequence_df = df[df.Instrument == "Sequence"].copy()
        if sequence_df.__len__() == 0:
            return df

        def f(index, name):
            path_ = USER_SEQUENCE_DIR + f"{name}.yaml"
            with open(path_, "r") as f:
                sq = pd.DataFrame(yaml.safe_load(f))
            return (index, sq)

        sq_list = [
            f(x, y) for x, y in zip(sequence_df.index, sequence_df["Command"])
            ]

        new_df = df.copy()
        for i, sq_cmd in sq_list:
            if i == 0:
                new_df = pd.concat([sq_cmd, new_df.loc[i+1:]])
            elif i == df.index[-1]:
                new_df = pd.concat([new_df.loc[:i-1], sq_cmd])
            else:
                new_df = pd.concat([new_df.loc[:i-1], sq_cmd, new_df.loc[i+1:]])

        return new_df.reset_index(drop=True)
    
    except Exception as e:
        title = "Base Sequence Error"
        message = "Errore adding SEQUENCE"
        if logger:
            logger.error(message)
        show_error(title, message, e)
        raise e        


def check_sequence(df: pd.DataFrame, logger):
    try:
        # check time
        _time = df.Time.copy()
        assert (_time >= 0).all(), (
            f"All value in 'Time' must be positive or equal to 0\n"
            f"Check index {(_time.index[(_time < 0)]+2).tolist()}")
        # check instrument
        instr = df.Instrument.str.lower().copy()
        instr_check = instr.isin(instr_dict)
        assert (instr_check).all(), (
            f"All value in 'Instrument' must be in {list(instr_dict.keys())}\n"
            f"Check index {(instr.index[~instr_check]+2).tolist()}")
        # check command for instrument
        command = df.Command.copy()
        command_err = []
        for i in range(command.__len__()):
            if instr[i] == "sleep":
                continue
            elif instr[i] == "sequence":
                if not path.exists(USER_SEQUENCE_DIR + f"{command[i]}.yaml"):
                    command_err.append(i+2)
            elif instr[i] == "armxl":
                if command[i] not in instr_dict.get("armxl"):
                    command_err.append(i+2)
            elif command[i] not in instr_dict.get(instr[i]).COMMAND:
                command_err.append(i+2)
        if len(command_err) > 0:
            raise AssertionError("Instrument and Command do not match\n"
                                 f"Check index {command_err}")
        # check argument lenght for command
        args = df.Argument.copy()
        args_err = []
        for i in range(args.__len__()):
            if instr[i] in ["sleep", "sequence"]:
                continue
            len_args = len(args[i].split()) if args[i] != "-" else 0
            if instr[i] == "armxl":
                if len_args != instr_dict.get("armxl")[command[i]]:
                    args_err.append(i+2)
                continue
            f = getattr(instr_dict.get(instr[i]), command[i])
            len_d = len(f.__defaults__) if f.__defaults__ is not None else 0
            if not f.__code__.co_argcount - len_d - 1 <= len_args <= f.__code__.co_argcount - 1:
                args_err.append(i+2)

    except Exception as e:
        title = "Errore FILE"
        message = "Errore colonne del file di comando"
        if logger:
            logger.error(message)
        show_error(title, message, e)
        raise e
    # TODO creare dizionario strumento, comando, tipo parametro e fare check
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
        df.to_json(outfile, orient='values', indent=4)


if __name__ == "__main__":
    get_data()
