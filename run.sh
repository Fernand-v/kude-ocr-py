#!/usr/bin/env bash
# Levanta el microservicio OCR en el puerto 8000.
set -e
cd "$(dirname "$0")"
# oneDNN/MKLDNN rompe el inference en algunas CPUs con paddle 3.x.
export FLAGS_use_mkldnn=0
# Limita hilos -> menos picos de RAM/CPU.
export OMP_NUM_THREADS=4
# Evita el chequeo de conectividad a los hosters de modelos en cada arranque.
export PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True
# Red de seguridad: techo de memoria virtual (8 GB). Si el OCR se dispara,
# muere SOLO este proceso, no el sistema. Subir si hace falta.
ulimit -v 8000000 || true
./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 "$@"
