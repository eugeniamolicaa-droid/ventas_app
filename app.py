import streamlit as st
import pandas as pd
from datetime import datetime
import hashlib
from sqlalchemy import create_engine, text

# =========================
# 🔐 SEGURIDAD
# =========================
def hash_pass(p):
    return hashlib.sha256(p.encode()).hexdigest()

# =========================
# 🎨 CONFIG
# =========================
st.set_page_config(layout="wide")

st.markdown("""
<style>
body {background-color: #0e1117; color: white;}
.stButton>button {
    height: 55px;
    font-size: 15px;
    border-radius: 10px;
    background-color: #1f6feb;
    color: white;
    font-weight: bold;
}
.card {
    padding: 12px;
    border-radius: 12px;
    background-color: #161b22;
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)

# =========================
# 🔌 DB
# =========================
DB_URL = st.secrets["DB_URL"]

engine = create_engine(
    DB_URL,
    pool_pre_ping=True,
    pool_recycle=300
)

# =========================
# 🧱 TABLAS
# =========================
with engine.begin() as conn:

    conn.execute(text("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT,
        rol TEXT
    )
    """))

    conn.execute(text("""
    CREATE TABLE IF NOT EXISTS productos (
        id SERIAL PRIMARY KEY,
        categoria TEXT,
        nombre TEXT,
        variante TEXT,
        precio FLOAT,
        costo FLOAT,
        stock INT,
        foto TEXT
    )
    """))

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

# =========================
# 👑 ADMIN DEFAULT
# =========================
with engine.begin() as conn:
    admin = conn.execute(text("SELECT * FROM usuarios WHERE username='admin'")).fetchone()

    if not admin:
        conn.execute(text("""
        INSERT INTO usuarios (username,password,rol)
        VALUES ('admin', :p, 'admin')
        """), {"p": hash_pass("1234")})

# =========================
# 🔐 LOGIN
# =========================
st.title("📱 Sistema de Ventas PRO")

user = st.text_input("Usuario", key="login_user")
pwd = st.text_input("Clave", type="password", key="login_pass")

if st.button("Entrar", key="login_btn"):

    with engine.connect() as conn:
        data = conn.execute(text("""
            SELECT * FROM usuarios
            WHERE username=:u AND password=:p
        """), {"u": user, "p": hash_pass(pwd)}).fetchone()

    if data:
        st.session_state["login"] = True
        st.session_state["user"] = data[1]
        st.session_state["rol"] = data[3]

        if "cart" not in st.session_state:
            st.session_state["cart"] = []

        st.rerun()
    else:
        st.error("❌ Login incorrecto")

if "login" not in st.session_state:
    st.stop()

st.success(f"👤 {st.session_state['user']} | {st.session_state['rol']}")

# =========================
# 📦 PRODUCTOS
# =========================
df = pd.read_sql("SELECT * FROM productos", engine)

# =========================
# 🛒 CARRITO (TODOS)
# =========================
st.sidebar.header("🛒 Carrito")

if st.session_state["cart"]:
    total_carrito = 0

    for i, item in enumerate(st.session_state["cart"]):
        st.sidebar.write(f"{item['nombre']} x{item['cant']}")

        total_carrito += item["precio"] * item["cant"]

        if st.sidebar.button("❌", key=f"del_{i}"):
            st.session_state["cart"].pop(i)
            st.rerun()

    st.sidebar.markdown(f"### 💰 Total: {total_carrito}")

    if st.sidebar.button("🧾 Finalizar compra"):

        with engine.begin() as conn:
            for item in st.session_state["cart"]:

                conn.execute(text("""
                    UPDATE productos SET stock = stock - :c
                    WHERE id = :id
                """), {"c": item["cant"], "id": item["id"]})

                conn.execute(text("""
                    INSERT INTO ventas
                    (producto_id,usuario,cantidad,total,ganancia,fecha)
                    VALUES (:p,:u,:c,:t,:g,:f)
                """), {
                    "p": item["id"],
                    "u": st.session_state["user"],
                    "c": item["cant"],
                    "t": item["precio"] * item["cant"],
                    "g": (item["precio"] - item["costo"]) * item["cant"],
                    "f": datetime.now()
                })

        st.session_state["cart"] = []
        st.success("✅ Compra realizada")
        st.rerun()

else:
    st.sidebar.info("Carrito vacío")

