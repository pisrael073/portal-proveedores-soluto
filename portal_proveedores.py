import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import calendar
import re
import unicodedata

# ══════════════════════════════════════════════════════════════════
#  CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Portal Proveedores - SOLUTO",
    layout="wide",
    page_icon="🏢",
    initial_sidebar_state="expanded"
)

# ══════════════════════════════════════════════════════════════════
#  FUNCIONES AUXILIARES (COPIADAS EXACTAS DE TU DASHBOARD)
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

# ══════════════════════════════════════════════════════════════════
#  CONEXIÓN GOOGLE SHEETS (EXACTA DE TU DASHBOARD)
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
#  CARGA DE DATOS (ADAPTADA PARA PROVEEDORES)
# ══════════════════════════════════════════════════════════════════

@st.cache_data(ttl=300)
def cargar_usuarios_proveedores():
    """Carga usuarios con enfoque en proveedores"""
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

    # Buscar columnas (mismo método que tu dashboard)
    col_nombre = next((c for c in df.columns if 'nombre' in c.lower()), None)
    col_pin    = next((c for c in df.columns if 'pin' in c.lower() or 'password' in c.lower()), None)
    col_rol    = next((c for c in df.columns if 'rol' in c.lower() or 'tipo' in c.lower()), None)
    col_proveedor = next((c for c in df.columns if 'proveedor' in c.lower()), None)
    col_marca = next((c for c in df.columns if 'marca' in c.lower()), None)

    # Normalizar columnas
    df['_nombre_orig'] = df[col_nombre].astype(str).str.strip() if col_nombre else ''
    df['_nombre_norm'] = df['_nombre_orig'].apply(norm_txt)
    df['_pin']         = df[col_pin].astype(str).str.strip() if col_pin else ''
    df['_rol']         = df[col_rol].astype(str).str.strip() if col_rol else 'Proveedor'
    df['_proveedor']   = df[col_proveedor].astype(str).str.strip() if col_proveedor else ''
    df['_marca']       = df[col_marca].astype(str).str.strip() if col_marca else ''
    
    return df

@st.cache_data(ttl=300)
def cargar_ventas_inventario():
    """Carga ventas e inventario - misma estructura que tu función"""
    gc = get_gc()
    sh = gc.open("soluto")

    # ── VENTAS (MISMO CÓDIGO QUE TU DASHBOARD) ─────────────────────
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
    col_costo = find_col(df_raw, 'COSTO')

    if col_fecha is None or col_total is None:
        st.error("❌ Error: No se encontraron columnas FECHA o TOTAL en VENTAS")
        return pd.DataFrame(), pd.DataFrame()

    # Parsear fecha y total (mismo código que tu dashboard)
    fecha_series = pd.to_datetime(df_raw[col_fecha], errors='coerce', dayfirst=True)
    total_series = pd.to_numeric(
        df_raw[col_total].astype(str).str.replace(r'[$,\s]', '', regex=True),
        errors='coerce'
    ).fillna(0)

    mask_ok = fecha_series.notna()
    df_v = df_raw[mask_ok].copy()
    df_v['Fecha']     = fecha_series[mask_ok].values
    df_v['Total']     = total_series[mask_ok].values
    df_v['Vendedor']  = df_v[col_vend].astype(str) if col_vend else ''
    df_v['Cliente']   = df_v[col_cli].astype(str) if col_cli else ''
    df_v['Marca']     = df_v[col_marca].astype(str) if col_marca else ''
    df_v['Proveedor'] = df_v[col_prov].astype(str) if col_prov else ''
    df_v['Costo']     = pd.to_numeric(df_v[col_costo], errors='coerce').fillna(0) if col_costo else 0

    # ── INVENTARIO ──────────────────────────────────────────────
    try:
        ws_i = sh.worksheet("INVENTARIO")
        df_inv_raw = pd.DataFrame(ws_i.get_all_records())
        df_inv_raw = limpiar_columnas(df_inv_raw)
        
        # Buscar columnas en inventario
        col_inv_prov = find_col(df_inv_raw, 'PROVEEDOR')
        col_inv_marca = find_col(df_inv_raw, 'MARCA')
        col_inv_desc = find_col(df_inv_raw, 'DESCRIPCION')
        col_inv_cant = find_col(df_inv_raw, 'CANT')
        col_inv_costo = find_col(df_inv_raw, 'COSTO')
        col_inv_pvp = find_col(df_inv_raw, 'PVP')
        
        df_inv = df_inv_raw.copy()
        df_inv['Proveedor'] = df_inv[col_inv_prov].astype(str) if col_inv_prov else ''
        df_inv['Marca'] = df_inv[col_inv_marca].astype(str) if col_inv_marca else ''
        df_inv['Descripcion'] = df_inv[col_inv_desc].astype(str) if col_inv_desc else ''
        df_inv['Cantidad'] = pd.to_numeric(df_inv[col_inv_cant], errors='coerce').fillna(0) if col_inv_cant else 0
        df_inv['Costo'] = pd.to_numeric(df_inv[col_inv_costo], errors='coerce').fillna(0) if col_inv_costo else 0
        df_inv['PVP'] = pd.to_numeric(df_inv[col_inv_pvp], errors='coerce').fillna(0) if col_inv_pvp else 0
        
    except Exception:
        df_inv = pd.DataFrame()

    return df_v, df_inv

