"""
EpaleBot v2 — Iniciativa de Logística Humanitaria Venezuela
============================================================
Mejoras v2:
- Ubicación en 2 pasos: Estado + Zona (opcional)
- Match por similitud (colchón = colchones)
- Múltiples matches ordenados por reputación
- Estados: Disponible → Conectado → Entregado
- Timer 48hs: calificación negativa automática si no se cierra
- Separación de ítems por coma y "y"
"""

import re
import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta
from difflib import SequenceMatcher
import asyncio
import itertools
_id_counter = itertools.count(1)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters, ContextTypes
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import gspread
from google.oauth2.service_account import Credentials

# ── CONFIG ─────────────────────────────────────────────────────────────────────
TOKEN    = os.environ.get("BOT_TOKEN", "8905191478:AAHFR-vDCV4XiA3-isnQ9OtEzHlGi18KZFQ")
SHEET_ID = os.environ.get("SHEET_ID", "19aX050iUUi9mB1A5jHQKsad8mhZysv2LENjjJLOruGs")
HORAS_MATCH = 48

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

CREDS_INFO = {
    "type": "service_account",
    "project_id": "buscave",
    "client_email": "buscave-sheets@buscave.iam.gserviceaccount.com",
    "private_key_id": "2feddb73f8e1c2eb149433cc298f737dab8b26a3",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQCo/MiVsXknveOV\nvhbNPfc0Ko8AK5SaBUv+mKuWlQNsokjFNeeCoooaa9E/MKiy9fWvETksfyFnOthR\nZzhAGa2n2TfAOL67ZESE8hlj3Y77SGfIRIff9DFEfIFphyr7WFZ3qfGWJQwcMqnZ\nVrWKEBUMV5wTogyaE+C0NPdKG8O6z5Gq97DSsLd2J0DffzGF+bQ247x/WRuq0d5T\nsAzvq0EPH+mhtM5+WtU+DWBzmrDvJqw5LjwDAeATZUAml3jZWlU+fV/BrUbdHUE8\nt72CF3bfGJQ45fskTppaM46uunQgDCjaUtqQAbeNseErdh8wHVp0rlD9q4KvR3FJ\nkxR+8W7PAgMBAAECggEADJZDlI7TEOg+du1hQmleq+aNnzwfxfcmCXEyurUfu6w8\n0l+o/lx//+bO/69uqWHTqnYUdaGEie1ipnGTSYcAHdP6qJkxb8DQr7xesscSetoS\nTOL54e8M6maBtywHwg/65M/mPEJHLCSD7TndrMp03uX5rKax3JolbxbQ4pa91gC4\nA0e+3KCfWAfXQcxGa7TWEkuY7TeG5olIwUyXNBGYHxXGA4Y0VFrVIOemslQAgjWw\n39brmEsJ3K6i2i2p6PTkcLwPl13zK+vJ5SY9K5FsC2Yt03jBYbun9RCPOSNEdgpy\nfzjwCOp0lnMYgFl/9ZtoQFVszGZggE/Q4NPKNwStRQKBgQDQOk4MDUheA9REp30O\nAqH3jhJnD4RvwEFrzzNI5eciBUsRihFjdxjzHDPkOfqz4ZRqSR+Js0c1sJwstN22\n2+Ric0aFEjGiEaKKM6WAiTPxCOLDydhZFHd+zqpdOCWc673WBAf7zgR1tKntmeI+\n6sTmsR5QrsX0xZHEHdikJW+4HQKBgQDPwc3z8LntA0r4/HvmUCvT4n78m7pWzFI8\nGojajdPy82QxC80Qvqr60gRMr8trdd6plupN+hvwYrT2WSEKF7635M5sYCkzk9A0\n4Bs3IozACBJZ2j4E8Y1xCqgX3FjrYPCNv25IJkK3t9nvdGtZA9nw7ra5LbelUZvP\n6B7dY3NG2wKBgQCG6Z/z0w9WSqjXqqUt1KrYWGa3+6fVN/2rOl6CFuNAeal/vbMy\nfNHfgiBk+OPkdH3St3oFn/C9aqZlmPImLia1WvcP9Q/PcBmd7YSH2V2cCCPUswzH\n+qjJsmFTcLN+Doe7CHWbwonFMb7/wTqDhVz6EzwPDo4X34JoTOY2xEK0SQKBgBMj\nQiqHcUkQ9ZYMBAnKNs9U3Oe+HKMkPSsGMrcXO3/0xbTy5lf1iGCEehrqUq26dOFg\nYoL+WBaDsTHEMhPw7gOYkx9OmF0E77f/MOKaTybdV3tpbC8eZS4VkjhodtRv4Jje\nGnWQ+LJdwDibm8veW/QiuThDqtgStWyocDdqktLjAoGBAIQwB+W1Wbzek8fIO1Jf\nvtqbh5fuh3Afw9MQ8mt6Bd9cGjS3DyTb9hdt1zxMfdNzCRvNT0WWHUiJOJXodddm\nBpmhCN3LmBZ16kNCrz4pMNTponpDoyLUivz1BmEof4xES/yDA2FvCWdH9GpyWoVC\nm2WfecF1HycsDhLaoedZMtM3\n-----END PRIVATE KEY-----\n",
    "client_id": "104187521655232190515",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/buscave-sheets%40buscave.iam.gserviceaccount.com"
}

