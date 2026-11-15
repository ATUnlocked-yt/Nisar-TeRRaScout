"""Keyless MapLibre global map for NISAR candidate regions.

Copy this file to visualization/map.py. The basemap comes from OpenFreeMap;
MapLibre includes the required map attribution. No provider key is required.
"""
import json
import os
from pathlib import Path

STYLE = "https://tiles.openfreemap.org/styles/liberty"


def generate_cluster_interactive_map(output_root, filename, df_regions):
    if df_regions.empty:
        print("No candidate regions; skipping regional vector map generation.")
        return
    os.makedirs(output_root, exist_ok=True)
    output_path = Path(output_root) / filename
    features = []
    for _, row in df_regions.iterrows():
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(row["centroid_lon"]), float(row["centroid_lat"])]},
            "properties": {
                "region": int(row["region_id"]), "area": float(row.get("area_km2", 0)),
                "mean": float(row.get("mean_change_db", 0)), "peak": float(row.get("max_change_db", 0)),
                "direction": str(row.get("change_direction", "")),
                "consistency": str(row.get("temporal_consistency", "")),
                "optical": str(row.get("cross_validation_status", "not run")),
            },
        })
    geo = {"type": "FeatureCollection", "features": features}
    data = json.dumps(geo, ensure_ascii=False).replace("</", "<\\/")
    center_lat = float(df_regions["centroid_lat"].mean())
    center_lon = float(df_regions["centroid_lon"].mean())
    page = f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NISAR candidate regions</title><link href="https://unpkg.com/maplibre-gl@5.6.2/dist/maplibre-gl.css" rel="stylesheet">
<style>html,body,#map{{height:100%;margin:0}}.maplibregl-popup-content{{font:13px Arial;line-height:1.5}}</style><script src="https://unpkg.com/maplibre-gl@5.6.2/dist/maplibre-gl.js"></script></head><body><div id="map"></div>
<script>const DATA={data};const map=new maplibregl.Map({{container:'map',style:'{STYLE}',center:[{center_lon},{center_lat}],zoom:8}});map.addControl(new maplibregl.NavigationControl());map.addControl(new maplibregl.FullscreenControl());
map.on('load',()=>{{map.addSource('regions',{{type:'geojson',data:DATA}});map.addLayer({{id:'regions',type:'circle',source:'regions',paint:{{'circle-radius':12,'circle-color':'#d62728','circle-stroke-color':'#fff','circle-stroke-width':2.5}}}});map.on('click','regions',e=>{{const p=e.features[0].properties;new maplibregl.Popup().setLngLat(e.lngLat).setHTML(`<b>Candidate region #${{p.region}}</b><br>Area: ${{Number(p.area).toFixed(4)}} km²<br>Mean change: ${{Number(p.mean).toFixed(2)}} dB<br>Peak change: ${{Number(p.peak).toFixed(2)}} dB<br>Direction: ${{p.direction}}<br>Temporal pattern: ${{p.consistency}}<br>Optical check: ${{p.optical}}`).addTo(map)}});map.on('mouseenter','regions',()=>map.getCanvas().style.cursor='pointer');map.on('mouseleave','regions',()=>map.getCanvas().style.cursor='')}});</script></body></html>'''
    output_path.write_text(page, encoding="utf-8")
    print(f"   Interactive keyless NISAR map saved to: '{output_path}'")
