import streamlit as st
import pandas as pd
from datetime import datetime
import hashlib
from sqlalchemy import create_engine, text
import os

# =========================
# 🎨 CONFIGURACIÓN - ESTILO APPLE
# =========================
st.set_page_config(page_title="POINT.MOBILE", layout="wide", page_icon="📱")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@400;500;600;700&display=swap');
    
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
        transform: translateY(-3px);
    }
    
    h1 { font-weight: 700; letter-spacing: -0.03em; }
    h2, h3 { font-weight: 600; letter-spacing: -0.02em; }
    
    .stButton>button {
        border-radius: 14px;
        height: 48px;
        font-weight: 600;
        font-size: 15px;
    }
</style>
""", unsafe_allow_html=True)

# =========================
# 🔐 FUNCIONES
# =========================
def hash_pass(p):
    return hashlib.sha256(p.encode()).hexdigest()

# =========================
# 🔌 BASE DE DATOS
# =========================
DB_URL = st.secrets["DB_URL"]
engine = create_engine(DB_URL, pool_pre_ping=True)

# =========================
# 🧱 CREACIÓN Y ACTUALIZACIÓN DE TABLAS (CORREGIDO)
# =========================
with engine.begin() as conn:
    # Tabla de usuarios
    conn.execute(text("""
    CREATE TABLE IF NOT EXISTS usuarios(
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        rol TEXT NOT NULL
    )"""))

    # Tabla de productos
    conn.execute(text("""
    CREATE TABLE IF NOT EXISTS productos(
        id SERIAL PRIMARY KEY,
        categoria TEXT,
        nombre TEXT NOT NULL,
        variante TEXT,
        precio FLOAT NOT NULL,
        costo FLOAT,
        stock INT DEFAULT 0,
        imagen TEXT
    )"""))

    # Agregar columna 'imagen' si no existe (SOLUCIÓN AL ERROR)
    conn.execute(text("""
    ALTER TABLE productos 
    ADD COLUMN IF NOT EXISTS imagen TEXT;
    """))

    # Tabla de ventas
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

# =========================
# 👑 USUARIO ADMIN POR DEFECTO
# =========================
with engine.begin() as conn:
    if not conn.execute(text("SELECT 1 FROM usuarios WHERE username='admin'")).fetchone():
        conn.execute(text("""
            INSERT INTO usuarios(username, password, rol) 
            VALUES('admin', :p, 'admin')
        """), {"p": hash_pass("1234")})

# =========================
# 🔐 LOGIN
# =========================
if "login" not in st.session_state:
    st.title("📱 POINT.MOBILE")
    st.markdown("<p style='text-align:center; color:#8e8e93; font-size:18px;'>Sistema de Ventas Móvil</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        username = st.text_input("Usuario", placeholder="Ingresa tu usuario")
        password = st.text_input("Contraseña", type="password", placeholder="Ingresa tu contraseña")
        
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
                st.error("❌ Usuario o contraseña incorrectos")
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
    st.markdown(f"<h2 style='text-align:center; margin-bottom:20px;'>POINT.MOBILE</h2>", unsafe_allow_html=True)
    st.markdown(f"**👤** {USER}\n**🔐** {ROL.upper()}")
    st.divider()
    
    menu_options = ["🛒 POS", "🛍️ Carrito", "💰 Caja"]
    if ROL == "admin":
        menu_options.insert(2, "⚙️ Admin")
    
    menu = st.radio("Módulos", menu_options, label_visibility="collapsed")
    
    st.divider()
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# Cargar productos
df_productos = pd.read_sql("SELECT * FROM productos ORDER BY nombre", engine)

# =========================
# 🛒 POS
# =========================
if menu == "🛒 POS":
    st.header("🛒 Punto de Venta")
    
    if df_productos.empty:
        st.warning("No hay productos cargados aún.")
    else:
        cols = st.columns(3)
        for idx, row in df_productos.iterrows():
            with cols[idx % 3]:
                st.markdown(f"""
                <div class="card">
                    <h4>{row['nombre']}</h4>
                    <p style='color:#8e8e93; margin:4px 0;'>{row['variante']}</p>
                    <h3 style='color:#34c759; margin:8px 0;'>${row['precio']:,.0f}</h3>
                    <small>Stock: {row['stock']} • {row['categoria']}</small>
                </div>
                """, unsafe_allow_html=True)
                
                qty = st.number_input("Cantidad", min_value=1, max_value=30, value=1, 
                                    key=f"qty_{row['id']}", label_visibility="collapsed")
                
                if st.button("➕ Agregar", key=f"add_{row['id']}", use_container_width=True):
                    st.session_state["cart"].append({
                        "id": int(row["id"]),
                        "name": row["nombre"],
                        "price": float(row["precio"]),
                        "qty": int(qty)
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
        st.markdown("<h3 style='text-align:center; color:#666;'>El carrito está vacío</h3>", unsafe_allow_html=True)
    else:
        total = sum(item["price"] * item["qty"] for item in cart)
        
        for i, item in enumerate(cart):
            subtotal = item["price"] * item["qty"]
            col1, col2, col3 = st.columns([5, 2, 1])
            with col1:
                st.write(f"**{item['name']}** × {item['qty']}")
            with col2:
                st.write(f"${subtotal:,.0f}")
            with col3:
                if st.button("🗑️", key=f"rm_{i}"):
                    cart.pop(i)
                    st.rerun()
        
        st.divider()
        st.markdown(f"<h2 style='text-align:right;'>Total: **${total:,.0f}**</h2>", unsafe_allow_html=True)
        
        if st.button("💳 Cobrar Venta", type="primary", use_container_width=True):
            with engine.begin() as conn:
                for item in cart:
                    conn.execute(text("UPDATE productos SET stock = stock - :q WHERE id = :id"),
                               {"q": item["qty"], "id": item["id"]})
                    
                    conn.execute(text("""
                        INSERT INTO ventas(producto_id, usuario, cantidad, total, ganancia, fecha)
                        VALUES(:pid, :user, :qty, :total, :ganancia, :fecha)
                    """), {
                        "pid": item["id"], "user": USER, "qty": item["qty"],
                        "total": item["price"]*item["qty"],
                        "ganancia": item["price"]*item["qty"]*0.3,
                        "fecha": datetime.now()
                    })
            
            st.session_state["cart"] = []
            st.success("¡Venta registrada exitosamente!", icon="🎉")
            st.rerun()

# =========================
# ⚙️ ADMIN
# =========================
elif menu == "⚙️ Admin" and ROL == "admin":
    st.header("⚙️ Administración")
    
    tab1, tab2 = st.tabs(["📦 Productos", "👥 Usuarios"])
    
    # ====================== TAB PRODUCTOS ======================
    with tab1:
        st.subheader("Agregar Nuevo Producto")
        
        with st.form("form_producto", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nombre = st.text_input("Nombre del Producto *")
                categoria = st.text_input("Categoría")
                variante = st.text_input("Variante (color, talle, etc.)")
            with col2:
                precio = st.number_input("Precio de Venta ($)", min_value=0.0, step=100.0)
                costo = st.number_input("Costo ($)", min_value=0.0, step=100.0)
                stock = st.number_input("Stock Inicial", min_value=0, value=10)
            
            imagen = st.file_uploader("📸 Foto del producto", type=["jpg", "jpeg", "png"])
            
            if st.form_submit_button("💾 Guardar Producto", type="primary"):
                if nombre and precio > 0:
                    img_path = None
                    if imagen:
                        os.makedirs("imagenes_productos", exist_ok=True)
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        img_path = f"imagenes_productos/{timestamp}_{imagen.name}"
                        with open(img_path, "wb") as f:
                            f.write(imagen.getbuffer())
                    
                    with engine.begin() as conn:
                        conn.execute(text("""
                            INSERT INTO productos (categoria, nombre, variante, precio, costo, stock, imagen)
                            VALUES (:cat, :nom, :var, :pre, :cos, :sto, :img)
                        """), {
                            "cat": categoria,
                            "nom": nombre,
                            "var": variante,
                            "pre": precio,
                            "cos": costo,
                            "sto": stock,
                            "img": img_path
                        })
                    
                    st.success("✅ Producto guardado correctamente", icon="🎉")
                    st.rerun()
                else:
                    st.error("❌ Nombre y precio son obligatorios")
        
        # Lista de productos
        st.subheader("Productos Registrados")
        if not df_productos.empty:
            for _, row in df_productos.iterrows():
                col1, col2, col3 = st.columns([4, 2, 2])
                with col1:
                    st.write(f"**{row['nombre']}** — {row.get('variante', '')}")
                with col2:
                    st.write(f"${row['precio']:,.0f} | Stock: **{row['stock']}**")
                with col3:
                    if st.button("🗑️ Eliminar", key=f"del_{row['id']}"):
                        with engine.begin() as conn:
                            conn.execute(text("DELETE FROM productos WHERE id = :id"), {"id": row["id"]})
                        st.success("Producto eliminado")
                        st.rerun()
        else:
            st.info("Aún no hay productos registrados.")

    # ====================== TAB USUARIOS ======================
    with tab2:
        st.subheader("Gestión de Usuarios")
        
        df_usuarios = pd.read_sql("SELECT id, username, rol FROM usuarios ORDER BY username", engine)
        st.dataframe(df_usuarios, use_container_width=True, hide_index=True)
        
        st.divider()
        st.subheader("Crear Nuevo Usuario")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            new_user = st.text_input("Nombre de usuario")
        with col2:
            new_pass = st.text_input("Contraseña", type="password")
        with col3:
            new_rol = st.selectbox("Rol", ["vendedor", "admin"])
        
        if st.button("Crear Usuario", type="primary"):
            if new_user and new_pass:
                try:
                    with engine.begin() as conn:
                        conn.execute(text("""
                            INSERT INTO usuarios(username, password, rol)
                            VALUES(:u, :p, :r)
                        """), {"u": new_user, "p": hash_pass(new_pass), "r": new_rol})
                    st.success(f"Usuario '{new_user}' creado correctamente ✅")
                    st.rerun()
                except:
                    st.error("Error: El nombre de usuario ya existe")
            else:
                st.warning("Completa usuario y contraseña")

# =========================
# 💰 CAJA
# =========================
elif menu == "💰 Caja":
    st.header("💰 Caja y Reportes")
    ventas = pd.read_sql("SELECT * FROM ventas ORDER BY fecha DESC", engine)
    
    if not ventas.empty:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Vendido", f"${ventas['total'].sum():,.0f}")
        with col2:
            st.metric("Ganancia Estimada", f"${ventas['ganancia'].sum():,.0f}")
        
        st.subheader("Ventas por Vendedor")
        st.bar_chart(ventas.groupby("usuario")["total"].sum())
        
        st.subheader("Historial de Ventas")
        st.dataframe(ventas, use_container_width=True)
    else:
        st.info("Todavía no hay ventas registradas.")
