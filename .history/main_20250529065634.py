import os
import logging
import concurrent.futures
import ipaddress
import csv
import json
from config_functions import *
from utils import *

# Crear carpeta logs si no existe
os.makedirs("logs", exist_ok=True)

# Crear archivo ip_list.csv de ejemplo si no existe
if not os.path.exists("ip_list.csv"):
    with open("ip_list.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["IP"])
        writer.writeheader()
        writer.writerow({"IP": "192.168.1.1"})  # fila de ejemplo

logger = logging.getLogger()
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
console_handler.setFormatter(console_formatter)
file_handler = logging.FileHandler("logs/mi_log.log", mode="a")
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
file_handler.setFormatter(file_formatter)
logger.addHandler(console_handler)
logger.addHandler(file_handler)

hosts = []
username = None
ultimo_username = None
password = None
alt_password = None
old_code = "32"
new_code = "511"
do_reboot = False
dry_run = False
max_workers = 10
mtu_objetivo = 1492

def input_data():
    global hosts, username, password, alt_password, old_code, new_code, do_reboot, dry_run, max_workers

    print("\n--- Ingresar/Editar datos ---")
    ips_input = input("Ingresa IPs manualmente o escribe csv:nombre_archivo.csv (default: csv:ip_list.csv): ").strip()
    if not ips_input:
        ips_input = "csv:ip_list.csv"

    ip_list = []
    if ips_input.lower().startswith("csv:"):
        csv_file = ips_input[4:]
        try:
            with open(csv_file, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ip = row.get("IP")
                    if ip:
                        token = ip.strip()
                        try:
                            if "/" in token:
                                network = ipaddress.ip_network(token, strict=False)
                                ip_list.extend([str(ip) for ip in network.hosts()])
                            else:
                                ip_list.append(token)
                        except Exception as e:
                            print(f"IP inválida '{token}', se omite. Error: {e}")
            print(f"Cargadas {len(ip_list)} IPs desde {csv_file}")
        except Exception as e:
            print(f"[ERROR] No se pudo leer el archivo CSV: {e}")
            presionar_tecla()
            return
    else:
        ip_tokens = [x.strip() for x in ips_input.split(",") if x.strip()]
        for token in ip_tokens:
            try:
                if "/" in token:
                    network = ipaddress.ip_network(token, strict=False)
                    ip_list.extend([str(ip) for ip in network.hosts()])
                else:
                    ip_list.append(token)
            except Exception as e:
                print(f"Token inválido '{token}', se omite. Error: {e}")

    hosts.clear()
    hosts.extend(ip_list)

    # Leer archivo JSON
    try:
        with open("config_pass.json") as f:
            credenciales_config = json.load(f)
    except Exception as e:
        print(f"\n❌ Error al leer config_pass.json: {e}")
        return

    print("\n" + "="*60)
    print("⚠️  ACTUALIZA: APs ó CPEs. Seleccione el que corresponda ⚠️")
    print("="*60)

    tipo = input("Seleccione una opción (A/C): ").strip().upper()
    tipo_clave = "AP" if tipo == "A" else "CPE" if tipo == "C" else None

    if tipo_clave and tipo_clave in credenciales_config:
        cred = credenciales_config[tipo_clave]

        # USERNAME
        if "user" in cred and cred["user"].strip():
            username = cred["user"]
            print(f"👤 Usuario tomado del perfil '{tipo_clave}': {username}")
        else:
            username = input("👤 Ingresá el nombre de usuario SSH (default: ubnt): ").strip() or "ubnt"

        # PASSWORDS
        password = cred["password"]
        alt_password = cred["alt_passwords"]
    else:
        print("\n❌ Opción inválida o tipo no configurado en JSON.\n")
        return

    old_input = input(f"Ingrese el valor actual del código de país (default {old_code}): ").strip()
    if old_input:
        old_code = old_input
    new_input = input(f"Ingrese el nuevo valor del código de país (default {new_code}): ").strip()
    if new_input:
        new_code = new_input
    reboot_input = input("¿Deseas reiniciar el dispositivo después? (s/n) [n]: ").strip().lower()
    do_reboot = True if reboot_input == "s" else False
    dry_run_input = input("¿Deseas ejecutar en modo dry-run? (s/n) [n]: ").strip().lower()
    dry_run = True if dry_run_input == "s" else False
    mw_input = input(f"Número máximo de hilos (default {max_workers}): ").strip()
    if mw_input.isdigit():
        max_workers = int(mw_input)

    print("\n✅ Datos guardados correctamente.\n")
    #logging.info("🔐 Usuario: %s | Tipo: %s | Password: %s | Alt: %s", username, tipo_clave, password, alt_password)   # Se quito porque en consola estos iconos dan problema
    logging.info(" -->  Usuario: %s | Tipo: %s | Password: %s | Alt: %s \n", username, tipo_clave, password, alt_password)
    logging.info(" -->  Datos actualizados: old_code=%s, new_code=%s, do_reboot=%s, dry_run=%s, max_workers=%s\n", old_code, new_code, do_reboot, dry_run, max_workers)
    logging.info(" -->  Host a Verificar:\n")
    logging.info("hosts=%s", hosts)
    
    presionar_tecla()
    limpiar_pantalla()


def check_one_device_mode(ip):
    if not ping_host(ip):
        return f"{ip}: No responde ping"
    ssh = connect_device(ip, username, password, dry_run=dry_run, alt_password=alt_password)
    if ssh is None:
        return f"{ip}: Conexión fallida para verificación"
    try:
        mode_dict = check_country_mode(ssh, ip, dry_run=dry_run)
        values = set(mode_dict.values())
        if len(values) == 1:
            if "32" in values:
                mode = "Argentina (32)"
            elif "511" in values:
                mode = "Licensed (511)"
            else:
                mode = f"Desconocido: {', '.join(values)}"
        else:
            mode = "Valores inconsistentes: " + ", ".join(f"{k}={v}" for k, v in mode_dict.items())
        return f"{ip}: Modo detectado -> {mode}"
    finally:
        ssh.close()

def check_device_mode_action():
    if not hosts or not username or not password:
        print("\n[ERROR] Primero debes ingresar los datos (opción 1 en el menú).")
        presionar_tecla()
        limpiar_pantalla()
        return
    limpiar_pantalla()
    resultados = []
    actual_workers = min(max_workers, len(hosts))
    with concurrent.futures.ThreadPoolExecutor(max_workers=actual_workers) as executor:
        futures = {executor.submit(check_one_device_mode, ip): ip for ip in hosts}
        for future in concurrent.futures.as_completed(futures):
            resultado = future.result()
            resultados.append(resultado)
    
    logging.info("\n === Resumen de verificación ===")
    print("\n📋 Resumen de verificación por modo detectado:\n")

    resumen = {
        "Argentina (32)": [],
        "Licensed (511)": [],
        "No responde ping": [],
        "Conexión fallida": [],
        "Error": [],
        "Inconsistente": [],
        "Desconocido": []
    }

    for res in resultados:
        logging.info(res)
        if "Argentina (32)" in res:
            resumen["Argentina (32)"].append("🟥 " + res)
        elif "Licensed (511)" in res:
            resumen["Licensed (511)"].append("🟩 " + res)
        elif "No responde ping" in res:
            resumen["No responde ping"].append("⚫ " + res)
        elif "Conexión fallida" in res:
            resumen["Conexión fallida"].append("❌ " + res)
        elif "inconsistente" in res.lower():
            resumen["Inconsistente"].append("⚠️ " + res)
        elif "Error" in res:
            resumen["Error"].append("❌ " + res)
        else:
            resumen["Desconocido"].append("❓ " + res)

    for categoria, items in resumen.items():
        if items:
            print(f"\n🔸 {categoria} ({len(items)}):")
            print_with_pagination(items)

    presionar_tecla()
    limpiar_pantalla()

def update_one_device(ip):
    if not ping_host(ip):
        logging.error(f"{ip}: No responde ping; se omite.")
        return f"{ip}: No responde ping"

    ssh = connect_device(ip, username, password, dry_run=dry_run, alt_password=alt_password)
    if ssh is None:
        logging.error(f"{ip}: Error de conexión.")
        return f"{ip}: Conexión fallida"

    try:
        mode_dict = check_country_mode(ssh, ip, dry_run=dry_run)
        values = set(mode_dict.values())

        # ¿Ya tiene el código deseado?
        if len(values) == 1 and new_code in values:
            logging.info(f"{ip}: Ya tiene el código de país {new_code}, no se realizan cambios.")
            return f"{ip}: Ya tiene el código {new_code}, no se actualiza ni reinicia."

        # Caso contrario, actualizamos
        update_config(ssh, ip, old_code, new_code, dry_run=dry_run)
        verify_update(ssh, ip, dry_run=dry_run)
        persist_changes(ssh, ip, dry_run=dry_run)
        if do_reboot:
            reboot_device(ssh, ip, dry_run=dry_run)
        return f"{ip}: Actualizado correctamente a {new_code}"
    except Exception as e:
        logging.error(f"{ip}: Error durante la actualización - {e}")
        return f"{ip}: Error - {e}"
    finally:
        ssh.close()

def update_country_code_action():
    if not hosts or not username or not password:
        print("\n[ERROR] Primero debes ingresar los datos (opción 1 en el menú).")
        presionar_tecla()
        limpiar_pantalla()
        return
    resultados = []
    actual_workers = min(max_workers, len(hosts))
    with concurrent.futures.ThreadPoolExecutor(max_workers=actual_workers) as executor:
        futures = {executor.submit(update_one_device, ip): ip for ip in hosts}
        for future in concurrent.futures.as_completed(futures):
            resultado = future.result()
            resultados.append(resultado)

    print("\n📋 Resumen de actualización:\n")

    actualizados = []
    errores = []
    sin_respuesta = []

    for res in resultados:
        logging.info(res)
        if "Actualizado correctamente" in res:
            actualizados.append("🛠️ " + res)
        elif "Conexión fallida" in res or "Error" in res:
            errores.append("❌ " + res)
        elif "No responde ping" in res:
            sin_respuesta.append("⚫ " + res)

    if actualizados:
        limpiar_pantalla()
        print(f"\n✅ Equipos actualizados correctamente ({len(actualizados)}):")
        print_with_pagination(actualizados)
    if errores:
        print(f"\n❌ Errores detectados ({len(errores)}):")
        print_with_pagination(errores)
    if sin_respuesta:
        print(f"\n⚫ Sin respuesta al ping ({len(sin_respuesta)}):")
        print_with_pagination(sin_respuesta)

    presionar_tecla()
    limpiar_pantalla()
    
def configurar_aps_estandar():
    import json
    from config_functions import connect_device, persist_changes, reboot_device

    global hosts, username, password, alt_password, dry_run, do_reboot

    if not hosts or not username or not password:
        print("\n[ERROR] Primero debes ingresar los datos (opción 1 en el menú).")
        presionar_tecla()
        limpiar_pantalla()
        return
    try:
        with open("config_ap_ac.json") as f:
            parametros = json.load(f)
    except Exception as e:
        print(f"[ERROR] No se pudo leer config_ap_ac.json: {e}")
        presionar_tecla()
        return

    # Cargo valores del JSON
    canalbw = parametros.get("radio.1.chanbw")
    potenciatx = parametros.get("radio.1.txpower")
    sensibilidadrx = parametros.get("radio.1.rx_sensitivity")
    

    print("\n--- Configuración personalizada (Enter para usar valores por defecto) ---")

    # Usuario SSH
    nuevo_user = input(f"👤 Usuario SSH (default del JSON: {username}): ").strip()
    if nuevo_user:
        username = nuevo_user

    # Ancho de canal: 20 o 40 MHz
    ancho = input(f"📶 Ancho de canal 20, 40 ó 80  MHz (default {canalbw}): ").strip()
    if ancho == "20":
        parametros["radio.1.ieee_mode"] = "11acvht20"
        parametros["radio.1.chanbw"] = "20"
    elif ancho == "40":
        parametros["radio.1.ieee_mode"] = "11acvht40"
        parametros["radio.1.chanbw"] = "40"
    elif ancho == "80":
        parametros["radio.1.ieee_mode"] = "11acvht80"
        parametros["radio.1.chanbw"] = "80"


    # TX Power
    txp = input(f"🔋 TX Power, ej: 25/28 (default {potenciatx}): ").strip()
    if txp.isdigit():
        parametros["radio.1.txpower"] = txp

    # Sensibilidad
    sens = input(f"🎧 Sensibilidad RX, ej: -75db (default {sensibilidadrx}): ").strip()
    if sens:
        parametros["radio.1.rx_sensitivity"] = sens

    logging.info("      === Aplicando configuración estándar a APs AC ===\n")
    resultados = []

    for ip in hosts:
        print(f"\n🔧 Configurando {ip} ...\n")
        ssh = connect_device(ip, username, password, dry_run=dry_run, alt_password=alt_password)
        if ssh is None:
            msg = f"{ip}: ❌ Conexión fallida"
            print(msg)
            logging.error(msg)
            resultados.append(msg)
            continue

        try:
            for clave, valor in parametros.items():
                comando = f'sed -i "s|^{clave}=.*|{clave}={valor}|" /tmp/system.cfg'
                if dry_run:
                    print(f"[DRY-RUN] {ip}: {comando}")
                else:
                    ssh.exec_command(comando)

            if not dry_run:
                persist_changes(ssh, ip, dry_run=False)
                if do_reboot:
                    reboot_device(ssh, ip, dry_run=False)

            msg = f"\n{ip}: Configuración aplicada"
            print(msg)
            logging.info(msg)
            resultados.append(msg)
        except Exception as e:
            msg = f"{ip}: Error durante la configuración - {e}"
            print(msg)
            logging.error(msg)
            resultados.append(msg)
        finally:
            ssh.close()

    print("\n   --- Resumen de configuración ---\n")
    for r in resultados:
        print(r)
    presionar_tecla()
    limpiar_pantalla()

def menu_principal():
    while True:
        print(f"\n\n     *****   ULTIMA RED EJECUTADA:   {hosts}" )
        print("\n--- Menú de opciones ---")
        print("1. Ingresar/Editar datos")
        print("2. Configurar parámetros estándar en APs AC")
        print("3. Consultar (verificar country code)")
        print("4. Modificar (actualizar country code)")
        print("5. Salir") 
        opcion = input("Seleccione una opción (1-5): ").strip()
        if opcion == "1":
            limpiar_pantalla()
            input_data()
        elif opcion == "2":
            limpiar_pantalla()
            configurar_aps_estandar()
        elif opcion == "3":
            limpiar_pantalla()
            check_device_mode_action()
        elif opcion == "4":
            limpiar_pantalla()
            print("\n⚠️  ATENCIÓN: MODIFICACIONES PERMANENTES EN LOS APs Y CPEs ⚠️")
            resp = input("¿Desea continuar? (Y/N): ").strip().upper()
            if resp == "Y":
                update_country_code_action()
            limpiar_pantalla()
        elif opcion == "5":
            print("Saliendo del programa.")
            limpiar_pantalla()
            break
        else:
            print("Opción no válida.")
            presionar_tecla()
            limpiar_pantalla()

def main():
    limpiar_pantalla()
    menu_principal()

if __name__ == "__main__":
    main()
