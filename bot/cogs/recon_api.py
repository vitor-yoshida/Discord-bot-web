"""
Cog de reconhecimento via API/biblioteca: /crt, /ipinfo, /whois, /dns.

Nenhum destes comandos usa subprocess. Eles consultam serviços na web
(crt.sh, ipinfo.io) ou bibliotecas Python (python-whois, dnspython).

Todos seguem o mesmo esqueleto:
1. Checa o cargo autorizado.
2. Valida a entrada (domínio ou IP).
3. defer() por causa do limite de 3 segundos do Discord.
4. Faz a consulta tratando os erros esperados um a um.
5. Formata e responde (embed ou arquivo .txt se longo).
"""

import asyncio

import aiohttp
import discord
import dns.asyncresolver
import dns.exception
import dns.resolver
import whois
from discord import app_commands
from discord.ext import commands

from ..core import authorization, formatting, messages, validation
from ..core.config import Config
from ..core.logging_setup import log_comando, obter_logger

logger = obter_logger()

# Timeout padrão (segundos) para chamadas de rede deste cog.
_TIMEOUT_HTTP = 15


class ReconApiCog(commands.Cog):
    """Agrupa os comandos de reconhecimento via API/biblioteca."""

    def __init__(self, bot: commands.Bot, config: Config) -> None:
        self.bot = bot
        self.config = config

    def _autorizado(self, interaction: discord.Interaction) -> bool:
        return authorization.tem_permissao(interaction, self.config.authorized_role_id)

    # -- /crt --------------------------------------------------------------
    @app_commands.command(name="crt", description=messages.DESC_CRT)
    @app_commands.describe(dominio=messages.DESC_CRT_DOMINIO)
    async def crt(self, interaction: discord.Interaction, dominio: str) -> None:
        if not self._autorizado(interaction):
            await interaction.response.send_message(
                messages.ERRO_SEM_PERMISSAO, ephemeral=True
            )
            return

        if not validation.dominio_valido(dominio):
            await interaction.response.send_message(
                messages.ERRO_DOMINIO_INVALIDO, ephemeral=True
            )
            return

        dominio = validation.normalizar_dominio(dominio)
        await interaction.response.defer(thinking=True)
        usuario = str(interaction.user)

        url = f"https://crt.sh/?q=%25.{dominio}&output=json"
        try:
            timeout = aiohttp.ClientTimeout(total=_TIMEOUT_HTTP)
            async with aiohttp.ClientSession(timeout=timeout) as sessao:
                async with sessao.get(url) as resposta:
                    if resposta.status == 429:
                        raise _LimiteExcedido()
                    if resposta.status >= 500:
                        raise _ServicoIndisponivel()
                    dados = await resposta.json(content_type=None)
        except asyncio.TimeoutError:
            await self._falha(interaction, usuario, "crt", messages.ERRO_TIMEOUT)
            return
        except _LimiteExcedido:
            await self._falha(interaction, usuario, "crt", messages.ERRO_API_LIMITE)
            return
        except (_ServicoIndisponivel, aiohttp.ClientError, ValueError):
            await self._falha(interaction, usuario, "crt", messages.ERRO_API_INDISPONIVEL)
            return

        # Extrai e deduplica os subdomínios do campo name_value.
        subdominios = set()
        for item in dados or []:
            nomes = str(item.get("name_value", "")).split("\n")
            for nome in nomes:
                nome = nome.strip().lower().lstrip("*.")
                if nome:
                    subdominios.add(nome)

        if not subdominios:
            await self._falha(interaction, usuario, "crt", messages.ERRO_RESULTADO_VAZIO)
            return

        ordenados = sorted(subdominios)
        corpo = f"Total: {len(ordenados)}\n\n" + "\n".join(ordenados)
        log_comando(usuario, "crt", sucesso=True, detalhe=f"dominio={dominio}")
        await formatting.responder_resultado(
            interaction, "crt", f"Subdomínios de {dominio}", corpo
        )

    # -- /ipinfo -----------------------------------------------------------
    @app_commands.command(name="ipinfo", description=messages.DESC_IPINFO)
    @app_commands.describe(ip=messages.DESC_IPINFO_IP)
    async def ipinfo(self, interaction: discord.Interaction, ip: str) -> None:
        if not self._autorizado(interaction):
            await interaction.response.send_message(
                messages.ERRO_SEM_PERMISSAO, ephemeral=True
            )
            return

        if not validation.ip_valido(ip):
            await interaction.response.send_message(
                messages.ERRO_IP_INVALIDO, ephemeral=True
            )
            return

        ip = ip.strip()
        await interaction.response.defer(thinking=True)
        usuario = str(interaction.user)

        url = f"https://ipinfo.io/{ip}/json"
        # O token vai no header Authorization, nunca na URL nem no log.
        headers = {"Authorization": f"Bearer {self.config.ipinfo_token}"}
        try:
            timeout = aiohttp.ClientTimeout(total=_TIMEOUT_HTTP)
            async with aiohttp.ClientSession(timeout=timeout) as sessao:
                async with sessao.get(url, headers=headers) as resposta:
                    if resposta.status == 429:
                        raise _LimiteExcedido()
                    if resposta.status >= 500:
                        raise _ServicoIndisponivel()
                    dados = await resposta.json(content_type=None)
        except asyncio.TimeoutError:
            await self._falha(interaction, usuario, "ipinfo", messages.ERRO_TIMEOUT)
            return
        except _LimiteExcedido:
            await self._falha(interaction, usuario, "ipinfo", messages.ERRO_API_LIMITE)
            return
        except (_ServicoIndisponivel, aiohttp.ClientError, ValueError):
            await self._falha(
                interaction, usuario, "ipinfo", messages.ERRO_API_INDISPONIVEL
            )
            return

        if not dados or dados.get("bogon"):
            await self._falha(interaction, usuario, "ipinfo", messages.ERRO_RESULTADO_VAZIO)
            return

        # Monta um embed com os campos mais úteis, quando presentes.
        embed = formatting.criar_embed(f"IPInfo — {ip}")
        campos = [
            ("Hostname", "hostname"),
            ("Cidade", "city"),
            ("Região", "region"),
            ("País", "country"),
            ("Organização", "org"),
            ("Coordenadas", "loc"),
        ]
        for rotulo, chave in campos:
            if dados.get(chave):
                embed.add_field(name=rotulo, value=str(dados[chave]), inline=True)

        log_comando(usuario, "ipinfo", sucesso=True, detalhe=f"ip={ip}")
        await interaction.edit_original_response(content=None, embed=embed)

    # -- /whois ------------------------------------------------------------
    @app_commands.command(name="whois", description=messages.DESC_WHOIS)
    @app_commands.describe(dominio=messages.DESC_WHOIS_DOMINIO)
    async def whois_cmd(self, interaction: discord.Interaction, dominio: str) -> None:
        if not self._autorizado(interaction):
            await interaction.response.send_message(
                messages.ERRO_SEM_PERMISSAO, ephemeral=True
            )
            return

        if not validation.dominio_valido(dominio):
            await interaction.response.send_message(
                messages.ERRO_DOMINIO_INVALIDO, ephemeral=True
            )
            return

        dominio = validation.normalizar_dominio(dominio)
        await interaction.response.defer(thinking=True)
        usuario = str(interaction.user)

        # python-whois é síncrono e faz rede; rodamos numa thread separada com
        # timeout para não travar o loop de eventos do bot.
        try:
            dados = await asyncio.wait_for(
                asyncio.to_thread(whois.whois, dominio), timeout=_TIMEOUT_HTTP
            )
        except asyncio.TimeoutError:
            await self._falha(interaction, usuario, "whois", messages.ERRO_TIMEOUT)
            return
        except Exception as exc:  # noqa: BLE001 (a lib lança vários tipos; tratamos genérico)
            # Detalhe técnico só no log; o usuário recebe a mensagem amigável.
            logger.warning("Falha em /whois dominio=%s: %r", dominio, exc)
            await self._falha(
                interaction, usuario, "whois", messages.ERRO_API_INDISPONIVEL
            )
            return

        # Se não veio nome de domínio, provavelmente não há registro.
        if not dados or not dados.get("domain_name"):
            await self._falha(interaction, usuario, "whois", messages.ERRO_RESULTADO_VAZIO)
            return

        embed = formatting.criar_embed(f"WHOIS — {dominio}")
        embed.add_field(name="Registrante", value=self._txt(dados.get("registrar")), inline=False)
        embed.add_field(name="Criação", value=self._txt(dados.get("creation_date")), inline=True)
        embed.add_field(name="Expiração", value=self._txt(dados.get("expiration_date")), inline=True)
        embed.add_field(name="Servidores DNS", value=self._txt(dados.get("name_servers")), inline=False)

        log_comando(usuario, "whois", sucesso=True, detalhe=f"dominio={dominio}")
        await interaction.edit_original_response(content=None, embed=embed)

    # -- /dns --------------------------------------------------------------
    @app_commands.command(name="dns", description=messages.DESC_DNS)
    @app_commands.describe(dominio=messages.DESC_DNS_DOMINIO)
    async def dns_cmd(self, interaction: discord.Interaction, dominio: str) -> None:
        if not self._autorizado(interaction):
            await interaction.response.send_message(
                messages.ERRO_SEM_PERMISSAO, ephemeral=True
            )
            return

        if not validation.dominio_valido(dominio):
            await interaction.response.send_message(
                messages.ERRO_DOMINIO_INVALIDO, ephemeral=True
            )
            return

        dominio = validation.normalizar_dominio(dominio)
        await interaction.response.defer(thinking=True)
        usuario = str(interaction.user)

        tipos = ["A", "AAAA", "MX", "NS", "TXT", "CNAME"]
        resolver = dns.asyncresolver.Resolver()
        resolver.lifetime = _TIMEOUT_HTTP  # tempo total por consulta

        linhas = []
        encontrados = 0  # quantos tipos devolveram ao menos um registro
        timeouts = 0     # quantos tipos estouraram o tempo
        for tipo in tipos:
            try:
                resposta = await resolver.resolve(dominio, tipo)
                registros = [r.to_text() for r in resposta]
                linhas.append(f"{tipo}:")
                linhas.extend(f"  {r}" for r in registros)
                encontrados += 1
            except dns.resolver.NXDOMAIN:
                # NXDOMAIN diz respeito ao NOME, não ao tipo: se o domínio não
                # existe, nenhuma outra consulta vai adiantar. Paramos aqui.
                await self._falha(
                    interaction, usuario, "dns", messages.ERRO_DOMINIO_INEXISTENTE
                )
                return
            except dns.resolver.NoAnswer:
                # O domínio existe, só não tem esse tipo de registro — normal.
                linhas.append(f"{tipo}: (nenhum)")
            except dns.exception.Timeout:
                linhas.append(f"{tipo}: (timeout)")
                timeouts += 1
            except dns.exception.DNSException:
                linhas.append(f"{tipo}: (erro na consulta)")

        # Todas as consultas estouraram o tempo: é um timeout, não um resultado.
        if timeouts == len(tipos):
            await self._falha(interaction, usuario, "dns", messages.ERRO_TIMEOUT)
            return

        # Nenhum tipo trouxe registro: resultado vazio.
        if encontrados == 0:
            await self._falha(interaction, usuario, "dns", messages.ERRO_RESULTADO_VAZIO)
            return

        conteudo = "\n".join(linhas)

        log_comando(usuario, "dns", sucesso=True, detalhe=f"dominio={dominio}")
        await formatting.responder_resultado(
            interaction, "dns", f"Registros DNS de {dominio}", conteudo, monospaco=True
        )

    # -- auxiliares --------------------------------------------------------
    @staticmethod
    def _txt(valor) -> str:
        """Transforma qualquer valor do WHOIS num texto legível para o embed."""
        if valor is None:
            return "—"
        if isinstance(valor, (list, tuple)):
            itens = [str(v) for v in valor if v]
            return "\n".join(dict.fromkeys(itens)) or "—"  # remove duplicados
        return str(valor)

    async def _falha(
        self,
        interaction: discord.Interaction,
        usuario: str,
        comando: str,
        mensagem: str,
    ) -> None:
        """Registra o erro no log e responde ao usuário com a mensagem amigável."""
        log_comando(usuario, comando, sucesso=False, detalhe=mensagem)
        await formatting.responder_erro(interaction, mensagem)


# Exceções internas curtas para diferenciar tipos de falha HTTP.
class _LimiteExcedido(Exception):
    pass


class _ServicoIndisponivel(Exception):
    pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ReconApiCog(bot, bot.metis_config))
