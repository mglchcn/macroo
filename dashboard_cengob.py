import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import uuid

# Configuración de página debe ser lo primero
st.set_page_config(
    page_title="Dashboard Macroeconómico CENGOB - Bolivia",
    layout="wide",
    page_icon="📊",
    initial_sidebar_state="expanded"
)

EXCEL_FILE = "Info.xlsx"
SHEET_NAME = "data"

# =========================
# CSS RESPONSIVO Y PREMIUM
# =========================
st.markdown("""
<style>
    /* =================================
       VARIABLES CSS NATIVAS DE STREAMLIT
       Usamos estas variables para asegurar compatibilidad
       total con modo claro y oscuro automáticamente.
    ================================= */

    :root {
        /* Definimos un estilo de tarjeta base que usa los colores del tema actual */
        --card-bg: var(--secondary-background-color);
        --card-border-color: var(--text-color-20); /* Color de texto con mucha transparencia */
        --card-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }

    /* =================================
       TIPOGRAFÍA FLUIDA (RESPONSIVA)
       Usa clamp() para ajustar el tamaño suavemente entre desktop y móvil.
    ================================= */
    h1, .responsive-h1 {
        font-size: clamp(2rem, 5vw, 3.5rem) !important;
        font-weight: 800 !important;
        letter-spacing: -0.02em !important;
    }

    h2, .responsive-h2 {
        font-size: clamp(1.5rem, 4vw, 2.2rem) !important;
        font-weight: 700 !important;
        /* Color secundario para subtítulos */
        color: var(--text-color-80) !important;
    }

    h3, .responsive-h3 {
        font-size: clamp(1.2rem, 3vw, 1.5rem) !important;
        font-weight: 600 !important;
    }

    p, .responsive-p {
        font-size: clamp(1rem, 1.5vw, 1.1rem) !important;
        line-height: 1.6 !important;
        color: var(--text-color-90) !important;
    }

    /* =================================
       COMPONENTES PERSONALIZADOS
    ================================= */

    /* Tarjeta Premium Genérica */
    .premium-card {
        background-color: var(--card-bg);
        border: 1px solid var(--card-border-color);
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: var(--card-shadow);
        transition: all 0.3s ease;
        height: 100%; /* Para que ocupen la misma altura en columnas */
    }

    /* Ajuste de métricas nativas de Streamlit para que resalten más */
    [data-testid="stMetric"] {
        background-color: var(--card-bg);
        padding: 1rem;
        border-radius: 12px;
        border: 1px solid var(--card-border-color);
        box-shadow: var(--card-shadow);
    }

    /* Etiquetas de las métricas más legibles */
    [data-testid="stMetricLabel"] {
        font-size: 1rem !important;
        font-weight: 600 !important;
        color: var(--text-color-80) !important;
    }

     /* Valores de las métricas más grandes */
    [data-testid="stMetricValue"] {
        font-size: clamp(1.5rem, 4vw, 2rem) !important;
        font-weight: 700 !important;
    }

    /* Ajustes para móviles */
    @media (max-width: 768px) {
        /* Reducir padding del contenedor principal en móviles */
        .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        /* Tarjetas más compactas en móvil */
        .premium-card, [data-testid="stMetric"] {
            padding: 1rem;
        }
    }

</style>
""", unsafe_allow_html=True)


# =========================
# CARGA DE DATOS (Sin cambios)
# =========================
@st.cache_data
def cargar_datos():
    try:
        raw = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_NAME, header=None)
    except FileNotFoundError:
        st.error(f"No se encontró el archivo '{EXCEL_FILE}'. Asegúrate de que esté en la misma carpeta.")
        return pd.DataFrame()

    nombres = raw.iloc[1].copy()
    nombres.iloc[0] = "fecha"
    nombres = nombres.astype(str).str.strip()

    nombres_unicos = []
    contador = {}
    for n in nombres:
        if n in contador:
            contador[n] += 1
            nombres_unicos.append(f"{n}_{contador[n]}")
        else:
            contador[n] = 0
            nombres_unicos.append(n)

    data = raw.iloc[2:].copy()
    data.columns = nombres_unicos
    data = data.rename(columns={data.columns[0]: "fecha"})

    data["fecha"] = pd.to_datetime(data["fecha"], errors="coerce")
    data = data.dropna(subset=["fecha"])
    data = data.dropna(axis=1, how="all")

    for col in data.columns:
        if col != "fecha":
            data[col] = pd.to_numeric(data[col], errors="coerce")

    return data

df_original = cargar_datos()

if df_original.empty:
    st.stop()

