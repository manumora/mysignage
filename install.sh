#!/bin/bash

echo "Instalando dependencias del sistema..."
sudo apt-get update
sudo apt-get install -y python3 python3-pip xdotool google-chrome-stable vlc

echo "Instalando dependencias de Python..."
pip install -r requirements.txt

echo "Configurando permisos para el script..."
chmod +x mysignage.py

echo "Instalación completada. Puede ejecutar la aplicación con 'python3 mysignage.py'"
