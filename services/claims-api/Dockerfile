FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# System deps kept minimal; scikit-learn/numpy ship manylinux wheels.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Bake synthetic data + trained models into the image so the container is
# self-contained and reproducible (seeding into Mongo happens at runtime).
RUN python -m data_gen.generate_data && python -m ml.train_models

RUN chmod +x entrypoint.sh
EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
