# 🛠️ Herramienta Pública de Configuración Masiva para Ubiquiti

[![Python](https://img.shields.io/badge/Python-3.7+-blue?logo=python)](https://www.python.org/)
[![Licencia MIT](https://img.shields.io/badge/Licencia-MIT-green)](LICENSE)
[![Soporte Técnico](https://img.shields.io/badge/Soporte-Ingeniería%20JLF-blueviolet)](https://github.com)

---

Herramienta CLI desarrollada por **SoporteIngJLF** para ISPs y técnicos de campo.
Permite configurar, verificar y actualizar en lote equipos Ubiquiti (CPEs y APs AC) mediante SSH de forma masiva y controlada.
Creditos Ing Jose Luis Flego
Contacto: <jlsoporte.ingenieria@gmail.com>

---

## 🔧 Funciones disponibles (menú)

1. **Ingresar/Editar IPs**
2. **Configurar parámetros estándar en APs AC**
3. **Consultar (verificar country code)**
4. **Modificar (actualizar country code)**

---

## 📁 Estructura del proyecto

HerramientasProyectoPublico/
├── config_ap_ac.json         # Parámetros por defecto para APs AC
├── config_pass.json          # Usuario y contraseñas por perfil (AP / CPE)
├── ip_list.csv               # Formato de carga de IPs (columna IP)
├── logs/                     # Carpeta de logs generados
├── main.py                   # Menú principal
├── utils.py                  # Funciones auxiliares
├── config_functions.py       # Conexión y lógica de verificación/configuración
├── requirements.txt          # Dependencias necesarias (paramiko)
└── README_PUBLICO.md         # Documentación para la versión compartida

## ▶️ ¿Cómo empezar?

### 1. Cloná el repositorio

``` bash
git clone https://github.com/tu_usuario/HerramientasProyectoPublico.git
cd HerramientasProyectoPublico
```

### 2. Activá tu entorno virtual (opcional pero recomendado)

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate   # Windows
```

### 3. Instalá los requisitos

```bash
pip install -r requirements.txt
```

---

## 📋 Uso básico

```bash
python main.py
```

Y seguí las instrucciones del menú para ingresar IPs o cargar desde `ip_list.csv`, configurar, verificar o actualizar los APs/CPEs.

---

## 📝 Notas

- El archivo `ip_list.csv` se genera automáticamente si no existe
- Se crea una carpeta `logs/` donde se guarda el log paramiko.log
- Los archivos `.json` pueden ser editados según tus necesidades

---

## 👨‍💻 Desarrollado por

**Soporte Ing. JLF** – Soporte técnico especializado para ISPs
**Creditos Ing Jose Luis Flego**
**Contacto: <jlsoporte.ingenieria@gmail.com>**

---

## 🛡️ Licencia

Este proyecto está licenciado bajo los términos de la licencia MIT.
