# Metis Bot

Bot de Discord escrito em Python (discord.py, com slash commands) para apoiar estudos de
reconhecimento e segurança. Ele reúne, num só lugar, ferramentas de linha de comando, consultas
a serviços públicos e utilitários de apoio, sempre com validação de entrada, controle de acesso
por cargo e execução segura.

> ⚠️ **Uso responsável:** os comandos de reconhecimento devem ser usados apenas em alvos
> próprios ou com autorização explícita do dono. Você é responsável pelo uso que faz da ferramenta.

---

## O que o bot faz

Os comandos são divididos em três grupos.

### Reconhecimento via binário externo
Executam ferramentas instaladas no sistema, sempre via subprocess assíncrono, com argumentos
passados como lista (nunca `shell=True`) e com timeout.

| Comando | Descrição | Exemplo |
| --- | --- | --- |
| `/scan alvo:<ip> perfil:<rapido\|servicos>` | Roda o **nmap** com perfis pré-definidos, validando o IP contra uma allowlist de redes. | `/scan alvo:192.168.0.10 perfil:rapido` |
| `/gau dominio:<dominio>` | Coleta endpoints de forma passiva com **gau** (GetAllURLs). | `/gau dominio:exemplo.com` |
| `/subfinder dominio:<dominio>` | Enumera subdomínios com **subfinder** (ProjectDiscovery). | `/subfinder dominio:exemplo.com` |

### Reconhecimento via API ou biblioteca
Não usam subprocess; consultam serviços ou bibliotecas Python.

| Comando | Descrição | Exemplo |
| --- | --- | --- |
| `/crt dominio:<dominio>` | Consulta o **crt.sh** (JSON) e deduplica os subdomínios encontrados. | `/crt dominio:exemplo.com` |
| `/ipinfo ip:<ip>` | Consulta o **ipinfo.io** usando um token lido de variável de ambiente. | `/ipinfo ip:8.8.8.8` |
| `/whois dominio:<dominio>` | Usa **python-whois** e organiza registrante, datas e servidores DNS. | `/whois dominio:exemplo.com` |
| `/dns dominio:<dominio>` | Usa **dnspython** para consultar os registros A, AAAA, MX, NS, TXT e CNAME. | `/dns dominio:exemplo.com` |

### Utilitários de apoio a estudos
Processamento local, sem rede.

| Comando | Descrição | Exemplo |
| --- | --- | --- |
| `/decode tipo:<base64\|url\|hex\|jwt> valor:<texto>` | Decodifica o valor conforme o tipo. | `/decode tipo:base64 valor:aGVsbG8=` |
| `/hash algoritmo:<md5\|sha1\|sha256> valor:<texto>` | Gera o hash do valor. | `/hash algoritmo:sha256 valor:senha` |
| `/payloads tipo:<xss\|sqli>` | Devolve uma lista de payloads comuns para teste. | `/payloads tipo:xss` |

---

## Estrutura do projeto

```
Metis-bot/
├── bot/
│   ├── __init__.py
│   ├── main.py                 # ponto de entrada: cria o bot, carrega os cogs, sobe
│   ├── cogs/                   # um arquivo por grupo de comandos
│   │   ├── __init__.py
│   │   ├── recon_bin.py        # /scan, /gau, /subfinder (binários externos)
│   │   ├── recon_api.py        # /crt, /ipinfo, /whois, /dns (APIs e bibliotecas)
│   │   └── utils_cmds.py       # /decode, /hash, /payloads (local)
│   └── core/                   # código compartilhado entre os cogs
│       ├── __init__.py
│       ├── config.py           # leitura das variáveis de ambiente
│       ├── validation.py       # validação de domínios e IPs
│       ├── formatting.py       # embeds, corte de texto longo, anexo .txt
│       ├── messages.py         # todas as mensagens em pt-BR, centralizadas
│       ├── authorization.py    # checagem do cargo autorizado
│       ├── runner.py           # subprocess assíncrono seguro + limite de concorrência
│       └── logging_setup.py    # configuração do logging no console
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .gitignore
├── .env.example
├── requirements.txt
├── intructions.md
└── README.md
```

**Por que essa divisão?** Cada grupo de comandos vira um *cog* (módulo do discord.py), o que
mantém cada arquivo curto e com uma responsabilidade só. A pasta `core/` guarda o que é comum
(validação, mensagens, formatação, segurança), evitando repetição e deixando um ponto único para
ajustes — por exemplo, todos os textos em português ficam em `messages.py`.

---

## Pré-requisitos

- Conta no Discord e permissão para adicionar um bot a um servidor.
- **Docker** e **Docker Compose** (forma recomendada de rodar), ou
- **Python 3.11+** e os binários `nmap`, `gau` e `subfinder` instalados (forma alternativa).

---

## 1. Criar a aplicação e o bot no Discord

1. Acesse o **Discord Developer Portal**: https://discord.com/developers/applications
2. Clique em **New Application**, dê um nome (ex.: *Metis*) e confirme.
3. No menu lateral, vá em **Bot** → **Add Bot**.
4. Em **Privileged Gateway Intents**, ative **Server Members Intent** (necessário para checar cargos).
5. Ainda na aba **Bot**, clique em **Reset Token** e copie o token — ele vai no `.env`
   (guarde com cuidado; nunca coloque no código nem no repositório).
