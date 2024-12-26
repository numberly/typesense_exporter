FROM python:3.12-slim

LABEL maintainer="Solvik Blum <solvik@numberly.com>"

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY typesense_exporter.py /app/typesense_exporter.py

RUN chown -R nobody:nogroup /app

USER nobody:nogroup

EXPOSE 8000

CMD ["python", "typesense_exporter.py", "--port=8000"]

