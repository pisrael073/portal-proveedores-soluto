# ═══════════════════════════════════════════════════════════════════════════════
#  PORTAL DE PROVEEDORES - SOLUTO
#  Versión: 2.0 (Segura + Estética Mejorada)
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
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Syne:wght@700;800&family=JetBrains+Mono:wght@400;600&display=swap');

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
    background: linear-gradient(135deg, #0A0F1E 0%, #0F1729 50%, #1A1F35 100%);
    color: #E2E8F0;
    letter-spacing: 0.5px;
}

header, footer, #MainMenu { visibility: hidden; }

.block-container {
    padding: 1.5rem 2rem !important;
    max-width: 1400px !important;
}

/* TOP BAR CON GLASSMORPHISM */
.top-bar {
    background: rgba(15, 23, 41, 0.6);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(30, 58, 138, 0.3);
    border-radius: 16px;
    padding: 18px 28px;
    margin-bottom: 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    animation: slideDown 0.5s ease-out;
}

@keyframes slideDown {
    from { opacity: 0; transform: translateY(-20px); }
    to { opacity: 1; transform: translateY(0); }
}

.top-bar-title {
    font-family: 'Syne', sans-serif;
    font-size: 1.4rem;
    font-weight: 800;
    color: #F8FAFC;
    display: flex;
    align-items: center;
    gap: 12px;
    letter-spacing: 1px;
}

.top-bar-user {
    font-size: 0.8rem;
    color: #93C5FD;
    font-weight: 600;
    text-align: right;
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.top-bar-user-role {
    font-size: 0.7rem;
    color: #60A5FA;
    opacity: 0.8;
}

/* KPI CARDS CON HOVER */
.kpi-card {
    background: linear-gradient(135deg, rgba(15, 23, 41, 0.8) 0%, rgba(26, 37, 64, 0.8) 100%);
    border: 1px solid rgba(59, 130, 246, 0.2);
    border-radius: 14px;
    padding: 24px 20px;
    text-align: center;
    position: relative;
    overflow: hidden;
    margin-bottom: 12px;
    backdrop-filter: blur(5px);
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
}

.kpi-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent);
    transition: left 0.5s ease;
}

.kpi-card:hover {
    border-color: rgba(59, 130, 246, 0.5);
    box-shadow: 0 12px 35px rgba(59, 130, 246, 0.15);
    transform: translateY(-4px);
}

.kpi-card:hover::before {
    left: 100%;
}