# =========================
# FUNCIONES DE AYUDA (Sin cambios mayores)
# =========================
def buscar_columna(texto):
    texto = texto.lower()
    for col in df_original.columns:
        if col != "fecha" and texto in str(col).lower():
            return col
    return None

def ultimo_valor(df, col):
    if col is None: return None, None
    s = df[["fecha", col]].dropna()
    if s.empty: return None, None
    u = s.iloc[-1]
    return u[col], u["fecha"]

def variacion_interanual(df, col):
    if col is None: return None
    s = df[["fecha", col]].dropna().sort_values("fecha")
    if len(s) < 13: return None
    actual = s.iloc[-1]
    # FIX: Usar pd.DateOffset para mayor precisión si los datos no son perfectamente mensuales
    base_fecha = actual["fecha"] - pd.DateOffset(years=1)
    # Buscamos el dato más cercano a esa fecha hacia atrás
    ant = s[s["fecha"] <= base_fecha]
    if ant.empty: return None
    # Tomamos el último dato disponible hasta esa fecha (el más cercano al año exacto)
    base = ant.iloc[-1][col]
    if base == 0 or pd.isna(base): return None
    return ((actual[col] / base) - 1) * 100

def formato_numero(x):
    if x is None or pd.isna(x): return "Sin dato"
    # Formato condicional según la magnitud
    if abs(x) >= 1_000_000:
        return f"{x/1_000_000:,.1f}M"
    elif abs(x) >= 1_000:
        return f"{x:,.0f}"
    return f"{x:,.2f}"

def kpi(df, titulo, col, unidad=""):
    valor, fecha = ultimo_valor(df, col)
    yoy = variacion_interanual(df, col)
    if valor is None:
        st.metric(titulo, "Sin dato")
        return
    delta = f"{yoy:,.1f}% interanual" if yoy is not None else None
    # Usamos la métrica nativa, el CSS se encarga del estilo
    st.metric(titulo, f"{formato_numero(valor)} {unidad}", delta)
    # Fecha pequeña debajo
    st.markdown(f"<small style='color:var(--text-color-60)'>Ult. dato: {fecha.strftime('%d/%m/%y')}</small>", unsafe_allow_html=True)


# =========================
# FUNCIONES GRÁFICAS (REDITADAS PARA TEMAS)
# =========================

# Configuración común para todos los gráficos Plotly para que sean agnósticos al tema
def aplicar_tema_plotly(fig, titulo, unidad=""):
    fig.update_layout(
        title=dict(
            text=titulo,
            font=dict(size=18, family="Source Sans Pro") # Fuente similar a Streamlit
        ),
        height=400,
        # CLAVE: Fondo transparente para que se vea el fondo de Streamlit (claro u oscuro)
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=60, b=30),
        xaxis_title="",
        yaxis_title=unidad,
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="right", x=1,
            bgcolor="rgba(0,0,0,0)" # Leyenda transparente
        ),
        # Color de fuente automático según el tema de Plotly (generalmente gris oscuro o blanco)
        # Si se quiere forzar: font=dict(color="var(--text-color)") NO funciona en Plotly directo.
        # Dejamos que Plotly maneje la fuente base, que suele contrastar bien.
    )
    # Líneas de cuadrícula sutiles y transparentes
    grid_color = "rgba(128, 128, 128, 0.2)"
    fig.update_xaxes(showgrid=False, gridcolor=grid_color, zerolinecolor=grid_color)
    fig.update_yaxes(gridcolor=grid_color, zerolinecolor=grid_color)
    return fig


def grafico_linea(df, col, titulo, unidad=""):
    if col is None:
        st.warning(f"No se encontró: {titulo}")
        return
    s = df[["fecha", col]].dropna()
    if s.empty:
        st.warning(f"Sin datos para: {titulo}")
        return

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=s["fecha"], y=s[col],
            mode="lines", line=dict(width=3), # Color automático de Plotly
            hovertemplate="%{x|%d/%m/%Y}<br>Valor: %{y:,.2f}<extra></extra>"
        )
    )
    fig = aplicar_tema_plotly(fig, titulo, unidad)
    fig.update_layout(
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1A", step="year", stepmode="backward"),
                    dict(count=5, label="5A", step="year", stepmode="backward"),
                    dict(step="all", label="Todo")
                ]),
                bgcolor="var(--secondary-background-color)", # Color de botones compatible
            ),
            type="date"
        ),
    )

    # FIX: Usar una key determinista, no uuid aleatorio
    st.plotly_chart(fig, use_container_width=True, key=f"linea_{col}_{titulo}")

