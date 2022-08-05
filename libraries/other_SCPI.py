import datetime
import logging
import time
from typing import Callable, Iterable, Literal, Type, Union

import numpy as np
import pyvisa

_logger = logging.getLogger()


class Instrument:
    # FIXME Potrei sostituire tutti i self._instrument.write con self.write_command. Idem per query e read # noqa: E501
    """Generic Instrument Class"""

    def __init__(self) -> None:
        self._instrument: pyvisa.resources.MessageBasedResource = None
        self.alias = None
        self.nameid = None
        self.connection = False

    def __str__(self) -> str:
        return f"Instrument string({self._instrument})"

    def connect(self, id_string: str):
        """Si connette allo strumento\n
        Args:
            id_string (str): stringa di connessione strumento
            (GPIB, USB, TCPIP, ...)"""
        try:
            self._instrument = pyvisa.ResourceManager(
                ).open_resource(id_string)
            self.connection = True
            _logger.debug(f"instrument at {id_string} connected")
            return True, None
        except pyvisa.Error as e:
            return False, e

    def config(self):  # vuoto
        """Comandi da effettuare subito dopo connessione"""
        raise NotImplementedError("Comando da sovrascrivere")
        # FIXME potrei mettere queste tre righe perchè presenti in tutti gli
        # strumenti e chiamare super
        # self.set_setup(self.setup_option)
        # self.set_data_configuration(self.dataconfig)
        # _logger.debug(f"{self._instrument}: config done")

    def ResetConfig(self):  # vuoto
        """Comandi da effettuare subito dopo connessione"""
        raise NotImplementedError("Comando da sovrascrivere")

    def check_error(self):  # vuoto
        """Check INST error e do something"""
        raise NotImplementedError("Comando da sovrascrivere")

    def set_terminator(self):  # vuoto
        """Setta carattere terminatore sia in scrittura che in lettura"""
        raise NotImplementedError("Comando da sovrascrivere")

    def set_datetime(self):  # vuoto
        """Imposta data e ora attuale nello strumento"""
        raise NotImplementedError("Comando da sovrascrivere")

    def set_setup(self, setuo_option):  # vuoto
        """Configura Impostazioni di setup\n
        Args:
            setup_option (dict): dizionario delle impostazioni"""
        raise NotImplementedError("Comando da sovrascrivere")

    def set_data_configuration(self, dataconfig):  # vuoto
        """Imposta lo strumento al fine di effettuare le misurazioni volute\n
        Args:
            dataconfig (dict): dizionario delle misure"""
        raise NotImplementedError("Comando da sovrascrivere")

    def get_data(self, typemod):  # vuoto
        """Legge le misure dello strumento"""
        raise NotImplementedError("Comando da sovrascrivere")

    def close(self):
        """Chiude la connessione con lo strumento"""
        self._instrument.close()
        _logger.debug(f"Closed {self._instrument}")

    def get_idn(self):
        """Lettura Id Strumento"""
        tempid = self._instrument.query("*IDN?")
        name = self._instrument.resource_info.alias
        self.alias = name
        self.nameid = tempid
        return tempid

    def set_cls(self):
        """This command clears all status register (ESR, STB, error queue)"""
        _logger.debug(f"Clear {self._instrument} error")
        return self._instrument.write("*CLS")

    def set_rst(self):
        """Comando di reset ai valori dafault"""
        _logger.debug(f"Reset {self._instrument} error")
        return self._instrument.write("*RST")

    def set_calibration(self):
        """Comando di avvio calibrazione generico (SHIFT+ESC)"""
        return self._instrument.write("*CAL?")

    def set_wai(self):
        """Comando di attesa generico"""
        return self._instrument.write("*WAI")

    def launch_test(self):  # da completare
        """Autotest dello strumento"""
        raise NotImplementedError("Instrument: launch_test not implemented")
        # get attual timeout
        self._instrument  # set timeout 50000ms
        try:
            result = self._instrument.query("*TST?")
            if result:
                return "Self-Test not successful"
            else:
                return "Self-Test successful"
        except Exception:
            raise Exception("TestError")
        finally:
            # set the previus timeout
            pass

    def set_timeout(self, timeout_value: float | None):
        """Setta il valore di timeout\n
        Args:
            timeout_value (int | None): se '0' equivale a istantaneo;
            se 'None' equivale a infinito; altrimenti valore passato (ms)"""
        if timeout_value is None:
            timeout_value = float("+inf")
        self._instrument.timeout = timeout_value

    def get_timeout(self) -> float:
        """Restituisce il valore di timeout\n
        Returns:
            int: valore del timeout in ms"""
        return self._instrument.timeout

    def write_command(self, command: str) -> int:
        """Generic write command\n
        Args:
            command (str): comando SCPI
        Returns:
            int: risposta byte strumento"""
        return self._instrument.write(command)

    def query_command(self, command):
        """Generic query command\n
        Args:
            command (str): comando SCPI
        Returns:
            str: risposta strumento"""
        return self._instrument.query(command)

    def read_command(self, command):
        """Generic read command\n
        Args:
            command (str): comando SCPI
        Returns:
            str: risposta strumento"""
        return self._instrument.read(command)

    # decorator for retry function and wait completation.
    # NEW FEATURE Maybe for get data functions
    '''def retry(
        self,
        attemp: int = 1,
        errors: tuple[Type[Exception], ...] = (Exception,),
        **fkwargs):
        """Wrap functions for retry functions n 'attemp' if catch 'errors'
        during execution with time delay between attemps\n
        Args:
            attemp (int, optional): attemp to try. Defaults to 1.
            errors (tuple[Type[Exception], ...], optional): errors to handle.
            Defaults to (Exception,).
            delay (float, optional): time delay between attemps.
            Defaults to 0.\n
        Returns:
            Any: return wrapper
        """
        logger = fkwargs.get('logger', logging.getLogger())

        def _decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                for run in range(attemp):
                    try:
                        return func(*args, **kwargs)
                    except errors as e:
                        text = traceback.format_exc()
                        logger.warning(f"Run: {run+1},"
                                       f"Error class: {e.__class__}")
                        self.set_wai()
                logger.error(f"After {run+1} run, function continue to fail\n"
                            f"{text}")
              return wrapper
          return _decorator'''


