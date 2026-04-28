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
    height: 60px;
    font-size: 16px;
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
# 🧠 CONEXIÓN SUPABASE
# =========================
from sqlalchemy import create_engine
import streamlit as st

# =========================
# 🔌 CONEXIÓN A SUPABASE (POOLER IPV4)
# =========================

DB_URL = st.secrets["DB_URL"]

engine = create_engine(
    DB_URL,
    pool_pre_ping=True,   # evita conexiones muertas
    pool_recycle=300,     # refresca conexiones viejas
    pool_size=5,          # conexiones activas
    max_overflow=10,      # extra si hay demanda
    echo=False            # ponelo True solo para debug
)
# =========================
# 🧱 CREAR TABLAS (AUTO)
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

user = st.text_input("Usuario")
pwd = st.text_input("Clave", type="password")

if st.button("Entrar"):

    with engine.connect() as conn:
        data = conn.execute(text("""
            SELECT * FROM usuarios
            WHERE username=:u AND password=:p
        """), {
            "u": user,
            "p": hash_pass(pwd)
        }).fetchone()

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

busqueda = st.text_input("🔍 Buscar")

if busqueda:
    df = df[df["nombre"].str.contains(busqueda, case=False)]

st.header("⚡ Venta")

if not df.empty:

    for cat in df["categoria"].unique():
        st.subheader(cat)
        df_cat = df[df["categoria"] == cat]

        for _, row in df_cat.iterrows():

            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(f"""
                <div class="card">
                <b>{row['nombre']} - {row['variante']}</b><br>
                💲 {row['precio']} | Stock: {row['stock']}
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
                                WHERE id = :id
                            """), {"c": cant, "id": row["id"]})

                            conn.execute(text("""
                                INSERT INTO ventas
                                (producto_id,usuario,cantidad,total,ganancia,fecha)
                                VALUES (:p,:u,:c,:t,:g,:f)
                            """), {
                                "p": row["id"],
                                "u": st.session_state["user"],
                                "c": cant,
                                "t": total,
                                "g": ganancia,
                                "f": datetime.now()
                            })

                        st.success("✅ Venta realizada")
                        st.rerun()

                    else:
                        st.error("❌ Sin stock")

# =========================
# 🔐 ADMIN PANEL
# =========================
if st.session_state["rol"] == "admin":

    st.divider()
    st.header("🔐 Admin")

    # 👤 USUARIOS
    st.subheader("Crear usuario")

    u1, u2, u3 = st.columns(3)
    new_user = u1.text_input("Usuario", key="u")
    new_pass = u2.text_input("Clave", type="password", key="p")
    new_rol = u3.selectbox("Rol", ["admin", "vendedor"], key="r")

    if st.button("Crear"):

        with engine.begin() as conn:
            existe = conn.execute(text("""
                SELECT * FROM usuarios WHERE username=:u
            """), {"u": new_user}).fetchone()

            if existe:
                st.error("Ya existe")
            else:
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

    # 📊 DASHBOARD
    st.subheader("📊 Dashboard")

    ventas = pd.read_sql("SELECT * FROM ventas", engine)

    if not ventas.empty:

        ventas["fecha"] = pd.to_datetime(ventas["fecha"])

        st.metric("💰 Total", ventas["total"].sum())
        st.metric("📈 Ganancia", ventas["ganancia"].sum())

        st.subheader("Ranking")
        st.bar_chart(ventas.groupby("usuario")["total"].sum())

    else:
        st.info("Sin ventas")
