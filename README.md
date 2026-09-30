# -FATEC_2SEM26_ED-COREN_WEBSCRAPING
# Web Scraping aplicado: conferência de registro profissional no COREN-SP

**Autor:** Fernando José Manesco
**Curso:** Fatec Rio Claro — Linguagem de Programação II
**Professor:** Me. Orlando Saraiva Júnior
**Contexto:** aplicação real na Manesco Enfermagem Ltda. (Cuidadores da Saúde — home care)

---

## 1. Problema

Uma empresa de home care é responsável, junto com o profissional, por garantir
que quem presta assistência de enfermagem tenha registro regular no conselho
de classe COREN. Escalar uma cuidadora com registro suspenso ou cancelado é
risco sanitário e jurídico. Hoje essa conferência é manual, um a um.

Este projeto automatiza a coleta da **situação cadastral** de cada profissional
de enfermagem (auxiliar, técnico e enfermeiro) a partir da consulta pública do
COREN-SP, e grava o resultado no cadastro da empresa.

> **Origem na aula:** é o mesmo padrão do mini-projeto `xkcd.py` — baixar uma
> página, extrair um dado, repetir para uma lista — só que aplicado a um
> problema real da empresa.

## 2. Fundamentação — as bibliotecas da aula

| Biblioteca | Papel no projeto |
|---|---|
| `requests` | baixar o HTML da página de consulta (etapa de sondagem) |
| `BeautifulSoup` (`bs4`) | analisar o HTML: achar o formulário, os campos e depois extrair os dados do resultado |
| `Selenium` | dirigir um navegador real na etapa que `requests` não vence (ver §3) |

## 3. Metodologia e a descoberta central

O desenvolvimento seguiu três passos — e o passo 2 é o achado que dá valor ao
trabalho:

**Passo 1 — Sondagem (`sonda_coren.py`, requests + BeautifulSoup).**
Baixei a página e analisei sua estrutura. Descobri um formulário POST com os
campos `criterio`, `valor` e um token CSRF.

**Passo 2 — O obstáculo real: reCAPTCHA.**
A sondagem detectou na página os scripts `recaptcha/api.js` e o campo
`g-recaptcha-response`. Ou seja: a consulta é protegida por **reCAPTCHA do
Google**. Um POST via `requests` sem o token do CAPTCHA apenas devolve o
próprio formulário — nenhum dado retorna. Isso confirma, na prática, a
limitação que o próprio material da disciplina antecipa: *"às vezes a URL não é
fácil de encontrar, ou o site exige que você faça login primeiro; o Selenium
dará aos seus programas o poder de executar essas tarefas sofisticadas."*

**Passo 3 — Solução: Selenium com humano no loop (`coren_assistido.py`).**
Como a conferência é anual e o volume é baixo, a solução escolhida é
**assistida**: o programa abre o Chrome, preenche a inscrição e **para** para
um operador resolver o CAPTCHA e clicar em Consultar. Só então o programa lê o
resultado (`driver.page_source`) e o entrega ao `BeautifulSoup` para extração.

> **Ética / limite claro:** o programa **não resolve nem burla** o CAPTCHA —
> quem o resolve é a pessoa. Isso mantém o uso dentro dos termos do site. É
> automação *assistida*, não elusão de proteção.

## 4. Arquitetura dos arquivos

```
coren_scraper_fatec/
├── sonda_coren.py       # Passo 1-2: requests+bs4, inspeciona a página e detecta o CAPTCHA
├── coren_assistido.py   # Passo 3: Selenium abre o navegador; humano resolve o CAPTCHA
├── parser_coren.py      # BeautifulSoup: extrai nome/inscrição/categoria/situação/data
├── requirements.txt
└── README.md
```

O `parser_coren.py` é isolado de propósito: a extração é testável sozinha
(`python3 parser_coren.py resultado.html`) e converte a situação textual do
COREN no flag do sistema (`A`/`I`).

## 5. Como executar

Numa máquina **com tela** e com o Google Chrome instalado:

```
# 1. dependências
pip install -r requirements.txt

# 2. (opcional) sondar a página e ver a detecção do CAPTCHA
python3 sonda_coren.py --inscricao 123456

# 3. coleta assistida (abre o Chrome; você resolve o CAPTCHA)
python3 coren_assistido.py --inscricao 123456
# ou uma fila:
python3 coren_assistido.py --lista inscricoes.txt
```

A cada inscrição o programa salva o HTML do resultado em `capturas/` e imprime
os campos extraídos.

## 6. Integração com o sistema da empresa

No ecossistema da empresa (FastAPI + Firebird), o resultado alimenta o cadastro
da cuidadora: a situação vira um flag `A`/`I` e a data da conferência é
registrada. A consulta é pública (ato de transparência) e o uso tem finalidade
legítima — o contratante verificando a regularidade da própria equipe —,
respeitando a LGPD (o autor é DPO da empresa).

## 7. Calibração e limitações

- Os seletores do `parser_coren.py` usam uma estratégia defensiva de
  rótulo→valor. Eles são **fixados definitivamente após capturar um resultado
  real** (o `coren_assistido.py` salva esse HTML na primeira execução).
- A solução é dimensionada para **volume baixo e conferência anual**. Para
  monitoramento recorrente e sem intervenção humana, o caminho seria uma API
  paga de consulta (que trata o CAPTCHA na infraestrutura do provedor) — fora
  do escopo deste trabalho.

## 8. Conclusão

O projeto cobre as três ferramentas da aula (`requests`, `BeautifulSoup`,
`Selenium`) e, mais que isso, demonstra o **critério de engenharia** de quando
cada uma se aplica: `requests`+`BeautifulSoup` para páginas abertas, e
`Selenium` (assistido) quando há proteção como o reCAPTCHA. O resultado é uma
ferramenta que já resolve um problema real de compliance da empresa.

## 9. Referências

- SWEIGART, Al. *Automate the Boring Stuff with Python*. No Starch Press, 2015.
- MITCHELL, Ryan. *Web Scraping with Python*. 3. ed. O'Reilly, 2024.
- NAIR, Vineeth G. N. *Getting Started with Beautiful Soup*. Packt, 2014.
