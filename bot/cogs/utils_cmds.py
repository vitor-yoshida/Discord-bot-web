"""
Cog de utilitários de apoio a estudos: /decode, /hash, /payloads.

São comandos de processamento LOCAL — não acessam a rede nem rodam binários.
Mesmo assim, seguem as mesmas regras: checagem de cargo, defer, mensagens em
pt-BR centralizadas e tratamento de erro explícito.
"""

import base64
import hashlib
import json
import urllib.parse

import discord
from discord import app_commands
from discord.ext import commands

from ..core import authorization, formatting, messages
from ..core.config import Config
from ..core.logging_setup import log_comando


# Listas de payloads comuns usados em estudos/CTF. São exemplos didáticos.
_PAYLOADS = {
    "xss": [
        "<script>alert(1)</script>",
        "\"><script>alert(1)</script>",
        "<img src=x onerror=alert(1)>",
        "<svg onload=alert(1)>",
        "javascript:alert(1)",
        "'\"><svg/onload=alert(1)>",
    ],
    "sqli": [
        "' OR '1'='1",
        "' OR '1'='1' -- ",
        "admin' -- ",
        "' UNION SELECT NULL-- ",
        "1; DROP TABLE users-- ",
        "' AND SLEEP(5)-- ",
    ],
}


class UtilsCog(commands.Cog):
    """Agrupa os comandos utilitários locais."""

    def __init__(self, bot: commands.Bot, config: Config) -> None:
        self.bot = bot
        self.config = config

    def _autorizado(self, interaction: discord.Interaction) -> bool:
        """Atalho para a checagem de cargo."""
        return authorization.tem_permissao(interaction, self.config.authorized_role_id)

    # -- /decode -----------------------------------------------------------
    @app_commands.command(name="decode", description=messages.DESC_DECODE)
    @app_commands.describe(tipo=messages.DESC_DECODE_TIPO, valor=messages.DESC_DECODE_VALOR)
    @app_commands.choices(
        tipo=[
            app_commands.Choice(name="base64", value="base64"),
            app_commands.Choice(name="url", value="url"),
            app_commands.Choice(name="hex", value="hex"),
            app_commands.Choice(name="jwt", value="jwt"),
        ]
    )
    async def decode(
        self,
        interaction: discord.Interaction,
        tipo: app_commands.Choice[str],
        valor: str,
    ) -> None:
        if not self._autorizado(interaction):
            await interaction.response.send_message(
                messages.ERRO_SEM_PERMISSAO, ephemeral=True
            )
            return

        # Comandos locais são rápidos, mas mantemos o defer por consistência.
        await interaction.response.defer(thinking=True)
        usuario = str(interaction.user)

        try:
            resultado = self._decodificar(tipo.value, valor)
        except Exception:  # noqa: BLE001 (qualquer falha de decode vira msg amigável)
            log_comando(usuario, "decode", sucesso=False, detalhe=f"tipo={tipo.value}")
            await formatting.responder_erro(interaction, messages.ERRO_DECODE)
            return

        log_comando(usuario, "decode", sucesso=True, detalhe=f"tipo={tipo.value}")
        await formatting.responder_resultado(
            interaction,
            nome_comando="decode",
            titulo=f"Decode ({tipo.value})",
            corpo=resultado,
            monospaco=True,
        )

    def _decodificar(self, tipo: str, valor: str) -> str:
        """Faz a decodificação conforme o tipo. Levanta exceção em caso de erro."""
        if tipo == "base64":
            # validate=True garante que caracteres inválidos causem erro.
            return base64.b64decode(valor, validate=True).decode("utf-8", errors="replace")
        if tipo == "url":
            return urllib.parse.unquote(valor)
        if tipo == "hex":
            return bytes.fromhex(valor).decode("utf-8", errors="replace")
        if tipo == "jwt":
            return self._decodificar_jwt(valor)
        # Não deve chegar aqui por causa das choices, mas ficamos seguros.
        raise ValueError("tipo desconhecido")

    @staticmethod
    def _decodificar_jwt(token: str) -> str:
        """
        Decodifica header e payload de um JWT (sem validar assinatura).

        Um JWT tem 3 partes separadas por ponto: header.payload.assinatura.
        Aqui só mostramos header e payload em JSON legível — é um utilitário de
        estudo, não uma verificação de segurança do token.
        """
        partes = token.split(".")
        if len(partes) < 2:
            raise ValueError("JWT precisa ter ao menos header e payload")

        def _b64url(segmento: str) -> str:
            # Base64 URL-safe pode vir sem o '=' de preenchimento; recompomos.
            padding = "=" * (-len(segmento) % 4)
            bruto = base64.urlsafe_b64decode(segmento + padding)
            # Reindenta o JSON para ficar legível.
            return json.dumps(json.loads(bruto), indent=2, ensure_ascii=False)

        header = _b64url(partes[0])
        payload = _b64url(partes[1])
        return f"HEADER:\n{header}\n\nPAYLOAD:\n{payload}"

    # -- /hash -------------------------------------------------------------
    @app_commands.command(name="hash", description=messages.DESC_HASH)
    @app_commands.describe(
        algoritmo=messages.DESC_HASH_ALGORITMO, valor=messages.DESC_HASH_VALOR
    )
    @app_commands.choices(
        algoritmo=[
            app_commands.Choice(name="md5", value="md5"),
            app_commands.Choice(name="sha1", value="sha1"),
            app_commands.Choice(name="sha256", value="sha256"),
        ]
    )
    async def hash(
        self,
        interaction: discord.Interaction,
        algoritmo: app_commands.Choice[str],
        valor: str,
    ) -> None:
        if not self._autorizado(interaction):
            await interaction.response.send_message(
                messages.ERRO_SEM_PERMISSAO, ephemeral=True
            )
            return

        await interaction.response.defer(thinking=True)
        usuario = str(interaction.user)

        # hashlib.new aceita o nome do algoritmo diretamente.
        digest = hashlib.new(algoritmo.value, valor.encode("utf-8")).hexdigest()

        log_comando(usuario, "hash", sucesso=True, detalhe=f"algoritmo={algoritmo.value}")
        await formatting.responder_resultado(
            interaction,
            nome_comando="hash",
            titulo=f"Hash ({algoritmo.value})",
            corpo=digest,
            monospaco=True,
        )

    # -- /payloads ---------------------------------------------------------
    @app_commands.command(name="payloads", description=messages.DESC_PAYLOADS)
    @app_commands.describe(tipo=messages.DESC_PAYLOADS_TIPO)
    @app_commands.choices(
        tipo=[
            app_commands.Choice(name="xss", value="xss"),
            app_commands.Choice(name="sqli", value="sqli"),
        ]
    )
    async def payloads(
        self,
        interaction: discord.Interaction,
        tipo: app_commands.Choice[str],
    ) -> None:
        if not self._autorizado(interaction):
            await interaction.response.send_message(
                messages.ERRO_SEM_PERMISSAO, ephemeral=True
            )
            return

        await interaction.response.defer(thinking=True)
        usuario = str(interaction.user)

        lista = _PAYLOADS.get(tipo.value, [])
        if not lista:
            await formatting.responder_erro(interaction, messages.ERRO_RESULTADO_VAZIO)
            return

        corpo = "\n".join(lista)
        log_comando(usuario, "payloads", sucesso=True, detalhe=f"tipo={tipo.value}")
        await formatting.responder_resultado(
            interaction,
            nome_comando="payloads",
            titulo=f"Payloads de teste ({tipo.value})",
            corpo=corpo,
            monospaco=True,
        )


async def setup(bot: commands.Bot) -> None:
    """
    Ponto de entrada do cog para o discord.py.

    O objeto Config é guardado em bot.metis_config (definido em main.py) para
    que os cogs tenham acesso à configuração já validada.
    """
    await bot.add_cog(UtilsCog(bot, bot.metis_config))
