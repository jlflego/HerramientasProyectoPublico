import paramiko
import logging
paramiko.util.log_to_file("paramiko.log")  # opcional, para log interno si lo querés
logging.getLogger("paramiko").setLevel(logging.WARNING)
import time

# Decorador para reintentos
def retry(max_attempts=3, delay=2):
    """
    Decorador que intenta ejecutar una función un número de veces,
    esperando 'delay' segundos entre cada intento.
    """
    def decorator_retry(func):
        def wrapper_retry(*args, **kwargs):
            attempts = 0
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    logging.error(f"Error en {func.__name__}: {e}. Intento {attempts} de {max_attempts}")
                    time.sleep(delay)
            raise Exception(f"{func.__name__} falló después de {max_attempts} intentos")
        return wrapper_retry
    return decorator_retry

# Clases para simular la conexión en modo dry-run
class DummySSH:
    """
    Objeto de conexión simulado para modo dry-run.
    Permite “ejecutar” comandos sin efectuar cambios reales en el dispositivo.
    """
    def exec_command(self, command):
        logging.info(f"DRY-RUN DummySSH: Se ejecutaría: {command}")
        # Se simula un canal cuyo exit status es 0
        class DummyChannel:
            def recv_exit_status(self):
                return 0
        dummy_stdout = DummyOutput(DummyChannel())
        dummy_stderr = DummyOutput(None)
        return None, dummy_stdout, dummy_stderr

    def close(self):
        logging.info("DRY-RUN DummySSH: Conexión cerrada.")

class DummyOutput:
    def __init__(self, channel):
        self.channel = channel
    def read(self):
        return b""

def _connect_device(ip, username, password, timeout=10, banner_timeout=5, auth_timeout=5):
    logging.info(f"Conectando a {ip} con usuario: {username} y contraseña: {password}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        ip,
        username=username,
        password=password,
        timeout=timeout,
        banner_timeout=banner_timeout,
        auth_timeout=auth_timeout
    )
    return ssh

def connect_device(ip, username, password, timeout=10, dry_run=False, alt_password=None,
                   banner_timeout=5, auth_timeout=5):
    """
    Intenta conectar vía SSH al dispositivo usando la contraseña primaria.
    Si falla y se proporciona alt_password (string o lista), intenta cada una.
    Si dry_run está activo, retorna un DummySSH.
    """
    if dry_run:
        logging.info(f"DRY-RUN: Simulando conexión a {ip} (username: {username})")
        return DummySSH()
    
    # Intento con la contraseña principal
    try:
        return _connect_device(ip, username, password, timeout, banner_timeout, auth_timeout)
    except Exception as e:
        logging.error(f"Error conectando a {ip} con la contraseña primaria: {e}")

    # Intento con contraseñas alternativas si existen
    if alt_password:
        alt_list = [alt_password] if isinstance(alt_password, str) else alt_password
        for idx, alt in enumerate(alt_list, start=1):
            try:
                logging.info(f"Intentando conectar a {ip} con contraseña alternativa {idx}...")
                return _connect_device(ip, username, alt, timeout, banner_timeout, auth_timeout)
            except Exception as e2:
                logging.error(f"Error conectando a {ip} con alternativa {idx}: {e2}")

    return None  # Si ninguna funcionó

            
def update_config(ssh, ip, old_code, new_code, remote_filepath="/tmp/system.cfg", dry_run=False):
    """
    Ejecuta el comando sed para reemplazar tanto 'radio.countrycode=old_code'
    como 'radio.1.countrycode=old_code' por el nuevo valor.
    """
    command_sed = f'sed -i "s/\\(radio\\(\\.1\\)\\?\\.countrycode=\\){old_code}/\\1{new_code}/g" {remote_filepath}'
    if dry_run:
        logging.info(f"[{ip}] DRY-RUN: Se ejecutaría: {command_sed}")
    else:
        stdin, stdout, stderr = ssh.exec_command(command_sed)
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            error_message = stderr.read().decode().strip()
            logging.error(f"[{ip}] Error en 'sed' (exit code {exit_code}): {error_message}")
        else:
            logging.info(f"[{ip}] Reemplazo en {remote_filepath} exitoso (exit code {exit_code}).")

def verify_update(ssh, ip, remote_filepath="/tmp/system.cfg", dry_run=False):
    """
    Ejecuta un comando grep para verificar que las líneas con country code
    se hayan actualizado correctamente.
    """
    verify_command = f"grep '^radio\\(\\.1\\)\\?\\.countrycode' {remote_filepath}"
    if dry_run:
        logging.info(f"[{ip}] DRY-RUN: Se ejecutaría: {verify_command}")
    else:
        stdin, stdout, stderr = ssh.exec_command(verify_command)
        verification_output = stdout.read().decode().strip()
        logging.info(f"[{ip}] Verificación: {verification_output}")

