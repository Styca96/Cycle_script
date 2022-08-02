#!/usr/bin/env python
"""Class for all Device that speak with ModBus standard"""
# import functools
# from Error import NotAvailable
import time
from typing import Annotated, Type, TypedDict, Union

from numpy import linspace
from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from pymodbus.constants import Endian
from pymodbus.exceptions import ConnectionException
from pymodbus.payload import BinaryPayloadBuilder, BinaryPayloadDecoder


class Reading_address(TypedDict):
    measure: dict[str, int]
    setpoint: dict[str, int]
    user_setting: dict[str, tuple[int, int]]
    device_setting: dict[str, tuple[int, int]]


class Writing_address(TypedDict):
    run_setting: dict[str, tuple[int, int]]
    setpoint: dict[str, int]


class ACS_Discovery1200(ModbusClient):
    """Classe per interfacciarsi con ACS_Discovery1200"""

    reading_area: Reading_address = {  # indirizzi dei registri leggibili
        # name: address
        "measure": {
            "dry bulb": 0,
            "PT100 suction": 0,
            "wet bulb": 2,
            "PT100 discharge": 2,
            "PT100.0": 4,
            "PT100.1": 6,
            "PT100.2": 8,
            "PT100.3": 10,
            "Low stage sunction pressure": 12,
            "LSSP": 12,
            "Low stage discharge pressure": 14,
            "LSDP": 14,
            "High stage sunction pressure": 16,
            "HSSP": 16,
            "High stage discharge pressure": 18,
            "HSDP": 18,
            "User analog input 0": 20,
            "User analog input 1": 22,
            "User analog input 2": 24,
            "User analog input 3": 26,
            "User analog input 4": 28,
            "User analog input 5": 30,
            "Capacitive probe": 30,
            "Temp": 32,
            "Rel Hum": 34,
            "Abs Hum": 36,
        },
        "setpoint": {
            "Temp": 77,
            "Temp_current": 79,
            "Temp_gradient": 81,
            "Hum": 83,
            "Hum_current": 85,
            "Hum_gradient": 87,
        },
        # name: address,bit
        "user_setting": {
            "run": (69, 0),
            "alarm reset": (69, 1),
            "enable temp": (69, 8),
            "enable hum": (69, 9),
            # 70,71,72
        },
        "device_setting": {
            "run": (73, 0),
            "alarm reset": (73, 1),
            "enable temp": (73, 8),
            "enable hum": (73, 9),
            # 74,75,76
        },
        # 'alarm': {
        # 64,65,66,67,68
        # },
    }
    writing_area: Writing_address = {  # indirizzi dei registri scrivibili
        # name: address,bit
        "run_setting": {
            "run": (500, 0),
            "alarm reset": (500, 1),
            "enable temp": (500, 8),
            "enable hum": (500, 9),
            # 501,502,503
        },
        # name: address
        "setpoint": {
            "Temp": 504,
            "Temp_gradient": 506,
            "Hum": 508,
            "Hum_gradient": 510,
        },
    }
    UNIT = 17  # indirizzo slave
    TEMP = (-75, 180)  # range di temperatura possibile
    GRADIENT = (-2.3, 4.5)  # not used, massimo gradientein discesa e salita
    DATA_OUTPUT = ['Chamber_Temp']

    def __init__(self, port: str, slave_address: int | None = None,
                 method='rtu', stopbit=1, bytesize=8, parity='N', timeout=1.5,
                 baudrate=9600, **kwargs):
        super().__init__(method, port=port, stopbit=stopbit, bytesize=bytesize,
                         parity=parity, timeout=timeout, baudrate=baudrate,
                         **kwargs)
        connection = self.connect()
        if connection is False:
            raise ConnectionException(f"Failed to connect[{self.__str__()}]")
        if slave_address:
            self.UNIT = slave_address
        self.temp_control = False
        self.hum_control = False

    def _check_connection(self):
        """Verifica se la connessione è attiva
        Returns:
            bool: True se attiva. False altrimenti
        """
        return self.is_socket_open()

    def __del__(self):
        self.close()

    def __str__(self):
        modbus = super().__str__()
        return f"Angelantoni ACS Discovery D1200 - {modbus}"

    # @classmethod   # to set class property, but instance writable
    @property
    # @functools.cache # to cache if is long to compute
    def measure(self):
        return list(self.reading_area["measure"].keys())

    @property
    def setpoint(self):
        return list(self.reading_area["setpoint"].keys())

    @property
    def settings(self):
        return list(self.reading_area["user_setting"].keys())

    # ----- Predefinite function ----- # FIXME mantenere il secondo bit (0-based) program mode ??? # noqa: E501
    def start_temp(self) -> bool:  # FIXME fare anche reset alarm?
        """Attiva il controllo di temperatura e comincia il controllo
            >>>N.B. il setpoint di temperatura deve essere settato\n
        Returns:
            bool: 'True' se presente un errore. 'False' altrimenti
        """
        # values = 00000001-00000001
        rr = self.write_registers(500, values=0x0101, unit=self.UNIT)
        self.temp_control = True
        return rr.isError()

    def start_hum(self) -> bool:  # FIXME fare anche reset alarm?
        """Attiva il controllo di umidità e comincia il controllo
            >>>N.B. il setpoint di umidità relativa deve essere settato\n
        Returns:
            bool: 'True' se presente un errore. 'False' altrimenti
        """
        # values = 00000010-00000001
        rr = self.write_registers(500, values=0x0201, unit=self.UNIT)
        self.hum_control = True
        return rr.isError()

    def start_temp_hum(self) -> bool:  # FIXME fare anche reset alarm?
        """Attiva il controllo di temperatura e umidità e comincia il controllo
            >>>N.B. il setpoint di temperatura e umidità deve essere settato\n
        Returns:
            bool: 'True' se presente un errore. 'False' altrimenti
        """
        # values = 00000011-00000001
        rr = self.write_registers(500, values=0x0301, unit=self.UNIT)
        self.temp_control = True
        self.hum_control = True
        return rr.isError()

    def stop_temp(self) -> bool:
        """Disattiva controllo temperatura della camera\n
        Returns:
            bool: 'True' se presente un errore. 'False' altrimenti
        """
        rr = self.__write_bit(500, 8, 0)
        self.temp_control = False
        return rr

    def stop_hum(self) -> bool:
        """Disattiva controllo umidità della camera\n
        Returns:
            bool: 'True' se presente un errore. 'False' altrimenti
        """
        rr = self.__write_bit(500, 9, 0)
        self.hum_control = False
        return rr

    def stop_temp_hum(self) -> bool:
        """Disattiva tutti i controlli della camera\n
        Returns:
            bool: 'True' se presente un errore. 'False' altrimenti
        """
        # values = 00000000-00000000
        rr = self.write_registers(500, values=0x0000, unit=self.UNIT)
        self.temp_control = False
        self.hum_control = False
        return rr.isError()

    def reset_alarm(self) -> bool:
        """Imposta a 1 l'alarm_reset della camera\n
        Returns:
            bool: 'True' se presente un errore. 'False' altrimenti
        """
        return self.__write_bit(500, 1, 1)

    # ----- Read Operation -----
    def read_measure(self, meas: str) -> tuple[bool, float]:
        """Restituisce il valore della misura scelta\n
        Args:
            meas (str): Misura da effettuare. A scelta tra quelle presenti in
            'measure'\n
        Raises:
            KeyError: se viene scelta una misura non presente\n
        Returns:
            tuple[bool, float]:
                bool: 'True' se presente un errore. 'False' altrimenti
                float: valore scritto nel registro
        """
        try:
            address = self.reading_area["measure"][meas]
        except KeyError:
            raise KeyError("Measure not present")
        return self.__read_float(address)

    def read_setpoint(self, meas: str) -> tuple[bool, float]:
        """Legge il tipo di setpoint impostato dall'utente\n
        Args:
            meas (str): setoint da leggere. A scelta tra quelli presenti in
            'setpoint'\n
        Raises:
            KeyError: se viene scelta una misura non presente\n
        Returns:
            tuple[bool, float]:
                bool: 'True' se presente un errore. 'False' altrimenti
                float: valore scritto nel registro
        """
        try:
            address = self.reading_area["setpoint"][meas]
        except KeyError:
            raise KeyError("Setpoint not present")
        return self.__read_float(address)

    def read_user_setting(self, meas: str) -> tuple[bool, bool]:
        """Legge il valore del bit correlato all'impostazione scelta\n
        Args:
            meas (str): impostazione da leggere. A scelta tra quelle presenti
            in 'settings'\n
        Raises:
            KeyError: se viene scelta una misura non presente\n
        Returns:
            tuple[bool, bool]:
                bool: 'True' se presente un errore. 'False' altrimenti
                bool: valore lettura
        """
        try:
            address, bit = self.reading_area["user_setting"][meas]
        except KeyError:
            raise KeyError("Setting not present")
        return self.__read_bit(address, bit)

    def __read_float(self, address: int) -> tuple[bool, float]:
        """Legge il registro selezionato più il seguente e restituisce un
        float\n
        Args:
            address (int): primo indirizzo da leggere\n
        Returns:
            tuple[bool, float]:
                bool: 'True' se presente un errore. 'False' altrimenti
                float: valore scritto nel registro
        """
        rr = self.read_holding_registers(address, 2, unit=self.UNIT)
        # ----- from 2*16bit to 32bit float
        decoder = BinaryPayloadDecoder.fromRegisters(rr.registers,
                                                     byteorder=Endian.Big,
                                                     wordorder=Endian.Big)
        rs = decoder.decode_32bit_float()
        return rr.isError(), rs

    def __read_bit(self, address: int, bit: Annotated[int, range(16)]
                   ) -> tuple[bool, bool]:
        """Legge il bit desiderato del registro scelto
        Args:
            address (int): indirizzo del registro
            bit (Annotated[int, range(16)]): quale bit leggere. 0-based, dal
            meno significativo\n
        Returns:
            tuple[bool, bool]:
                bool: 'True' se presente un errore. 'False' altrimenti
                bool: valore bit, 'True'==1, 'False'==0
        """
        rr = self.read_holding_registers(address, 1, unit=self.UNIT)
        decoder = BinaryPayloadDecoder.fromRegisters(rr.registers,
                                                     byteorder=Endian.Big,
                                                     wordorder=Endian.Big)
        rs = decoder.decode_bits()
        rs = decoder.decode_bits() + rs
        return rr.isError(), rs[bit]

    # ----- Write Operation -----
    def write_setpoint(self, meas: str, value: int | float,
                       time_to_set: None | int = None) -> bool:
        """Cambia il valore del setpoint desiderato\n
        Args:
            meas (str): setpoint da cambiare. A scelta tra quelli in 'setpoint'
            value (int | float): valore da impostare\n
            time_to_set (None | int, optional): Valore in minuti per arrivare
            alla temperatura voluta. Se espresso realizza uno pseudogradiente.
            Defaults to None.
        Raises:
            KeyError: se setpoint selezionato non presente
            ValueError: se valore passato non corretto\n
        Returns:
            bool: 'True' se presente un errore. 'False' altrimenti
        """
        try:
            if meas == "Temp current":
                meas = "Temp"
            elif meas == "Hum current":
                meas = "Hum"
            self.__validate(meas, value)
            address: int = self.writing_area["setpoint"][meas]
            # ---- gradient generator
            if time_to_set:
                import threading

                assert isinstance(time_to_set, int)
                if meas == "Hum":
                    meas = "Rel Hum"
                readed, start_value = self.read_measure(meas)
                if readed:
                    grad = threading.Thread(
                        target=self.__gradient_setpoint,
                        args=(address, value, time_to_set, start_value),
                        daemon=True,
                    )
                    grad.start()
        except KeyError:
            raise KeyError("Setpoint not present")
        except ValueError:
            raise ValueError("Valore fuori soglia")
        except AssertionError:
            raise AssertionError("Specificare un valore in minuti intero")

        return self.__write_float(address, value)

    def __gradient_setpoint(self, address: int, final_value: int | float,
                            time_to_set: int, start_value: float):
        """Approssima il gradiente con una funzione a gradini(pre) ed invia
        più setpoint intermedi alla macchina
        Args:
            address (int): indirizzo di scrittura del setpoint
            final_value (int | float): valore finale da raggiungere
            time_to_set (int): tempo in minuti in cui si vuole raggiungere il
            valore finale
            start_value (float): valore attuale della misura
        """
        step_setpoint = linspace(start_value, final_value, time_to_set + 1)
        for i in range(1, time_to_set + 1):
            now = time.time()
            self.__write_float(address, step_setpoint[i])
            while time.time() <= (now + 60) and i < (time_to_set):  # aspetta 60 secondi # noqa: E501
                continue

    def write_setting(self, meas: str, value: bool | int) -> bool:
        """Attiva o disattiva un'impostazione\n
        Args:
            meas (str): impostazione da modificare. A scelta tra quelle in
            'settings'
            value (bool | int): valore da scrivere. 0 se 'False' o '0'.
            1 altrimenti\n
        Raises:
            KeyError: se impostazione non presente
            ValueError: se valore non valido\n
        Returns:
            bool: 'True' se presente un errore. 'False' altrimenti
        """
        try:
            self.__validate(meas, value)
            address, bit = self.writing_area["run_setting"][meas]
        except KeyError:
            raise KeyError("Setting not present")
        except ValueError:
            raise ValueError("Valore non valido")
        return self.__write_bit(address, bit, value)

    def __write_float(self, address: int, value: int | float) -> bool:
        """Scrive un int o un float nel registro selezionato\n
        Args:
            address (int): indirizzo del registro
            value (int|float): valore da scrivere\n
        Returns:
            bool: 'True' se presente un errore. 'False' altrimenti
        """
        builder = BinaryPayloadBuilder(byteorder=Endian.Big,
                                       wordorder=Endian.Big)
        builder.add_32bit_float(value)
        payload = builder.to_registers()
        rw = self.write_registers(address, payload, unit=self.UNIT)
        return rw.isError()

    def __write_bit(self, address: int, bit: Annotated[int, range(16)],
                    value: bool | int) -> bool:
        """Scrive il valore nel singolo bit del registro selezionato\n
        Args:
            address (int): indirizzo del registro
            bit (Annotated[int, range(16)]): quale bit leggere. 0-based, dal
            meno significativo
            value (bool | int): valore da scrivere. 0 se 'False' o '0'.
            1 altrimenti\n
        Returns:
            bool: 'True' se presente un errore. 'False' altrimenti
        """
        rr = self.read_holding_registers(address, 1, unit=self.UNIT)
        _all = 0xFFFF
        _and = _all - 2**bit
        if value:
            _or = _all - _and
        else:
            _or = 0b0
        payload = (rr.registers[0] & _and) | _or
        rw = self.write_registers(address, values=payload, unit=self.UNIT)
        return rw.isError()

    # ----- other function -----
    @classmethod
    def __validate(cls, meas: str, value):
        """Controlla i valori in base alla misura\n
        Args:
            meas (str): misura
            value (_Any_): valore da associare alla misura\n
        Raises:
            ValueError: Se valore non valido per la misura
        """
        # NEW FEATURE control combinate Temp and Hum during humidity test(bulbo umido) and gradient # noqa: E501
        if meas == "Temp":
            if not cls.TEMP[0] < value < cls.TEMP[1]:
                raise ValueError
        elif meas == "Hum":
            if not 10 <= value <= 98:
                raise ValueError
        else:
            try:
                int(value)
            except Exception:
                raise ValueError

    def get_data(self) -> list[float]:
        """Get the value requested by test execution\n
        Returns:
            list[float]: lista temp
        """
        data = []
        for i in ["Temp"]:
            readed, value = self.read_measure(i)
            if readed is False:
                data.append(value)
            else:
                data.append(float("NaN"))
        return data

    COMMAND = ['start_temp', 'stop_temp', 'start_hum', 'stop_hum',
               'start_temp_hum', 'stop_temp_hum', 'write_setpoint']


