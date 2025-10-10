import os
import time
import platform
import subprocess
import tempfile
from urllib.parse import quote
from datetime import datetime, timedelta, time as dtime
from zoneinfo import ZoneInfo
import threading

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# =====================================
# CONFIGURACIÓN
# =====================================
TU_NOMBRE = "Regencia de Farmacia UTP- Univirtual"

# Credenciales/identidad (solo usadas si Google pide correo/clave)
ZOOM_EMAIL = "univirtual_zoom_2@utp.edu.co"   # ← Cambia si corresponde
ZOOM_PASSWORD = "Utpunivirtual2020"           # ← Cambia si corresponde

# Perfil de Chrome para guardar sesión (crear automáticamente)
CHROME_PROFILE_DIR = os.path.join(tempfile.gettempdir(), "zoom_chrome_profile")

# Comportamiento de sesión
GUARDAR_SESION = True   # True = guarda cookies/sesión; False = sesión desechable
PRIMERA_VEZ = False     # True = forzar login Google y almacenar sesión; luego ponlo en False

# Zona horaria local
TZ = ZoneInfo("America/Bogota")

# Reuniones a abrir (ejemplos con programación)
reuniones = [
    {
        "nombre": "Prueba 1",
        "url": "https://renata.zoom.us/j/86426544795",
        "modo": "zoom_app",
        "programacion": {
            "tipo": "semanal",
            "dias": ["lun", "jue", "vie"],   # lunes y jueves
            "hora": "15:30"           # 5:00 PM (formato 24h, hora local)
        },
        "abrir_antes_min": 20
    },
    {
        "nombre": "ILEX G7 - Life and Discovery 2025",
        "url": "https://renata.zoom.us/w/81139053579?tk=...",
        "modo": "navegador_auto",
        "incognito": False,
        "nombre_usuario": "Regencia de Farmacia UTP- Univirtual",
        "programacion": {
            "tipo": "semanal",
            "dias": ["lun", "jue"],   # mismo horario recurrente
            "hora": "17:00"
        },
        "abrir_antes_min": 20
    }
]

# =====================================
# HELPERS
# =====================================
def zoom_logged_in(driver):
    """Heurística rápida para saber si hay sesión activa en Zoom."""
    try:
        url = driver.current_url
        if "zoom.us/profile" in url or "renata.zoom.us/profile" in url:
            return True
        els = driver.find_elements(
            By.XPATH,
            "//*[@aria-label='Profile' or contains(@class,'user-menu') or contains(@aria-label,'Account')]"
        )
        return len(els) > 0
    except Exception:
        return False

def extract_meeting_id(meeting_url: str) -> str:
    """
    Extrae el meeting/webinar ID de URLs tipo:
    - https://zoom.us/j/XXXXXXXXX
    - https://renata.zoom.us/j/XXXXXXXXX
    - https://zoom.us/w/XXXXXXXXX (webinar)
    - https://renata.zoom.us/w/XXXXXXXXX
    Devuelve solo el ID (sin parámetros).
    """
    try:
        if "/j/" in meeting_url:
            return meeting_url.split("/j/")[-1].split("?")[0]
        if "/w/" in meeting_url:
            return meeting_url.split("/w/")[-1].split("?")[0]
    except Exception:
        pass
    return ""

def build_webclient_url(meeting_url: str, as_host: bool = True, display_name: str = "Host") -> str:
    """
    Construye URL del Web Client:
      - Para dominios renata.zoom.us siempre usa /wc/join/
      - Para zoom.us usa /wc/host/ si se desea host, /wc/join/ si no.
    """
    base = "https://renata.zoom.us" if "renata.zoom.us" in meeting_url else "https://zoom.us"
    mid = extract_meeting_id(meeting_url)
    if not mid:
        return meeting_url  # fallback

    if "renata.zoom.us" in base:
        # Renata no soporta /wc/host/
        return f"{base}/wc/join/{mid}?uname={quote(display_name)}"
    else:
        if as_host:
            return f"{base}/wc/host/{mid}?prefer=1"
        else:
            return f"{base}/wc/join/{mid}?uname={quote(display_name)}"

