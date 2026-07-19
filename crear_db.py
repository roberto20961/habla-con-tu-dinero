import sqlite3

connection = sqlite3.connect("movimientos.db")
cursor = connection.cursor()

cursor.execute("""

    CREATE TABLE IF NOT EXISTS transaccion(
        id INTEGER PRIMARY KEY,
        fecha TEXT CHECK(fecha LIKE '____-__-__'),
        importe REAL,
        concepto TEXT,
        categoria TEXT CHECK(categoria IN ('Ocio', 'Restaurantes', 'Supers e Hipers', 'Salud', 'Bienestar y Belleza', 
                                           'Transporte', 'Hogar', 'Donaciones', 'Educación', 'Ropa y calzado', 
                                           'Electrónica y Electrodomésticos', 'Otros', 'Ingresos'))
    )

""")

connection.commit()
connection.close()