# ── CATEGORÍAS ─────────────────────────────────────────────────────────────────
CATEGORIAS = {
    "🍚 Alimentos":          ["comida","alimento","arroz","pasta","harina","aceite","leche",
                              "carne","pollo","atun","sardina","frijol","caraotas","azucar",
                              "sal","cafe","pan","galleta","cereal","fruta","verdura",
                              "huevo","enlatado","mantequilla","queso","yogur","avena","lenteja"],
    "👕 Ropa":               ["ropa","camisa","pantalon","vestido","zapato","tenis","sandalia",
                              "medias","abrigo","chaqueta","sueter","falda","jean","uniforme",
                              "pijama","calzado","ropa interior"],
    "🛏️ Muebles":            ["mueble","silla","mesa","cama","colchon","sofa","closet",
                              "armario","escritorio","estante","anaquel","cajonera","hamaca",
                              "mecedora","buro","nevera de madera","gabinetero"],
    "💊 Medicamentos":       ["medicamento","medicina","pastilla","tableta","jarabe",
                              "antibiotico","analgesico","vitamina","insulina","suero",
                              "venda","curacion","gaza","alcohol","antiseptico","paracetamol"],
    "📺 Electrodomésticos":  ["nevera","lavadora","microondas","licuadora","television","tv",
                              "abanico","ventilador","estufa","cocina","plancha","computadora",
                              "laptop","celular","telefono","radio","electrodomestico"],
    "🧱 Materiales":         ["cemento","bloque","ladrillo","pintura","madera","hierro",
                              "cabilla","lamina","techo","zinc","herramienta","martillo",
                              "pala","pico","clavo","tornillo","material"],
    "🧴 Higiene":            ["jabon","shampoo","crema","desodorante","papel higienico",
                              "toalla","panal","pañal","cepillo","pasta dental","detergente",
                              "cloro","desinfectante","higiene","servilleta"],
    "📚 Educación":          ["libro","cuaderno","lapiz","lapicero","mochila","bolso",
                              "regla","tijera","marcador","crayon","calculadora","diccionario",
                              "material escolar"],
    "🚌 Transporte":         ["transporte","pasaje","bus","metro","moto","bicicleta",
                              "gasolina","gasoil"],
    "📦 Otros":              []
}

ESTADOS_VE = [
    "Distrito Capital", "Miranda", "Aragua", "Carabobo", "Lara",
    "Zulia", "Bolívar", "Anzoátegui", "Monagas", "Sucre",
    "Mérida", "Táchira", "Barinas", "Portuguesa", "Guárico",
    "Cojedes", "Yaracuy", "Falcón", "Vargas", "Nueva Esparta",
    "Trujillo", "Apure", "Amazonas", "Delta Amacuro"
]

# ── HELPERS ────────────────────────────────────────────────────────────────────
# Rate limiting: máximo 5 publicaciones por usuario por hora
_rate_limit = {}  # {user_id: [timestamps]}

def check_rate_limit(user_id):
    """Retorna True si el usuario puede publicar, False si excedió el límite."""
    from datetime import timedelta
    ahora = datetime.now()
    uid = str(user_id)
    if uid not in _rate_limit:
        _rate_limit[uid] = []
    # Limpiar timestamps viejos (más de 1 hora)
    _rate_limit[uid] = [t for t in _rate_limit[uid] if ahora - t < timedelta(hours=1)]
    if len(_rate_limit[uid]) >= 5:
        return False
    _rate_limit[uid].append(ahora)
    return True

def normalizar(texto):
    t = texto.lower().strip()
    for k, v in {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ü":"u","ñ":"n"}.items():
        t = t.replace(k, v)
    return t

def detectar_categoria(texto):
    t = normalizar(texto)
    puntajes = {}
    for cat, palabras in CATEGORIAS.items():
        p = 0
        for w in palabras:
            wn = normalizar(w)
            # Palabra COMPLETA (no substring: evita "pan" dentro de "pantalon"),
            # tolerando plural (+s / +es: silla->sillas, huevo->huevos).
            # Las frases (ej "ropa interior") pesan más al desempatar.
            if re.search(r'(?<!\w)' + re.escape(wn) + r'(?:es|s)?(?!\w)', t):
                p += len(wn.split())
        if p > 0:
            puntajes[cat] = p
    return max(puntajes, key=puntajes.get) if puntajes else "📦 Otros"

def similitud(a, b):
    """Calcula similitud entre dos strings (0-1). Considera raíces comunes."""
    a, b = normalizar(a), normalizar(b)
    # Coincidencia exacta
    if a == b:
        return 1.0
    # Uno contiene al otro (colchon en colchones)
    if a in b or b in a:
        return 0.9
    # Similitud por caracteres
    return SequenceMatcher(None, a, b).ratio()

def sanitizar(texto, max_len=200):
    """Limpia el texto de usuario — previene injection y limita longitud."""
    if not texto:
        return ""
    # Eliminar caracteres peligrosos para Sheets (= + - @ que pueden ejecutar fórmulas)
    texto = re.sub(r'^[=+\-@]', '', texto.strip())
    # Eliminar caracteres de control
    texto = re.sub(r'[\x00-\x1f\x7f]', '', texto)
    # Limitar longitud
    return texto[:max_len]

def separar_items(texto):
    """Separa ítems por coma y por 'y'."""
    texto = sanitizar(texto)
    partes = texto.split(",")
    items = []
    for parte in partes:
        sub = re.split(r'\s+[yY]\s+', parte.strip())
        items.extend([s.strip() for s in sub if s.strip()])
    return [i for i in items if i][:10]  # máximo 10 ítems por envío

def stars(rep):
    """Convierte reputación numérica a estrellas."""
    try:
        r = int(rep)
    except:
        r = 0
    if r <= 0:
        return "Sin calificaciones"
    return "⭐" * min(r, 5)

# ── SHEETS ─────────────────────────────────────────────────────────────────────
def _cargar_creds_info():
    """
    Carga las credenciales en orden de prioridad, tolerando el mangling de \\n:
      1. Secret File de Render (ruta en GOOGLE_CREDS_FILE, default /etc/secrets/credentials.json)
      2. Variable de entorno GOOGLE_CREDS_JSON (normalizando \\n literales)
      3. Dict CREDS_INFO hardcodeado en el script (fallback validado)
    Devuelve (info_dict, fuente_str).
    """
    import json, os

    # 1) Secret File (recomendado — no sufre mangling de \n)
    ruta = os.environ.get("GOOGLE_CREDS_FILE", "/etc/secrets/credentials.json")
    if ruta and os.path.exists(ruta):
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                info = json.load(f)
            return info, f"secret_file:{ruta}"
        except Exception as e:
            logging.warning(f"No se pudo leer secret file {ruta}: {e}")

    # 2) Env var GOOGLE_CREDS_JSON (normalizando saltos de línea)
    creds_json = os.environ.get("GOOGLE_CREDS_JSON")
    if creds_json:
        try:
            info = json.loads(creds_json)
            if isinstance(info.get("private_key"), str):
                info["private_key"] = info["private_key"].replace("\\n", "\n")
            return info, "env:GOOGLE_CREDS_JSON"
        except Exception as e:
            logging.warning(f"GOOGLE_CREDS_JSON inválida, usando fallback: {e}")

    # 3) Fallback: dict hardcodeado (clave validada localmente)
    return CREDS_INFO, "hardcoded:CREDS_INFO"


def get_client():
    info, fuente = _cargar_creds_info()
    logging.info(f"[auth] Credenciales cargadas desde: {fuente}")
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)

