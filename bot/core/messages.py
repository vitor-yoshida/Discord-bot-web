"""
Todas as mensagens exibidas ao usuário, centralizadas e em português do Brasil.

Motivo de existir: as instruções pedem que TODO texto mostrado no Discord
(respostas, erros, descrições de comandos e parâmetros) esteja em pt-BR e
concentrado num só lugar. Assim, para ajustar um texto, você mexe só aqui.

Convenção:
- ERRO_*  -> mensagens de erro padronizadas.
- DESC_*  -> descrições de comandos e parâmetros (aparecem na interface do slash).
- Algumas entradas são funções, porque o texto varia conforme um valor.
"""

# ---------------------------------------------------------------------------
# Mensagens de erro (usadas em todos os comandos)
# ---------------------------------------------------------------------------

ERRO_SEM_PERMISSAO = (
    "⛔ Você não tem o cargo necessário para usar este comando."
)
ERRO_DOMINIO_INVALIDO = (
    "❌ Domínio inválido. Envie algo como `exemplo.com`."
)
ERRO_IP_INVALIDO = (
    "❌ IP inválido. Envie um endereço IPv4 ou IPv6 válido."
)
ERRO_IP_FORA_ALLOWLIST = (
    "⛔ Este IP não está dentro das redes permitidas para o /scan. "
    "Só é possível escanear alvos autorizados na configuração."
)
ERRO_PERFIL_INVALIDO = (
    "❌ Perfil de scan inválido. Escolha um dos perfis disponíveis."
)
ERRO_TIPO_INVALIDO = (
    "❌ Tipo inválido. Confira as opções disponíveis para este comando."
)
ERRO_HOST_INACESSIVEL = (
    "🚫 Não foi possível alcançar o host. Verifique se o alvo está ativo e acessível."
)
ERRO_DOMINIO_INEXISTENTE = (
    "❌ Este domínio não existe (o DNS respondeu NXDOMAIN). Confira se digitou certo."
)
ERRO_DECODE = (
    "❌ Não foi possível decodificar. Verifique se o valor corresponde ao tipo escolhido."
)
ERRO_TIMEOUT = (
    "⏱️ A operação demorou demais e foi cancelada (timeout). Tente novamente mais tarde."
)
ERRO_API_INDISPONIVEL = (
    "🌐 O serviço externo está indisponível ou fora do ar no momento. Tente mais tarde."
)
ERRO_API_LIMITE = (
    "🚦 Limite de requisições do serviço externo excedido. Aguarde um pouco e tente de novo."
)
ERRO_FERRAMENTA_AUSENTE = (
    "🛠️ A ferramenta necessária não está instalada no sistema onde o bot roda."
)
ERRO_RESULTADO_VAZIO = (
    "ℹ️ A consulta foi feita, mas nenhum resultado foi encontrado."
)
ERRO_CONCORRENCIA = (
    "⚙️ Há muitos comandos pesados rodando agora. Aguarde alguns segundos e tente novamente."
)
ERRO_INESPERADO = (
    "💥 Ocorreu um erro inesperado. A equipe pode conferir os logs para detalhes."
)

# ---------------------------------------------------------------------------
# Mensagens de status / sucesso
# ---------------------------------------------------------------------------

STATUS_PROCESSANDO = "⏳ Processando, um momento..."


def resultado_como_arquivo(nome_comando: str) -> str:
    """Texto que acompanha um resultado longo enviado como arquivo .txt."""
    return f"📎 O resultado de `/{nome_comando}` ficou grande, então segue em anexo."


# ---------------------------------------------------------------------------
# Descrições dos comandos (aparecem na interface de slash commands)
# ---------------------------------------------------------------------------

# Grupo: reconhecimento via binário
DESC_SCAN = "Roda um scan de portas com nmap em um alvo autorizado."
DESC_SCAN_ALVO = "Endereço IP do alvo (precisa estar nas redes permitidas)."
DESC_SCAN_PERFIL = "Perfil do scan: rapido (portas comuns) ou servicos (detecta serviços)."

DESC_GAU = "Coleta endpoints/URLs conhecidos de um domínio de forma passiva (gau)."
DESC_GAU_DOMINIO = "Domínio a consultar, ex.: exemplo.com."

DESC_SUBFINDER = "Enumera subdomínios de um domínio (subfinder)."
DESC_SUBFINDER_DOMINIO = "Domínio a consultar, ex.: exemplo.com."

# Grupo: reconhecimento via API/biblioteca
DESC_CRT = "Busca subdomínios em certificados via crt.sh."
DESC_CRT_DOMINIO = "Domínio a consultar, ex.: exemplo.com."

DESC_IPINFO = "Consulta informações de um IP no ipinfo.io."
DESC_IPINFO_IP = "Endereço IP a consultar, ex.: 8.8.8.8."

DESC_WHOIS = "Consulta dados de registro (WHOIS) de um domínio."
DESC_WHOIS_DOMINIO = "Domínio a consultar, ex.: exemplo.com."

DESC_DNS = "Consulta os registros DNS (A, AAAA, MX, NS, TXT, CNAME) de um domínio."
DESC_DNS_DOMINIO = "Domínio a consultar, ex.: exemplo.com."

# Grupo: utilitários
DESC_DECODE = "Decodifica um valor (base64, url, hex ou jwt)."
DESC_DECODE_TIPO = "Tipo de decodificação: base64, url, hex ou jwt."
DESC_DECODE_VALOR = "Texto a decodificar."

DESC_HASH = "Gera o hash de um texto (md5, sha1 ou sha256)."
DESC_HASH_ALGORITMO = "Algoritmo: md5, sha1 ou sha256."
DESC_HASH_VALOR = "Texto a ser transformado em hash."

DESC_PAYLOADS = "Mostra uma lista de payloads comuns de teste (xss ou sqli)."
DESC_PAYLOADS_TIPO = "Categoria de payloads: xss ou sqli."
