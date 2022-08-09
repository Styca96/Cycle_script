#!/usr/bin/env python
"""Class for all Device that need connection with paramiko (SSH)"""
from stat import S_ISDIR, S_ISREG
from typing import Type

import paramiko

# import logging
# _logger = logging.getLogger(__name__)


class Charger:
    """Classe connessione charger"""

    def __init__(self, host: str, user: str = "root", pwd: str = "abb") -> None:    # noqa: E501
        """Inizializza il client SSH e si connette tramite l'host, l'user e la
        pwd\n
        Args:
            host (str): indirizzo host
            user (str, optional): username. Defaults to 'root'.
            pwd (str, optional): password. Defaults to 'ABB'.
        """
        self._sftp: paramiko.SFTPClient | None = None
        self._shell = None
        # crate a client
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._client.load_system_host_keys()
        self._client.connect(hostname=host, username=user, password=pwd,
                             timeout=5)
        self.hostname = self.get_hostname()

        # other
        self._transport = self._client.get_transport()
        self._transport.set_keepalive(60)
        self._shell = self._client.invoke_shell()  # new Channel for shell

    def __del__(self):
        """chiude tutti i canali"""
        if self._sftp is not None:
            self._sftp.close()
        if self._shell is not None:
            self._shell.close()
        self._client.close()

    def __str__(self):
        return f"ARMxl {self.hostname}"

    def command(self, command: str, *args):
        """Esegue comando sul server connesso\n
        Args:
            command (str): stringa eseguita nella shell di arrivo\n
            *args: eventuali opzioni da passare in più al comando
        Returns:
            (str): risposta del server. Risposta o Errore
        """
        stdin, stdout, stderr = self._client.exec_command(command)
        if args:
            stdin.write(f"{args}")
        out = stdout.read().decode(encoding="UTF-8").strip()
        error = stderr.read().decode(encoding="UTF-8").strip()

        stdin.close()
        stdout.close()
        stderr.close()

        if out != "":
            return out
        else:
            return error

    def get_hostname(self):
        """Get name of host\n
        Returns:
            hostname(str): name
        """
        _, stdout, _ = self._client.exec_command("hostname")
        hostname = stdout.read()
        if isinstance(hostname, bytes):
            hostname = hostname.decode("utf-8")
        return hostname.strip()

    def is_alive(self) -> bool:
        """Verifica se la connessione è sempre attiva\n
        Returns:
            bool: 'True' se ancora connesso. 'False' altrimenti
        """
        return self._transport.is_active()

    # ---------- SFTP command ----------
    def connect_SFTP(self) -> bool:
        """Open SFTP client object session across an open SSH Transport and
        perform remote file operations.\n
        Returns:
            bool: 'True' se la connessione è riuscita. 'False' altrimenti
        """
        try:
            self._sftp = self._client.open_sftp()
            self._sftp.chdir(".")  # set basic directory
            return True
        except Exception:
            return False

    def set_dir(self, path: str = "."):
        """Seleziona la directory in path\n
        Args:
            path (str, optional): path to directory. Defaults to '.'"""
        self._sftp.chdir(path)

    def get_current_dir(self):
        """Return current directory path\n
        Returns:
            str: path to current directory"""
        return self._sftp.getcwd()

    def get_current_dir_list(self, path: str | None = None
                             ) -> tuple[list[str], list[str]]:
        """Restituisce lista file e cartelle nella directory attuale\n
        Args:
            path (str|None): path to directory. Default current directory
        Returns:
            tuple[list[str],list[str]]: lista file, lista folder
        """
        if path is None:
            path = self.get_current_dir()
        if self._sftp:
            file = []
            folder = []
            for entry in self._sftp.listdir_attr(path):
                mode = entry.st_mode
                if S_ISDIR(mode):
                    folder.append(entry.filename)
                elif S_ISREG(mode):
                    file.append(entry.filename)
            file.sort(), folder.sort()
            return file, folder
        else:
            raise paramiko.SSHException("Connessione SFTP non effettuata")

    def put_file(self, localpath: str, remotepath: str, mode: int = 0o100775):
        """Copia file (localpath) nel server remoto (remotepath). Il nome e
        l'estensione del file devono essere presenti sia in localpath che in
        remotepath\n
        Args:
            localpath (str): path del file da copiare
            remotepath (str): path di destinazione del file
            mode (int, optional): permessi del file copiato.
            Defaults equivalent to '-rwxrwxr-x'.\n
        Returns:
            SFTPAttributes del file copiato"""
        SFTPAttributes = self._sftp.put(localpath, remotepath, confirm=True)
        self._sftp.chmod(remotepath, mode)
        return SFTPAttributes

    def remove_file(self, filename: str):
        """Rimuove file dalla directory corrente\n
        Args:
            filename (str): nome del file con estensione"""
        self._sftp.remove(filename)

    def get_file(self, remotepath: str, localpath: str):
        """Crea copia locale (localpath) del file del server remoto
        (remotepath)\n
        Args:
            remotepath (str): path remota del file da copiare
            localpath (str): path locale di destinazione del file
        """
        self._sftp.get(remotepath, localpath)

    # ----- close -----
    def close(self):
        """Chiude tutti i canali"""
        if self._sftp is not None:
            self._sftp.close()
        self._shell.close()
        self._client.close()


CONNECTION: dict[str, Type[Charger]] = {"Arm-Xl": Charger}

if __name__ == "__main__":
    print("Class for charger connection")