class ITECH(Instrument):
    """It is because the channel 1 is the default channel for SOURce language
    node. On the other hand, if you want to refer to channel 2, "SOURce2" or
    "SOUR2" must be used in the program line.

    <NR1>: represents an integer value, such as 273;
    <NR2>: represents a real number in floating-point format, such as .273;
    <NR3>: represents a real number in scientific notation, such as 2.73E+2;
    <Nrf>: The extensible form includes <NR1>, <NR2> and <NR3>;
    <Nrf+>: The extensible decimal form includes <Nrf>, MIN, MAX and
    DEF. MIN and MAX are the minimum and maximum finite number. Within
    the range of the parameter definition, DEF is the default of the
    parameter."""
    typeOfInstrument = "Electronic Load"
    manufactor = "Itech Electronic"
    _setup_option = {  # first is default value
        'function': ('voltage', 'current'),
        'mode': ('fixed', 'list', 'battery', 'solar', 'carprofile'),
    }
    TIMESTEP = 0.5

    def __init__(self, setup: dict = {}, dataconfig: dict = {}):
        super().__init__()
        self._setup = setup
        self._dataconfig = dataconfig

    @property
    def setup(self):
        return self._setup_option

    @setup.setter
    def setup(self, value: dict):
        assert isinstance(value, dict)
        self._setup_option = value

    @property
    def dataconfig(self):
        return self._dataconfig

    @dataconfig.setter
    def dataconfig(self, value: dict):
        assert isinstance(value, dict)
        self._dataconfig = value

    def set_terminator(self) -> str:
        """Setta carattere terminatore sia in scrittura che in lettura"""
        self._instrument.read_termination = "\n"
        self._instrument.write_termination = "\n"
        return "read_terminator:\t \\n\nwrite_terminator:\t \\n"

    # ----- Configuration function ----- #
    def ResetConfig(self):
        """Reset e configura strumento"""
        self.set_cls()
        self.set_rst()
        self.get_idn()
        self.set_terminator()

        self.config()

    def config(self):
        """Configurazione setup e measurement"""
        self.set_setup(self.setup)

    def save_config(self, n: int):
        assert isinstance(n, int) and 0 <= n <= 9
        self._set_sav(n)

    def load_config(self, n: int):
        assert isinstance(n, int) and 0 <= n <= 9
        self._get_sav(n)

    def _set_sav(self, n: int):
        return self._instrument.write(f"*SAV {n}")

    def _get_sav(self, n: int):
        return self._instrument.read(f"*RCL {n}")

    # ----- function ITECH ----- #
    def set_output(self, state: bool | Literal['on', 'off']):
        if isinstance(state, bool):
            state = int(state)  # boolean to 0 1
        self._instrument.write(f'OUTPut {state}')

    def set_function(self, value: Literal["voltage", "current"] = 'voltage'):
        self._instrument.write(f"FUNCtion {value}")

    def set_mode(self, value: str = 'fixed'):
        self._instrument.write(f"FUNCtion:MODE {value}")

    def __gradient_setpoint(self, target: Callable,
                            values: Iterable, timer: float):  # VERIFY gradient
        n_step = len(values)
        start = time.time()
        for i in range(0, n_step):
            now = time.time()
            target(values[i])
            while (time.time() <= (now + self.TIMESTEP) and
                   (time.time() - start) < timer):
                continue

    # # --- cc mode --- # #
    def set_current(self, value: int | float,
                    time_to_set: None | float = None):  # VERIFY time_to_set
        if time_to_set:
            if time_to_set <= 1:  # condition to set immediate final value
                self._instrument.write(f'CURRent {value}')
            else:
                import threading

                assert isinstance(time_to_set, float | int)
                start_value = self._instrument.query_ascii_values("CURR?")
                target = self.set_current
                step = (value - start_value) / (time_to_set / self.TIMESTEP)
                values = np.arange(start_value, value, step).tolist() + [value]
                t = threading.Thread(target=self.__gradient_setpoint,
                                     args=(target, values, time_to_set),
                                     daemon=True)
                t.start()
        else:
            self._instrument.write(f'CURRent {value}')

    def set_v_limit(self, v_neg: float, v_pos: float):
        """Setta i valori limiti di tensione per la CC mode\n
        Args:
            values (tuple[float, float]): coppia valore Vl-Vh
        """
        self._instrument.write(f'VOLTage:LIMit:NEGative {v_neg}')
        self._instrument.write(f'VOLTage:LIMit:POSitive {v_pos}')

    # # --- cv mode --- # #
    def set_voltage(self, value: int | float, time_to_set: None | int = None):  # VERIFY time_to_set # noqa: E501
        if time_to_set:
            if time_to_set <= 1:  # condition to set immediate final value
                self._instrument.write(f'CURRent {value}')
            else:
                import threading

                assert isinstance(time_to_set, float | int)
                start_value = self._instrument.query_ascii_values("VOLT?")
                target = self.set_voltage
                step = (value - start_value) / (time_to_set / self.TIMESTEP)
                values = np.arange(start_value, value, step).tolist() + [value]
                t = threading.Thread(target=self.__gradient_setpoint,
                                     args=(target, values, time_to_set),
                                     daemon=True)
                t.start()
        else:
            self._instrument.write(f'VOLTage {value}')

    def set_c_limit(self, i_neg: float, i_pos: float):
        """Setta i valori limiti di corrente per la CV mode\n
        Args:
            values (tuple[float, float]): coppia valore (I-,I+)
        """
        self._instrument.write(f'CURRent:LIMit:NEGative {i_neg}')
        self._instrument.write(f'CURRent:LIMit:POSitive {i_pos}')

    # def get_function(self):
    #     return self._instrument.query(f"FUNCtion?")

    # ----- setup and reading ----- #
    def read_measure(self) -> tuple[str, str, str]:
        # v, c, p, _, _ = self._instrument.query("MEASure:SCALar?")
        v, c, p, _, _ = self._instrument.query("FETch:SCALar?")
        return v, c, p

    # def set_setup(self, setup:dict): # NEW FEATURE tutte impostazioni setup ITECH
    #   """Impostazioni di setup\n
    #   Args:
    #       setup_option (dict): dizionario delle impostazioni"""
    #   self._instrument.write(f"FUNCtion: {setup.get('function', 'voltage')}")
    #   self._instrument.write(f"FUNCtion:MODE {setup.get('mode', 'fixed')}")
    COMMAND = ["set_output", "set_function", "set_current", "set_v_limit",
               "set_voltage", "set_c_limit"]