class Sauter_PLC(ModbusClient):  # VERIFY da verificare funzionamento classe
    """Classe per interfacciarsi con PLC Sauter per le camere di prova vita"""

    UNIT = 1
    SUBUNIT = {  # NEW FEATURE add unit 6-9 se vengono aggiunte camere
        1: {
            "read": 10,
            "write": 11,
            "run": 54,
        },
        2: {
            "read": 16,
            "write": 17,
            "run": 55,
        },
        3: {
            "read": 27,
            "write": 31,
            "run": 56,
        },
        4: {
            "read": 34,
            "write": 39,
            "run": 57,
        },
        5: {
            "read": 50,
            "write": 52,
            "run": 58,
        },
    }
    DATA_OUTPUT = [f'Chamber_{i}_Temp' for i in list(SUBUNIT.keys())]

    def __init__(self, port: str, slave_address: int | None = None,
                 method='rtu', stopbit=1, bytesize=8, parity='N', timeout=2,
                 baudrate=57600, **kwargs):
        super().__init__(method, port=port, stopbit=stopbit, bytesize=bytesize,
                         parity=parity, timeout=timeout, baudrate=baudrate,
                         # handle_local_echo=True, # VERIFY yes or no?
                         **kwargs)
        connection = self.connect()
        if connection is False:
            raise ConnectionException(f"Failed to connect[{self.__str__()}]")
        if slave_address:
            self.UNIT = slave_address
        self.temp_control = {1: False, 2: False, 3: False, 4: False, 5: False}
        # self.hum_control = { 1:False, #NEW FEATURE if hum control is possible
        #                      2:False,
        #                      3:False,
        #                      4:False,
        #                      5:False
        #                      }

    def _check_connection(self):
        """Verifica se la connessione è attiva
        Returns:
            bool: True se attiva. False altrimenti
        """
        return self.is_socket_open()

    def __del__(self):
        self.close()

    def __str__(self):
        modbus = super().__str__()
        return f"Sauter PLC for LifeTest Chamber - {modbus}"

    # ----- Predefine function -----
    def start_temp(self, unit: int) -> bool:
        """Attiva il controllo di temperatura e comincia il controllo
            >>>N.B. il setpoint di temperatura deve essere settato\n
        Args:
            unit: unità da controllare
        Returns:
            bool: 'True' se presente un errore. 'False' altrimenti
        """
        register = self.SUBUNIT[unit]["run"]
        rr = self.write_register(register, values=0x0001, unit=self.UNIT)  # 1
        error = rr.isError()
        if not error:
            self.temp_control[unit] = True
        return error

    def stop_temp(self, unit: int) -> bool:
        """Disattiva controllo temperatura della camera\n
        Returns:
            bool: 'True' se presente un errore. 'False' altrimenti
        """
        register = self.SUBUNIT[unit]["run"]
        rr = self.write_register(register, values=0x0000, unit=self.UNIT)  # 1
        error = rr.isError()
        if not error:
            self.temp_control[unit] = False
        return error

    # NEW FEATURE if hum control is possible
    # def start_hum(self)->bool:
    #     """Attiva il controllo di umidità e comincia il controllo
    #         >>>N.B. il setpoint di umidità relativa deve essere settato\n
    #     Returns:
    #         bool: 'True' se presente un errore. 'False' altrimenti
    #     """
    #     # 00000010-00000001
    #     rr = self.write_registers(500, values=0x0201, unit=self.UNIT)
    #     self.hum_control = True
    #     return rr.isError()

    # def start_temp_hum(self)->bool:
    #     """Attiva il controllo di temperatura e umidità e comincia il controllo # noqa: E501
    #         >>>N.B. il setpoint di temperatura e umidità deve essere settato\n # noqa: E501
    #     Returns:
    #         bool: 'True' se presente un errore. 'False' altrimenti
    #     """
    #     # 00000011-00000001
    #     rr = self.write_registers(500, values=0x0301, unit=self.UNIT)
    #     self.temp_control = True
    #     self.hum_control = True
    #     return rr.isError()

    # def stop_hum(self)->bool:
    #     """Disattiva controllo umidità della camera\n
    #     Returns:
    #         bool: 'True' se presente un errore. 'False' altrimenti
    #     """
    #     rr = self.__write_bit(500, 9, 0)
    #     self.hum_control = False
    #     return rr

    def start_all(self) -> bool:
        """Attiva il controllo in tutte le camere\n
        Returns:
            bool: 'True' se presente un errore. 'False' altrimenti
        """
        response = []
        for key, val in self.SUBUNIT.items():
            register = val["run"]
            rr = self.write_register(register, values=0x0001, unit=self.UNIT)
            error = rr.isError()
            if not error:
                self.temp_control[key] = True
            response.append(error)
        return any(response)

    def stop_all(self) -> bool:
        """Disattiva tutti i controlli della camera\n
        Returns:
            bool: 'True' se presente un errore. 'False' altrimenti
        """
        response = []
        for key, val in self.SUBUNIT.items():
            register = val["run"]
            rr = self.write_register(register, values=0x0000, unit=self.UNIT)
            error = rr.isError()
            if not error:
                self.temp_control[key] = False
            response.append(error)
        return any(response)

    def read_temp(self, unit: int) -> tuple[bool, float]:
        register = self.SUBUNIT[unit]["read"]
        rr = self.read_holding_registers(register, unit=self.UNIT)
        decoder = BinaryPayloadDecoder.fromRegisters(rr.registers,
                                                     byteorder=Endian.Big,
                                                     wordorder=Endian.Big)  # VERIFY endian # noqa: E501
        rs = decoder.decode_16bit_uint()
        return rr.isError(), rs / 10

    def write_temp_sp(self, value: float, unit: int) -> bool:
        val = int(value * 10)
        register = self.SUBUNIT[unit]["write"]
        builder = BinaryPayloadBuilder(byteorder=Endian.Big,
                                       wordorder=Endian.Big)  # VERIFY endian
        builder.add_16bit_uint(val)
        payload = builder.to_registers()
        rw = self.write_register(register, payload, unit=self.UNIT)  # VERIFY what function to write? # noqa: E501
        return rw.isError()

    # ----- other function -----
    def get_data(self) -> list[float]:
        """Get the value requested by test execution\n
        Returns:
            list[float]: lista temp
        """
        data = []
        for i in list(self.SUBUNIT.keys()):
            readed, value = self.read_temp(i)
            if readed is False:
                data.append(value)
            else:
                data.append(float("NaN"))
        return data

    COMMAND = ['start_temp', 'stop_temp', 'start_all', 'stop_all',
               'write_temp_sp']


CHAMBER: dict[str, Union[Type[ACS_Discovery1200], Type[Sauter_PLC]]] = {
    "ACS_Discovery1200": ACS_Discovery1200,
    "Sauter LifeTest": Sauter_PLC,
}

# __all__ must contains:
# dict of all CHAMBER class
# all CHAMBER class
__all__ = ["CHAMBER", "ACS_Discovery1200", "Sauter_PLC"]

if __name__ == "__main__":
    print("File for Climate Chamber class:", flush=True)
    print("Angelantoni ACS Discovery D1200: ACS_Discovery1200")
    # a=ACS_Discovery1200('COM7')
    # a._check_connection()
    # a.read_measure('Temp')
    # a.write_setpoint('Temp', value=23.72)
    # a.write_setpoint('Hum', value=1)
    # a.write_setting('run','a')
