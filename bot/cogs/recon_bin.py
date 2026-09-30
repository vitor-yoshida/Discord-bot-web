"""
Cog de reconhecimento via binário externo: /scan, /gau, /subfinder.

Estes são os comandos "pesados": eles executam ferramentas instaladas no
sistema. Por isso passam pelo módulo runner, que garante:
- execução assíncrona e segura (lista de argumentos, sem shell);
- timeout;
- limite de no máximo 2 execuções pesadas ao mesmo tempo.

Regras específicas:
- /scan valida o IP com ipaddress E confere se ele está na allowlist de redes;
  só aceita perfis de scan pré-definidos (nunca argumentos livres do usuário).
"""

import discord
from discord import app_commands
from discord.ext import commands

from ..core import authorization, formatting, messages, runner, validation
from ..core.config import Config
from ..core.logging_setup import log_comando, obter_logger

logger = obter_logger()

# Perfis de scan permitidos. O usuário só escolhe a CHAVE; os argumentos reais
# são fixos aqui, então ele nunca injeta flags arbitrárias no nmap.
_PERFIS_SCAN = {
    "rapido": ["-F"],          # varredura rápida das portas mais comuns
    "servicos": ["-sV", "-F"],  # detecta versões de serviço nas portas comuns
}

# Timeouts (segundos) por ferramenta.
_TIMEOUT_NMAP = 120
_TIMEOUT_GAU = 90
_TIMEOUT_SUBFINDER = 120


def _nmap_host_inacessivel(saida: str) -> bool:
    """
    Detecta, pela saída do nmap, que o alvo não respondeu.

    O nmap termina com código 0 mesmo quando o host está fora do ar — ele só
    avisa no texto ("Host seems down" e "(0 hosts up)" no resumo final). Por
    isso não dá para confiar só no código de saída e olhamos a saída também.
    """
    return "(0 hosts up)" in saida or "Host seems down" in saida


