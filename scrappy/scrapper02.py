"""
Twitter / X — Extractor de hilos con autenticación
====================================================
1. Solicita credenciales por consola (usuario/email + contraseña)
2. Inicia sesión en x.com de forma automática
3. Extrae todas las publicaciones del hilo indicado
4. Guarda los resultados en thread_data.json

Dependencias:
    pip install playwright
    playwright install chromium
"""

import asyncio
import getpass
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PWTimeout


# ── Configuración ────────────────────────────────────────────────────────────
TARGET_URL = (
    "https://x.com/DiegoArcos14/status/2037145702506119642"
)
LOGIN_URL  = "https://x.com/i/flow/login"
OUTPUT_FILE = Path("thread_data.json")
SESSION_FILE = Path("session_twitter.json")   # caché de sesión (opcional)

SCROLL_ROUNDS   = 20      # máximo de rondas de scroll
SCROLL_PAUSE_MS = 1500    # pausa entre scrolls (ms)
MAX_NO_NEW      = 3       # rondas sin novedad antes de parar

# ── Helpers de consola ───────────────────────────────────────────────────────

def print_banner():
    print("\n" + "═" * 56)
    print("   🐦  Twitter / X  —  Extractor de hilos")
    print("═" * 56 + "\n")


def solicitar_credenciales() -> tuple[str, str]:
    """Pide usuario y contraseña de forma segura por consola."""
    print("Ingresa tus credenciales de X (Twitter).")
    print("(La contraseña no se muestra mientras escribes)\n")
    usuario = input("  Usuario o correo electrónico: ").strip()
    if not usuario:
        sys.exit("❌  El usuario no puede estar vacío.")
    contrasena = getpass.getpass("  Contraseña: ")
    if not contrasena:
        sys.exit("❌  La contraseña no puede estar vacía.")
    print()
    return usuario, contrasena


# ── Lógica de extracción (JavaScript inyectado) ──────────────────────────────

EXTRACT_JS = """
() => {
    const articles = document.querySelectorAll('article[data-testid="tweet"]');
    const data = [];

    articles.forEach((el, idx) => {
        const getText = sel => el.querySelector(sel)?.innerText?.trim() ?? null;
        const getAttr = (sel, attr) => el.querySelector(sel)?.getAttribute(attr) ?? null;

        const authorName   = getText('[data-testid="User-Name"] span:first-child');
        const authorHandle = getText('[data-testid="User-Name"] span[dir="ltr"]');
        const tweetText    = getText('[data-testid="tweetText"]');
        const timeEl       = el.querySelector('time');
        const tweetDate    = timeEl?.getAttribute('datetime') ?? null;
        const tweetUrl     = timeEl?.closest('a')?.href ?? null;
        const avatarUrl    = getAttr('img[src*="profile_images"]', 'src');

        const metrics = {};
        el.querySelectorAll('[data-testid$="-count"]').forEach(m => {
            const key = m.dataset.testid.replace('-count', '');
            metrics[key] = m.innerText.trim();
        });

        const replyContext = getText('[data-testid="tweet-reply-context"]');
        const hasConnector = !!el.querySelector('[data-testid="tweet-reply-context"]');

        const images = [...el.querySelectorAll('[data-testid="tweetPhoto"] img')]
            .map(img => img.src);

        const videos = [...el.querySelectorAll('video source')]
            .map(v => v.src)
            .filter(Boolean);

        const links = [...el.querySelectorAll('[data-testid="tweetText"] a')]
            .map(a => a.href)
            .filter(h => !h.includes('twitter.com') && !h.includes('x.com'));

        data.push({
            position: idx,
            isMainTweet: idx === 0,
            authorName,
            authorHandle,
            tweetText,
            tweetDate,
            tweetUrl,
            avatarUrl,
            metrics,
            hasConnector,
            replyContext,
            images,
            videos,
            links,
        });
    });

    return data;
}
"""


# ── Inicio de sesión ─────────────────────────────────────────────────────────

async def login(page, usuario: str, contrasena: str) -> bool:
    """
    Navega por el flujo de login de X.
    Devuelve True si el login fue exitoso.
    """
    print("🔐  Iniciando sesión en X...")
    await page.goto(LOGIN_URL, wait_until="networkidle", timeout=60_000)
    await page.wait_for_timeout(2000)

    # ── Paso 1: campo de usuario / email ────────────────────────────────────
    try:
        user_input = page.get_by_label("Phone, email, or username")
        if not await user_input.is_visible(timeout=5000):
            raise PWTimeout
    except PWTimeout:
        user_input = page.locator('input[autocomplete="username"]').first

    await user_input.fill(usuario)
    await page.wait_for_timeout(500)

    # Botón "Next"
    await page.get_by_role("button", name="Next").click()
    await page.wait_for_timeout(2000)

    # ── Paso intermedio: verificación adicional (handle de usuario) ──────────
    try:
        extra = page.get_by_label("Phone or username")
        if await extra.is_visible(timeout=3000):
            print("  ⚠️   X pide verificación adicional (handle)…")
            handle = usuario if usuario.startswith("@") else f"@{usuario}"
            await extra.fill(handle)
            await page.get_by_role("button", name="Next").click()
            await page.wait_for_timeout(2000)
    except PWTimeout:
        pass

    # ── Paso 2: contraseña ───────────────────────────────────────────────────
    try:
        pwd_input = page.get_by_label("Password", exact=True)
        if not await pwd_input.is_visible(timeout=5000):
            raise PWTimeout
    except PWTimeout:
        pwd_input = page.locator('input[type="password"]').first

    await pwd_input.fill(contrasena)
    await page.wait_for_timeout(500)

    await page.get_by_role("button", name="Log in").click()
    await page.wait_for_timeout(4000)

    # ── Verificar login exitoso ──────────────────────────────────────────────
    if "home" in page.url or "x.com" in page.url and "login" not in page.url:
        print("  ✅  Sesión iniciada correctamente.\n")
        return True

    # Detectar error visible
    error_text = ""
    try:
        toast = page.locator('[data-testid="toast"]')
        if await toast.is_visible(timeout=2000):
            error_text = await toast.inner_text()
    except Exception:
        pass

    print(f"  ❌  Login fallido. {error_text or 'Verifica tus credenciales.'}\n")
    return False