# ══════════════════════════════════════════════════════════════════
#  SISTEMA DE AUTENTICACIÓN
# ══════════════════════════════════════════════════════════════════

def es_super_admin_portal(usuario, password):
    """Verifica si es Israel (super admin)"""
    return usuario.upper() == "ISRAEL" and password == "2024"

def es_admin_portal(usuario, password):
    """Verifica si es admin general"""
    return usuario.upper() == "ADMIN" and password == "admin2024"

def autenticar_usuario(usuario, password, df_usuarios):
    """Autentica usuarios del portal"""
    
    # Super Admin Israel
    if es_super_admin_portal(usuario, password):
        return True, {
            "tipo": "super_admin",
            "usuario": "ISRAEL PAREDES",
            "nombre": "Israel",
            "proveedor": "",
            "marca": "",
            "acceso": "TOTAL"
        }
    
    # Admin general
    if es_admin_portal(usuario, password):
        return True, {
            "tipo": "admin",
            "usuario": "ADMINISTRADOR",
            "nombre": "Admin",
            "proveedor": "",
            "marca": "",
            "acceso": "GENERAL"
        }
    
    # Buscar en proveedores específicos
    for _, user in df_usuarios.iterrows():
        user_nombre = str(user.get('_nombre_orig', '')).upper()
        user_pin = str(user.get('_pin', ''))
        user_rol = str(user.get('_rol', '')).upper()
        
        # Verificar si es un proveedor
        if ('PROVEEDOR' in user_rol or 'MARCA' in user_rol) and user_nombre == usuario.upper() and user_pin == password:
            return True, {
                "tipo": "proveedor",
                "usuario": user.get('_nombre_orig', usuario),
                "nombre": usuario,
                "proveedor": user.get('_proveedor', ''),
                "marca": user.get('_marca', ''),
                "acceso": "FILTRADO"
            }
    
    return False, None

# ══════════════════════════════════════════════════════════════════
#  FILTROS DE DATOS SEGÚN USUARIO
# ══════════════════════════════════════════════════════════════════