# Cache de worksheets ya verificados para no llamar a Sheets en cada operación
_ws_cache = {}

def get_ws(nombre, headers):
    global _ws_cache
    # Si ya está en cache y fue verificado, devolver directo
    if nombre in _ws_cache:
        return _ws_cache[nombre]
    try:
        client = get_client()
        sheet  = client.open_by_key(SHEET_ID)
        try:
            ws = sheet.worksheet(nombre)
            # Solo verificar headers la primera vez
            existing = ws.row_values(1)
            if not existing:
                ws.append_row(headers)
            elif existing != headers:
                # NO borrar datos: solo reescribir la fila de encabezados
                # (permite agregar columnas nuevas como FOTO sin perder registros).
                logging.warning(f"Actualizando headers en [{nombre}] sin borrar datos...")
                ws.update(values=[headers], range_name="A1")
        except gspread.exceptions.WorksheetNotFound:
            ws = sheet.add_worksheet(nombre, rows=2000, cols=len(headers))
            ws.append_row(headers)
        _ws_cache[nombre] = ws
        return ws
    except Exception as e:
        logging.error(f"Sheets error [{nombre}]: {e}")
        return None

HDRS_DON = ["ID","FECHA","FECHA_MATCH","USER_ID","USERNAME","NOMBRE",
            "ESTADO_VE","ZONA","DESCRIPCION","CATEGORIA","ESTADO","MATCH_ID","REPUTACION","FOTO"]
HDRS_NEC = ["ID","FECHA","FECHA_MATCH","USER_ID","USERNAME","NOMBRE",
            "ESTADO_VE","ZONA","DESCRIPCION","CATEGORIA","ESTADO","MATCH_ID","REPUTACION","FOTO"]
HDRS_MAT = ["ID","FECHA","DON_ID","NEC_ID","DON_USER","NEC_USER",
            "CATEGORIA","DESC_DON","DESC_NEC","ESTADO_DON","ZONA_DON","ESTADO_NEC","ZONA_NEC","ESTADO_MATCH"]

def guardar_sync(hoja, hdrs, fila):
    ws = get_ws(hoja, hdrs)
    if ws:
        ws.append_row(fila)
        return True
    return False