class CHROMA(Instrument):
    """
    <NR1>: represents an integer value, such as 273;
    <NR2>: represents a real number in floating-point format, such as .273;
    <NR3>: represents a real number in scientific notation, such as 2.73E+2;
    """
    typeOfInstrument = "Grid Simulator"
    manufactor = "Chroma Systems Solutions"
    # _setup_option = {  # first is default value
    #     "function": ("voltage", "current"),
    #     "mode": ("fixed", "list", "battery", "solar", "carprofile"),
    # }
    measure = {  # non tutte le misure possibili
        **dict.fromkeys(("frequency", "freq", "FREQUENCY", "F"), "frequency"),
        **dict.fromkeys(("current", "C", "curr", "corrente"), "current"),
        **dict.fromkeys(("voltage", "V", "volt", "voltaggio"), "voltage"),
        **dict.fromkeys(("ac", "alternate", "alternata", "AC"), "AC"),
        **dict.fromkeys(("dc", "continuos", "continua", "DC"), "DC"),
        **dict.fromkeys(("rms", "RSM", "ACDC", "acdc"), "ACDC"),
        **dict.fromkeys(("power", "P", "potenza"), "power"),
        **dict.fromkeys(("apparent", "apparente", "S"), "apparent"),
        **dict.fromkeys(("reactive", "reattiva", "Q"), "reactive"),
    }

    def __init__(self, setup: dict = {}, dataconfig: dict = {}):
        super().__init__()
        self._setup = setup
        self._dataconfig = dataconfig

    @property
    def setup(self):
        return self._setup_option

    @setup.setter
    def setup(self, value: dict):
        assert isinstance(value, dict)
        self._setup_option = value

    @property
    def dataconfig(self):
        return self._dataconfig

    @dataconfig.setter
    def dataconfig(self, value: dict):
        assert isinstance(value, dict)
        self._dataconfig = value

    def set_terminator(self) -> str:
        """Setta carattere terminatore sia in scrittura che in lettura"""
        self._instrument.read_termination = "\n"
        self._instrument.write_termination = "\n"
        return "read_terminator:\t \\n\nwrite_terminator:\t \\n"

    # ----- Configuration function ----- #
    def ResetConfig(self):
        """Reset e configura strumento"""
        self.set_cls()
        self.set_rst()
        self.get_idn()
        self.set_terminator()

        self.config()

    def config(self):
        """Configurazione setup e measurement"""
        self._instrument.write("INSTrument:COUPle ALL")  # setup for all phase
        self.set_setup(self.setup)
        # self.set_data_configuration(self.dataconfig)

    # ----- function CHROMA ----- #
    def set_output(self, state: bool | Literal["on", "off"]):
        if isinstance(state, bool):
            if state:
                state = "ON"
            else:
                state = "OFF"
        self._instrument.write(f"OUTPut {state}")

    def set_frequency(self, value: float):
        if isinstance(value, int):
            value = float(value)
        self._instrument.write(f"FREQuency {value}")

    def set_voltage(self, value: float, mode: Literal["ac", "dc"] = "ac"):
        if isinstance(value, int):
            value = float(value)

        if mode in ("ac", "alternate", "alternata", "AC"):
            self._instrument.write(f"VOLTage:AC {value}")
        elif mode in ("dc", "continuos", "continua", "DC"):
            self._instrument.write(f"VOLTage:DC {value}")

    def set_phase(self, mode: Literal["1", "3"], *args):  # TODO phase options
        pass

    # ----- predefine CHROMA ----- #
    def europe_grid(self):
        self.set_frequency(50.0)
        self.set_voltage(230.0, "ac")

    def usa_grid(self):
        self.set_frequency(60.0)
        self.set_voltage(277.0, "ac")

    # ----- setup and reading ----- #
    def read_measure(self, measure: str, *args: str) -> str:
        meas = self.measure.get(measure)
        for i in args:
            options = self.measure.get(i, None)
            if options:
                meas += f":{options}"
        # out = self._instrument.query(f"MEASure:{meas}?"")
        out = self._instrument.query(f"FETch:{meas}?")
        return out

    def status_measure(self):
        frequency = []
        voltage = []
        current = []
        power = []
        pf = []
        for i in range(1, 4):
            self._instrument.write(f"INSTR:NSEL {i}")
            out = self._instrument.query_ascii_values("FETCH:FREQ?")
            frequency.append(out)
            out = self._instrument.query_ascii_values("FETCH:VOLTAGE:ACDC?")
            voltage.append(out)
            out = self._instrument.query_ascii_values("FETCH:CURRENT:ACDC?")
            current.append(out)
            out = self._instrument.query_ascii_values("FETCH:POWER:AC?")
            power.append(out)
            out = self._instrument.query_ascii_values("FETCH:POWER:AC:PFAC?")
            pf.append(out)
        return frequency, voltage, current, power, pf

    COMMAND = ["set_output", "set_frequency", "set_voltage",
               "europe_grid", "usa_grid"]