# ── Extracción del hilo ───────────────────────────────────────────────────────

async def extract_thread(page) -> dict:
    print(f"📡  Navegando al hilo:\n    {TARGET_URL}\n")
    await page.goto(TARGET_URL, wait_until="networkidle", timeout=60_000)

    try:
        await page.wait_for_selector('article[data-testid="tweet"]', timeout=30_000)
    except PWTimeout:
        sys.exit("❌  No se encontraron tweets. El contenido puede requerir login o no estar disponible.")

    await page.wait_for_timeout(2000)

    # Capturar respuestas GraphQL de la API
    api_responses = []

    async def capture_api(response):
        url = response.url
        if any(k in url for k in ["TweetDetail", "ThreadedConversation"]):
            try:
                data = await response.json()
                fname = f"api_{int(time.time() * 1000)}.json"
                Path(fname).write_text(json.dumps(data, indent=2, ensure_ascii=False))
                api_responses.append(fname)
                print(f"  [API] Capturada → {fname}")
            except Exception:
                pass

    page.on("response", capture_api)

    # ── Scroll + extracción iterativa ────────────────────────────────────────
    seen_urls: set[str] = set()
    all_tweets: list[dict] = []
    no_new_rounds = 0

    print("🔄  Extrayendo publicaciones del hilo…\n")

    for ronda in range(1, SCROLL_ROUNDS + 1):
        tweets = await page.evaluate(EXTRACT_JS)

        nuevos = 0
        for tweet in tweets:
            url = tweet.get("tweetUrl")
            key = url or f"no_url_{tweet.get('position')}_{tweet.get('authorHandle')}"
            if key not in seen_urls:
                seen_urls.add(key)
                all_tweets.append(tweet)
                nuevos += 1

        print(f"  Ronda {ronda:02d} | +{nuevos} nuevos | Total: {len(all_tweets)}")

        if nuevos == 0:
            no_new_rounds += 1
            if no_new_rounds >= MAX_NO_NEW:
                print("\n  ℹ️  Sin contenido nuevo. Extracción finalizada.")
                break
        else:
            no_new_rounds = 0

        # Scroll
        await page.evaluate("() => window.scrollBy(0, window.innerHeight * 2)")
        await page.wait_for_timeout(SCROLL_PAUSE_MS)

        # Botón "Mostrar más respuestas"
        for label in ["Show more replies", "Ver más respuestas", "Show"]:
            try:
                btn = page.locator(f"text=/{label}/i").first
                if await btn.is_visible(timeout=800):
                    await btn.click()
                    await page.wait_for_timeout(1800)
                    break
            except Exception:
                pass

    # Separar tweet principal de replies
    main_tweet = next((t for t in all_tweets if t["isMainTweet"]), None)
    replies    = [t for t in all_tweets if not t["isMainTweet"]]

    return {
        "extracted_at": datetime.utcnow().isoformat() + "Z",
        "url": TARGET_URL,
        "api_files_captured": api_responses,
        "tweet_principal": main_tweet,
        "total_replies": len(replies),
        "replies": replies,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    print_banner()
    usuario, contrasena = solicitar_credenciales()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,   # ← True para modo silencioso
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )

        # Reusar sesión guardada si existe
        context_kwargs = dict(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
            locale="es-ES",
        )
        if SESSION_FILE.exists():
            context_kwargs["storage_state"] = str(SESSION_FILE)
            print(f"ℹ️  Sesión cargada desde {SESSION_FILE}\n")

        context = await browser.new_context(**context_kwargs)
        page    = await context.new_page()

        # Login solo si no hay sesión guardada o si falla la carga
        if not SESSION_FILE.exists():
            ok = await login(page, usuario, contrasena)
            if not ok:
                await browser.close()
                sys.exit(1)
            # Guardar sesión para próximas ejecuciones
            await context.storage_state(path=str(SESSION_FILE))
            print(f"💾  Sesión guardada en {SESSION_FILE}\n")

        # Extracción
        output = await extract_thread(page)

        # Guardar JSON
        OUTPUT_FILE.write_text(
            json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        print(f"\n{'═' * 56}")
        print(f"  ✅  Tweet principal : {output['tweet_principal']['authorHandle'] if output['tweet_principal'] else 'N/A'}")
        print(f"  💬  Replies extraídas: {output['total_replies']}")
        print(f"  📄  Archivo generado : {OUTPUT_FILE.resolve()}")
        print(f"{'═' * 56}\n")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())