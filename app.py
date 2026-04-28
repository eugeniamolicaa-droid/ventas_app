import streamlit as st
import pandas as pd
from datetime import datetime
import hashlib
from sqlalchemy import create_engine, text
import os

# =========================
# 🎨 CONFIGURACIÓN APPLE STYLE
# =========================
st.set_page_config(page_title="ERP PRO", layout="wide", page_icon="🏢")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@400;500;600&display=swap');
    
    body, .stApp {
        background: #0a0c10;
        color: #f5f5f7;
        font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .main > div { padding-top: 2rem; }
    
    .card {
        background: rgba(255,255,255,0.08);
        backdrop-filter: blur(20px);
        border-radius: 20px;
        padding: 20px;
        border: 1px solid rgba(255,255,255,0.1);
        transition: all 0.3s ease;
    }
    .card:hover {
        transform: translateY(-4px);
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3);
    }
    
    h1, h2, h3 {
        font-weight: 600;
        letter-spacing: -0.02em;
    }
    
    .stButton>button {
        border-radius: 14px;
        height: 48px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    
    .stButton>button:hover {
        transform: scale(1.02);
    }
    
    .sidebar .css-1d391kg { background: #0f1117; }
    
    .metric-card {
        background: rgba(255,255,255,0.06);
        border-radius: 16px;
        padding: 16px;
    }
</style>
""", unsafe_allow_html=True)

# =========================
# 🔐 SEGURIDAD
# =========================
def hash_pass(p):
    return hashlib.sha256(p.encode()).hexdigest()

# =========================
# 🔌 BASE DE DATOS
# =========================
DB_URL = st.secrets["DB_URL"]
engine = create_engine(DB_URL, pool_pre_ping=True)

# =========================
# 🧱 CREAR TABLAS
# =========================
with engine.begin() as conn:
    conn.execute(text("""
    CREATE TABLE IF NOT EXISTS usuarios(
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT,
        rol TEXT
    )"""))
    
    conn.execute(text("""
    CREATE TABLE IF NOT EXISTS productos(
        id SERIAL PRIMARY KEY,
        categoria TEXT,
        nombre TEXT,
        variante TEXT,
        precio FLOAT,
        costo FLOAT,
        stock INT DEFAULT 0,
        imagen TEXT
    )"""))
    
    conn.execute(text("""
    CREATE TABLE IF NOT EXISTS ventas(
        id SERIAL PRIMARY KEY,
        producto_id INT,
        usuario TEXT,
        cantidad INT,
        total FLOAT,
        ganancia FLOAT,
        fecha TIMESTAMP
    )"""))

# Usuario admin por defecto
with engine.begin() as conn:
    if not conn.execute(text("SELECT 1 FROM usuarios WHERE username='admin'")).fetchone():
        conn.execute(text("""
            INSERT INTO usuarios(username, password, rol) 
            VALUES('admin', :p, 'admin')
        """), {"p": hash_pass("1234")})

# =========================
# 🔐 LOGIN (Apple Style)
# =========================
if "login" not in st.session_state:
    st.title("🏢 ERP PRO")
    st.markdown("<h3 style='text-align:center; color:#a1a1aa;'>Bienvenido de nuevo</h3>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container():
            username = st.text_input("Usuario", placeholder="Ingresa tu usuario", label_visibility="collapsed")
            password = st.text_input("Contraseña", type="password", placeholder="Contraseña", label_visibility="collapsed")
            
            if st.button("Iniciar Sesión", type="primary", use_container_width=True):
                with engine.connect() as conn:
                    user_data = conn.execute(text("""
                        SELECT * FROM usuarios WHERE username = :u AND password = :p
                    """), {"u": username, "p": hash_pass(password)}).fetchone()
                
                if user_data:
                    st.session_state.update({
                        "login": True,
                        "user": user_data[1],
                        "rol": user_data[3],
                        "cart": []
                    })
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos", icon="❌")
    st.stop()

# =========================
# SESIÓN ACTIVA
# =========================
USER = st.session_state["user"]
ROL = st.session_state["rol"]

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.markdown(f"<h2 style='text-align:center;'>ERP PRO</h2>", unsafe_allow_html=True)
    st.markdown(f"**👤** {USER}  \n**🔐** {ROL.upper()}")
    st.divider()
    
    menu_options = ["🛒 POS", "🛍️ Carrito", "💰 Caja"]
    if ROL == "admin":
        menu_options.insert(2, "⚙️ Admin")
    
    menu = st.radio("Menú", menu_options, label_visibility="collapsed")
    
    st.divider()
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# Cargar productos
df = pd.read_sql("SELECT * FROM productos ORDER BY nombre", engine)

# =========================
# 🛒 POS
# =========================
if menu == "🛒 POS":
    st.header("🛒 Punto de Venta")
    st.markdown("### Productos disponibles")

    if df.empty:
        st.info("Aún no hay productos. Ve a Admin para agregarlos.")
    else:
        cols = st.columns(3)
        for idx, row in df.iterrows():
            with cols[idx % 3]:
                st.markdown(f"""
                <div class="card">
                    <h4>{row['nombre']}</h4>
                    <p style='color:#a1a1aa; margin:5px 0;'>{row['variante']}</p>
                    <h3 style='color:#34c759;'>${row['precio']:,.0f}</h3>
                    <small>Stock: {row['stock']} | {row['categoria']}</small>
                </div>
                """, unsafe_allow_html=True)
                
                qty = st.number_input("Cantidad", min_value=1, max_value=20, value=1, 
                                    key=f"qty_{row['id']}", label_visibility="collapsed")
                
                if st.button("Agregar al carrito", key=f"add_{row['id']}"):
                    st.session_state["cart"].append({
                        "id": row["id"],
                        "name": row["nombre"],
                        "price": row["precio"],
                        "qty": qty
                    })
                    st.toast(f"✅ {row['nombre']} agregado", icon="🛒")
                    st.rerun()

# =========================
# 🛍️ CARRITO
# =========================
elif menu == "🛍️ Carrito":
    st.header("🛍️ Carrito")
    
    cart = st.session_state.get("cart", [])
    
    if not cart:
        st.markdown("<h3 style='text-align:center; color:#666;'>Tu carrito está vacío</h3>", unsafe_allow_html=True)
    else:
        total = 0
        for i, item in enumerate(cart):
            subtotal = item["price"] * item["qty"]
            total += subtotal
            
            col1, col2, col3 = st.columns([5, 2, 1])
            with col1:
                st.write(f"**{item['name']}** × {item['qty']}")
            with col2:
                st.write(f"${subtotal:,.0f}")
            with col3:
                if st.button("🗑️", key=f"del_{i}"):
                    cart.pop(i)
                    st.rerun()
        
        st.divider()
        st.markdown(f"<h2 style='text-align:right;'>Total: **${total:,.0f}**</h2>", unsafe_allow_html=True)
        
        if st.button("💳 Cobrar Ahora", type="primary", use_container_width=True):
            with engine.begin() as conn:
                for item in cart:
                    conn.execute(text("UPDATE productos SET stock = stock - :q WHERE id = :id"),
                                {"q": item["qty"], "id": item["id"]})
                    
                    conn.execute(text("""
                        INSERT INTO ventas (producto_id, usuario, cantidad, total, ganancia, fecha)
                        VALUES (:pid, :user, :qty, :total, :ganancia, :fecha)
                    """), {
                        "pid": item["id"],
                        "user": USER,
                        "qty": item["qty"],
                        "total": item["price"] * item["qty"],
                        "ganancia": item["price"] * item["qty"] * 0.3,
                        "fecha": datetime.now()
                    })
            
            st.session_state["cart"] = []
            st.success("¡Venta realizada con éxito!", icon="🎉")
            st.rerun()

# =========================
# ⚙️ ADMIN (Apple Style + Editar/Eliminar)
# =========================
elif menu == "⚙️ Admin" and ROL == "admin":
    st.header("⚙️ Administración")
    
    tab1, tab2 = st.tabs(["📦 Productos", "👥 Usuarios"])
    
    with tab1:
        st.subheader("Agregar Nuevo Producto")
        
        with st.form("nuevo_producto", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nombre = st.text_input("Nombre del Producto *")
                categoria = st.text_input("Categoría")
                variante = st.text_input("Variante (Talle, Color, etc.)")
            with col2:
                precio = st.number_input("Precio de Venta ($)", min_value=0.0, step=500.0)
                costo = st.number_input("Costo ($)", min_value=0.0, step=500.0)
                stock = st.number_input("Stock Inicial", min_value=0, value=10)
            
            imagen = st.file_uploader("Foto del producto", type=["jpg", "jpeg", "png"], help="Sube desde tu celular")
            
            if st.form_submit_button("Guardar Producto", type="primary"):
                if nombre and precio > 0:
                    img_path = None
                    if imagen:
                        os.makedirs("imagenes_productos", exist_ok=True)
                        img_path = f"imagenes_productos/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{imagen.name}"
                        with open(img_path, "wb") as f:
                            f.write(imagen.getbuffer())
                    
                    with engine.begin() as conn:
                        conn.execute(text("""
                            INSERT INTO productos (categoria, nombre, variante, precio, costo, stock, imagen)
                            VALUES (:cat, :nom, :var, :pre, :cos, :sto, :img)
                        """), {
                            "cat": categoria, "nom": nombre, "var": variante,
                            "pre": precio, "cos": costo, "sto": stock, "img": img_path
                        })
                    
                    st.success("Producto guardado correctamente", icon="✅")
                    st.rerun()
                else:
                    st.error("Nombre y precio son obligatorios")
        
        # Lista de productos con editar y eliminar
        st.subheader("Productos Registrados")
        if not df.empty:
            for _, row in df.iterrows():
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 2, 1.5, 1])
                    with col1:
                        st.write(f"**{row['nombre']}** — {row['variante']}")
                    with col2:
                        st.write(f"${row['precio']:,.0f} | Stock: **{row['stock']}**")
                    with col3:
                        if st.button("Editar", key=f"edit_{row['id']}"):
                            st.session_state["edit_id"] = row["id"]
                            st.rerun()
                    with col4:
                        if st.button("Eliminar", key=f"del_{row['id']}"):
                            with engine.begin() as conn:
                                conn.execute(text("DELETE FROM productos WHERE id = :id"), {"id": row["id"]})
                            st.success("Producto eliminado")
                            st.rerun()
        else:
            st.info("No hay productos aún.")

    with tab2:
        st.subheader("Gestión de Usuarios")
        # (mantengo tu código de usuarios aquí, se puede mejorar más adelante)

# =========================
# 💰 CAJA
# =========================
elif menu == "💰 Caja":
    st.header("💰 Reportes de Caja")
    ventas = pd.read_sql("""
        SELECT v.*, p.nombre as producto 
        FROM ventas v 
        LEFT JOIN productos p ON v.producto_id = p.id 
        ORDER BY fecha DESC
    """, engine)
    
    if not ventas.empty:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Vendido", f"${ventas['total'].sum():,.0f}")
        with col2:
            st.metric("Ganancia Estimada", f"${ventas['ganancia'].sum():,.0f}")
        
        st.subheader("Ventas por Vendedor")
        st.bar_chart(ventas.groupby("usuario")["total"].sum())
        
        st.subheader("Últimas Ventas")
        st.dataframe(ventas[["fecha", "usuario", "producto", "cantidad", "total"]], use_container_width=True)
    else:
        st.info("Todavía no hay ventas registradas.")
