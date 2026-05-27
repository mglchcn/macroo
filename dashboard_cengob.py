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

    /* Insignias (Badges) para metadatos */
    .badge-meta {
        display: inline-flex;
        align-items: center;
        background-color: var(--card-bg);
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 500;
        border: 1px solid var(--card-border-color);
        color: var(--text-color-80);
        margin-right: 10px;
        margin-bottom: 10px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
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
# CARGA DE DATOS
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
# METADATOS DEL DASHBOARD
# =========================
fecha_ultima_act = df_original["fecha"].max()
str_ultima_act = fecha_ultima_act.strftime('%d/%m/%Y') if not pd.isna(fecha_ultima_act) else "Desconocida"
cantidad_variables = len(df_original.columns) - 1  # Restamos la columna 'fecha'

# =========================
# FUNCIONES DE AYUDA
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
    # FIX: Usar pd.DateOffset para mayor precisión
    base_fecha = actual["fecha"] - pd.DateOffset(years=1)
    ant = s[s["fecha"] <= base_fecha]
    if ant.empty: return None
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
    st.metric(titulo, f"{formato_numero(valor)} {unidad}", delta)
    st.markdown(f"<small style='color:var(--text-color-60)'>Ult. dato: {fecha.strftime('%d/%m/%y')}</small>", unsafe_allow_html=True)


# =========================
# FUNCIONES GRÁFICAS
# =========================
def aplicar_tema_plotly(fig, titulo, unidad=""):
    fig.update_layout(
        title=dict(
            text=titulo,
            font=dict(size=18, family="Source Sans Pro")
        ),
        height=400,
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
            bgcolor="rgba(0,0,0,0)"
        ),
    )
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
            mode="lines", line=dict(width=3),
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
                bgcolor="var(--secondary-background-color)",
            ),
            type="date"
        ),
    )
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
                    mode="lines", name=c[:30],
                    line=dict(width=3),
                    hovertemplate="%{x|%d/%m/%Y}<br>%{y:,.2f}<extra></extra>"
                )
            )

    fig = aplicar_tema_plotly(fig, titulo, unidad)
    st.plotly_chart(fig, use_container_width=True, key=f"multi_{titulo[:10]}")


def tarjeta_riesgo_moderna(titulo, nivel, explicacion=""):
    colores_estado = {
        "Alto": ("#ef4444", "🔴"),
        "Moderado": ("#f59e0b", "🟡"),
        "Bajo": ("#22c55e", "🟢"),
        "Adecuado": ("#22c55e", "🟢"),
        "Crítico": ("#b91c1c", "⚫"),
        "Sin dato": ("#9ca3af", "⚪")
    }
    color_hex, icono = colores_estado.get(nivel, ("#9ca3af", "⚪"))
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
# CARGA DE VARIABLES
# =========================
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
# SIDEBAR
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
# HEADER RESPONSIVO Y MEJORADO
# =========================
col_logo, col_text = st.columns([1, 4], gap="medium")

with col_logo:
    # Mostramos el logo de CENGOB de forma directa
    st.image("logo_cengob.png", use_column_width=True)

with col_text:
    # Incluye el título fluido y las nuevas insignias de metadatos
    st.markdown(f"""
        <h1 class="responsive-h1" style="margin-bottom: 0;">
            Dashboard Macroeconómico
        </h1>
        <h2 class="responsive-h2" style="margin-top: 0.2rem; margin-bottom: 1rem;">
            Centro de Gobierno - Bolivia
        </h2>
        
        <div style="display: flex; flex-wrap: wrap; margin-bottom: 1rem;">
            <div class="badge-meta">
                📅 Última actualización: <span style="color:var(--text-color); margin-left:5px; font-weight:700;">{str_ultima_act}</span>
            </div>
            <div class="badge-meta">
                📊 Variables monitoreadas: <span style="color:var(--text-color); margin-left:5px; font-weight:700;">{cantidad_variables}</span>
            </div>
        </div>
        
        <p class="responsive-p" style="margin-top: 0.5rem;">
            Monitor ejecutivo interactivo de coyuntura económica, monetaria y financiera.
        </p>
    """, unsafe_allow_html=True)

st.markdown("---")


# =========================
# KPIs
# =========================
c1, c2, c3, c4 = st.columns(4)
with c1: kpi(df, "Actividad (IGAE)", igae, "")
with c2: kpi(df, "Inflación 12m", inflacion_12m, "%")
with c3: kpi(df, "RIN", rin, "M $us")
with c4: kpi(df, "TC Venta", tc_venta, "Bs/$us")

st.markdown("<br>", unsafe_allow_html=True) 

c5, c6, c7, c8 = st.columns(4)
with c5: kpi(df, "Base Monetaria", base_monetaria, "M Bs")
with c6: kpi(df, "Crédito Privado", credito_privado, "M Bs")
with c7: kpi(df, "Depósitos", depositos, "M Bs")
with c8: kpi(df, "Saldo Comercial", saldo_comercial, "M $us")

st.markdown("---")

st.info(
    "**💡 Lectura ejecutiva:** La inflación se mantiene en zona de alerta, "
    "mientras las reservas internacionales continúan siendo el principal factor de riesgo externo."
)