async def guardar(hoja, hdrs, fila):
    """Guardar en thread separado para no bloquear el bot."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, guardar_sync, hoja, hdrs, fila)

def get_disponibles_sync(hoja, hdrs):
    ws = get_ws(hoja, hdrs)
    if not ws:
        return []
    try:
        return [r for r in ws.get_all_records() if r.get("ESTADO") == "Disponible"]
    except:
        return []

async def get_disponibles(hoja, hdrs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, get_disponibles_sync, hoja, hdrs)

async def buscar_matches_similitud(descripcion, categoria, hoja, hdrs):
    """Busca registros con categoría igual y descripción similar."""
    disponibles = await get_disponibles(hoja, hdrs)
    matches = []
    for r in disponibles:
        if r.get("CATEGORIA") != categoria:
            continue
        sim = similitud(descripcion, r.get("DESCRIPCION", ""))
        if sim >= 0.5:  # umbral de similitud
            matches.append((sim, r))
    # Ordenar: primero por reputación, luego por similitud
    matches.sort(key=lambda x: (int(x[1].get("REPUTACION") or 0), x[0]), reverse=True)
    return [r for _, r in matches]

def actualizar_estado_id_sync(hoja, hdrs, id_reg, estado, match_id="", fecha_match=""):
    ws = get_ws(hoja, hdrs)
    if not ws:
        return
    try:
        rows = ws.get_all_values()
        hdrs_row = rows[0]
        for i, row in enumerate(rows[1:], start=2):
            if row[0] == str(id_reg):
                ws.update_cell(i, hdrs_row.index("ESTADO")+1, estado)
                if match_id:
                    ws.update_cell(i, hdrs_row.index("MATCH_ID")+1, match_id)
                if fecha_match and "FECHA_MATCH" in hdrs_row:
                    ws.update_cell(i, hdrs_row.index("FECHA_MATCH")+1, fecha_match)
                break
    except Exception as e:
        logging.error(f"Error actualizando {id_reg}: {e}")

async def actualizar_estado_id(hoja, hdrs, id_reg, estado, match_id="", fecha_match=""):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, actualizar_estado_id_sync, hoja, hdrs, id_reg, estado, match_id, fecha_match)

def actualizar_reputacion(hoja, hdrs, id_reg, puntos):
    ws = get_ws(hoja, hdrs)
    if not ws:
        return
    try:
        rows = ws.get_all_values()
        hdrs_row = rows[0]
        for i, row in enumerate(rows[1:], start=2):
            if row[0] == str(id_reg):
                actual = int(row[hdrs_row.index("REPUTACION")] or 0)
                ws.update_cell(i, hdrs_row.index("REPUTACION")+1, actual + puntos)
                break
    except Exception as e:
        logging.error(f"Error reputacion: {e}")

def get_match_activo(match_id):
    ws = get_ws("Matches", HDRS_MAT)
    if not ws:
        return None
    try:
        for r in ws.get_all_records():
            if r.get("ID") == match_id:
                return r
        return None
    except:
        return None

def cerrar_match(match_id, estado="Entregado"):
    ws = get_ws("Matches", HDRS_MAT)
    if not ws:
        return
    try:
        rows = ws.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if row[0] == match_id:
                ws.update_cell(i, HDRS_MAT.index("ESTADO_MATCH")+1, estado)
                break
    except:
        pass

# ── ESTADOS DE CONVERSACIÓN ────────────────────────────────────────────────────
(TIPO, ESTADO_VE, ZONA, DESCRIPCION, FOTO_STEP, CONFIRMAR, CALIFICAR_STEP) = range(7)

# ── SCHEDULER para vencimiento de matches ─────────────────────────────────────
scheduler = AsyncIOScheduler()

async def vencer_match(bot, match_id, don_user_id, nec_user_id, don_id, nec_id):
    """Se ejecuta a las 48hs — califica negativo y libera los ítems."""
    logging.info(f"Venciendo match {match_id}")
    match = get_match_activo(match_id)
    if not match or match.get("ESTADO_MATCH") in ["Entregado", "Vencido"]:
        return  # Ya fue cerrado manualmente

    cerrar_match(match_id, "Vencido")
    actualizar_estado_id("Donaciones", HDRS_DON, don_id, "Disponible")
    actualizar_estado_id("Necesidades", HDRS_NEC, nec_id, "Disponible")
    actualizar_reputacion("Donaciones", HDRS_DON, don_id, -1)
    actualizar_reputacion("Necesidades", HDRS_NEC, nec_id, -1)

    msg = (
        "⏰ *Match vencido*\n\n"
        "Han pasado 48 horas sin confirmar la entrega.\n"
        "Ambas partes recibieron una calificación negativa automática.\n"
        "Sus publicaciones vuelven a estar disponibles.\n\n"
        "Si hubo un problema coordinando, podés publicar de nuevo con /start."
    )
    for uid in [don_user_id, nec_user_id]:
        try:
            if uid:
                await bot.send_message(chat_id=int(uid), text=msg, parse_mode="Markdown")
        except:
            pass

# ── /start ─────────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nombre = update.effective_user.first_name
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 Tengo algo para dar",  callback_data="donar")],
        [InlineKeyboardButton("🔴 Necesito ayuda",       callback_data="necesitar")],
        [InlineKeyboardButton("📋 Mis publicaciones",    callback_data="mis_pub")],
        [InlineKeyboardButton("ℹ️ Cómo funciona",        callback_data="info")],
    ])
    await update.message.reply_text(
        f"👋 *¡Hola, {nombre}!*\n"
        "Bienvenido/a a *EpaleBot* — conectamos donantes con personas que necesitan ayuda en Venezuela.\n"
        "Aquí nos ayudamos entre todos. 🇻🇪🤝",
        parse_mode="Markdown",
        reply_markup=kb
    )
    return TIPO

# ── MENÚ ───────────────────────────────────────────────────────────────────────
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data  = query.data

    if data == "info":
        await query.edit_message_text(
            "ℹ️ *Cómo funciona EpaleBot*\n\n"
            "1️⃣ Elegís si tenés algo para dar o necesitás ayuda\n"
            "2️⃣ Indicás tu estado y zona\n"
            "3️⃣ Describís los ítems separados por coma\n"
            "4️⃣ El bot detecta la categoría automáticamente\n"
            "5️⃣ Si hay match te mostramos los disponibles ordenados por reputación\n"
            "6️⃣ Elegís con quién contactar y tienen 48hs para coordinar\n"
            "7️⃣ Al completar escribís /calificar\n\n"
            "🔒 Tu número no se comparte. Solo tu usuario de Telegram.\n"
            "⏰ Los matches vencen a las 48hs sin confirmación.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    if data == "mis_pub":
        uid = str(query.from_user.id)
        msg = "📋 *Tus publicaciones:*\n\n"
        encontrado = False
        for hoja, hdrs, tipo in [("Donaciones", HDRS_DON, "🟢 Donación"),
                                  ("Necesidades", HDRS_NEC, "🔴 Necesidad")]:
            ws = get_ws(hoja, hdrs)
            if ws:
                try:
                    for r in ws.get_all_records():
                        if str(r.get("USER_ID","")) == uid:
                            estado = r.get("ESTADO","")
                            msg += (f"*{tipo}* — {r.get('CATEGORIA','')}\n"
                                    f"📍 {r.get('ESTADO_VE','')} · {r.get('ZONA','')}\n"
                                    f"_{r.get('DESCRIPCION','')}_\n"
                                    f"Estado: {estado} · {stars(r.get('REPUTACION',0))}\n\n")
                            encontrado = True
                except:
                    pass
        if not encontrado:
            msg += "No tenés publicaciones."
        await query.edit_message_text(msg, parse_mode="Markdown")
        return ConversationHandler.END

    context.user_data["tipo"] = data
    await query.edit_message_text(
        f"{'🟢 *Donación*' if data == 'donar' else '🔴 *Necesidad*'}\n\n"
        "📍 *¿En qué estado de Venezuela estás?*\n\n"
        "_Ej: Distrito Capital, Miranda, Zulia, Carabobo..._",
        parse_mode="Markdown"
    )
    return ESTADO_VE

# ── ESTADO VENEZUELA ───────────────────────────────────────────────────────────
async def recibir_estado_ve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    estado_ve = update.message.text.strip()
    context.user_data["estado_ve"] = estado_ve
    await update.message.reply_text(
        f"✅ Estado: *{estado_ve}*\n\n"
        "📍 *¿En qué zona, sector o municipio?*\n"
        "_Opcional — podés escribir 'No especificada' si preferís_\n\n"
        "_Ej: Petare, Montalbán, El Hatillo, Centro..._",
        parse_mode="Markdown"
    )
    return ZONA

# ── ZONA ───────────────────────────────────────────────────────────────────────
async def recibir_zona(update: Update, context: ContextTypes.DEFAULT_TYPE):
    zona = update.message.text.strip()
    context.user_data["zona"] = zona
    tipo = context.user_data.get("tipo","donar")

    # Si el usuario venía de "Editar ubicación", ya tiene ítems cargados:
    # volvemos directo a la confirmación sin pedir la descripción de nuevo.
    if context.user_data.pop("editando_ubic", False):
        return await mostrar_confirmacion(update, context)

    await update.message.reply_text(
        f"✅ Zona: *{zona}*\n\n"
        f"{'📦 *¿Qué vas a donar?*' if tipo == 'donar' else '🙏 *¿Qué necesitás?*'}\n\n"
        "Si tenés varias cosas, separalas con coma.\n\n"
        "_Ej: pantalones, zapatos, colchón_\n"
        "_Ej: arroz, leche y medicamentos_",
        parse_mode="Markdown"
    )
    return DESCRIPCION

# ── DESCRIPCIÓN ────────────────────────────────────────────────────────────────
async def mostrar_confirmacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Arma y envía la pantalla de confirmación con los datos ya cargados."""
    tipo          = context.user_data.get("tipo","donar")
    items_con_cat = context.user_data.get("items", [])
    resumen = "".join(f"  {cat} — {item}\n" for item, cat in items_con_cat)
    plural  = len(items_con_cat) > 1

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirmar y publicar", callback_data="confirmar")],
        [InlineKeyboardButton("📝 Editar lo que doy",    callback_data="cambiar_desc")],
        [InlineKeyboardButton("📍 Editar ubicación",     callback_data="cambiar_ubic")],
        [InlineKeyboardButton("❌ Cancelar",             callback_data="cancelar")],
    ])
    foto_txt = "📷 Con foto adjunta\n" if context.user_data.get("foto") else ""
    texto = (
        f"{'🟢' if tipo == 'donar' else '🔴'} *Revisá tu{'s' if plural else ''} publicación{'es' if plural else ''}:*\n\n"
        f"📍 *{context.user_data['estado_ve']}* · {context.user_data['zona']}\n"
        f"📦 *{'Ítems' if plural else 'Ítem'} ({len(items_con_cat)}):*\n{resumen}\n"
        f"{foto_txt}\n¿Todo correcto?"
    )
    # Funciona tanto si venimos de un mensaje de texto como de un botón (callback)
    destino = update.message or update.callback_query.message
    await destino.reply_text(texto, parse_mode="Markdown", reply_markup=kb)
    return CONFIRMAR

