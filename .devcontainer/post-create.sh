#!/usr/bin/env bash
set -e

if [ -f backend/requirements.txt ]; then
  echo "Instalando dependências do backend..."
  pip3 install --upgrade pip
  pip3 install -r backend/requirements.txt
fi

if [ -f frontend/package.json ]; then
  echo "Instalando dependências do frontend..."
  cd frontend
  npm install
  cd ..
fi

echo "Ambiente pronto."