def filtrar_datos_por_usuario(df_ventas, df_inventario, user_info):
    """Filtra datos según el tipo de usuario"""
    
    if user_info['tipo'] in ['super_admin', 'admin']:
        # Israel y Admin ven todo
        return df_ventas, df_inventario
    
    elif user_info['tipo'] == 'proveedor':
        # Filtrar por proveedor o marca específica
        proveedor = user_info.get('proveedor', '')
        marca = user_info.get('marca', '')
        
        # Filtro en ventas
        df_v_filtrado = df_ventas.copy()
        if marca and marca.strip():
            # Filtrar por marca específica
            df_v_filtrado = df_v_filtrado[df_v_filtrado['Marca'].str.contains(marca, case=False, na=False)]
        elif proveedor and proveedor.strip():
            # Filtrar por proveedor
            df_v_filtrado = df_v_filtrado[df_v_filtrado['Proveedor'].str.contains(proveedor, case=False, na=False)]
        
        # Filtro en inventario
        df_i_filtrado = df_inventario.copy()
        if marca and marca.strip():
            df_i_filtrado = df_i_filtrado[df_i_filtrado['Marca'].str.contains(marca, case=False, na=False)]
        elif proveedor and proveedor.strip():
            df_i_filtrado = df_i_filtrado[df_i_filtrado['Proveedor'].str.contains(proveedor, case=False, na=False)]
        
        return df_v_filtrado, df_i_filtrado
    
    return pd.DataFrame(), pd.DataFrame()

# ══════════════════════════════════════════════════════════════════
#  ANÁLISIS Y MÉTRICAS
# ══════════════════════════════════════════════════════════════════

def calcular_metricas_proveedor(df_ventas, mes_seleccionado):
    """Calcula métricas del proveedor para el mes seleccionado"""
    
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
            'crecimiento': 0
        }
    
    # Métricas básicas
    total_ventas = df_mes['Total'].sum()
    total_facturas = len(df_mes)
    clientes_unicos = df_mes['Cliente'].nunique()
    vendedores_activos = df_mes[df_mes['Total'] > 0]['Vendedor'].nunique()
    
    # Top productos y vendedores
    top_productos = df_mes.groupby('Marca')['Total'].sum().nlargest(5)
    top_vendedores = df_mes.groupby('Vendedor')['Total'].sum().nlargest(5)
    
    # Calcular crecimiento (mes anterior)
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
        'crecimiento': round(crecimiento, 1)
    }

def generar_sugerido_compra(df_inventario, df_ventas):
    """Genera sugerido de compra basado en rotación"""
    
    if df_inventario.empty or df_ventas.empty:
        return pd.DataFrame()
    
    try:
        # Ventas últimos 90 días
        fecha_limite = datetime.now() - pd.Timedelta(days=90)
        df_ventas_recientes = df_ventas[df_ventas['Fecha'] >= fecha_limite]
        
        # Agrupar por producto (usar Marca como identificador)
        rotacion = df_ventas_recientes.groupby('Marca').agg({
            'Total': 'sum',
            'Fecha': 'count'
        }).rename(columns={'Fecha': 'Transacciones'}).reset_index()
        
        # Merge con inventario
        df_sugerido = df_inventario.merge(rotacion, left_on='Marca', right_on='Marca', how='left').fillna(0)
        
        # Calcular sugeridos
        df_sugerido['Rotacion_Mensual'] = df_sugerido['Total'] / 3  # Promedio mensual
        df_sugerido['Stock_Sugerido'] = df_sugerido['Rotacion_Mensual'] * 1.5  # 1.5 meses de stock
        df_sugerido['Diferencia'] = df_sugerido['Stock_Sugerido'] - df_sugerido['Cantidad']
        df_sugerido['Sugerido_Compra'] = df_sugerido['Diferencia'].apply(lambda x: max(0, x))
        df_sugerido['Valor_Compra'] = df_sugerido['Sugerido_Compra'] * df_sugerido['Costo']
        
        # Filtrar solo productos que necesitan reposición
        df_sugerido = df_sugerido[df_sugerido['Sugerido_Compra'] > 0]
        
        return df_sugerido.sort_values('Valor_Compra', ascending=False).head(20)
    
    except Exception as e:
        st.error(f"Error calculando sugerido: {e}")
        return pd.DataFrame()

# ══════════════════════════════════════════════════════════════════
#  INTERFAZ DE USUARIO
# ══════════════════════════════════════════════════════════════════

# Estilos CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Syne:wght@700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: #2D3748;
}

