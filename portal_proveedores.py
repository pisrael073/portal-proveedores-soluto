import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import calendar
import re
import unicodedata

# Importaciones opcionales con fallbacks
try:
    import plotly.graph_objects as go
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    st.warning("⚠️ Plotly no disponible - gráficos deshabilitados")

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

# ══════════════════════════════════════════════════════════════════
#  CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Portal Proveedores - SOLUTO",
    layout="wide",
    page_icon="🏢",
    initial_sidebar_state="expanded"
)

# Estilos CSS para el portal de proveedores
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
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

.metric-card {
    background: linear-gradient(145deg, #ffffff, #f8fafc);
    border: 1px solid #e2e8f0;
    border-radius: 15px;
    padding: 1.5rem;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    transition: transform 0.3s ease;
}

.metric-card:hover {
    transform: translateY(-5px);
}

.metric-value {
    font-size: 2.5rem;
    font-weight: 700;
    color: #4F46E5;
    margin-bottom: 0.5rem;
}

.metric-label {
    font-size: 0.875rem;
    color: #64748B;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.login-container {
    max-width: 400px;
    margin: 0 auto;
    background: rgba(255, 255, 255, 0.9);
    padding: 3rem;
    border-radius: 20px;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
}

.stButton > button {
    background: linear-gradient(135deg, #4F46E5, #7C3AED);
    color: white;
    border: none;
    border-radius: 10px;
    padding: 0.75rem 2rem;
    font-weight: 600;
    transition: all 0.3s ease;
}

.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 25px rgba(79, 70, 229, 0.4);
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

# ══════════════════════════════════════════════════════════════════
#  CONEXIÓN GOOGLE SHEETS
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
            st.stop()
    
    return gspread.authorize(creds)

@st.cache_data(ttl=180)
def cargar_datos_proveedor():
    """Carga datos de ventas, inventario y usuarios"""
    try:
        gc = get_gc()
        sheet = gc.open("soluto").worksheet("VENTAS")
        data = sheet.get_all_records()
        df_ventas = pd.DataFrame(data)
        
        # Procesar fechas
        df_ventas['Fecha'] = pd.to_datetime(df_ventas['Fecha'], errors='coerce')
        df_ventas['Total'] = pd.to_numeric(df_ventas['Total'], errors='coerce').fillna(0)
        df_ventas['Costo'] = pd.to_numeric(df_ventas['Costo'], errors='coerce').fillna(0)
        
        # Cargar inventario
        inv_sheet = gc.open("soluto").worksheet("INVENTARIO")
        inv_data = inv_sheet.get_all_records()
        df_inventario = pd.DataFrame(inv_data)
        
        # Procesar inventario
        df_inventario['Cant.'] = pd.to_numeric(df_inventario['Cant.'], errors='coerce').fillna(0)
        df_inventario['Costo'] = pd.to_numeric(df_inventario['Costo'], errors='coerce').fillna(0)
        df_inventario['PVP'] = pd.to_numeric(df_inventario['PVP'], errors='coerce').fillna(0)
        
        # Cargar usuarios
        user_sheet = gc.open("soluto").worksheet("Usuarios")
        user_data = user_sheet.get_all_records()
        df_usuarios = pd.DataFrame(user_data)
        
        return df_ventas, df_inventario, df_usuarios
    
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# ══════════════════════════════════════════════════════════════════
#  AUTENTICACIÓN
# ══════════════════════════════════════════════════════════════════

def autenticar_proveedor(usuario, password, df_usuarios):
    """Autentica proveedores y administradores"""
    
    # Super Admin Israel
    if usuario.upper() == "ISRAEL" and password == "2024":
        return True, {"tipo": "super_admin", "usuario": "ISRAEL PAREDES", "proveedor": "SUPER_ADMIN"}
    
    # Admin general
    if usuario.upper() == "ADMIN" and password == "admin2024":
        return True, {"tipo": "admin", "usuario": "ADMINISTRADOR", "proveedor": "ADMIN"}
    
    # Buscar en usuarios específicos (proveedores)
    for _, user in df_usuarios.iterrows():
        if (str(user.get('usuario', '')).upper() == usuario.upper() and 
            str(user.get('password', '')) == password):
            return True, {
                "tipo": "proveedor",
                "usuario": user.get('nombre', usuario),
                "proveedor": user.get('proveedor', ''),
                "marca": user.get('marca', '')
            }
    
    return False, None

# ══════════════════════════════════════════════════════════════════
#  ANÁLISIS DE DATOS
# ══════════════════════════════════════════════════════════════════

def filtrar_datos_proveedor(df_ventas, df_inventario, user_info):
    """Filtra datos según el tipo de usuario"""
    
    if user_info['tipo'] == 'super_admin':
        # Israel ve todo
        return df_ventas, df_inventario
    
    elif user_info['tipo'] == 'admin':
        # Admin ve todo pero puede filtrar
        return df_ventas, df_inventario
    
    elif user_info['tipo'] == 'proveedor':
        # Filtrar por proveedor específico
        proveedor = user_info['proveedor']
        marca = user_info.get('marca', '')
        
        if marca and marca != '':
            # Si tiene marca específica, filtrar por marca
            df_v_filtrado = df_ventas[df_ventas['Marca'].str.contains(marca, case=False, na=False)]
            df_i_filtrado = df_inventario[df_inventario['Marca'].str.contains(marca, case=False, na=False)]
        else:
            # Filtrar por proveedor
            df_v_filtrado = df_ventas[df_ventas['Proveedor'].str.contains(proveedor, case=False, na=False)]
            df_i_filtrado = df_inventario[df_inventario['Proveedor'].str.contains(proveedor, case=False, na=False)]
        
        return df_v_filtrado, df_i_filtrado
    
    return pd.DataFrame(), pd.DataFrame()

def generar_metricas_proveedor(df_ventas, mes_actual):
    """Genera métricas específicas del proveedor"""
    
    # Filtrar por mes actual
    df_mes = df_ventas[df_ventas['Fecha'].dt.strftime('%B %Y') == mes_actual]
    
    # Métricas básicas
    total_ventas = df_mes['Total'].sum()
    total_facturas = len(df_mes)
    clientes_unicos = df_mes['Cliente'].nunique()
    vendedores_activos = df_mes[df_mes['Total'] > 0]['Vendedor'].nunique()
    
    # Mes anterior para comparación
    fecha_actual = datetime.now()
    if fecha_actual.month == 1:
        mes_anterior = f"{calendar.month_name[12]} {fecha_actual.year - 1}"
    else:
        mes_anterior = f"{calendar.month_name[fecha_actual.month - 1]} {fecha_actual.year}"
    
    df_anterior = df_ventas[df_ventas['Fecha'].dt.strftime('%B %Y') == mes_anterior]
    ventas_anterior = df_anterior['Total'].sum()
    
    # Calcular crecimiento
    if ventas_anterior > 0:
        crecimiento = round(((total_ventas - ventas_anterior) / ventas_anterior) * 100, 1)
    else:
        crecimiento = 0
    
    # Top productos
    top_productos = df_mes.groupby(['Descripcion', 'Marca'])['Total'].sum().nlargest(5)
    
    # Top vendedores
    top_vendedores = df_mes.groupby('Vendedor')['Total'].sum().nlargest(5)
    
    return {
        'total_ventas': total_ventas,
        'total_facturas': total_facturas,
        'clientes_unicos': clientes_unicos,
        'vendedores_activos': vendedores_activos,
        'crecimiento': crecimiento,
        'top_productos': top_productos,
        'top_vendedores': top_vendedores,
        'ventas_anterior': ventas_anterior
    }

def generar_sugerido_compra(df_inventario, df_ventas, user_info):
    """Genera sugerido de compra basado en rotación y stock"""
    
    if df_inventario.empty or df_ventas.empty:
        return pd.DataFrame()
    
    # Calcular rotación de productos (últimos 3 meses)
    fecha_limite = datetime.now() - pd.Timedelta(days=90)
    df_ventas_recientes = df_ventas[df_ventas['Fecha'] >= fecha_limite]
    
    # Agrupar ventas por producto
    rotacion = df_ventas_recientes.groupby(['Codigo', 'Descripcion']).agg({
        'Cantidad': 'sum',
        'Total': 'sum'
    }).reset_index()
    
    # Merge con inventario
    df_sugerido = df_inventario.merge(
        rotacion, on=['Codigo', 'Descripcion'], how='left'
    ).fillna(0)
    
    # Calcular sugeridos
    df_sugerido['Rotacion_Mensual'] = df_sugerido['Cantidad'] / 3  # Promedio mensual
    df_sugerido['Stock_Sugerido'] = df_sugerido['Rotacion_Mensual'] * 2  # 2 meses de stock
    df_sugerido['Diferencia'] = df_sugerido['Stock_Sugerido'] - df_sugerido['Cant.']
    df_sugerido['Sugerido_Compra'] = df_sugerido['Diferencia'].apply(lambda x: max(0, x))
    
    # Filtrar productos que necesitan reposición
    df_sugerido = df_sugerido[df_sugerido['Sugerido_Compra'] > 0]
    
    # Calcular valor de compra sugerida
    df_sugerido['Valor_Compra'] = df_sugerido['Sugerido_Compra'] * df_sugerido['Costo']
    
    return df_sugerido.sort_values('Valor_Compra', ascending=False)

# ══════════════════════════════════════════════════════════════════
#  INTERFACE PRINCIPAL
# ══════════════════════════════════════════════════════════════════

def pantalla_login():
    """Pantalla de login para proveedores"""
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    st.markdown("""
    <div style='text-align: center; margin-bottom: 2rem;'>
        <h1 style='color: #4F46E5; margin-bottom: 0.5rem;'>🏢 Portal Proveedores</h1>
        <p style='color: #64748B; font-size: 1.1rem;'>SOLUTO - Acceso Exclusivo</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("login_form"):
        usuario = st.text_input("👤 Usuario:", placeholder="Ingresa tu usuario")
        password = st.text_input("🔐 Contraseña:", type="password", placeholder="Ingresa tu contraseña")
        submit = st.form_submit_button("🚀 Ingresar", use_container_width=True)
        
        if submit:
            if not usuario or not password:
                st.error("❌ Por favor completa todos los campos")
                return
            
            # Cargar datos para autenticación
            _, _, df_usuarios = cargar_datos_proveedor()
            
            success, user_info = autenticar_proveedor(usuario, password, df_usuarios)
            
            if success:
                st.session_state['authenticated'] = True
                st.session_state['user_info'] = user_info
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
        - **Proveedores:** Credenciales específicas por proveedor
        
        **📧 Contacto:**
        Para obtener credenciales de acceso, contacta al administrador del sistema.
        """)

def dashboard_principal():
    """Dashboard principal del portal"""
    user_info = st.session_state['user_info']
    
    # Header
    st.markdown(f"""
    <div class="header-portal">
        <h1>🏢 Portal {user_info['tipo'].title().replace('_', ' ')}</h1>
        <h2>Bienvenido, {user_info['usuario']}</h2>
        <p style="opacity: 0.9;">
            {f"Proveedor: {user_info['proveedor']}" if user_info['tipo'] == 'proveedor' else "Acceso Completo al Sistema"}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown(f"""
        **👤 Sesión Activa:**
        - Usuario: {user_info['usuario']}
        - Tipo: {user_info['tipo'].title().replace('_', ' ')}
        """)
        
        if user_info['tipo'] == 'proveedor':
            st.markdown(f"- Proveedor: {user_info['proveedor']}")
            if user_info.get('marca'):
                st.markdown(f"- Marca: {user_info['marca']}")
        
        if st.button("🚪 Cerrar Sesión"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    # Cargar datos
    df_ventas, df_inventario, df_usuarios = cargar_datos_proveedor()
    
    if df_ventas.empty:
        st.error("❌ No se pudieron cargar los datos")
        return
    
    # Filtrar datos según usuario
    df_v_filtrado, df_i_filtrado = filtrar_datos_proveedor(df_ventas, df_inventario, user_info)
    
    # Filtros
    col_mes, col_filtro = st.columns([2, 1])
    
    with col_mes:
        # Selector de mes
        df_v_filtrado['Mes_Año'] = df_v_filtrado['Fecha'].dt.strftime('%B %Y')
        meses_disponibles = sorted(df_v_filtrado['Mes_Año'].dropna().unique(), reverse=True)
        mes_seleccionado = st.selectbox("📅 Seleccionar Período:", meses_disponibles)
    
    with col_filtro:
        # Filtro adicional para admins
        if user_info['tipo'] in ['super_admin', 'admin']:
            proveedores = ['TODOS'] + sorted(df_ventas['Proveedor'].dropna().unique().tolist())
            proveedor_filtro = st.selectbox("🏢 Filtrar Proveedor:", proveedores)
            
            if proveedor_filtro != 'TODOS':
                df_v_filtrado = df_v_filtrado[df_v_filtrado['Proveedor'] == proveedor_filtro]
                df_i_filtrado = df_i_filtrado[df_i_filtrado['Proveedor'] == proveedor_filtro]
    
    # Generar métricas
    metricas = generar_metricas_proveedor(df_v_filtrado, mes_seleccionado)
    
    # Mostrar métricas principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        delta_ventas = f"+{metricas['crecimiento']}%" if metricas['crecimiento'] > 0 else f"{metricas['crecimiento']}%"
        st.metric(
            "💰 Ventas Totales",
            f"${metricas['total_ventas']:,.0f}",
            delta=delta_ventas
        )
    
    with col2:
        st.metric(
            "📄 Facturas",
            f"{metricas['total_facturas']:,}"
        )
    
    with col3:
        st.metric(
            "👥 Clientes Únicos",
            f"{metricas['clientes_unicos']:,}"
        )
    
    with col4:
        st.metric(
            "🏪 Vendedores Activos",
            f"{metricas['vendedores_activos']:,}"
        )
    
    st.markdown("---")
    
    # Tabs principales
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Análisis", "🏪 Top Vendedores", "📦 Inventario", "🛒 Sugerido Compra"])
    
    with tab1:
        # Gráficos de análisis
        col_left, col_right = st.columns(2)
        
        with col_left:
            # Ventas por marca
            if not df_v_filtrado.empty and PLOTLY_AVAILABLE:
                ventas_marca = df_v_filtrado[df_v_filtrado['Fecha'].dt.strftime('%B %Y') == mes_seleccionado].groupby('Marca')['Total'].sum().nlargest(8)
                
                fig_marca = go.Figure(data=[
                    go.Pie(labels=ventas_marca.index, values=ventas_marca.values, hole=0.4)
                ])
                fig_marca.update_layout(
                    title="🏷️ Ventas por Marca",
                    template="plotly_white",
                    height=400
                )
                st.plotly_chart(fig_marca, use_container_width=True)
            elif not df_v_filtrado.empty:
                # Fallback sin Plotly
                st.markdown("### 🏷️ Ventas por Marca")
                ventas_marca = df_v_filtrado[df_v_filtrado['Fecha'].dt.strftime('%B %Y') == mes_seleccionado].groupby('Marca')['Total'].sum().nlargest(8)
                for marca, valor in ventas_marca.items():
                    st.write(f"**{marca}:** ${valor:,.0f}")
            else:
                st.info("📝 Sin datos de ventas para mostrar")
        
        with col_right:
            # Tendencia mensual
            if len(df_v_filtrado) > 0 and PLOTLY_AVAILABLE:
                tendencia = df_v_filtrado.groupby(df_v_filtrado['Fecha'].dt.to_period('M'))['Total'].sum().reset_index()
                tendencia['Fecha'] = tendencia['Fecha'].dt.strftime('%B %Y')
                
                fig_trend = go.Figure(data=[
                    go.Scatter(x=tendencia['Fecha'], y=tendencia['Total'], mode='lines+markers', line_color='#4F46E5')
                ])
                fig_trend.update_layout(
                    title="📈 Tendencia de Ventas",
                    template="plotly_white",
                    height=400,
                    xaxis_title="Mes",
                    yaxis_title="Ventas ($)"
                )
                st.plotly_chart(fig_trend, use_container_width=True)
            elif len(df_v_filtrado) > 0:
                # Fallback sin Plotly
                st.markdown("### 📈 Tendencia de Ventas")
                tendencia = df_v_filtrado.groupby(df_v_filtrado['Fecha'].dt.to_period('M'))['Total'].sum()
                st.line_chart(tendencia)
            else:
                st.info("📝 Sin datos para mostrar tendencia")
    
    with tab2:
        # Top vendedores
        st.markdown("### 🏆 Ranking de Vendedores")
        
        if not metricas['top_vendedores'].empty:
            for i, (vendedor, venta) in enumerate(metricas['top_vendedores'].items(), 1):
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
            valor_inventario = (df_i_filtrado['Cant.'] * df_i_filtrado['Costo']).sum()
            productos_agotados = len(df_i_filtrado[df_i_filtrado['Cant.'] <= 0])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📦 Total Productos", f"{total_productos:,}")
            with col2:
                st.metric("💰 Valor Inventario", f"${valor_inventario:,.0f}")
            with col3:
                st.metric("⚠️ Productos Agotados", f"{productos_agotados:,}")
            
            # Tabla de inventario
            st.markdown("#### 📋 Detalle de Inventario")
            df_inv_display = df_i_filtrado[['Marca', 'Descripcion', 'Cant.', 'Costo', 'PVP']].copy()
            df_inv_display['Valor Total'] = df_inv_display['Cant.'] * df_inv_display['Costo']
            st.dataframe(df_inv_display, use_container_width=True, height=350)
        else:
            st.info("📝 Sin datos de inventario disponibles")
    
    with tab4:
        # Sugerido de compra
        st.markdown("### 🛒 Sugerido de Compra")
        
        df_sugerido = generar_sugerido_compra(df_i_filtrado, df_v_filtrado, user_info)
        
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
            df_display = df_sugerido[['Marca', 'Descripcion', 'Cant.', 'Sugerido_Compra', 'Costo', 'Valor_Compra']].copy()
            df_display.columns = ['Marca', 'Producto', 'Stock Actual', 'Cantidad Sugerida', 'Costo Unit.', 'Valor Total']
            
            st.dataframe(df_display, use_container_width=True, height=400)
            
            # Alerta de productos críticos
            productos_criticos = df_sugerido[df_sugerido['Cant.'] <= 0]
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
    if not st.session_state.get('authenticated', False):
        pantalla_login()
    else:
        dashboard_principal()

if __name__ == "__main__":
    main()
