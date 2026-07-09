#!/usr/bin/env bash
#
# gerar_deck_id.sh
# =================
# Gera um deck_id numérico único para usar no decks.csv do anki_gerador.py
#
# Uso:
#   ./gerar_deck_id.sh
#
# O intervalo (2^30 a 2^31-1) garante um número grande o suficiente para
# evitar colisões e dentro do limite que o genanki/Anki aceita (inteiro de 32 bits).

set -euo pipefail

MIN=1073741824   # 2^30
MAX=2147483647   # 2^31 - 1

id=$(( RANDOM * RANDOM % (MAX - MIN) + MIN ))

echo "$id"
