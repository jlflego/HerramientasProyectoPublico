# 🛠️ Herramienta Pública de Configuración Masiva para Ubiquiti

Desarrollada por el equipo técnico de **Soporte Ing. JLF**, esta herramienta permite configurar rápidamente parámetros críticos en equipos Ubiquiti desde un entorno seguro, claro y automatizado.

## ✅ Funciones disponibles

1. **Ingresar/Editar IPs**: Carga manual o por archivo CSV
2. **Configurar APs tipo AC**: Aplica configuraciones estandarizadas (canal, potencia, sensibilidad, etc.)
3. **Consultar Country Code**: Verifica qué código de país está configurado actualmente en los equipos
4. **Actualizar Country Code**: Cambia el código de país de forma masiva (ej. de 32 a 511)

## 🔐 ¿Qué no incluye esta versión pública?

- Opciones de diagnóstico avanzadas (MTU, NTP, traceroute, comparadores, etc.)
- Funciones internas y específicas de producción de SoporteIngJLF

## 📦 Archivos incluidos

- `main.py` – Menú principal con las opciones 1–4
- `utils.py` – Funciones auxiliares (limpiar pantalla, esperar tecla)
- `config_functions.py` – Conexión SSH, verificación y cambio de configuración
- `config_ap_ac.json` – Parámetros estándar para APs tipo AC
- `config_pass.json` – Usuario y contraseñas por perfil (AP / CPE)

## ▶️ Requisitos

- Python 3.7+
- Módulos: `paramiko`, `ipaddress`, `csv`, `json`, `rich`

## 🚀 Cómo usar

1. Ejecutá `main.py`
2. Seleccioná la opción `1` para ingresar IPs y credenciales
3. Luego usá `2`, `3` o `4` según la acción que quieras aplicar

---

**Compartilo, mejoralo y usalo libremente.**

Creado con ❤️ por **Ing José Luis Flego** – Soporte para ISPs -
