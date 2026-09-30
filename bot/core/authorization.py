"""
Autorização por cargo (role).

Cada comando só pode ser usado por membros que tenham o cargo configurado em
AUTHORIZED_ROLE_ID. Este módulo oferece uma checagem simples e reutilizável.

Como é usado nos cogs: no começo de cada comando, chamamos `tem_permissao(...)`.
Se retornar False, respondemos com a mensagem de "sem permissão" e paramos.
"""

import discord


def tem_permissao(interaction: discord.Interaction, role_id_autorizado: int) -> bool:
    """
    Retorna True se quem chamou o comando possui o cargo autorizado.

    Detalhes para iniciantes:
    - `interaction.user` pode ser um Member (dentro de um servidor) ou um User
      (em DM). Só um Member tem cargos, então checamos isso primeiro.
    - Comandos de reconhecimento não fazem sentido em DM, então fora de um
      servidor a permissão é sempre negada.
    """
    usuario = interaction.user

    # Se não for um Member (por exemplo, chamada em mensagem direta), nega.
    if not isinstance(usuario, discord.Member):
        return False

    # Verifica se algum dos cargos do membro tem o ID autorizado.
    return any(cargo.id == role_id_autorizado for cargo in usuario.roles)
