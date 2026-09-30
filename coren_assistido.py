#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
coren_assistido.py — coleta ASSISTIDA da situação de registro no COREN-SP.

Por que "assistida": a página pública do COREN-SP protege a consulta com
reCAPTCHA. Este programa NÃO resolve nem tenta burlar o CAPTCHA — ele abre
o navegador, preenche a inscrição e PARA para um humano marcar o "não sou
robô" e clicar em Consultar. Só depois ele lê e interpreta o resultado.
É a aplicação prática do Selenium citado no fim da aula (tarefas que
requests+BeautifulSoup sozinhos não vencem).

Roda numa máquina COM TELA (o servidor headless não serve).

Uso:
    python3 coren_assistido.py --inscricao 123456
    python3 coren_assistido.py --lista inscricoes.txt   # uma por linha

Requisitos: ver requirements.txt (selenium usa o Selenium Manager, que
baixa o driver do Chrome automaticamente — precisa do Chrome instalado).
"""

import argparse
import os
import sys
import time

from parser_coren import parse_resultado, situacao_para_flag

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import Select
except ImportError:
    print("Selenium não instalado. Rode:  pip install -r requirements.txt")
    sys.exit(1)

URL = "https://servicos.coren-sp.gov.br/consulta-de-profissionais/"
PASTA = "capturas"

# Nomes dos campos descobertos pela sondagem (sonda_coren.py)
CAMPO_CRITERIO = "app_busca_de_profissionais[criterio]"
CAMPO_VALOR = "app_busca_de_profissionais[valor]"


def abrir_navegador():
    opts = webdriver.ChromeOptions()
    opts.add_argument("--start-maximized")
    # NUNCA headless aqui: o humano precisa ver e resolver o CAPTCHA.
    return webdriver.Chrome(options=opts)


def preencher(driver, inscricao):
    driver.get(URL)
    time.sleep(1.5)
    # seleciona o critério "inscrição" quando existir esse <select>
    try:
        sel = Select(driver.find_element(By.NAME, CAMPO_CRITERIO))
        for opcao in sel.options:
            if "inscri" in (opcao.text or "").lower():
                sel.select_by_visible_text(opcao.text)
                break
    except Exception:
        pass  # se o layout mudar, o humano ajusta na tela
    # digita o número da inscrição
    try:
        campo = driver.find_element(By.NAME, CAMPO_VALOR)
        campo.clear()
        campo.send_keys(str(inscricao))
    except Exception:
        print("  [aviso] não achei o campo do número — preencha na tela.")


def coletar_uma(driver, inscricao):
    print(f"\n=== Inscrição {inscricao} ===")
    preencher(driver, inscricao)
    print("  >> No navegador: resolva o CAPTCHA e clique em CONSULTAR.")
    input("  >> Quando o resultado aparecer na tela, tecle ENTER aqui... ")

    html = driver.page_source
    os.makedirs(PASTA, exist_ok=True)
    caminho = os.path.join(PASTA, f"resultado_{inscricao}.html")
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  HTML salvo em {caminho}")

    dados = parse_resultado(html)
    dados["flag_sistema"] = situacao_para_flag(dados.get("situacao"))
    for k, v in dados.items():
        print(f"  {k:16}: {v}")
    return dados


def main():
    ap = argparse.ArgumentParser(description="Coleta assistida do COREN-SP.")
    ap.add_argument("--inscricao", help="uma inscrição")
    ap.add_argument("--lista", help="arquivo com uma inscrição por linha")
    args = ap.parse_args()

    if args.lista:
        with open(args.lista, encoding="utf-8") as f:
            inscricoes = [l.strip() for l in f if l.strip()]
    elif args.inscricao:
        inscricoes = [args.inscricao]
    else:
        ap.error("informe --inscricao ou --lista")

    driver = abrir_navegador()
    resultados = []
    try:
        for insc in inscricoes:
            resultados.append(coletar_uma(driver, insc))
    finally:
        input("\nTecle ENTER para fechar o navegador... ")
        driver.quit()

    ativos = sum(1 for r in resultados if r.get("flag_sistema") == "A")
    print(f"\nResumo: {len(resultados)} consultada(s) | {ativos} ativa(s).")


if __name__ == "__main__":
    main()
