import streamlit as st
import pandas as pd
from datetime import datetime, date
import hashlib
from sqlalchemy import create_engine, text
import os

# =========================
# 🎨 ESTILO
# =========================
st.set_page_config(page_title="POINT.MOBILE", layout="wide", page_icon="📱")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@400;500;600;700&display=swap');
    body, .stApp { background: #0a0c10; color: #f5f5f7; font-family: 'SF Pro Display', sans-serif; }
    .card { background: rgba(255,255,255,0.08); backdrop-filter: blur(20px); border-radius: 20px; padding: 20px; border: 1px solid rgba(255,255,255,0.1); }
    h1, h2, h3 { font-weight: 600; letter-spacing: -0.02em; }
    .stButton>button { border-radius: 14px; height: 44px; font-weight: 600; }
    img { border-radius: 12px; }
</style>
""", unsafe_allow_html=True)

def hash_pass(p):
    return hashlib.sha256(p.encode()).hexdigest()

# =========================
# BASE DE DATOS
# =========================
DB_URL = st.secrets["DB_URL"]
engine = create_engine(DB_URL, pool_pre_ping=True)

with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            rol TEXT NOT NULL
        )
    """))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS productos (
            id SERIAL PRIMARY KEY,
            categoria TEXT,
            nombre TEXT NOT NULL,
            variante TEXT,
            precio FLOAT NOT NULL,
            costo FLOAT,
            stock INT DEFAULT 0,
            imagen TEXT
        )
    """))
    conn.execute(text("ALTER TABLE productos ADD COLUMN IF NOT EXISTS imagen TEXT;"))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS ventas (
            id SERIAL PRIMARY KEY,
            producto_id INT,
            usuario TEXT,
            cantidad INT,
            total FLOAT,
            ganancia FLOAT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))

# Admin por defecto
with engine.begin() as conn:
    if not conn.execute(text("SELECT 1 FROM usuarios WHERE username='admin'")).fetchone():
        conn.execute(text("INSERT INTO usuarios(username, password, rol) VALUES('admin', :p, 'admin')"), 
                    {"p": hash_pass("1234")})

# =========================
# LOGIN
# =========================
if "login" not in st.session_state:
    st.title("📱 POINT.MOBILE")
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        user = st.text_input("Usuario", placeholder="Usuario")
        pwd = st.text_input("Contraseña", type="password", placeholder="Contraseña")
        if st.button("Iniciar Sesión", type="primary", use_container_width=True):
            with engine.connect() as conn:
                data = conn.execute(text("SELECT * FROM usuarios WHERE username=:u AND password=:p"),
                                  {"u": user, "p": hash_pass(pwd)}).fetchone()
            if data:
                st.session_state.update({"login": True, "user": data[1], "rol": data[3], "cart": []})
                st.rerun()
            else:
                st.error("❌ Credenciales incorrectas")
    st.stop()

USER = st.session_state["user"]
ROL = st.session_state["rol"]

# Sidebar
with st.sidebar:
    st.markdown("<h2 style='text-align:center;'>POINT.MOBILE</h2>", unsafe_allow_html=True)
    st.write(f"**👤** {USER}")
    st.write(f"**🔐** {ROL.upper()}")
    st.divider()
    
    menu_options = ["🛒 Agregar Producto", "🛍️ Carrito"]
    if ROL == "admin":
        menu_options.extend(["⚙️ Admin", "📊 Reportes"])
    menu = st.radio("Módulos", menu_options, label_visibility="collapsed")
    
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

df_productos = pd.read_sql("SELECT * FROM productos ORDER BY nombre", engine)

# =========================
# 🛒 AGREGAR PRODUCTO
# =========================
if menu == "🛒 Agregar Producto":
    st.header("🛒 Agregar Producto")
    search = st.text_input("🔎 Buscar producto", "")
    
    df_filtrado = df_productos[
        df_productos['nombre'].str.contains(search, case=False, na=False) |
        df_productos.get('variante', '').str.contains(search, case=False, na=False)
    ] if search else df_productos

    if df_filtrado.empty:
        st.warning("No se encontraron productos")
    else:
        cols = st.columns(3)
        for idx, row in df_filtrado.iterrows():
            with cols[idx % 3]:
                if row.get('imagen') and os.path.exists(str(row['imagen'])):
                    st.image(row['imagen'], use_column_width=True)
                else:
                    st.markdown('<div style="height:180px;background:rgba(255,255,255,0.05);border-radius:12px;display:flex;align-items:center;justify-content:center;color:#666;">Sin foto</div>', unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class="card">
                    <h4>{row['nombre']}</h4>
                    <p style='color:#8e8e93;'>{row.get('variante', '')}</p>
                    <h3 style='color:#34c759;'>${row['precio']:,.0f}</h3>
                    <small>Stock: {row['stock']}</small>
                </div>
                """, unsafe_allow_html=True)
                
                qty = st.number_input("Cantidad", min_value=1, max_value=30, value=1, key=f"qty_{row['id']}")
                if st.button("➕ Agregar al carrito", key=f"add_{row['id']}", use_container_width=True):
                    st.session_state["cart"].append({
                        "id": int(row["id"]), "name": row["nombre"],
                        "price": float(row["precio"]), "qty": int(qty)
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
        st.info("El carrito está vacío")
    else:
        total = sum(item["price"] * item["qty"] for item in cart)
        for i, item in enumerate(cart):
            col1, col2, col3 = st.columns([5, 2, 1])
            with col1: st.write(f"**{item['name']}** × {item['qty']}")
            with col2: st.write(f"${item['price']*item['qty']:,.0f}")
            with col3:
                if st.button("🗑️", key=f"rm{i}"):
                    cart.pop(i)
                    st.rerun()
        st.divider()
        st.subheader(f"Total: ${total:,.0f}")
        if st.button("💳 Cobrar Venta", type="primary", use_container_width=True):
            with engine.begin() as conn:
                for item in cart:
                    conn.execute(text("UPDATE productos SET stock = stock - :q WHERE id = :id"), {"q": item["qty"], "id": item["id"]})
                    conn.execute(text("""
                        INSERT INTO ventas (producto_id, usuario, cantidad, total, ganancia, fecha)
                        VALUES (:pid, :user, :qty, :total, :ganancia, NOW())
                    """), {
                        "pid": item["id"], "user": USER, "qty": item["qty"],
                        "total": item["price"]*item["qty"], "ganancia": item["price"]*item["qty"]*0.3
                    })
            st.session_state["cart"] = []
            st.success("¡Venta completada exitosamente!")
            st.rerun()

# =========================
# ⚙️ ADMIN - COMPLETO Y CORREGIDO
# =========================
elif menu == "⚙️ Admin" and ROL == "admin":
    st.header("⚙️ Administración")
    tab1, tab2 = st.tabs(["📦 Productos", "👥 Usuarios"])
    
    # ====================== TAB PRODUCTOS ======================
    with tab1:
        st.subheader("Agregar Nuevo Producto")
        with st.form("nuevo_producto", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nombre = st.text_input("Nombre del Producto *")
                categoria = st.text_input("Categoría")
                variante = st.text_input("Variante")
            with col2:
                precio = st.number_input("Precio de Venta ($)", min_value=0.0, step=100.0)
                costo = st.number_input("Costo ($)", min_value=0.0, step=100.0)
                stock = st.number_input("Stock Inicial", min_value=0, value=10)
            imagen = st.file_uploader("📸 Foto del producto", type=["jpg", "jpeg", "png"])
            
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
                        """), {"cat": categoria, "nom": nombre, "var": variante,
                               "pre": precio, "cos": costo, "sto": stock, "img": img_path})
                    st.success("✅ Producto agregado correctamente")
                    st.rerun()
                else:
                    st.error("Nombre y precio son obligatorios")

        st.subheader("Productos Registrados")
        if not df_productos.empty:
            for _, row in df_productos.iterrows():
                col1, col2, col3, col4 = st.columns([3, 2, 1.5, 1.5])
                with col1: st.write(f"**{row['nombre']}** — {row.get('variante','')}")
                with col2: st.write(f"${row['precio']:,.0f} | Stock: **{row['stock']}**")
                with col3:
                    if st.button("✏️ Editar", key=f"edit_prod_{row['id']}"):
                        st.session_state["edit_product_id"] = row["id"]
                        st.rerun()
                with col4:
                    if st.button("🗑️ Eliminar", key=f"del_prod_{row['id']}"):
                        with engine.begin() as conn:
                            conn.execute(text("DELETE FROM productos WHERE id = :id"), {"id": row["id"]})
                        st.success("Producto eliminado")
                        st.rerun()

        # Editar Producto
        if "edit_product_id" in st.session_state:
            pid = st.session_state["edit_product_id"]
            prod = pd.read_sql(f"SELECT * FROM productos WHERE id = {pid}", engine).iloc[0]
            
            st.subheader(f"Editando: {prod['nombre']}")
            with st.form("editar_producto"):
                col1, col2 = st.columns(2)
                with col1:
                    e_nombre = st.text_input("Nombre", value=prod['nombre'])
                    e_categoria = st.text_input("Categoría", value=prod.get('categoria', ''))
                    e_variante = st.text_input("Variante", value=prod.get('variante', ''))
                with col2:
                    e_precio = st.number_input("Precio", value=float(prod['precio']))
                    e_costo = st.number_input("Costo", value=float(prod.get('costo', 0)))
                    e_stock = st.number_input("Stock", value=int(prod['stock']))
                
                if prod.get('imagen') and os.path.exists(str(prod['imagen'])):
                    st.image(prod['imagen'], width=300, caption="Foto actual")
                nueva_imagen = st.file_uploader("Cambiar foto", type=["jpg","jpeg","png"])
                
                if st.form_submit_button("💾 Guardar Cambios", type="primary"):
                    img_path = prod['imagen']
                    if nueva_imagen:
                        os.makedirs("imagenes_productos", exist_ok=True)
                        img_path = f"imagenes_productos/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{nueva_imagen.name}"
                        with open(img_path, "wb") as f:
                            f.write(nueva_imagen.getbuffer())
                    
                    with engine.begin() as conn:
                        conn.execute(text("""
                            UPDATE productos SET nombre=:nom, categoria=:cat, variante=:var,
                            precio=:pre, costo=:cos, stock=:sto, imagen=:img WHERE id=:id
                        """), {"nom": e_nombre, "cat": e_categoria, "var": e_variante,
                               "pre": e_precio, "cos": e_costo, "sto": e_stock,
                               "img": img_path, "id": pid})
                    del st.session_state["edit_product_id"]
                    st.success("Producto actualizado correctamente")
                    st.rerun()

    # ====================== TAB USUARIOS (CORREGIDO) ======================
    with tab2:
        st.subheader("Usuarios del Sistema")
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
                    st.success(f"✅ Usuario '{new_user}' creado correctamente")
                    st.rerun()
                except Exception as e:
                    st.error("El nombre de usuario ya existe")
            else:
                st.warning("Por favor completa usuario y contraseña")

# =========================
# 📊 REPORTES (Placeholder)
# =========================
elif menu == "📊 Reportes" and ROL == "admin":
    st.header("📊 Reportes y Gestión de Ventas")
    st.info("La sección de Reportes se completará en la siguiente actualización.")

else:
    st.info("Selecciona un módulo desde la barra lateral.")
