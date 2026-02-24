import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import plotly.io as pio
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import io
import zipfile
import calendar
import re
import unicodedata
import requests
from datetime import datetime

# ══════════════════════════════════════════════════════════════════
#  CONFIG TELEGRAM
# ══════════════════════════════════════════════════════════════════

# 🔧 CONFIGURACIÓN TELEGRAM - DATOS REALES
TELEGRAM_CONFIG = {
    'BOT_TOKEN': '8249353159:AAFvpNkEUdTcuIu_kpMcQbOtqyB0WbZkGTc',
    'CHAT_IDS': {
        'gerencia': '7900265168',        # Tu chat personal
        'administracion': '7900265168',  # Tu chat personal
        'vendedores': '-5180849774'      # Grupo "Reportes Automaticos" 
    }
}

# ══════════════════════════════════════════════════════════════════
#  FUNCIONES DE PROVEEDORES (NUEVAS)
# ══════════════════════════════════════════════════════════════════

def es_super_admin(user_codigo, user_nombre):
    """Verifica si el usuario es Israel (super administrador)"""
    # Criterios para Super Admin
    codigo_israel = str(user_codigo) == '1804140794'
    nombre_israel = 'ISRAEL' in str(user_nombre).upper()
    nombre_completo = 'PAREDES ALTAMIRANO ISRAEL' in str(user_nombre).upper()
    
    return codigo_israel or nombre_israel or nombre_completo


def tiene_permisos_admin(user_rol):
    """Verifica si el usuario tiene permisos básicos de admin"""
    return user_rol.lower() in ('admin', 'administrador', 'gerente', 'supervisor', 'jefe')


def es_proveedor(user_rol):
    """Verifica si el usuario es un proveedor"""
    return user_rol.lower() in ('proveedor', 'marca', 'distribuidor', 'supplier')


def filtrar_datos_proveedor(df_ventas, user_info):
    """Filtra datos según el proveedor/marca del usuario"""
    user_rol = user_info.get('_rol', '').lower()
    
    # Si no es proveedor, devolver datos completos
    if not es_proveedor(user_rol):
        return df_ventas
    
    # Intentar extraer filtro de diferentes campos del usuario
    filtros_posibles = [
        user_info.get('_zona', ''),       # A veces la zona contiene la marca
        user_info.get('_nombre_orig', ''), # Nombre puede contener marca
    ]
    
    # Aplicar filtros
    df_filtrado = df_ventas.copy()
    for filtro in filtros_posibles:
        if filtro and filtro.strip() and filtro.upper() not in ('NAN', 'NONE', ''):
            # Intentar filtrar por proveedor
            mask_prov = df_filtrado['Proveedor'].str.contains(filtro, case=False, na=False)
            if mask_prov.sum() > 0:
                df_filtrado = df_filtrado[mask_prov]
                break
            
            # Si no funciona proveedor, intentar por marca
            mask_marca = df_filtrado['Marca'].str.contains(filtro, case=False, na=False)
            if mask_marca.sum() > 0:
                df_filtrado = df_filtrado[mask_marca]
                break
    
    return df_filtrado


def calcular_metricas_proveedor(df_ventas, mes_seleccionado, user_info):
    """Calcula métricas específicas para proveedores"""
    # Filtrar por mes
    df_mes = df_ventas[df_ventas['Fecha'].dt.strftime('%B %Y') == mes_seleccionado]
    
    if df_mes.empty:
        return {
            'total_ventas': 0,
            'total_facturas': 0,
            'clientes_unicos': 0,
            'vendedores_activos': 0,
            'top_productos': pd.Series(dtype=float),
            'top_vendedores': pd.Series(dtype=float),
            'crecimiento': 0,
            'es_proveedor': es_proveedor(user_info.get('_rol', ''))
        }
    
    total_ventas = df_mes['Total'].sum()
    total_facturas = len(df_mes)
    clientes_unicos = df_mes['Cliente'].nunique()
    vendedores_activos = df_mes[df_mes['Total'] > 0]['Vendedor'].nunique()
    top_productos = df_mes.groupby('Marca')['Total'].sum().nlargest(5)
    top_vendedores = df_mes.groupby('Vendedor')['Total'].sum().nlargest(5)
    
    # Calcular crecimiento vs mes anterior
    try:
        fecha_actual = datetime.now()
        if fecha_actual.month == 1:
            mes_anterior = f"{calendar.month_name[12]} {fecha_actual.year - 1}"
        else:
            mes_anterior = f"{calendar.month_name[fecha_actual.month - 1]} {fecha_actual.year}"
        
        df_anterior = df_ventas[df_ventas['Fecha'].dt.strftime('%B %Y') == mes_anterior]
        ventas_anterior = df_anterior['Total'].sum()
        
        if ventas_anterior > 0:
            crecimiento = ((total_ventas - ventas_anterior) / ventas_anterior) * 100
        else:
            crecimiento = 0
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
        'es_proveedor': es_proveedor(user_info.get('_rol', ''))
    }


