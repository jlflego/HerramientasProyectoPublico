import re
import os
import time
import sys
import subprocess
import platform
import json
import getpass
from datetime import datetime
from rich.console import Console
from rich.table import Table
from collections import defaultdict

# ANSI Escape Cleaner
ansi_escape = re.compile(r"(?:\x1B[@-_][0-?]*[ -/]*[@-~])")


def limpiar_linea(line):
    return ansi_escape.sub("", line).strip()


# 🧠 Función para limpiar pantalla
def limpiar_pantalla():
    os.system("cls" if os.name == "nt" else "clear")


# ⌨️ Pausa para el usuario
def presionar_tecla():
    input("\nPresione Enter para continuar...")


# 📊  Funcion que define los Country Code
def nombre_country_code(code):
    dic = {"AR": "Argentina", "BR": "Brasil", "CL": "Chile", "UY": "Uruguay"}
    return dic.get(code.upper(), "Desconocido")


def parsear_ip_respuesta(salida):
    match = re.search(r"from\s+([\d\.]+)", salida)
    if match:
        return match.group(1)
    match = re.search(r"Respuesta desde ([\d\.]+)", salida)  # Windows en español
    if match:
        return match.group(1)
    return ""


def es_windows():
    return platform.system().lower().startswith("win")


# 📊  Funcion para imprimir en crudo
def print_with_pagination(items, page_size=20):
    for i, item in enumerate(items, 1):
        print(item)
        if i % page_size == 0:
            presionar_tecla()


# 📂 Cargar credenciales desde JSON
def cargar_credenciales():
    import json

    with open("credenciales.json") as f:
        return json.load(f)


def obtener_credenciales_actualizadas(
    ruta="credenciales.json", incluir_loop: bool = True
):
    """
    Carga/crea el JSON y pide sólo los valores necesarios.
    Si incluir_loop=False, no solicita intervalo ni umbral.
    """
    if not os.path.exists(ruta):
        datos = {
            "mikrotik": {
                "ip": "172.26.22.129",
                "usuario": "boca",
                "clave": "boca8806",
                "iptracert": "8.8.8.8",
                "interfacemk": "ether1",
                "src-address": "192.168.88.1",
                "timeouticmp": "00:00:01.00",
            },
            "intervalo_loop_traceroute": 60,
            "cuello_rtt_umbral": 50,
        }
    else:
        with open(ruta, "r", encoding="utf-8") as f:
            datos = json.load(f)

    print("\n" + "-" * 120 + "\n")
    mk = datos["mikrotik"]
    mk["ip"] = input(f" 🖧 IP Router (default {mk['ip']}): ").strip() or mk["ip"]
    mk["usuario"] = (
        input(f" 👤 Usuario (default {mk['usuario']}): ").strip() or mk["usuario"]
    )
    mk["clave"] = (
        getpass.getpass(" 🔐 Contraseña (Enter para mantener): ").strip() or mk["clave"]
    )
    mk["iptracert"] = (
        input(f" 🌐 IP destino (default {mk['iptracert']}): ").strip()
        or mk["iptracert"]
    )
    mk["interfacemk"] = (
        input(f" 🔌 Interface (default {mk['interfacemk']}): ").strip()
        or mk["interfacemk"]
    )
    mk["src-address"] = (
        input(f" 📤 Origen (default {mk['src-address']}): ").strip()
        or mk["src-address"]
    )
    mk["timeouticmp"] = (
        input(f" ⏱️ Timeout ICMP (default {mk['timeouticmp']}): ").strip()
        or mk["timeouticmp"]
    )

    if incluir_loop:
        iv = input(
            f"🔁 Intervalo loop (s, default {datos['intervalo_loop_traceroute']}): "
        ).strip()
        datos["intervalo_loop_traceroute"] = (
            int(iv) if iv else datos["intervalo_loop_traceroute"]
        )
        um = input(
            f"🎯 Umbral cuello (ms, default {datos['cuello_rtt_umbral']}): "
        ).strip()
        datos["cuello_rtt_umbral"] = int(um) if um else datos["cuello_rtt_umbral"]

    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4)
        print("\n✅ Credenciales actualizadas.")

    return datos


# 🧹 Limpia ANSI de la salida y devuelve línea por línea
def limpiar_salida_ansi(salida):
    lineas_limpias = []
    for line in salida.splitlines():
        limpio = ansi_escape.sub("", line).strip()
        if limpio:
            lineas_limpias.append(limpio)
    return lineas_limpias


# 📊  Funcion que cheque si un host esta vivo o no en la red
def ping_host(host):
    try:
        resultado = subprocess.run(
            ["ping", "-n" if os.name == "nt" else "-c", "1", host],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return resultado.returncode == 0
    except Exception:
        return False
