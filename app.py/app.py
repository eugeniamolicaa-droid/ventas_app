import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib

# =========================
# 🔐 FUNCIONES SEGURIDAD
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
height: 70px;
font-size: 18px;
border-radius: 12px;
background-color: #1f6feb;
color: white;
font-weight: bold;
}
.stButton>button:hover {background-color: #388bfd;}
.card {
padding: 15px;
border-radius: 15px;
background-color: #161b22;
margin-bottom: 10px;
text-align: center;
box-shadow: 0px 0px 10px rgba(0,0,0,0.5);
}
</style>
""", unsafe_allow_html=True)

# =========================
# DB
# =========================
conn = sqlite3.connect("stock.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
id INTEGER PRIMARY KEY AUTOINCREMENT,
username TEXT,
password TEXT,
rol TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS productos (
id INTEGER PRIMARY KEY AUTOINCREMENT,
categoria TEXT,
nombre TEXT,
variante TEXT,
precio REAL,
costo REAL,
stock INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS ventas (
id INTEGER PRIMARY KEY AUTOINCREMENT,
producto_id INTEGER,
cantidad INTEGER,
total REAL,
ganancia REAL,
fecha TEXT
)
""")

conn.commit()

# ADMIN DEFAULT
cursor.execute("SELECT * FROM usuarios")
if not cursor.fetchall():
    cursor.execute("INSERT INTO usuarios VALUES (NULL,?,?,?)",
                   ("admin", hash_pass("1234"), "admin"))
    conn.commit()

# =========================
# LOGIN
# =========================
st.title("📱 Sistema de Ventas PRO")

user = st.text_input("Usuario")
pwd = st.text_input("Clave", type="password")

if st.button("Entrar"):
    data = cursor.execute(
        "SELECT * FROM usuarios WHERE username=? AND password=?",
        (user, hash_pass(pwd))
    ).fetchone()

    if data:
        st.session_state["login"] = True
        st.session_state["rol"] = data[3]
        st.rerun()
    else:
        st.error("Datos incorrectos")

if "login" not in st.session_state:
    st.stop()

# =========================
# CARGA PRODUCTOS
# =========================
df = pd.read_sql("SELECT * FROM productos", conn)

if df.empty:
    st.warning("⚠️ No hay productos cargados, agrega desde el panel admin")

# =========================
# BUSCADOR
# =========================
busqueda = st.text_input("🔍 Buscar producto")

if busqueda:
    df = df[df["nombre"].str.contains(busqueda, case=False)]

# =========================
# VENTA
# =========================
st.header("⚡ Venta rápida")

for categoria in df["categoria"].unique():
    st.subheader(f"📦 {categoria}")

    df_cat = df[df["categoria"] == categoria]

    for nombre in df_cat["nombre"].unique():
        st.markdown(f"## {nombre}")

        productos = df_cat[df_cat["nombre"] == nombre]

        cols = st.columns(2)

        for i, (_, row) in enumerate(productos.iterrows()):
            col = cols[i % 2]

            stock_color = "red" if row["stock"] <= 3 else "white"

            with col:
                st.markdown(f"""
                <div class="card">
                <h3>{row['variante']}</h3>
                <p>💲{row['precio']}</p>
                <p style="color:{stock_color}">Stock: {row['stock']}</p>
                </div>
                """, unsafe_allow_html=True)

                cantidad = st.number_input(
                    "Cantidad", min_value=1, value=1,
                    key=f"cant_{row['id']}"
                )

                if st.button(f"Vender ${row['precio']}", key=f"v_{row['id']}", use_container_width=True):

                    if row["stock"] >= cantidad:

                        ganancia = (row["precio"] - row["costo"]) * cantidad
                        total = row["precio"] * cantidad

                        cursor.execute("UPDATE productos SET stock=stock-? WHERE id=?",
                                       (cantidad, row["id"]))

                        cursor.execute("""
                        INSERT INTO ventas (producto_id,cantidad,total,ganancia,fecha)
                        VALUES (?,?,?,?,?)
                        """, (row["id"], cantidad, total, ganancia, datetime.now()))

                        conn.commit()
                        st.success("✅ Venta realizada")
                        st.rerun()
                    else:
                        st.error("❌ Stock insuficiente")

            if row["stock"] <= 3:
                st.warning(f"⚠️ Bajo stock en {row['nombre']} - {row['variante']}")

# =========================
# ADMIN
# =========================
if st.session_state["rol"] == "admin":
    st.divider()
    st.header("🔐 Panel Admin")

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    categoria = c1.text_input("Categoría")
    nombre = c2.text_input("Nombre")
    variante = c3.text_input("Variante")
    precio = c4.number_input("Precio")
    costo = c5.number_input("Costo")
    stock = c6.number_input("Stock")

    if st.button("Guardar producto"):
        cursor.execute("""
        INSERT INTO productos (categoria,nombre,variante,precio,costo,stock)
        VALUES (?,?,?,?,?,?)
        """, (categoria,nombre,variante,precio,costo,stock))

        conn.commit()
        st.success("Producto agregado")
        st.rerun()

    # =========================
    # DASHBOARD
    # =========================
    ventas = pd.read_sql("SELECT * FROM ventas", conn)

    if not ventas.empty:
        ventas["fecha"] = pd.to_datetime(ventas["fecha"])

        hoy = ventas[ventas["fecha"].dt.date == datetime.now().date()]

        st.metric("💰 Total vendido", ventas["total"].sum())
        st.metric("📈 Ganancia total", ventas["ganancia"].sum())
        st.metric("📅 Ventas hoy", hoy["total"].sum())

    if st.button("📥 Exportar Excel"):
        ventas.to_excel("ventas.xlsx", index=False)
        st.success("Excel exportado")