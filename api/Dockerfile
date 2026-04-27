# Użyj oficjalnego, lekkiego obrazu Pythona.
# Warianty „slim” są mniejsze i lepiej nadają się do usług produkcyjnych.
FROM python:3.10-slim

WORKDIR /app

# Ustaw zmienne środowiskowe.
# PYTHONDONTWRITEBYTECODE: Zapobiega zapisywaniu plików pyc przez Python na dysku.
# PYTHONUNBUFFERED: Zapewnia natychmiastowe przesyłanie logów do strumienia (niezbędne dla logów Docker).
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Zainstaluj zależności.
# --no-cache-dir ogranicza rozmiar obrazu.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Skopiuj pliki kodu aplikacji.
COPY *.py .
COPY .env .

# Utwórz użytkownika niebędącego administratorem ze względów bezpieczeństwa i przejdź do niego
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Uruchom aplikację
CMD ["python", "app.py"]