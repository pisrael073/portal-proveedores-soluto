import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from datetime import datetime
import calendar
import re
import unicodedata

# ══════════════════════════════════════════════════════════════════
#  CONFIG TELEGRAM
# ══════════════════════════════════════════════════════════════════

TELEGRAM_CONFIG = {
    'BOT_TOKEN': '8249353159:AAFvpNkEUdTcuIu_kpMcQbOtqyB0WbZkGTc',
    'CHAT_IDS': {
        'gerencia': '7900265168',
        'administracion': '7900265168',
        'vendedores': '-5180849774'
    }
}

# ══════════════════════════════════════════════════════════════════
#  FUNCIONES DE PROVEEDORES
# ══════════════════════════════════════════════════════════════════

def es_super_admin(user_codigo, user_nombre):
    """Verifica si el usuario es Israel (super administrador)"""
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
    
    if not es_proveedor(user_rol):
        return df_ventas
    
    # Usar zona o nombre para filtrar
    filtros_posibles = [
        user_info.get('_zona', ''),
        user_info.get('_nombre_orig', ''),
    ]
    
    df_filtrado = df_ventas.copy()
    for filtro in filtros_posibles:
        if filtro and filtro.strip() and filtro.upper() not in ('NAN', 'NONE', ''):
            # Filtrar por proveedor
            mask_prov = df_filtrado['Proveedor'].str.contains(filtro, case=False, na=False)
            if mask_prov.sum() > 0:
                df_filtrado = df_filtrado[mask_prov]
                break
            # Filtrar por marca
            mask_marca = df_filtrado['Marca'].str.contains(filtro, case=False, na=False)
            if mask_marca.sum() > 0:
                df_filtrado = df_filtrado[mask_marca]
                break
    
    return df_filtrado

def calcular_metricas_proveedor(df_ventas, mes_seleccionado, user_info):
    """Calcula métricas específicas para proveedores"""
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
    
    # Crecimiento vs mes anterior
    try:
        fecha_actual = datetime.now()
        if fecha_actual.month == 1:
            mes_anterior = f"{calendar.month_name[12]} {fecha_actual.year - 1}"
        else:
            mes_anterior = f"{calendar.month_name[fecha_actual.month - 1]} {fecha_actual.year}"
        
        df_anterior = df_ventas[df_ventas['Fecha'].dt.strftime('%B %Y') == mes_anterior]
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
        'es_proveedor': es_proveedor(user_info.get('_rol', ''))
    }

