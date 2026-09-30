"""
Ponto de entrada do Metis Bot.

Responsabilidades deste arquivo:
1. Configurar o logging.
2. Ler e validar a configuração (variáveis de ambiente).
3. Criar o bot com os intents necessários.
4. Carregar os três cogs (grupos de comandos).
5. Sincronizar os slash commands com o Discord.
6. Registrar um tratador global de erros inesperados.
7. Subir o bot.

Rode com:  python -m bot.main
(o "-m" é necessário porque o código usa imports relativos, como "from .core";
rodar "python bot/main.py" direto quebra esses imports.)
"""

import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from .core import messages
from .core.config import Config, ConfigError
from .core.formatting import embed_erro
from .core.logging_setup import configurar_logging, obter_logger

# Logger no nível do módulo: assim as funções abaixo funcionam mesmo que este
# arquivo seja importado por outro (ex.: testes), e não só executado.
logger = obter_logger()

# Lista dos cogs a carregar. Cada um é um módulo em bot/cogs/.
_COGS = [
    "bot.cogs.recon_bin",
    "bot.cogs.recon_api",
    "bot.cogs.utils_cmds",
]


def criar_bot(config: Config) -> commands.Bot:
    """
    Cria e configura a instância do bot.

    Intents são "permissões de eventos" que o bot pede ao Discord. Precisamos
    de `members` para conseguir ler os cargos de quem chama os comandos (usado
    na autorização).
    """
    intents = discord.Intents.default()
    intents.members = True  # necessário para checar cargos (autorização)

    # command_prefix é exigido pelo commands.Bot, mas como só usamos slash
    # commands, ele fica sem uso prático.
    bot = commands.Bot(command_prefix="!", intents=intents)

    # Guardamos a config no próprio bot para os cogs acessarem em setup().
    bot.metis_config = config

    @bot.event
    async def on_ready() -> None:
        # Sincroniza os slash commands assim que o bot conecta.
        # Isso registra/atualiza os comandos na API do Discord.
        try:
            if config.guild_id is not None:
                # Modo desenvolvimento: sync só neste servidor (instantâneo).
                # Copiamos os comandos globais para o guild e sincronizamos.
                guild = discord.Object(id=config.guild_id)
                bot.tree.copy_global_to(guild=guild)
                sincronizados = await bot.tree.sync(guild=guild)
                logger.info(
                    "Bot conectado como %s. %d comandos sincronizados no servidor %s (modo dev).",
                    bot.user,
                    len(sincronizados),
                    config.guild_id,
                )
            else:
                # Modo padrão: sync global (funciona em qualquer servidor).
                sincronizados = await bot.tree.sync()
                logger.info(
                    "Bot conectado como %s. %d comandos sincronizados globalmente.",
                    bot.user,
                    len(sincronizados),
                )
        except discord.DiscordException as exc:
            logger.error("Falha ao sincronizar comandos: %s", exc)

    @bot.tree.error
    async def on_app_command_error(
        interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        """
        Rede de segurança para QUALQUER erro não tratado dentro de um comando.

        Os cogs tratam os erros esperados (timeout, API fora do ar etc.). Se
        algo imprevisto escapar, o discord.py chama esta função. Sem ela, o
        usuário ficaria vendo "pensando..." para sempre.

        - O stack trace completo vai só para o log (exc_info).
        - O usuário recebe apenas a mensagem genérica ERRO_INESPERADO.
        """
        nome = interaction.command.name if interaction.command else "?"
        logger.error(
            "Erro inesperado em /%s usuario=%s",
            nome,
            interaction.user,
            exc_info=error,
        )

        try:
            if interaction.response.is_done():
                # Já houve defer (ou resposta): editamos a resposta original.
                await interaction.edit_original_response(
                    content=None, embed=embed_erro(messages.ERRO_INESPERADO), attachments=[]
                )
            else:
                # Ainda não respondemos: enviamos uma resposta só para quem chamou.
                await interaction.response.send_message(
                    messages.ERRO_INESPERADO, ephemeral=True
                )
        except discord.DiscordException:
            # Nem avisar o usuário deu certo (ex.: interação expirou). Só loga.
            logger.exception("Não foi possível avisar o usuário sobre o erro em /%s", nome)

    return bot


async def _carregar_cogs(bot: commands.Bot) -> None:
    """Carrega todos os cogs listados em _COGS."""
    for cog in _COGS:
        await bot.load_extension(cog)
        logger.info("Cog carregado: %s", cog)


async def _main(config: Config) -> None:
    """Fluxo assíncrono principal: cria, carrega e inicia o bot."""
    bot = criar_bot(config)
    async with bot:
        await _carregar_cogs(bot)
        await bot.start(config.discord_token)


if __name__ == "__main__":
    # 1) Logging primeiro, para que qualquer erro já apareça formatado.
    configurar_logging()

    # 2) Configuração. Se algo estiver errado no .env, paramos com mensagem clara.
    try:
        config = Config()
    except ConfigError as erro:
        logger.error("Erro de configuração: %s", erro)
        raise SystemExit(1)

    # 3) Sobe o bot. Ctrl+C encerra de forma limpa.
    try:
        asyncio.run(_main(config))
    except KeyboardInterrupt:
        logger.info("Encerrando o bot (interrupção pelo teclado).")