.kpi-val {
    font-family: 'JetBrains Mono', monospace;
    font-size: 2.2rem;
    font-weight: 800;
    background: linear-gradient(135deg, #3B82F6, #60A5FA);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1;
    margin-bottom: 8px;
    letter-spacing: -1px;
}

.kpi-lbl {
    font-size: 0.7rem;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: 2px;
    font-weight: 700;
    word-spacing: 2px;
}

/* BADGES */
.admin-badge {
    background: linear-gradient(135deg, #7C3AED, #A855F7);
    border: 1px solid rgba(168, 85, 247, 0.3);
    border-radius: 8px;
    padding: 4px 12px;
    font-size: 0.65rem;
    font-weight: 800;
    color: #F5F3FF;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    display: inline-block;
    margin-left: 8px;
    box-shadow: 0 4px 12px rgba(124, 58, 237, 0.3);
    animation: pulse 2s infinite;
}

.proveedor-badge {
    background: linear-gradient(135deg, #F59E0B, #FBBF24);
    border: 1px solid rgba(245, 158, 11, 0.3);
    border-radius: 8px;
    padding: 4px 12px;
    font-size: 0.65rem;
    font-weight: 800;
    color: #78350F;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    display: inline-block;
    margin-left: 8px;
    box-shadow: 0 4px 12px rgba(245, 158, 11, 0.2);
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.8; }
}

/* SECTION TITLES */
.section-title {
    font-family: 'Syne', sans-serif;
    font-size: 1.05rem;
    font-weight: 800;
    color: #CBD5E1;
    margin: 28px 0 14px;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    position: relative;
    padding-bottom: 10px;
}

.section-title::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    width: 60px;
    height: 3px;
    background: linear-gradient(90deg, #3B82F6, transparent);
    border-radius: 2px;
}

/* BOTONES */
.stButton > button {
    background: linear-gradient(135deg, #1E40AF, #3B82F6) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    padding: 12px 24px !important;
    font-size: 0.95rem !important;
    letter-spacing: 0.5px !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3) !important;
    text-transform: uppercase;
}

.stButton > button:hover {
    background: linear-gradient(135deg, #1E3A8A, #2563EB) !important;
    box-shadow: 0 8px 25px rgba(59, 130, 246, 0.5) !important;
    transform: translateY(-2px) !important;
}

/* TABS */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background: rgba(15, 23, 41, 0.4);
    padding: 8px;
    border-radius: 12px;
    border: 1px solid rgba(30, 58, 138, 0.2);
}

.stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 8px;
    color: #94A3B8;
    font-weight: 600;
    padding: 10px 20px;
    transition: all 0.3s ease;
}

.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: linear-gradient(135deg, #1E40AF, #3B82F6);
    color: #FFFFFF;
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

/* DATAFRAME */
.stDataFrame {
    border-radius: 12px !important;
    overflow: hidden !important;
}

.stDataFrame tbody tr {
    border-bottom: 1px solid rgba(30, 58, 138, 0.2) !important;
    transition: background-color 0.2s ease !important;
}

.stDataFrame tbody tr:hover {
    background-color: rgba(59, 130, 246, 0.1) !important;
}

/* ALERTS */
.stAlert {
    border-radius: 12px !important;
    border-left: 4px solid !important;
}

.stSuccess {
    background-color: rgba(16, 185, 129, 0.1) !important;
    border-left-color: #10B981 !important;
}

.stWarning {
    background-color: rgba(245, 158, 11, 0.1) !important;
    border-left-color: #F59E0B !important;
}

.stError {
    background-color: rgba(239, 68, 68, 0.1) !important;
    border-left-color: #EF4444 !important;
}

.stInfo {
    background-color: rgba(59, 130, 246, 0.1) !important;
    border-left-color: #3B82F6 !important;
}

/* INPUTS */
.stSelectbox, .stTextInput {
    border-radius: 10px !important;
}

.stSelectbox [data-baseweb="select"] {
    background: rgba(26, 37, 64, 0.6) !important;
    border: 1px solid rgba(30, 58, 138, 0.3) !important;
}

/* RANKING CARD */
.ranking-card {
    background: linear-gradient(145deg, #111827, #1A2540);
    border-left: 5px solid;
    border-radius: 8px;
    padding: 15px 20px;
    margin-bottom: 10px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    transition: all 0.3s ease;
}

.ranking-card:hover {
    transform: translateX(4px);
    box-shadow: 0 6px 12px rgba(0, 0, 0, 0.4);
}

/* RESPONSIVE */
@media (max-width: 768px) {
    .top-bar {
        flex-direction: column;
        gap: 12px;
        text-align: center;
    }
    
    .kpi-val { font-size: 1.6rem; }
    .section-title { font-size: 0.9rem; }
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
            try:
                pin_correcto = str(int(float(u['_pin'])))
            except Exception:
                pin_correcto = str(u['_pin'])

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

def kpi_card(col, valor, label, sub="", prefix="$", suffix=""):
    """Renderiza una tarjeta KPI"""
    val_fmt = (f"{prefix}{valor:,.0f}{suffix}" if isinstance(valor, (int, float)) else str(valor))
    col.markdown(
        f"<div class='kpi-card'>"
        f"<div class='kpi-val'>{val_fmt}</div>"
        f"<div class='kpi-lbl'>{label}</div>"
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
        f"<div><span class='top-bar-title'>🏢 Portal Proveedores</span>{admin_badge}</div>"
        f"<div>"
        f"<div class='top-bar-user'>👤 {user_nombre}</div>"
        f"<div class='top-bar-user-role'>🎭 {user_rol}</div>"
        f"</div>"
        f"</div>", unsafe_allow_html=True)

    prov_sel = "TODOS"
    
    with st.sidebar:
        st.markdown(f"**👤 {user_nombre}**")
        st.markdown(f"**🎭 Rol:** {user_rol}")
        st.markdown(f"**📍 Zona:** {user_zona or '—'}")
        
        if is_proveedor_user: 
            st.info("📊 Vista filtrada por tus productos")
        elif is_super_admin or is_admin: 
            st.success("🔑 Acceso completo")
            st.markdown("---")
            lista_prov = ["TODOS"] + sorted([str(p) for p in df_v_all['Proveedor'].unique() if str(p).strip() != '' and str(p).upper() != 'NAN'])
            prov_sel = st.selectbox("🔎 Auditar Proveedor:", lista_prov)
        
        if st.button("🚪 Cerrar Sesión"):
            st.session_state.clear()
            st.rerun()

    # LÓGICA DE FILTRADO
    if is_proveedor_user:
        df_final = filtrar_datos_proveedor(df_v_all, usuario_row)
        df_inv_final = filtrar_datos_proveedor(df_i_all, usuario_row) if not df_i_all.empty else df_i_all
        filtro_info = f"📊 Vista filtrada para {user_rol}"
    else:
        if prov_sel != "TODOS":
            df_final = df_v_all[df_v_all['Proveedor'] == prov_sel].copy()
            if not df_i_all.empty and 'Proveedor' in df_i_all.columns:
                df_inv_final = df_i_all[df_i_all['Proveedor'] == prov_sel].copy()
            else:
                df_inv_final = df_i_all.copy()
            filtro_info = f"📊 Modo Auditoría: Proveedor {prov_sel}"
        else:
            df_final = df_v_all.copy()
            df_inv_final = df_i_all.copy()
            filtro_info = "📊 Vista Global de Administrador"

    if df_final.empty:
        st.warning("⚠️ No se encontraron datos para este usuario o zona.")
        return

    fecha_dt = pd.to_datetime(df_final['Fecha'])
    df_final['Mes_N'] = fecha_dt.dt.strftime('%B %Y')
    meses = sorted(df_final['Mes_N'].unique().tolist(), reverse=True)
    
    col_mes, col_info = st.columns([1, 2])
    with col_mes:
        if meses: m_sel = st.selectbox("📅 Período:", meses)
        else:
            st.warning("⚠️ Sin datos disponibles")
            return
    with col_info: st.info(filtro_info)

    df_mes = df_final[df_final['Mes_N'] == m_sel].copy()
    if df_mes.empty:
        st.warning(f"⚠️ Sin datos para {m_sel}")
        return

    metricas = calcular_metricas_proveedor(df_mes, m_sel, usuario_row)

    st.markdown(f"<div class='section-title'>📊 {m_sel} — Análisis Integral</div>", unsafe_allow_html=True)
    k1, k2, k3, k4 = st.columns(4)
    kpi_card(k1, metricas['total_ventas'], "Ventas Totales")
    kpi_card(k2, metricas['total_facturas'], "Facturas Emitidas", prefix="")
    kpi_card(k3, metricas['clientes_unicos'], "Cobertura de Clientes", prefix="")
    kpi_card(k4, metricas['vendedores_activos'], "Fuerza de Ventas", prefix="")

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
                    medalla = "🥇"
                    color_borde = "#F59E0B"
                elif index == 1:
                    medalla = "🥈"
                    color_borde = "#94A3B8"
                elif index == 2:
                    medalla = "🥉"
                    color_borde = "#B45309"
                else:
                    medalla = f"#{index + 1}"
                    color_borde = "#1E3A8A"
                
                nombre_limpio = vendedor.split(' - ')[1] if ' - ' in vendedor else vendedor
                
                st.markdown(f"""
                <div style="
                    background: linear-gradient(145deg, #111827, #1A2540);
                    border-left: 5px solid {color_borde};
                    border-radius: 8px;
                    padding: 15px 20px;
                    margin-bottom: 10px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
                ">
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <span style="font-size: 1.5rem; font-weight: bold; width: 30px; text-align: center; color: {color_borde};">{medalla}</span>
                        <span style="font-size: 1.1rem; font-weight: 600; color: #E2E8F0; text-transform: uppercase;">{nombre_limpio}</span>
                    </div>
                    <div style="font-size: 1.3rem; font-weight: 800; color: #3B82F6;">
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
