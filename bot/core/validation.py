"""
Validação de entrada.

Regra de ouro do projeto: validar SEMPRE antes de agir. Entrada inválida é
recusada na hora, com mensagem clara, sem chamar nenhuma ferramenta ou API.

- IPs são validados com o módulo `ipaddress` da biblioteca padrão.
- Domínios são validados com uma expressão regular adequada (formato de hostname).
"""

import ipaddress
import re

# Expressão regular para um nome de domínio válido.
# Explicando por partes, para quem está começando:
#   (?!-)            -> um rótulo não pode começar com hífen
#   [A-Za-z0-9-]{1,63} -> cada rótulo tem de 1 a 63 caracteres (letras, números, hífen)
#   (?<!-)           -> um rótulo não pode terminar com hífen
#   (\.<rótulo>)+    -> pelo menos um ponto separando rótulos (ex.: exemplo.com)
#   [A-Za-z]{2,}     -> a extensão final (TLD) tem só letras, no mínimo 2
_DOMINIO_REGEX = re.compile(
    r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*\.[A-Za-z]{2,}$"
)


def dominio_valido(dominio: str) -> bool:
    """
    Retorna True se o texto tem formato de domínio válido.

    Faz uma limpeza básica (tira espaços) e limita o tamanho total a 253
    caracteres, que é o máximo permitido para um nome de domínio.
    """
    if not dominio:
        return False
    dominio = dominio.strip().lower()
    if len(dominio) > 253:
        return False
    return bool(_DOMINIO_REGEX.match(dominio))


def normalizar_dominio(dominio: str) -> str:
    """Padroniza o domínio (sem espaços, minúsculo) para uso após a validação."""
    return dominio.strip().lower()


def ip_valido(ip: str) -> bool:
    """Retorna True se o texto é um endereço IP (v4 ou v6) válido."""
    if not ip:
        return False
    try:
        ipaddress.ip_address(ip.strip())
        return True
    except ValueError:
        return False


def ip_na_allowlist(ip: str, redes_permitidas: list) -> bool:
    """
    Retorna True se o IP pertence a alguma das redes permitidas.

    Usado pelo /scan: mesmo sendo um IP válido, ele só pode ser escaneado se
    estiver dentro de uma rede autorizada na configuração (ALLOWED_NETWORKS).
    """
    try:
        endereco = ipaddress.ip_address(ip.strip())
    except ValueError:
        return False
    return any(endereco in rede for rede in redes_permitidas)
