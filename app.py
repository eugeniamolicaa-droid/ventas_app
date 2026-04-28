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

engine = create_engine(DB_URL, pool_pre_ping=True, pool_recycle=300)

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
        stock INT
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

user = st.text_input("Usuario").strip().lower()
pwd = st.text_input("Clave", type="password")

if st.button("Entrar"):

    with engine.connect() as conn:
        data = conn.execute(text("""
        SELECT * FROM usuarios
        WHERE username=:u AND password=:p
        """), {"u": user, "p": hash_pass(pwd)}).fetchone()

    if data:
        st.session_state["login"] = True
        st.session_state["user"] = data[1]
        st.session_state["rol"] = data[3]
        st.rerun()
    else:
        st.error("❌ Usuario o clave incorrectos")

if "login" not in st.session_state:
    st.stop()

st.success(f"👤 {st.session_state['user']} ({st.session_state['rol']})")

# =========================
# 📦 PRODUCTOS
# =========================
df = pd.read_sql("SELECT * FROM productos", engine)

st.header("⚡ Ventas")

if not df.empty:

    for _, row in df.iterrows():

        col1, col2 = st.columns([3,1])

        with col1:

            extra = ""
            if st.session_state["rol"] == "admin":
                extra = f"💰 Costo: {row['costo']} | Profit: {row['precio'] - row['costo']}"

            st.markdown(f"""
            <div class="card">
            <b>{row['nombre']} - {row['variante']}</b><br>
            💲 {row['precio']} | Stock: {row['stock']}<br>
            {extra}
            </div>
            """, unsafe_allow_html=True)

        with col2:

            cant = st.number_input("Cant", 1, 100, key=f"c{row['id']}")

            if st.button("Vender", key=f"v{row['id']}"):

                if row["stock"] >= cant:

                    total = row["precio"] * cant
                    ganancia = (row["precio"] - row["costo"]) * cant

                    with engine.begin() as conn:

                        conn.execute(text("""
                        UPDATE productos
                        SET stock = stock - :c
                        WHERE id=:id
                        """), {"c": cant, "id": row["id"]})

                        conn.execute(text("""
                        INSERT INTO ventas
                        VALUES (DEFAULT,:p,:u,:c,:t,:g,:f)
                        """), {
                            "p": row["id"],
                            "u": st.session_state["user"],
                            "c": cant,
                            "t": total,
                            "g": ganancia,
                            "f": datetime.now()
                        })

                    st.success("✅ Vendido")
                    st.rerun()

                else:
                    st.error("Sin stock")

# =========================
# 👑 ADMIN PANEL
# =========================
if st.session_state["rol"] == "admin":

    st.divider()
    st.header("🔐 ADMIN PANEL")

    # =========================
    # 👤 USUARIOS
    # =========================
    st.subheader("👤 Usuarios")

    users = pd.read_sql("SELECT * FROM usuarios", engine)
    st.dataframe(users)

    del_user = st.text_input("Eliminar usuario")

    if st.button("🗑️ Eliminar usuario"):

        with engine.begin() as conn:
            conn.execute(text("DELETE FROM usuarios WHERE username=:u"),
                         {"u": del_user.strip().lower()})

        st.success("Usuario eliminado")
        st.rerun()

    # =========================
    # 📦 PRODUCTOS
    # =========================
    st.subheader("📦 Agregar producto")

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    cat = c1.text_input("Categoria")
    nom = c2.text_input("Nombre")
    var = c3.text_input("Variante")
    pre = c4.number_input("Precio")
    cos = c5.number_input("Costo")
    sto = c6.number_input("Stock", step=1)

    if st.button("Agregar producto"):

        with engine.begin() as conn:
            conn.execute(text("""
            INSERT INTO productos
            VALUES (DEFAULT,:c,:n,:v,:p,:co,:s)
            """), {
                "c": cat,
                "n": nom,
                "v": var,
                "p": pre,
                "co": cos,
                "s": int(sto)
            })

        st.success("Producto agregado")
        st.rerun()

    # =========================
    # ❌ ELIMINAR PRODUCTO
    # =========================
    st.subheader("🗑️ Eliminar producto")

    del_prod = st.text_input("ID producto")

    if st.button("Eliminar producto"):

        with engine.begin() as conn:
            conn.execute(text("DELETE FROM productos WHERE id=:id"),
                         {"id": del_prod})

        st.success("Producto eliminado")
        st.rerun()

    # =========================
    # 📊 DASHBOARD
    # =========================
    ventas = pd.read_sql("SELECT * FROM ventas", engine)

    if not ventas.empty:

        st.metric("💰 Total", ventas["total"].sum())
        st.metric("📈 Ganancia", ventas["ganancia"].sum())

        st.subheader("Ranking")
        st.bar_chart(ventas.groupby("usuario")["total"].sum())

    else:
        st.info("Sin ventas")
