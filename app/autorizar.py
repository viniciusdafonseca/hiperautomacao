from fastapi import HTTPException, Security
from fastapi.security import APIKeyQuery

tokens_validos = ["RfTyLoYxtxC3hnPDnkMHog7mib7sGXmMJhLDGT39"] #Hash aleatório gerado para o token de acesso


async def autorizar_request(token: str = Security(APIKeyQuery(name="token"))):
    if token not in tokens_validos:
        raise HTTPException(status_code=401)
