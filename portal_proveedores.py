import streamlit as st
import pandas as pd
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
#  DATOS DE DEMO
# ══════════════════════════════════════════════════════════════════

def cargar_datos_demo():
    """Carga datos de demostración"""
    
    # Usuarios de demo
    usuarios = [
        {"nombre": "ISRAEL", "pin": "2024", "rol": "SUPER_ADMIN", "proveedor": "", "marca": ""},
        {"nombre": "ADMIN", "pin": "admin2024", "rol": "ADMIN", "proveedor": "", "marca": ""},
        {"nombre": "KAAPANY", "pin": "kaa2024", "rol": "PROVEEDOR", "proveedor": "KAAPAANY PDV S.A.S", "marca": "KAAPANY"},
        {"nombre": "NESTLE", "pin": "nes2024", "rol": "PROVEEDOR", "proveedor": "NESTLE", "marca": "NESTLE"},
        {"nombre": "UNILEVER", "pin": "uni2024", "rol": "PROVEEDOR", "proveedor": "UNILEVER", "marca": "UNILEVER"},
    ]
    
    # Ventas de demo
    vendedores = ["PDV01 - CARLOS MENDEZ", "PDV02 - MARIA LOPEZ", "PDV03 - LUIS GARCIA", 
                  "PDV04 - ANA TORRES", "PDV05 - JOSE RIVERA"]
    marcas = ["KAAPANY", "NESTLE", "UNILEVER", "COLGATE", "PEPSI"]
    proveedores = ["KAAPAANY PDV S.A.S", "NESTLE", "UNILEVER", "COLGATE PALMOLIVE", "PEPSI"]
    clientes = ["CLIENTE A", "CLIENTE B", "CLIENTE C", "CLIENTE D", "CLIENTE E", 
                "CLIENTE F", "CLIENTE G", "CLIENTE H", "CLIENTE I", "CLIENTE J"]
    
    ventas_data = []
    for i in range(500):  # 500 registros de ejemplo
        fecha = datetime.now() - pd.Timedelta(days=i%60)  # Últimos 60 días
        ventas_data.append({
            'Fecha': fecha,
            'Vendedor': vendedores[i % len(vendedores)],
            'Cliente': clientes[i % len(clientes)],
            'Marca': marcas[i % len(marcas)],
            'Proveedor': proveedores[i % len(proveedores)],
            'Total': round((i + 1) * 150 + (i % 10) * 50, 0),
            'Costo': round((i + 1) * 100 + (i % 8) * 30, 0)
        })
    
    # Inventario de demo
    inventario_data = []
    productos = ["PRODUCTO A", "PRODUCTO B", "PRODUCTO C", "PRODUCTO D", "PRODUCTO E"]
    
    for i, marca in enumerate(marcas):
        for j, producto in enumerate(productos):
            inventario_data.append({
                'Marca': marca,
                'Proveedor': proveedores[i % len(proveedores)],
                'Descripcion': f"{marca} {producto}",
                'Cantidad': (i + 1) * (j + 1) * 10,
                'Costo': 25 + (i * 5) + (j * 3),
                'PVP': 35 + (i * 7) + (j * 4)
            })
    
    return pd.DataFrame(usuarios), pd.DataFrame(ventas_data), pd.DataFrame(inventario_data)

# ══════════════════════════════════════════════════════════════════
#  FUNCIONES AUXILIARES
# ══════════════════════════════════════════════════════════════════