async def recibir_descripcion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    items = separar_items(texto)
    items_con_cat = [(item, detectar_categoria(item)) for item in items]
    context.user_data["items"] = items_con_cat
    context.user_data.setdefault("foto", "")

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⏭️ Omitir foto", callback_data="omitir_foto")]])
    await update.message.reply_text(
        "📷 *¿Querés adjuntar una foto?*\n"
        "Enviá una foto del/los ítem(s) para mostrar su estado, o tocá *Omitir*.\n"
        "_(La foto queda visible desde el bot.)_",
        parse_mode="Markdown",
        reply_markup=kb
    )
    return FOTO_STEP

async def recibir_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guarda el file_id de la foto y pasa a confirmación."""
    if update.message.photo:
        # la última es la de mayor resolución
        context.user_data["foto"] = update.message.photo[-1].file_id
    return await mostrar_confirmacion(update, context)

async def omitir_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["foto"] = ""
    # mostrar_confirmacion usa update.message; con callback lo tomamos del mensaje editado
    await query.edit_message_text("📷 Sin foto. Preparando confirmación...")
    return await mostrar_confirmacion(update, context)

# ── CONFIRMAR ──────────────────────────────────────────────────────────────────
async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data  = query.data

    if data == "cancelar":
        await query.edit_message_text("❌ Cancelado. /start para comenzar de nuevo.")
        return ConversationHandler.END

    if data == "cambiar_desc":
        await query.edit_message_text(
            "📝 Escribí de nuevo *qué vas a donar/necesitar* (con comas si son varias cosas):",
            parse_mode="Markdown"
        )
        return DESCRIPCION

    if data == "cambiar_ubic":
        context.user_data["editando_ubic"] = True
        await query.edit_message_text(
            "📍 *¿En qué estado de Venezuela estás?*\n_Ej: Distrito Capital, Miranda..._",
            parse_mode="Markdown"
        )
        return ESTADO_VE

    # ── Guardar registros ──────────────────────────────────────────────────────
    user      = query.from_user
    tipo      = context.user_data.get("tipo","donar")
    estado_ve = context.user_data.get("estado_ve","")
    zona      = context.user_data.get("zona","")
    items     = context.user_data.get("items",[])
    fecha     = datetime.now().strftime("%Y-%m-%d %H:%M")
    uid       = str(user.id)
    uname     = f"@{user.username}" if user.username else user.first_name
    nombre    = user.first_name
    hoja      = "Donaciones" if tipo == "donar" else "Necesidades"
    hdrs      = HDRS_DON if tipo == "donar" else HDRS_NEC
    hoja_op   = "Necesidades" if tipo == "donar" else "Donaciones"
    hdrs_op   = HDRS_NEC if tipo == "donar" else HDRS_DON

    # Rate limit — maximo 5 publicaciones por hora por usuario
    if not check_rate_limit(user.id):
        await query.edit_message_text("Alcanzaste el limite de 5 publicaciones por hora. Intenta mas tarde.")
        return ConversationHandler.END

    ids_guardados = []
    for item_desc, item_cat in items:
        item_id = f"{'DON' if tipo=='donar' else 'NEC'}-{datetime.now().strftime('%Y%m%d%H%M%S')}-{next(_id_counter)}"
        foto = context.user_data.get("foto", "")
        await guardar(hoja, hdrs, [item_id, fecha, "", uid, uname, nombre,
                             estado_ve, zona, item_desc, item_cat, "Disponible", "", 0, foto])
        ids_guardados.append((item_id, item_desc, item_cat))

    # ── Buscar matches para cada ítem ──────────────────────────────────────────
    matches_encontrados = []
    for item_id, item_desc, item_cat in ids_guardados:
        matches = await buscar_matches_similitud(item_desc, item_cat, hoja_op, hdrs_op)
        if matches:
            matches_encontrados.append((item_id, item_desc, item_cat, matches))

    if matches_encontrados:
        # Tomar el primer ítem con matches y mostrar opciones
        item_id, item_desc, item_cat, matches = matches_encontrados[0]
        context.user_data["match_item_id"] = item_id
        context.user_data["match_item_desc"] = item_desc
        context.user_data["match_item_cat"] = item_cat
        context.user_data["match_hoja"] = hoja
        context.user_data["match_hoja_op"] = hoja_op
        context.user_data["match_hdrs"] = hdrs
        context.user_data["match_hdrs_op"] = hdrs_op

        plural = len(ids_guardados) > 1
        msg = (
            f"✅ *{'Publicaciones registradas' if plural else 'Publicación registrada'}* — "
            f"{len(ids_guardados)} ítem{'s' if plural else ''}\n\n"
            f"🎉 *Matches encontrados para:*\n"
            f"🏷️ {item_cat} — _{item_desc}_\n\n"
            f"*Opciones disponibles:*\n\n"
        )

        botones = []
        for i, m in enumerate(matches[:5]):
            rep     = stars(m.get("REPUTACION", 0))
            uname_m = m.get("USERNAME","")
            loc     = f"{m.get('ESTADO_VE','')} · {m.get('ZONA','')}"
            desc_m  = m.get("DESCRIPCION","")
            cat_m   = m.get("CATEGORIA","")
            tiene_foto = "  📷" if m.get("FOTO","") else ""
            msg    += f"{i+1}. {rep}{tiene_foto}\n👤 {uname_m} — 📍 {loc}\n🏷️ {cat_m}: _{desc_m}_\n\n"
            botones.append([InlineKeyboardButton(
                f"Elegir opcion {i+1} — {uname_m}", callback_data=f"elegir_{m.get('ID','')}"
            )])

        botones.append([InlineKeyboardButton("⏭️ Ver mis publicaciones sin match", callback_data="sin_match")])
        await query.edit_message_text(msg, parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup(botones))
        return CONFIRMAR

    else:
        resumen = "".join(f"  {c} — {d}\n" for _, d, c in ids_guardados)
        await query.edit_message_text(
            f"✅ *{'Publicaciones registradas' if len(ids_guardados)>1 else 'Publicación registrada'}*\n\n"
            f"{'🟢 Donación' if tipo=='donar' else '🔴 Necesidad'}\n"
            f"📍 *{estado_ve}* · {zona}\n\n{resumen}\n"
            "No hay matches disponibles ahora.\n"
            "Te avisamos cuando aparezca alguien compatible. 🤖",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

async def elegir_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """El usuario eligió con quién hacer match."""
    query = update.callback_query
    await query.answer()
    data  = query.data

    if data == "sin_match":
        await query.edit_message_text(
            "✅ Tus publicaciones están registradas. Te avisamos cuando haya matches. 🤖"
        )
        return ConversationHandler.END

    otro_id = data.replace("elegir_", "")
    user    = query.from_user
    tipo    = context.user_data.get("tipo","donar")
    hoja    = context.user_data.get("match_hoja","Donaciones")
    hoja_op = context.user_data.get("match_hoja_op","Necesidades")
    hdrs    = context.user_data.get("match_hdrs", HDRS_DON)
    hdrs_op = context.user_data.get("match_hdrs_op", HDRS_NEC)
    mi_id   = context.user_data.get("match_item_id","")
    uname   = f"@{user.username}" if user.username else user.first_name
    fecha   = datetime.now().strftime("%Y-%m-%d %H:%M")
    vencimiento = (datetime.now() + timedelta(hours=HORAS_MATCH)).strftime("%Y-%m-%d %H:%M")
    match_id = f"MATCH-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # Buscar datos del otro
    ws_op = get_ws(hoja_op, hdrs_op)
    otro  = {}
    if ws_op:
        for r in ws_op.get_all_records():
            if r.get("ID") == otro_id:
                otro = r
                break

    otro_uid  = otro.get("USER_ID","")
    otro_user = otro.get("USERNAME","")
    item_desc = context.user_data.get("match_item_desc","")
    item_cat  = context.user_data.get("match_item_cat","")

    # Guardar match
    await guardar("Matches", HDRS_MAT, [
        match_id, fecha,
        mi_id if tipo=="donar" else otro_id,
        otro_id if tipo=="donar" else mi_id,
        uname if tipo=="donar" else otro_user,
        otro_user if tipo=="donar" else uname,
        item_cat, item_desc, otro.get("DESCRIPCION",""),
        context.user_data.get("estado_ve",""), context.user_data.get("zona",""),
        otro.get("ESTADO_VE",""), otro.get("ZONA",""),
        "Activo"
    ])

    # Actualizar estados
    await actualizar_estado_id(hoja,    hdrs,    mi_id,   "Conectado", match_id, fecha)
    await actualizar_estado_id(hoja_op, hdrs_op, otro_id, "Conectado", match_id, fecha)

    # Guardar para /calificar
    context.user_data["match_id_activo"]  = match_id
    context.user_data["otro_id_reg"]      = otro_id
    context.user_data["otro_hoja"]        = hoja_op
    context.user_data["otro_uid"]         = otro_uid

    msg_match = (
        f"🤝 *¡Match confirmado!*\n\n"
        f"🏷️ *Categoría:* {item_cat}\n"
        f"👤 *Contacto:* {otro_user}\n"
        f"📍 *Ubicación:* {otro.get('ESTADO_VE','')} · {otro.get('ZONA','')}\n\n"
        f"⏰ Tienen *{HORAS_MATCH} horas* para coordinar la entrega.\n"
        f"Si no confirman antes de las {vencimiento}, ambos recibirán una calificación negativa automática.\n\n"
        f"Cuando completen la entrega escribí /calificar ✅"
    )

    await query.edit_message_text(msg_match, parse_mode="Markdown")

    # Enviar la foto del ítem (si la publicación del otro tiene una)
    foto_otro = otro.get("FOTO", "")
    if foto_otro:
        try:
            await context.bot.send_photo(
                chat_id=user.id,
                photo=foto_otro,
                caption=f"📷 Foto del ítem: {otro.get('DESCRIPCION','')}"
            )
        except Exception as e:
            logging.error(f"Error enviando foto del match: {e}")

    # Notificar al otro
    try:
        if otro_uid:
            await context.bot.send_message(
                chat_id=int(otro_uid),
                text=(
                    f"🤝 *¡Alguien eligió tu publicación!*\n\n"
                    f"🏷️ *Categoría:* {item_cat}\n"
                    f"👤 *Contacto:* {uname}\n\n"
                    f"⏰ Tienen *{HORAS_MATCH} horas* para coordinar la entrega.\n"
                    f"Si no confirman antes de las {vencimiento}, ambos recibirán una calificación negativa automática.\n\n"
                    f"Cuando completen escribí /calificar ✅"
                ),
                parse_mode="Markdown"
            )
    except Exception as e:
        logging.error(f"Error notificando match: {e}")

    # Programar vencimiento a las 48hs
    scheduler.add_job(
        vencer_match,
        'date',
        run_date=datetime.now() + timedelta(hours=HORAS_MATCH),
        args=[context.bot, match_id, str(user.id), otro_uid,
              mi_id if tipo=="donar" else otro_id,
              otro_id if tipo=="donar" else mi_id],
        id=match_id
    )

    return ConversationHandler.END

# ── /calificar ─────────────────────────────────────────────────────────────────
async def calificar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("👍 Se completó correctamente", callback_data="rep_pos")],
        [InlineKeyboardButton("👎 Hubo problemas",           callback_data="rep_neg")],
    ])
    await update.message.reply_text(
        "⭐ *Calificar intercambio*\n\n¿Cómo resultó?",
        parse_mode="Markdown",
        reply_markup=kb
    )
    return CALIFICAR_STEP

async def recibir_calificacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await query.answer()
    positivo = query.data == "rep_pos"
    puntos   = 1 if positivo else -1

    match_id  = context.user_data.get("match_id_activo","")
    otro_id   = context.user_data.get("otro_id_reg","")
    otro_hoja = context.user_data.get("otro_hoja","Donaciones")
    hdrs_op   = HDRS_DON if otro_hoja == "Donaciones" else HDRS_NEC

    if otro_id:
        actualizar_reputacion(otro_hoja, hdrs_op, otro_id, puntos)
        # También actualizar reputación propia positivamente si fue buena
        if positivo:
            mi_hoja  = "Necesidades" if otro_hoja == "Donaciones" else "Donaciones"
            mis_hdrs = HDRS_DON if mi_hoja == "Donaciones" else HDRS_NEC
            mi_id_cal = context.user_data.get("match_item_id","")
            if mi_id_cal:
                actualizar_reputacion(mi_hoja, mis_hdrs, mi_id_cal, 1)

    if match_id:
        cerrar_match(match_id, "Entregado" if positivo else "Con problemas")
        # Cancelar el job de vencimiento si existe
        try:
            scheduler.remove_job(match_id)
        except:
            pass

    await query.edit_message_text(
        f"{'👍 ¡Gracias!' if positivo else '👎 Lamentamos que no salió bien.'}\n\n"
        f"{'Tu calificación ayuda a construir una comunidad confiable.' if positivo else 'Tu reporte ayuda a mejorar el sistema.'}\n\n"
        "🇻🇪 _Venezuela se ayuda sola._",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

# ── /liberar ───────────────────────────────────────────────────────────────────
async def liberar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Libera un ítem conectado si el match no prosperó."""
    uid = str(update.effective_user.id)
    liberados = 0
    for hoja, hdrs in [("Donaciones", HDRS_DON), ("Necesidades", HDRS_NEC)]:
        ws = get_ws(hoja, hdrs)
        if ws:
            try:
                rows = ws.get_all_values()
                hdrs_row = rows[0]
                for i, row in enumerate(rows[1:], start=2):
                    if row[hdrs_row.index("USER_ID")] == uid and row[hdrs_row.index("ESTADO")] == "Conectado":
                        ws.update_cell(i, hdrs_row.index("ESTADO")+1, "Disponible")
                        liberados += 1
            except:
                pass
    if liberados:
        await update.message.reply_text(
            f"✅ {liberados} publicación{'es' if liberados>1 else ''} liberada{'s' if liberados>1 else ''} — vuelven a estar disponibles.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("No tenés publicaciones conectadas para liberar.")

async def cancelar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelado. /start para volver al menú.")
    return ConversationHandler.END

async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🇻🇪 *EpaleBot — Comandos*\n\n"
        "/start — Menú principal\n"
        "/calificar — Calificar una entrega completada\n"
        "/liberar — Liberar un match que no prosperó\n"
        "/ayuda — Esta ayuda\n\n"
        "_La ayuda es más efectiva cuando está organizada._",
        parse_mode="Markdown"
    )