def login_zoom_via_google(driver, wait, tenant_base="https://zoom.us"):
    """
    Inicia sesión en Zoom usando 'Sign in with Google'.
    tenant_base: 'https://zoom.us' o 'https://renata.zoom.us'
    """
    try:
        driver.get(f"{tenant_base}/signin")
        time.sleep(2)

        # Botón "Sign in with Google"
        google_btn_selectors = [
            "//button[contains(., 'Google')]",
            "//div[contains(@class,'signin-with') and contains(.,'Google')]",
            "//a[contains(.,'Google') and contains(@href,'google')]",
            "//button[contains(@data-qa,'google-signin')]",
            "//a[contains(@data-qa,'google-signin')]"
        ]
        clicked = False
        for sx in google_btn_selectors:
            try:
                btn = wait.until(EC.element_to_be_clickable((By.XPATH, sx)))
                driver.execute_script("arguments[0].click();", btn)
                clicked = True
                break
            except Exception:
                continue

        if not clicked:
            driver.get(f"{tenant_base}/signin/google")
            time.sleep(2)

        # Flujo de Google: elegir cuenta o ingresar credenciales
        try:
            cuenta = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.XPATH, f"//div[@data-identifier='{ZOOM_EMAIL}']|//div[contains(.,'{ZOOM_EMAIL}')]"))
            )
            driver.execute_script("arguments[0].click();", cuenta)
        except Exception:
            # Ingresar correo
            try:
                email_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//input[@type='email' and @name='identifier']|//input[@type='email']"))
                )
                email_input.clear()
                email_input.send_keys(ZOOM_EMAIL)
                next_btn = driver.find_element(By.XPATH, "//span[text()='Siguiente']/ancestor::button|//button[@type='submit']")
                driver.execute_script("arguments[0].click();", next_btn)
            except Exception as e:
                print(f"   ⚠️ No pude ingresar el correo en Google: {e}")

            # Ingresar contraseña (si Google la pide)
            try:
                pwd_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//input[@type='password' and @name='Passwd']|//input[@type='password']"))
                )
                pwd_input.clear()
                pwd_input.send_keys(ZOOM_PASSWORD)
                next_btn2 = driver.find_element(By.XPATH, "//span[text()='Siguiente']/ancestor::button|//button[@type='submit']")
                driver.execute_script("arguments[0].click();", next_btn2)
            except Exception as e:
                print(f"   ⚠️ No pude ingresar la contraseña de Google (¿2FA activo?): {e}")

        # Esperar redirección de vuelta a Zoom
        try:
            WebDriverWait(driver, 20).until(lambda d: "zoom.us" in d.current_url or "renata.zoom.us" in d.current_url)
            print("   ✅ Login Google -> Zoom completado (redirigido a Zoom)")
        except Exception:
            print("   ⚠️ No se observó redirección inmediata, continuando...")
    except Exception as e:
        print(f"   ❌ Error en login via Google: {e}")

# =====================================
# FUNCIONES PRINCIPALES (APERTURA)
# =====================================
def abrir_zoom_app(url):
    """Abre la reunión con la aplicación de Zoom usando el protocolo zoommtg://."""
    sistema = platform.system()
    if "zoom.us/j/" in url:
        meeting_id = url.split("/j/")[-1].split("?")[0]
        zoom_url = f"zoommtg://zoom.us/join?confno={meeting_id}"
    else:
        zoom_url = url

    try:
        if sistema == "Windows":
            os.startfile(zoom_url)  # type: ignore
        elif sistema == "Linux":
            subprocess.Popen(["xdg-open", zoom_url])
        elif sistema == "Darwin":
            subprocess.Popen(["open", zoom_url])
        print("✅ App de Zoom abierta")
        return True
    except Exception as e:
        print(f"❌ Error al abrir Zoom app: {e}")
        return False

