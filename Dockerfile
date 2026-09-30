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

# Versões fixadas das ferramentas (reprodutibilidade).
RUN go install github.com/lc/gau/v2/cmd/gau@v2.2.4 \
    && go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@v2.16.0

# ---------- Etapa 2: imagem final ----------
FROM python:3.11-slim-bookworm

# Instala o nmap (única ferramenta que vem via apt) e limpa o cache do apt
# para manter a imagem pequena.
RUN apt-get update \
    && apt-get install -y --no-install-recommends nmap ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copia os binários Go compilados na etapa anterior para um diretório no PATH.
COPY --from=builder /go/bin/gau /usr/local/bin/gau
COPY --from=builder /go/bin/subfinder /usr/local/bin/subfinder

# Cria um usuário sem privilégios para rodar o bot (boa prática de segurança:
# se algo der errado, o processo não tem poderes de root).
RUN useradd --create-home --shell /usr/sbin/nologin metis

WORKDIR /app

# Instala as dependências Python primeiro (aproveita o cache de camadas do
# Docker: enquanto o requirements.txt não muda, esta camada é reaproveitada).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código do bot.
COPY bot/ ./bot/

# A partir daqui, tudo roda como o usuário não-root.
USER metis

# Sobe o bot.
CMD ["python", "-m", "bot.main"]
