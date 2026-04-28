import base64
import hashlib
from datetime import datetime

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text


# =========================
# CONFIG / ESTILO
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
        padding: 18px;
        border: 1px solid rgba(255,255,255,0.1);
        margin-bottom: 14px;
    }

    .product-title {
        font-size: 20px;
        font-weight: 700;
        margin-bottom: 4px;
    }

    .muted {
        color: #8e8e93;
        font-size: 14px;
    }

    .price {
        color: #34c759;
        font-size: 24px;
        font-weight: 700;
    }

    h1, h2, h3 {
        font-weight: 700;
        letter-spacing: -0.02em;
    }

    .stButton>button {
        border-radius: 14px;
        height: 44px;
        font-weight: 700;
    }

    img {
        border-radius: 14px;
    }
</style>
""", unsafe_allow_html=True)


# =========================
# FUNCIONES
# =========================
def hash_pass(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def normalize_user(username: str) -> str:
    return username.strip().lower()


def image_to_base64(uploaded_file):
    if uploaded_file is None:
        return None

    file_bytes = uploaded_file.getvalue()
    encoded = base64.b64encode(file_bytes).decode("utf-8")
    return encoded


def show_product_image(img_base64, width=220):
    if img_base64 and isinstance(img_base64, str) and len(img_base64) > 20:
        try:
            st.image(base64.b64decode(img_base64), width=width)
        except Exception:
            st.markdown(
                '<div style="height:180px;background:rgba(255,255,255,0.05);'
                'border-radius:14px;display:flex;align-items:center;justify-content:center;'
                'color:#777;">Foto inválida</div>',
                unsafe_allow_html=True
            )
    else:
        st.markdown(
            '<div style="height:180px;background:rgba(255,255,255,0.05);'
            'border-radius:14px;display:flex;align-items:center;justify-content:center;'
            'color:#777;">Sin foto</div>',
            unsafe_allow_html=True
        )


def require_admin():
    if st.session_state.get("rol") != "admin":
        st.error("Acceso restringido")
        st.stop()


# =========================
# BASE DE DATOS
# =========================
DB_URL = st.secrets["DB_URL"]

engine = create_engine(
    DB_URL,
    pool_pre_ping=True,
    pool_recycle=300
)

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
            costo FLOAT DEFAULT 0,
            stock INT DEFAULT 0,
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
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))

    conn.execute(text("ALTER TABLE productos ADD COLUMN IF NOT EXISTS imagen TEXT;"))
    conn.execute(text("ALTER TABLE productos ADD COLUMN IF NOT EXISTS costo FLOAT DEFAULT 0;"))
    conn.execute(text("ALTER TABLE productos ADD COLUMN IF NOT EXISTS stock INT DEFAULT 0;"))


# ADMIN DEFAULT
with engine.begin() as conn:
    existe_admin = conn.execute(
        text("SELECT 1 FROM usuarios WHERE username='admin'")
    ).fetchone()

    if not existe_admin:
        conn.execute(text("""
            INSERT INTO usuarios(username, password, rol)
            VALUES('admin', :p, 'admin')
        """), {"p": hash_pass("1234")})


# =========================
# LOGIN
# =========================
if "login" not in st.session_state:
    st.title("📱 POINT.MOBILE")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("### Iniciar sesión")

        login_user = st.text_input("Usuario", placeholder="Usuario", key="login_user")
        login_pass = st.text_input("Contraseña", type="password", placeholder="Contraseña", key="login_pass")

        if st.button("Iniciar Sesión", type="primary", use_container_width=True, key="btn_login"):
            username = normalize_user(login_user)

            with engine.connect() as conn:
                data = conn.execute(text("""
                    SELECT * FROM usuarios
                    WHERE username=:u AND password=:p
                """), {
                    "u": username,
                    "p": hash_pass(login_pass)
                }).fetchone()

            if data:
                st.session_state["login"] = True
                st.session_state["user"] = data[1]
                st.session_state["rol"] = data[3]

                if "cart" not in st.session_state:
                    st.session_state["cart"] = []

                st.rerun()
            else:
                st.error("❌ Credenciales incorrectas")

    st.stop()


USER = st.session_state["user"]
ROL = st.session_state["rol"]

if "cart" not in st.session_state:
    st.session_state["cart"] = []


# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.markdown("<h2 style='text-align:center;'>POINT.MOBILE</h2>", unsafe_allow_html=True)
    st.write(f"**👤 Usuario:** {USER}")
    st.write(f"**🔐 Rol:** {ROL.upper()}")
    st.divider()

    menu_options = ["🛒 Agregar Producto", "🛍️ Carrito"]

    if ROL == "admin":
        menu_options.extend(["⚙️ Admin", "📊 Reportes"])

    menu = st.radio("Módulos", menu_options, label_visibility="collapsed")

    st.divider()

    if st.button("🚪 Cerrar Sesión", use_container_width=True, key="logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


# =========================
# DATA
# =========================
df_productos = pd.read_sql(
    "SELECT * FROM productos ORDER BY nombre",
    engine
)


# =========================
# 🛒 AGREGAR PRODUCTO AL CARRITO
# =========================
if menu == "🛒 Agregar Producto":
    st.header("🛒 Agregar Producto")

    search = st.text_input("🔎 Buscar producto", "", key="buscar_producto")

    if search:
        df_filtrado = df_productos[
            df_productos["nombre"].str.contains(search, case=False, na=False)
            | df_productos["variante"].fillna("").str.contains(search, case=False, na=False)
            | df_productos["categoria"].fillna("").str.contains(search, case=False, na=False)
        ]
    else:
        df_filtrado = df_productos

    if df_filtrado.empty:
        st.warning("No se encontraron productos")
    else:
        cols = st.columns(3)

        for idx, row in df_filtrado.reset_index(drop=True).iterrows():
            with cols[idx % 3]:
                show_product_image(row.get("imagen"), width=220)

                stock = int(row["stock"] or 0)
                precio = float(row["precio"] or 0)

                st.markdown(f"""
                <div class="card">
                    <div class="product-title">{row['nombre']}</div>
                    <div class="muted">{row.get('variante') or ''}</div>
                    <div class="muted">{row.get('categoria') or ''}</div>
                    <div class="price">${precio:,.0f}</div>
                    <small>Stock: {stock}</small>
                </div>
                """, unsafe_allow_html=True)

                if stock <= 0:
                    st.error("Sin stock")
                else:
                    qty = st.number_input(
                        "Cantidad",
                        min_value=1,
                        max_value=max(1, stock),
                        value=1,
                        step=1,
                        key=f"qty_{row['id']}"
                    )

                    if st.button("➕ Agregar al carrito", key=f"add_{row['id']}", use_container_width=True):
                        st.session_state["cart"].append({
                            "id": int(row["id"]),
                            "name": row["nombre"],
                            "variant": row.get("variante") or "",
                            "price": precio,
                            "cost": float(row.get("costo") or 0),
                            "qty": int(qty)
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

            with col1:
                st.write(f"**{item['name']}** {item.get('variant', '')} × {item['qty']}")

            with col2:
                st.write(f"${item['price'] * item['qty']:,.0f}")

            with col3:
                if st.button("🗑️", key=f"rm_cart_{i}"):
                    cart.pop(i)
                    st.rerun()

        st.divider()
        st.subheader(f"Total: ${total:,.0f}")

        c1, c2 = st.columns(2)

        with c1:
            if st.button("🧹 Vaciar carrito", use_container_width=True, key="vaciar_carrito"):
                st.session_state["cart"] = []
                st.rerun()

        with c2:
            if st.button("💳 Cobrar Venta", type="primary", use_container_width=True, key="cobrar_venta"):
                try:
                    with engine.begin() as conn:
                        for item in cart:
                            producto = conn.execute(text("""
                                SELECT stock, costo, precio
                                FROM productos
                                WHERE id=:id
                            """), {"id": item["id"]}).fetchone()

                            if not producto:
                                raise Exception(f"Producto no encontrado: {item['name']}")

                            stock_actual = int(producto[0] or 0)

                            if stock_actual < item["qty"]:
                                raise Exception(f"Stock insuficiente para {item['name']}")

                        for item in cart:
                            conn.execute(text("""
                                UPDATE productos
                                SET stock = stock - :q
                                WHERE id = :id
                            """), {
                                "q": item["qty"],
                                "id": item["id"]
                            })

                            total_item = item["price"] * item["qty"]
                            ganancia_item = (item["price"] - item["cost"]) * item["qty"]

                            conn.execute(text("""
                                INSERT INTO ventas (producto_id, usuario, cantidad, total, ganancia, fecha)
                                VALUES (:pid, :user, :qty, :total, :ganancia, NOW())
                            """), {
                                "pid": item["id"],
                                "user": USER,
                                "qty": item["qty"],
                                "total": total_item,
                                "ganancia": ganancia_item
                            })

                    st.session_state["cart"] = []
                    st.success("✅ Venta completada exitosamente")
                    st.rerun()

                except Exception as e:
                    st.error(f"Error al cobrar: {str(e)}")


# =========================
# ⚙️ ADMIN
# =========================
elif menu == "⚙️ Admin" and ROL == "admin":
    require_admin()

    st.header("⚙️ Administración")

    tab1, tab2 = st.tabs(["📦 Productos", "👥 Usuarios"])

    # =========================
    # PRODUCTOS
    # =========================
    with tab1:
        st.subheader("Agregar Nuevo Producto")

        with st.form("form_nuevo_producto", clear_on_submit=True):
            col1, col2 = st.columns(2)

            with col1:
                nombre = st.text_input("Nombre del Producto *", key="nuevo_nombre")
                categoria = st.text_input("Categoría", key="nueva_categoria")
                variante = st.text_input("Variante", key="nueva_variante")

            with col2:
                precio = st.number_input("Precio de Venta ($)", min_value=0.0, step=100.0, key="nuevo_precio")
                costo = st.number_input("Costo ($)", min_value=0.0, step=100.0, key="nuevo_costo")
                stock = st.number_input("Stock Inicial", min_value=0, value=10, step=1, key="nuevo_stock")

            imagen = st.file_uploader(
                "📸 Foto del producto",
                type=["jpg", "jpeg", "png"],
                key="nueva_imagen"
            )

            submit_producto = st.form_submit_button("Guardar Producto", type="primary")

            if submit_producto:
                if nombre and precio > 0:
                    img_base64 = image_to_base64(imagen)

                    with engine.begin() as conn:
                        conn.execute(text("""
                            INSERT INTO productos (categoria, nombre, variante, precio, costo, stock, imagen)
                            VALUES (:cat, :nom, :var, :pre, :cos, :sto, :img)
                        """), {
                            "cat": categoria,
                            "nom": nombre,
                            "var": variante,
                            "pre": precio,
                            "cos": costo,
                            "sto": int(stock),
                            "img": img_base64
                        })

                    st.success("✅ Producto agregado correctamente")
                    st.rerun()
                else:
                    st.error("Nombre y precio son obligatorios")

        st.divider()
        st.subheader("Productos Registrados")

        df_productos_admin = pd.read_sql(
            "SELECT * FROM productos ORDER BY nombre",
            engine
        )

        if df_productos_admin.empty:
            st.info("No hay productos registrados")
        else:
            for _, row in df_productos_admin.iterrows():
                col1, col2, col3, col4 = st.columns([3, 2, 1.5, 1.5])

                with col1:
                    st.write(f"**{row['nombre']}** — {row.get('variante') or ''}")

                with col2:
                    st.write(f"${float(row['precio']):,.0f} | Stock: **{int(row['stock'] or 0)}**")

                with col3:
                    if st.button("✏️ Editar", key=f"edit_prod_{row['id']}"):
                        st.session_state["edit_product_id"] = int(row["id"])
                        st.rerun()

                with col4:
                    if st.button("🗑️ Eliminar", key=f"del_prod_{row['id']}"):
                        with engine.begin() as conn:
                            conn.execute(
                                text("DELETE FROM productos WHERE id = :id"),
                                {"id": int(row["id"])}
                            )
                        st.success("Producto eliminado")
                        st.rerun()

        if "edit_product_id" in st.session_state:
            pid = int(st.session_state["edit_product_id"])

            prod_df = pd.read_sql(
                text("SELECT * FROM productos WHERE id=:id"),
                engine,
                params={"id": pid}
            )

            if prod_df.empty:
                st.error("Producto no encontrado")
                del st.session_state["edit_product_id"]
                st.rerun()

            prod = prod_df.iloc[0]

            st.divider()
            st.subheader(f"Editando: {prod['nombre']}")

            with st.form("form_editar_producto"):
                col1, col2 = st.columns(2)

                with col1:
                    e_nombre = st.text_input("Nombre", value=prod["nombre"], key="edit_nombre")
                    e_categoria = st.text_input("Categoría", value=prod.get("categoria") or "", key="edit_categoria")
                    e_variante = st.text_input("Variante", value=prod.get("variante") or "", key="edit_variante")

                with col2:
                    e_precio = st.number_input("Precio", value=float(prod["precio"] or 0), key="edit_precio")
                    e_costo = st.number_input("Costo", value=float(prod.get("costo") or 0), key="edit_costo")
                    e_stock = st.number_input("Stock", value=int(prod["stock"] or 0), step=1, key="edit_stock")

                st.write("Foto actual:")
                show_product_image(prod.get("imagen"), width=280)

                nueva_imagen = st.file_uploader(
                    "Cambiar foto",
                    type=["jpg", "jpeg", "png"],
                    key="edit_imagen"
                )

                col_save, col_cancel = st.columns(2)

                with col_save:
                    guardar_cambios = st.form_submit_button("💾 Guardar Cambios", type="primary")

                with col_cancel:
                    cancelar = st.form_submit_button("Cancelar")

                if cancelar:
                    del st.session_state["edit_product_id"]
                    st.rerun()

                if guardar_cambios:
                    img_base64 = prod.get("imagen")

                    if nueva_imagen:
                        img_base64 = image_to_base64(nueva_imagen)

                    with engine.begin() as conn:
                        conn.execute(text("""
                            UPDATE productos
                            SET nombre=:nom,
                                categoria=:cat,
                                variante=:var,
                                precio=:pre,
                                costo=:cos,
                                stock=:sto,
                                imagen=:img
                            WHERE id=:id
                        """), {
                            "nom": e_nombre,
                            "cat": e_categoria,
                            "var": e_variante,
                            "pre": e_precio,
                            "cos": e_costo,
                            "sto": int(e_stock),
                            "img": img_base64,
                            "id": pid
                        })

                    del st.session_state["edit_product_id"]
                    st.success("Producto actualizado")
                    st.rerun()

    # =========================
    # USUARIOS
    # =========================
    with tab2:
        st.subheader("Usuarios del Sistema")

        df_usuarios = pd.read_sql(
            "SELECT id, username, rol FROM usuarios ORDER BY username",
            engine
        )

        st.dataframe(df_usuarios, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("Crear Nuevo Usuario")

        col1, col2, col3 = st.columns(3)

        with col1:
            new_user = st.text_input("Nombre de usuario", key="crear_user_nombre")

        with col2:
            new_pass = st.text_input("Contraseña", type="password", key="crear_user_pass")

        with col3:
            new_rol = st.selectbox("Rol", ["vendedor", "admin"], key="crear_user_rol")

        if st.button("Crear Usuario", type="primary", key="btn_crear_usuario"):
            if new_user and new_pass:
                try:
                    with engine.begin() as conn:
                        conn.execute(text("""
                            INSERT INTO usuarios(username, password, rol)
                            VALUES(:u, :p, :r)
                        """), {
                            "u": normalize_user(new_user),
                            "p": hash_pass(new_pass),
                            "r": new_rol
                        })

                    st.success(f"✅ Usuario '{new_user}' creado correctamente")
                    st.rerun()

                except Exception:
                    st.error("El usuario ya existe")
            else:
                st.warning("Completa todos los campos")

        st.divider()
        st.subheader("🗑️ Eliminar Usuario")

        usuarios_eliminables = df_usuarios[df_usuarios["username"] != "admin"]

        if usuarios_eliminables.empty:
            st.info("No hay usuarios eliminables")
        else:
            usuario_a_eliminar = st.selectbox(
                "Seleccionar usuario",
                usuarios_eliminables["username"].tolist(),
                key="select_eliminar_usuario"
            )

            if st.button("Eliminar Usuario", type="primary", key="btn_eliminar_usuario"):
                with engine.begin() as conn:
                    conn.execute(text("""
                        DELETE FROM usuarios
                        WHERE username = :u
                    """), {"u": usuario_a_eliminar})

                st.success(f"✅ Usuario '{usuario_a_eliminar}' eliminado")
                st.rerun()


# =========================
# 📊 REPORTES
# =========================
elif menu == "📊 Reportes" and ROL == "admin":
    require_admin()

    st.header("📊 Reportes y Gestión de Ventas")

    if st.button("🔄 Recargar Reportes", key="recargar_reportes"):
        st.rerun()

    try:
        ventas = pd.read_sql("""
            SELECT
                v.id AS venta_id,
                v.producto_id,
                v.fecha,
                v.usuario,
                p.nombre AS producto,
                v.cantidad,
                v.total,
                v.ganancia
            FROM ventas v
            LEFT JOIN productos p ON v.producto_id = p.id
            ORDER BY v.fecha DESC
        """, engine)

        st.success(f"Total de ventas encontradas: {len(ventas)}")

        if ventas.empty:
            st.warning("No hay ventas registradas aún")
        else:
            st.subheader("Selecciona las ventas que deseas eliminar")

            ventas = ventas.copy()
            ventas["Seleccionar"] = False

            edited_df = st.data_editor(
                ventas[[
                    "Seleccionar",
                    "venta_id",
                    "producto_id",
                    "fecha",
                    "usuario",
                    "producto",
                    "cantidad",
                    "total",
                    "ganancia"
                ]],
                hide_index=True,
                column_config={
                    "Seleccionar": st.column_config.CheckboxColumn("Seleccionar", default=False),
                    "venta_id": st.column_config.NumberColumn("ID Venta", disabled=True),
                    "producto_id": st.column_config.NumberColumn("ID Producto", disabled=True),
                    "fecha": st.column_config.DatetimeColumn("Fecha", format="DD/MM/YYYY HH:mm"),
                    "total": st.column_config.NumberColumn("Total", format="$%d"),
                    "ganancia": st.column_config.NumberColumn("Ganancia", format="$%d"),
                },
                disabled=[
                    "venta_id",
                    "producto_id",
                    "fecha",
                    "usuario",
                    "producto",
                    "cantidad",
                    "total",
                    "ganancia"
                ],
                use_container_width=True,
                key="editor_ventas"
            )

            if st.button("🗑️ Eliminar Ventas Seleccionadas", type="primary", key="eliminar_ventas"):
                selected_rows = edited_df[edited_df["Seleccionar"] == True]

                if selected_rows.empty:
                    st.warning("No has seleccionado ninguna venta")
                else:
                    with engine.begin() as conn:
                        for _, row in selected_rows.iterrows():
                            venta_id = int(row["venta_id"])
                            producto_id = int(row["producto_id"]) if pd.notna(row["producto_id"]) else None
                            cantidad = int(row["cantidad"])

                            if producto_id:
                                conn.execute(text("""
                                    UPDATE productos
                                    SET stock = stock + :q
                                    WHERE id = :pid
                                """), {
                                    "q": cantidad,
                                    "pid": producto_id
                                })

                            conn.execute(text("""
                                DELETE FROM ventas
                                WHERE id = :id
                            """), {"id": venta_id})

                    st.success(f"✅ Se eliminaron {len(selected_rows)} venta(s) y se devolvió el stock")
                    st.rerun()

            st.divider()

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Total Vendido", f"${ventas['total'].sum():,.0f}")

            with col2:
                st.metric("Ganancia Total", f"${ventas['ganancia'].sum():,.0f}")

            with col3:
                st.metric("Ventas Totales", len(ventas))

            st.subheader("Ventas por usuario")
            st.bar_chart(ventas.groupby("usuario")["total"].sum())

    except Exception as e:
        st.error(f"Error al leer las ventas: {str(e)}")


else:
    st.info("Selecciona un módulo desde la barra lateral")
