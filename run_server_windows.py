from waitress import serve
import socket
from app import app

if __name__ == "__main__":
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    print("\n" + "="*60)
    print("SERVIDOR DE PRODUCCIÓN ACTIVO (WAITRESS)")
    print("="*60)
    print(f"IP LOCAL: {local_ip}")
    print(f"ACCESO LOCAL: http://127.0.0.1:5000")
    print(f"ACCESO RED: http://{local_ip}:5000")
    print("="*60 + "\n")
    
    # Configuración de Waitress para producción
    serve(
        app,
        host="0.0.0.0",
        port=5000,
        threads=12,  # Ajusta según tu CPU (número de núcleos * 2)
        connection_limit=1000,
        channel_timeout=120,
        url_prefix="",
        ident="Movilidad-Conocimiento-Server"
    )
