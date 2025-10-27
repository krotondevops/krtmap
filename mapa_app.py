import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import urllib.request

# --- Configuración de la Página ---
st.set_page_config(layout="wide", page_title="Clientes Canal Operador")

# --- CSS para Impresión PDF ---
print_style = """
<style>
    @media print {
        @page {
            size: landscape !important; 
            margin: 1cm !important;
        }
        body {
            -webkit-print-color-adjust: exact !important;
            color-adjust: exact !important;
        }
        [data-testid="stSidebar"], [data-testid="stHeader"], .noprint {
            display: none !important;
        }
        [data-testid="stAppViewContainer"] {
            padding: 0 !important;
            margin: 0 !important;
        }
        [data-testid="block-container"] {
            padding: 0 !important;
            margin: 0 !important;
        }
    }
    .print-button {
        width: 100%;
        padding: 8px;
        background-color: #FF4B4B; 
        color: white;
        border: none;
        border-radius: 5px;
        cursor: pointer;
        font-weight: bold;
        margin-top: 10px;
    }
    .print-button:hover {
        background-color: #CC3C3C;
    }
</style>
"""
st.html(print_style)

# --- 0. Función de Formato K/M ---
def format_k_m(num):
    """Convierte un número a formato K (miles) o M (millones)"""
    if not pd.isna(num):
        if abs(num) >= 1_000_000:
            return f"{num / 1_000_000:.1f}M"
        if abs(num) >= 1_000:
            return f"{num / 1_000:.0f}K"
        return f"{num:.0f}"
    return "N/A"

# --- 1. Nombres de Columnas en tu CSV ---
COL_ZONA = "ZONA DEL PERU"
COL_CLIENTES = "NÚMERO DE CLIENTES"
COL_FACTURACION = "FACTURACIÓN USD 2025"
COL_LAT = "LATITUD"
COL_LNG = "LONGITUD"
COL_ZONA_PRINCIPAL = "ZONA_PRINCIPAL" 
COL_FACTURACION_STR = "Facturación (USD)"

# --- 2. Carga y Procesamiento de Datos ---
@st.cache_data
def load_and_process_data(filepath):
    try:
        df_raw = pd.read_csv(filepath, sep=';')
    except FileNotFoundError:
        st.error(f"Error: No se encontró el archivo en la ruta '{filepath}'.")
        st.error("Asegúrate de que 'dataset_zonas.csv' esté en la misma carpeta que el script.")
        st.stop()
    except Exception as e:
        st.error(f"Error al leer el archivo CSV: {e}")
        st.stop()

    cols_necesarias = [COL_ZONA, COL_CLIENTES, COL_FACTURACION, COL_LAT, COL_LNG]
    if not all(col in df_raw.columns for col in cols_necesarias):
        st.error(f"Error: El CSV debe tener las columnas: {', '.join(cols_necesarias)}")
        st.subheader("Columnas encontradas:")
        st.write(list(df_raw.columns))
        st.stop()

    df_raw[COL_ZONA] = df_raw[COL_ZONA].str.strip()
    df_raw[COL_LAT] = pd.to_numeric(df_raw[COL_LAT], errors='coerce')
    df_raw[COL_LNG] = pd.to_numeric(df_raw[COL_LNG], errors='coerce')
    df_raw[COL_FACTURACION] = pd.to_numeric(df_raw[COL_FACTURACION], errors='coerce')
    df_final = df_raw.dropna(subset=[COL_LAT, COL_LNG, COL_FACTURACION])

    def categorizar_zona(zona_str):
        zona_str = str(zona_str).upper()
        if "LIMA" == zona_str: return "LIMA"
        if "CENTRO" in zona_str: return "CENTRO"
        if "NORTE" in zona_str: return "NORTE"
        if "SUR" in zona_str: return "SUR"
        if "ORIENTE" in zona_str: return "ORIENTE"
        return "OTRO"

    df_final[COL_ZONA_PRINCIPAL] = df_final[COL_ZONA].apply(categorizar_zona)
    
    df_final[COL_FACTURACION_STR] = df_final[COL_FACTURACION].apply(lambda x: f"$ {format_k_m(x)}")
    
    return df_final, df_final[COL_CLIENTES].sum(), df_final[COL_FACTURACION].sum(), len(df_final)

# --- 3. Cargar GeoJSON de Perú ---
@st.cache_data
def load_geojson(url):
    try:
        with urllib.request.urlopen(url) as response:
            geojson_data = json.loads(response.read().decode())
        return geojson_data
    except Exception as e:
        st.warning(f"No se pudo cargar el contorno de Perú (GeoJSON): {e}")
        return None

# --- Carga de Datos ---
df, total_clientes, total_facturacion, total_registros = load_and_process_data(
    'dataset_zonas.csv' 
)
GEOJSON_URL = 'https://raw.githubusercontent.com/juaneladio/peru-geojson/master/peru_departamental_simple.geojson'
peru_geojson = load_geojson(GEOJSON_URL)

# --- 4. Lógica de Estilo (Colores y Rangos) ---
bins = [0, 50, 100, 200, 500, float('inf')]
labels = ['1-50 clientes', '51-100 clientes', '101-200 clientes', '201-500 clientes', '501+ clientes']
if not df.empty:
    df['rango_clientes'] = pd.cut(df[COL_CLIENTES], bins=bins, labels=labels, right=True)