# ══════════════════════════════════════════════════════════════════
#  RESTO DEL CÓDIGO IGUAL QUE TU DASHBOARD PRINCIPAL
# ══════════════════════════════════════════════════════════════════

def enviar_telegram(mensaje, chat_id=None, imagen=None):
    """Envía mensaje y/o imagen a Telegram"""
    if not chat_id:
        chat_id = TELEGRAM_CONFIG['CHAT_IDS']['gerencia']
    
    bot_token = TELEGRAM_CONFIG['BOT_TOKEN']
    
    try:
        # Enviar mensaje de texto
        if mensaje:
            url_texto = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': mensaje,
                'parse_mode': 'HTML'
            }
            requests.post(url_texto, data=payload)
        
        # Enviar imagen si existe
        if imagen:
            try:
                url_foto = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
                files = {'photo': imagen}
                data = {'chat_id': chat_id}
                response = requests.post(url_foto, files=files, data=data)
                
                if response.status_code == 200:
                    return True
                else:
                    return True
            except:
                return True
            
        return True
    except Exception as e:
        return False

st.set_page_config(
    page_title="Portal Proveedores - SOLUTO",
    layout="wide",
    page_icon="🏢",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Syne:wght@700;800&display=swap');
html,body,[class*="css"]{font-family:'Space Grotesk',sans-serif;background:#0A0F1E;color:#E2E8F0;}
header,footer,#MainMenu{visibility:hidden;}
.block-container{padding:1rem 1.5rem!important;max-width:100%!important;}
div[data-testid="stSidebar"]{background:linear-gradient(180deg,#0A0F1E,#111827);border-right:1px solid #1E3A8A33;}
.login-logo{font-family:'Syne',sans-serif;font-size:2rem;font-weight:800;color:#3B82F6;letter-spacing:-1px;margin-bottom:4px;}
.login-sub{font-size:0.78rem;color:#64748B;text-transform:uppercase;letter-spacing:2px;margin-bottom:28px;}
.login-label{font-size:0.72rem;color:#94A3B8;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:6px;font-weight:600;}
.error-box{background:#450A0A;border:1px solid #7F1D1D;border-radius:8px;padding:10px 14px;font-size:0.82rem;color:#FCA5A5;margin-top:12px;}
.top-bar{background:linear-gradient(135deg,#0F172A,#1E2940);border:1px solid #1E3A8A44;border-radius:14px;padding:14px 22px;margin-bottom:16px;display:flex;justify-content:space-between;align-items:center;}
.top-bar-title{font-family:'Syne',sans-serif;font-size:1.3rem;font-weight:800;color:#F8FAFC;}
.top-bar-user{font-size:0.78rem;color:#60A5FA;font-weight:600;text-align:right;}
.top-bar-badge{background:#1E3A8A;border-radius:20px;padding:4px 14px;font-size:0.7rem;color:#BFDBFE;font-weight:700;text-transform:uppercase;display:inline-block;margin-top:4px;}
.kpi-card{background:linear-gradient(145deg,#111827,#1A2540);border:1px solid #1E3A8A33;border-radius:14px;padding:18px 20px;text-align:center;position:relative;overflow:hidden;margin-bottom:8px;}
.kpi-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:var(--accent,#3B82F6);border-radius:14px 14px 0 0;}
.kpi-val{font-family:'Syne',sans-serif;font-size:1.8rem;font-weight:800;color:var(--accent,#3B82F6);line-height:1;margin-bottom:4px;}
.kpi-lbl{font-size:0.62rem;color:#64748B;text-transform:uppercase;letter-spacing:1.5px;font-weight:600;}
.kpi-sub{font-size:0.7rem;color:#94A3B8;margin-top:4px;}
.section-title{font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;color:#CBD5E1;margin:18px 0 10px;text-transform:uppercase;letter-spacing:1px;}
.cruce-ok{background:#052e16;border:1px solid #16a34a;border-radius:8px;padding:8px 14px;font-size:0.8rem;color:#86efac;margin:6px 0;}
.cruce-err{background:#450a0a;border:1px solid #dc2626;border-radius:8px;padding:8px 14px;font-size:0.8rem;color:#fca5a5;margin:6px 0;}
.admin-badge{background:linear-gradient(135deg,#7C3AED,#A855F7);border-radius:6px;padding:2px 10px;font-size:0.65rem;font-weight:700;color:#F5F3FF;text-transform:uppercase;letter-spacing:1px;display:inline-block;margin-left:8px;}
.proveedor-badge{background:linear-gradient(135deg,#F59E0B,#D97706);border-radius:6px;padding:2px 10px;font-size:0.65rem;font-weight:700;color:#FFF;text-transform:uppercase;letter-spacing:1px;display:inline-block;margin-left:8px;}
.stButton>button,.stDownloadButton>button{background:linear-gradient(135deg,#1E40AF,#3B82F6)!important;color:white!important;border:none!important;border-radius:8px!important;font-weight:700!important;}
.stTabs [data-baseweb="tab-list"]{background:#111827;border-radius:10px;padding:4px;gap:4px;}
.stTabs [data-baseweb="tab"]{background:transparent!important;color:#64748B!important;border-radius:8px!important;font-weight:600!important;}
.stTabs [aria-selected="true"]{background:#1E3A8A!important;color:#fff!important;}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════
def norm_txt(v):
    """Quita tildes, mayúsculas, colapsa espacios."""
    s = str(v).strip().upper()
    s = ''.join(c for c in unicodedata.normalize('NFD', s)
                if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', s)


def limpiar_columnas(df):
    """Elimina BOM, espacios y caracteres invisibles de los nombres de columna."""
    df.columns = [
        str(c).strip()
          .replace('\ufeff', '')
          .replace('\xa0', '')
          .replace('\u200b', '')
        for c in df.columns
    ]
    return df


def descomponer_vendedor(texto):
    """
    'PDV09 - YANEZ FLORES JENNIFER LISSETTE'  → ('PDV09', 'YANEZ FLORES JENNIFER LISSETTE')
    """
    texto = str(texto).strip()
    m = re.match(r'(PDV\d+)', texto.upper())
    codigo = m.group(1) if m else ''

    if ' - ' in texto:
        nombre = texto.split(' - ', 1)[1].strip()
    elif codigo:
        nombre = re.sub(r'^PDV\d+\S*\s*', '', texto, flags=re.IGNORECASE).strip()
    else:
        nombre = texto

    return codigo.upper(), norm_txt(nombre)


# ══════════════════════════════════════════════════════════════════
#  CONEXIÓN GOOGLE SHEETS (IGUAL QUE TU DASHBOARD)
# ══════════════════════════════════════════════════════════════════
@st.cache_resource(ttl=300)
def get_gc():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    
    try:
        # Usar secrets de Streamlit Cloud
        creds_dict = dict(st.secrets["google"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    except Exception:
        try:
            # Fallback local
            creds = ServiceAccountCredentials.from_json_keyfile_name('credenciales.json', scope)
        except Exception as e:
            st.error("❌ Error de conexión con Google Sheets")
            st.info("💡 Contacta al administrador del sistema")
            st.stop()
    
    return gspread.authorize(creds)


# ══════════════════════════════════════════════════════════════════
#  CARGA USUARIOS
# ══════════════════════════════════════════════════════════════════
@st.cache_data(ttl=300)
def cargar_usuarios():
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
        return df

    col_nombre = next((c for c in df.columns if 'nombre' in c.lower()), None)
    col_pin    = next((c for c in df.columns if 'pin'    in c.lower()), None)
    col_rol    = next((c for c in df.columns if 'rol'    in c.lower()), None)
    col_zona   = next((c for c in df.columns if 'zona'   in c.lower()), None)
    col_codigo = next((c for c in df.columns if 'codigo' in c.lower()), None)

    df['_nombre_orig'] = df[col_nombre].astype(str).str.strip() if col_nombre else ''
    df['_nombre_norm'] = df['_nombre_orig'].apply(norm_txt)
    df['_pin']         = df[col_pin].astype(str).str.strip()    if col_pin    else ''
    df['_rol']         = df[col_rol].astype(str).str.strip()    if col_rol    else 'Vendedor'
    df['_zona']        = df[col_zona].astype(str).str.strip()   if col_zona   else ''
    df['_codigo_pdv']  = (
        df[col_codigo].astype(str).str.strip().str.upper()
        if col_codigo else ''
    )
    df['_codigo_pdv'] = df['_codigo_pdv'].replace({'NAN': '', 'NONE': ''})
    return df


# ══════════════════════════════════════════════════════════════════
#  CARGA VENTAS + PRESUPUESTO (IGUAL QUE TU DASHBOARD)
# ══════════════════════════════════════════════════════════════════
@st.cache_data(ttl=300)
def cargar_ventas_presupuesto():
    gc = get_gc()
    sh = gc.open("soluto")

    # ── VENTAS ────────────────────────────────────────────────────
    ws_v   = sh.worksheet("VENTAS")
    df_raw = pd.DataFrame(ws_v.get_all_records())
    df_raw = limpiar_columnas(df_raw)

    def find_col(df, keyword):
        return next((c for c in df.columns if keyword in norm_txt(c)), None)

    col_fecha = find_col(df_raw, 'FECHA')
    col_total = find_col(df_raw, 'TOTAL')
    col_vend  = find_col(df_raw, 'VENDEDOR')
    col_cli   = find_col(df_raw, 'CLIENTE')
    col_marca = find_col(df_raw, 'MARCA')
    col_prov  = find_col(df_raw, 'PROVEEDOR')

    st.session_state['_cols_ventas'] = list(df_raw.columns)

    if col_fecha is None:
        raise ValueError(f"❌ No se encontró columna FECHA en la hoja VENTAS.")
    if col_total is None:
        raise ValueError(f"❌ No se encontró columna TOTAL en la hoja VENTAS.")

    fecha_series = pd.to_datetime(df_raw[col_fecha], errors='coerce', dayfirst=True)
    total_series = pd.to_numeric(
        df_raw[col_total].astype(str).str.replace(r'[$,\s]', '', regex=True),
        errors='coerce'
    ).fillna(0)

    mask_ok = fecha_series.notna()
    df_v = df_raw[mask_ok].copy()
    df_v['Fecha']    = fecha_series[mask_ok].values
    df_v['Total']    = total_series[mask_ok].values
    df_v['Vendedor'] = df_v[col_vend].astype(str)  if col_vend  else ''
    df_v['Cliente']  = df_v[col_cli].astype(str)   if col_cli   else ''
    df_v['Marca']    = df_v[col_marca].astype(str) if col_marca else ''
    df_v['Proveedor']= df_v[col_prov].astype(str)  if col_prov  else ''

    descomp = df_v['Vendedor'].apply(descomponer_vendedor)
    df_v['_codigo_pdv']  = descomp.apply(lambda x: x[0])
    df_v['_nombre_vend'] = descomp.apply(lambda x: x[1])

    # ── PRESUPUESTO ───────────────────────────────────────────────
    ws_p = sh.worksheet("PRESUPUESTO")
    df_p = pd.DataFrame(ws_p.get_all_records())
    df_p = limpiar_columnas(df_p)

    rename_map = {}
    for c in df_p.columns:
        cn = norm_txt(c)
        if 'VENDEDOR' in cn:
            rename_map[c] = 'V_Orig'
        elif 'OBJETIVO' in cn or cn == 'DN':
            rename_map[c] = 'M_DN'
        elif 'PRESUPUESTO' in cn or 'META' in cn:
            rename_map[c] = 'M_V'
    df_p = df_p.rename(columns=rename_map)

    for col in ['M_V', 'M_DN']:
        if col not in df_p.columns:
            df_p[col] = 0
        df_p[col] = pd.to_numeric(
            df_p[col].astype(str).str.replace(r'[$,\s]', '', regex=True),
            errors='coerce'
        ).fillna(0)

    if 'V_Orig' not in df_p.columns:
        df_p['V_Orig'] = ''

    audit = {'monto_perdido': 0, 'filas_afectadas': 0}
    return df_v, df_p, audit


# ══════════════════════════════════════════════════════════════════
#  LOGIN
# ══════════════════════════════════════════════════════════════════
def pantalla_login():
    df_users = cargar_usuarios()
    if df_users.empty:
        st.error("❌ No se pudo cargar la hoja Usuario_Roles.")
        return

    nombres = sorted(df_users['_nombre_orig'].tolist())

    _, col_c, _ = st.columns([1, 1.1, 1])
    with col_c:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(
            "<div class='login-logo'>🏢 Portal Proveedores</div>"
            "<div class='login-sub'>SOLUTO · Acceso Exclusivo</div>",
            unsafe_allow_html=True
        )

        st.markdown("<div class='login-label'>👤 Selecciona tu nombre</div>",
                    unsafe_allow_html=True)
        nombre_sel = st.selectbox("", ["— Selecciona —"] + nombres,
                                  key="login_nombre", label_visibility="collapsed")

        st.markdown("<div class='login-label' style='margin-top:16px;'>🔐 Ingresa tu PIN</div>",
                    unsafe_allow_html=True)
        pin_inp = st.text_input("", type="password", placeholder="• • • • •",
                                key="login_pin", label_visibility="collapsed", max_chars=6)

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("→ INGRESAR", use_container_width=True, key="btn_login"):
            if nombre_sel == "— Selecciona —":
                st.markdown("<div class='error-box'>⚠️ Selecciona tu nombre.</div>",
                            unsafe_allow_html=True)
                return

            fila = df_users[df_users['_nombre_orig'] == nombre_sel]
            if fila.empty:
                st.markdown("<div class='error-box'>❌ Usuario no encontrado.</div>",
                            unsafe_allow_html=True)
                return

            u = fila.iloc[0]
            try:
                pin_correcto = str(int(float(u['_pin'])))
            except Exception:
                pin_correcto = str(u['_pin'])

            if pin_inp.strip() != pin_correcto:
                st.markdown("<div class='error-box'>🔒 PIN incorrecto.</div>",
                            unsafe_allow_html=True)
                return

            st.session_state.update({
                'logged_in':   True,
                'user_nombre': nombre_sel,
                'user_norm':   str(u['_nombre_norm']),
                'user_rol':    str(u['_rol']),
                'user_zona':   str(u['_zona']),
                'user_codigo': str(u['_codigo_pdv']),
                'user_row':    u.to_dict(),
            })
            st.rerun()

        st.caption("🔒 Acceso restringido — Portal Proveedores SOLUTO")
        
        # Info para proveedores
        with st.expander("ℹ️ Información de Acceso"):
            st.markdown("""
            **🏢 Portal Exclusivo para Proveedores y Socios Comerciales**
            
            **📊 Funcionalidades:**
            - Análisis de ventas de tus productos
            - Rankings de vendedores por marca
            - Métricas de crecimiento
            - Análisis detallado por período
            
            **📞 Soporte:** Contacta al administrador del sistema
            """)


# ══════════════════════════════════════════════════════════════════
#  KPI CARD
# ══════════════════════════════════════════════════════════════════
def kpi_card(col, valor, label, sub="", accent="#3B82F6", prefix="$", suffix=""):
    val_fmt = (f"{prefix}{valor:,.0f}{suffix}"
               if isinstance(valor, (int, float)) else str(valor))
    col.markdown(
        f"<div class='kpi-card' style='--accent:{accent};'>"
        f"<div class='kpi-val'>{val_fmt}</div>"
        f"<div class='kpi-lbl'>{label}</div>"
        f"{'<div class=kpi-sub>' + sub + '</div>' if sub else ''}"
        f"</div>",
        unsafe_allow_html=True
    )


# ══════════════════════════════════════════════════════════════════
#  DASHBOARD PROVEEDORES
# ══════════════════════════════════════════════════════════════════
def dashboard_proveedores(df_v_all, df_p, usuario_row):
    user_nombre = st.session_state['user_nombre']
    user_rol    = st.session_state['user_rol']
    user_zona   = st.session_state['user_zona']
    user_codigo = st.session_state['user_codigo']
    
    # Sistema de permisos
    is_super_admin = es_super_admin(user_codigo, user_nombre)
    is_admin = tiene_permisos_admin(user_rol)
    is_proveedor_user = es_proveedor(user_rol)

    # ── Top bar ──────────────────────────────────────────────────
    if is_super_admin:
        admin_badge = "<span class='admin-badge'>SUPER ADMIN</span>"
    elif is_admin:
        admin_badge = "<span class='admin-badge'>Admin</span>"
    elif is_proveedor_user:
        admin_badge = "<span class='proveedor-badge'>Proveedor</span>"
    else:
        admin_badge = ""
        
    cod_lbl = (f"<span style='color:#475569;font-size:0.7rem;margin-left:8px;'>"
               f"[{user_codigo}]</span>") if user_codigo else ""
    st.markdown(
        f"<div class='top-bar'>"
        f"<div><span class='top-bar-title'>🏢 Portal Proveedores</span>{admin_badge}</div>"
        f"<div><div class='top-bar-user'>👤 {user_nombre}{cod_lbl}</div>"
        f"<div class='top-bar-badge'>{user_zona or 'SIN ZONA'}</div></div>"
        f"</div>",
        unsafe_allow_html=True
    )

    # ── Sidebar ───────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(
            f"<div style='color:#60A5FA;font-weight:700;padding:8px 0;'>"
            f"👤 {user_nombre}</div>",
            unsafe_allow_html=True
        )
        st.markdown(
            f"<div style='color:#64748B;font-size:0.75rem;margin-bottom:12px;'>"
            f"Rol: {user_rol} · Zona: {user_zona or '—'}</div>",
            unsafe_allow_html=True
        )
        
        if is_proveedor_user:
            st.info("📊 Vista filtrada por tus productos")
        elif is_super_admin or is_admin:
            st.success("🔑 Acceso completo de administrador")
        
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

    # ── Filtrar datos según tipo de usuario ──────────────────────
    if is_proveedor_user:
        # Los proveedores ven solo sus datos filtrados
        df_final = filtrar_datos_proveedor(df_v_all, usuario_row)
        filtro_info = f"📊 Mostrando datos filtrados para {user_rol}: {user_nombre}"
    else:
        # Admins e Israel ven todo
        df_final = df_v_all.copy()
        filtro_info = f"📊 Vista completa de administrador"

    # ── Controles ─────────────────────────────────────────────────
    df_final['Mes_N'] = df_final['Fecha'].dt.strftime('%B %Y')
    meses = sorted(df_final['Mes_N'].unique().tolist(), reverse=True)
    
    col_mes, col_info, col_logout = st.columns([2, 2, 1])
    
    with col_mes:
        if meses:
            m_sel = st.selectbox("📅 Selecciona el período:", meses, key="mes_sel")
        else:
            st.warning("Sin datos disponibles para este usuario")
            return
    
    with col_info:
        st.info(filtro_info)
    
    st.markdown("---")

    # ── Análisis por mes seleccionado ─────────────────────────────
    df_mes = df_final[df_final['Mes_N'] == m_sel].copy()
    
    if df_mes.empty:
        st.warning(f"⚠️ Sin datos para {m_sel}")
        return

    # ── Calcular métricas ─────────────────────────────────────────
    metricas = calcular_metricas_proveedor(df_mes, m_sel, usuario_row)

    # ── KPIs ──────────────────────────────────────────────────────
    st.markdown(f"<div class='section-title'>📊 {m_sel} — Análisis {user_rol}</div>",
                unsafe_allow_html=True)

    k1, k2, k3, k4 = st.columns(4)
    
    delta_color = "normal" if metricas['crecimiento'] >= 0 else "inverse"
    
    kpi_card(k1, metricas['total_ventas'], "Ventas Totales",
             f"Crecimiento {metricas['crecimiento']:+.1f}%", "#3B82F6")
    kpi_card(k2, metricas['total_facturas'], "Facturas",
             f"Total transacciones", "#F59E0B", prefix="")
    kpi_card(k3, metricas['clientes_unicos'], "Clientes Únicos",
             f"Alcance de mercado", "#10B981", prefix="")
    kpi_card(k4, metricas['vendedores_activos'], "Vendedores Activos",
             f"Equipo de ventas", "#A855F7", prefix="")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────────────
    if is_proveedor_user:
        tab1, tab2, tab3 = st.tabs(["📊 Mi Análisis", "🏪 Vendedores", "📦 Productos"])
    else:
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Análisis", "🏪 Vendedores", "📦 Productos", "🛡️ Admin"])

    # ── Tab 1: Análisis ───────────────────────────────────────────
    with tab1:
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown("<div class='section-title'>🏷️ Distribución por Marca</div>",
                        unsafe_allow_html=True)
            if not metricas['top_productos'].empty:
                fig_marcas = px.pie(
                    values=metricas['top_productos'].values,
                    names=metricas['top_productos'].index,
                    hole=0.45,
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig_marcas.update_layout(
                    paper_bgcolor='#111827',
                    plot_bgcolor='#111827',
                    font_color='#E2E8F0',
                    margin=dict(t=20, b=20, l=20, r=20),
                    legend=dict(font=dict(color='#E2E8F0')),
                    height=350
                )
                fig_marcas.update_traces(
                    textfont=dict(color='#FFFFFF', size=12),
                )
                st.plotly_chart(fig_marcas, use_container_width=True)
            else:
                st.info("📝 Sin datos de marcas para mostrar")

        with col_right:
            st.markdown("<div class='section-title'>📈 Tendencia de Ventas</div>",
                        unsafe_allow_html=True)
            if not df_mes.empty:
                try:
                    # Tendencia diaria
                    tendencia = df_mes.groupby(df_mes['Fecha'].dt.date)['Total'].sum().reset_index()
                    
                    fig_trend = px.line(
                        tendencia, x='Fecha', y='Total',
                        line_shape='spline'
                    )
                    fig_trend.update_layout(
                        paper_bgcolor='#111827',
                        plot_bgcolor='#111827',
                        font_color='#E2E8F0',
                        xaxis=dict(gridcolor='#1E3A8A22'),
                        yaxis=dict(gridcolor='#1E3A8A22'),
                        margin=dict(t=20, b=20, l=20, r=20),
                        height=350
                    )
                    fig_trend.update_traces(line_color='#3B82F6', line_width=3)
                    st.plotly_chart(fig_trend, use_container_width=True)
                except:
                    st.info("📝 Sin datos suficientes para tendencia")

    # ── Tab 2: Vendedores ─────────────────────────────────────────
    with tab2:
        st.markdown("### 🏆 Ranking de Vendedores")
        st.caption(f"Vendedores que más venden {'tus productos' if is_proveedor_user else 'en total'}")
        
        if not metricas['top_vendedores'].empty:
            # Mostrar ranking visual
            for i, (vendedor, venta) in enumerate(metricas['top_vendedores'].items(), 1):
                # Extraer nombre del vendedor
                nombre = vendedor.split(' - ')[1] if ' - ' in vendedor else vendedor
                nombre_corto = nombre[:35] + "..." if len(nombre) > 35 else nombre
                
                emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"#{i}"
                
                # Calcular porcentaje del top vendedor
                pct = round(venta / metricas['top_vendedores'].iloc[0] * 100) if metricas['top_vendedores'].iloc[0] > 0 else 0
                
                st.markdown(f"""
                <div style='background:linear-gradient(135deg,#1E40AF,#3B82F6);color:white;padding:1rem;border-radius:10px;margin:0.5rem 0;'>
                    <div style='display:flex;justify-content:space-between;align-items:center;'>
                        <div>
                            <span style='font-size:1.2rem;font-weight:bold;'>{emoji}</span>
                            <span style='font-size:1.1rem;margin-left:10px;'>{nombre_corto}</span>
                        </div>
                        <div style='text-align:right;'>
                            <div style='font-size:1.3rem;font-weight:bold;'>${venta:,.0f}</div>
                            <div style='font-size:0.9rem;opacity:0.8;'>{pct}%</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("📝 Sin datos de vendedores para el período seleccionado")

    # ── Tab 3: Productos ──────────────────────────────────────────
    with tab3:
        st.markdown("### 📦 Detalle de Productos")
        
        if not df_mes.empty:
            # Resumen por marca/producto
            resumen = df_mes.groupby(['Marca', 'Proveedor']).agg({
                'Total': ['sum', 'count', 'mean'],
                'Cliente': 'nunique'
            }).round(2)
            
            resumen.columns = ['Venta Total', 'Facturas', 'Venta Promedio', 'Clientes Únicos']
            resumen = resumen.reset_index().sort_values('Venta Total', ascending=False)
            
            # Métricas de productos
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🏷️ Marcas Activas", resumen['Marca'].nunique())
            with col2:
                st.metric("🏢 Proveedores", resumen['Proveedor'].nunique())
            with col3:
                promedio_por_marca = resumen['Venta Total'].mean()
                st.metric("💰 Promedio por Marca", f"${promedio_por_marca:,.0f}")
            
            # Tabla detallada
            st.markdown("#### 📋 Resumen por Marca")
            st.dataframe(resumen, use_container_width=True, height=400)
            
            # Gráfico de barras
            st.markdown("#### 📊 Top 10 Marcas")
            top_10 = resumen.head(10)
            fig_bar = px.bar(
                top_10, x='Venta Total', y='Marca',
                orientation='h',
                color='Venta Total',
                color_continuous_scale='Blues'
            )
            fig_bar.update_layout(
                paper_bgcolor='#111827',
                plot_bgcolor='#111827',
                font_color='#E2E8F0',
                height=400,
                showlegend=False
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("📝 Sin datos de productos disponibles")

    # ── Tab 4: Admin (Solo para admins) ───────────────────────────
    if not is_proveedor_user and 'tab4' in locals():
        with tab4:
            st.markdown("### 🛡️ Panel de Administración")
            
            if is_super_admin:
                st.success("🔑 Acceso Super Administrador")
                
                # Estadísticas generales
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    total_proveedores = df_final['Proveedor'].nunique()
                    st.metric("🏢 Proveedores", total_proveedores)
                with col2:
                    total_marcas = df_final['Marca'].nunique()
                    st.metric("🏷️ Marcas", total_marcas)
                with col3:
                    total_vendedores = df_final['Vendedor'].nunique()
                    st.metric("👥 Vendedores", total_vendedores)
                with col4:
                    total_clientes = df_final['Cliente'].nunique()
                    st.metric("🏪 Clientes", total_clientes)
                
                # Análisis por proveedor
                st.markdown("#### 📊 Análisis por Proveedor")
                analisis_prov = df_mes.groupby('Proveedor').agg({
                    'Total': 'sum',
                    'Cliente': 'nunique',
                    'Vendedor': 'nunique'
                }).round(0).reset_index()
                analisis_prov.columns = ['Proveedor', 'Ventas', 'Clientes', 'Vendedores']
                analisis_prov = analisis_prov.sort_values('Ventas', ascending=False)
                st.dataframe(analisis_prov, use_container_width=True)
                
            else:
                st.info("🔒 Panel disponible solo para Super Administrador")


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
        df_v, df_p, _ = cargar_ventas_presupuesto()
    except ValueError as e:
        st.error(str(e))
        st.stop()

    if df_v.empty:
        st.error("❌ Sin datos de ventas en la hoja VENTAS.")
        return

    dashboard_proveedores(df_v, df_p, st.session_state.get('user_row', {}))


if __name__ == "__main__":
    main()
