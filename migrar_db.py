import os
import json
from datetime import datetime
import sqlite3
import pymysql
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

basedir = os.path.abspath(os.path.dirname(__file__))

def exportar_sqlite():
    """
    Exporta todos los datos de SQLite a un archivo JSON.
    """
    print("Exportando datos de SQLite...")
    
    sqlite_db_path = os.path.join(basedir, 'instance', 'unisinu.db')
    
    if not os.path.exists(sqlite_db_path):
        print(f"No se encontró la base de datos SQLite en: {sqlite_db_path}")
        return None
    
    conn = sqlite3.connect(sqlite_db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Obtener todas las tablas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [row['name'] for row in cursor.fetchall()]
    
    datos_exportados = {}
    
    for tabla in tables:
        print(f"  Exportando tabla: {tabla}...")
        cursor.execute(f"SELECT * FROM {tabla}")
        filas = cursor.fetchall()
        
        datos_exportados[tabla] = []
        for fila in filas:
            datos_fila = dict(fila)
            # Convertir valores datetime a string para JSON
            for key, value in datos_fila.items():
                if isinstance(value, datetime):
                    datos_fila[key] = value.isoformat()
            datos_exportados[tabla].append(datos_fila)
    
    conn.close()
    
    # Guardar en archivo JSON
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archivo_exportado = os.path.join(basedir, f"backup_{timestamp}.json")
    
    with open(archivo_exportado, 'w', encoding='utf-8') as f:
        json.dump(datos_exportados, f, ensure_ascii=False, indent=2)
    
    print(f"Datos exportados exitosamente a: {archivo_exportado}")
    return archivo_exportado


def importar_mariadb(archivo_json):
    """
    Importa los datos del JSON a una base de datos MariaDB/MySQL.
    """
    print("Importando datos a MariaDB/MySQL...")
    
    if not os.path.exists(archivo_json):
        print(f"No se encontró el archivo: {archivo_json}")
        return False
    
    with open(archivo_json, 'r', encoding='utf-8') as f:
        datos_importados = json.load(f)
    
    # Configuración de conexión
    host = os.environ.get('DB_HOST', 'localhost')
    puerto = int(os.environ.get('DB_PORT', 3306))
    usuario = os.environ.get('DB_USER', 'root')
    contrasena = os.environ.get('DB_PASSWORD', '')
    nombre_db = os.environ.get('DB_NAME', 'unisinu')
    
    print(f"  Conectando a {host}:{puerto} como {usuario}...")
    
    try:
        # Conectar y crear la base de datos si no existe
        connection = pymysql.connect(
            host=host,
            port=puerto,
            user=usuario,
            password=contrasena,
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{nombre_db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            cursor.execute(f"USE `{nombre_db}`;")
        
        connection.commit()
        connection.close()
        
        # Ahora conectamos a la base de datos específica
        connection = pymysql.connect(
            host=host,
            port=puerto,
            user=usuario,
            password=contrasena,
            database=nombre_db,
            charset='utf8mb4'
        )
        
        # Importar tablas en orden de dependencia
        orden_tablas = ['usuario', 'programa', 'postulacion', 'noticia', 'mensaje_contacto', 'mensaje_chat']
        
        for tabla in orden_tablas:
            if tabla not in datos_importados:
                continue
                
            print(f"  Importando tabla: {tabla}...")
            filas = datos_importados[tabla]
            
            if not filas:
                print(f"    No hay datos para {tabla}")
                continue
            
            # Obtener columnas
            columnas = list(filas[0].keys())
            placeholders = ', '.join(['%s'] * len(columnas))
            columnas_str = ', '.join([f"`{col}`" for col in columnas])
            
            with connection.cursor() as cursor:
                # Desactivar restricciones de llave foránea temporalmente
                cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
                
                for fila in filas:
                    valores = []
                    for col in columnas:
                        val = fila.get(col)
                        # Convertir strings ISO de vuelta a datetime si es necesario
                        if isinstance(val, str) and len(val) > 10 and 'T' in val:
                            try:
                                val = datetime.fromisoformat(val)
                            except:
                                pass
                        valores.append(val)
                    
                    sql = f"INSERT INTO `{tabla}` ({columnas_str}) VALUES ({placeholders})"
                    try:
                        cursor.execute(sql, tuple(valores))
                    except Exception as e:
                        print(f"    ⚠️ Error al insertar en {tabla}: {e}")
                        print(f"       Datos: {fila}")
                
                cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
            
            connection.commit()
            print(f"    {len(filas)} registros importados")
        
        connection.close()
        print(" Importación completada exitosamente!")
        return True
        
    except Exception as e:
        print(f" Error durante la importación: {e}")
        return False


def main():
    print("=" * 70)
    print("HERRAMIENTA DE MIGRACIÓN DE BASE DE DATOS")
    print("=" * 70)
    print("\n1. Exportar datos de SQLite a JSON")
    print("2. Importar datos de JSON a MariaDB/MySQL")
    
    opcion = input("\nSelecciona una opción (1/2): ").strip()
    
    if opcion == '1':
        exportar_sqlite()
    elif opcion == '2':
        archivo = input("Ruta del archivo JSON (ej: backup_20260513_120000.json): ").strip()
        importar_mariadb(archivo)
    else:
        print("Opción inválida.")


if __name__ == "__main__":
    main()
