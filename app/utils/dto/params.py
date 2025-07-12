from typing import Optional

from pydantic import BaseModel


class ParamsDto(BaseModel):
    """Classe de parâmetros para a coleta de dados do Portal da Transparência."""
    parametro_busca: str
    filtro_busca: Optional[str] = ""