def abrir_navegador_automatico(url, nombre_usuario, incognito=False):
    """
    Abre Zoom en el navegador y entra como anfitrión (SSO con Google).
    Si post-SSO te deja en /profile, redirige al Web Client join automáticamente.
    """
    print(f"   🤖 Iniciando navegador automatizado...")
    print(f"   👤 Usuario: {nombre_usuario}")

    # Configurar Chrome
    chrome_options = Options()

    if incognito:
        chrome_options.add_argument("--incognito")
        print("   🕶️  Modo incógnito activado")

    # PERFIL PERSISTENTE (guardar cookies/sesión)
    if GUARDAR_SESION and not incognito:
        os.makedirs(CHROME_PROFILE_DIR, exist_ok=True)
        chrome_options.add_argument(f"--user-data-dir={CHROME_PROFILE_DIR}")
        chrome_options.add_argument("--profile-directory=Default")

    # Opciones útiles para Linux/CI
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    # Suprimir logs
    chrome_options.add_argument("--log-level=3")

    # Permisos: auto-permitir mic/cámara para Zoom
    chrome_options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.media_stream_mic": 1,
        "profile.default_content_setting_values.media_stream_camera": 1,
        "profile.default_content_setting_values.notifications": 1,
        "protocol_handler.excluded_schemes.zoommtg": False,
        "protocol_handler.excluded_schemes.zoomus": False
    })
    chrome_options.add_argument("--use-fake-ui-for-media-stream")

    driver = None
    try:
        # Iniciar el navegador con ChromeDriverManager
        print("   ⏳ Descargando/verificando ChromeDriver...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        wait = WebDriverWait(driver, 15)
        print("   ✅ Navegador iniciado")

        # Abrir la URL de la reunión
        driver.get(url)
        print("   🌐 Página cargada")
        time.sleep(2)

        # Forzar SSO si es primera vez o nos manda a login
        if PRIMERA_VEZ or "signin" in driver.current_url or "accounts.google.com" in driver.current_url:
            print("   ℹ️ Realizando SSO con Google (primera vez o sesión inválida)...")
            tenant_base = "https://renata.zoom.us" if "renata.zoom.us" in url else "https://zoom.us"
            login_zoom_via_google(driver, wait, tenant_base=tenant_base)
            time.sleep(2)

        # Estado actual
        try:
            cur = driver.current_url
        except Exception:
            cur = ""

        host_wc_url = build_webclient_url(url, as_host=True, display_name=TU_NOMBRE)
        join_wc_url = build_webclient_url(url, as_host=False, display_name=TU_NOMBRE)

        # Si estás en /profile, o en un lugar que no sea la sala, fuerza join
        if "/profile" in cur or ("/wc/" not in cur and "/j/" not in cur and "/w/" not in cur):
            driver.get(join_wc_url)
            time.sleep(3)

        # Intentar “Start/Join” (en web client)
        try:
            print("   ⏳ Intentando entrar (Web Client)...")
            posibles_botones = [
                "//button[contains(translate(text(), 'INICIAR', 'iniciar'),'iniciar')]",
                "//button[contains(translate(text(), 'JOIN', 'join'),'join')]",
                "//button[contains(translate(text(), 'UNIRSE', 'unirse'),'unirse')]",
                "//button[@id='joinBtn']",
                "//button[contains(@class, 'preview-join-button')]",
                "//button[contains(@aria-label, 'join')]"
            ]
            for sx in posibles_botones:
                try:
                    btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, sx)))
                    driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                    time.sleep(0.3)
                    driver.execute_script("arguments[0].click();", btn)
                    print("   ✅ Botón de unión presionado")
                    time.sleep(2)
                    break
                except Exception:
                    continue
        except Exception as e:
            print(f"   ℹ️ No se pudo auto-press en WC: {e}")

        # Verificar si entró al Web Client (wc/)
        try:
            time.sleep(1.5)
            current_url = driver.current_url
            if '/wc/' in current_url:
                print("   🎉 ¡ÉXITO! Ya estás en la reunión de Zoom (Web Client).")
            else:
                print("   ℹ️ Verifica manualmente si entraste a la reunión.")
                print(f"   URL actual: {current_url[:100]}...")
        except Exception:
            pass

        print("   ℹ️  El navegador permanecerá abierto (no cierres la ventana).")
        return True

    except Exception as e:
        print(f"   ❌ Error general: {e}")
        try:
            if driver:
                driver.quit()
        except Exception:
            pass
        return False

def abrir_reunion(reunion):
    """Abre una reunión según su configuración."""
    modo = reunion.get("modo", "zoom_app")
    url = reunion["url"]

    if modo == "zoom_app":
        return abrir_zoom_app(url)
    elif modo == "navegador_auto":
        nombre = reunion.get("nombre_usuario", "Usuario")
        incognito = reunion.get("incognito", False)
        return abrir_navegador_automatico(url, nombre, incognito)
    else:
        print(f"⚠️  Modo desconocido: {modo}")
        return False

# =====================================
# PLANIFICADOR
# =====================================
WEEKDAY_MAP = {
    # español
    "lun": 0, "mar": 1, "mie": 2, "mié": 2, "jue": 3, "vie": 4, "sab": 5, "sáb": 5, "dom": 6,
    # inglés (por si acaso)
    "mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6
}

