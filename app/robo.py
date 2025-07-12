import json
import re

from bs4 import BeautifulSoup
from loguru import logger

from app.utils import ParamsDto
from app.utils.camoufox import CamoufoxBrowser
from app.utils.server.exceptions.parametros import ParamsError


class PortalTransparencia:
    _inscricao: str
    _documento: str
    _url_base = "https://portaldatransparencia.gov.br/"

    def __init__(self, params: ParamsDto):
        self._parametro_busca = re.sub(r'[^a-zA-Z0-9\s]', '', params.parametro_busca)
        self._filtro_busca = params.filtro_busca
        self._tipo_parametro_busca = self._valida_tipo_parametro_busca()
        self.camoufox = CamoufoxBrowser(headless=False)

    def _valida_tipo_parametro_busca(self) -> str:
        """
        Valida o tipo de parâmetro de busca fornecido.

        Este método verifica se o parâmetro de busca é um CPF ou NIS (11 dígitos).
        Se sim, o tipo de busca será definido como "cpf_nis".
        Caso contrário, o tipo de busca será definido como "nome".
        """
        if re.search(r"\d{11}", self._parametro_busca) and len(self._parametro_busca) == 11:
            return "cpf_nis"
        else:
            return "nome"

    async def start(self) -> None:
        self.context = await self.camoufox.start()
        self.page = await self.context.new_page()

    async def finish(self) -> None:
        await self.camoufox.finish()

    async def _acesso_sistema(self) -> None:
        """
        Acessa o sistema do Portal da Transparência e realiza as ações iniciais necessárias.
        
        Este método:
        - Navega para a URL base do portal
        - Acessa a página de consulta de pessoa física
        """

        await self.page.goto(self._url_base, wait_until="domcontentloaded")
        # await self.page.click("#accept-all-b", delay=1000, timeout=5000)
        await self.page.click("#accept-all-btn", delay=1000)
        await self.page.goto("https://portaldatransparencia.gov.br/pessoa/visao-geral")

    async def _aplica_filtro(self) -> None:
        """
        Aplica o filtro de busca, se necessário.
        Este método verifica se o filtro de busca foi fornecido e, se sim, aplica o filtro na página.
        """
        await self.page.get_by_text("Refine a Busca").click()
        if self._filtro_busca:
            soup = BeautifulSoup(await self.page.content(), "html.parser")
            filtro = soup.find("label", string=re.compile(rf"{self._filtro_busca}", re.I))["for"]
            await self.page.locator(f"label[for='{filtro}']").click()
            logger.info(f"Filtro aplicado: {self._filtro_busca}")\

    async def _valida_parametro_busca(self, resultados: dict) -> None:
        """
        Valida o parâmetro de busca retornado.
        Este método verifica se o número de resultados encontrados é zero.
        Se for zero, lança uma exceção ParamsError com uma mensagem apropriada.
        Caso contrário, não faz nada.

        :param resultados: Dicionário contendo os resultados da busca
        :raises ParamsError: Se o número de resultados encontrados for zero.
        """
        if resultados["totalRegistros"] == 0:
            if self._tipo_parametro_busca == "cpf_nis":
                raise ParamsError("Não foi possível retornar os dados no tempo de resposta solicitado")
            elif self._tipo_parametro_busca == "nome":
                termo = await self.page.locator("#infoTermo").locator("strong").inner_text()
                raise ParamsError(f"Foram encontrados 0 resultados para o termo {termo}")

        logger.info("Paramêtro validado com sucesso!")

    async def _acessa_consulta_pessoa(self) -> None:
        """
        Acessa a página de consulta de pessoa física no Portal da Transparência.

        Este método:
        - Acessa a consulta de pessoa física
        - Preenche o campo de busca com o parâmetro fornecido
        - Aplica o filtro, se necessário
        - Clica no botão de consultar
        - Aguarda o carregamento da página de resultados
        """
        await self._acesso_sistema()

        await self.page.click("#button-consulta-pessoa-fisica")
        await self.page.type("#termo", self._parametro_busca, delay=250)
        await self._aplica_filtro()

        async with self.page.expect_response(
                re.compile(r"https://portaldatransparencia.gov.br/pessoa-fisica/busca/resultado")
        ) as response_info:
            await self.page.click('#btnConsultarPF')

        logger.info("Consulta realizada com sucesso!")
        response_json = await response_info.value
        resultados = json.loads(await response_json.body())
        await self._valida_parametro_busca(resultados)

        await self.page.locator("a[class='link-busca-nome']").first.click()
        await self.page.wait_for_selector("#main-content")
        logger.info("Página de resultados carregada!")

    async def _get_debitos_detalhar(self, beneficio_linha) -> list:
        detalhar_debitos = []

        href = await beneficio_linha.get_by_text("Detalhar").get_attribute("href")
        page_detalhar = await self.context.new_page()
        await page_detalhar.goto(f"https://portaldatransparencia.gov.br{href}")
        await page_detalhar.wait_for_selector('table[class="dataTable no-footer"]')

        detalhar_linhas = await page_detalhar.locator('table[class="dataTable no-footer"]').locator("tbody").locator("tr[role='row']").all()
        for detalhar_linha in detalhar_linhas:
            detalhar_colunas = await detalhar_linha.locator("td").locator("span").all()

            debito = {}
            for detalhar_coluna in detalhar_colunas:
                key = (await detalhar_coluna.get_attribute("data-original-title")).replace("<strong>", "").replace("</strong>", "")
                value = await detalhar_coluna.inner_text()
                debito[key] = value

            detalhar_debitos.append(debito)

        await page_detalhar.close()
        return detalhar_debitos

    async def _get_valores_beneficio_linha(self, beneficio_linha) -> dict:
        """
        Obtém os valores de uma linha de benefício.

        Este método extrai os valores de uma linha de benefício e retorna um dicionário com os dados.

        :param beneficio_linha da linha do benefício
        :return: dict contendo os valores do benefício
        """
        beneficio_colunas = await beneficio_linha.locator("td").all()
        valor_recebido = await beneficio_colunas[3].inner_text()
        debitos = await self._get_debitos_detalhar(beneficio_linha)
        return {
            "valor_recebido": valor_recebido.strip(),
            "detalhar": debitos
        }

    async def _get_beneficio_dados(self, beneficio) -> list:
        beneficio_resultado = []
        beneficio_tabela = beneficio.locator("#tabela-visao-geral-sancoes").locator("tbody")
        beneficio_linhas = await beneficio_tabela.locator("tr").all()

        for beneficio_linha in beneficio_linhas:
            beneficio_resultado.append(await self._get_valores_beneficio_linha(beneficio_linha))

        return beneficio_resultado

    async def _get_beneficio(self, beneficio) -> dict:
        beneficio_nome = await beneficio.locator("strong").inner_text()
        beneficio_info = await self._get_beneficio_dados(beneficio)
        return {
            "nome": beneficio_nome,
            "dados": beneficio_info,
        }

    async def _get_beneficios(self) -> list:
        beneficios_resultado = []

        label = self.page.get_by_text("Recebimentos de recursos")
        await label.click(delay=1000)
        await self.page.wait_for_load_state("domcontentloaded")
        await self.page.wait_for_timeout(2000)

        beneficios = await self.page.locator("div[class='responsive']").all()
        for beneficio in beneficios:
            beneficio_resultado = await self._get_beneficio(beneficio)
            beneficios_resultado.append(beneficio_resultado)

        return beneficios_resultado

    async def _get_pessoa_fisica_info(self) -> dict[str, str]:
        """
        Obtém informações da pessoa física consultada.

        Este método:
        - Localiza a seção de dados tabelados
        - Extrai informações como nome, CPF e localidade
        - Retorna os dados extraídos em um dicionário

        :return: dict[str, str] contendo as informações da pessoa física
        """
        infos = await self.page.locator('section[class="dados-tabelados"]').locator('div[class="row"]').locator("div").all()
        return {
            "nome": await infos[0].locator("span").inner_text(),
            "cpf": await infos[1].locator("span").inner_text(),
            "localidade": await infos[2].locator("span").inner_text(),
        }

    async def coleta(self) -> dict:
        await self._acessa_consulta_pessoa()

        info_pessoa = await self._get_pessoa_fisica_info()
        beneficios_resultado = await self._get_beneficios()

        return {
            **info_pessoa,
            "beneficios": beneficios_resultado,
        }