class HP6032A(Instrument):

    def __init__(self, setup: dict = {}, dataconfig: dict = {}) -> None:
        super().__init__()
        self._setup = setup
        self._dataconfig = dataconfig

    @property
    def setup(self):
        return self._setup_option

    @setup.setter
    def setup(self, value: dict):
        assert isinstance(value, dict)
        self._setup_option = value

    @property
    def dataconfig(self):
        return self._dataconfig

    @dataconfig.setter
    def dataconfig(self, value: dict):
        assert isinstance(value, dict)
        self._dataconfig = value

    def set_terminator(self) -> str:
        """Setta carattere terminatore sia in scrittura che in lettura"""
        self._instrument.read_termination = "\n"
        self._instrument.write_termination = "\n"
        return "read_terminator:\t \\n\nwrite_terminator:\t \\n"

    # ----- Configuration function ----- #
    def ResetConfig(self):
        """Reset e configura strumento"""
        self.set_cls()
        self.set_rst()
        self.get_idn()
        self.set_terminator()

        self.config()

    def config(self):
        """Configurazione setup e measurement"""
        self.set_setup(self.setup)
        # self.set_data_configuration(self.dataconfig)

    # ----- function HPPowerSupply ----- #
    def set_current(self, value: float | None = None):
        if value is None:
            return self._instrument.query(":CURR?")
        else:
            self._instrument.write(f":CURR {value}")

    def set_voltage(self, value: float | None = None):
        if value is None:
            return self._instrument.query(":VOLT?")
        else:
            self._instrument.write(f":VOLT {value}")

    def set_output(self, state: bool | Literal["on", "off"]):
        if isinstance(state, str):
            if state in ("on", "ON"):
                state = 1
            else:
                state = 0
        self._instrument.write(f"OUTPUT {int(state)}")

    # ----- predefine HPPowerSupply ----- #
    # ----- status and reading ----- #
    def read_measure(self, mode: Literal["current", "voltage"]):
        if mode == "current":
            return self._instrument.query("MEAS:CURR?")
        elif mode == "voltage":
            return self._instrument.query("MEAS:VOLT?")
        else:
            raise KeyError("misura non disponibile\nSeleziona tra"
                           " 'current' o 'voltage'")
    # ----- all COMMAND -----#
    COMMAND = ["set_output", "set_current", "set_voltage"]


