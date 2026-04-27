import psycopg2
import time
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class DbCredentials:
    user: str = os.getenv("DB_USER")
    password: str = os.getenv("DB_PASSWORD")
    host: str = os.getenv("DB_HOST")
    name: str = os.getenv("DB_NAME")

db_cred = DbCredentials()

def get_connection():
    retries = 5
    while retries > 0:
        try:
            return psycopg2.connect(
                host=db_cred.host,
                dbname=db_cred.name,
                user=db_cred.user,
                password=db_cred.password
            )
        except Exception as e:
            print(f"Błąd połączenia z bazą: {e}. Ponawiam za 2 sekundy...")
            retries -= 1
            time.sleep(2)
    raise Exception("Nie można połączyć się z bazą danych.")