# ── MAIN ────────────────────────────────────────────────────────────────────────
class HealthHandler(BaseHTTPRequestHandler):
    def _responder(self, con_cuerpo=True):
        cuerpo = b"OK"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Connection", "close")
        self.end_headers()
        if con_cuerpo:
            self.wfile.write(cuerpo)

    def do_GET(self):
        self._responder(con_cuerpo=True)

    def do_HEAD(self):
        self._responder(con_cuerpo=False)

    def log_message(self, format, *args):
        pass  # Silenciar logs del servidor HTTP

def iniciar_servidor_http():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

def main():
    logging.basicConfig(
        format="%(asctime)s — %(levelname)s — %(message)s",
        level=logging.INFO
    )
    # Iniciar servidor HTTP en thread separado para mantener Render activo
    t = threading.Thread(target=iniciar_servidor_http, daemon=True)
    t.start()

    app = Application.builder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(menu, pattern="^(donar|necesitar|mis_pub|info)$")
        ],
        per_message=False,
        states={
            TIPO:         [CallbackQueryHandler(menu, pattern="^(donar|necesitar|mis_pub|info)$")],
            ESTADO_VE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_estado_ve)],
            ZONA:         [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_zona)],
            DESCRIPCION:  [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_descripcion)],
            FOTO_STEP:    [
                MessageHandler(filters.PHOTO, recibir_foto),
                CallbackQueryHandler(omitir_foto, pattern="^omitir_foto$"),
            ],
            CONFIRMAR:    [
                CallbackQueryHandler(confirmar,    pattern="^(confirmar|cambiar_desc|cambiar_ubic|cancelar|sin_match)$"),
                CallbackQueryHandler(elegir_match, pattern="^elegir_"),
            ],
        },
        fallbacks=[CommandHandler("cancelar", cancelar_cmd)],
        allow_reentry=True
    )

    cal_conv = ConversationHandler(
        entry_points=[CommandHandler("calificar", calificar)],
        per_message=False,
        states={
            CALIFICAR_STEP: [CallbackQueryHandler(recibir_calificacion, pattern="^(rep_pos|rep_neg)$")]
        },
        fallbacks=[CommandHandler("cancelar", cancelar_cmd)]
    )

    app.add_handler(conv)
    app.add_handler(cal_conv)
    app.add_handler(CommandHandler("liberar", liberar))
    app.add_handler(CommandHandler("ayuda",   ayuda))
    app.add_handler(CommandHandler("help",    ayuda))

    async def post_init(application):
        scheduler.start()

    app.post_init = post_init

    print("="*50)
    print("  EpaleBot v2 activo — @Angel1000_bot")
    print("  Conectando ayuda en Venezuela 🇻🇪")
    print("="*50)

    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