class ReconBinCog(commands.Cog):
    """Agrupa os comandos que executam binários externos."""

    def __init__(self, bot: commands.Bot, config: Config) -> None:
        self.bot = bot
        self.config = config

    def _autorizado(self, interaction: discord.Interaction) -> bool:
        return authorization.tem_permissao(interaction, self.config.authorized_role_id)

    # -- /scan -------------------------------------------------------------
    @app_commands.command(name="scan", description=messages.DESC_SCAN)
    @app_commands.describe(alvo=messages.DESC_SCAN_ALVO, perfil=messages.DESC_SCAN_PERFIL)
    @app_commands.choices(
        perfil=[
            app_commands.Choice(name="rapido", value="rapido"),
            app_commands.Choice(name="servicos", value="servicos"),
        ]
    )
    async def scan(
        self,
        interaction: discord.Interaction,
        alvo: str,
        perfil: app_commands.Choice[str],
    ) -> None:
        if not self._autorizado(interaction):
            await interaction.response.send_message(
                messages.ERRO_SEM_PERMISSAO, ephemeral=True
            )
            return

        # 1) O alvo precisa ser um IP válido.
        if not validation.ip_valido(alvo):
            await interaction.response.send_message(
                messages.ERRO_IP_INVALIDO, ephemeral=True
            )
            return

        # 2) E precisa estar dentro das redes autorizadas.
        if not validation.ip_na_allowlist(alvo, self.config.allowed_networks):
            await interaction.response.send_message(
                messages.ERRO_IP_FORA_ALLOWLIST, ephemeral=True
            )
            return

        # 3) O perfil precisa existir (as choices já garantem, mas conferimos).
        args_perfil = _PERFIS_SCAN.get(perfil.value)
        if args_perfil is None:
            await interaction.response.send_message(
                messages.ERRO_PERFIL_INVALIDO, ephemeral=True
            )
            return

        alvo = alvo.strip()
        # Monta o comando como LISTA. Argumentos fixos + alvo validado no final.
        comando = ["nmap", *args_perfil, alvo]
        await self._executar_binario(
            interaction, "scan", comando, _TIMEOUT_NMAP,
            titulo=f"nmap ({perfil.value}) — {alvo}", detalhe=f"alvo={alvo}",
            host_inacessivel=_nmap_host_inacessivel,
        )

    # -- /gau --------------------------------------------------------------
    @app_commands.command(name="gau", description=messages.DESC_GAU)
    @app_commands.describe(dominio=messages.DESC_GAU_DOMINIO)
    async def gau(self, interaction: discord.Interaction, dominio: str) -> None:
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
        comando = ["gau", dominio]
        await self._executar_binario(
            interaction, "gau", comando, _TIMEOUT_GAU,
            titulo=f"gau — {dominio}", detalhe=f"dominio={dominio}",
        )

    # -- /subfinder --------------------------------------------------------
    @app_commands.command(name="subfinder", description=messages.DESC_SUBFINDER)
    @app_commands.describe(dominio=messages.DESC_SUBFINDER_DOMINIO)
    async def subfinder(self, interaction: discord.Interaction, dominio: str) -> None:
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
        # -silent deixa a saída limpa (só os subdomínios), sem banner.
        comando = ["subfinder", "-silent", "-d", dominio]
        await self._executar_binario(
            interaction, "subfinder", comando, _TIMEOUT_SUBFINDER,
            titulo=f"subfinder — {dominio}", detalhe=f"dominio={dominio}",
        )

    # -- núcleo compartilhado ---------------------------------------------
    async def _executar_binario(
        self,
        interaction: discord.Interaction,
        nome_comando: str,
        comando: list,
        timeout: int,
        titulo: str,
        detalhe: str,
        host_inacessivel=None,
    ) -> None:
        """
        Fluxo comum a /scan, /gau e /subfinder.

        Faz o defer, chama o runner (com limite de concorrência e timeout) e
        trata, um a um, os erros esperados — cada caso com sua mensagem própria.

        `host_inacessivel` é opcional: uma função que recebe a saída da
        ferramenta e devolve True se ela indica que o alvo não respondeu
        (usado pelo /scan, já que o nmap não sinaliza isso pelo código de saída).
        """
        # defer ANTES de rodar: o binário pode passar dos 3 segundos do Discord.
        await interaction.response.defer(thinking=True)
        usuario = str(interaction.user)

        try:
            saida = await runner.executar(comando, timeout=timeout)
        except runner.ConcorrenciaError:
            await self._falha(interaction, usuario, nome_comando, messages.ERRO_CONCORRENCIA)
            return
        except runner.FerramentaAusenteError:
            await self._falha(
                interaction, usuario, nome_comando, messages.ERRO_FERRAMENTA_AUSENTE
            )
            return
        except runner.TimeoutFerramentaError:
            await self._falha(interaction, usuario, nome_comando, messages.ERRO_TIMEOUT)
            return
        except runner.ExecucaoFerramentaError as exc:
            # Log detalhado (stderr) só no console, nunca para o usuário.
            logger.warning("Falha em /%s stderr=%s", nome_comando, exc.stderr[:500])
            await self._falha(
                interaction, usuario, nome_comando, messages.ERRO_HOST_INACESSIVEL
            )
            return

        if not saida:
            await self._falha(
                interaction, usuario, nome_comando, messages.ERRO_RESULTADO_VAZIO
            )
            return

        if host_inacessivel is not None and host_inacessivel(saida):
            await self._falha(
                interaction, usuario, nome_comando, messages.ERRO_HOST_INACESSIVEL
            )
            return

        log_comando(usuario, nome_comando, sucesso=True, detalhe=detalhe)
        # monospaco=True: no chat sai em bloco de código (alinhado); se for longo,
        # vira um .txt limpo, sem as cercas de código.
        await formatting.responder_resultado(
            interaction, nome_comando, titulo, saida, monospaco=True
        )

    async def _falha(
        self,
        interaction: discord.Interaction,
        usuario: str,
        comando: str,
        mensagem: str,
    ) -> None:
        log_comando(usuario, comando, sucesso=False, detalhe=mensagem)
        await formatting.responder_erro(interaction, mensagem)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ReconBinCog(bot, bot.metis_config))
