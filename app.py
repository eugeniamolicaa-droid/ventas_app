import streamlit as st
import pandas as pd
from datetime import datetime
import hashlib
from sqlalchemy import create_engine, text
import os

# =========================
# 🎨 ESTILO APPLE PREMIUM
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
    
    .card {
        background: rgba(255,255,255,0.08);
        backdrop-filter: blur(20px);
        border-radius: 20px;
        padding: 16px;
        border: 1px solid rgba(255,255,255,0.1);
        transition: all 0.3s ease;
    }
    .card:hover { transform: translateY(-4px); }
    
    h1 { font-weight: 700; letter-spacing: -0.03em; }
    h2, h3 { font-weight: 600; letter-spacing: -0.02em; }
    
    .stButton>button { border-radius: 14px; height: 48px; font-weight: 600; }
    img { border-radius: 12px; }
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
# 🧱 CREACIÓN DE TABLAS
# =========================
with engine.begin() as conn:
    conn.execute(text("""
    CREATE TABLE IF NOT EXISTS usuarios(
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        rol TEXT NOT NULL
    )"""))

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

    conn.execute(text("ALTER TABLE productos ADD COLUMN IF NOT EXISTS imagen TEXT;"))

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

# Admin por defecto
with engine.begin() as conn:
    if not conn.execute(text("SELECT 1 FROM usuarios WHERE username='admin'")).fetchone():
        conn.execute(text("""
            INSERT INTO usuarios(username, password, rol) VALUES('admin', :p, 'admin')
        """), {"p": hash_pass("1234")})

