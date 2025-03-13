# MySignage

Una aplicación simple de señalización digital que muestra URLs, videos e imágenes en modo de pantalla completa.

## Requisitos

- Python 3.6 o superior
- Google Chrome
- VLC Media Player

## Instalación

1. Clone este repositorio:
```
git clone https://github.com/usuario/mysignage.git
cd mysignage
```

2. Instale las dependencias:
```
pip install -r requirements.txt
```

3. Configure la aplicación editando el archivo `config.ini`:
```ini
[general]
content_file = ruta/al/archivo/content.txt
read_interval = 30   # Intervalo de lectura del archivo en segundos
rotation_interval = 60   # Intervalo de rotación entre elementos en segundos

[commands]
chrome_cmd = google-chrome --kiosk {url}
vlc_cmd = vlc --fullscreen --no-video-title {video}
```

## Uso

1. Cree un archivo de contenido (por defecto `content.txt`) con una lista de URLs, videos o imágenes, una por línea. Por ejemplo:
```
https://ejemplo.com
/ruta/a/mi/video.mp4
/ruta/a/mi/imagen.jpg
```

2. Ejecute la aplicación:
```
python mysignage.py
```

3. La aplicación leerá el archivo de contenido y mostrará cada elemento en rotación.

## Formato del archivo de contenido

- URLs: Deben comenzar con http:// o https://
- Videos: Ruta completa a archivos de video (mp4, mkv, avi, etc.)
- Imágenes: Ruta completa a archivos de imagen (jpg, png, etc.)

Cada elemento debe estar en una línea separada.