class MSO58B(Instrument):  # VERIFY try this instrument
    typeOfInstrument = "Oscilloscope"
    manufactor = "Tektronik"
    measure = None  # NEW FEATURE measure options
    # SOCKET port is 4000

    # ACTONEVent:MASKFail:ACTION:SAVEIMAGe:STATE Save a screen capture when a
    #   mask test fails.
    # ACTONEVent:MASKHit:ACTION:SAVEIMAGe:STATE Saves a screen capture when a
    #   mask hit occurs.

    # ACQuire:STATE Starts, stops, or returns acquisition state.

    # SAVEONEVent:FILEDest Sets or queries the file path.
    # SAVEONEVent:FILEName Sets or queries the file name without the extension.
    # SAVEONEVent:IMAGe:FILEFormat Sets or returns the file extension
    #   (png, jpg, bmp).

    # FILESystem:READFile Copies the named file to the interface.

    # SAVe:IMAGe Saves a capture of the screen contents to the specified
    #   image file.

    # SAVEON:FILE:DEST Sets or queries the location where files are saved.
    # SAVEON:FILE:NAME Sets or queries the file name to use when
    #   SAVEON:TRIGer is ON.
    # SAVEON:IMAGe:FILEFormat Sets or queries the file format to be used for
    #   saved image files.
    # SAVEON:IMAGe Sets or queries whether to save a screen capture when
    #   a trigger occurs.
    # SAVEON:TRIGger Sets or queries whether to save a file when
    #   a trigger occurs.

    # *OPC Generates the operation complete message in the standard event
    #   status register when all pending operations are finished Or
    #   returns “1” when all current operations are finished.

    def __init__(self, setup: dict = {}, dataconfig: dict = {}):
        super().__init__()
        self._setup = setup
        self._dataconfig = dataconfig

    @property
    def setup(self):
        return self._setup_option

    @setup.setter
    def setup(self, value: dict):
        assert isinstance(value, dict)
        self._setup_option = value

    @property
    def dataconfig(self):
        return self._dataconfig

    @dataconfig.setter
    def dataconfig(self, value: dict):
        assert isinstance(value, dict)
        self._dataconfig = value

    def set_terminator(self) -> str:
        """Setta carattere terminatore sia in scrittura che in lettura"""
        self._instrument.read_termination = "\n"
        self._instrument.write_termination = "\n"
        return "read_terminator:\t \\n\nwrite_terminator:\t \\n"

    # ----- Configuration function ----- #
    def ResetConfig(self):
        """Reset e configura strumento"""
        self.set_cls()
        self.set_rst()
        self.get_idn()
        self.set_terminator()

        self.config()

    def config(self):  # FIXME if add some default command
        """Configurazione setup e measurement"""
        self.set_setup(self.setup)
        # self.set_data_configuration(self.dataconfig)

    # ----- function MSO58B ----- #
    # ----- predefine MSO58B ----- #
    def save_screen(self, filepath: str = "default"):
        dt = datetime.datetime.now()
        if filepath == "default":
            filepath = dt.strftime("OSC/MSO58B_%Y%m%d-%H%M%S.png")
        else:
            filepath = dt.strftime(f"{filepath}_%Y%m%d-%H%M%S.png")
        self.write_command('SAVE:IMAGe \"C:/Temp.png\"')
        self.query_command("*OPC?")
        self.write_command('FILESystem:READFile \"C:/Temp.png\"')
        imgData = self._instrument.read_raw(1024*1024)

        with open(filepath, "wb") as file:
            file.write(imgData)

        self.write_command('FILESystem:DELEte \"C:/Temp.png\"')

    # ----- status and reading ----- #
    # ----- all COMMAND -----#
    COMMAND = ["save_screen"]


instrument: dict[str, Union[Type[ITECH],
                            Type[CHROMA],
                            Type[HP6032A],
                            Type[MSO58B]]] = {
                                                "ITECH": ITECH,
                                                "CHROMA": CHROMA,
                                                "HP6032A": HP6032A,
                                                "MSO58B": MSO58B
                                                }


# if __name__ == "__main__":
#     osc = MSO58B()
#     osc.connect("TCPIP0::192.168.0.106::inst0::INSTR")
    
#     osc.save_screen("C:\\Users\\ITSAGON\\image")
