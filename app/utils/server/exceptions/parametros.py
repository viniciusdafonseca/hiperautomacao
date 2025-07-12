class ParamsError(Exception):
    """Exceção disparada quando o parâmetro está inválido."""

    def __init__(self, message: str):
        self.message = message

    def __str__(self) -> str:
        return self.message