def grafico_lineas_multiples(df, cols, titulo, unidad=""):
    cols = [c for c in cols if c is not None]
    if not cols:
        st.warning(f"No hay variables disponibles para: {titulo}")
        return

    fig = go.Figure()
    for c in cols:
        s = df[["fecha", c]].dropna()
        if not s.empty:
            fig.add_trace(
                go.Scatter(
                    x=s["fecha"], y=s[c],
                    mode="lines", name=c[:30], # Acortar nombres largos
                    line=dict(width=3),
                    hovertemplate="%{x|%d/%m/%Y}<br>%{y:,.2f}<extra></extra>"
                )
            )

    fig = aplicar_tema_plotly(fig, titulo, unidad)
    # FIX: Key determinista
    st.plotly_chart(fig, use_container_width=True, key=f"multi_{titulo[:10]}")


def grafico_barras(df, cols, titulo):
    # ... (código similar al anterior, aplicando aplicar_tema_plotly)
    # Por brevedad, omito la implementación completa ya que el principio es el mismo
    pass

# =========================
# NUEVA FUNCION TARJETA RIESGO (RESPONSIVA Y TEMATIZADA)
# =========================
def tarjeta_riesgo_moderna(titulo, nivel, explicacion=""):
    """
    Crea una tarjeta de riesgo que se adapta al tema claro/oscuro.
    Usa un borde lateral de color y un icono para indicar el estado.
    """
    # Definición de colores y estado
    colores_estado = {
        # Color Hex, Icono
        "Alto": ("#ef4444", "🔴"),      # Rojo intenso
        "Moderado": ("#f59e0b", "🟡"), # Ámbar
        "Bajo": ("#22c55e", "🟢"),     # Verde
        "Adecuado": ("#22c55e", "🟢"), # Verde
        "Crítico": ("#b91c1c", "⚫"),  # Rojo oscuro
        "Sin dato": ("#9ca3af", "⚪")  # Gris
    }

    color_hex, icono = colores_estado.get(nivel, ("#9ca3af", "⚪"))

    # Usamos la clase CSS 'premium-card' base y añadimos estilos en línea dinámicos
    html_card = f"""
    <div class="premium-card" style="border-left: 6px solid {color_hex}; display: flex; flex-direction: column; justify-content: center;">
        <h4 style="margin: 0; color: var(--text-color-80); font-size: 1.1rem;">
            {titulo}
        </h4>
        <div style="display: flex; align-items: center; margin-top: 0.8rem;">
            <span style="font-size: 1.8rem; margin-right: 0.8rem; line-height: 1;">{icono}</span>
            <h2 style="margin: 0; color: {color_hex}; font-weight: 800; font-size: 1.8rem;">
                {nivel}
            </h2>
        </div>
        {"<p style='margin-top:0.5rem; font-size:0.9rem; color:var(--text-color-60);'>" + explicacion + "</p>" if explicacion else ""}
    </div>
    """
    st.markdown(html_card, unsafe_allow_html=True)


# =========================
# CARGA DE VARIABLES (Sin cambios)
# =========================
# ... (Mismo bloque de carga de variables del código original) ...
igae = buscar_columna("IGAE")
inflacion_12m = buscar_columna("Variación a doce meses")
inflacion_mensual = buscar_columna("Variación mensual inflacion total")
inflacion_acumulada = buscar_columna("Variación acumulada en el año")
rin = buscar_columna("Reservas internacionales netas")
tc_venta = buscar_columna("Valor referencial de venta")
tc_oficial = buscar_columna("Tipo de cambio oficial")
if tc_oficial is None:
    tc_oficial = buscar_columna("Tipo de cambio de venta")
bol_dep = buscar_columna("Bolivianización Depósitos")
bol_cred = buscar_columna("Bolivianización Créditos")
base_monetaria = buscar_columna("Base monetaria")
credito_privado = buscar_columna("Crédito del sistema financiero al sector privado")
depositos = buscar_columna("Depósitos en entidades")
exportaciones = buscar_columna("Exportaciones")
importaciones = buscar_columna("Importaciones")
saldo_comercial = buscar_columna("Saldo Comercial")
m1 = buscar_columna("M’1")
m2 = buscar_columna("M’2")
m3 = buscar_columna("M’3")


# =========================
# SIDEBAR (Mínimos cambios)
# =========================
st.sidebar.title("⚙️ Filtros")
if not df_original.empty and "fecha" in df_original.columns:
    fecha_min = df_original["fecha"].min()
    fecha_max = df_original["fecha"].max()
    rango = st.sidebar.date_input(
        "Rango de análisis",
        value=(fecha_min, fecha_max),
        min_value=fecha_min, max_value=fecha_max
    )
    df = df_original.copy()
    if len(rango) == 2:
        inicio, fin = pd.to_datetime(rango[0]), pd.to_datetime(rango[1])
        df = df[(df["fecha"] >= inicio) & (df["fecha"] <= fin)]