else:
    df['rango_clientes'] = []

color_map = {
    '1-50 clientes': '#bbf7d0',   # Verde Pastel
    '51-100 clientes': '#d9f99d',  # Lima Pastel
    '101-200 clientes': '#fef08a',  # Amarillo Pastel
    '201-500 clientes': '#fed7aa',  # Naranja Pastel
    '501+ clientes': '#fecaca'   # Rojo Pastel
}

# --- 5. Panel Lateral (Sidebar) ---
st.sidebar.image(
    "https://studio--krt-db.us-central1.hosted.app/images/kroton_logo.png", 
    width=150
)
st.sidebar.title("Clientes del Canal Operador")

st.sidebar.metric(
    "Total Clientes",
    f"{total_clientes:,.0f}",
    f"{total_registros} registros/provincias"
)
# --- AQUÍ ESTÁ EL CAMBIO ---
st.sidebar.metric(
    "Total Facturación (USD) ENE-SET 2025", # <-- Texto modificado
    f"$ {format_k_m(total_facturacion)}"
)
# --- FIN DEL CAMBIO ---
st.sidebar.divider()

st.sidebar.subheader("📊 Resumen por Zona Principal")
df_resumen_zona = df.groupby(COL_ZONA_PRINCIPAL)[[COL_CLIENTES, COL_FACTURACION]].sum().reset_index()
df_resumen_zona[COL_FACTURACION_STR] = df_resumen_zona[COL_FACTURACION].apply(lambda x: f"$ {format_k_m(x)}")
df_resumen_zona = df_resumen_zona.sort_values(COL_CLIENTES, ascending=False)
max_val_resumen = 1 if df_resumen_zona.empty else int(df_resumen_zona[COL_CLIENTES].max())

st.sidebar.dataframe(
    df_resumen_zona[[COL_ZONA_PRINCIPAL, COL_CLIENTES, COL_FACTURACION_STR]].set_index(COL_ZONA_PRINCIPAL),
    use_container_width=True,
    column_config={
        COL_CLIENTES: st.column_config.ProgressColumn(
            "Clientes",
            format="%f",
            min_value=0,
            max_value=max_val_resumen,
        ),
    }
)
st.sidebar.divider()

st.sidebar.subheader("📈 Detalle por Provincia")
df_zonas = df.sort_values(COL_CLIENTES, ascending=False)
max_val_detalle = 1 if df_zonas.empty else int(df_zonas[COL_CLIENTES].max())

st.sidebar.dataframe(
    df_zonas[[COL_ZONA, COL_CLIENTES, COL_FACTURACION_STR]].set_index(COL_ZONA),
    use_container_width=True,
    height=400,
    column_config={
        COL_CLIENTES: st.column_config.ProgressColumn(
            "Clientes",
            format="%f",
            min_value=0,
            max_value=max_val_detalle,
        ),
    }
)
st.sidebar.divider()

st.sidebar.subheader("ℹ️ Leyenda")
for label in labels:
    color = color_map.get(label, '#ccc')
    st.sidebar.markdown(f'<span style="display:flex; align-items:center; margin-bottom: 5px;"><div style="width:16px; height:16px; background-color:{color}; border-radius:50%; margin-right:10px; border: 2px solid #ddd;"></div><span>{label}</span></span>', unsafe_allow_html=True)

# --- Botón de Impresión PDF ---
st.sidebar.divider()
st.sidebar.markdown(
    '<button onclick="window.print()" class="noprint print-button">🖨️ Exportar a PDF (Horizontal)</button>',
    unsafe_allow_html=True
)

# --- 6. Contenido Principal ---
st.caption("Distribución geográfica por Zona / Provincia (Datos del CSV)")

fig = px.scatter_mapbox(
    df,
    lat=COL_LAT,
    lon=COL_LNG,
    size=COL_CLIENTES, 
    color="rango_clientes",
    color_discrete_map=color_map,
    category_orders={"rango_clientes": labels},
    hover_name=COL_ZONA,
    hover_data={
        COL_CLIENTES: ':,d', 
        COL_FACTURACION_STR: True,
        COL_FACTURACION: False,
        COL_LAT: False,
        COL_LNG: False,
        "rango_clientes": False
    },
    size_max=50,
    opacity=0.7,
    zoom=4.8,
    center={"lat": -10.0, "lon": -76.0}
)

fig.add_trace(go.Scattermapbox(
    lat=df[COL_LAT],
    lon=df[COL_LNG],
    mode='text',
    text=df[COL_CLIENTES].astype(str),
    textfont=dict(
        size=16,
        color='black'
    ),
    name='Cantidad',
    hoverinfo='none'
))

fig.update_layout(
    mapbox_style="carto-positron", 
    margin={"r":0,"t":0,"l":0,"b":0},
    showlegend=False,
    height=800
)

# --- Contorno de Perú (Líneas Claras) ---
if peru_geojson:
    fig.update_layout(
        mapbox_layers=[
            {
                "source": peru_geojson,
                "type": "line",
                "color": "#9C9C9C", # Gris muy claro
                "line": {"width": 1}
            }
        ]
    )

st.plotly_chart(fig, use_container_width=True)