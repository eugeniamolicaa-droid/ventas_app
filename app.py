import streamlit as st
import pandas as pd
from datetime import datetime
import hashlib
from sqlalchemy import create_engine, text

# =========================
# 🎨 UI ERP STYLE
# =========================
st.set_page_config(page_title="ERP PRO", layout="wide")

st.markdown("""
<style>
body {
    background: #0b0f14;
    color: white;
    font-family: -apple-system;
}

.card {
    background: rgba(255,255,255,0.06);
    padding: 14px;
    border-radius: 16px;
    margin: 10px 0;
    backdrop-filter: blur(10px);
}

section[data-testid="stSidebar"] {
    background: #0a0d12;
}
</style>
""", unsafe_allow_html=True)

# =========================
# 🔐 SECURITY
# =========================
def hash_pass(p):
    return hashlib.sha256(p.encode()).hexdigest()

# =========================
# 🔌 DB
# =========================
DB_URL = st.secrets["DB_URL"]
engine = create_engine(DB_URL, pool_pre_ping=True)

# =========================
# 🧱 INIT TABLES ERP
# =========================
with engine.begin() as conn:

    conn.execute(text("""
    CREATE TABLE IF NOT EXISTS usuarios(
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT,
        rol TEXT
    )
    """))

    conn.execute(text("""
    CREATE TABLE IF NOT EXISTS productos(
        id SERIAL PRIMARY KEY,
        categoria TEXT,
        nombre TEXT,
        variante TEXT,
        precio FLOAT,
        costo FLOAT,
        stock INT,
        imagen TEXT
    )
    """))

    conn.execute(text("""
    CREATE TABLE IF NOT EXISTS ventas(
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
        INSERT INTO usuarios(username,password,rol)
        VALUES('admin',:p,'admin')
        """), {"p": hash_pass("1234")})

# =========================
# 🔐 LOGIN
# =========================
st.title("🏢 ERP PRO SYSTEM")

user = st.text_input("Usuario")
pwd = st.text_input("Clave", type="password")

if st.button("Entrar"):

    with engine.connect() as conn:
        data = conn.execute(text("""
        SELECT * FROM usuarios
        WHERE username=:u AND password=:p
        """), {"u":user,"p":hash_pass(pwd)}).fetchone()

    if data:
        st.session_state["login"] = True
        st.session_state["user"] = data[1]
        st.session_state["rol"] = data[3]
        st.session_state["cart"] = []
        st.session_state["cash_open"] = True
        st.rerun()

    else:
        st.error("Login incorrecto")

if "login" not in st.session_state:
    st.stop()

USER = st.session_state["user"]
ROL = st.session_state["rol"]

# =========================
# SIDEBAR ERP
# =========================
st.sidebar.title("ERP PRO")
st.sidebar.write(f"👤 {USER}")
st.sidebar.write(f"🔐 {ROL}")

menu = st.sidebar.radio("Módulos", ["POS", "Carrito", "Admin", "Caja"])

df = pd.read_sql("SELECT * FROM productos", engine)

# =========================
# 🛒 POS
# =========================
if menu == "POS":

    st.header("🛒 Punto de Venta")

    for _, r in df.iterrows():

        st.markdown(f"""
        <div class="card">
        <b>{r['nombre']}</b> - {r['variante']}<br>
        💲 {r['precio']} | Stock: {r['stock']}
        </div>
        """, unsafe_allow_html=True)

        qty = st.number_input("Cantidad", 1, 20, key=f"q{r['id']}")

        if st.button("Agregar", key=f"a{r['id']}"):

            st.session_state["cart"].append({
                "id": r["id"],
                "name": r["nombre"],
                "price": r["precio"],
                "qty": qty
            })

            st.success("Agregado")

# =========================
# 🧾 CARRITO ERP
# =========================
elif menu == "Carrito":

    st.header("🧾 Carrito")

    cart = st.session_state["cart"]

    if not cart:
        st.info("Vacío")
    else:

        total = 0

        for i, item in enumerate(cart):
            sub = item["price"] * item["qty"]
            total += sub

            col1, col2 = st.columns([3,1])

            with col1:
                st.write(f"{item['name']} x{item['qty']} = {sub}")

            with col2:
                if st.button("❌", key=f"rm{i}"):
                    cart.pop(i)
                    st.rerun()

        st.divider()
        st.subheader(f"TOTAL: {total}")

        if st.button("💳 Cobrar"):

            with engine.begin() as conn:

                for item in cart:

                    conn.execute(text("""
                    UPDATE productos SET stock = stock - :q WHERE id=:id
                    """), {"q":item["qty"],"id":item["id"]})

                    conn.execute(text("""
                    INSERT INTO ventas(producto_id,usuario,cantidad,total,ganancia,fecha)
                    VALUES(:p,:u,:c,:t,:g,:f)
                    """), {
                        "p":item["id"],
                        "u":USER,
                        "c":item["qty"],
                        "t":item["price"]*item["qty"],
                        "g":item["price"]*item["qty"]*0.3,
                        "f":datetime.now()
                    })

            st.session_state["cart"] = []
            st.success("Venta completada")
            st.rerun()

# =========================
# 👑 ADMIN ERP
# =========================
elif menu == "Admin" and ROL == "admin":

    st.header("👑 ERP ADMIN")

    users = pd.read_sql("SELECT * FROM usuarios", engine)
    st.subheader("Usuarios")
    st.dataframe(users)

    st.subheader("Crear usuario")

    u,p,r = st.columns(3)
    nu = u.text_input("user")
    np = p.text_input("pass", type="password")
    nr = r.selectbox("rol",["admin","vendedor"])

    if st.button("Crear usuario"):
        with engine.begin() as conn:
            conn.execute(text("""
            INSERT INTO usuarios(username,password,rol)
            VALUES(:u,:p,:r)
            """), {"u":nu,"p":hash_pass(np),"r":nr})
        st.success("OK")

# =========================
# 💰 CAJA ERP
# =========================
elif menu == "Caja":

    st.header("💰 Caja")

    ventas = pd.read_sql("SELECT * FROM ventas", engine)

    if not ventas.empty:
        st.metric("Total vendido", ventas["total"].sum())
        st.metric("Ganancia", ventas["ganancia"].sum())
        st.bar_chart(ventas.groupby("usuario")["total"].sum())
