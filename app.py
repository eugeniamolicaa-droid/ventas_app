import streamlit as st
import pandas as pd
from datetime import datetime
import hashlib
from sqlalchemy import create_engine, text

engine = create_engine(
    st.secrets["DB_URL"],
    pool_pre_ping=True
)

# 🧪 TEST DE CONEXIÓN (TEMPORAL)
with engine.connect() as conn:
    st.write("Conexión OK", conn.execute(text("SELECT 1")).fetchone())

# =========================
# 🔐 FUNCIONES
# =========================
def hash_pass(p):
    return hashlib.sha256(p.encode()).hexdigest()

# =========================
# 🎨 CONFIG
# =========================
st.set_page_config(layout="wide")

# =========================
# DB
# =========================
engine = create_engine(st.secrets["DB_URL"], pool_pre_ping=True)

# =========================
# LOGIN
# =========================
st.title("📱 Sistema de Ventas PRO")

user = st.text_input("Usuario")
pwd = st.text_input("Clave", type="password")

if st.button("Entrar"):
    with engine.connect() as conn:
        data = conn.execute(text("""
        SELECT * FROM usuarios
        WHERE username = :u AND password = :p
        """), {"u": user, "p": hash_pass(pwd)}).fetchone()

    if data:
        st.session_state["login"] = True
        st.session_state["rol"] = data[3]
        st.session_state["user"] = data[1]
        st.rerun()
    else:
        st.error("Datos incorrectos")

if "login" not in st.session_state:
    st.stop()

st.write(f"👤 {st.session_state['user']} | {st.session_state['rol']}")

# =========================
# PRODUCTOS
# =========================
df = pd.read_sql("SELECT * FROM productos", engine)

if df.empty:
    st.warning("⚠️ No hay productos")

# =========================
# BUSCADOR
# =========================
busqueda = st.text_input("🔍 Buscar")

if busqueda:
    df = df[df["nombre"].str.contains(busqueda, case=False)]

# =========================
# VENTA
# =========================
st.header("⚡ Venta rápida")

for categoria in df["categoria"].unique():
    st.subheader(categoria)

    df_cat = df[df["categoria"] == categoria]

    for nombre in df_cat["nombre"].unique():
        st.markdown(f"### {nombre}")

        productos = df_cat[df_cat["nombre"] == nombre]

        cols = st.columns(2)

        for i, (_, row) in enumerate(productos.iterrows()):
            col = cols[i % 2]

            with col:
                st.write(f"{row['variante']} - ${row['precio']}")
                st.write(f"Stock: {row['stock']}")

                cantidad = st.number_input(
                    "Cantidad", min_value=1, value=1,
                    key=f"c_{row['id']}"
                )

                if st.button("Vender", key=f"v_{row['id']}"):

                    if row["stock"] >= cantidad:

                        total = row["precio"] * cantidad
                        ganancia = (row["precio"] - row["costo"]) * cantidad

                        with engine.begin() as conn:
                            conn.execute(text("""
                            UPDATE productos SET stock = stock - :cant WHERE id = :id
                            """), {"cant": cantidad, "id": row["id"]})

                            conn.execute(text("""
                            INSERT INTO ventas (producto_id,usuario,cantidad,total,ganancia,fecha)
                            VALUES (:p,:u,:c,:t,:g,:f)
                            """), {
                                "p": row["id"],
                                "u": st.session_state["user"],
                                "c": cantidad,
                                "t": total,
                                "g": ganancia,
                                "f": datetime.now()
                            })

                        st.success("Venta realizada")
                        st.rerun()
                    else:
                        st.error("Stock insuficiente")

# =========================
# ADMIN
# =========================
if st.session_state["rol"] == "admin":

    st.divider()
    st.header("🔐 Admin")

    # CREAR USUARIO
    st.subheader("👤 Usuario")

    new_user = st.text_input("Usuario nuevo")
    new_pass = st.text_input("Clave", type="password")
    new_rol = st.selectbox("Rol", ["admin", "vendedor"])

    if st.button("Crear usuario"):

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

    # PRODUCTO
    st.subheader("📦 Producto")

    categoria = st.text_input("Categoría")
    nombre = st.text_input("Nombre")
    variante = st.text_input("Variante")
    precio = st.number_input("Precio")
    costo = st.number_input("Costo")
    stock = st.number_input("Stock")

    if st.button("Guardar producto"):
        with engine.begin() as conn:
            conn.execute(text("""
            INSERT INTO productos (categoria,nombre,variante,precio,costo,stock)
            VALUES (:c,:n,:v,:p,:co,:s)
            """), {
                "c": categoria,
                "n": nombre,
                "v": variante,
                "p": precio,
                "co": costo,
                "s": stock
            })

        st.success("Producto agregado")
        st.rerun()

    # DASHBOARD
    st.subheader("📊 Dashboard")

    ventas = pd.read_sql("SELECT * FROM ventas", engine)

    if not ventas.empty:
        st.metric("Total", ventas["total"].sum())

        ranking = ventas.groupby("usuario")["total"].sum()
        st.bar_chart(ranking)
