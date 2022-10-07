# from os import path

from os import path

import pandas as pd
import yaml

FILEPATH = "./command_debug.xlsx"
SHEEET_NAME = "sequence"
SEQUENCE_DIR = (f"{path.dirname(path.abspath(__file__))}"
                "/predefine_sequence/")
SEQUENCE_NAME = "stop_all2"
# MODE = "Ares"

try:
    df = pd.read_excel(
                FILEPATH,
                engine="openpyxl",
                sheet_name=SHEEET_NAME,
                usecols=["Time", "Instrument", "Command", "Argument"],
                header=0,
                dtype={"Time": int,
                       "Instrument": str,
                       "Command": str,
                       "Argument": str}
                )
    df.Command = df.Command.str.strip()
    # data = df.to_json(indent=4, orient="index")

    with open(f"{SEQUENCE_DIR+SEQUENCE_NAME}.yaml", "w") as f:
        yaml.dump(df.to_dict(orient="records"), f, sort_keys=False)
    with open(f"{SEQUENCE_DIR+SEQUENCE_NAME}.yaml", "r") as f:
        print(f"La sequenza {SEQUENCE_NAME} è stata creata con successo\n\n",
              pd.DataFrame(yaml.safe_load(f)))

except Exception as e:
    print("Errore durante la creazione della sequenza\n\n")
    print(e)

finally:
    input("\nInvio per terminare... ")
