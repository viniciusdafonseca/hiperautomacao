from fastapi import Depends, FastAPI

from app.autorizar import autorizar_request
from app.robo import PortalTransparencia
from app.utils import ParamsDto, exc_handlers, ParamsError

app = FastAPI(
    dependencies=[Depends(autorizar_request)],
    title="Portal da Transparência",
    swagger_ui_parameters={"docExpansion": "none"},
)

app.exception_handler(ParamsError)(exc_handlers.erro_parametro)
app.exception_handler(Exception)(exc_handlers.erro_generico)


@app.post("/api/portal_transparencia")
async def coleta_dados(params: ParamsDto):
    spider = PortalTransparencia(params)
    await spider.start()
    try:
        return await spider.coleta()
    except Exception as e:
        raise e
    finally:
        await spider.finish()