def _parse_hhmm(hhmm: str) -> dtime:
    hh, mm = hhmm.strip().split(":")
    return dtime(hour=int(hh), minute=int(mm), tzinfo=TZ)

def _next_weekday_datetime(target_wd: int, hhmm: dtime, now: datetime) -> datetime:
    """Próxima fecha con el weekday target_wd a la hora hhmm, a partir de now."""
    days_ahead = (target_wd - now.weekday()) % 7
    candidate = (now + timedelta(days=days_ahead)).replace(hour=hhmm.hour, minute=hhmm.minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=7)
    return candidate

def compute_next_run(reu: dict) -> datetime | None:
    """
    Devuelve el próximo datetime (en TZ local) para abrir la reunión,
    restando 'abrir_antes_min' al horario programado.
    """
    prog = reu.get("programacion") or {}
    abrir_antes = int(reu.get("abrir_antes_min", 20))
    now = datetime.now(TZ)

    if prog.get("tipo") == "unico":
        fh = prog.get("fecha_hora")  # "YYYY-MM-DD HH:MM"
        if not fh:
            return None
        try:
            dt = datetime.strptime(fh, "%Y-%m-%d %H:%M").replace(tzinfo=TZ)
        except ValueError:
            print(f"⚠️  fecha_hora inválida: {fh} (usa 'YYYY-MM-DD HH:MM')")
            return None
        run = dt - timedelta(minutes=abrir_antes)
        return run if run > now else None

    elif prog.get("tipo") == "semanal":
        dias = prog.get("dias") or []
        if not dias or not prog.get("hora"):
            return None
        hhmm = _parse_hhmm(prog["hora"])
        # buscar la próxima ocurrencia entre los días configurados
        candidates = []
        for d in dias:
            wd = WEEKDAY_MAP.get(d.strip().lower())
            if wd is None:
                continue
            candidates.append(_next_weekday_datetime(wd, hhmm, now))
        if not candidates:
            return None
        next_dt = min(candidates)
        return next_dt - timedelta(minutes=abrir_antes)

    else:
        # Sin programación: ejecutar inmediatamente
        return now

def planificar_reunion(reunion: dict):
    """Thread que espera hasta el siguiente run y abre la reunión."""
    nombre = reunion.get("nombre")
    while True:
        proximo = compute_next_run(reunion)
        now = datetime.now(TZ)
        if proximo is None:
            print(f"⏭️  {nombre}: no hay próximas ejecuciones (quizá ya pasó o falta configurar).")
            return

        delta = (proximo - now).total_seconds()
        if delta <= 0:
            # Ejecutar ya
            print(f"\n🕒 [{now.strftime('%Y-%m-%d %H:%M:%S')}] Abriendo: {nombre}")
            abrir_reunion(reunion)
            # Si es único, terminar; si es semanal, recalcular para la próxima vuelta
            if (reunion.get("programacion") or {}).get("tipo") == "unico":
                print(f"✅ {nombre}: ejecución única realizada. Fin.")
                return
            else:
                # Esperar 60s antes de calcular la próxima
                time.sleep(60)
                continue
        else:
            # Informar y dormir en intervalos razonables
            mins = int(delta // 60)
            secs = int(delta % 60)
            print(f"⏳ {nombre}: se abrirá en {mins}m {secs}s (a las {proximo.astimezone(TZ).strftime('%H:%M')} local).")
            sleep_chunk = min(30, int(delta))  # dormimos en trozos de hasta 30s
            time.sleep(max(1, sleep_chunk))

# =====================================
# PROCESO PRINCIPAL
# =====================================
def main():
    print("=" * 70)
    print("🚀 ZOOM AUTO-JOIN LAUNCHER v3.0 (Programación automática - abre X min antes)")
    print("=" * 70)
    print(f"Sistema operativo: {platform.system()}")
    print(f"Zona horaria: {TZ.key}")
    print(f"Total de reuniones configuradas: {len(reuniones)}\n")

    # Lanzar un hilo por reunión (cada uno espera su horario y la abre)
    threads = []
    for r in reuniones:
        t = threading.Thread(target=planificar_reunion, args=(r,), daemon=True)
        t.start()
        threads.append(t)

    # Mantener el script corriendo
    try:
        while any(t.is_alive() for t in threads):
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Script finalizado por el usuario")

# =====================================
# EJECUCIÓN
# =====================================
if __name__ == "__main__":
    main()
