#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parser_coren.py — extrai os campos do resultado da consulta COREN-SP.

Isolado de propósito: o parsing é a parte "BeautifulSoup" do projeto e fica
testável sozinha. Os seletores finais são calibrados contra um resultado
REAL (capturado pelo coren_assistido.py) — ver README, seção "Calibração".
Enquanto isso, usa uma estratégia defensiva de rótulo->valor que funciona
para a maioria das páginas de consulta cadastral.
"""

import re
import bs4

CAMPOS = ("nome", "numero", "categoria", "tipo_inscricao", "situacao", "data_inicio")

# Rótulos que costumam aparecer na página do COREN -> chave interna
ROTULOS = {
    "nome": ("nome",),
    "numero": ("inscri", "número", "numero", "registro"),
    "categoria": ("categoria",),
    "tipo_inscricao": ("tipo de inscri", "tipo inscri", "tipo"),
    "situacao": ("situa",),
    "data_inicio": ("data de início", "data de inicio", "início", "inicio", "data"),
}


def _texto_limpo(s):
    return re.sub(r"\s+", " ", (s or "").strip())


def _por_tabela(soup):
    """Estratégia 1: se o resultado vier numa <table> de 'rótulo | valor'."""
    achados = {}
    for tr in soup.find_all("tr"):
        celulas = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
        if len(celulas) >= 2:
            rotulo = celulas[0].lower()
            valor = _texto_limpo(celulas[1])
            for chave, sinonimos in ROTULOS.items():
                if chave not in achados and any(s in rotulo for s in sinonimos):
                    achados[chave] = valor
    return achados


def _por_rotulo_valor(soup):
    """Estratégia 2: varre o texto visível procurando 'Rótulo: valor'."""
    achados = {}
    texto = soup.get_text("\n", strip=True)
    linhas = [l for l in texto.split("\n") if l.strip()]
    for i, linha in enumerate(linhas):
        baixo = linha.lower()
        for chave, sinonimos in ROTULOS.items():
            if chave in achados:
                continue
            if any(s in baixo for s in sinonimos):
                # "Rótulo: valor" na mesma linha?
                if ":" in linha:
                    valor = _texto_limpo(linha.split(":", 1)[1])
                    if valor:
                        achados[chave] = valor
                        continue
                # senão, valor pode estar na próxima linha
                if i + 1 < len(linhas):
                    achados[chave] = _texto_limpo(linhas[i + 1])
    return achados


def parse_resultado(html):
    """Recebe o HTML do resultado e devolve um dict com os CAMPOS.
    Campos não encontrados voltam como None."""
    soup = bs4.BeautifulSoup(html, "html.parser")
    dados = {k: None for k in CAMPOS}

    for estrategia in (_por_tabela, _por_rotulo_valor):
        for chave, valor in estrategia(soup).items():
            if dados.get(chave) is None and valor:
                dados[chave] = valor

    return dados


def situacao_para_flag(situacao):
    """Converte a situação textual do COREN no flag do sistema (A/I).
    Ver README: gravado em CUIDADORES.CONCORDATA (campo legado reutilizado)."""
    if not situacao:
        return None
    s = situacao.strip().lower()
    return "A" if ("ativo" in s or "regular" in s) else "I"


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8", errors="replace") as f:
            resultado = parse_resultado(f.read())
        for k, v in resultado.items():
            print(f"{k:16}: {v}")
        print(f"{'flag_sistema':16}: {situacao_para_flag(resultado['situacao'])}")
    else:
        print("uso: python3 parser_coren.py resultado.html")