# =========================
# 🔐 LOGIN
# =========================
if "login" not in st.session_state:
    st.title("📱 POINT.MOBILE")
    st.markdown("<p style='text-align:center; color:#8e8e93;'>Sistema de Ventas Móvil</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        user = st.text_input("Usuario", placeholder="Usuario")
        pwd = st.text_input("Contraseña", type="password", placeholder="Contraseña")
        
        if st.button("Iniciar Sesión", type="primary", use_container_width=True):
            with engine.connect() as conn:
                data = conn.execute(text("""
                    SELECT * FROM usuarios WHERE username=:u AND password=:p
                """), {"u": user, "p": hash_pass(pwd)}).fetchone()
            
            if data:
                st.session_state.update({"login": True, "user": data[1], "rol": data[3], "cart": []})
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos")
    st.stop()

USER = st.session_state["user"]
ROL = st.session_state["rol"]

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.markdown("<h2 style='text-align:center;'>POINT.MOBILE</h2>", unsafe_allow_html=True)
    st.write(f"**👤** {USER}")
    st.write(f"**🔐** {ROL.upper()}")
    st.divider()
    
    menu_options = ["🛒 POS", "🛍️ Carrito"]
    if ROL == "admin":
        menu_options.extend(["⚙️ Admin", "💰 Caja"])
    
    menu = st.radio("Módulos", menu_options, label_visibility="collapsed")
    
    st.divider()
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# Cargar datos
df_productos = pd.read_sql("SELECT * FROM productos ORDER BY nombre", engine)

# =========================
# 🛒 POS - CON FOTOS Y BUSCADOR
# =========================
if menu == "🛒 POS":
    st.header("🛒 Punto de Venta")
    
    search = st.text_input("🔎 Buscar producto", placeholder="Nombre o variante...")
    
    df_filtrado = df_productos[
        df_productos['nombre'].str.contains(search, case=False, na=False) |
        df_productos['variante'].str.contains(search, case=False, na=False)
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
                
                qty = st.number_input("Cantidad", min_value=1, max_value=30, value=1, 
                                    key=f"qty_{row['id']}", label_visibility="collapsed")
                
                if st.button("➕ Agregar", key=f"add_{row['id']}", use_container_width=True):
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
            subtotal = item["price"] * item["qty"]
            col1, col2, col3 = st.columns([5, 2, 1])
            with col1: st.write(f"**{item['name']}** × {item['qty']}")
            with col2: st.write(f"${subtotal:,.0f}")
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
            st.success("¡Venta realizada con éxito!", icon="🎉")
            st.rerun()

# =========================
# ⚙️ ADMIN - GESTIÓN COMPLETA DE PRODUCTOS Y USUARIOS
# =========================
elif menu == "⚙️ Admin" and ROL == "admin":
    st.header("⚙️ Administración")
    
    tab1, tab2 = st.tabs(["📦 Productos", "👥 Usuarios"])
    
    # ====================== TAB PRODUCTOS ======================
    with tab1:
        st.subheader("Agregar Nuevo Producto")
        with st.form("form_nuevo_producto", clear_on_submit=True):
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
                        """), {
                            "cat": categoria, "nom": nombre, "var": variante,
                            "pre": precio, "cos": costo, "sto": stock, "img": img_path
                        })
                    st.success("✅ Producto agregado", icon="🎉")
                    st.rerun()
                else:
                    st.error("Nombre y precio son obligatorios")

        st.subheader("Productos Registrados")
        if not df_productos.empty:
            for _, row in df_productos.iterrows():
                col1, col2, col3, col4 = st.columns([3, 2, 1.5, 1.5])
                with col1:
                    st.write(f"**{row['nombre']}** — {row.get('variante', '')}")
                with col2:
                    st.write(f"${row['precio']:,.0f} | Stock: **{row['stock']}**")
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

        # Formulario de Edición de Producto
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
                    e_precio = st.number_input("Precio", value=float(prod['precio']), min_value=0.0)
                    e_costo = st.number_input("Costo", value=float(prod.get('costo', 0)), min_value=0.0)
                    e_stock = st.number_input("Stock", value=int(prod['stock']), min_value=0)
                
                if prod.get('imagen') and os.path.exists(str(prod['imagen'])):
                    st.image(prod['imagen'], width=250, caption="Foto actual")
                
                nueva_foto = st.file_uploader("Cambiar foto", type=["jpg","jpeg","png"])
                
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.form_submit_button("💾 Guardar Cambios", type="primary"):
                        img_path = prod['imagen']
                        if nueva_foto:
                            os.makedirs("imagenes_productos", exist_ok=True)
                            img_path = f"imagenes_productos/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{nueva_foto.name}"
                            with open(img_path, "wb") as f:
                                f.write(nueva_foto.getbuffer())
                        
                        with engine.begin() as conn:
                            conn.execute(text("""
                                UPDATE productos SET nombre=:nom, categoria=:cat, variante=:var,
                                precio=:pre, costo=:cos, stock=:sto, imagen=:img WHERE id=:id
                            """), {
                                "nom": e_nombre, "cat": e_categoria, "var": e_variante,
                                "pre": e_precio, "cos": e_costo, "sto": e_stock,
                                "img": img_path, "id": pid
                            })
                        del st.session_state["edit_product_id"]
                        st.success("Producto actualizado correctamente")
                        st.rerun()
                with col_b:
                    if st.form_submit_button("Cancelar"):
                        del st.session_state["edit_product_id"]
                        st.rerun()

    # ====================== TAB USUARIOS (COMPLETO) ======================
    with tab2:
        st.subheader("Gestión de Usuarios")
        
        df_usuarios = pd.read_sql("SELECT id, username, rol FROM usuarios ORDER BY username", engine)
        
        # Lista de usuarios con botones
        for _, row in df_usuarios.iterrows():
            if row['username'] == 'admin':  # Proteger usuario admin principal
                col1, col2, col3 = st.columns([4, 2, 2])
                with col1:
                    st.write(f"**{row['username']}** (Admin Principal)")
                with col2:
                    st.write(f"Rol: **{row['rol']}**")
                with col3:
                    st.write("Protegido")
            else:
                col1, col2, col3, col4 = st.columns([3, 2, 1.5, 1.5])
                with col1:
                    st.write(f"**{row['username']}**")
                with col2:
                    st.write(f"Rol: **{row['rol']}**")
                with col3:
                    if st.button("✏️ Editar", key=f"edit_user_{row['id']}"):
                        st.session_state["edit_user_id"] = row["id"]
                        st.rerun()
                with col4:
                    if st.button("🗑️ Eliminar", key=f"del_user_{row['id']}"):
                        st.session_state["confirm_delete_user"] = row["id"]
                        st.rerun()

        # Confirmación de eliminación
        if "confirm_delete_user" in st.session_state:
            user_to_delete = pd.read_sql(f"SELECT username FROM usuarios WHERE id = {st.session_state['confirm_delete_user']}", engine).iloc[0]
            st.warning(f"¿Estás seguro de eliminar al usuario **{user_to_delete['username']}**?")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Sí, eliminar", type="primary"):
                    with engine.begin() as conn:
                        conn.execute(text("DELETE FROM usuarios WHERE id = :id"), 
                                   {"id": st.session_state["confirm_delete_user"]})
                    st.success("Usuario eliminado correctamente")
                    del st.session_state["confirm_delete_user"]
                    st.rerun()
            with col2:
                if st.button("Cancelar"):
                    del st.session_state["confirm_delete_user"]
                    st.rerun()

        # Formulario de edición de usuario
        if "edit_user_id" in st.session_state:
            uid = st.session_state["edit_user_id"]
            user_data = pd.read_sql(f"SELECT * FROM usuarios WHERE id = {uid}", engine).iloc[0]
            
            st.subheader(f"Editando usuario: {user_data['username']}")
            with st.form("edit_user_form"):
                new_username = st.text_input("Nombre de usuario", value=user_data['username'])
                new_rol = st.selectbox("Rol", ["vendedor", "admin"], 
                                     index=0 if user_data['rol'] == "vendedor" else 1)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("💾 Guardar Cambios", type="primary"):
                        with engine.begin() as conn:
                            conn.execute(text("""
                                UPDATE usuarios SET username = :u, rol = :r WHERE id = :id
                            """), {"u": new_username, "r": new_rol, "id": uid})
                        st.success("Usuario actualizado correctamente")
                        del st.session_state["edit_user_id"]
                        st.rerun()
                with col2:
                    if st.form_submit_button("Cancelar"):
                        del st.session_state["edit_user_id"]
                        st.rerun()

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
                    st.error("El nombre de usuario ya existe")
            else:
                st.warning("Completa usuario y contraseña")

# =========================
# 💰 CAJA - SOLO ADMIN
# =========================
elif menu == "💰 Caja" and ROL == "admin":
    st.header("💰 Caja y Reportes Generales")
    ventas = pd.read_sql("""
        SELECT v.fecha, v.usuario, p.nombre as producto, 
               v.cantidad, v.total, v.ganancia 
        FROM ventas v 
        LEFT JOIN productos p ON v.producto_id = p.id 
        ORDER BY v.fecha DESC
    """, engine)
    
    if not ventas.empty:
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("Total Vendido", f"${ventas['total'].sum():,.0f}")
        with col2: st.metric("Ganancia Estimada", f"${ventas['ganancia'].sum():,.0f}")
        with col3: st.metric("Total de Ventas", len(ventas))
        
        st.subheader("Ventas por Vendedor")
        st.bar_chart(ventas.groupby("usuario")["total"].sum())
        
        st.subheader("Historial de Ventas")
        st.dataframe(ventas, use_container_width=True)
    else:
        st.info("Aún no hay ventas registradas.")
