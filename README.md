### 🧾 **README.md**

````markdown
# 🧠 Apertura de Aulas Automáticas Zoom

Script en **Python 3** que permite abrir reuniones de **Zoom** de manera automática, ya sea desde la aplicación o desde el navegador, **X minutos antes** de la hora programada (por defecto 20 minutos).

Diseñado especialmente para el entorno **Univirtual UTP**, con soporte para inicios de sesión SSO mediante **Google (Renata Zoom)** y configuración flexible de horarios semanales o eventos únicos.

---

## 🚀 Características principales

- ✅ Apertura automática de reuniones de Zoom (App o Navegador)
- ⏰ Planificación semanal o por fecha única
- 🕓 Permite definir cuántos minutos antes abrir la reunión
- 👤 Inicio de sesión automático con Google (SSO)
- 💾 Guarda la sesión en Chrome (no pide login cada vez)
- 🧩 Compatible con `renata.zoom.us` y `zoom.us`
- ⚙️ Funciona en Linux, Windows o macOS

---

## 🧩 Requisitos

- **Python 3.9+**
- Google Chrome instalado
- Paquetes de Python:
  ```bash
  pip install selenium webdriver-manager
````

---

## 📁 Instalación

1. Clona este repositorio o descárgalo:

   ```bash
   git clone https://github.com/Santi292003/Apertura-de-aulas-autom-ticas-Zoom.git
   cd Apertura-de-aulas-autom-ticas-Zoom
   ```

2. (Opcional pero recomendado) crea un entorno virtual:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Instala las dependencias:

   ```bash
   pip install -r requirements.txt
   ```

> Si no tienes `requirements.txt`, puedes generarlo con:
>
> ```bash
> pip freeze > requirements.txt
> ```

---

## ⚙️ Configuración

Abre el archivo `zoom_auto_launcher.py` y modifica los parámetros principales:

```python
TU_NOMBRE = "Regencia de Farmacia UTP - Univirtual"
ZOOM_EMAIL = "univirtual_zoom_2@utp.edu.co"
ZOOM_PASSWORD = "Utpunivirtual2020"
```

Define tus reuniones en la lista `reuniones`:

```python
reuniones = [
    {
        "nombre": "Legislación Farmacéutica I G301",
        "url": "https://zoom.us/j/84835100297",
        "modo": "zoom_app",
        "programacion": {
            "tipo": "semanal",
            "dias": ["lun", "jue"],  # días de la semana
            "hora": "17:00"          # hora local (24h)
        },
        "abrir_antes_min": 20        # minutos antes de la hora programada
    }
]
```

---

## 🕹️ Ejecución

Simplemente ejecuta:

```bash
python zoom_auto_launcher.py
```

El script mostrará:

* Cuándo se abrirá cada reunión
* Cuánto falta para la próxima apertura
* Mensajes de estado en consola (inicios de sesión, éxito, advertencias, etc.)

Ejemplo de salida:

```
⏳ Legislación Farmacéutica I G301: se abrirá en 19m 58s (a las 16:40 local).
🕒 [2025-10-09 16:40:00] Abriendo: Legislación Farmacéutica I G301
🎉 ¡ÉXITO! Ya estás en la reunión de Zoom (Web Client).
```

---

## 🧰 Estructura del proyecto

```
Apertura-de-aulas-autom-ticas-Zoom/
│
├── zoom_auto_launcher.py     # Script principal
├── requirements.txt          # Dependencias (opcional)
├── README.md                 # Documentación
└── .gitignore                # Ignora el venv/ y otros archivos locales
```

---

## 💡 Notas importantes

* Si usas **Renata Zoom**, el script entra directamente con `/wc/join/` (modo navegador).
* Si es tu primera ejecución, activa `PRIMERA_VEZ = True` para guardar tu sesión Google.
* No cierres el navegador una vez abierta la reunión: el script mantiene la sesión activa.
* Puedes ejecutar este script en segundo plano (por ejemplo con `tmux` o `nohup`).

---

## 🧠 Autores

👤 **Juan Pablo González Trejos**
Ingeniero de Sistemas Univirtual - Universidad Tecnológica de Pereira
📧 Contacto: [soporteunivirtual@utp.edu.co](soporteunivirtual@utp.edu.co)

👤 **Santiago Ramírez González**
Practicante Univirtual - Universidad Tecnológica de Pereira
📧 Contacto: [soporteunivirtual@utp.edu.co](soporteunivirtual@utp.edu.co)

---

## 📜 Licencia

Este proyecto se distribuye bajo la licencia **MIT**.
Puedes usarlo, modificarlo y compartirlo libremente dando crédito al autor.

````

---

### 📌 Para agregarlo a tu repositorio

Guárdalo como `README.md` dentro de tu carpeta del proyecto y luego ejecuta:

```bash
git add README.md
git commit -m "Agrega README con documentación completa"
git push
````


