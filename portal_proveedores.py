# ═══════════════════════════════════════════════════════════════════════════════
#  PORTAL DE PROVEEDORES - SOLUTO
#  Versión: 3.0 (Corporativo + Filtros Admin)
# ═══════════════════════════════════════════════════════════════════════════════

import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from datetime import datetime
import calendar
import re
import unicodedata
import hashlib
import html as _html
import logging
from functools import lru_cache

# ══════════════════════════════════════════════════════════════════
#  LOGGING Y AUDITORÍA
# ════���═════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('portal_auditoria.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════
#  ESTILOS CSS MEJORADOS (GLASSMORPHISM + ANIMATIONS)
# ══════════════════════════════════════════════════════════════════

CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;700&display=swap');

* { margin: 0; padding: 0; box-sizing: border-box; }

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background: #111111 !important;
    color: #E8EDF2;
}

header, footer, #MainMenu { visibility: hidden; }

.block-container {
    padding: 1rem 1.8rem !important;
    max-width: 1440px !important;
    background: #111111 !important;
}

/* ── SIDEBAR ─────────────────────────────── */
[data-testid="stSidebar"] {
    background: #161616 !important;
    border-right: 1px solid #2A2A2A !important;
}
[data-testid="stSidebar"] * { color: #C8D4DF !important; }
[data-testid="stSidebar"] hr { border-color: #2A2A2A !important; }
[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] {
    background: #1E1E1E !important;
    border: 1px solid #333 !important;
}

/* ── TOP BAR ─────────────────────────────── */
.top-bar {
    background: #1A1A1A;
    border: 1px solid #2C2C2C;
    border-left: 4px solid #00BCD4;
    border-radius: 10px;
    padding: 14px 24px;
    margin-bottom: 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.top-bar-title {
    font-size: 1.25rem;
    font-weight: 800;
    color: #FFFFFF;
    letter-spacing: 0.3px;
}

.top-bar-accent { color: #00BCD4; }

.top-bar-user {
    font-size: 0.8rem;
    color: #A0B4C8;
    font-weight: 600;
    text-align: right;
    line-height: 1.6;
}

.top-bar-user-role { font-size: 0.7rem; color: #607080; }

/* ── KPI CARDS — colored solid (igual que monitor-pdv) ─── */
.kpi-card {
    border-radius: 12px;
    padding: 26px 20px 22px;
    text-align: center;
    margin-bottom: 10px;
    position: relative;
    overflow: hidden;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    box-shadow: 0 4px 18px rgba(0,0,0,0.45);
}

.kpi-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 28px rgba(0,0,0,0.55);
}

.kpi-val {
    font-family: 'JetBrains Mono', monospace;
    font-size: 2.6rem;
    font-weight: 700;
    color: #FFFFFF;
    line-height: 1;
    margin-bottom: 10px;
    letter-spacing: -1px;
}

.kpi-lbl {
    font-size: 0.66rem;
    color: rgba(255,255,255,0.75);
    text-transform: uppercase;
    letter-spacing: 1.8px;
    font-weight: 700;
}

.kpi-sub {
    font-size: 0.7rem;
    color: rgba(255,255,255,0.55);
    margin-top: 5px;
}

/* ── BADGES ──────────────────────────────── */
.admin-badge {
    background: #1565C0;
    border-radius: 5px;
    padding: 3px 10px;
    font-size: 0.6rem;
    font-weight: 800;
    color: #E3F2FD;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    display: inline-block;
    margin-left: 10px;
}

.proveedor-badge {
    background: #E65100;
    border-radius: 5px;
    padding: 3px 10px;
    font-size: 0.6rem;
    font-weight: 800;
    color: #FFF3E0;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    display: inline-block;
    margin-left: 10px;
}

/* ── SECTION TITLES — estilo monitor-pdv ─── */
.section-title {
    font-size: 0.78rem;
    font-weight: 800;
    color: #00BCD4;
    margin: 24px 0 12px;
    text-transform: uppercase;
    letter-spacing: 2.5px;
    display: flex;
    align-items: center;
    gap: 6px;
}

/* ── FILTRO LABEL SIDEBAR ────────────────── */
.filter-label {
    font-size: 0.68rem;
    color: #00BCD4;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    font-weight: 700;
    margin-bottom: 3px;
}

/* ── BOTONES ─────────────────────────────── */
.stButton > button {
    background: #1565C0 !important;
    color: #E3F2FD !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    padding: 10px 20px !important;
    font-size: 0.88rem !important;
    letter-spacing: 0.5px !important;
    transition: background 0.2s ease !important;
    text-transform: uppercase !important;
}

.stButton > button:hover {
    background: #0D47A1 !important;
}

/* ── TABS ─────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: #1A1A1A;
    padding: 6px;
    border-radius: 10px;
    border: 1px solid #2A2A2A;
}

.stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 7px;
    color: #607080;
    font-weight: 600;
    font-size: 0.84rem;
    padding: 8px 16px;
    transition: all 0.2s ease;
}

.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: #1E3A5F;
    color: #90CAF9;
    border-bottom: 2px solid #00BCD4;
}

/* ── DATAFRAME ───────────────────────────── */
.stDataFrame { border-radius: 10px !important; overflow: hidden !important; }
.stDataFrame tbody tr { border-bottom: 1px solid #222 !important; }
.stDataFrame tbody tr:hover { background-color: rgba(0,188,212,0.06) !important; }

/* ── ALERTS ──────────────────────────────── */
.stAlert { border-radius: 8px !important; border-left: 3px solid !important; }

/* ── INPUTS ──────────────────────────────── */
.stSelectbox [data-baseweb="select"] {
    background: #1A1A1A !important;
    border: 1px solid #2E2E2E !important;
    border-radius: 8px !important;
    color: #E8EDF2 !important;
}

.stTextInput input {
    background: #1A1A1A !important;
    border: 1px solid #2E2E2E !important;
    border-radius: 8px !important;
    color: #E8EDF2 !important;
}

/* ── RANKING CARDS ───────────────────────── */
.ranking-card {
    background: #1A1A1A;
    border-left: 4px solid;
    border-radius: 8px;
    padding: 13px 18px;
    margin-bottom: 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    transition: transform 0.2s ease;
}

.ranking-card:hover { transform: translateX(3px); }

/* ── RESPONSIVE ──────────────────────────── */
@media (max-width: 768px) {
    .top-bar { flex-direction: column; gap: 8px; text-align: center; }
    .kpi-val  { font-size: 1.8rem; }
}
"""

st.markdown(f"<style>{CUSTOM_CSS}</style>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════���══
#  CONFIG TELEGRAM (SEGURA)
# ══════════════════════════════════════════════════════════════════

def get_telegram_config():
    """Obtiene config de Telegram SOLO desde secrets"""
    try:
        bot_token = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
        if not bot_token or bot_token.startswith('8249353159'):
            logger.error("❌ Token de Telegram inválido o hardcodeado")
            return None
        return {
            'BOT_TOKEN': bot_token,
            'CHAT_IDS': {
                'gerencia': st.secrets.get("TELEGRAM_GERENCIA", ""),
                'administracion': st.secrets.get("TELEGRAM_ADMIN", ""),
                'vendedores': st.secrets.get("TELEGRAM_VENDEDORES", "")
            }
        }
    except KeyError:
        logger.warning("⚠️ Secrets de Telegram no configurados")
        return None

# ══════════════════════════════════════════════════════════════════
#  HELPERS & FORMATO
# ════════════════════════════════════════════════════════════════���═

def norm_txt(v):
    """Normaliza texto: mayúsculas, sin acentos, sin espacios extras"""
    s = str(v).strip().upper()
    s = ''.join(c for c in unicodedata.normalize('NFD', s)
                if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', s)

def limpiar_columnas(df):
    """Limpia nombres de columnas"""
    df.columns = [
        str(c).strip().replace('\ufeff', '').replace('\xa0', '').replace('\u200b', '')
        for c in df.columns
    ]
    return df

def anonimizar_cliente(nombre, user_codigo):
    """Anonimiza cliente con hash único (evita colisiones)"""
    if pd.isna(nombre) or str(nombre).strip() == "":
        return "DESC"
    
    nombre_norm = str(nombre).strip().upper()
    seed = f"{nombre_norm}_{user_codigo}".encode()
    hash_val = hashlib.md5(seed).hexdigest()[:6].upper()
    
    return f"CLI_{hash_val}"

def anonimizar_ciudad(ciudad):
    """Convierte ciudades a códigos de zona"""
    if pd.isna(ciudad) or str(ciudad).strip() == "":
        return "ZN-00"
    
    ciudad_norm = str(ciudad).strip().upper()
    
    mapa_zonas = {
        'AMBATO': 'ZN-A1', 'LATACUNGA': 'ZN-B1', 'RIOBAMBA': 'ZN-C1',
        'QUITO': 'ZN-Q1', 'GUAYAQUIL': 'ZN-G1', 'CUENCA': 'ZN-S1',
        'BAÑOS': 'ZN-A2', 'PELILEO': 'ZN-A3', 'PILLARO': 'ZN-A4',
        'SALCEDO': 'ZN-B2', 'PUJILI': 'ZN-B3'
    }
    
    for key, secreto in mapa_zonas.items():
        if key in ciudad_norm:
            return secreto
    
    return f"ZN-X{len(ciudad_norm)}"

# ══════════════════════════════════════════════════════════════════
#  RATE LIMITER (PREVIENE FUERZA BRUTA)
# ══════════════════════════════════════════════════════════════════

class RateLimiter:
    """Previene fuerza bruta en login"""
    def __init__(self):
        self.intentos = {}
    
    def check(self, identificador, max_intentos=5, ventana_segundos=300):
        ahora = datetime.now()
        if identificador not in self.intentos:
            self.intentos[identificador] = []
        
        # Limpiar intentos antiguos
        self.intentos[identificador] = [
            t for t in self.intentos[identificador] 
            if (ahora - t).total_seconds() < ventana_segundos
        ]
        
        if len(self.intentos[identificador]) >= max_intentos:
            return False, f"❌ Demasiados intentos. Espera {ventana_segundos} segundos."
        
        self.intentos[identificador].append(ahora)
        return True, None
    
    def registrar_intento(self, identificador, exitoso):
        logger.info(f"{'✅' if exitoso else '❌'} Login - {identificador}")

rate_limiter = RateLimiter()

# ══════════════════════════════════════════════════════════════════
#  FUNCIONES DE SEGURIDAD Y PERMISOS
# ══════════════════════════════════════════════════════════════════

def es_super_admin(user_codigo, user_nombre):
    """Detecta si es super admin"""
    codigo_israel = str(user_codigo) == '1804140794'
    nombre_israel = 'ISRAEL' in str(user_nombre).upper()
    nombre_completo = 'PAREDES ALTAMIRANO ISRAEL' in str(user_nombre).upper()
    return codigo_israel or nombre_israel or nombre_completo

def tiene_permisos_admin(user_rol):
    """Verifica si tiene permisos de administrador"""
    return user_rol.lower() in ('admin', 'administrador', 'gerente', 'supervisor', 'jefe')

def es_proveedor(user_rol):
    """Verifica si es proveedor"""
    return user_rol.lower() in ('proveedor', 'marca', 'distribuidor', 'supplier')

def filtrar_datos_proveedor(df_datos, user_info):
    """Filtra datos SEGURAMENTE por proveedor/zona"""
    user_rol = user_info.get('_rol', '').lower()
    if not es_proveedor(user_rol):
        return df_datos
    
    filtro = user_info.get('_zona', '').strip()
    if not filtro:
        filtro = user_info.get('_nombre_orig', '').strip()

    mask = pd.Series([False] * len(df_datos))
    
    for col in ['Proveedor', 'Marca', 'PROVEEDOR', 'MARCA']:
        if col in df_datos.columns:
            mask = mask | df_datos[col].astype(str).str.contains(filtro, case=False, na=False)
    
    df_filtrado = df_datos[mask]
    logger.info(f"🔍 Proveedor {filtro} - {len(df_filtrado)} registros accedidos")
    return df_filtrado

def calcular_metricas_proveedor(df_ventas, mes_seleccionado, user_info):
    """Calcula métricas de proveedor"""
    if df_ventas.empty:
        return {
            'total_ventas': 0, 'total_facturas': 0, 'clientes_unicos': 0,
            'vendedores_activos': 0, 'top_productos': pd.Series(dtype=float),
            'top_vendedores': pd.Series(dtype=float), 'crecimiento': 0,
        }
    
    fecha_dt = pd.to_datetime(df_ventas['Fecha'])
    df_mes = df_ventas[fecha_dt.dt.strftime('%B %Y') == mes_seleccionado]
    
    if df_mes.empty:
        return {
            'total_ventas': 0, 'total_facturas': 0, 'clientes_unicos': 0,
            'vendedores_activos': 0, 'top_productos': pd.Series(dtype=float),
            'top_vendedores': pd.Series(dtype=float), 'crecimiento': 0,
        }
    
    total_ventas = df_mes['Total'].sum()
    total_facturas = len(df_mes)
    clientes_unicos = df_mes['Cliente'].nunique()
    vendedores_activos = df_mes[df_mes['Total'] > 0]['Vendedor'].nunique()
    top_productos = df_mes.groupby('Marca')['Total'].sum().nlargest(5)
    top_vendedores = df_mes.groupby('Vendedor')['Total'].sum().nlargest(5)
    
    try:
        fecha_actual = datetime.now()
        if fecha_actual.month == 1:
            mes_anterior = f"{calendar.month_name[12]} {fecha_actual.year - 1}"
        else:
            mes_anterior = f"{calendar.month_name[fecha_actual.month - 1]} {fecha_actual.year}"
        
        df_anterior = df_ventas[fecha_dt.dt.strftime('%B %Y') == mes_anterior]
        ventas_anterior = df_anterior['Total'].sum()
        crecimiento = ((total_ventas - ventas_anterior) / ventas_anterior) * 100 if ventas_anterior > 0 else 0
    except:
        crecimiento = 0
    
    return {
        'total_ventas': total_ventas,
        'total_facturas': total_facturas,
        'clientes_unicos': clientes_unicos,
        'vendedores_activos': vendedores_activos,
        'top_productos': top_productos,
        'top_vendedores': top_vendedores,
        'crecimiento': round(crecimiento, 1),
    }

# ══════════════════════════════════════════════════════════════════
#  CONFIG PÁGINA
# ══════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Portal Proveedores - SOLUTO",
    layout="wide",
    page_icon="🏢",
    initial_sidebar_state="expanded"
)

# ══════════════════════════════════════════════════════════════════
#  CONEXIÓN GOOGLE SHEETS
# ══════════════════════════════════════════════════════════════════

@st.cache_resource(ttl=300)
def get_gc():
    """Conecta a Google Sheets de forma segura"""
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    try:
        creds_dict = dict(st.secrets["google"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        logger.info("✅ Conectado a Google Sheets")
    except Exception as e:
        logger.error(f"❌ Error de conexión: {e}")
        st.error("❌ Error de conexión con Google Sheets")
        st.stop()
    return gspread.authorize(creds)

@st.cache_data(ttl=300)
def cargar_usuarios():
    """Carga usuarios desde Google Sheets"""
    gc = get_gc()
    sh = gc.open("soluto")
    df = pd.DataFrame()

    for hoja in ["Usuario_Roles", "Usuarios", "USUARIOS"]:
        try:
            ws = sh.worksheet(hoja)
            df = pd.DataFrame(ws.get_all_records())
            df = limpiar_columnas(df)
            break
        except Exception:
            continue

    if df.empty:
        logger.warning("⚠️ No se pudo cargar usuarios")
        return df

    col_nombre = next((c for c in df.columns if 'nombre' in c.lower()), None)
    col_pin = next((c for c in df.columns if 'pin' in c.lower()), None)
    col_rol = next((c for c in df.columns if 'rol' in c.lower()), None)
    col_zona = next((c for c in df.columns if 'zona' in c.lower()), None)
    col_codigo = next((c for c in df.columns if 'codigo' in c.lower()), None)

    df['_nombre_orig'] = df[col_nombre].astype(str).str.strip() if col_nombre else ''
    df['_nombre_norm'] = df['_nombre_orig'].apply(norm_txt)
    df['_pin'] = df[col_pin].astype(str).str.strip() if col_pin else ''
    df['_rol'] = df[col_rol].astype(str).str.strip() if col_rol else 'Vendedor'
    df['_zona'] = df[col_zona].astype(str).str.strip() if col_zona else ''
    df['_codigo_pdv'] = (df[col_codigo].astype(str).str.strip().str.upper() if col_codigo else '')
    df['_codigo_pdv'] = df['_codigo_pdv'].replace({'NAN': '', 'NONE': ''})
    
    logger.info(f"✅ Cargados {len(df)} usuarios")
    return df

@st.cache_data(ttl=300)
def cargar_ventas_presupuesto():
    """Carga ventas, presupuesto e inventario"""
    gc = get_gc()
    sh = gc.open("soluto")

    # CARGAR VENTAS
    ws_v = sh.worksheet("VENTAS")
    df_raw = pd.DataFrame(ws_v.get_all_records())
    df_raw = limpiar_columnas(df_raw)

    def find_col(df, keyword):
        return next((c for c in df.columns if keyword in norm_txt(c)), None)

    col_fecha = find_col(df_raw, 'FECHA')
    col_total = find_col(df_raw, 'TOTAL')
    col_vend = find_col(df_raw, 'VENDEDOR')
    col_cli = find_col(df_raw, 'CLIENTE')
    col_marca = find_col(df_raw, 'MARCA')
    col_prov = find_col(df_raw, 'PROVEEDOR')
    col_desc = find_col(df_raw, 'DESCRIPCION')
    col_factura = find_col(df_raw, 'FACTURA')
    col_ciudad = find_col(df_raw, 'CIUDAD')
    col_ruta = find_col(df_raw, 'RUTA')
    col_grupo = find_col(df_raw, 'GRUPO')
    col_subgrupo = find_col(df_raw, 'SUBGRUPO')
    col_codigo = find_col(df_raw, 'CODIGO')
    col_cantidad = find_col(df_raw, 'CANTIDAD')

    if col_fecha is None or col_total is None:
        raise ValueError("❌ No se encontraron columnas FECHA o TOTAL en VENTAS")

    fecha_series = pd.to_datetime(df_raw[col_fecha], errors='coerce', dayfirst=True)
    total_series = pd.to_numeric(df_raw[col_total].astype(str).str.replace(r'[$,\s]', '', regex=True), errors='coerce').fillna(0)

    mask_ok = fecha_series.notna()
    df_v = df_raw[mask_ok].copy()
    
    df_v['Fecha'] = fecha_series[mask_ok].dt.date
    df_v['Total'] = total_series[mask_ok].values
    df_v['Vendedor'] = df_v[col_vend].astype(str) if col_vend else ''
    df_v['Cliente'] = df_v[col_cli].astype(str) if col_cli else ''
    df_v['Marca'] = df_v[col_marca].astype(str) if col_marca else ''
    df_v['Proveedor'] = df_v[col_prov].astype(str) if col_prov else ''
    df_v['Descripcion'] = df_v[col_desc].astype(str) if col_desc else 'Sin Detalle'
    df_v['Factura'] = df_v[col_factura].astype(str) if col_factura else ''
    df_v['Ciudad'] = df_v[col_ciudad].astype(str) if col_ciudad else ''
    df_v['Ruta'] = df_v[col_ruta].astype(str) if col_ruta else ''
    df_v['Grupo'] = df_v[col_grupo].astype(str) if col_grupo else ''
    df_v['SubGrupo'] = df_v[col_subgrupo].astype(str) if col_subgrupo else ''
    df_v['Codigo_Prod'] = df_v[col_codigo].astype(str) if col_codigo else ''
    
    if col_cantidad:
        df_v['Cantidad'] = pd.to_numeric(df_raw[col_cantidad], errors='coerce').fillna(0)
    else:
        df_v['Cantidad'] = 0

    # CARGAR PRESUPUESTO
    try:
        ws_p = sh.worksheet("PRESUPUESTO")
        df_p = pd.DataFrame(ws_p.get_all_records())
        df_p = limpiar_columnas(df_p)
    except:
        df_p = pd.DataFrame()

    # CARGAR INVENTARIO
    try:
        ws_i = sh.worksheet("INVENTARIO")
        df_i = pd.DataFrame(ws_i.get_all_records())
        df_i = limpiar_columnas(df_i)
    except:
        df_i = pd.DataFrame()

    logger.info(f"✅ Cargadas {len(df_v)} transacciones de ventas")
    return df_v, df_p, df_i

# ══════════════════════════════════════════════════════════════════
#  PANTALLA LOGIN
# ══════════════════════════════════════════════════════════════════

def pantalla_login():
    """Pantalla de login con validación segura"""
    df_users = cargar_usuarios()
    if df_users.empty:
        st.error("❌ No se pudo cargar la hoja de Usuarios.")
        return

    _, col_c, _ = st.columns([1, 1.1, 1])
    with col_c:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("### 🏢 Portal Proveedores SOLUTO")
        st.markdown("##### Acceso Exclusivo para Socios Comerciales")

        roles = sorted(df_users['_rol'].unique().tolist())
        rol_sel = st.selectbox("🎭 Selecciona tu Rol:", ["— Selecciona —"] + roles)

        if rol_sel != "— Selecciona —":
            nombres = sorted(df_users[df_users['_rol'] == rol_sel]['_nombre_orig'].tolist())
            nombre_sel = st.selectbox("👤 Selecciona tu nombre:", ["— Selecciona —"] + nombres)
        else:
            nombre_sel = "— Selecciona —"
            st.selectbox("👤 Selecciona tu nombre:", ["— Selecciona un rol primero —"], disabled=True)

        pin_inp = st.text_input("🔐 Ingresa tu PIN:", type="password", max_chars=6)

        if st.button("→ INGRESAR", use_container_width=True):
            if nombre_sel == "— Selecciona —" or rol_sel == "— Selecciona —":
                st.error("⚠️ Completa los datos requeridos.")
                return

            # RATE LIMITING
            identificador = f"{nombre_sel}_{rol_sel}"
            permitido, msg_error = rate_limiter.check(identificador)
            if not permitido:
                st.error(msg_error)
                logger.warning(f"❌ Rate limit - {identificador}")
                return

            fila = df_users[(df_users['_nombre_orig'] == nombre_sel) & (df_users['_rol'] == rol_sel)]
            if fila.empty:
                st.error("❌ Usuario no encontrado.")
                rate_limiter.registrar_intento(identificador, False)
                return

            u = fila.iloc[0]
            pin_correcto = str(u['_pin']).strip()

            if pin_inp.strip() != pin_correcto:
                st.error("🔒 PIN incorrecto.")
                rate_limiter.registrar_intento(identificador, False)
                return

            # LOGIN EXITOSO
            st.session_state.update({
                'logged_in': True,
                'user_nombre': nombre_sel,
                'user_rol': str(u['_rol']),
                'user_zona': str(u['_zona']),
                'user_codigo': str(u['_codigo_pdv']),
                'user_row': u.to_dict(),
                'login_time': datetime.now(),
            })
            
            rate_limiter.registrar_intento(identificador, True)
            logger.info(f"✅ Login exitoso - {nombre_sel} ({u['_rol']})")
            st.rerun()

# ══════════════════════════════════════════════════════════════════
#  FUNCIONES DE UI
# ══════════════════════════════════════════════════════════════════

def kpi_card(col, valor, label, sub="", prefix="$", suffix="", color="#2E7D32"):
    """Renderiza tarjeta KPI con fondo de color sólido (estilo monitor-pdv)"""
    val_fmt = (f"{prefix}{valor:,.0f}{suffix}" if isinstance(valor, (int, float)) else str(valor))
    sub_html = f"<div class='kpi-sub'>{sub}</div>" if sub else ""
    col.markdown(
        f"<div class='kpi-card' style='background:{color};'>"
        f"<div class='kpi-val'>{val_fmt}</div>"
        f"<div class='kpi-lbl'>{label}</div>"
        f"{sub_html}"
        f"</div>",
        unsafe_allow_html=True
    )

# ══════════════════════════════════════════════════════════════════
#  DASHBOARD PRINCIPAL
# ══���═══════════════════════════════════════════════════════════════

def dashboard_proveedores(df_v_all, df_p, df_i_all, usuario_row):
    """Dashboard principal de proveedores"""
    user_nombre = st.session_state['user_nombre']
    user_rol = st.session_state['user_rol']
    user_zona = st.session_state['user_zona']
    user_codigo = st.session_state['user_codigo']
    
    is_super_admin = es_super_admin(user_codigo, user_nombre)
    is_admin = tiene_permisos_admin(user_rol)
    is_proveedor_user = es_proveedor(user_rol)

    admin_badge = "<span class='admin-badge'>SUPER ADMIN</span>" if is_super_admin else \
                  "<span class='admin-badge'>Admin</span>" if is_admin else \
                  "<span class='proveedor-badge'>Proveedor</span>" if is_proveedor_user else ""
        
    st.markdown(
        f"<div class='top-bar'>"
        f"<div><span class='top-bar-title'>🏢 Portal <span class='top-bar-accent'>Proveedores</span> · SOLUTO</span>{admin_badge}</div>"
        f"<div>"
        f"<div class='top-bar-user'>👤 {_html.escape(user_nombre)}</div>"
        f"<div class='top-bar-user-role'>🎭 {_html.escape(user_rol)}</div>"
        f"</div>"
        f"</div>", unsafe_allow_html=True)

    prov_sel  = "TODOS"
    vend_sel  = "TODOS"
    zona_sel  = "TODAS"

    # ── Sidebar: solo info de usuario + logout ────────────
    with st.sidebar:
        st.markdown(f"**👤 {_html.escape(user_nombre)}**")
        st.markdown(f"**🎭 Rol:** {_html.escape(user_rol)}")
        st.markdown(f"**📍 Zona:** {_html.escape(user_zona or '—')}")
        if is_proveedor_user:
            st.info("📊 Vista filtrada por tus productos")
        elif is_super_admin or is_admin:
            st.success("🔑 Acceso completo a todos los datos")
        st.markdown("---")
        if st.button("🚪 Cerrar Sesión"):
            st.session_state.clear()
            st.rerun()

    # ── Barra de filtros admin (área principal, siempre visible) ──
    if is_super_admin or is_admin:
        st.markdown("""
        <div style="background:#1A1A1A;border:1px solid #2A2A2A;border-left:4px solid #00BCD4;
             border-radius:10px;padding:14px 20px 6px;margin-bottom:18px;">
          <div style="font-size:0.7rem;font-weight:800;color:#00BCD4;text-transform:uppercase;
               letter-spacing:2px;margin-bottom:10px;">🔍 FILTROS DE ANÁLISIS</div>
        """, unsafe_allow_html=True)

        lista_prov = ["TODOS"] + sorted([
            str(p) for p in df_v_all['Proveedor'].unique()
            if str(p).strip() not in ('', 'nan', 'NAN')
        ])
        lista_vend = ["TODOS"] + sorted([
            str(v) for v in df_v_all['Vendedor'].unique()
            if str(v).strip() not in ('', 'nan', 'NAN')
        ])
        lista_zona = ["TODAS"] + sorted([
            str(z) for z in df_v_all['Ciudad'].unique()
            if str(z).strip() not in ('', 'nan', 'NAN')
        ])

        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            prov_sel = st.selectbox("🔎 Proveedor", lista_prov, key="sb_prov")
        with fc2:
            vend_sel = st.selectbox("👤 Vendedor",  lista_vend, key="sb_vend")
        with fc3:
            zona_sel = st.selectbox("📍 Zona / Ciudad", lista_zona, key="sb_zona")

        st.markdown("</div>", unsafe_allow_html=True)

    # LÓGICA DE FILTRADO
    if is_proveedor_user:
        df_final = filtrar_datos_proveedor(df_v_all, usuario_row)
        df_inv_final = filtrar_datos_proveedor(df_i_all, usuario_row) if not df_i_all.empty else df_i_all
        filtro_info = f"📊 Vista filtrada para {user_rol}"
    else:
        df_final = df_v_all.copy()
        df_inv_final = df_i_all.copy()

        # Filtro por proveedor
        if prov_sel != "TODOS":
            df_final = df_final[df_final['Proveedor'] == prov_sel].copy()
            if not df_inv_final.empty and 'Proveedor' in df_inv_final.columns:
                df_inv_final = df_inv_final[df_inv_final['Proveedor'] == prov_sel].copy()

        # Filtro por vendedor
        if vend_sel != "TODOS" and 'Vendedor' in df_final.columns:
            df_final = df_final[df_final['Vendedor'] == vend_sel].copy()

        # Filtro por zona / ciudad
        if zona_sel != "TODAS" and 'Ciudad' in df_final.columns:
            df_final = df_final[df_final['Ciudad'] == zona_sel].copy()

        # Descripción del filtro activo
        partes = []
        if prov_sel  != "TODOS":  partes.append(f"Proveedor: {prov_sel}")
        if vend_sel  != "TODOS":  partes.append(f"Vendedor: {vend_sel}")
        if zona_sel  != "TODAS":  partes.append(f"Zona: {zona_sel}")
        filtro_info = "📊 " + " · ".join(partes) if partes else "📊 Vista Global de Administrador"

    if df_final.empty:
        st.warning("⚠️ No se encontraron datos para este usuario o zona.")
        return

    fecha_dt = pd.to_datetime(df_final['Fecha'])
    df_final['Mes_N'] = fecha_dt.dt.strftime('%B %Y')
    meses = sorted(df_final['Mes_N'].unique().tolist(), reverse=True)

    if not meses:
        st.warning("⚠️ Sin datos disponibles")
        return

    # Selector de período + badge de filtro activo
    pm1, pm2 = st.columns([1, 3])
    with pm1:
        m_sel = st.selectbox("📅 Período:", meses)
    with pm2:
        if filtro_info != "📊 Vista Global de Administrador":
            st.markdown(
                f"<div style='background:#1A2A1A;border:1px solid #2E7D32;border-radius:8px;"
                f"padding:10px 16px;margin-top:4px;font-size:0.82rem;color:#81C784;font-weight:600'>"
                f"✅ Filtro activo: {_html.escape(filtro_info.replace('📊 ',''))}</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                "<div style='background:#141414;border:1px solid #2A2A2A;border-radius:8px;"
                "padding:10px 16px;margin-top:4px;font-size:0.82rem;color:#607080'>📊 Sin filtros — vista global</div>",
                unsafe_allow_html=True
            )

    df_mes = df_final[df_final['Mes_N'] == m_sel].copy()
    if df_mes.empty:
        st.warning(f"⚠️ Sin datos para {m_sel}")
        return

    metricas = calcular_metricas_proveedor(df_mes, m_sel, usuario_row)

    crecimiento = metricas.get('crecimiento', 0)
    crec_txt = f"{'▲' if crecimiento >= 0 else '▼'} {abs(crecimiento):.1f}% vs mes ant." if crecimiento != 0 else ""

    st.markdown(f"<div class='section-title'>📊 {_html.escape(m_sel)} — ANÁLISIS INTEGRAL</div>", unsafe_allow_html=True)
    k1, k2, k3, k4 = st.columns(4)
    kpi_card(k1, metricas['total_ventas'],      "Ventas Totales",        sub=crec_txt,           color="#2E7D32")
    kpi_card(k2, metricas['total_facturas'],    "Facturas Emitidas",     prefix="",              color="#1565C0")
    kpi_card(k3, metricas['clientes_unicos'],   "Clientes Alcanzados",   prefix="",              color="#00695C")
    kpi_card(k4, metricas['vendedores_activos'],"Vendedores Activos",    prefix="",              color="#E65100")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Análisis Comercial", 
        "📋 Sábana de Ventas", 
        "📦 Rendimiento de Productos", 
        "🏆 Ranking Vendedores",
        "📦 Inventario Actual"
    ])

    with tab1:
        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown("<div class='section-title'>🏷️ Penetración de Marca</div>", unsafe_allow_html=True)
            if not metricas['top_productos'].empty: 
                st.bar_chart(metricas['top_productos'])
            else: 
                st.info("Sin datos de marcas")
        with col_r:
            st.markdown("<div class='section-title'>🚀 Tendencia de Demanda</div>", unsafe_allow_html=True)
            if not df_mes.empty:
                try:
                    tendencia = df_mes.groupby(pd.to_datetime(df_mes['Fecha']).dt.date)['Total'].sum()
                    st.line_chart(tendencia.tail(15))
                except: 
                    st.info("Sin datos para tendencia")

    with tab2:
        st.markdown("<div class='section-title'>📋 Sábana de Ventas Detallada</div>", unsafe_allow_html=True)
        if not df_mes.empty:
            df_detalle = df_mes.copy()
            df_detalle['Cliente_Codificado'] = df_detalle['Cliente'].apply(lambda x: anonimizar_cliente(x, user_codigo))
            df_detalle['Ciudad_Codificada'] = df_detalle['Ciudad'].apply(anonimizar_ciudad)
            
            columnas_sabana = [
                'Fecha', 'Factura', 'Ciudad_Codificada', 'Ruta', 'Vendedor', 
                'Cliente_Codificado', 'Grupo', 'SubGrupo', 'Marca', 
                'Codigo_Prod', 'Descripcion', 'Cantidad', 'Total'
            ]
            
            columnas_finales = [col for col in columnas_sabana if col in df_detalle.columns]
            df_mostrar = df_detalle[columnas_finales].rename(columns={
                'Cliente_Codificado': 'Cód. Cliente',
                'Ciudad_Codificada': 'Cód. Zona'
            })
            
            st.dataframe(
                df_mostrar,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Total": st.column_config.NumberColumn("Total", format="$%.2f"),
                    "Cantidad": st.column_config.NumberColumn("Cantidad", format="%d")
                }
            )
        else: 
            st.info("Sin datos de ventas para este período")

    with tab3:
        st.markdown("<div class='section-title'>📦 Detalle Analítico de Productos</div>", unsafe_allow_html=True)
        if not df_mes.empty:
            resumen = df_mes.groupby(['Marca', 'Proveedor']).agg({
                'Total': ['sum', 'count'], 'Cliente': 'nunique'
            }).round(2)
            
            resumen.columns = ['Volumen Negocio', 'Transacciones', 'Alcance Clientes']
            resumen = resumen.reset_index().sort_values('Volumen Negocio', ascending=False)
            
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("🏷️ Portafolio (Marcas)", resumen['Marca'].nunique())
            with c2: st.metric("🏢 Líneas Activas", resumen['Proveedor'].nunique())
            with c3: st.metric("💰 Promedio por Línea", f"${resumen['Volumen Negocio'].mean():,.2f}")
            
            st.dataframe(resumen, use_container_width=True, hide_index=True)

    with tab4:
        st.markdown("<div class='section-title'>🏆 Top Vendedores del Mes</div>", unsafe_allow_html=True)
        st.markdown("Rendimiento de la fuerza de ventas basado en el volumen de facturación.")
        
        if not df_mes.empty:
            ranking_df = df_mes.groupby('Vendedor')['Total'].sum().reset_index()
            ranking_df = ranking_df.sort_values('Total', ascending=False).reset_index(drop=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            for index, row in ranking_df.iterrows():
                vendedor = row['Vendedor']
                total = row['Total']
                
                if index == 0:
                    medalla = "🥇"; color_borde = "#F9A825"; bg_card = "#1A1500"
                elif index == 1:
                    medalla = "🥈"; color_borde = "#90A4AE"; bg_card = "#141A1E"
                elif index == 2:
                    medalla = "🥉"; color_borde = "#A1631A"; bg_card = "#1A1208"
                else:
                    medalla = f"#{index + 1}"; color_borde = "#1565C0"; bg_card = "#141414"

                nombre_limpio = _html.escape(vendedor.split(' - ')[1] if ' - ' in vendedor else vendedor)
                max_total = ranking_df['Total'].max()
                pct = int(total / max_total * 100) if max_total > 0 else 0

                st.markdown(f"""
                <div style="background:{bg_card};border-left:4px solid {color_borde};border-radius:8px;
                    padding:13px 18px;margin-bottom:8px;display:flex;justify-content:space-between;
                    align-items:center;">
                    <div style="display:flex;align-items:center;gap:12px;flex:1">
                        <span style="font-size:1.3rem;width:26px;text-align:center;color:{color_borde};">{medalla}</span>
                        <div style="flex:1">
                            <div style="font-size:0.9rem;font-weight:700;color:#E8EDF2;text-transform:uppercase;letter-spacing:0.5px;">{nombre_limpio}</div>
                            <div style="background:#222;border-radius:3px;height:4px;margin-top:5px;width:100%">
                                <div style="background:{color_borde};width:{pct}%;height:4px;border-radius:3px;"></div>
                            </div>
                        </div>
                    </div>
                    <div style="font-size:1.1rem;font-weight:800;color:#00BCD4;font-family:'JetBrains Mono',monospace;margin-left:16px;">
                        ${total:,.2f}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Sin datos de ventas para generar el ranking.")

    with tab5:
        st.markdown("<div class='section-title'>📦 Inventario Actual</div>", unsafe_allow_html=True)
        st.markdown("Disponibilidad de stock detallado (Saldos y Cajas) para tu portafolio.")
        
        if not df_inv_final.empty:
            cols_base = [
                'Proveedor', 'Marca', 'Group', 'Sub Grupo', 'Codigo', 'Descripcion', 
                'Costo', 'Iva', 'Unid.', 'Cant.', 'Und. X Cja', 'Cant. Emb.', 'Uni. Emb.'
            ]
            
            cols_reales = [c for c in df_inv_final.columns if c in cols_base]
            
            if not cols_reales:
                cols_reales = [c for c in df_inv_final.columns if c.upper() not in ['PVP', '% RENT', 'RENTABILIDAD']]

            df_mostrar_inv = df_inv_final[cols_reales].copy()

            busqueda_inv = st.text_input("🔍 Buscar producto en inventario (Ej. COLADITA):")
            if busqueda_inv:
                mask_inv = df_mostrar_inv.astype(str).apply(lambda x: x.str.contains(busqueda_inv, case=False)).any(axis=1)
                df_mostrar_inv = df_mostrar_inv[mask_inv]

            st.dataframe(
                df_mostrar_inv,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Aún no hay datos de inventario disponibles.")

# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    if 'logged_in' not in st.session_state: 
        st.session_state['logged_in'] = False
    
    if not st.session_state['logged_in']:
        pantalla_login()
        return

    try: 
        df_v, df_p, df_i = cargar_ventas_presupuesto()
    except ValueError as e:
        st.error(str(e))
        st.stop()

    if df_v.empty:
        st.error("❌ Sin datos de ventas.")
        return

    dashboard_proveedores(df_v, df_p, df_i, st.session_state.get('user_row', {}))

if __name__ == "__main__":
    main()
