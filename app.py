import base64
import hashlib
import uuid

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


def show_image_from_base64(img_base64, width=220):
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
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            venta_grupo TEXT
        )
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS cobros (
            id SERIAL PRIMARY KEY,
            venta_grupo TEXT,
            usuario TEXT,
            total FLOAT,
            efectivo FLOAT DEFAULT 0,
            transferencia FLOAT DEFAULT 0,
            comprobante TEXT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))

    conn.execute(text("ALTER TABLE productos ADD COLUMN IF NOT EXISTS imagen TEXT;"))
    conn.execute(text("ALTER TABLE productos ADD COLUMN IF NOT EXISTS costo FLOAT DEFAULT 0;"))
    conn.execute(text("ALTER TABLE productos ADD COLUMN IF NOT EXISTS stock INT DEFAULT 0;"))
    conn.execute(text("ALTER TABLE ventas ADD COLUMN IF NOT EXISTS venta_grupo TEXT;"))
    conn.execute(text("ALTER TABLE cobros ADD COLUMN IF NOT EXISTS comprobante TEXT;"))


# =========================
# ADMIN DEFAULT
# =========================
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
                show_image_from_base64(row.get("imagen"), width=220)

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

        st.markdown("### 💳 Forma de pago")

        colp1, colp2 = st.columns(2)

        with colp1:
            pago_efectivo = st.number_input(
                "💵 Efectivo",
                min_value=0.0,
                max_value=float(total),
                value=0.0,
                step=100.0,
                key="pago_efectivo"
            )

        with colp2:
            pago_transferencia = st.number_input(
                "🏦 Transferencia",
                min_value=0.0,
                max_value=float(total),
                value=0.0,
                step=100.0,
                key="pago_transferencia"
            )

        comprobante_transferencia = None

        if pago_transferencia > 0:
            comprobante_transferencia = st.file_uploader(
                "📸 Comprobante de transferencia",
                type=["jpg", "jpeg", "png"],
                key="comprobante_transferencia"
            )

        total_pagado = pago_efectivo + pago_transferencia
        diferencia = total_pagado - total

        st.write(f"**Pagado:** ${total_pagado:,.0f}")

        if diferencia < 0:
            st.warning(f"Faltan pagar: ${abs(diferencia):,.0f}")
        elif diferencia > 0:
            st.error(f"El pago supera el total por: ${diferencia:,.0f}")
        else:
            st.success("Pago exacto ✅")

        colb1, colb2 = st.columns(2)

        with colb1:
            if st.button("🧹 Vaciar carrito", use_container_width=True, key="vaciar_carrito"):
                st.session_state["cart"] = []
                st.rerun()

        with colb2:
            if st.button("💳 Cobrar Venta", type="primary", use_container_width=True, key="cobrar_venta"):

                if total_pagado < total:
                    st.error("❌ El pago no alcanza para cubrir el total")

                elif total_pagado > total:
                    st.error("❌ El pago no puede ser mayor al total de los productos")

                elif pago_transferencia > 0 and comprobante_transferencia is None:
                    st.error("❌ Debes subir el comprobante de transferencia")

                else:
                    try:
                        venta_grupo = str(uuid.uuid4())
                        comprobante_base64 = image_to_base64(comprobante_transferencia)

                        with engine.begin() as conn:
                            # Validar stock antes de cobrar
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

                            # Registrar cobro total de la venta
                            conn.execute(text("""
                                INSERT INTO cobros
                                (venta_grupo, usuario, total, efectivo, transferencia, comprobante, fecha)
                                VALUES (:vg, :user, :total, :efectivo, :transferencia, :comprobante, NOW())
                            """), {
                                "vg": venta_grupo,
                                "user": USER,
                                "total": total,
                                "efectivo": float(pago_efectivo),
                                "transferencia": float(pago_transferencia),
                                "comprobante": comprobante_base64
                            })

                            # Registrar productos vendidos
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
                                    INSERT INTO ventas
                                    (producto_id, usuario, cantidad, total, ganancia, fecha, venta_grupo)
                                    VALUES (:pid, :user, :qty, :total, :ganancia, NOW(), :vg)
                                """), {
                                    "pid": item["id"],
                                    "user": USER,
                                    "qty": item["qty"],
                                    "total": total_item,
                                    "ganancia": ganancia_item,
                                    "vg": venta_grupo
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
                show_image_from_base64(prod.get("imagen"), width=280)

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

    st.header("📊 Reportes de Ventas")

    if st.button("🔄 Recargar Reportes", key="recargar_reportes"):
        st.rerun()

    try:
        cobros = pd.read_sql("""
            SELECT
                id,
                venta_grupo,
                fecha,
                usuario,
                total,
                efectivo,
                transferencia,
                comprobante
            FROM cobros
            ORDER BY fecha DESC
        """, engine)

        if cobros.empty:
            st.warning("No hay ventas registradas todavía")
        else:
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("💰 Total Vendido", f"${cobros['total'].sum():,.0f}")

            with col2:
                st.metric("💵 Efectivo", f"${cobros['efectivo'].sum():,.0f}")

            with col3:
                st.metric("🏦 Transferencia", f"${cobros['transferencia'].sum():,.0f}")

            with col4:
                st.metric("🧾 Ventas", len(cobros))

            st.divider()
            st.subheader("🧾 Ventas realizadas")

            for _, cobro in cobros.iterrows():
                venta_grupo = cobro["venta_grupo"]

                titulo = (
                    f"Venta #{cobro['id']} | "
                    f"{cobro['usuario']} | "
                    f"${cobro['total']:,.0f} | "
                    f"{pd.to_datetime(cobro['fecha']).strftime('%d/%m/%Y %H:%M')}"
                )

                with st.expander(titulo):

                    st.write("### 💳 Pago")
                    p1, p2, p3 = st.columns(3)

                    with p1:
                        st.metric("Total", f"${cobro['total']:,.0f}")

                    with p2:
                        st.metric("Efectivo", f"${cobro['efectivo']:,.0f}")

                    with p3:
                        st.metric("Transferencia", f"${cobro['transferencia']:,.0f}")

                    if cobro["transferencia"] > 0:
                        st.write("### 📸 Comprobante")

                        if cobro["comprobante"]:
                            try:
                                st.image(base64.b64decode(cobro["comprobante"]), width=350)
                            except Exception:
                                st.error("No se pudo mostrar el comprobante")
                        else:
                            st.warning("Esta venta tiene transferencia pero no tiene comprobante cargado")

                    st.divider()
                    st.write("### 🛍️ Productos vendidos")

                    detalle = pd.read_sql(text("""
                        SELECT
                            v.id AS venta_id,
                            v.producto_id,
                            p.nombre AS producto,
                            p.variante AS variante,
                            v.cantidad,
                            v.total,
                            v.ganancia
                        FROM ventas v
                        LEFT JOIN productos p ON v.producto_id = p.id
                        WHERE v.venta_grupo = :vg
                        ORDER BY v.id
                    """), engine, params={"vg": venta_grupo})

                    if detalle.empty:
                        st.warning("No hay productos asociados a esta venta")
                    else:
                        st.dataframe(
                            detalle[["producto", "variante", "cantidad", "total", "ganancia"]],
                            use_container_width=True,
                            hide_index=True
                        )

                        d1, d2 = st.columns(2)

                        with d1:
                            st.metric("Total productos", f"${detalle['total'].sum():,.0f}")

                        with d2:
                            st.metric("Ganancia", f"${detalle['ganancia'].sum():,.0f}")

                    st.divider()

                    if st.button("🗑️ Eliminar esta venta y devolver stock", key=f"del_venta_grupo_{venta_grupo}"):

                        with engine.begin() as conn:
                            ventas_grupo = conn.execute(text("""
                                SELECT id, producto_id, cantidad
                                FROM ventas
                                WHERE venta_grupo = :vg
                            """), {"vg": venta_grupo}).fetchall()

                            for venta in ventas_grupo:
                                venta_id = venta[0]
                                producto_id = venta[1]
                                cantidad = venta[2]

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

                            conn.execute(text("""
                                DELETE FROM cobros
                                WHERE venta_grupo = :vg
                            """), {"vg": venta_grupo})

                        st.success("✅ Venta eliminada y stock devuelto")
                        st.rerun()

            st.divider()
            st.subheader("📊 Ranking de vendedores")

            ranking = cobros.groupby("usuario")["total"].sum()

            if not ranking.empty:
                st.bar_chart(ranking)

    except Exception as e:
        st.error(f"Error al leer los reportes: {str(e)}")

else:
    st.info("Selecciona un módulo desde la barra lateral")
