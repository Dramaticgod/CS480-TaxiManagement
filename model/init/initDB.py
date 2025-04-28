import sqlite3

# Connect to a database (it will create the DB file if it doesn't exist)
conn = sqlite3.connect('model/TaxiDB.db')

# Read SQL commands from a file
with open('model/init/updatedDB.sql', 'r') as sql_file:
    sql_script = sql_file.read()

# Execute the SQL script
cursor = conn.cursor()
cursor.executescript(sql_script)

# Commit changes and close connection
conn.commit()
conn.close()