.main {
    background: rgba(255, 255, 255, 0.95);
    border-radius: 20px;
    padding: 2rem;
    margin: 1rem;
    backdrop-filter: blur(10px);
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
}

.header-portal {
    background: linear-gradient(135deg, #4F46E5, #7C3AED);
    color: white;
    padding: 2rem;
    border-radius: 15px;
    margin-bottom: 2rem;
    text-align: center;
    box-shadow: 0 10px 25px rgba(79, 70, 229, 0.3);
}

.login-container {
    max-width: 400px;
    margin: 0 auto;
    background: rgba(255, 255, 255, 0.9);
    padding: 3rem;
    border-radius: 20px;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
    text-align: center;
}

.stButton > button {
    background: linear-gradient(135deg, #4F46E5, #7C3AED) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.75rem 2rem !important;
    font-weight: 600 !important;
    width: 100% !important;
}

.top-vendor-card {
    background: linear-gradient(135deg, #10B981, #059669);
    color: white;
    padding: 1rem;
    border-radius: 10px;
    margin: 0.5rem 0;
}

.alert-card {
    background: linear-gradient(135deg, #F59E0B, #D97706);
    color: white;
    padding: 1rem;
    border-radius: 10px;
    margin: 0.5rem 0;
}
</style>
""", unsafe_allow_html=True)

def pantalla_login():
    """Pantalla de login para proveedores"""
    
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    st.markdown("""
    <div style='text-align: center; margin-bottom: 2rem;'>
        <h1 style='color: #4F46E5; margin-bottom: 0.5rem;'>🏢 Portal Proveedores</h1>
        <p style='color: #64748B; font-size: 1.1rem;'>SOLUTO - Acceso Exclusivo</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Cargar usuarios para autenticación
    df_usuarios = cargar_usuarios_proveedores()
    
    with st.form("login_form"):
        usuario = st.text_input("👤 Usuario:", placeholder="Ingresa tu nombre de usuario")
        password = st.text_input("🔐 Contraseña:", type="password", placeholder="Ingresa tu contraseña")
        submit = st.form_submit_button("🚀 Ingresar", use_container_width=True)
        
        if submit:
            if not usuario or not password:
                st.error("❌ Por favor completa todos los campos")
                return
            
            success, user_info = autenticar_usuario(usuario, password, df_usuarios)
            
            if success:
                st.session_state.update({
                    'authenticated': True,
                    'user_info': user_info
                })
                st.success("✅ Login exitoso")
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Información de acceso
    with st.expander("ℹ️ Información de Acceso"):
        st.markdown("""
        **🔐 Tipos de Usuario:**
        - **Super Admin:** `ISRAEL` / `2024`
        - **Administrador:** `ADMIN` / `admin2024`
        - **Proveedores:** Credenciales específicas (configuradas en Usuario_Roles)
        
        **📧 Contacto:**
        Para obtener credenciales de proveedor, contacta al administrador del sistema.
        """)

def dashboard_proveedor():
    """Dashboard principal para proveedores"""
    
    user_info = st.session_state['user_info']
    
    # Header
    st.markdown(f"""
    <div class="header-portal">
        <h1>🏢 Portal {user_info['tipo'].title().replace('_', ' ')}</h1>
        <h2>Bienvenido, {user_info['usuario']}</h2>
        <p style="opacity: 0.9;">
            {f"Proveedor: {user_info['proveedor']}" if user_info['proveedor'] else "Acceso " + user_info['acceso']}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown(f"""
        **👤 Sesión Activa:**
        - Usuario: {user_info['usuario']}
        - Tipo: {user_info['tipo'].title().replace('_', ' ')}
        - Acceso: {user_info['acceso']}
        """)
        
        if user_info.get('proveedor'):
            st.markdown(f"- Proveedor: {user_info['proveedor']}")
        if user_info.get('marca'):
            st.markdown(f"- Marca: {user_info['marca']}")
        
        if st.button("🚪 Cerrar Sesión"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    # Cargar datos
    with st.spinner("Cargando datos..."):
        df_ventas, df_inventario = cargar_ventas_inventario()
        
        if df_ventas.empty:
            st.error("❌ No se pudieron cargar los datos de ventas")
            return
    
    # Filtrar datos según usuario
    df_v_filtrado, df_i_filtrado = filtrar_datos_por_usuario(df_ventas, df_inventario, user_info)
    
    # Controles
    col_mes, col_filtro = st.columns([2, 1])
    
    with col_mes:
        # Selector de mes
        if not df_v_filtrado.empty:
            df_v_filtrado['Mes_Año'] = df_v_filtrado['Fecha'].dt.strftime('%B %Y')
            meses_disponibles = sorted(df_v_filtrado['Mes_Año'].dropna().unique(), reverse=True)
            
            if meses_disponibles:
                mes_seleccionado = st.selectbox("📅 Seleccionar Período:", meses_disponibles)
            else:
                st.warning("No hay datos disponibles")
                return
        else:
            st.warning("No hay datos disponibles para este usuario")
            return
    
    with col_filtro:
        # Filtro adicional para admins
        if user_info['tipo'] in ['super_admin', 'admin']:
            proveedores = ['TODOS'] + sorted(df_ventas['Proveedor'].dropna().unique().tolist())
            proveedor_filtro = st.selectbox("🏢 Filtrar Proveedor:", proveedores)
            
            if proveedor_filtro != 'TODOS':
                df_v_filtrado = df_v_filtrado[df_v_filtrado['Proveedor'].str.contains(proveedor_filtro, case=False, na=False)]
                df_i_filtrado = df_i_filtrado[df_i_filtrado['Proveedor'].str.contains(proveedor_filtro, case=False, na=False)]
    
    # Generar métricas
    metricas = calcular_metricas_proveedor(df_v_filtrado, mes_seleccionado)
    
    # Mostrar métricas principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        delta_color = "normal" if metricas['crecimiento'] >= 0 else "inverse"
        st.metric(
            "💰 Ventas Totales",
            f"${metricas['total_ventas']:,.0f}",
            delta=f"{metricas['crecimiento']:+.1f}%",
            delta_color=delta_color
        )
    
    with col2:
        st.metric("📄 Facturas", f"{metricas['total_facturas']:,}")
    
    with col3:
        st.metric("👥 Clientes Únicos", f"{metricas['clientes_unicos']:,}")
    
    with col4:
        st.metric("🏪 Vendedores Activos", f"{metricas['vendedores_activos']:,}")
    
    st.markdown("---")
    
    # Tabs principales
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Análisis", "🏪 Top Vendedores", "📦 Inventario", "🛒 Sugerido Compra"])
    
    with tab1:
        # Gráficos de análisis
        col_left, col_right = st.columns(2)
        
        with col_left:
            # Ventas por marca
            if not metricas['top_productos'].empty:
                fig_marca = go.Figure(data=[
                    go.Pie(labels=metricas['top_productos'].index, values=metricas['top_productos'].values, hole=0.4)
                ])
                fig_marca.update_layout(
                    title="🏷️ Ventas por Marca",
                    template="plotly_white",
                    height=400
                )
                st.plotly_chart(fig_marca, use_container_width=True)
            else:
                st.info("📝 Sin datos de productos para mostrar")
        
        with col_right:
            # Tendencia mensual
            if not df_v_filtrado.empty:
                try:
                    tendencia = df_v_filtrado.groupby(df_v_filtrado['Fecha'].dt.to_period('M'))['Total'].sum().reset_index()
                    tendencia['Fecha_str'] = tendencia['Fecha'].dt.strftime('%B %Y')
                    
                    fig_trend = go.Figure(data=[
                        go.Scatter(x=tendencia['Fecha_str'], y=tendencia['Total'], mode='lines+markers', line_color='#4F46E5')
                    ])
                    fig_trend.update_layout(
                        title="📈 Tendencia de Ventas",
                        template="plotly_white",
                        height=400,
                        xaxis_title="Mes",
                        yaxis_title="Ventas ($)"
                    )
                    st.plotly_chart(fig_trend, use_container_width=True)
                except Exception:
                    st.info("📝 Sin datos suficientes para mostrar tendencia")
            else:
                st.info("📝 Sin datos para mostrar tendencia")
    
    with tab2:
        # Top vendedores
        st.markdown("### 🏆 Ranking de Vendedores")
        
        if not metricas['top_vendedores'].empty:
            for i, (vendedor, venta) in enumerate(metricas['top_vendedores'].items(), 1):
                # Extraer solo el nombre del vendedor
                nombre = vendedor.split(' - ')[1] if ' - ' in vendedor else vendedor
                nombre_corto = nombre[:30] + "..." if len(nombre) > 30 else nombre
                
                emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                
                st.markdown(f"""
                <div class="top-vendor-card">
                    <h4>{emoji} {nombre_corto}</h4>
                    <p style="font-size: 1.2rem; margin: 0;"><strong>${venta:,.0f}</strong></p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("📝 Sin datos de vendedores para el período seleccionado")
    
    with tab3:
        # Inventario
        st.markdown("### 📦 Estado del Inventario")
        
        if not df_i_filtrado.empty:
            # Métricas de inventario
            total_productos = len(df_i_filtrado)
            valor_inventario = (df_i_filtrado['Cantidad'] * df_i_filtrado['Costo']).sum()
            productos_agotados = len(df_i_filtrado[df_i_filtrado['Cantidad'] <= 0])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📦 Total Productos", f"{total_productos:,}")
            with col2:
                st.metric("💰 Valor Inventario", f"${valor_inventario:,.0f}")
            with col3:
                st.metric("⚠️ Productos Agotados", f"{productos_agotados:,}")
            
            # Tabla de inventario
            st.markdown("#### 📋 Detalle de Inventario")
            df_inv_display = df_i_filtrado[['Marca', 'Descripcion', 'Cantidad', 'Costo', 'PVP']].copy()
            df_inv_display['Valor Total'] = df_inv_display['Cantidad'] * df_inv_display['Costo']
            st.dataframe(df_inv_display, use_container_width=True, height=350)
        else:
            st.info("📝 Sin datos de inventario disponibles")
    
    with tab4:
        # Sugerido de compra
        st.markdown("### 🛒 Sugerido de Compra")
        
        df_sugerido = generar_sugerido_compra(df_i_filtrado, df_v_filtrado)
        
        if not df_sugerido.empty:
            # Resumen del sugerido
            total_sugerido = df_sugerido['Valor_Compra'].sum()
            productos_sugeridos = len(df_sugerido)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("💸 Valor Total Sugerido", f"${total_sugerido:,.0f}")
            with col2:
                st.metric("📦 Productos a Reponer", f"{productos_sugeridos:,}")
            
            # Tabla de sugeridos
            st.markdown("#### 📋 Lista de Reposición")
            df_display = df_sugerido[['Marca', 'Descripcion', 'Cantidad', 'Sugerido_Compra', 'Costo', 'Valor_Compra']].copy()
            df_display.columns = ['Marca', 'Producto', 'Stock Actual', 'Cantidad Sugerida', 'Costo Unit.', 'Valor Total']
            
            st.dataframe(df_display, use_container_width=True, height=400)
            
            # Alertas de productos críticos
            productos_criticos = df_sugerido[df_sugerido['Cantidad'] <= 0]
            if not productos_criticos.empty:
                st.markdown(f"""
                <div class="alert-card">
                    <h4>⚠️ PRODUCTOS AGOTADOS</h4>
                    <p>{len(productos_criticos)} productos sin stock requieren reposición urgente</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("✅ No hay productos que requieran reposición según la rotación actual")

# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    """Función principal"""
    
    if not st.session_state.get('authenticated', False):
        pantalla_login()
    else:
        dashboard_proveedor()

if __name__ == "__main__":
    main()