# ══════════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════════

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
.top-bar{background:linear-gradient(135deg,#0F172A,#1E2940);border:1px solid #1E3A8A44;border-radius:14px;padding:14px 22px;margin-bottom:16px;display:flex;justify-content:space-between;align-items:center;}
.top-bar-title{font-family:'Syne',sans-serif;font-size:1.3rem;font-weight:800;color:#F8FAFC;}
.top-bar-user{font-size:0.78rem;color:#60A5FA;font-weight:600;text-align:right;}
.kpi-card{background:linear-gradient(145deg,#111827,#1A2540);border:1px solid #1E3A8A33;border-radius:14px;padding:18px 20px;text-align:center;position:relative;overflow:hidden;margin-bottom:8px;}
.kpi-val{font-family:'Syne',sans-serif;font-size:1.8rem;font-weight:800;color:#3B82F6;line-height:1;margin-bottom:4px;}
.kpi-lbl{font-size:0.62rem;color:#64748B;text-transform:uppercase;letter-spacing:1.5px;font-weight:600;}
.section-title{font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;color:#CBD5E1;margin:18px 0 10px;text-transform:uppercase;letter-spacing:1px;}
.proveedor-badge{background:linear-gradient(135deg,#F59E0B,#D97706);border-radius:6px;padding:2px 10px;font-size:0.65rem;font-weight:700;color:#FFF;text-transform:uppercase;letter-spacing:1px;display:inline-block;margin-left:8px;}
.admin-badge{background:linear-gradient(135deg,#7C3AED,#A855F7);border-radius:6px;padding:2px 10px;font-size:0.65rem;font-weight:700;color:#F5F3FF;text-transform:uppercase;letter-spacing:1px;display:inline-block;margin-left:8px;}
.stButton>button{background:linear-gradient(135deg,#1E40AF,#3B82F6)!important;color:white!important;border:none!important;border-radius:8px!important;font-weight:700!important;}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
#  HELPERS (IGUAL QUE TU DASHBOARD)
# ══════════════════════════════════════════════════════════════════

def norm_txt(v):
    s = str(v).strip().upper()
    s = ''.join(c for c in unicodedata.normalize('NFD', s)
                if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', s)

def limpiar_columnas(df):
    df.columns = [
        str(c).strip().replace('\ufeff', '').replace('\xa0', '').replace('\u200b', '')
        for c in df.columns
    ]
    return df

def descomponer_vendedor(texto):
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
        creds_dict = dict(st.secrets["google"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    except Exception:
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name('credenciales.json', scope)
        except Exception as e:
            st.error("❌ Error de conexión con Google Sheets")
            st.stop()
    return gspread.authorize(creds)

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
    col_pin    = next((c for c in df.columns if 'pin' in c.lower()), None)
    col_rol    = next((c for c in df.columns if 'rol' in c.lower()), None)
    col_zona   = next((c for c in df.columns if 'zona' in c.lower()), None)
    col_codigo = next((c for c in df.columns if 'codigo' in c.lower()), None)

    df['_nombre_orig'] = df[col_nombre].astype(str).str.strip() if col_nombre else ''
    df['_nombre_norm'] = df['_nombre_orig'].apply(norm_txt)
    df['_pin'] = df[col_pin].astype(str).str.strip() if col_pin else ''
    df['_rol'] = df[col_rol].astype(str).str.strip() if col_rol else 'Vendedor'
    df['_zona'] = df[col_zona].astype(str).str.strip() if col_zona else ''
    df['_codigo_pdv'] = (df[col_codigo].astype(str).str.strip().str.upper() if col_codigo else '')
    df['_codigo_pdv'] = df['_codigo_pdv'].replace({'NAN': '', 'NONE': ''})
    return df

@st.cache_data(ttl=300)
def cargar_ventas_presupuesto():
    gc = get_gc()
    sh = gc.open("soluto")

    # VENTAS
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

    if col_fecha is None or col_total is None:
        raise ValueError("❌ No se encontraron columnas FECHA o TOTAL en VENTAS")

    fecha_series = pd.to_datetime(df_raw[col_fecha], errors='coerce', dayfirst=True)
    total_series = pd.to_numeric(
        df_raw[col_total].astype(str).str.replace(r'[$,\s]', '', regex=True),
        errors='coerce'
    ).fillna(0)

    mask_ok = fecha_series.notna()
    df_v = df_raw[mask_ok].copy()
    df_v['Fecha'] = fecha_series[mask_ok].values
    df_v['Total'] = total_series[mask_ok].values
    df_v['Vendedor'] = df_v[col_vend].astype(str) if col_vend else ''
    df_v['Cliente'] = df_v[col_cli].astype(str) if col_cli else ''
    df_v['Marca'] = df_v[col_marca].astype(str) if col_marca else ''
    df_v['Proveedor'] = df_v[col_prov].astype(str) if col_prov else ''

    # PRESUPUESTO (simplificado)
    try:
        ws_p = sh.worksheet("PRESUPUESTO")
        df_p = pd.DataFrame(ws_p.get_all_records())
        df_p = limpiar_columnas(df_p)
    except:
        df_p = pd.DataFrame()

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
        st.markdown("### 🏢 Portal Proveedores SOLUTO")
        st.markdown("##### Acceso Exclusivo para Socios Comerciales")

        nombre_sel = st.selectbox("👤 Selecciona tu nombre:", ["— Selecciona —"] + nombres)
        pin_inp = st.text_input("🔐 Ingresa tu PIN:", type="password", max_chars=6)

        if st.button("→ INGRESAR", use_container_width=True):
            if nombre_sel == "— Selecciona —":
                st.error("⚠️ Selecciona tu nombre.")
                return

            fila = df_users[df_users['_nombre_orig'] == nombre_sel]
            if fila.empty:
                st.error("❌ Usuario no encontrado.")
                return

            u = fila.iloc[0]
            try:
                pin_correcto = str(int(float(u['_pin'])))
            except Exception:
                pin_correcto = str(u['_pin'])

            if pin_inp.strip() != pin_correcto:
                st.error("🔒 PIN incorrecto.")
                return

            st.session_state.update({
                'logged_in': True,
                'user_nombre': nombre_sel,
                'user_rol': str(u['_rol']),
                'user_zona': str(u['_zona']),
                'user_codigo': str(u['_codigo_pdv']),
                'user_row': u.to_dict(),
            })
            st.rerun()

        with st.expander("ℹ️ Información de Acceso"):
            st.markdown("""
            **🏢 Portal Exclusivo para Proveedores**
            
            **📊 Funcionalidades:**
            - Análisis de ventas de tus productos
            - Rankings de vendedores por marca
            - Métricas de crecimiento
            - Análisis detallado por período
            """)

# ══════════════════════════════════════════════════════════════════
#  KPI CARD
# ══════════════════════════════════════════════════════════════════

def kpi_card(col, valor, label, sub="", prefix="$", suffix=""):
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
# ══════════════════════════════════════════════════════════════════

def dashboard_proveedores(df_v_all, df_p, usuario_row):
    user_nombre = st.session_state['user_nombre']
    user_rol = st.session_state['user_rol']
    user_zona = st.session_state['user_zona']
    user_codigo = st.session_state['user_codigo']
    
    # Sistema de permisos
    is_super_admin = es_super_admin(user_codigo, user_nombre)
    is_admin = tiene_permisos_admin(user_rol)
    is_proveedor_user = es_proveedor(user_rol)

    # Top bar
    if is_super_admin:
        admin_badge = "<span class='admin-badge'>SUPER ADMIN</span>"
    elif is_admin:
        admin_badge = "<span class='admin-badge'>Admin</span>"
    elif is_proveedor_user:
        admin_badge = "<span class='proveedor-badge'>Proveedor</span>"
    else:
        admin_badge = ""
        
    st.markdown(
        f"<div class='top-bar'>"
        f"<div><span class='top-bar-title'>🏢 Portal Proveedores</span>{admin_badge}</div>"
        f"<div><div class='top-bar-user'>👤 {user_nombre}</div></div>"
        f"</div>",
        unsafe_allow_html=True
    )

    # Sidebar
    with st.sidebar:
        st.markdown(f"**👤 {user_nombre}**")
        st.markdown(f"**Rol:** {user_rol}")
        st.markdown(f"**Zona:** {user_zona or '—'}")
        
        if is_proveedor_user:
            st.info("📊 Vista filtrada por tus productos")
        elif is_super_admin or is_admin:
            st.success("🔑 Acceso completo")
        
        if st.button("🚪 Cerrar Sesión"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

    # Filtrar datos según tipo de usuario
    if is_proveedor_user:
        df_final = filtrar_datos_proveedor(df_v_all, usuario_row)
        filtro_info = f"📊 Vista filtrada para {user_rol}"
    else:
        df_final = df_v_all.copy()
        filtro_info = f"📊 Vista completa de administrador"

    # Controles
    df_final['Mes_N'] = df_final['Fecha'].dt.strftime('%B %Y')
    meses = sorted(df_final['Mes_N'].unique().tolist(), reverse=True)
    
    col_mes, col_info = st.columns([1, 2])
    with col_mes:
        if meses:
            m_sel = st.selectbox("📅 Período:", meses)
        else:
            st.warning("Sin datos disponibles")
            return
    with col_info:
        st.info(filtro_info)

    # Análisis por mes
    df_mes = df_final[df_final['Mes_N'] == m_sel].copy()
    if df_mes.empty:
        st.warning(f"⚠️ Sin datos para {m_sel}")
        return

    # Métricas
    metricas = calcular_metricas_proveedor(df_mes, m_sel, usuario_row)

    # KPIs
    st.markdown(f"<div class='section-title'>📊 {m_sel} — Análisis {user_rol}</div>", unsafe_allow_html=True)

    k1, k2, k3, k4 = st.columns(4)
    kpi_card(k1, metricas['total_ventas'], "Ventas Totales")
    kpi_card(k2, metricas['total_facturas'], "Facturas", prefix="")
    kpi_card(k3, metricas['clientes_unicos'], "Clientes Únicos", prefix="")
    kpi_card(k4, metricas['vendedores_activos'], "Vendedores Activos", prefix="")

    # Tabs
    if is_proveedor_user:
        tab1, tab2, tab3 = st.tabs(["📊 Mi Análisis", "🏪 Vendedores", "📦 Productos"])
    else:
        tab1, tab2, tab3 = st.tabs(["📊 Análisis", "🏪 Vendedores", "📦 Productos"])

    # Tab 1: Análisis
    with tab1:
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown("#### 🏷️ Distribución por Marca")
            if not metricas['top_productos'].empty:
                # Gráfico simple con Streamlit nativo
                st.bar_chart(metricas['top_productos'])
            else:
                st.info("Sin datos de marcas")

        with col_right:
            st.markdown("#### 📈 Tendencia de Ventas")
            if not df_mes.empty:
                try:
                    tendencia = df_mes.groupby(df_mes['Fecha'].dt.date)['Total'].sum()
                    st.line_chart(tendencia.tail(15))
                except:
                    st.info("Sin datos para tendencia")

    # Tab 2: Vendedores
    with tab2:
        st.markdown("### 🏆 Ranking de Vendedores")
        
        if not metricas['top_vendedores'].empty:
            for i, (vendedor, venta) in enumerate(metricas['top_vendedores'].items(), 1):
                nombre = vendedor.split(' - ')[1] if ' - ' in vendedor else vendedor
                nombre_corto = nombre[:35] + "..." if len(nombre) > 35 else nombre
                
                emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"#{i}"
                
                st.markdown(f"""
                <div style='background:linear-gradient(135deg,#1E40AF,#3B82F6);color:white;padding:1rem;border-radius:10px;margin:0.5rem 0;'>
                    <div style='display:flex;justify-content:space-between;'>
                        <div><span style='font-size:1.2rem;font-weight:bold;'>{emoji}</span> {nombre_corto}</div>
                        <div style='font-size:1.3rem;font-weight:bold;'>${venta:,.0f}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Sin datos de vendedores")

    # Tab 3: Productos
    with tab3:
        st.markdown("### 📦 Detalle de Productos")
        
        if not df_mes.empty:
            resumen = df_mes.groupby(['Marca', 'Proveedor']).agg({
                'Total': ['sum', 'count'],
                'Cliente': 'nunique'
            }).round(2)
            
            resumen.columns = ['Venta Total', 'Facturas', 'Clientes Únicos']
            resumen = resumen.reset_index().sort_values('Venta Total', ascending=False)
            
            # Métricas
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🏷️ Marcas", resumen['Marca'].nunique())
            with col2:
                st.metric("🏢 Proveedores", resumen['Proveedor'].nunique())
            with col3:
                st.metric("💰 Promedio", f"${resumen['Venta Total'].mean():,.0f}")
            
            st.dataframe(resumen, use_container_width=True)

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
        st.error("❌ Sin datos de ventas.")
        return

    dashboard_proveedores(df_v, df_p, st.session_state.get('user_row', {}))

if __name__ == "__main__":
    main()
