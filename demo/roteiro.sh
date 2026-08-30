#!/usr/bin/env bash
# demo/roteiro.sh - teste de aceitacao do projeto inteiro (SPEC.md secao 10).
#
# E a definicao de pronto. Existe desde a primeira hora, mesmo quebrado:
# enquanto uma trilha nao entregou, o passo dela falha e o roteiro diz qual.
#
# Uso:
#   bash demo/roteiro.sh            # roteiro completo
#   bash demo/roteiro.sh --base     # so a Trilha 0 (fundacao + bases)
#
# Windows: rodar no Git Bash. O interpretador Python e resolvido abaixo.

set -u
cd "$(dirname "$0")/.."

# --- resolve o interpretador -----------------------------------------------
if [ -n "${PYTHON:-}" ]; then
  PY="$PYTHON"
elif [ -x "$LOCALAPPDATA/Programs/Python/Python312/python.exe" ]; then
  PY="$LOCALAPPDATA/Programs/Python/Python312/python.exe"
elif command -v python3 >/dev/null 2>&1; then
  PY=python3
else
  PY=python
fi
export PYTHONIOENCODING=utf-8
echo "interpretador: $PY"

falhas=0
passo() {
  echo
  echo "------------------------------------------------------------------"
  echo ">> $1"
  echo "------------------------------------------------------------------"
  shift
  if "$@"; then
    echo "   [OK]"
  else
    echo "   [FALHOU] - trilha responsavel ainda nao entregou este passo"
    falhas=$((falhas + 1))
  fi
}

# --- Trilha 0 - fundacao ----------------------------------------------------
passo "R-01 base de embargos do Ibama (baixar, inspecionar, recortar)" \
      "$PY" ferramentas/baixar_ibama.py
passo "seed.py - 60 produtores, ~100 talhoes, 3 lotes, arquivos crus" \
      "$PY" seed.py
passo "testes da fundacao - contagens e conflitos plantados" \
      "$PY" ferramentas/testar_fundacao.py

if [ "${1:-}" = "--base" ]; then
  echo
  echo "=================================================================="
  echo " roteiro --base concluido com $falhas falha(s)"
  echo "=================================================================="
  exit $falhas
fi

# --- Trilhas A a D ----------------------------------------------------------
passo "Trilha A - ingestao dos 60 produtores" \
      "$PY" ingestao.py --todos
passo "Trilha B - verificacao de todos os talhoes" \
      "$PY" verificacao.py --tudo
passo "Trilha C - dossie do lote CAC-2026-114" \
      "$PY" dossie.py --lote CAC-2026-114
passo "Demo - injecao do embargo sobre o talhao do produtor nos 3 lotes" \
      "$PY" demo/injetar_embargo.py

echo
echo "=================================================================="
echo " roteiro concluido com $falhas falha(s)"
echo
echo " Agora, para o cenario ao vivo:"
echo "   terminal 1:  $PY vigilancia.py"
echo "   terminal 2:  streamlit run app.py"
echo "   terminal 3:  $PY demo/injetar_embargo.py"
echo " Esperado: a vigilancia reage em segundos, tres lotes mudam de status,"
echo " uma excecao aparece na fila e tres dossies novos ficam disponiveis."
echo "=================================================================="
exit $falhas