# =========================
# TABS
# =========================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈 Resumen", "🔥 Inflación", "🌎 Externo", "💵 Monetario", "🏦 Financiero", "⚠️ Riesgos"
])

with tab1:
    row1_col1, row1_col2 = st.columns(2)
    with row1_col1: grafico_linea(df, igae, "IGAE - Actividad económica")
    with row1_col2: grafico_linea(df, inflacion_12m, "Inflación interanual", "%")

    row2_col1, row2_col2 = st.columns(2)
    with row2_col1: grafico_linea(df, rin, "Reservas Internacionales (RIN)", "M $us")
    with row2_col2: grafico_lineas_multiples(df, [credito_privado, depositos], "Sistema Financiero", "M Bs")

with tab2:
    grafico_linea(df, inflacion_12m, "Inflación a doce meses (Principal)", "%")
    st.markdown("### Indicadores complementarios")
    i1, i2 = st.columns(2)
    with i1: grafico_linea(df, inflacion_mensual, "Variación mensual", "%")
    with i2: grafico_linea(df, inflacion_acumulada, "Acumulada en el año", "%")

with tab3:
    a, b = st.columns(2)
    with a: grafico_linea(df, rin, "Reservas Internacionales Netas", "M $us")
    with b: grafico_lineas_multiples(df, [tc_venta, tc_oficial], "Tipo de Cambio (Oficial vs Mercado)", "Bs/$us")

    c, d = st.columns(2)
    with c: grafico_linea(df, exportaciones, "Exportaciones Totales", "M $us")
    with d: grafico_linea(df, importaciones, "Importaciones Totales", "M $us")

with tab4:
    grafico_lineas_multiples(df, [m1, m2, m3], "Agregados Monetarios (M1, M2, M3)", "M Bs")
    grafico_linea(df, base_monetaria, "Base Monetaria", "M Bs")

with tab5:
    a, b = st.columns(2)
    with a: grafico_lineas_multiples(df, [credito_privado, depositos], "Crédito y Depósitos", "M Bs")
    with b: grafico_lineas_multiples(df, [bol_dep, bol_cred], "Bolivianización (%)", "%")

with tab6:
    st.subheader("🚦 Semáforo de Riesgos Macroeconómicos")
    st.markdown("Monitoreo de umbrales críticos de las principales variables.")
    st.markdown("<br>", unsafe_allow_html=True)

    infl_val, _ = ultimo_valor(df, inflacion_12m)
    rin_val, _ = ultimo_valor(df, rin)
    tc_ref_val, _ = ultimo_valor(df, tc_venta)
    tc_of_val, _ = ultimo_valor(df, tc_oficial)

    brecha_tc = None
    if tc_ref_val is not None and tc_of_val is not None and tc_of_val != 0:
        brecha_tc = ((tc_ref_val / tc_of_val) - 1) * 100

    cred_yoy = variacion_interanual(df, credito_privado)

    def clasificar(valor, umbral_bajo, umbral_alto, invertido=False):
        if valor is None: return "Sin dato"
        if not invertido:
            if valor < umbral_bajo: return "Bajo"
            elif valor < umbral_alto: return "Moderado"
            else: return "Alto"
        else:
            if valor > umbral_alto: return "Bajo"
            elif valor > umbral_bajo: return "Moderado"
            else: return "Alto"

    riesgo_infl = clasificar(infl_val, 3, 6)
    riesgo_rin = clasificar(rin_val, 2000, 5000, invertido=True)
    riesgo_tc = clasificar(brecha_tc, 5, 20)
    riesgo_cred = clasificar(cred_yoy, 5, 15)

    rc1, rc2, rc3, rc4 = st.columns(4, gap="medium")

    with rc1: tarjeta_riesgo_moderna("Riesgo Inflacionario", riesgo_infl, f"Inflación actual: {formato_numero(infl_val)}%")
    with rc2: tarjeta_riesgo_moderna("Posición Externa (RIN)", riesgo_rin, f"Nivel RIN: {formato_numero(rin_val)} M$us")
    with rc3: tarjeta_riesgo_moderna("Presión Cambiaria", riesgo_tc, f"Brecha aprox: {formato_numero(brecha_tc)}%")
    with rc4: tarjeta_riesgo_moderna("Expansión Crediticia", riesgo_cred, f"Crecimiento: {formato_numero(cred_yoy)}%")

    st.markdown("<br>", unsafe_allow_html=True)
    st.warning("Nota: Los umbrales son referenciales para el monitoreo ejecutivo.")

# =========================
# EXPLORADOR
# =========================
st.markdown("---")
st.subheader("🔎 Explorador de variables")
variables_excluir = [
    "Bolivianización (%)_1", "Bolivianización (%)_2",
    "Bolivianización (%)_3", "Bolivianización (%)_4",
    "A la vista", "Caja de ahorro", "Plazo", "Otros"
]

variables = [
    c for c in df.columns
    if c != "fecha" and c not in variables_excluir
]
seleccion = st.selectbox("Selecciona cualquier variable del Excel para explorarla:", variables)
grafico_linea(df, seleccion, seleccion)

st.download_button(
    label="⬇️ Descargar base de datos filtrada (CSV)",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name="base_macro_filtrada.csv",
    mime="text/csv",
    use_container_width=True
)