def persist_changes(ssh, ip, remote_filepath="/tmp/system.cfg", dry_run=False):
    """
    Persiste los cambios en la flash del dispositivo usando cfgmtd.
    """
    command_cfgmtd = f"cfgmtd -f {remote_filepath} -w"
    if dry_run:
        logging.info(f"[{ip}] DRY-RUN: Se ejecutaría: {command_cfgmtd}")
    else:
        stdin, stdout, stderr = ssh.exec_command(command_cfgmtd)
        exit_code = stdout.channel.recv_exit_status()
        error_msg = stderr.read().decode().strip()
        if exit_code != 0:
            logging.error(f"[{ip}] 'cfgmtd' falló (exit code {exit_code}): {error_msg}")
        else:
            logging.info(f"[{ip}] Cambios guardados en la flash (exit code {exit_code}).")

def reboot_device(ssh, ip, dry_run=False):
    """
    Reinicia el dispositivo.
    """
    command_reboot = "reboot"
    if dry_run:
        logging.info(f"[{ip}] DRY-RUN: Se ejecutaría: {command_reboot}")
    else:
        logging.info(f"[{ip}] Reiniciando el dispositivo...")
        ssh.exec_command(command_reboot)

def check_country_mode(ssh, ip, remote_filepath="/tmp/system.cfg", dry_run=False):
    """
    Verifica el country code en el dispositivo.
    Ejecuta un grep sobre el archivo de configuración.
    Si no se encuentra la línea, se asume que el dispositivo está en Licensed (511).
    Retorna un diccionario con la clave 'radio.countrycode' y su valor.
    Por ejemplo:
       {"radio.countrycode": "32"} o {"radio.countrycode": "511"}
    """
    command = f"grep '^radio\\(\\.1\\)\\?\\.countrycode' {remote_filepath}"
    if dry_run:
        logging.info(f"[{ip}] DRY-RUN: Simulated check for country mode.")
        return {"radio.countrycode": "32", "radio.1.countrycode": "32"}
    else:
        stdin, stdout, stderr = ssh.exec_command(command)
        lines = stdout.read().decode().strip().splitlines()
        if not lines:
            logging.warning(f"{ip}: No se encontró la línea de countrycode en {remote_filepath}, asumiendo Licensed (511).")
            return {"radio.countrycode": "511"}
        result = {}
        for line in lines:
            if "=" in line:
                key, value = line.split("=", 1)
                result[key.strip()] = value.strip()
        return result

def corregir_mtu_pppoe(ssh, ip, dry_run=False, do_reboot=False):
    """
    Verifica si el CPE tiene ppp.1.mtu o ppp.1.mru distintos de 1492 y los corrige si es necesario.
    """
    try:
        sftp = ssh.open_sftp()
        remote_path = "/tmp/system.cfg"
        local_temp = f"/tmp/system_{ip.replace('.', '_')}.cfg"

        sftp.get(remote_path, local_temp)

        with open(local_temp, "r") as f:
            cfg_lines = f.readlines()

        mtu_line = next((line for line in cfg_lines if "ppp.1.mtu=" in line), None)
        mru_line = next((line for line in cfg_lines if "ppp.1.mru=" in line), None)

        mtu_ok = mtu_line and mtu_line.strip().endswith("1492")
        mru_ok = mru_line and mru_line.strip().endswith("1492")

        if mtu_ok and mru_ok:
            print(f"{ip:<16} -> ✅ MTU y MRU ya están correctos (1492)")
            return

        print(f"{ip:<16} -> 🛠️ Corrigiendo MTU/MRU PPPoE (MTU: {mtu_line.strip() if mtu_line else 'N/A'}, MRU: {mru_line.strip() if mru_line else 'N/A'})")

        if not dry_run:
            cmds = [
                "sed -i 's/^ppp\\.1\\.mtu=.*/ppp.1.mtu=1492/' /tmp/system.cfg",
                "sed -i 's/^ppp\\.1\\.mru=.*/ppp.1.mru=1492/' /tmp/system.cfg",
                "cfgmtd -f /tmp/system.cfg -w"
            ]
            for cmd in cmds:
                ssh.exec_command(cmd)

            if do_reboot:
                ssh.exec_command("reboot")
                print(f"\n{ip:<16} -> 🔄 Reboot solicitado")

    except Exception as e:
        print(f"{ip:<16} -> ❌ Error corrigiendo MTU/MRU: {e}")