"""
Leitura e validação das variáveis de ambiente.

Toda configuração do bot (tokens, cargo autorizado, redes permitidas) vem de
variáveis de ambiente — nunca fica escrita no código. Este módulo lê essas
variáveis uma única vez e as deixa disponíveis para o resto do programa.

Se estiver rodando sem Docker, as variáveis podem vir de um arquivo .env
(carregado com python-dotenv). Com Docker, o docker-compose já injeta o .env.
"""

import ipaddress
import os

from dotenv import load_dotenv

# Carrega o arquivo .env, se existir, para dentro das variáveis de ambiente.
# Em produção (Docker) as variáveis já vêm do ambiente; aqui é só conveniência
# para quem roda localmente.
load_dotenv()


class ConfigError(Exception):
    """Erro de configuração: falta uma variável ou ela está com valor inválido."""


def _get_required(name: str) -> str:
    """Lê uma variável obrigatória. Se faltar, para o bot com mensagem clara."""
    valor = os.getenv(name)
    if not valor:
        raise ConfigError(
            f"Variável de ambiente obrigatória ausente: {name}. "
            f"Confira o seu arquivo .env (use o .env.example como base)."
        )
    return valor


def _parse_networks(bruto: str) -> list:
    """
    Converte a string 'ALLOWED_NETWORKS' numa lista de redes.

    Aceita redes separadas por vírgula, ex.: "192.168.0.0/16,10.0.0.0/8".
    Cada item é validado como uma rede IP real; item inválido para o bot.
    """
    redes = []
    for item in bruto.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            # strict=False permite escrever "192.168.0.10/24" sem erro.
            redes.append(ipaddress.ip_network(item, strict=False))
        except ValueError as exc:
            raise ConfigError(
                f"Rede inválida em ALLOWED_NETWORKS: '{item}' ({exc})."
            ) from exc
    if not redes:
        raise ConfigError(
            "ALLOWED_NETWORKS está vazia. Defina ao menos uma rede permitida "
            "para o comando /scan (ex.: 192.168.0.0/16)."
        )
    return redes


class Config:
    """
    Guarda toda a configuração já validada.

    É criada uma vez em main.py e passada para os cogs, para que ninguém
    precise ler os.getenv espalhado pelo código.
    """

    def __init__(self) -> None:
        # Segredos — obrigatórios.
        self.discord_token: str = _get_required("DISCORD_TOKEN")
        self.ipinfo_token: str = _get_required("IPINFO_TOKEN")

        # Cargo autorizado — precisa ser um número (ID do Discord).
        role_bruto = _get_required("AUTHORIZED_ROLE_ID")
        try:
            self.authorized_role_id: int = int(role_bruto)
        except ValueError as exc:
            raise ConfigError(
                f"AUTHORIZED_ROLE_ID precisa ser um número (o ID do cargo), "
                f"mas veio: '{role_bruto}'."
            ) from exc

        # Redes permitidas para o /scan.
        self.allowed_networks = _parse_networks(_get_required("ALLOWED_NETWORKS"))

        # GUILD_ID é OPCIONAL e serve só para desenvolvimento.
        # Se preenchido, os comandos são sincronizados só nesse servidor, o que
        # é INSTANTÂNEO (ótimo para testar). Se vazio, o sync é global, que
        # funciona em qualquer servidor mas pode levar até ~1h para aparecer.
        guild_bruto = os.getenv("GUILD_ID", "").strip()
        if guild_bruto:
            try:
                self.guild_id = int(guild_bruto)
            except ValueError as exc:
                raise ConfigError(
                    f"GUILD_ID, se preenchido, precisa ser um número (o ID do "
                    f"servidor), mas veio: '{guild_bruto}'."
                ) from exc
        else:
            self.guild_id = None
