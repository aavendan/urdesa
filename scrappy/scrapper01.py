import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

async def main():
    async with async_playwright() as p:

        # Usar Chrome real del sistema (no el Chromium de Playwright)
        browser = await p.chromium.launch_persistent_context(
            user_data_dir="./chrome_profile",   # guarda la sesión entre ejecuciones
            channel="chrome",                    # usa Google Chrome instalado
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--start-maximized",
            ],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport=None,                       # usar tamaño real de ventana
            locale="es-ES",
            timezone_id="America/Guayaquil",
            java_script_enabled=True,
        )

        page = await browser.new_page()

        # Aplicar stealth en la página
        await stealth_async(page)

        print("🌐 Abriendo página de login de X...")
        await page.goto(
            "https://x.com/i/flow/login?redirect_after_login=%2Fhome",
            wait_until="domcontentloaded"
        )

        print("⏳ Ingresa tu usuario y contraseña en el navegador.")
        print("   Tienes hasta 5 minutos para completar el login.\n")

        await page.wait_for_url("https://x.com/home", timeout=300000)

        print("✅ ¡Login exitoso! Redirigido a https://x.com/home")

        await page.screenshot(path="x_home.png")
        print("📸 Screenshot guardado como x_home.png")

        await asyncio.sleep(5)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())