#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sonda_coren.py  -  FASE 1: sondagem do endpoint publico de consulta do COREN-SP
--------------------------------------------------------------------------------
Objetivo: descobrir COMO o site responde, ANTES de escrever o leitor de verdade.
NAO grava nada, NAO acessa o banco, NAO resolve CAPTCHA. So observa e relata.

[ SERVIDOR T-140 ] este script roda aqui (precisa de internet).

Uso:
    cd ~/coren_sonda
    python3 sonda_coren.py --inscricao 123456
    python3 sonda_coren.py --cpf 12345678900

Pegue uma inscricao real de teste com a query q.py que esta no README.
"""

import argparse
import os
import sys
import textwrap

try:
    import requests
    import bs4
except ImportError as e:
    print("Falta biblioteca:", e)
    print("Instale no venv do servidor:  pip install requests beautifulsoup4")
    sys.exit(1)

URL_CONSULTA = "https://servicos.coren-sp.gov.br/consulta-de-profissionais/"
PASTA_SAIDA = "sonda_out"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# Pistas que denunciam que requests+bs4 NAO vao bastar (precisaria de navegador/CAPTCHA)
PISTAS_BLOQUEIO = [
    "g-recaptcha", "grecaptcha", "recaptcha/api.js",   # Google reCAPTCHA
    "hcaptcha", "cf-turnstile",                          # hCaptcha / Cloudflare Turnstile
    "__cf_chl", "cloudflare",                            # desafio Cloudflare
]
# Pistas de SPA (pagina montada por JS -> HTML inicial vem vazio)
PISTAS_SPA = ["react", "vue", "angular", "app.js", "main.js", "__NEXT_DATA__"]


def separador(titulo):
    print("\n" + "=" * 70)
    print(titulo)
    print("=" * 70)


def salvar(nome, conteudo):
    os.makedirs(PASTA_SAIDA, exist_ok=True)
    caminho = os.path.join(PASTA_SAIDA, nome)
    modo = "wb" if isinstance(conteudo, (bytes, bytearray)) else "w"
    with open(caminho, modo) as f:
        f.write(conteudo)
    print(f"  -> salvo: {caminho}")


def procurar_pistas(texto_lower, pistas):
    return sorted({p for p in pistas if p in texto_lower})


def relatar_resposta(res):
    print(f"  HTTP {res.status_code}  |  URL final: {res.url}")
    print(f"  Content-Type: {res.headers.get('Content-Type', '?')}")
    print(f"  Tamanho corpo: {len(res.content)} bytes")
    server = res.headers.get("Server")
    if server:
        print(f"  Server: {server}")


def analisar_html(html):
    baixo = html.lower()

    bloqueios = procurar_pistas(baixo, PISTAS_BLOQUEIO)
    if bloqueios:
        print(f"  [!] Sinais de CAPTCHA/anti-bot: {bloqueios}")
        print("      -> requests+bs4 provavelmente NAO vao passar. Avaliar API paga.")
    else:
        print("  [ok] Nenhum sinal obvio de CAPTCHA/Cloudflare no HTML.")

    spa = procurar_pistas(baixo, PISTAS_SPA)
    if spa:
        print(f"  [!] Sinais de pagina montada por JS (SPA): {spa}")
        print("      -> se o HTML vier 'vazio', o dado chega por chamada AJAX separada.")

    soup = bs4.BeautifulSoup(html, "html.parser")
    forms = soup.find_all("form")
    print(f"  Formularios encontrados: {len(forms)}")
    for i, form in enumerate(forms):
        metodo = (form.get("method") or "GET").upper()
        action = form.get("action") or "(mesma URL)"
        print(f"    - form[{i}]: method={metodo}  action={action}")
        campos = form.find_all(["input", "select", "textarea"])
        for c in campos:
            nome = c.get("name")
            tipo = c.get("type", c.name)
            if nome:
                marca = "  (oculto/token?)" if tipo == "hidden" else ""
                print(f"        campo: name={nome!r} type={tipo}{marca}")
    return forms


def main():
    ap = argparse.ArgumentParser(description="Sonda o endpoint publico do COREN-SP.")
    ap.add_argument("--inscricao", help="numero de inscricao COREN (de teste)")
    ap.add_argument("--cpf", help="CPF do profissional (so digitos)")
    args = ap.parse_args()

    sessao = requests.Session()
    sessao.headers.update({"User-Agent": UA})

    # ---------------------------------------------------------------
    # PASSO 1 - GET da pagina de consulta (ver a estrutura e os riscos)
    # ---------------------------------------------------------------
    separador("PASSO 1  -  GET da pagina de consulta")
    print(f"  Alvo: {URL_CONSULTA}")
    try:
        res = sessao.get(URL_CONSULTA, timeout=20)
    except requests.RequestException as e:
        print(f"  [ERRO] Nao consegui abrir a pagina: {e}")
        sys.exit(2)

    relatar_resposta(res)
    salvar("passo1_get.html", res.text)
    forms = analisar_html(res.text)

    # ---------------------------------------------------------------
    # PASSO 2 - tentar uma consulta (POST no formulario), se pediram
    # ---------------------------------------------------------------
    if not (args.inscricao or args.cpf):
        separador("PASSO 2  -  PULADO")
        print("  Rode de novo com --inscricao ou --cpf para tentar uma consulta real.")
        _resumo()
        return

    separador("PASSO 2  -  tentativa de consulta")
    if not forms:
        print("  [!] Nenhum <form> no HTML inicial.")
        print("      Forte indicio de SPA/AJAX: o campo de busca e enviado por JS")
        print("      para um endpoint que NAO aparece aqui. Precisamos capturar essa")
        print("      chamada no navegador (aba Rede) para saber a URL/JSON real.")
        _resumo()
        return

    # Usa o primeiro formulario como palpite. Preenche o campo cujo name
    # lembre inscricao/cpf/nome e reenvia os campos ocultos (tokens).
    form = forms[0]
    metodo = (form.get("method") or "GET").upper()
    action = form.get("action") or URL_CONSULTA
    if action.startswith("/"):
        action = "https://servicos.coren-sp.gov.br" + action
    elif not action.startswith("http"):
        action = URL_CONSULTA

    dados = {}
    for c in form.find_all(["input", "select", "textarea"]):
        nome = c.get("name")
        if not nome:
            continue
        n = nome.lower()
        if args.inscricao and ("inscri" in n or "numero" in n or "registro" in n):
            dados[nome] = args.inscricao
        elif args.cpf and "cpf" in n:
            dados[nome] = args.cpf
        else:
            dados[nome] = c.get("value", "")  # reenvia hidden/token como veio

    print(f"  {metodo} -> {action}")
    print(f"  Campos enviados: { {k: (v[:20] if v else '') for k, v in dados.items()} }")

    try:
        if metodo == "POST":
            res2 = sessao.post(action, data=dados, timeout=20)
        else:
            res2 = sessao.get(action, params=dados, timeout=20)
    except requests.RequestException as e:
        print(f"  [ERRO] Falha ao consultar: {e}")
        _resumo()
        return

    relatar_resposta(res2)
    salvar("passo2_resposta.html", res2.text)
    procurar_pistas(res2.text.lower(), PISTAS_BLOQUEIO)

    # A resposta traz os dados? Procuro por rotulos que o COREN costuma exibir.
    baixo2 = res2.text.lower()
    rotulos = [r for r in ("situa", "categoria", "inscri", "enfermeir",
                           "tecnic", "auxiliar") if r in baixo2]
    if rotulos:
        print(f"  [ok] A resposta parece conter dados do profissional (rotulos: {rotulos}).")
        print("       Abra sonda_out/passo2_resposta.html para eu ver a estrutura.")
    else:
        print("  [!] Nao achei rotulos esperados na resposta.")
        print("       Pode ser CAPTCHA, sessao/token faltando, ou resposta via AJAX.")

    _resumo()


def _resumo():
    separador("PROXIMO PASSO")
    print(textwrap.dedent("""\
        Me mande de volta:
          1. O que este script imprimiu (copie o terminal inteiro).
          2. O arquivo  sonda_out/passo2_resposta.html  (ou passo1_get.html).
        Com isso eu escrevo o leitor real (parser) + o script de atualizacao.
        Se aparecer CAPTCHA, partimos para o plano B (API paga de consulta).
    """))


if __name__ == "__main__":
    main()
