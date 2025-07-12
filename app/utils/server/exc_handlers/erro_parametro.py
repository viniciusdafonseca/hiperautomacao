from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger

from app.utils.server.exceptions.parametros import ParamsError


async def erro_parametro(req: Request, exc: ParamsError):
    """Realiza o tratamento dos erros de parâmetro inválido"""
    logger.warning(
        f"Parâmetro inválido: [{req.url!r}]!"
    )
    response = JSONResponse(
        content={
            "mensagem_erro": exc.message
        }
    )

    return response