def norm_txt(v):
    """Normaliza texto"""
    s = str(v).strip().upper()
    s = ''.join(c for c in unicodedata.normalize('NFD', s)
                if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', s)

# ══════════════════════════════════════════════════════════════════
#  AUTENTICACIÓN
# ══════════════════════════════════════════════════════════════════

def autenticar_usuario(usuario, password, df_usuarios):
    """Autentica usuarios"""
    
    for _, user in df_usuarios.iterrows():
        if user['nombre'].upper() == usuario.upper() and str(user['pin']) == password:
            return True, {
                "tipo": user['rol'].lower(),
                "usuario": user['nombre'],
                "proveedor": user['proveedor'],
                "marca": user['marca'],
                "acceso": "DEMO"
            }
    
    return False, None

def filtrar_datos_por_usuario(df_ventas, df_inventario, user_info):
    """Filtra datos según usuario"""
    
    if user_info['tipo'] in ['super_admin', 'admin']:
        return df_ventas, df_inventario
    
    elif user_info['tipo'] == 'proveedor':
        proveedor = user_info.get('proveedor', '')
        marca = user_info.get('marca', '')
        
        # Filtrar por marca o proveedor
        if marca:
            df_v_filtrado = df_ventas[df_ventas['Marca'] == marca]
            df_i_filtrado = df_inventario[df_inventario['Marca'] == marca]
        elif proveedor:
            df_v_filtrado = df_ventas[df_ventas['Proveedor'] == proveedor]
            df_i_filtrado = df_inventario[df_inventario['Proveedor'] == proveedor]
        else:
            df_v_filtrado = pd.DataFrame()
            df_i_filtrado = pd.DataFrame()
            
        return df_v_filtrado, df_i_filtrado
    
    return pd.DataFrame(), pd.DataFrame()

# ══════════════════════════════════════════════════════════════════
#  MÉTRICAS
# ══════════════════════════════════════════════════════════════════

def calcular_metricas(df_ventas, mes_seleccionado):
    """Calcula métricas"""
    
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
    
    total_ventas = df_mes['Total'].sum()
    total_facturas = len(df_mes)
    clientes_unicos = df_mes['Cliente'].nunique()
    vendedores_activos = df_mes['Vendedor'].nunique()
    top_productos = df_mes.groupby('Marca')['Total'].sum().nlargest(5)
    top_vendedores = df_mes.groupby('Vendedor')['Total'].sum().nlargest(5)
    
    return {
        'total_ventas': total_ventas,
        'total_facturas': total_facturas,
        'clientes_unicos': clientes_unicos,
        'vendedores_activos': vendedores_activos,
        'top_productos': top_productos,
        'top_vendedores': top_vendedores,
        'crecimiento': 15.3  # Demo
    }

# ══════════════════════════════════════════════════════════════════
#  INTERFAZ
# ══════════════════════════════════════════════════════════════════

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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

.vendor-card {
    background: linear-gradient(135deg, #10B981, #059669);
    color: white;
    padding: 1rem;
    border-radius: 10px;
    margin: 0.5rem 0;
}

.demo-banner {
    background: linear-gradient(135deg, #F59E0B, #D97706);
    color: white;
    padding: 1rem;
    border-radius: 10px;
    margin-bottom: 1rem;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

def pantalla_login():
    """Login"""
    
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    st.markdown("""
    <div>
        <h1 style='color: #4F46E5; margin-bottom: 0.5rem;'>🏢 Portal Proveedores</h1>
        <p style='color: #64748B; font-size: 1.1rem;'>SOLUTO - Versión Demo</p>
    </div>
    """, unsafe_allow_html=True)
    
    df_usuarios, _, _ = cargar_datos_demo()
    
    with st.form("login_form"):
        usuario = st.text_input("👤 Usuario:", placeholder="Prueba: ISRAEL, KAAPANY, NESTLE")
        password = st.text_input("🔐 Contraseña:", type="password", placeholder="Ver credenciales abajo")
        submit = st.form_submit_button("🚀 Ingresar")
        
        if submit:
            if not usuario or not password:
                st.error("❌ Completa todos los campos")
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
                st.error("❌ Credenciales incorrectas")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Credenciales de demo
    with st.expander("🔐 Credenciales Demo"):
        st.markdown("""
        **🔐 Usuarios de Prueba:**
        - **Super Admin:** `ISRAEL` / `2024`
        - **Administrador:** `ADMIN` / `admin2024`
        - **Proveedor KAAPANY:** `KAAPANY` / `kaa2024`
        - **Proveedor NESTLE:** `NESTLE` / `nes2024`
        - **Proveedor UNILEVER:** `UNILEVER` / `uni2024`
        
        **📊 Datos Demo:**
        - 500 ventas simuladas últimos 60 días
        - 25 productos en inventario
        - Métricas y gráficos funcionales
        """)

def dashboard_demo():
    """Dashboard demo"""
    
    user_info = st.session_state['user_info']
    
    # Banner demo
    st.markdown("""
    <div class="demo-banner">
        <h3>🧪 VERSIÓN DEMO - DATOS SIMULADOS</h3>
        <p>Esta es una demostración del Portal de Proveedores usando datos ficticios</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown(f"""
    <div class="header-portal">
        <h1>🏢 Portal {user_info['tipo'].title()}</h1>
        <h2>Bienvenido, {user_info['usuario']}</h2>
        <p style="opacity: 0.9;">
            {f"Proveedor: {user_info['proveedor']}" if user_info['proveedor'] else "Acceso " + user_info['acceso']}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown(f"**👤 {user_info['usuario']}**")
        st.markdown(f"**Tipo:** {user_info['tipo']}")
        if user_info.get('proveedor'):
            st.markdown(f"**Proveedor:** {user_info['proveedor']}")
        if user_info.get('marca'):
            st.markdown(f"**Marca:** {user_info['marca']}")
        
        if st.button("🚪 Cerrar Sesión"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    # Cargar datos demo
    _, df_ventas, df_inventario = cargar_datos_demo()
    
    # Filtrar según usuario
    df_v_filtrado, df_i_filtrado = filtrar_datos_por_usuario(df_ventas, df_inventario, user_info)
    
    # Controles
    if not df_v_filtrado.empty:
        df_v_filtrado['Mes_Año'] = df_v_filtrado['Fecha'].dt.strftime('%B %Y')
        meses_disponibles = sorted(df_v_filtrado['Mes_Año'].dropna().unique(), reverse=True)
        mes_seleccionado = st.selectbox("📅 Período:", meses_disponibles)
    else:
        st.warning("Sin datos para este usuario")
        return
    
    # Métricas
    metricas = calcular_metricas(df_v_filtrado, mes_seleccionado)
    
    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("💰 Ventas", f"${metricas['total_ventas']:,.0f}", 
                 delta=f"+{metricas['crecimiento']}%")
    with col2:
        st.metric("📄 Facturas", f"{metricas['total_facturas']:,}")
    with col3:
        st.metric("👥 Clientes", f"{metricas['clientes_unicos']:,}")
    with col4:
        st.metric("🏪 Vendedores", f"{metricas['vendedores_activos']:,}")
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["📊 Análisis", "🏪 Vendedores", "📦 Inventario"])
    
    with tab1:
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown("### 🏷️ Ventas por Marca")
            if not metricas['top_productos'].empty:
                st.bar_chart(metricas['top_productos'])
            else:
                st.info("Sin datos de productos")
        
        with col_right:
            st.markdown("### 📈 Tendencia")
            tendencia = df_v_filtrado.groupby(df_v_filtrado['Fecha'].dt.date)['Total'].sum()
            st.line_chart(tendencia.tail(15))
    
    with tab2:
        st.markdown("### 🏆 Top Vendedores")
        
        if not metricas['top_vendedores'].empty:
            for i, (vendedor, venta) in enumerate(metricas['top_vendedores'].items(), 1):
                emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                st.markdown(f"""
                <div class="vendor-card">
                    <h4>{emoji} {vendedor}</h4>
                    <p style="font-size: 1.2rem; margin: 0;"><strong>${venta:,.0f}</strong></p>
                </div>
                """, unsafe_allow_html=True)
    
    with tab3:
        st.markdown("### 📦 Inventario")
        
        if not df_i_filtrado.empty:
            total_productos = len(df_i_filtrado)
            valor_inventario = (df_i_filtrado['Cantidad'] * df_i_filtrado['Costo']).sum()
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("📦 Productos", f"{total_productos:,}")
            with col2:
                st.metric("💰 Valor", f"${valor_inventario:,.0f}")
            
            st.dataframe(df_i_filtrado[['Marca', 'Descripcion', 'Cantidad', 'Costo', 'PVP']], 
                        use_container_width=True)

# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    if not st.session_state.get('authenticated', False):
        pantalla_login()
    else:
        dashboard_demo()

if __name__ == "__main__":
    main()
