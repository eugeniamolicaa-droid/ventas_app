import streamlit as st
import pandas as pd
from datetime import datetime, date
import hashlib
from sqlalchemy import create_engine, text
import os

# =========================
# 🎨 ESTILO APPLE
# =========================
st.set_page_config(page_title="POINT.MOBILE", layout="wide", page_icon="📱")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@400;500;600;700&display=swap');
    body, .stApp { 
        background: #0a0c10; 
        color: #f5f5f7; 
        font-family: 'SF Pro Display', sans-serif; 
    }
    .card {
        background: rgba(255,255,255,0.08);
        backdrop-filter: blur(20px);
        border-radius: 20px;
        padding: 20px;
        border: 1px solid rgba(255,255,255,0.1);
    }
    h1, h2, h3 { font-weight: 600; letter-spacing: -0.02em; }
    .stButton>button { border-radius: 14px; height: 44px; font-weight: 600; }
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
            fecha TIMESTAMP
        )
    """))

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
        username = st.text_input("Usuario", placeholder="Usuario")
        password = st.text_input("Contraseña", type="password", placeholder="Contraseña")
        
        if st.button("Iniciar Sesión", type="primary", use_container_width=True):
            with engine.connect() as conn:
                data = conn.execute(text("""
                    SELECT * FROM usuarios WHERE username=:u AND password=:p
                """), {"u": username, "p": hash_pass(password)}).fetchone()
            
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
    
    menu_options = ["🛒 Agregar Producto", "🛍️ Carrito"]
    if ROL == "admin":
        menu_options.extend(["⚙️ Admin", "📊 Reportes"])
    
    menu = st.radio("Módulos", menu_options, label_visibility="collapsed")
    
    st.divider()
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# Cargar productos
df_productos = pd.read_sql("SELECT * FROM productos ORDER BY nombre", engine)

# =========================
# 🛒 AGREGAR PRODUCTO
# =========================
if menu == "🛒 Agregar Producto":
    st.header("🛒 Agregar Producto")
    
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
                if row.get('imagen') and os.path.exists(str(row.get('imagen', ''))):
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
            st.success("¡Venta realizada con éxito!", icon="🎉")
            st.rerun()

# =========================
# 📊 REPORTES - SOLO ADMIN (CORREGIDO)
# =========================
elif menu == "📊 Reportes" and ROL == "admin":
    st.header("📊 Reportes y Gestión de Ventas")
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    with col1:
        fecha_desde = st.date_input("Desde", value=date.today())
    with col2:
        fecha_hasta = st.date_input("Hasta", value=date.today())
    with col3:
        vendedores = ["Todos"] + pd.read_sql("SELECT DISTINCT usuario FROM ventas", engine)['usuario'].tolist() if not pd.read_sql("SELECT DISTINCT usuario FROM ventas", engine).empty else ["Todos"]
        vendedor_filtro = st.selectbox("Vendedor", vendedores)

    # Cargar ventas
    query = """
        SELECT v.id, v.fecha, v.usuario, p.nombre as producto, 
               v.cantidad, v.total, v.ganancia
        FROM ventas v 
        LEFT JOIN productos p ON v.producto_id = p.id 
        WHERE DATE(v.fecha) BETWEEN :desde AND :hasta
    """
    params = {"desde": fecha_desde, "hasta": fecha_hasta}

    if vendedor_filtro != "Todos":
        query += " AND v.usuario = :vendedor"
        params["vendedor"] = vendedor_filtro

    ventas = pd.read_sql(query + " ORDER BY v.fecha DESC", engine, params=params)

    # Métricas
    if not ventas.empty:
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("Total Vendido", f"${ventas['total'].sum():,.0f}")
        with c2: st.metric("Ganancia Estimada", f"${ventas['ganancia'].sum():,.0f}")
        with c3: st.metric("N° de Ventas", len(ventas))
        with c4: st.metric("Unidades Vendidas", int(ventas['cantidad'].sum()))

        st.subheader("Historial de Ventas")
        
        for _, row in ventas.iterrows():
            col1, col2, col3, col4, col5 = st.columns([2.5, 2.5, 1.8, 1, 1])
            with col1:
                st.write(f"**{row['fecha'].strftime('%d/%m %H:%M')}**")
            with col2:
                st.write(f"{row['usuario']} → **{row['producto']}**")
            with col3:
                st.write(f"{row['cantidad']} uds - ${row['total']:,.0f}")
            with col4:
                if st.button("✏️ Modificar", key=f"mod_{row['id']}"):
                    st.session_state["edit_venta_id"] = row["id"]
                    st.rerun()
            with col5:
                if st.button("🗑️ Eliminar", key=f"del_{row['id']}"):
                    st.session_state["confirm_delete"] = row["id"]
                    st.rerun()
            st.divider()
    else:
        st.info("No hay ventas en el rango de fechas seleccionado.")

    # Modificar Venta
    if "edit_venta_id" in st.session_state:
        vid = st.session_state["edit_venta_id"]
        venta = pd.read_sql(f"SELECT * FROM ventas WHERE id = {vid}", engine).iloc[0]
        
        st.subheader(f"Modificar Venta #{vid}")
        nueva_cantidad = st.number_input("Nueva Cantidad", min_value=1, value=int(venta["cantidad"]))
        
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("💾 Guardar Cambios", type="primary"):
                diferencia = nueva_cantidad - venta["cantidad"]
                nuevo_total = (venta["total"] / venta["cantidad"]) * nueva_cantidad
                
                with engine.begin() as conn:
                    conn.execute(text("""
                        UPDATE ventas SET cantidad = :cant, total = :total, ganancia = :total * 0.3 
                        WHERE id = :id
                    """), {"cant": nueva_cantidad, "total": nuevo_total, "id": vid})
                    conn.execute(text("UPDATE productos SET stock = stock - :diff WHERE id = :pid"),
                               {"diff": diferencia, "pid": venta["producto_id"]})
                
                del st.session_state["edit_venta_id"]
                st.success("Venta modificada correctamente")
                st.rerun()
        with col_b:
            if st.button("Cancelar"):
                del st.session_state["edit_venta_id"]
                st.rerun()

    # Eliminar Venta
    if "confirm_delete" in st.session_state:
        st.warning("¿Estás seguro de eliminar esta venta? El stock se devolverá automáticamente.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Sí, Eliminar", type="primary"):
                with engine.begin() as conn:
                    v = conn.execute(text("SELECT producto_id, cantidad FROM ventas WHERE id = :id"), 
                                   {"id": st.session_state["confirm_delete"]}).fetchone()
                    if v:
                        conn.execute(text("UPDATE productos SET stock = stock + :cant WHERE id = :pid"),
                                   {"cant": v[1], "pid": v[0]})
                        conn.execute(text("DELETE FROM ventas WHERE id = :id"), 
                                   {"id": st.session_state["confirm_delete"]})
                st.success("Venta eliminada y stock devuelto")
                del st.session_state["confirm_delete"]
                st.rerun()
        with col2:
            if st.button("Cancelar"):
                del st.session_state["confirm_delete"]
                st.rerun()

# =========================
# ⚙️ ADMIN (Placeholder - puedes expandir después)
# =========================
elif menu == "⚙️ Admin" and ROL == "admin":
    st.header("⚙️ Administración")
    st.info("Gestión de Productos y Usuarios estará aquí.")
    # Agrega aquí tu código de Admin anterior si quieres

else:
    st.info("Selecciona un módulo desde la barra lateral.")
