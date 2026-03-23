import json

import geopandas as gpd
import pydeck as pdk
import streamlit as st

GPKG_PATH = "2020-kokusei-saikyo.gpkg"

EXCLUDE_COLS = {
    "KEY_CODE", "HCODE", "KBSUM", "X_CODE", "Y_CODE", "KCODE1",
    "HYOSYO", "HTKSYORI", "HTKSAKI", "GASSAN", "AREA_MAX_F",
    "DUMMY1", "R2KAxx", "R2KAxx_ID", "KIHON1", "KIHON2",
    "KEYCODE1", "KEYCODE2",
}


@st.cache_data
def load_data() -> gpd.GeoDataFrame:
    gdf = gpd.read_file(GPKG_PATH)
    if gdf.crs is None or gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs("EPSG:4326")
    return gdf


def value_to_color(norm: float) -> list[int]:
    """0〜1の正規化値をRGBAリストに変換（青→赤グラデーション）"""
    r = int(255 * norm)
    g = int(80 * (1 - norm))
    b = int(230 * (1 - norm))
    return [r, g, b, 180]


def build_geojson(gdf: gpd.GeoDataFrame, col: str):
    values = gdf[col].fillna(0)
    min_val, max_val = float(values.min()), float(values.max())
    span = max_val - min_val if max_val != min_val else 1

    geojson = json.loads(gdf.to_json())
    for feature in geojson["features"]:
        val = feature["properties"].get(col) or 0
        norm = (val - min_val) / span
        feature["properties"]["_color"] = value_to_color(norm)
        feature["properties"]["_value"] = val

    return geojson, min_val, max_val


def main():
    st.set_page_config(page_title="国勢調査 人口マップ", layout="wide")
    st.title("2020年国勢調査 人口マップ")

    gdf = load_data()

    numeric_cols = [
        c for c in gdf.select_dtypes(include=["number"]).columns
        if c not in EXCLUDE_COLS
    ]

    DEFAULT_COL = "総数、年齢\u300c不詳\u300d含む"
    default_index = numeric_cols.index(DEFAULT_COL) if DEFAULT_COL in numeric_cols else 0
    selected_col = st.selectbox("表示する項目を選択", numeric_cols, index=default_index)

    geojson, min_val, max_val = build_geojson(gdf, selected_col)

    layer = pdk.Layer(
        "GeoJsonLayer",
        data=geojson,
        pickable=True,
        stroked=True,
        filled=True,
        get_fill_color="properties._color",
        get_line_color=[255, 255, 255, 180],
        line_width_min_pixels=1,
    )

    bounds = gdf.total_bounds
    center_lon = (bounds[0] + bounds[2]) / 2
    center_lat = (bounds[1] + bounds[3]) / 2

    view_state = pdk.ViewState(
        longitude=center_lon,
        latitude=center_lat,
        zoom=12,
        pitch=0,
    )

    st.pydeck_chart(
        pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            tooltip={"text": "{NAME}\n" + selected_col + ": {_value}"},
            map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        ),
        width="stretch",
        height=600,
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("最小値", f"{min_val:,.0f}")
    col2.metric("最大値", f"{max_val:,.0f}")
    col3.metric("合計", f"{gdf[selected_col].fillna(0).sum():,.0f}")

    st.subheader(f"{selected_col} 降順")
    all_cols = [c for c in gdf.columns if c != "geometry"]
    sorted_df = (
        gdf[all_cols]
        .sort_values(selected_col, ascending=False)
        .reset_index(drop=True)
    )
    sorted_df.index += 1
    st.dataframe(sorted_df, width="stretch", height=400)


if __name__ == "__main__":
    main()
