"""
Configuração do logging.

Objetivo (das instruções): registrar no console o comando usado, o usuário e se
deu certo ou erro — SEM nunca gravar tokens ou segredos.

Este módulo expõe:
- configurar_logging(): ajusta o formato e o nível dos logs uma vez, no início.
- log_comando(): função de conveniência para registrar o uso de um comando de
  forma padronizada.
"""

import logging

_LOGGER_NOME = "metis"


def configurar_logging() -> logging.Logger:
    """
    Configura o logging global e devolve o logger principal do bot.

    Chamado uma única vez em main.py, antes de o bot subir.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger(_LOGGER_NOME)


def obter_logger() -> logging.Logger:
    """Devolve o logger do bot para uso nos cogs."""
    return logging.getLogger(_LOGGER_NOME)


def log_comando(usuario: str, comando: str, sucesso: bool, detalhe: str = "") -> None:
    """
    Registra o uso de um comando de forma padronizada.

    Parâmetros:
    - usuario: identificação do usuário (ex.: 'nome#0001' ou o id).
    - comando: nome do comando (ex.: 'scan').
    - sucesso: True se terminou bem, False se houve erro.
    - detalhe: informação extra opcional (ex.: alvo, tipo de erro).
              NUNCA passe tokens ou segredos aqui.
    """
    logger = obter_logger()
    status = "OK" if sucesso else "ERRO"
    mensagem = f"comando=/{comando} usuario={usuario} status={status}"
    if detalhe:
        mensagem += f" detalhe={detalhe}"
    if sucesso:
        logger.info(mensagem)
    else:
        logger.warning(mensagem)
