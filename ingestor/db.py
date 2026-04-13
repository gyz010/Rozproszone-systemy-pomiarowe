import psycopg2
import time

DB_HOST = "database"
DB_NAME = "abcd_db"
DB_USER = "admin"
DB_PASSWORD = "admin_pass1234"

def get_connection():
    retries = 5
    while retries > 0:
        try:
            return psycopg2.connect(
                host=DB_HOST,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD
            )
        except Exception as e:
            print(f"Błąd połączenia z bazą: {e}. Ponawiam za 2 sekundy...")
            retries -= 1
            time.sleep(2)
    raise Exception("Nie można połączyć się z bazą danych.")