else:
    df = df_original.copy()

st.sidebar.markdown("---")
st.sidebar.info("Este dashboard se adapta automáticamente al tema claro/oscuro de tu dispositivo.")


# =========================
# HEADER RESPONSIVO
# =========================
# Usamos columnas que se apilan en móviles
col_logo, col_text = st.columns([1, 4], gap="medium")

with col_logo:
    # Placeholder si no existe la imagen para que no se rompa el layout
    try:
        st.image("logo_cengob.png", use_column_width=True)
    except:
         st.markdown("""
        <div style="background: var(--text-color-10); border-radius: 12px; padding: 2rem; text-align: center;">
            <span style="font-size: 3rem;">🏛️</span><br>
            <strong style="color: var(--text-color);">CENGOB</strong>
        </div>
        """, unsafe_allow_html=True)

with col_text:
    # Usamos las clases CSS fluidas definidas al principio
    st.markdown("""
        <h1 class="responsive-h1" style="margin-bottom: 0;">
            Dashboard Macroeconómico
        </h1>
        <h2 class="responsive-h2" style="margin-top: 0.5rem;">
            Centro de Gobierno - Bolivia
        </h2>
        <p class="responsive-p" style="margin-top: 1rem;">
            Monitor ejecutivo de coyuntura económica, monetaria y financiera.
        </p>
    """, unsafe_allow_html=True)

st.markdown("---")


# =========================
# KPIs (LAYOUT RESPONSIVO)
# =========================
# En desktop serán 4 columnas, en móvil Streamlit las apilará automáticamente
c1, c2, c3, c4 = st.columns(4)
with c1: kpi(df, "Actividad (IGAE)", igae, "")
with c2: kpi(df, "Inflación 12m", inflacion_12m, "%")
with c3: kpi(df, "RIN", rin, "M $us")
with c4: kpi(df, "TC Venta", tc_venta, "Bs/$us")

st.markdown("<br>", unsafe_allow_html=True) # Espacio

c5, c6, c7, c8 = st.columns(4)
with c5: kpi(df, "Base Monetaria", base_monetaria, "M Bs")
with c6: kpi(df, "Crédito Privado", credito_privado, "M Bs")
with c7: kpi(df, "Depósitos", depositos, "M Bs")
with c8: kpi(df, "Saldo Comercial", saldo_comercial, "M $us")

st.markdown("---")

# Mensaje ejecutivo usando el estilo nativo que se adapta al tema
st.info(
    "**💡 Lectura ejecutiva:** La inflación se mantiene en zona de alerta, "
    "mientras las reservas internacionales continúan siendo el principal factor de riesgo externo."
)

# =========================
# TABS
# =========================
# Se simplificaron los iconos para asegurar compatibilidad
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈 Resumen", "🔥 Inflación", "🌎 Externo", "💵 Monetario", "🏦 Financiero", "⚠️ Riesgos"
])

# --- TAB 1: RESUMEN ---
with tab1:
    # Layout 2x2 que se convierte en 1x4 en móvil
    row1_col1, row1_col2 = st.columns(2)
    with row1_col1: grafico_linea(df, igae, "IGAE - Actividad económica")
    with row1_col2: grafico_linea(df, inflacion_12m, "Inflación interanual", "%")

    row2_col1, row2_col2 = st.columns(2)
    with row2_col1: grafico_linea(df, rin, "Reservas Internacionales (RIN)", "M $us")
    with row2_col2: grafico_lineas_multiples(df, [credito_privado, depositos], "Sistema Financiero", "M Bs")

# --- TAB 2: INFLACIÓN ---
with tab2:
    grafico_linea(df, inflacion_12m, "Inflación a doce meses (Principal)", "%")
    st.markdown("### Indicadores complementarios")
    i1, i2 = st.columns(2)
    with i1: grafico_linea(df, inflacion_mensual, "Variación mensual", "%")
    with i2: grafico_linea(df, inflacion_acumulada, "Acumulada en el año", "%")

# --- TAB 3: EXTERNO ---
with tab3:
    a, b = st.columns(2)
    with a: grafico_linea(df, rin, "Reservas Internacionales Netas", "M $us")
    with b: grafico_lineas_multiples(df, [tc_venta, tc_oficial], "Tipo de Cambio (Oficial vs Mercado)", "Bs/$us")

    c, d = st.columns(2)
    with c: grafico_linea(df, exportaciones, "Exportaciones Totales", "M $us")
    with d: grafico_linea(df, importaciones, "Importaciones Totales", "M $us")

