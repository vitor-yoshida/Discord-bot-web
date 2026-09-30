"""
Formatação das respostas para o Discord.

Cuida de duas coisas que as instruções pedem:
1. Usar embeds quando fizer sentido (respostas organizadas e legíveis).
2. Quando o texto passar de ~1900 caracteres, enviar como arquivo .txt anexado,
   porque o Discord limita mensagens a 2000 caracteres.

Também centraliza uma cor padrão para os embeds, deixando o visual consistente.
"""

import io

import discord

from . import messages

# Limite prático de caracteres antes de trocar para arquivo.
# O Discord permite 2000; deixamos folga para título/formatação.
LIMITE_TEXTO = 1900

# Cor padrão dos embeds (um azul discreto). Mantida num só lugar.
COR_PADRAO = discord.Color.blue()
COR_ERRO = discord.Color.red()


def criar_embed(titulo: str, descricao: str = "", cor: discord.Color = COR_PADRAO) -> discord.Embed:
    """Cria um embed simples com título e descrição."""
    return discord.Embed(title=titulo, description=descricao, color=cor)


def embed_erro(mensagem: str) -> discord.Embed:
    """Cria um embed padronizado para mensagens de erro (cor vermelha)."""
    return discord.Embed(title="Erro", description=mensagem, color=COR_ERRO)


def texto_para_arquivo(texto: str, nome_arquivo: str) -> discord.File:
    """
    Empacota um texto grande num arquivo .txt para anexar à resposta.

    O conteúdo é mantido em memória (io.BytesIO), sem gravar em disco.
    """
    buffer = io.BytesIO(texto.encode("utf-8"))
    return discord.File(buffer, filename=nome_arquivo)


async def responder_resultado(
    interaction: discord.Interaction,
    nome_comando: str,
    titulo: str,
    corpo: str,
    monospaco: bool = False,
) -> None:
    """
    Envia o resultado de um comando.

    Recebe o texto CRU (sem formatação de code block) e decide sozinho:
    - Curto  -> embed. Se `monospaco=True`, envolve o texto numa cerca de código
                ``` ``` ``` para manter alinhamento (útil para saída de ferramentas).
    - Longo  -> grava o texto puro num arquivo .txt e anexa. Aqui NÃO usamos
                cercas de código: elas só fazem sentido no chat, não dentro do
                arquivo, que fica limpo.

    Passar o texto cru (em vez de já com as cercas) é justamente o que permite
    ter o arquivo limpo no caso longo.
    """
    if len(corpo) <= LIMITE_TEXTO:
        conteudo_embed = f"```\n{corpo}\n```" if monospaco else corpo
        embed = criar_embed(titulo, conteudo_embed)
        await interaction.edit_original_response(content=None, embed=embed)
    else:
        arquivo = texto_para_arquivo(corpo, f"{nome_comando}.txt")
        await interaction.edit_original_response(
            content=messages.resultado_como_arquivo(nome_comando),
            embed=None,
            attachments=[arquivo],
        )


async def responder_erro(interaction: discord.Interaction, mensagem: str) -> None:
    """Edita a resposta (já deferida) com um embed de erro padronizado."""
    await interaction.edit_original_response(content=None, embed=embed_erro(mensagem))
