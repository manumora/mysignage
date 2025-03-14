import os
import subprocess
import time
import threading
import configparser
import urllib.parse
import mimetypes
import logging
import re
from pathlib import Path
import psutil

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("mysignage.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("mysignage")

class ContentItem:
    def __init__(self, path, duration=None):
        self.path = path
        self.duration = duration  # Duración en segundos para este elemento
        self.process = None
        self.type = self._determine_type()
        self.window_id = None
        
    def _determine_type(self):
        """Determina si el contenido es URL, video o imagen"""
        # Comprobar si es una URL
        try:
            result = urllib.parse.urlparse(self.path)
            if all([result.scheme, result.netloc]):
                return "url"
        except Exception:
            pass
        
        # Comprobar si el archivo existe
        if not os.path.exists(self.path):
            logger.warning(f"El archivo {self.path} no existe")
            return "unknown"
            
        # Comprobar el tipo de archivo
        mime_type, _ = mimetypes.guess_type(self.path)
        if mime_type:
            if mime_type.startswith('video/'):
                return "video"
            elif mime_type.startswith('image/'):
                return "image"
            
        # Si llegamos aquí, no podemos determinar el tipo
        return "unknown"
    
    def get_window_id(self):
        """Obtiene el ID de la ventana recién abierta según el tipo de contenido"""
        try:
            time.sleep(1)  # Dar más tiempo a la ventana para abrirse completamente
            
            if self.type == "video":
                # Para ventanas de VLC
                cmd = "xdotool search --onlyvisible --class vlc | tail -1"
                result = subprocess.check_output(cmd, shell=True, text=True)
                window_id = result.strip()
            else:
                # Para ventanas de Chrome/Chromium (URLs e imágenes)
                browser_type = config.get('browser', 'type').lower()
                browser_class = "Chrome" if browser_type == "chrome" else "Chromium"
                cmd = f"xdotool search --onlyvisible --class {browser_class} | tail -1"
                result = subprocess.check_output(cmd, shell=True, text=True)
                window_id = result.strip()
                
            if window_id:
                logger.info(f"ID de ventana capturado para {self.path}: {window_id} ({self.type})")
                return window_id
        except Exception as e:
            logger.error(f"Error al obtener ID de ventana: {str(e)}")
        return None

    def process_exists(self):
        """Verifica si el proceso sigue en ejecución"""
        if self.process is None:
            return False
        try:
            return psutil.pid_exists(self.process.pid)
        except:
            return False

    def activate_window(self):
        """Activa la ventana existente usando xdotool"""
        if self.window_id:
            try:
                cmd = f"xdotool windowactivate {self.window_id}"
                subprocess.run(cmd, shell=True)
                logger.info(f"Ventana activada para: {self.path} (ID: {self.window_id})")
                return True
            except Exception as e:
                logger.error(f"Error al activar ventana {self.window_id}: {str(e)}")
        return False
    
    def open(self, config):
        """Abre el contenido según su tipo o activa la ventana existente"""
        # Si ya tiene un ID de ventana, intenta activarla
        if self.window_id:
            # Para ventanas de video que fueron ocultadas, necesitamos mostrarlas de nuevo
            if self.type == "video":
                try:
                    # Mostrar la ventana (para contrarrestar windowunmap)
                    subprocess.run(f"xdotool windowmap {self.window_id}", shell=True)
                    time.sleep(0.3)  # Esperar a que se muestre
                    
                    # Activar la ventana
                    subprocess.run(f"xdotool windowactivate {self.window_id}", shell=True)
                    time.sleep(0.3)
                    
                    # Reanudar la reproducción del video
                    subprocess.run(f"xdotool key --window {self.window_id} space", shell=True)
                    logger.info(f"Ventana de video restaurada y reproducción reanudada: {self.path}")
                    return
                except Exception as e:
                    logger.error(f"Error al restaurar ventana de video: {str(e)}")
                    self.window_id = None  # Resetear el ID si hay error
            elif self.activate_window():
                return
        
        # Si el proceso ya no existe, anular window_id
        if not self.process_exists():
            self.window_id = None
            
        # Si necesitamos abrir una nueva ventana
        if self.type == "url":
            browser_type = config.get('browser', 'type').lower()
            cmd_key = f"{browser_type}_cmd"
            cmd = config.get('commands', cmd_key).format(url=self.path)
            logger.info(f"Abriendo URL con {browser_type}: {self.path}")
        elif self.type == "video":
            cmd = config.get('commands', 'vlc_cmd').format(video=self.path)
            logger.info(f"Reproduciendo video: {self.path}")
        elif self.type == "image":
            # Para imágenes, creamos una URL de archivo local
            file_url = f"file://{os.path.abspath(self.path)}"
            browser_type = config.get('browser', 'type').lower()
            cmd_key = f"{browser_type}_cmd"
            cmd = config.get('commands', cmd_key).format(url=file_url)
            logger.info(f"Mostrando imagen con {browser_type}: {self.path}")
        else:
            logger.warning(f"Tipo de contenido desconocido: {self.path}")
            return
            
        try:
            self.process = subprocess.Popen(cmd, shell=True)
            # Esperar un poco para que la ventana se abra
            time.sleep(3)  # Aumentado de 2 a 3 segundos
            # Obtener ID de la ventana
            self.window_id = self.get_window_id()
        except Exception as e:
            logger.error(f"Error al abrir {self.path}: {str(e)}")
    
    def minimize(self):
        """Minimiza la ventana en lugar de cerrarla"""
        if self.window_id:
            try:
                # Verificar que la ventana existe antes de minimizarla
                check_cmd = f"xdotool getwindowname {self.window_id} 2>/dev/null || echo 'No existe'"
                check_result = subprocess.check_output(check_cmd, shell=True, text=True).strip()
                
                if check_result == 'No existe':
                    logger.warning(f"Ventana {self.window_id} ya no existe para {self.path}")
                    self.window_id = None
                    return False
                
                # Si es un video, pausar la reproducción antes de ocultarlo
                if self.type == "video":
                    # Asegurar que la ventana esté activa antes de enviar comandos
                    subprocess.run(f"xdotool windowactivate {self.window_id}", shell=True)
                    time.sleep(0.2)  # Pequeña pausa para asegurar que se active
                    
                    # Enviar tecla de espacio para pausar VLC
                    subprocess.run(f"xdotool key --window {self.window_id} space", shell=True)
                    logger.info(f"Video pausado: {self.path}")
                    time.sleep(0.3)  # Esperar a que se procese la pausa
                    
                    # Ocultar completamente la ventana de VLC 
                    cmd = f"xdotool windowunmap {self.window_id}"
                    subprocess.run(cmd, shell=True)
                    
                    # Verificar si la ventana se ocultó correctamente
                    check_visible = f"xdotool search --onlyvisible --name {self.window_id} 2>/dev/null || echo ''"
                    result = subprocess.check_output(check_visible, shell=True, text=True).strip()
                    if result:
                        # Si la ventana sigue visible, forzar minimización
                        subprocess.run(f"xdotool windowminimize {self.window_id}", shell=True)
                    
                    logger.info(f"Ventana de video ocultada: {self.path} (ID: {self.window_id})")
                else:
                    # Para otras ventanas, continuar con la minimización normal
                    # Asegurar que la ventana esté activa antes de minimizarla
                    subprocess.run(f"xdotool windowactivate {self.window_id}", shell=True)
                    time.sleep(0.3)  # Pequeña pausa para asegurar que se active
                    
                    cmd = f"xdotool windowminimize {self.window_id}"
                    subprocess.run(cmd, shell=True)
                    logger.info(f"Ventana minimizada: {self.path} (ID: {self.window_id})")
                
                # Esperar a que se complete la minimización u ocultamiento
                time.sleep(0.5)
                return True
            except Exception as e:
                logger.error(f"Error al minimizar ventana: {str(e)}")
                self.window_id = None  # Resetear el ID si hay error
        return False
    
    def close(self):
        """Cierra el proceso si está abierto"""
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                time.sleep(1)
                if self.process.poll() is None:
                    self.process.kill()
                logger.info(f"Proceso cerrado para: {self.path}")
                self.window_id = None
            except Exception as e:
                logger.error(f"Error al cerrar {self.path}: {str(e)}")

class SignageManager:
    def __init__(self, config_path="config.ini"):
        self.config = configparser.ConfigParser()
        self.config.read(config_path)
        
        # Configurar variable global para ContentItem
        global config
        config = self.config
        
        self.content_file = self.config.get('general', 'content_file')
        self.read_interval = self.config.getint('general', 'read_interval')
        self.rotation_interval = self.config.getint('general', 'rotation_interval')
        
        self.content_items = {}  # Diccionario para mantener los elementos actuales
        self.current_item = None
        self.running = True
        
        # Añadir evento para señalizar cuando hay contenido disponible
        self.content_available = threading.Event()
        
        # Inicializar mimetypes
        mimetypes.init()
    
    def read_content_file(self):
        """Lee el archivo de contenido y actualiza los elementos"""
        if not os.path.exists(self.content_file):
            logger.error(f"Archivo de contenido no encontrado: {self.content_file}")
            return {}
            
        try:
            content_dict = {}
            with open(self.content_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    parts = line.split('#', 1)
                    if len(parts) == 2:
                        try:
                            duration = int(parts[0])
                            path = parts[1]
                            content_dict[path] = duration
                        except ValueError:
                            logger.error(f"Formato incorrecto en línea: {line}")
                    else:
                        logger.error(f"Formato incorrecto en línea: {line}")
            
            return content_dict
        except Exception as e:
            logger.error(f"Error al leer el archivo de contenido: {str(e)}")
            return {}
    
    def update_content(self):
        """Actualiza la lista de contenido según el archivo externo"""
        while self.running:
            current_content = self.read_content_file()  # Ahora devuelve un diccionario {path: duration}
            
            # Cerrar elementos que ya no están en la lista
            paths_to_remove = set(self.content_items.keys()) - set(current_content.keys())
            for path in paths_to_remove:
                self.content_items[path].close()
                del self.content_items[path]
                logger.info(f"Elemento eliminado: {path}")
                
            # Añadir nuevos elementos o actualizar duraciones
            for path, duration in current_content.items():
                if path not in self.content_items:
                    self.content_items[path] = ContentItem(path, duration)
                    logger.info(f"Nuevo elemento añadido: {path} (duración: {duration}s)")
                else:
                    # Actualizar duración si ha cambiado
                    if self.content_items[path].duration != duration:
                        self.content_items[path].duration = duration
                        logger.info(f"Duración actualizada para {path}: {duration}s")
            
            # Señalizar que hay contenido disponible si se encontraron elementos
            if self.content_items and not self.content_available.is_set():
                self.content_available.set()
                
            time.sleep(self.read_interval)
    
    def rotate_content(self):
        """Rota entre los elementos de contenido disponibles"""
        while self.running:
            # Esperar a que haya contenido disponible (o salir si termina el programa)
            if not self.content_items:
                logger.warning("No hay elementos de contenido disponibles")
                # Esperar hasta que haya contenido o timeout cada segundo para comprobar self.running
                self.content_available.wait(1)
                if not self.running:
                    break
                if not self.content_items:
                    continue
            
            # Si hay un elemento activo, minimizarlo en lugar de cerrarlo
            if self.current_item:
                logger.info(f"Preparando transición desde: {self.current_item.path}")
                minimized = self.current_item.minimize()
                if not minimized:
                    # Si no se pudo minimizar, podemos intentar cerrarlo
                    logger.warning(f"No se pudo minimizar {self.current_item.path}, intentando cerrar")
                    self.current_item.close()
                
                # Pausa más larga después de minimizar para permitir que el escritorio se muestre
                time.sleep(1.5)  # Incrementado para permitir la transición
            
            # Seleccionar el siguiente elemento
            items = list(self.content_items.values())
            if not items:
                time.sleep(1)  # Espera corta si de alguna manera no hay items
                continue
                
            # Si el elemento actual es el último, volver al primero
            if self.current_item not in items:
                index = 0
            else:
                current_index = items.index(self.current_item)
                index = (current_index + 1) % len(items)
                
            self.current_item = items[index]
            self.current_item.open(self.config)
            
            # Usar la duración específica del elemento o el valor predeterminado
            display_time = self.current_item.duration if self.current_item.duration else self.rotation_interval
            logger.info(f"Mostrando {self.current_item.path} durante {display_time} segundos")
            
            time.sleep(display_time)
    
    def start(self):
        """Inicia el gestor de signage"""
        logger.info("Iniciando MySignage")
        
        # Verificar contenido inicial inmediatamente antes de iniciar hilos
        initial_content = self.read_content_file()
        for path, duration in initial_content.items():
            self.content_items[path] = ContentItem(path, duration)
            logger.info(f"Nuevo elemento añadido: {path} (duración: {duration}s)")
            
        if self.content_items:
            self.content_available.set()
        
        # Iniciar hilo de actualización de contenido
        update_thread = threading.Thread(target=self.update_content)
        update_thread.daemon = True
        update_thread.start()
        
        # Iniciar hilo de rotación de contenido
        rotation_thread = threading.Thread(target=self.rotate_content)
        rotation_thread.daemon = True
        rotation_thread.start()
        
        try:
            # Mantener el programa en ejecución
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Cerrando MySignage")
            self.running = False
            self.content_available.set()  # Permitir que los hilos de espera salgan
            
            # Cerrar todos los procesos
            for item in self.content_items.values():
                item.close()

if __name__ == "__main__":
    manager = SignageManager()
    manager.start()