# =========================
# 🔍 BUSCAR
# =========================
busqueda = st.text_input("🔍 Buscar producto", key="search")

if busqueda:
    df = df[df["nombre"].str.contains(busqueda, case=False)]

# =========================
# 🛍️ PRODUCTOS + AGREGAR CARRITO
# =========================
st.header("🛍️ Productos")

if not df.empty:

    for _, row in df.iterrows():

        col1, col2, col3 = st.columns([3, 1, 1])

        with col1:
            st.markdown(f"""
            <div class="card">
                <b>{row['nombre']} - {row['variante']}</b><br>
                💲 {row['precio']} | Stock: {row['stock']}
            </div>
            """, unsafe_allow_html=True)

            if row.get("foto"):
                st.image(row["foto"], width=120)

        with col2:
            cant = st.number_input(
                "Cant",
                1, 100,
                key=f"cant_{row['id']}"
            )

        with col3:
            if st.button("🛒 Agregar", key=f"add_{row['id']}"):

                st.session_state["cart"].append({
                    "id": row["id"],
                    "nombre": row["nombre"],
                    "precio": row["precio"],
                    "costo": row["costo"],
                    "cant": cant
                })

                st.success("Agregado al carrito")
                st.rerun()

# =========================
# 🔐 ADMIN PANEL
# =========================
if st.session_state["rol"] == "admin":

    st.subheader("👥 Gestionar usuarios")

usuarios = pd.read_sql("SELECT id, username, rol FROM usuarios", engine)

for _, u in usuarios.iterrows():

    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

    with col1:
        st.write(f"👤 {u['username']}")

    with col2:
        nuevo_rol = st.selectbox(
            "Rol",
            ["admin", "vendedor"],
            index=0 if u["rol"] == "admin" else 1,
            key=f"role_{u['id']}"
        )

        if st.button("💾 Cambiar", key=f"save_{u['id']}"):
            with engine.begin() as conn:
                conn.execute(text("""
                    UPDATE usuarios
                    SET rol = :r
                    WHERE id = :id
                """), {"r": nuevo_rol, "id": u["id"]})

            st.success("Rol actualizado")
            st.rerun()

    with col4:
        if u["username"] != "admin":  # protección básica

            if st.button("🗑️", key=f"del_{u['id']}"):
                with engine.begin() as conn:
                    conn.execute(text("""
                        DELETE FROM usuarios WHERE id=:id
                    """), {"id": u["id"]})

                st.warning("Usuario eliminado")
                st.rerun()

    # =========================
    # 👤 USUARIOS
    # =========================
    st.subheader("Crear usuario")

    u1, u2, u3 = st.columns(3)

    new_user = u1.text_input("Usuario", key="admin_user")
    new_pass = u2.text_input("Clave", type="password", key="admin_pass")
    new_rol = u3.selectbox("Rol", ["admin", "vendedor"], key="admin_role")

    if st.button("Crear usuario", key="create_user"):

        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO usuarios (username,password,rol)
                VALUES (:u,:p,:r)
            """), {
                "u": new_user,
                "p": hash_pass(new_pass),
                "r": new_rol
            })

        st.success("Usuario creado")
        st.rerun()

    # =========================
    # 📦 PRODUCTOS (CON FOTO REAL)
    # =========================
    st.subheader("📦 Agregar producto")

    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)

    categoria = c1.text_input("Categoría", key="cat")
    nombre = c2.text_input("Nombre", key="name")
    variante = c3.text_input("Variante", key="var")
    precio = c4.number_input("Precio", key="price")
    costo = c5.number_input("Costo", key="cost")
    stock = c6.number_input("Stock", step=1, key="stock")

    foto = c7.file_uploader("📸 Foto", type=["png", "jpg", "jpeg"])

    if st.button("Agregar producto", key="add_product"):

        foto_bytes = None
        if foto:
            foto_bytes = foto.getvalue()

        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO productos
                (categoria,nombre,variante,precio,costo,stock,foto)
                VALUES (:c,:n,:v,:p,:co,:s,:f)
            """), {
                "c": categoria,
                "n": nombre,
                "v": variante,
                "p": precio,
                "co": costo,
                "s": int(stock),
                "f": str(foto_bytes) if foto_bytes else None
            })

        st.success("Producto agregado")
        st.rerun()
