#!/bin/bash

# Script de inicio para Linux con Gunicorn
# Uso: chmod +x run_server_linux.sh && ./run_server_linux.sh

# Obtener IP local
LOCAL_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "============================================================"
echo "  SERVIDOR DE PRODUCCIÓN ACTIVO (GUNICORN)"
echo "============================================================"
echo "  IP LOCAL: $LOCAL_IP"
echo "  ACCESO LOCAL: http://127.0.0.1:5000"
echo "  ACCESO RED: http://$LOCAL_IP:5000"
echo "============================================================"
echo ""

# Ejecutar Gunicorn
# workers = (2 * número de núcleos CPU) + 1
# threads = ajusta según tu necesidad
gunicorn --workers 4 --threads 4 --timeout 120 --bind 0.0.0.0:5000 app:app
