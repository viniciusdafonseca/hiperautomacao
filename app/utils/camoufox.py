from camoufox import AsyncCamoufox


class CamoufoxBrowser:
    def __init__(self, headless: bool):
        self.camoufox = AsyncCamoufox(headless=headless, geoip=True, humanize=True)

    async def start(self):
        self.browser = await self.camoufox.start()
        return self.camoufox.browser

    async def finish(self):
        print(self.camoufox.browser)
        await self.camoufox.browser.close()
