import sqlite3
from datetime import date

today = date.today().isoformat() # Today's date

# Allows running a read-only query in the database
def run_query(query):
    try:
        with sqlite3.connect("file:../movimientos.db?mode=ro", uri=True) as ro_connection:
            return ro_connection.execute(query).fetchall()
    except sqlite3.Error:
        return None

# Returns the total balance of the user bank account
def check_balance():
    balance = run_query("SELECT SUM(importe) FROM transaccion")
    if balance is None or balance[0][0] is None:
        return None
    
    return float(balance[0][0])

# Allow the user to send a Bizum and adds the movement to the bank account
def send_bizum(receiver, amount):
    balance = check_balance()
    if balance is None:
        return "Error en la base de datos..."

    elif amount <= 0:
        return "La cantidad del Bizum no puede ser de nula o negativa."

    elif amount > balance:
        return "La cantidad del Bizum supera al saldo de su cuenta."
    
    try:
        with sqlite3.connect("../movimientos.db") as w_connection:
            w_connection.execute("INSERT INTO transaccion (fecha, importe, concepto, categoria) VALUES (?, ?, ?, ?)",
                                (today, -amount, f"Bizum a {receiver}", "Otros"))
        
        return f"Bizum de {amount}€ enviado a {receiver} correctamente."
    
    except sqlite3.Error:
        return "Error en la base de datos..."

# Checks if the query is a SELECT and contains no more than one 
def valid_query(query):
    query = query.lower()
    return query.startswith("select") and query.rstrip(";").count(";") == 0

# Checks whether the query accesses the transaction table
def table_query(query):
    query = query.lower()
    return "from transaccion" in query