# --- TAB 4: MONETARIO ---
with tab4:
    grafico_lineas_multiples(df, [m1, m2, m3], "Agregados Monetarios (M1, M2, M3)", "M Bs")
    grafico_linea(df, base_monetaria, "Base Monetaria", "M Bs")

# --- TAB 5: FINANCIERO ---
with tab5:
    a, b = st.columns(2)
    with a: grafico_lineas_multiples(df, [credito_privado, depositos], "Crédito y Depósitos", "M Bs")
    with b: grafico_lineas_multiples(df, [bol_dep, bol_cred], "Bolivianización (%)", "%")


# =========================
# TAB 6: RIESGOS (REDITADO CON NUEVAS TARJETAS)
# =========================
with tab6:
    st.subheader("🚦 Semáforo de Riesgos Macroeconómicos")
    st.markdown("Monitoreo de umbrales críticos de las principales variables.")
    st.markdown("<br>", unsafe_allow_html=True)

    # Cálculo de valores (Sin cambios en la lógica)
    infl_val, _ = ultimo_valor(df, inflacion_12m)
    rin_val, _ = ultimo_valor(df, rin)
    tc_ref_val, _ = ultimo_valor(df, tc_venta)
    tc_of_val, _ = ultimo_valor(df, tc_oficial)

    brecha_tc = None
    if tc_ref_val is not None and tc_of_val is not None and tc_of_val != 0:
        brecha_tc = ((tc_ref_val / tc_of_val) - 1) * 100

    cred_yoy = variacion_interanual(df, credito_privado)

    # Funciones de clasificación simples
    def clasificar(valor, umbral_bajo, umbral_alto, invertido=False):
        if valor is None: return "Sin dato"
        if not invertido:
            if valor < umbral_bajo: return "Bajo"
            elif valor < umbral_alto: return "Moderado"
            else: return "Alto"
        else: # Para variables donde menor es peor (ej. RIN)
            if valor > umbral_alto: return "Bajo"
            elif valor > umbral_bajo: return "Moderado"
            else: return "Alto"

    # Clasificación
    riesgo_infl = clasificar(infl_val, 3, 6)
    riesgo_rin = clasificar(rin_val, 2000, 5000, invertido=True)
    # Asumimos brecha porcentual: <5% bajo, <20% moderado, >20% alto
    riesgo_tc = clasificar(brecha_tc, 5, 20)
    riesgo_cred = clasificar(cred_yoy, 5, 15)

    # Layout de tarjetas responsivas
    # Usamos st.container para agruparlas y CSS grid si quisieramos más control,
    # pero st.columns(4) funciona decentemente en móvil apilándose.
    rc1, rc2, rc3, rc4 = st.columns(4, gap="medium")

    with rc1: tarjeta_riesgo_moderna("Riesgo Inflacionario", riesgo_infl, f"Inflación actual: {formato_numero(infl_val)}%")
    with rc2: tarjeta_riesgo_moderna("Posición Externa (RIN)", riesgo_rin, f"Nivel RIN: {formato_numero(rin_val)} M$us")
    with rc3: tarjeta_riesgo_moderna("Presión Cambiaria", riesgo_tc, f"Brecha aprox: {formato_numero(brecha_tc)}%")
    with rc4: tarjeta_riesgo_moderna("Expansión Crediticia", riesgo_cred, f"Crecimiento: {formato_numero(cred_yoy)}%")

    st.markdown("<br>", unsafe_allow_html=True)
    st.warning("Nota: Los umbrales son referenciales para el monitoreo ejecutivo.")

# =========================
# EXPLORADOR (Añadido al final para completar)
# =========================
st.markdown("---")
st.subheader("🔎 Explorador de variables")
variables_excluir = [
    "Bolivianización (%)_1",
    "Bolivianización (%)_2",
    "Bolivianización (%)_3",
    "Bolivianización (%)_4",
    "A la vista",
    "Caja de ahorro",
    "Plazo",
    "Otros"
]

variables = [
    c for c in df.columns
    if c != "fecha" and c not in variables_excluir
]
seleccion = st.selectbox("Selecciona cualquier variable del Excel para explorarla:", variables)
grafico_linea(df, seleccion, seleccion)

# Botón de descarga con estilo
st.download_button(
    label="⬇️ Descargar base de datos filtrada (CSV)",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name="base_macro_filtrada.csv",
    mime="text/csv",
    use_container_width=True
)