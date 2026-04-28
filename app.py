import streamlit as st
import pandas as pd
from datetime import datetime
import hashlib
from sqlalchemy import create_engine, text

# =========================
# 🍎 UI GOD MODE
# =========================
st.set_page_config(page_title="SHOP PRO", layout="wide")

st.markdown("""
<style>
html, body {
    background: radial-gradient(circle at top, #0b0f1a, #05070d);
    color: white;
    font-family: -apple-system, BlinkMacSystemFont;
}

.card {
    background: rgba(255,255,255,0.06);
    padding: 14px;
    border-radius: 18px;
    margin: 10px 0;
    backdrop-filter: blur(14px);
    box-shadow: 0 8px 25px rgba(0,0,0,0.4);
}

button {
    border-radius: 12px !important;
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
# 🧱 INIT TABLES
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
        imagen TEXT
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
        INSERT INTO usuarios(username,password,rol)
        VALUES('admin',:p,'admin')
        """), {"p": hash_pass("1234")})

# =========================
# 🔐 LOGIN
# =========================
st.title("🛍️ SHOP PRO — GOD MODE")

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
        st.rerun()
    else:
        st.error("Login incorrecto")

if "login" not in st.session_state:
    st.stop()

USER = st.session_state["user"]
ROL = st.session_state["rol"]

st.sidebar.success(USER)
st.sidebar.info(ROL)

menu = st.sidebar.radio("Navegación", ["🛒 Tienda", "🧾 Carrito", "📦 Admin"])

df = pd.read_sql("SELECT * FROM productos", engine)

# =========================
# 🛒 TIENDA
# =========================
if menu == "🛒 Tienda":

    st.header("🛍️ Productos")

    for _, r in df.iterrows():

        st.markdown(f"""
        <div class="card">
        <b>{r['nombre']} - {r['variante']}</b><br>
        💲 {r['precio']} | Stock: {r['stock']}
        </div>
        """, unsafe_allow_html=True)

        qty = st.number_input("Cantidad", 1, 20, key=f"q{r['id']}")

        if st.button("Agregar al carrito", key=f"a{r['id']}"):

            st.session_state["cart"].append({
                "id": r["id"],
                "name": r["nombre"],
                "price": r["precio"],
                "qty": qty
            })

            st.success("Agregado al carrito")

# =========================
# 🧾 CARRITO (SHOPIFY CORE)
# =========================
elif menu == "🧾 Carrito":

    st.header("🧾 Tu carrito")

    cart = st.session_state["cart"]

    if not cart:
        st.info("Carrito vacío")
    else:

        total = 0

        for item in cart:
            subtotal = item["price"] * item["qty"]
            total += subtotal

            st.write(f"{item['name']} x{item['qty']} = ${subtotal}")

        st.divider()
        st.subheader(f"TOTAL: ${total}")

        if st.button("💳 FINALIZAR COMPRA"):

            with engine.begin() as conn:

                for item in cart:

                    conn.execute(text("""
                    UPDATE productos
                    SET stock = stock - :q
                    WHERE id=:id
                    """), {"q":item["qty"],"id":item["id"]})

                    conn.execute(text("""
                    INSERT INTO ventas
                    (producto_id,usuario,cantidad,total,ganancia,fecha)
                    VALUES(:p,:u,:c,:t,:g,:f)
                    """), {
                        "p": item["id"],
                        "u": USER,
                        "c": item["qty"],
                        "t": item["price"] * item["qty"],
                        "g": item["price"] * item["qty"] * 0.3,
                        "f": datetime.now()
                    })

            st.session_state["cart"] = []
            st.success("Compra realizada")
            st.rerun()

# =========================
# 👑 ADMIN GOD MODE
# =========================
elif menu == "📦 Admin" and ROL == "admin":

    st.header("👑 PANEL DIOS")

    users = pd.read_sql("SELECT id,username,rol FROM usuarios", engine)
    st.subheader("Usuarios")
    st.dataframe(users)

    st.subheader("Crear usuario")

    u,p,r = st.columns(3)
    nu = u.text_input("user")
    np = p.text_input("pass", type="password")
    nr = r.selectbox("rol",["admin","vendedor"])

    if st.button("Crear"):
        with engine.begin() as conn:
            conn.execute(text("""
            INSERT INTO usuarios(username,password,rol)
            VALUES(:u,:p,:r)
            """), {"u":nu,"p":hash_pass(np),"r":nr})

        st.success("Usuario creado")

    st.subheader("Eliminar usuario")

    delu = st.selectbox("usuario", users["username"])

    if st.button("Eliminar"):
        if delu != "admin":
            with engine.begin() as conn:
                conn.execute(text("DELETE FROM usuarios WHERE username=:u"), {"u":delu})
            st.success("Eliminado")

    st.subheader("📊 Dashboard")

    ventas = pd.read_sql("SELECT * FROM ventas", engine)

    if not ventas.empty:
        st.metric("Ventas", ventas["total"].sum())
        st.metric("Ganancia", ventas["ganancia"].sum())
        st.bar_chart(ventas.groupby("usuario")["total"].sum())
