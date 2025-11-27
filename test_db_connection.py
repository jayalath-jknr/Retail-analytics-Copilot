import sqlite3

conn = sqlite3.connect('data/northwind.sqlite')
cursor = conn.cursor()
cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = [row[0] for row in cursor.fetchall()]
print('Tables found:', len(tables))
for table in tables[:10]:
    print(f'  - {table}')
conn.close()
print('\nDatabase connection successful!')