6. Para convidar o bot ao servidor, vá em **OAuth2 → URL Generator**:
   - Em **Scopes**, marque `bot` e `applications.commands`.
   - Em **Bot Permissions**, marque no mínimo `Send Messages`, `Embed Links` e `Attach Files`.
   - Copie a URL gerada, abra no navegador e escolha o servidor.
7. Pegue o **ID do cargo** que poderá usar os comandos: ative o *Modo Desenvolvedor* no Discord
   (Configurações → Avançado), clique com o botão direito no cargo e em **Copiar ID**.

---

## 2. Configurar o `.env`

Copie o modelo e preencha com seus valores:

```bash
cp .env.example .env
```

Variáveis esperadas (veja `.env.example`):

| Variável | O que é |
| --- | --- |
| `DISCORD_TOKEN` | Token do bot (passo 1). |
| `IPINFO_TOKEN` | Token da API do ipinfo.io. |
| `AUTHORIZED_ROLE_ID` | ID do cargo autorizado a usar os comandos. |
| `ALLOWED_NETWORKS` | Redes permitidas para o `/scan`, separadas por vírgula (ex.: `192.168.0.0/16,10.0.0.0/8`). |

O `.env` está no `.gitignore` e no `.dockerignore` — ele nunca entra no repositório nem na imagem.

---

## 3. Rodar com Docker (recomendado)

```bash
docker compose up --build -d
```

O `docker-compose.yml` lê as variáveis do `.env`, e o container reinicia sozinho se cair
(`restart: unless-stopped`). Para acompanhar os logs:

```bash
docker compose logs -f
```

Para parar:

```bash
docker compose down
```

---

## 4. Rodar sem Docker (alternativa)

Instale os binários necessários no sistema:

- **nmap** — https://nmap.org/download.html
- **gau** — https://github.com/lc/gau
- **subfinder** — https://github.com/projectdiscovery/subfinder

Depois:

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Linux/macOS:  source .venv/bin/activate
pip install -r requirements.txt
python -m bot.main
```

---

## Observações de segurança embutidas no bot

- Entrada validada antes de qualquer ação (IPs com `ipaddress`, domínios com validação própria).
- `/scan` só aceita perfis pré-definidos e alvos dentro da allowlist de redes.
- Binários executados sem shell, com argumentos em lista e com timeout.
- No máximo 2 comandos "pesados" (com binário) ao mesmo tempo.
- Cada comando só roda para membros com o cargo autorizado.
- Segredos apenas por variável de ambiente; tokens nunca aparecem nos logs.
- O bot nunca mostra stack traces ao usuário — erros detalhados vão só para o log.

---

## Manutenção segura das dependências

As versões estão **fixadas** (`requirements.txt` e `Dockerfile`) para builds reprodutíveis.
O lado negativo é que versões fixadas envelhecem e podem acumular vulnerabilidades (CVEs).
Para não depender de checagem manual, o repositório inclui o **Dependabot**
(`.github/dependabot.yml`): ele abre Pull Requests automáticos quando surge uma atualização,
priorizando correções de segurança. Você revisa e só aprova o que fizer sentido — os pins
continuam existindo, mas deixam de ser esquecidos.

O Dependabot cobre:
- **pip** — as dependências do `requirements.txt`.
- **docker** — as imagens base do `Dockerfile` (`python:3.11-slim-bookworm`, `golang:1.27-bookworm`).
- **github-actions** — quando houver workflows em `.github/workflows/`.

**Limitação conhecida:** o Dependabot **não** acompanha o `gau` e o `subfinder`, porque eles
são compilados dentro do Dockerfile, não por um gerenciador que ele entenda. O mesmo vale para
as dependências Go que o Dockerfile força para versões corrigidas (`golang.org/x/net`,
`x/text`, `x/crypto`, `logrus`, `fasthttp`). Quando o Trivy do CI apontar um CVE novo num
desses binários, atualize a versão correspondente nas linhas `go get` do `Dockerfile` (o próprio
relatório do Trivy mostra a versão que corrige). Para as ferramentas em si, acompanhe os
*releases* nos repositórios oficiais (links na seção "Rodar sem Docker").

### Pipeline de CI/segurança (`.github/workflows/ci.yml`)

Enquanto o Dependabot **avisa** sobre versões novas, o pipeline de CI **escaneia** o que já
está no código. Ele roda a cada push na `main` e a cada Pull Request, com três verificações:

1. **Sanidade** — compila todos os módulos Python (`compileall`) para pegar erro de sintaxe.
2. **Auditoria de dependências** — `pip-audit` procura CVEs conhecidos nas versões fixadas do
   `requirements.txt`; se achar, o PR é reprovado.
3. **Build e scan do container** — constrói a imagem e roda o **Trivy** para:
   - CVEs na imagem (SO + Python + binários — cobre inclusive `gau`/`subfinder`), reprovando
     apenas por falhas que já têm correção (`ignore-unfixed`);
   - **segredos** vazados e **más configurações** no repositório.

Assim, uma dependência vulnerável ou um segredo esquecido barram a mudança antes do merge,
independentemente de como entraram no projeto.
