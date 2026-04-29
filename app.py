import base64
import hashlib
import uuid
from datetime import datetime
from io import BytesIO

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from sqlalchemy import create_engine, text
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas


# =========================
# CONFIG / ESTILO
# =========================
st.set_page_config(
    page_title="POINT.MOBILE",
    layout="wide",
    page_icon="📱",
    initial_sidebar_state="collapsed"
)

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

    /* =========================
       POS / VENTAS UI
    ========================= */

    .pos-hero {
        background: linear-gradient(135deg, rgba(0,122,255,0.22), rgba(52,199,89,0.12));
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 28px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.35);
    }

    .pos-title {
        font-size: 34px;
        font-weight: 800;
        letter-spacing: -0.04em;
        margin-bottom: 4px;
    }

    .pos-subtitle {
        color: #a1a1aa;
        font-size: 15px;
    }

    .metric-pill {
        background: rgba(255,255,255,0.08);
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 18px;
        padding: 14px 16px;
        text-align: center;
    }

    .metric-pill .label {
        color: #8e8e93;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    .metric-pill .value {
        color: #f5f5f7;
        font-size: 22px;
        font-weight: 800;
        margin-top: 4px;
    }

    .category-chip {
        display: inline-block;
        padding: 8px 14px;
        margin: 4px 6px 10px 0;
        background: rgba(255,255,255,0.08);
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 999px;
        color: #f5f5f7;
        font-size: 13px;
        font-weight: 700;
    }

    .product-card-pro {
        background: radial-gradient(circle at top left, rgba(255,255,255,0.14), rgba(255,255,255,0.055));
        border: 1px solid rgba(255,255,255,0.11);
        border-radius: 20px;
        padding: 12px;
        margin-bottom: 14px;
        box-shadow: 0 12px 32px rgba(0,0,0,0.22);
        min-height: 210px;
    }

    .product-img-wrap {
        height: 115px;
        background: rgba(255,255,255,0.045);
        border-radius: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #71717a;
        margin-bottom: 10px;
        overflow: hidden;
    }

    .product-name-pro {
        font-size: 16px;
        font-weight: 800;
        letter-spacing: -0.02em;
        line-height: 1.1;
        margin-bottom: 4px;
    }

    .product-variant-pro {
        color: #a1a1aa;
        font-size: 12px;
        margin-bottom: 6px;
    }

    .product-price-pro {
        color: #30d158;
        font-size: 21px;
        font-weight: 900;
        margin-bottom: 4px;
    }

    .stock-ok {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 999px;
        background: rgba(48,209,88,0.16);
        color: #30d158;
        font-size: 12px;
        font-weight: 800;
    }

    .stock-low {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 999px;
        background: rgba(255,214,10,0.16);
        color: #ffd60a;
        font-size: 12px;
        font-weight: 800;
    }

    .stock-out {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 999px;
        background: rgba(255,69,58,0.16);
        color: #ff453a;
        font-size: 12px;
        font-weight: 800;
    }

    @media (max-width: 768px) {
        .pos-title {
            font-size: 27px;
        }

        .pos-hero {
            padding: 18px;
            border-radius: 22px;
        }

        .product-card-pro {
            min-height: auto;
        }

        .product-img-wrap {
            height: 105px;
        }
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


def stock_badge(stock: int) -> str:
    if stock <= 0:
        return '<span class="stock-out">Sin stock</span>'
    elif stock <= 3:
        return f'<span class="stock-low">Stock bajo: {stock}</span>'
    else:
        return f'<span class="stock-ok">Stock: {stock}</span>'


def render_pos_header(df_productos, cart):
    productos_total = len(df_productos)
    items_carrito = sum(item["qty"] for item in cart)

    st.markdown("""
    <div class="pos-hero">
        <div class="pos-title">Punto de venta</div>
        <div class="pos-subtitle">Buscá, elegí variante y agregá productos al carrito en segundos.</div>
    </div>
    """, unsafe_allow_html=True)

    m1, m2 = st.columns(2)

    with m1:
        st.markdown(f"""
        <div class="metric-pill">
            <div class="label">Productos</div>
            <div class="value">{productos_total}</div>
        </div>
        """, unsafe_allow_html=True)

    with m2:
        st.markdown(f"""
        <div class="metric-pill">
            <div class="label">En carrito</div>
            <div class="value">{items_carrito}</div>
        </div>
        """, unsafe_allow_html=True)


def render_category_chips(df_productos):
    categorias = (
        df_productos["categoria"]
        .fillna("Sin categoría")
        .replace("", "Sin categoría")
        .drop_duplicates()
        .tolist()
    )

    if categorias:
        chips = "".join([f'<span class="category-chip">{cat}</span>' for cat in categorias[:12]])
        st.markdown(chips, unsafe_allow_html=True)


def require_admin():
    if st.session_state.get("rol") != "admin":
        st.error("Acceso restringido")
        st.stop()


def reset_pagos():
    st.session_state["pago_key_version"] = st.session_state.get("pago_key_version", 0) + 1


def marcar_fin_dia_descargado():
    st.session_state["fin_dia_pdf_descargado"] = True


def auto_collapse_sidebar():
    components.html(
        """
        <script>
        setTimeout(function() {
            const doc = window.parent.document;
            const buttons = Array.from(doc.querySelectorAll('button'));
            const collapseButton = buttons.find(btn => {
                const label = (btn.getAttribute('aria-label') || '').toLowerCase();
                return label.includes('close sidebar') ||
                       label.includes('cerrar') ||
                       label.includes('collapse') ||
                       label.includes('sidebar');
            });
            const sidebar = doc.querySelector('[data-testid="stSidebar"]');
            const isExpanded = sidebar && sidebar.getAttribute('aria-expanded') !== 'false';
            if (collapseButton && isExpanded) {
                collapseButton.click();
            }
        }, 350);
        </script>
        """,
        height=0,
        width=0
    )


def crear_pdf_fin_dia(resumen, ventas_detalle):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    width, height = A4
    y = height - 2 * cm

    def nueva_pagina():
        nonlocal y
        pdf.showPage()
        y = height - 2 * cm

    def check_y(min_y=2 * cm):
        if y < min_y:
            nueva_pagina()

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(2 * cm, y, "POINT.MOBILE - FIN DEL DIA")

    y -= 1 * cm
    pdf.setFont("Helvetica", 10)
    pdf.drawString(2 * cm, y, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    y -= 1.2 * cm
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(2 * cm, y, "Resumen general")

    y -= 0.8 * cm
    pdf.setFont("Helvetica", 11)
    pdf.drawString(2 * cm, y, f"Venta total: ${resumen['total']:,.0f}")

    y -= 0.6 * cm
    pdf.drawString(2 * cm, y, f"Efectivo: ${resumen['efectivo']:,.0f}")

    y -= 0.6 * cm
    pdf.drawString(2 * cm, y, f"Transferencia: ${resumen['transferencia']:,.0f}")

    y -= 0.6 * cm
    pdf.drawString(2 * cm, y, f"Descuentos: ${resumen['descuentos']:,.0f}")

    y -= 0.6 * cm
    pdf.drawString(2 * cm, y, f"Cantidad de ventas: {resumen['cantidad_ventas']}")

    y -= 1.2 * cm
    check_y()

    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(2 * cm, y, "Totales por usuario")

    y -= 0.8 * cm

    usuarios = (
        ventas_detalle
        .groupby("usuario", dropna=False)
        .agg(
            ventas=("id", "count"),
            total=("total", "sum"),
            efectivo=("efectivo", "sum"),
            transferencia=("transferencia", "sum"),
            descuentos=("descuento_monto", "sum")
        )
        .reset_index()
    )

    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(2 * cm, y, "Usuario")
    pdf.drawString(6 * cm, y, "Ventas")
    pdf.drawString(8 * cm, y, "Total")
    pdf.drawString(10.5 * cm, y, "Efectivo")
    pdf.drawString(13 * cm, y, "Transf.")
    pdf.drawString(15.5 * cm, y, "Desc.")

    pdf.setFont("Helvetica", 8)

    for _, row in usuarios.iterrows():
        y -= 0.5 * cm
        check_y()

        pdf.drawString(2 * cm, y, str(row["usuario"])[:20])
        pdf.drawString(6 * cm, y, str(int(row["ventas"])))
        pdf.drawString(8 * cm, y, f"${row['total']:,.0f}")
        pdf.drawString(10.5 * cm, y, f"${row['efectivo']:,.0f}")
        pdf.drawString(13 * cm, y, f"${row['transferencia']:,.0f}")
        pdf.drawString(15.5 * cm, y, f"${row['descuentos']:,.0f}")

    y -= 1.2 * cm
    check_y()

    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(2 * cm, y, "Detalle de ventas por usuario")

    for usuario, df_user in ventas_detalle.groupby("usuario", dropna=False):
        y -= 1 * cm
        check_y()

        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(2 * cm, y, f"Usuario: {usuario}")

        y -= 0.6 * cm
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawString(2 * cm, y, "Hora")
        pdf.drawString(4 * cm, y, "Total")
        pdf.drawString(6.5 * cm, y, "Efectivo")
        pdf.drawString(9 * cm, y, "Transf.")
        pdf.drawString(11.5 * cm, y, "Desc.")
        pdf.drawString(14 * cm, y, "Tipo desc.")

        pdf.setFont("Helvetica", 8)

        for _, row in df_user.iterrows():
            y -= 0.5 * cm
            check_y()

            fecha = pd.to_datetime(row["fecha"]).strftime("%H:%M")
            pdf.drawString(2 * cm, y, fecha)
            pdf.drawString(4 * cm, y, f"${row['total']:,.0f}")
            pdf.drawString(6.5 * cm, y, f"${row['efectivo']:,.0f}")
            pdf.drawString(9 * cm, y, f"${row['transferencia']:,.0f}")
            pdf.drawString(11.5 * cm, y, f"${row['descuento_monto']:,.0f}")
            pdf.drawString(14 * cm, y, str(row["descuento_tipo"])[:18])

        y -= 0.7 * cm
        check_y()

        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(2 * cm, y, f"Total usuario: ${df_user['total'].sum():,.0f}")
        pdf.drawString(7 * cm, y, f"Efectivo: ${df_user['efectivo'].sum():,.0f}")
        pdf.drawString(12 * cm, y, f"Transf.: ${df_user['transferencia'].sum():,.0f}")

    pdf.save()
    buffer.seek(0)
    return buffer


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
            subtotal FLOAT DEFAULT 0,
            descuento_tipo TEXT DEFAULT 'Sin descuento',
            descuento_monto FLOAT DEFAULT 0,
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
    conn.execute(text("ALTER TABLE cobros ADD COLUMN IF NOT EXISTS subtotal FLOAT DEFAULT 0;"))
    conn.execute(text("ALTER TABLE cobros ADD COLUMN IF NOT EXISTS descuento_tipo TEXT DEFAULT 'Sin descuento';"))
    conn.execute(text("ALTER TABLE cobros ADD COLUMN IF NOT EXISTS descuento_monto FLOAT DEFAULT 0;"))
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

                if "descuento_tipo" not in st.session_state:
                    st.session_state["descuento_tipo"] = None

                reset_pagos()

                st.rerun()
            else:
                st.error("❌ Credenciales incorrectas")

    st.stop()


USER = st.session_state["user"]
ROL = st.session_state["rol"]

if "cart" not in st.session_state:
    st.session_state["cart"] = []

if "descuento_tipo" not in st.session_state:
    st.session_state["descuento_tipo"] = None

if "pago_key_version" not in st.session_state:
    st.session_state["pago_key_version"] = 0


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

    menu = st.radio("Módulos", menu_options, label_visibility="collapsed", key="menu_radio")

    st.divider()

    if st.button("🚪 Cerrar Sesión", use_container_width=True, key="logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

auto_collapse_sidebar()


# =========================
# DATA
# =========================
df_productos = pd.read_sql(
    "SELECT * FROM productos ORDER BY nombre, variante",
    engine
)


# =========================
# 🛒 AGREGAR PRODUCTO AL CARRITO
# =========================
if menu == "🛒 Agregar Producto":
    cart = st.session_state.get("cart", [])

    render_pos_header(df_productos, cart)

    st.divider()

    col_search, col_filter = st.columns([2.2, 1])

    with col_search:
        search = st.text_input(
            "Buscar producto",
            "",
            placeholder="Buscar por producto, color, modelo o categoría...",
            key="buscar_producto"
        )

    with col_filter:
        categorias_disponibles = (
            df_productos["categoria"]
            .fillna("Sin categoría")
            .replace("", "Sin categoría")
            .drop_duplicates()
            .tolist()
        )

        categoria_seleccionada = st.selectbox(
            "Categoría",
            ["Todas"] + categorias_disponibles,
            key="filtro_categoria_ventas"
        )

    render_category_chips(df_productos)

    df_filtrado = df_productos.copy()

    if categoria_seleccionada != "Todas":
        df_filtrado = df_filtrado[
            df_filtrado["categoria"].fillna("Sin categoría").replace("", "Sin categoría") == categoria_seleccionada
        ]

    if search:
        df_filtrado = df_filtrado[
            df_filtrado["nombre"].str.contains(search, case=False, na=False)
            | df_filtrado["variante"].fillna("").str.contains(search, case=False, na=False)
            | df_filtrado["categoria"].fillna("").str.contains(search, case=False, na=False)
        ]

    st.write("")

    if df_filtrado.empty:
        st.warning("No se encontraron productos con ese filtro")
    else:
        st.caption(f"Mostrando {len(df_filtrado)} producto(s)")

        cols = st.columns(4)

        for idx, row in df_filtrado.reset_index(drop=True).iterrows():
            with cols[idx % 4]:
                stock = int(row["stock"] or 0)
                precio = float(row["precio"] or 0)
                variante = row.get("variante") or ""
                categoria = row.get("categoria") or "Sin categoría"

                st.markdown('<div class="product-card-pro">', unsafe_allow_html=True)

                if row.get("imagen") and isinstance(row.get("imagen"), str) and len(row.get("imagen")) > 20:
                    try:
                        st.image(base64.b64decode(row.get("imagen")), width=130)
                    except Exception:
                        st.markdown(
                            '<div class="product-img-wrap">Foto inválida</div>',
                            unsafe_allow_html=True
                        )
                else:
                    st.markdown(
                        '<div class="product-img-wrap">Sin foto</div>',
                        unsafe_allow_html=True
                    )

                st.markdown(f"""
                    <div class="product-name-pro">{row['nombre']}</div>
                    <div class="product-variant-pro">{variante}</div>
                    <div class="product-variant-pro">{categoria}</div>
                    <div class="product-price-pro">${precio:,.0f}</div>
                    {stock_badge(stock)}
                """, unsafe_allow_html=True)

                if stock <= 0:
                    st.button(
                        "Sin stock",
                        disabled=True,
                        use_container_width=True,
                        key=f"sin_stock_{row['id']}"
                    )
                else:
                    qty = st.number_input(
                        "Cantidad",
                        min_value=1,
                        max_value=max(1, stock),
                        value=1,
                        step=1,
                        key=f"qty_{row['id']}"
                    )

                    if st.button(
                        "➕ Agregar",
                        key=f"add_{row['id']}",
                        use_container_width=True,
                        type="primary"
                    ):
                        st.session_state["cart"].append({
                            "id": int(row["id"]),
                            "name": row["nombre"],
                            "variant": variante,
                            "price": precio,
                            "cost": float(row.get("costo") or 0),
                            "qty": int(qty)
                        })

                        reset_pagos()
                        st.toast(f"✅ {row['nombre']} agregado", icon="🛒")
                        st.rerun()

                st.markdown("</div>", unsafe_allow_html=True)


# =========================
# 🛍️ CARRITO
# =========================
elif menu == "🛍️ Carrito":
    st.header("🛍️ Carrito")

    cart = st.session_state.get("cart", [])

    if not cart:
        st.info("El carrito está vacío")
        st.session_state["descuento_tipo"] = None
        reset_pagos()

    else:
        subtotal = sum(item["price"] * item["qty"] for item in cart)

        for i, item in enumerate(cart):
            col1, col2, col3 = st.columns([5, 2, 1])

            with col1:
                st.write(f"**{item['name']}** {item.get('variant', '')} × {item['qty']}")

            with col2:
                st.write(f"${item['price'] * item['qty']:,.0f}")

            with col3:
                if st.button("🗑️", key=f"rm_cart_{i}"):
                    cart.pop(i)
                    reset_pagos()
                    st.rerun()

        st.divider()

        st.subheader("🎟️ Descuentos")

        col_desc1, col_desc2, col_desc3 = st.columns(3)

        with col_desc1:
            if st.button("🎁 BONIFICACIÓN 10%", use_container_width=True, key="desc_bonificacion"):
                st.session_state["descuento_tipo"] = "bonificacion"
                reset_pagos()
                st.rerun()

        with col_desc2:
            if ROL == "admin":
                if st.button("👥 EMPLEADOS 20%", use_container_width=True, key="desc_empleados"):
                    st.session_state["descuento_tipo"] = "empleados"
                    reset_pagos()
                    st.rerun()
            else:
                st.button(
                    "👥 EMPLEADOS 20%",
                    use_container_width=True,
                    key="desc_empleados_bloqueado",
                    disabled=True
                )
                st.caption("Solo admin")

        with col_desc3:
            if st.button("❌ Quitar descuento", use_container_width=True, key="quitar_descuento"):
                st.session_state["descuento_tipo"] = None
                reset_pagos()
                st.rerun()

        descuento_tipo = st.session_state.get("descuento_tipo")

        if descuento_tipo == "bonificacion":
            descuento_porcentaje = 0.10
            descuento_nombre = "BONIFICACIÓN 10%"
        elif descuento_tipo == "empleados":
            descuento_porcentaje = 0.20
            descuento_nombre = "EMPLEADOS 20%"
        else:
            descuento_porcentaje = 0.0
            descuento_nombre = "Sin descuento"

        descuento_monto = subtotal * descuento_porcentaje
        total = subtotal - descuento_monto
        total = max(0.0, float(total))

        col_total1, col_total2, col_total3 = st.columns(3)

        with col_total1:
            st.metric("Subtotal", f"${subtotal:,.0f}")

        with col_total2:
            st.metric(descuento_nombre, f"-${descuento_monto:,.0f}")

        with col_total3:
            st.metric("Total final", f"${total:,.0f}")

        st.markdown("### 💳 Forma de pago")

        pago_key_version = st.session_state.get("pago_key_version", 0)

        efectivo_key = f"input_pago_efectivo_{pago_key_version}"
        transferencia_key = f"input_pago_transferencia_{pago_key_version}"

        colp1, colp2 = st.columns(2)

        with colp1:
            pago_efectivo = st.number_input(
                "💵 Efectivo",
                min_value=0.0,
                value=0.0,
                step=100.0,
                key=efectivo_key
            )

        restante_para_transferencia = max(0.0, total - float(pago_efectivo))

        with colp2:
            pago_transferencia = st.number_input(
                "🏦 Transferencia",
                min_value=0.0,
                value=0.0,
                step=100.0,
                key=transferencia_key
            )

        comprobante_transferencia = None

        if pago_transferencia > 0:
            comprobante_transferencia = st.file_uploader(
                "📸 Comprobante de transferencia",
                type=["jpg", "jpeg", "png"],
                key=f"comprobante_transferencia_{pago_key_version}"
            )

        total_pagado = float(pago_efectivo) + float(pago_transferencia)
        diferencia = total_pagado - total

        st.write(f"**Total final:** ${total:,.0f}")
        st.write(f"**Pagado:** ${total_pagado:,.0f}")
        st.write(f"**Máximo permitido en transferencia:** ${restante_para_transferencia:,.0f}")

        if pago_efectivo > total:
            st.error("❌ El efectivo no puede superar el total final")

        elif pago_transferencia > restante_para_transferencia:
            st.error("❌ La transferencia no puede superar lo que falta pagar")

        elif diferencia < 0:
            st.warning(f"Faltan pagar: ${abs(diferencia):,.0f}")

        elif diferencia > 0:
            st.error(f"El pago supera el total por: ${diferencia:,.0f}")

        else:
            st.success("Pago exacto ✅")

        colb1, colb2 = st.columns(2)

        with colb1:
            if st.button("🧹 Vaciar carrito", use_container_width=True, key="vaciar_carrito"):
                st.session_state["cart"] = []
                st.session_state["descuento_tipo"] = None
                reset_pagos()
                st.rerun()

        with colb2:
            if st.button("💳 Cobrar Venta", type="primary", use_container_width=True, key="cobrar_venta"):

                if pago_efectivo > total:
                    st.error("❌ El efectivo no puede superar el total final")

                elif pago_transferencia > restante_para_transferencia:
                    st.error("❌ La transferencia no puede superar lo que falta pagar")

                elif total_pagado < total:
                    st.error("❌ El pago no alcanza para cubrir el total")

                elif total_pagado > total:
                    st.error("❌ El pago no puede ser mayor al total final con descuento aplicado")

                elif pago_transferencia > 0 and comprobante_transferencia is None:
                    st.error("❌ Debes subir el comprobante de transferencia")

                else:
                    try:
                        venta_grupo = str(uuid.uuid4())
                        comprobante_base64 = image_to_base64(comprobante_transferencia)

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

                            conn.execute(text("""
                                INSERT INTO cobros
                                (
                                    venta_grupo,
                                    usuario,
                                    subtotal,
                                    descuento_tipo,
                                    descuento_monto,
                                    total,
                                    efectivo,
                                    transferencia,
                                    comprobante,
                                    fecha
                                )
                                VALUES (
                                    :vg,
                                    :user,
                                    :subtotal,
                                    :descuento_tipo,
                                    :descuento_monto,
                                    :total,
                                    :efectivo,
                                    :transferencia,
                                    :comprobante,
                                    NOW()
                                )
                            """), {
                                "vg": venta_grupo,
                                "user": USER,
                                "subtotal": float(subtotal),
                                "descuento_tipo": descuento_nombre,
                                "descuento_monto": float(descuento_monto),
                                "total": float(total),
                                "efectivo": float(pago_efectivo),
                                "transferencia": float(pago_transferencia),
                                "comprobante": comprobante_base64
                            })

                            for item in cart:
                                conn.execute(text("""
                                    UPDATE productos
                                    SET stock = stock - :q
                                    WHERE id = :id
                                """), {
                                    "q": item["qty"],
                                    "id": item["id"]
                                })

                                item_subtotal = item["price"] * item["qty"]
                                proporcion = item_subtotal / subtotal if subtotal > 0 else 0
                                item_descuento = descuento_monto * proporcion
                                total_item = item_subtotal - item_descuento

                                costo_item = item["cost"] * item["qty"]
                                ganancia_item = total_item - costo_item

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
                        st.session_state["descuento_tipo"] = None
                        reset_pagos()
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

    with tab1:
        st.subheader("Agregar Nuevo Producto con Variantes")

        with st.form("form_nuevo_producto_variantes", clear_on_submit=True):
            col1, col2 = st.columns(2)

            with col1:
                categoria = st.text_input(
                    "Categoría",
                    placeholder="Ej: Fundas",
                    key="nueva_categoria"
                )

                nombre = st.text_input(
                    "Producto / Modelo *",
                    placeholder="Ej: iPhone 17",
                    key="nuevo_nombre"
                )

                precio = st.number_input(
                    "Precio de Venta ($)",
                    min_value=0.0,
                    step=100.0,
                    key="nuevo_precio"
                )

            with col2:
                costo = st.number_input(
                    "Costo ($)",
                    min_value=0.0,
                    step=100.0,
                    key="nuevo_costo"
                )

                imagen = st.file_uploader(
                    "📸 Foto del producto",
                    type=["jpg", "jpeg", "png"],
                    key="nueva_imagen"
                )

            st.markdown("### 🎨 Variantes / Colores")
            st.info("Escribí una variante por línea con este formato: color, stock")

            variantes_texto = st.text_area(
                "Variantes",
                placeholder="Negro, 5\nAzul, 8\nRojo, 3\nTransparente, 10",
                height=180,
                key="variantes_texto"
            )

            submit_producto = st.form_submit_button(
                "Guardar Producto con Variantes",
                type="primary"
            )

            if submit_producto:
                if not nombre or precio <= 0 or not variantes_texto.strip():
                    st.error("Producto, precio y variantes son obligatorios")

                else:
                    img_base64 = image_to_base64(imagen)
                    variantes = []

                    for linea in variantes_texto.splitlines():
                        linea = linea.strip()

                        if not linea:
                            continue

                        partes = linea.split(",")

                        if len(partes) != 2:
                            st.error(f"Formato incorrecto en: {linea}")
                            st.stop()

                        variante_nombre = partes[0].strip()
                        variante_stock = partes[1].strip()

                        try:
                            variante_stock = int(variante_stock)
                        except Exception:
                            st.error(f"Stock inválido en: {linea}")
                            st.stop()

                        if variante_nombre and variante_stock >= 0:
                            variantes.append((variante_nombre, variante_stock))

                    if not variantes:
                        st.error("No hay variantes válidas")
                    else:
                        with engine.begin() as conn:
                            for variante_nombre, variante_stock in variantes:
                                conn.execute(text("""
                                    INSERT INTO productos
                                    (categoria, nombre, variante, precio, costo, stock, imagen)
                                    VALUES (:cat, :nom, :var, :pre, :cos, :sto, :img)
                                """), {
                                    "cat": categoria,
                                    "nom": nombre,
                                    "var": variante_nombre,
                                    "pre": precio,
                                    "cos": costo,
                                    "sto": variante_stock,
                                    "img": img_base64
                                })

                        stock_total = sum(v[1] for v in variantes)

                        st.success(
                            f"✅ Producto '{nombre}' agregado con {len(variantes)} variantes. "
                            f"Stock total: {stock_total}"
                        )
                        st.rerun()

        st.divider()
        st.subheader("Productos Registrados")

        df_productos_admin = pd.read_sql(
            "SELECT * FROM productos ORDER BY categoria, nombre, variante",
            engine
        )

        if df_productos_admin.empty:
            st.info("No hay productos registrados")
        else:
            resumen_stock = df_productos_admin.groupby(
                ["categoria", "nombre"],
                dropna=False
            ).agg(
                stock_total=("stock", "sum"),
                precio=("precio", "first"),
                costo=("costo", "first"),
                variantes=("variante", "count")
            ).reset_index()

            st.markdown("### 📦 Resumen por producto")

            st.dataframe(
                resumen_stock.rename(columns={
                    "categoria": "Categoría",
                    "nombre": "Producto",
                    "stock_total": "Stock Total",
                    "precio": "Precio",
                    "costo": "Costo",
                    "variantes": "Variantes"
                }),
                use_container_width=True,
                hide_index=True
            )

            st.markdown("### 🎨 Variantes cargadas")

            for _, row in df_productos_admin.iterrows():
                col1, col2, col3, col4 = st.columns([3, 2, 1.5, 1.5])

                with col1:
                    st.write(
                        f"**{row['categoria']} | {row['nombre']}** | "
                        f"{row.get('variante') or 'Sin variante'}"
                    )

                with col2:
                    st.write(
                        f"${float(row['precio']):,.0f} | "
                        f"Stock: **{int(row['stock'] or 0)}**"
                    )

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
                        st.success("Variante eliminada")
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
            st.subheader(f"Editando: {prod['nombre']} - {prod.get('variante') or ''}")

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
        st.subheader("🔑 Cambiar contraseña")

        if df_usuarios.empty:
            st.info("No hay usuarios")
        else:
            usuario_password = st.selectbox(
                "Usuario",
                df_usuarios["username"].tolist(),
                key="select_usuario_password"
            )

            nueva_password = st.text_input(
                "Nueva contraseña",
                type="password",
                key="nueva_password_usuario"
            )

            confirmar_password = st.text_input(
                "Confirmar contraseña",
                type="password",
                key="confirmar_password_usuario"
            )

            if st.button("Actualizar contraseña", type="primary", key="btn_actualizar_password"):
                if not nueva_password or not confirmar_password:
                    st.warning("Completa ambos campos de contraseña")

                elif nueva_password != confirmar_password:
                    st.error("Las contraseñas no coinciden")

                else:
                    with engine.begin() as conn:
                        conn.execute(text("""
                            UPDATE usuarios
                            SET password = :p
                            WHERE username = :u
                        """), {
                            "p": hash_pass(nueva_password),
                            "u": usuario_password
                        })

                    st.success(f"✅ Contraseña de '{usuario_password}' actualizada correctamente")
                    st.rerun()

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
                subtotal,
                descuento_tipo,
                descuento_monto,
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
                st.metric("🎟️ Descuentos", f"${cobros['descuento_monto'].sum():,.0f}")

            st.divider()
            st.header("🏁 FIN DEL DÍA")

            hoy = datetime.now().date()
            hoy_key = datetime.now().strftime("%Y_%m_%d")

            if st.session_state.get("fin_dia_fecha") != hoy_key:
                st.session_state["fin_dia_fecha"] = hoy_key
                st.session_state["fin_dia_pdf_descargado"] = False

            cobros_hoy = cobros[
                pd.to_datetime(cobros["fecha"]).dt.date == hoy
            ].copy()

            if cobros_hoy.empty:
                st.info("Todavía no hay ventas hoy")
                st.session_state["fin_dia_pdf_descargado"] = False
            else:
                total_dia = cobros_hoy["total"].sum()
                efectivo_dia = cobros_hoy["efectivo"].sum()
                transferencia_dia = cobros_hoy["transferencia"].sum()
                descuentos_dia = cobros_hoy["descuento_monto"].sum()
                cantidad_ventas = len(cobros_hoy)

                f1, f2, f3, f4 = st.columns(4)

                with f1:
                    st.metric("Venta total hoy", f"${total_dia:,.0f}")

                with f2:
                    st.metric("Efectivo hoy", f"${efectivo_dia:,.0f}")

                with f3:
                    st.metric("Transferencia hoy", f"${transferencia_dia:,.0f}")

                with f4:
                    st.metric("Descuentos hoy", f"${descuentos_dia:,.0f}")

                st.subheader("Totales por usuario del día")

                resumen_usuarios_hoy = (
                    cobros_hoy
                    .groupby("usuario", dropna=False)
                    .agg(
                        ventas=("id", "count"),
                        total=("total", "sum"),
                        efectivo=("efectivo", "sum"),
                        transferencia=("transferencia", "sum"),
                        descuentos=("descuento_monto", "sum")
                    )
                    .reset_index()
                )

                st.dataframe(
                    resumen_usuarios_hoy.rename(columns={
                        "usuario": "Usuario",
                        "ventas": "Ventas",
                        "total": "Total",
                        "efectivo": "Efectivo",
                        "transferencia": "Transferencia",
                        "descuentos": "Descuentos"
                    }),
                    use_container_width=True,
                    hide_index=True
                )

                resumen_fin_dia = {
                    "total": total_dia,
                    "efectivo": efectivo_dia,
                    "transferencia": transferencia_dia,
                    "descuentos": descuentos_dia,
                    "cantidad_ventas": cantidad_ventas
                }

                pdf_buffer = crear_pdf_fin_dia(resumen_fin_dia, cobros_hoy)

                col_pdf, col_nuevo_dia = st.columns(2)

                with col_pdf:
                    st.download_button(
                        label="📄 FIN DEL DÍA - Descargar PDF",
                        data=pdf_buffer,
                        file_name=f"fin_del_dia_{datetime.now().strftime('%Y_%m_%d')}.pdf",
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True,
                        on_click=marcar_fin_dia_descargado,
                        key=f"descargar_fin_dia_{hoy_key}"
                    )

                with col_nuevo_dia:
                    st.markdown("### 🌅 Nuevo día")

                    password_nuevo_dia = st.text_input(
                        "Clave admin para iniciar nuevo día",
                        type="password",
                        key=f"password_nuevo_dia_{hoy_key}"
                    )

                    if st.button(
                        "🌅 NUEVO DÍA",
                        type="primary",
                        use_container_width=True,
                        key="nuevo_dia_confirmado"
                    ):
                        if not password_nuevo_dia:
                            st.error("❌ Ingresá la clave del admin")

                        else:
                            with engine.connect() as conn:
                                admin_ok = conn.execute(text("""
                                    SELECT 1
                                    FROM usuarios
                                    WHERE username = :u
                                    AND password = :p
                                    AND rol = 'admin'
                                """), {
                                    "u": USER,
                                    "p": hash_pass(password_nuevo_dia)
                                }).fetchone()

                            if not admin_ok:
                                st.error("❌ Clave admin incorrecta")

                            else:
                                grupos_hoy = cobros_hoy["venta_grupo"].dropna().tolist()

                                with engine.begin() as conn:
                                    for grupo in grupos_hoy:
                                        conn.execute(text("""
                                            DELETE FROM ventas
                                            WHERE venta_grupo = :vg
                                        """), {"vg": grupo})

                                        conn.execute(text("""
                                            DELETE FROM cobros
                                            WHERE venta_grupo = :vg
                                        """), {"vg": grupo})

                                st.session_state["fin_dia_pdf_descargado"] = False
                                st.session_state["cart"] = []
                                reset_pagos()

                                st.success("✅ Nuevo día iniciado. Ventas y cobros del día fueron limpiados sin devolver stock.")
                                st.rerun()

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
                    st.write("### 💳 Pago y descuentos")

                    p1, p2, p3, p4 = st.columns(4)

                    with p1:
                        st.metric("Subtotal", f"${cobro['subtotal']:,.0f}")

                    with p2:
                        st.metric("Descuento", f"${cobro['descuento_monto']:,.0f}")

                    with p3:
                        st.metric("Total", f"${cobro['total']:,.0f}")

                    with p4:
                        st.metric("Tipo", str(cobro["descuento_tipo"]))

                    p5, p6 = st.columns(2)

                    with p5:
                        st.metric("Efectivo", f"${cobro['efectivo']:,.0f}")

                    with p6:
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
                    st.markdown("### 🧹 Acciones sobre esta venta")

                    col_accion1, col_accion2 = st.columns(2)

                    with col_accion1:
                        if st.button(
                            "↩️ Anular y devolver stock",
                            key=f"anular_devolver_{venta_grupo}"
                        ):
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

                            st.success("✅ Venta anulada y stock devuelto")
                            st.rerun()

                    with col_accion2:
                        if st.button(
                            "🗑️ Eliminar sin devolver stock",
                            key=f"eliminar_sin_stock_{venta_grupo}"
                        ):
                            with engine.begin() as conn:
                                conn.execute(text("""
                                    DELETE FROM ventas
                                    WHERE venta_grupo = :vg
                                """), {"vg": venta_grupo})

                                conn.execute(text("""
                                    DELETE FROM cobros
                                    WHERE venta_grupo = :vg
                                """), {"vg": venta_grupo})

                            st.success("✅ Venta eliminada sin modificar stock")
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
