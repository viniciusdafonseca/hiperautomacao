from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger


async def erro_generico(req: Request, exc: Exception):
    logger.error(f"Rota: {req.url.path!r} | {req.query_params!r}")
    logger.error(f"Erro: {str(exc)!r} | Tipo: {type(exc)!r}")

    if not str(exc):
        exc = Exception("Erro inesperado")
    response = JSONResponse(
        status_code=500,
        content={
            "mensagem_erro": str(exc)
        }
    )

    return response