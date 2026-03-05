FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# alembic.ini va script.py.mako yaratish
RUN alembic init alembic_temp && \
    cp /app/alembic.ini /tmp/alembic.ini && \
    cp alembic_temp/script.py.mako /tmp/script.py.mako && \
    rm -rf alembic_temp

COPY . .

# Fayllarni to'g'ri joyga ko'chirish + script_location tuzatish
RUN cp /tmp/alembic.ini . && \
    cp /tmp/script.py.mako alembic/ && \
    mkdir -p alembic/versions && \
    sed -i 's/script_location = alembic_temp/script_location = alembic/' alembic.ini

EXPOSE 8000