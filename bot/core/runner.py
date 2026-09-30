"""
Execução segura de binários externos + limite de concorrência.

Este módulo concentra tudo que é sensível na hora de rodar ferramentas externas
(nmap, gau, subfinder), seguindo as regras do projeto:

- SEMPRE via asyncio subprocess (não trava o bot enquanto a ferramenta roda).
- Argumentos SEMPRE como lista, NUNCA com shell=True (evita injeção de comando).
- SEMPRE com timeout (a operação é cancelada se demorar demais).
- No máximo 2 comandos "pesados" (com binário) ao mesmo tempo — controlado por
  um semáforo. Pedidos além disso recebem aviso para tentar de novo.

Erros são traduzidos em exceções específicas para o cog decidir a mensagem.
"""

import asyncio

# Semáforo global: no máximo 2 execuções de binário simultâneas.
# Um semáforo é como um "número de vagas": cada execução ocupa 1 vaga e
# devolve ao terminar. Se não há vaga, quem chega tenta pegar sem esperar.
_MAX_PESADOS = 2
_semaforo = asyncio.Semaphore(_MAX_PESADOS)


class FerramentaAusenteError(Exception):
    """O binário não foi encontrado no sistema (não instalado / fora do PATH)."""


class TimeoutFerramentaError(Exception):
    """A execução ultrapassou o tempo limite e foi cancelada."""


class ConcorrenciaError(Exception):
    """Já há o número máximo de comandos pesados rodando agora."""


class ExecucaoFerramentaError(Exception):
    """A ferramenta rodou mas terminou com erro (código de saída diferente de 0)."""

    def __init__(self, mensagem: str, stderr: str = "") -> None:
        super().__init__(mensagem)
        self.stderr = stderr


async def executar(comando: list, timeout: int) -> str:
    """
    Executa um binário de forma assíncrona e segura, devolvendo a saída (stdout).

    Parâmetros:
    - comando: lista com o binário e seus argumentos, ex.: ["nmap", "-F", ip].
               Passar como lista é o que evita injeção de shell.
    - timeout: tempo máximo em segundos.

    Levanta:
    - ConcorrenciaError    -> se já há 2 comandos pesados rodando.
    - FerramentaAusenteError -> se o binário não existe no sistema.
    - TimeoutFerramentaError -> se estourar o timeout.
    - ExecucaoFerramentaError -> se a ferramenta retornar erro.
    """
    # Tenta ocupar uma vaga quase sem esperar. Se as 2 vagas já estão ocupadas,
    # o acquire não completa a tempo e avisamos o usuário para tentar depois.
    # (Não bloqueamos indefinidamente de propósito: preferimos responder rápido.)
    try:
        await asyncio.wait_for(_semaforo.acquire(), timeout=0.05)
    except asyncio.TimeoutError:
        raise ConcorrenciaError()

    try:
        # Cria o processo. create_subprocess_exec NÃO usa shell — recebe a lista
        # de argumentos diretamente, que é o modo seguro.
        try:
            processo = await asyncio.create_subprocess_exec(
                *comando,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            # O binário não existe / não está no PATH.
            raise FerramentaAusenteError(str(exc)) from exc

        # Espera a saída respeitando o timeout. Se estourar, mata o processo.
        try:
            stdout, stderr = await asyncio.wait_for(
                processo.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError as exc:
            processo.kill()
            # Aguarda o processo realmente encerrar para não deixar zumbis.
            await processo.wait()
            raise TimeoutFerramentaError() from exc

        saida = stdout.decode("utf-8", errors="replace").strip()
        erro = stderr.decode("utf-8", errors="replace").strip()

        # Código de saída != 0 indica falha da ferramenta.
        if processo.returncode != 0:
            raise ExecucaoFerramentaError(
                f"A ferramenta retornou código {processo.returncode}.",
                stderr=erro,
            )

        return saida
    finally:
        # Sempre devolve a vaga do semáforo, mesmo se deu erro.
        _semaforo.release()
