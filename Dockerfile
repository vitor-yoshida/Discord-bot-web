# =========================================================================
# Dockerfile do Metis Bot — build em duas etapas (multi-stage).
#
# Etapa 1 (builder): usa a imagem oficial do Go só para compilar as ferramentas
#   gau e subfinder, que são escritas em Go.
# Etapa 2 (final): imagem Python enxuta, onde instalamos nmap, copiamos os
#   binários Go da etapa 1, instalamos as dependências Python e rodamos o bot
#   como um usuário NÃO-root.
# =========================================================================

# ---------- Etapa 1: compilar as ferramentas Go ----------
FROM golang:1.27-bookworm AS builder

# Por que não um simples "go install ferramenta@versão"?
# Porque ele compila com as dependências EXATAS que a ferramenta declarou — e
# algumas delas têm CVEs já corrigidos em versões mais novas (o gau, por
# exemplo, não tem release desde 2024). O Trivy do CI reprova isso.
#
# A solução: para cada ferramenta, criamos um módulo Go "de fachada" que
# depende dela, forçamos as dependências vulneráveis para versões corrigidas
# com "go get" e só então compilamos. O Go sempre escolhe a MAIOR versão
# pedida de cada dependência, então as correções prevalecem.
#
# Cada ferramenta tem seu próprio módulo para que as dependências de uma não
# interfiram nas da outra. Versões fixadas = build reprodutível.

# gau v2.2.4 + dependências corrigidas.
WORKDIR /build/gau
RUN go mod init metis/gau \
    && go get github.com/lc/gau/v2/cmd/gau@v2.2.4 \
    && go get golang.org/x/net@v0.59.0 \
              golang.org/x/text@v0.42.0 \
              github.com/sirupsen/logrus@v1.10.2 \
              github.com/valyala/fasthttp@v1.74.0 \
    && go build -trimpath -ldflags="-s -w" -o /out/gau github.com/lc/gau/v2/cmd/gau

# subfinder v2.16.0 + dependências corrigidas.
WORKDIR /build/subfinder
RUN go mod init metis/subfinder \
    && go get github.com/projectdiscovery/subfinder/v2/cmd/subfinder@v2.16.0 \
    && go get golang.org/x/net@v0.59.0 \
              golang.org/x/text@v0.42.0 \
              golang.org/x/crypto@v0.57.0 \
    && go build -trimpath -ldflags="-s -w" -o /out/subfinder github.com/projectdiscovery/subfinder/v2/cmd/subfinder

# ---------- Etapa 2: imagem final ----------
FROM python:3.11-slim-bookworm

# Instala o nmap (única ferramenta que vem via apt) e limpa o cache do apt
# para manter a imagem pequena.
RUN apt-get update \
    && apt-get install -y --no-install-recommends nmap ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copia os binários Go compilados na etapa anterior para um diretório no PATH.
COPY --from=builder /out/gau /usr/local/bin/gau
COPY --from=builder /out/subfinder /usr/local/bin/subfinder

# Cria um usuário sem privilégios para rodar o bot (boa prática de segurança:
# se algo der errado, o processo não tem poderes de root).
RUN useradd --create-home --shell /usr/sbin/nologin metis

WORKDIR /app

# Instala as dependências Python primeiro (aproveita o cache de camadas do
# Docker: enquanto o requirements.txt não muda, esta camada é reaproveitada).
#
# Depois de instalar, REMOVEMOS pip, setuptools e wheel: o bot não precisa
# deles para rodar (só para instalar), e eles trazem pacotes embutidos com CVEs
# conhecidos (ex.: msgpack dentro do pip, jaraco.context dentro do setuptools).
# Menos software na imagem = menos superfície de ataque e Trivy limpo.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip uninstall -y setuptools wheel \
    && python -m pip uninstall -y pip

# Copia o código do bot.
COPY bot/ ./bot/

# A partir daqui, tudo roda como o usuário não-root.
USER metis

# Sobe o bot.
CMD ["python", "-m", "bot.main"]
