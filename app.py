import os
import shutil
import json
import csv
import queue
import threading
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import quote
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import pandas as pd


ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

ASF_COUNTRY_GEOJSON = "https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson"
OPENFREEMAP_STYLE = "https://tiles.openfreemap.org/styles/liberty"

# Small discovery AOIs for city and regional searches. Boxes are approximate
# search extents; confirm individual ASF scene footprints before analysis.
LOCATION_AOIS = {
    "Delhi NCR": ("India", 76.65, 28.25, 77.55, 28.95),
    "Mumbai": ("India", 72.70, 18.80, 73.15, 19.35),
    "Pune": ("India", 73.65, 18.30, 74.05, 18.75),
    "Ahmedabad": ("India", 72.35, 22.85, 72.75, 23.20),
    "Jaipur": ("India", 75.55, 26.70, 76.05, 27.10),
    "Lucknow": ("India", 80.75, 26.65, 81.15, 27.00),
    "Bhopal": ("India", 77.20, 23.05, 77.60, 23.45),
    "Kolkata": ("India", 88.15, 22.35, 88.60, 22.75),
    "Guwahati": ("India", 91.55, 25.95, 92.05, 26.45),
    "Srinagar": ("India", 74.65, 34.00, 75.10, 34.30),
    "Dhaka": ("Bangladesh", 90.20, 23.55, 90.60, 23.95),
    "Kathmandu": ("Nepal", 85.15, 27.55, 85.55, 27.90),
    "Colombo": ("Sri Lanka", 79.75, 6.75, 80.05, 7.10),
    "Jakarta": ("Indonesia", 106.55, -6.45, 107.10, -5.95),
    "Nairobi": ("Kenya", 36.65, -1.50, 37.10, -1.10),
    "Sao Paulo": ("Brazil", -46.90, -23.80, -46.25, -23.25),
    "Mexico City": ("Mexico", -99.40, 19.15, -98.95, 19.65),
    "Manila": ("Philippines", 120.85, 14.35, 121.15, 14.80),
    "Bangkok": ("Thailand", 100.30, 13.50, 100.95, 14.05),
    "Istanbul": ("Turkey", 28.65, 40.75, 29.35, 41.35),
    "San Francisco": ("United States of America", -122.60, 37.60, -122.25, 37.90),
    "Los Angeles": ("United States of America", -118.70, 33.65, -118.10, 34.35),
    "New York City": ("United States of America", -74.30, 40.45, -73.65, 40.95),
    "Anchorage": ("United States of America", -150.20, 61.00, -149.50, 61.40),
    "London": ("United Kingdom", -0.55, 51.25, 0.35, 51.75),
    "Paris": ("France", 2.15, 48.70, 2.60, 49.00),
    "Rome": ("Italy", 12.30, 41.70, 12.75, 42.00),
    "Cairo": ("Egypt", 31.05, 29.75, 31.55, 30.20),
    "Lagos": ("Nigeria", 2.75, 6.30, 3.70, 6.80),
    "Cape Town": ("South Africa", 18.20, -34.10, 18.80, -33.70),
    "Riyadh": ("Saudi Arabia", 46.40, 24.40, 47.00, 25.00),
    "Beijing": ("China", 115.70, 39.60, 116.90, 40.40),
    "Tokyo": ("Japan", 139.45, 35.45, 140.00, 35.90),
    "Seoul": ("South Korea", 126.70, 37.35, 127.25, 37.75),
    "Sydney": ("Australia", 150.50, -34.15, 151.40, -33.55),
    "Melbourne": ("Australia", 144.50, -38.10, 145.50, -37.50),
}


def write_keyless_map(output_path, geojson_data, places, regions, catalog, title="NISAR Worldwide Showcase"):
    """Build a detailed global vector map using OpenFreeMap + MapLibre (no key)."""
    safe = lambda value: json.dumps(value, ensure_ascii=False).replace("</", "<\\/")
    page = f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><link href="https://unpkg.com/maplibre-gl@5.6.2/dist/maplibre-gl.css" rel="stylesheet">
<style>html,body,#map{{height:100%;margin:0}}.badge{{position:absolute;z-index:2;top:12px;left:50%;transform:translateX(-50%);background:white;padding:9px 14px;border-radius:7px;font:600 15px Arial;box-shadow:0 2px 8px #0003}}.maplibregl-popup-content{{font:13px Arial;line-height:1.5;max-width:330px}}</style>
<script src="https://unpkg.com/maplibre-gl@5.6.2/dist/maplibre-gl.js"></script></head><body><div class="badge">{title} · Country, city and NISAR layers</div><div id="map"></div>
<script>const WORLD={safe(geojson_data)}, PLACES={safe(places)}, REGIONS={safe(regions)}, CATALOG={safe(catalog)};
const map=new maplibregl.Map({{container:'map',style:'{OPENFREEMAP_STYLE}',center:[0,20],zoom:2}});map.addControl(new maplibregl.NavigationControl());map.addControl(new maplibregl.FullscreenControl());
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
map.on('load',()=>{{map.addSource('countries',{{type:'geojson',data:WORLD}});map.addLayer({{id:'country-fill',type:'fill',source:'countries',paint:{{'fill-color':['case',['>', ['to-number',['get','candidate_regions']],0],'#31a878','#d7e0e8'],'fill-opacity':0.43}}}});map.addLayer({{id:'country-line',type:'line',source:'countries',paint:{{'line-color':'#5c6b78','line-width':0.6}}}});
map.addSource('places',{{type:'geojson',data:{{type:'FeatureCollection',features:PLACES.map(p=>({{type:'Feature',geometry:{{type:'Point',coordinates:[p.lon,p.lat]}},properties:p}}))}}}});map.addLayer({{id:'places-points',type:'circle',source:'places',paint:{{'circle-radius':5,'circle-color':'#1261a0','circle-stroke-color':'white','circle-stroke-width':1.5}}}});
map.addSource('regions',{{type:'geojson',data:{{type:'FeatureCollection',features:REGIONS.map(p=>({{type:'Feature',geometry:{{type:'Point',coordinates:[p.lon,p.lat]}},properties:p}}))}}}});map.addLayer({{id:'region-points',type:'circle',source:'regions',paint:{{'circle-radius':12,'circle-color':'#d62728','circle-stroke-color':'white','circle-stroke-width':2.5}}}});
map.addSource('catalog',{{type:'geojson',data:CATALOG}});map.addLayer({{id:'catalog-fill',type:'fill',source:'catalog',filter:['in',['geometry-type'],['literal',['Polygon','MultiPolygon']]],paint:{{'fill-color':'#ef4444','fill-opacity':0.17}}}});map.addLayer({{id:'catalog-outline',type:'line',source:'catalog',filter:['in',['geometry-type'],['literal',['Polygon','MultiPolygon']]],paint:{{'line-color':'#c81e1e','line-width':1.5}}}});map.addLayer({{id:'catalog-centers',type:'circle',source:'catalog',filter:['==',['geometry-type'],'Point'],paint:{{'circle-radius':8,'circle-color':'#c81e1e','circle-stroke-color':'white','circle-stroke-width':2}}}});
map.on('click','country-fill',e=>{{const p=e.features[0].properties;new maplibregl.Popup().setLngLat(e.lngLat).setHTML(`<b>${{esc(p.showcase_country||p.name||p.ADMIN||'Country')}}</b><br>Status: ${{esc(p.analysis_status||'Not analyzed')}}<br>Candidate regions: ${{esc(p.candidate_regions||0)}}<br>Results: ${{esc(p.results_csv||'No local run yet')}}<br><small>Search ASF for scene coverage and dates.</small>`).addTo(map)}});
map.on('click','places-points',e=>{{const p=e.features[0].properties;new maplibregl.Popup().setLngLat(e.lngLat).setHTML(`<b>${{esc(p.place)}} · ${{esc(p.country)}}</b><br>Center: ${{Number(p.lat).toFixed(4)}}, ${{Number(p.lon).toFixed(4)}}<br>Search box: ${{esc(p.bbox)}}<br>NISAR: search ASF catalog for available acquisitions.`).addTo(map)}});
map.on('click','region-points',e=>{{const p=e.features[0].properties;new maplibregl.Popup().setLngLat(e.lngLat).setHTML(`<b>${{esc(p.title)}}</b><br>Area: ${{esc(p.area)}} km²<br>Mean change: ${{esc(p.change)}} dB<br>Direction: ${{esc(p.direction)}}<br>Optical check: ${{esc(p.optical)}}`).addTo(map)}});
map.on('click','catalog-fill',e=>showCatalog(e));map.on('click','catalog-outline',e=>showCatalog(e));map.on('click','catalog-centers',e=>showCatalog(e));function showCatalog(e){{const p=e.features[0].properties;new maplibregl.Popup().setLngLat(e.lngLat).setHTML(`<b>Official ASF NISAR acquisition</b><br>Product: ${{esc(p.product||'NISAR product')}}<br>Acquired: ${{esc(p.acquired||'date unavailable')}}<br>Level: ${{esc(p.level||'')}}<br>Data maturity: ${{esc(p.maturity||'')}}<br><small>Footprint from ASF catalog metadata.</small>`).addTo(map)}}
for(const layer of ['country-fill','places-points','region-points','catalog-fill','catalog-outline','catalog-centers']){{map.on('mouseenter',layer,()=>map.getCanvas().style.cursor='pointer');map.on('mouseleave',layer,()=>map.getCanvas().style.cursor='')}}
}});</script></body></html>'''
    Path(output_path).write_text(page, encoding="utf-8")


def load_world_geojson(boundary_file):
    """Download once, then reuse the country boundaries for search and maps."""
    boundary_file = Path(boundary_file)
    boundary_file.parent.mkdir(parents=True, exist_ok=True)
    if not boundary_file.exists():
        request = Request(ASF_COUNTRY_GEOJSON, headers={"User-Agent": "NISAR-Showcase/1.0"})
        with urlopen(request, timeout=60) as response:
            boundary_file.write_bytes(response.read())
    with boundary_file.open("r", encoding="utf-8") as source:
        data = json.load(source)
    if not data.get("features"):
        raise ValueError("The cached world country boundary file is empty or invalid.")
    return data


def country_folder_slug(name):
    return "".join(ch if ch.isalnum() else "_" for ch in name).strip("_")


class NISARDesktopApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("NISAR Multi-Temporal Radar Sensor & Field Analyzer")
        self.geometry("1420x900")
        self.minsize(1180, 760)

        # Configure root layout grid
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Base directory configurations
        self.project_dir = os.path.dirname(os.path.abspath(__file__))
        self.datasets_dir = os.path.join(self.project_dir, "datasets")
        self.outputs_root = os.path.join(self.project_dir, "outputs")
        self.outputs_dir = self.outputs_root
        self.events = queue.Queue()
        self.country_bounds = {}
        self.catalog_results = []
        self.catalog_rows = {}
        self.busy = False
        self._map_http_server = None
        os.makedirs(self.datasets_dir, exist_ok=True)
        os.makedirs(self.outputs_root, exist_ok=True)

        # Build UI Components
        self.setup_sidebar()
        self.setup_main_panel()
        self.after(150, self._process_events)

    # =========================================================================
    # SIDEBAR PANEL
    # =========================================================================
    def setup_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=270, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        # Header
        self.title_label = ctk.CTkLabel(
            self.sidebar,
            text="📡 NISAR Radar Platform",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        self.title_label.pack(padx=20, pady=(20, 10))

        self.subtitle_label = ctk.CTkLabel(
            self.sidebar,
            text="Disaster & Environmental Analysis",
            font=ctk.CTkFont(size=12, slant="italic"),
        )
        self.subtitle_label.pack(padx=20, pady=(0, 20))

        # Folder Upload Section
        self.btn_upload = ctk.CTkButton(
            self.sidebar,
            text="📂 Upload Dataset Folder",
            font=ctk.CTkFont(weight="bold"),
            command=self.upload_dataset_folder,
        )
        self.btn_upload.pack(padx=20, pady=10)

        # Dataset Selection Dropdown
        self.dataset_label = ctk.CTkLabel(
            self.sidebar, text="Active Location / Dataset:", anchor="w"
        )
        self.dataset_label.pack(padx=20, pady=(15, 0), anchor="w")

        self.dataset_menu = ctk.CTkOptionMenu(
            self.sidebar, values=self.get_available_datasets(), command=self.on_dataset_selected
        )
        self.dataset_menu.pack(padx=20, pady=5)

        # Run Analysis Pipeline Button
        self.btn_run = ctk.CTkButton(
            self.sidebar,
            text="🚀 Run Pipeline Analysis",
            fg_color="#1f77b4",
            hover_color="#145a8d",
            font=ctk.CTkFont(weight="bold"),
            command=self.run_pipeline,
        )
        self.btn_run.pack(padx=20, pady=(25, 10))

        # Status Box
        self.status_box = ctk.CTkTextbox(self.sidebar, height=180, width=230)
        self.status_box.pack(padx=20, pady=(20, 10))
        self.log_status("System Initialized.\nReady to import .h5 telemetry.")

    # =========================================================================
    # MAIN DISPLAY TAB VIEW
    # =========================================================================
    def setup_main_panel(self):
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        self.tabview = ctk.CTkTabview(self.main_frame)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        # Define Application Tabs
        self.tab_decoded = self.tabview.add("📊 Decoded Findings")
        self.tab_map = self.tabview.add("🗺️ Interactive Map")
        self.tab_rasters = self.tabview.add("🖼️ Raster Presenter")
        self.tab_theory = self.tabview.add("📚 Scientific Theory Hub")
        self.tab_world = self.tabview.add("🌍 Worldwide Data")

        # Initialize Individual Tab Contents
        self.setup_decoded_tab()
        self.setup_map_tab()
        self.setup_raster_tab()
        self.setup_theory_tab()
        self.setup_worldwide_tab()

    # =========================================================================
    # TAB 1: DECODED FINDINGS & LOCATION METRICS
    # =========================================================================
    def setup_decoded_tab(self):
        self.scroll_decoded = ctk.CTkScrollableFrame(self.tab_decoded)
        self.scroll_decoded.pack(fill="both", expand=True, padx=10, pady=10)

        self.lbl_decoded_title = ctk.CTkLabel(
            self.scroll_decoded,
            text="🔍 Plain-English Regional Analysis",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        self.lbl_decoded_title.pack(anchor="w", padx=10, pady=(10, 5))

        self.btn_refresh_decoded = ctk.CTkButton(
            self.scroll_decoded,
            text="🔄 Decode Latest Output Data",
            command=self.populate_decoded_data,
        )
        self.btn_refresh_decoded.pack(anchor="w", padx=10, pady=(0, 15))

        self.txt_decoded = ctk.CTkTextbox(
            self.scroll_decoded, height=520, font=ctk.CTkFont(size=13, family="Courier")
        )
        self.txt_decoded.pack(fill="both", expand=True, padx=10, pady=5)

        # Initial Auto-Populate
        self.populate_decoded_data()

    def populate_decoded_data(self):
        self.txt_decoded.delete("1.0", tk.END)
        csv_path = os.path.join(self.outputs_dir, "06_candidate_regions.csv")

        if not os.path.exists(csv_path):
            self.txt_decoded.insert(
                tk.END,
                "⚠️ No output database detected (06_candidate_regions.csv missing).\n\n"
                "To see decoded metrics:\n"
                "1. Upload a dataset folder using the left sidebar.\n"
                "2. Click 'Run Pipeline Analysis' to process the location.\n"
                "3. Click 'Decode Latest Output Data' above.\n",
            )
            return

        try:
            df = pd.read_csv(csv_path)

            report = []
            report.append("=" * 75)
            report.append("          DYNAMIC NISAR RADAR DECODER — LOCATION REPORT")
            report.append("=" * 75 + "\n")

            total_regions = len(df)
            total_area = df["area_km2"].sum() if "area_km2" in df.columns else 0.0

            report.append(f"📌 LOCATION OVERVIEW:")
            report.append(f" • Detected Change Zones : {total_regions} continuous regions")
            report.append(f" • Total Area Impacted  : {total_area:.2f} sq. km")
            report.append(
                f" • Signal Drop Context  : Negative dB indicates standing water, mud,"
            )
            report.append(
                f"                           or destroyed forest canopy structure.\n"
            )

            report.append("-" * 75)
            report.append("🚨 TOP HIGH-SEVERITY DISASTER ZONES (RANKED BY SIGNAL DROP)")
            report.append("-" * 75)

            # Sort by mean change (lowest dB = strongest drop)
            if "mean_change_db" in df.columns:
                top_df = df.sort_values(by="mean_change_db", ascending=True).head(10)
            else:
                top_df = df.head(10)

            for idx, row in top_df.iterrows():
                reg_id = int(row.get("region_id", idx))
                area = row.get("area_km2", 0.0)
                lat = row.get("centroid_lat", 0.0)
                lon = row.get("centroid_lon", 0.0)
                mean_db = row.get("mean_change_db", 0.0)
                max_db = row.get("max_change_db", 0.0)

                # Translate dB into plain language severity
                if mean_db < -4.0:
                    severity = "CRITICAL INUNDATION / STRUCTURAL COLLAPSE"
                elif mean_db < -3.0:
                    severity = "SEVERE LAND WATERLOGGING / VEGETATION LOSS"
                else:
                    severity = "MODERATE SOIL SATURATION / SURFACE ALTERATION"

                report.append(
                    f"\n▶ Zone ID #{reg_id} | Location: {lat:.6f}°N, {lon:.6f}°E"
                )
                report.append(f"   • Affected Coverage : {area:.2f} sq. km")
                report.append(
                    f"   • Mean Radar Drop   : {mean_db:.2f} dB  --->  [{severity}]"
                )
                report.append(f"   • Peak Radar Drop   : {max_db:.2f} dB")
                report.append(
                    f"   • Plain Explanation : The satellite observed a massive decrease in"
                )
                report.append(
                    f"                         signal reflection here. Radio waves bounced away"
                )
                report.append(
                    f"                         due to smooth standing water or lost foliage."
                )

            report.append("\n" + "=" * 75)
            report.append("END OF DECODED REPORT")
            report.append("=" * 75)

            self.txt_decoded.insert(tk.END, "\n".join(report))
            self.log_status("Decoded output data successfully.")

        except Exception as e:
            self.txt_decoded.insert(
                tk.END, f"Error decoding location dataset: {str(e)}"
            )

    # =========================================================================
    # TAB 2: INTERACTIVE MAP
    # =========================================================================
    def setup_map_tab(self):
        lbl = ctk.CTkLabel(
            self.tab_map,
            text="Interactive Geographic Map & Region Inspection",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        lbl.pack(pady=(15, 5))

        lbl_sub = ctk.CTkLabel(
            self.tab_map,
            text="Launches a interactive viewer loaded with your generated '05_interactive_map.html'",
            font=ctk.CTkFont(size=12),
        )
        lbl_sub.pack(pady=(0, 15))

        btn_launch = ctk.CTkButton(
            self.tab_map,
            text="🌐 Launch Interactive Vector Map",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=45,
            fg_color="#2ca02c",
            hover_color="#1e6b1e",
            command=self.open_interactive_map,
        )
        btn_launch.pack(pady=20)

    def open_interactive_map(self):
        # Rebuild from the active CSV so an older HTML file that still points at
        # OpenStreetMap's public tile server is not silently reopened.
        csv_path = os.path.join(self.outputs_dir, "06_candidate_regions.csv")
        if os.path.isfile(csv_path):
            try:
                regions = pd.read_csv(csv_path)
                if not regions.empty:
                    from visualization.map import generate_cluster_interactive_map
                    os.makedirs(self.outputs_dir, exist_ok=True)
                    generate_cluster_interactive_map(
                        self.outputs_dir, "05_interactive_map.html", regions
                    )
                    regenerated = os.path.join(self.outputs_dir, "05_interactive_map.html")
                    if os.path.isfile(regenerated):
                        self._open_map_file(regenerated)
                        return
                else:
                    self._refresh_worldwide_outputs()
                    worldwide = os.path.join(self.outputs_root, "worldwide_showcase.html")
                    self._open_map_file(worldwide)
                    return
            except Exception as exc:
                messagebox.showerror("Map generation failed", str(exc))
                return

        # Prefer the active dataset's detailed vector map, then fall back to
        # legacy output location and the no-tile worldwide vector map.
        candidates = [
            os.path.join(self.outputs_dir, "05_interactive_map.html"),
            os.path.join(self.outputs_root, "05_interactive_map.html"),
            os.path.join(self.outputs_root, "worldwide_showcase.html"),
        ]
        html_path = None
        for candidate in candidates:
            if not os.path.isfile(candidate):
                continue
            try:
                page = Path(candidate).read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            # Ignore stale Folium exports that still request OSM's community tiles.
            if "tile.openstreetmap.org" in page:
                continue
            html_path = candidate
            break
        if html_path:
            self._open_map_file(html_path)
            return

        messagebox.showerror(
            "Map not found",
            "No interactive map exists for this dataset yet. Run its pipeline first. "
            "If a map exists in another folder, select that dataset in the sidebar.",
        )

    # =========================================================================
    # TAB 3: RASTER & IMAGE PRESENTER
    # =========================================================================
    def setup_raster_tab(self):
        self.controls_frame = ctk.CTkFrame(self.tab_rasters)
        self.controls_frame.pack(fill="x", padx=10, pady=5)

        self.lbl_select = ctk.CTkLabel(
            self.controls_frame, text="Select Output Layer:"
        )
        self.lbl_select.pack(side="left", padx=10, pady=10)

        self.img_select = ctk.CTkOptionMenu(
            self.controls_frame,
            values=[
                "01_raw_measurement.png",
                "02_temporal_change.tif",
                "03_anomaly_mask.tif",
                "04_temporal_mean_trend.tif",
            ],
            command=self.load_selected_image,
        )
        self.img_select.pack(side="left", padx=10, pady=10)

        self.lbl_image_desc = ctk.CTkLabel(
            self.controls_frame,
            text="Select an item above to view image and explanation.",
            font=ctk.CTkFont(slant="italic"),
        )
        self.lbl_image_desc.pack(side="left", padx=20, pady=10)

        self.image_label = ctk.CTkLabel(
            self.tab_rasters, text="Select a raster output to view"
        )
        self.image_label.pack(fill="both", expand=True, padx=10, pady=10)

    def load_selected_image(self, filename):
        file_path = os.path.join(self.outputs_dir, filename)

        descriptions = {
            "01_raw_measurement.png": "📈 RAW MEASUREMENT: Graph of radar signal reflections across satellite passes.",
            "02_temporal_change.tif": "🖼️ TEMPORAL CHANGE RASTER: Shows exact grid locations where radar backscatter dropped or rose.",
            "03_anomaly_mask.tif": "🎭 ANOMALY MASK: Binary highlight showing only zones crossing critical disaster thresholds.",
            "04_temporal_mean_trend.tif": "📊 MEAN TREND RASTER: Background spatial average used to eliminate short-term cloud noise.",
        }

        self.lbl_image_desc.configure(
            text=descriptions.get(filename, "Viewing output artifact.")
        )

        if not os.path.exists(file_path):
            self.image_label.configure(
                text=f"File {filename} not yet generated in outputs folder.", image=None
            )
            return

        try:
            raw_img = Image.open(file_path)
            display_size = (780, 480)
            raw_img.thumbnail(display_size, Image.Resampling.LANCZOS)

            ctk_img = ctk.CTkImage(
                light_image=raw_img, dark_image=raw_img, size=raw_img.size
            )
            self.image_label.configure(image=ctk_img, text="")
        except Exception as e:
            self.image_label.configure(
                text=f"Error rendering image file: {str(e)}", image=None
            )

    # =========================================================================
    # TAB 4: SCIENTIFIC THEORY & DECODER HUB
    # =========================================================================
    def setup_theory_tab(self):
        scroll_theory = ctk.CTkScrollableFrame(self.tab_theory)
        scroll_theory.pack(fill="both", expand=True, padx=10, pady=10)

        title = ctk.CTkLabel(
            scroll_theory,
            text="📚 Complete Science & Physics Decoder",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title.pack(anchor="w", padx=10, pady=(10, 15))

        theory_guide = (
            "1. WHAT IS NISAR AND L-BAND RADAR?\n"
            "   • Unlike optical cameras (which see visible light and get blocked by clouds/night),\n"
            "     NISAR uses active microwave radio signals.\n"
            "   • L-Band radar penetrates cloud cover and forest canopies to measure actual ground\n"
            "     and tree structure 24 hours a day.\n\n"
            "2. WHAT IS BACKSCATTER (Sigma0 / dB)?\n"
            "   • Backscatter is the amount of radio energy that bounces off the ground back to the satellite.\n"
            "   • High Reflection (Positive dB): Rough ground, buildings, dense healthy tree trunks.\n"
            "   • Low Reflection / Signal Drop (Negative dB): Smooth standing water, flooded soil,\n"
            "     or ground cleared by landslides (radio pulses bounce away like a mirror).\n\n"
            "3. HOW TO READ THE OUTPUT NUMBERS IN SIMPLE TERMS:\n"
            "   • Decibel Drop (e.g., -4.54 dB):\n"
            "     A severe drop in signal reflection. Indicates standing floodwater or land collapse.\n"
            "   • Baseline Median (+0.385 dB):\n"
            "     The typical background change expected during normal seasonal shifts.\n"
            "   • Threshold Cutoffs (-1.99 dB to +1.43 dB):\n"
            "     Mathematical boundaries used to ignore noise and flag true physical disaster zones.\n"
            "   • Connected Anomaly Components (e.g., 1,013 zones):\n"
            "     Neighboring pixels showing extreme drops grouped together into individual physical sites.\n\n"
            "4. OUTPUT FILES DECODED:\n"
            "   • 01_raw_measurement.png     --> Signal graph over time.\n"
            "   • 02_temporal_change.tif      --> Spatial raster showing magnitude of ground changes.\n"
            "   • 03_anomaly_mask.tif        --> Binary black/white filter isolating disaster zones.\n"
            "   • 04_temporal_mean_trend.tif   --> Averaged baseline filtering out short-term noise.\n"
            "   • 05_interactive_map.html    --> Openable field map with pin locations and coordinates.\n"
            "   • 06_candidate_regions.csv   --> Spreadsheet ranking all impact sites by size and drop."
        )

        lbl_text = ctk.CTkLabel(
            scroll_theory,
            text=theory_guide,
            justify="left",
            font=ctk.CTkFont(size=13, family="Courier"),
        )
        lbl_text.pack(anchor="w", padx=10, pady=5)

    # =========================================================================
    # TAB 5: WORLDWIDE ASF CATALOG SEARCH AND DOWNLOAD
    # =========================================================================
    def setup_worldwide_tab(self):
        frame = ctk.CTkFrame(self.tab_world)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(4, weight=1)

        ctk.CTkLabel(frame, text="Worldwide NISAR Data Explorer", font=ctk.CTkFont(size=21, weight="bold")).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 2))
        ctk.CTkLabel(frame, text="Search ASF by country and date, download selected files, then analyze them in the existing tabs.", text_color="#b8c5d6").grid(row=1, column=0, sticky="w", padx=14, pady=(0, 10))

        controls = ctk.CTkFrame(frame)
        controls.grid(row=2, column=0, sticky="new", padx=8, pady=5)
        for col in range(9):
            controls.grid_columnconfigure(col, weight=1 if col == 0 else 0)
        self.country_var = tk.StringVar(value="Loading countries…")
        self.country_menu = ctk.CTkOptionMenu(controls, variable=self.country_var, values=["Loading countries…"], command=self._on_country_change, width=200)
        self.country_menu.grid(row=0, column=0, padx=7, pady=10, sticky="w")
        self.area_var = tk.StringVar(value="Entire country")
        self.area_menu = ctk.CTkOptionMenu(controls, variable=self.area_var, values=["Entire country"], command=self._on_area_change, width=155)
        self.area_menu.grid(row=0, column=1, padx=5, pady=10)
        self.start_var = tk.StringVar(value="2025-01-01")
        self.end_var = tk.StringVar(value=date.today().isoformat())
        ctk.CTkEntry(controls, textvariable=self.start_var, width=112, placeholder_text="Start YYYY-MM-DD").grid(row=0, column=2, padx=5, pady=10)
        ctk.CTkEntry(controls, textvariable=self.end_var, width=112, placeholder_text="End YYYY-MM-DD").grid(row=0, column=3, padx=5, pady=10)
        self.level_var = tk.StringVar(value="SME2")
        ctk.CTkOptionMenu(controls, variable=self.level_var, values=["SME2", "GCOV", "GSLC", "GUNW", "RSLC"], width=90).grid(row=0, column=4, padx=5, pady=10)
        self.limit_var = tk.StringVar(value="100")
        ctk.CTkOptionMenu(controls, variable=self.limit_var, values=["25", "50", "100", "250"], width=78).grid(row=0, column=5, padx=5, pady=10)
        self.search_btn = ctk.CTkButton(controls, text="Search ASF", command=self.search_asf)
        self.search_btn.grid(row=0, column=6, padx=5, pady=10)
        self.download_btn = ctk.CTkButton(controls, text="Download selected", command=self.download_asf_selected, state="disabled")
        self.download_btn.grid(row=0, column=7, padx=5, pady=10)
        self.worldmap_btn = ctk.CTkButton(controls, text="Open Worldwide Results Map", command=self.open_worldwide_map, fg_color="#3b4657")
        self.worldmap_btn.grid(row=0, column=8, padx=5, pady=10)
        self.global_search_btn = ctk.CTkButton(controls, text="Search Global ASF Catalog", command=lambda: self.search_asf(global_search=True), fg_color="#9a3030")
        self.global_search_btn.grid(row=1, column=0, columnspan=2, padx=7, pady=(0, 9), sticky="w")
        ctk.CTkLabel(controls, text="Search official ASF NISAR footprints worldwide, then open the map.", text_color="#b8c5d6").grid(row=1, column=2, columnspan=7, padx=5, pady=(0, 9), sticky="w")

        self.catalog_count = ctk.CTkLabel(frame, text="Choose a country and search the ASF catalog.", anchor="w")
        self.catalog_count.grid(row=3, column=0, sticky="ew", padx=12, pady=(5, 2))
        table_frame = ctk.CTkFrame(frame)
        table_frame.grid(row=4, column=0, sticky="nsew", padx=8, pady=4)
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)
        columns = ("acquired", "product", "track", "direction", "maturity")
        self.catalog_table = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="extended", height=12)
        for key, title, width in [("acquired", "Acquired", 150), ("product", "Product / granule", 600), ("track", "Track", 90), ("direction", "Pass", 90), ("maturity", "Maturity", 150)]:
            self.catalog_table.heading(key, text=title)
            self.catalog_table.column(key, width=width, anchor="w")
        self.catalog_table.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.catalog_table.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.catalog_table.configure(yscrollcommand=scroll.set)
        self.catalog_table.bind("<<TreeviewSelect>>", self._catalog_selection_changed)
        self.place_details = ctk.CTkLabel(frame, text="Place details will appear here. Choose a country or city area.", wraplength=1050, justify="left", anchor="w", text_color="#c7d4e4")
        self.place_details.grid(row=5, column=0, sticky="ew", padx=12, pady=(4, 2))
        map_note = "Map: free OpenFreeMap/MapLibre basemap, no key or billing; country boundaries, official ASF NISAR acquisition footprints, analyzed NISAR regions and sample city AOIs are clickable. Catalog footprints and analyzed candidate regions use red outlines/dots; analysis dots are larger."
        self.world_hint = ctk.CTkLabel(frame, text=f"Select a city AOI such as Delhi NCR for a focused search, or Entire country for a broad search. {map_note} Catalog searches are free; downloading products requires a free NASA Earthdata Login. NISAR acquisitions are periodic, not live earthquake readings.", wraplength=1050, justify="left", text_color="#b8c5d6")
        self.world_hint.grid(row=6, column=0, sticky="ew", padx=12, pady=(4, 10))
        self._load_country_bounds()

    def _load_country_bounds(self):
        def worker():
            try:
                boundary_file = Path(self.datasets_dir) / "world_countries.geojson"
                features = load_world_geojson(boundary_file).get("features", [])
                bounds = {}
                for feature in features:
                    props = feature.get("properties", {})
                    name = props.get("ADMIN") or props.get("name") or props.get("NAME")
                    points = []
                    def walk(value):
                        if isinstance(value, (list, tuple)):
                            if len(value) >= 2 and isinstance(value[0], (int, float)) and isinstance(value[1], (int, float)):
                                points.append((float(value[0]), float(value[1])))
                            else:
                                for child in value:
                                    walk(child)
                    walk((feature.get("geometry") or {}).get("coordinates", []))
                    if name and points:
                        xs, ys = zip(*points)
                        bounds[name] = (min(xs), min(ys), max(xs), max(ys))
                if not bounds:
                    raise ValueError("Country boundary file had no usable entries.")
                self.events.put(("countries", bounds))
            except Exception as exc:
                self.events.put(("error", f"Could not load country boundaries: {exc}"))
        threading.Thread(target=worker, daemon=True).start()

    def _process_events(self):
        while True:
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "countries":
                self.country_bounds = value
                names = sorted(value)
                self.country_menu.configure(values=names)
                self.country_var.set("India" if "India" in value else names[0])
                self._update_area_options()
                self._update_place_details()
                self.log_status(f"Worldwide country list loaded ({len(names)} entries).")
            elif kind == "results":
                self._show_asf_results(value)
            elif kind == "refresh_datasets":
                names = self.get_available_datasets()
                self.dataset_menu.configure(values=names)
                if value in names:
                    self.dataset_menu.set(value)
                    self.on_dataset_selected(value)
            elif kind == "log":
                self.log_status(value)
            elif kind == "error":
                self.log_status("ERROR: " + value)
                messagebox.showerror("NISAR Worldwide", value)
            elif kind == "busy":
                self.busy = value
                state = "disabled" if value else "normal"
                self.search_btn.configure(state=state)
                self.global_search_btn.configure(state=state)
                self.btn_run.configure(state=state)
                self.dataset_menu.configure(state=state)
                self.country_menu.configure(state=state)
                self.download_btn.configure(state="disabled" if value else ("normal" if self.catalog_table.selection() else "disabled"))
                if not value:
                    self._catalog_selection_changed()
            elif kind == "pipeline_done":
                self.populate_decoded_data()
                self.load_selected_image(self.img_select.get())
                self.log_status("Decoded findings and raster viewer refreshed for the active dataset.")
        self.after(150, self._process_events)

    def _on_country_change(self, selected):
        self.country_var.set(selected)
        self._update_area_options()
        self._update_place_details()

    def _on_area_change(self, selected):
        self.area_var.set(selected)
        self._update_place_details()

    def _update_place_details(self):
        country = self.country_var.get()
        area = self.area_var.get()
        if area in LOCATION_AOIS and LOCATION_AOIS[area][0] == country:
            _, west, south, east, north = LOCATION_AOIS[area]
            lat, lon = (south + north) / 2, (west + east) / 2
            self.place_details.configure(text=f"{area}, {country} · Approximate AOI center: {lat:.4f}°N, {lon:.4f}°E · Search bounds: {west:.3f}–{east:.3f}° longitude, {south:.3f}–{north:.3f}° latitude. Choose Search ASF to check acquisition availability for your selected dates.")
        elif country in self.country_bounds:
            west, south, east, north = self.country_bounds[country]
            self.place_details.configure(text=f"{country} · Approximate country bounds: {west:.3f}–{east:.3f}° longitude, {south:.3f}–{north:.3f}° latitude. Country search covers a broad box; inspect ASF scene footprints before downloading or analyzing.")

    def _update_area_options(self):
        country = self.country_var.get()
        cities = sorted(name for name, details in LOCATION_AOIS.items() if details[0] == country)
        values = ["Entire country"] + cities
        self.area_menu.configure(values=values)
        if self.area_var.get() not in values:
            self.area_var.set("Entire country")
        self._update_place_details()

    def _catalog_selection_changed(self, _event=None):
        if hasattr(self, "catalog_table"):
            state = "normal" if self.catalog_table.selection() and not self.busy else "disabled"
            self.download_btn.configure(state=state)

    @staticmethod
    def _product_props(product):
        return getattr(product, "properties", {}) or {}

    def _show_asf_results(self, products):
        self.catalog_results = products
        self.catalog_rows.clear()
        for item in self.catalog_table.get_children():
            self.catalog_table.delete(item)
        for i, product in enumerate(products):
            p = self._product_props(product)
            label = p.get("fileID") or p.get("granuleName") or p.get("sceneName") or p.get("productName") or str(i)
            row = self.catalog_table.insert("", "end", values=(p.get("startTime", p.get("sceneDate", "")), label, p.get("track", ""), p.get("flightDirection", ""), p.get("dataMaturity", p.get("maturity", "see ASF metadata"))))
            self.catalog_rows[row] = product
        self.catalog_count.configure(text=f"Found {len(products)} official ASF NISAR catalog result(s). Select rows to download, then open the worldwide map to see footprints.")

    def _open_map_file(self, path):
        """Serve local map HTML over localhost so browser map libraries can load."""
        path = Path(path).resolve()
        root = Path(self.outputs_root).resolve()
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError:
            webbrowser.open(path.as_uri())
            return
        if self._map_http_server is None:
            class QuietHandler(SimpleHTTPRequestHandler):
                def log_message(self, _format, *_args):
                    pass
            handler = partial(QuietHandler, directory=str(root))
            self._map_http_server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
            threading.Thread(target=self._map_http_server.serve_forever, daemon=True).start()
        port = self._map_http_server.server_address[1]
        webbrowser.open(f"http://localhost:{port}/{quote(relative, safe='/')}")

    def search_asf(self, global_search=False):
        country = self.country_var.get()
        if not global_search and country not in self.country_bounds:
            messagebox.showwarning("Country list loading", "Wait for the global country list to finish loading.")
            return
        try:
            date.fromisoformat(self.start_var.get().strip())
            date.fromisoformat(self.end_var.get().strip())
            limit = int(self.limit_var.get())
        except ValueError:
            messagebox.showerror("Invalid search", "Use YYYY-MM-DD dates and a numeric result limit.")
            return
        if self.start_var.get() > self.end_var.get():
            messagebox.showerror("Invalid search", "Start date must be on or before end date.")
            return
        selected_area = "Worldwide" if global_search else self.area_var.get()
        wkt = None
        if not global_search:
            if selected_area in LOCATION_AOIS and LOCATION_AOIS[selected_area][0] == country:
                _, west, south, east, north = LOCATION_AOIS[selected_area]
            else:
                selected_area = "Entire country"
                west, south, east, north = self.country_bounds[country]
            wkt = f"POLYGON(({west} {south},{east} {south},{east} {north},{west} {north},{west} {south}))"
        self.busy = True
        self.search_btn.configure(state="disabled")
        self.catalog_count.configure(text=f"Searching ASF {selected_area} for {self.level_var.get()} products…")
        self.log_status(f"Searching ASF: {selected_area} / {country}, {self.start_var.get()} through {self.end_var.get()}, {self.level_var.get()}")
        def worker():
            try:
                import asf_search as asf
                query = {"dataset": "NISAR", "processingLevel": self.level_var.get(),
                    "start": self.start_var.get(), "end": self.end_var.get(), "maxResults": limit}
                if wkt:
                    query["intersectsWith"] = wkt
                results = asf.search(**query)
                results.raise_if_incomplete()
                self.events.put(("results", list(results)))
                self.events.put(("log", f"ASF {selected_area} search returned {len(results)} official NISAR product(s)."))
            except Exception as exc:
                self.events.put(("error", f"ASF search failed: {exc}"))
            finally:
                self.events.put(("busy", False))
        threading.Thread(target=worker, daemon=True).start()

    def download_asf_selected(self):
        products = [self.catalog_rows[row] for row in self.catalog_table.selection() if row in self.catalog_rows]
        ids = []
        for product in products:
            p = self._product_props(product)
            product_id = p.get("fileID") or p.get("granuleName") or p.get("sceneName") or p.get("productName")
            if product_id:
                ids.append(product_id)
        if not ids:
            messagebox.showinfo("Select results", "Select one or more catalog results first.")
            return
        country = self.country_var.get()
        folder_name = "".join(ch if ch.isalnum() else "_" for ch in country).strip("_")
        target = Path(self.datasets_dir) / folder_name
        target.mkdir(parents=True, exist_ok=True)
        self.busy = True
        self.download_btn.configure(state="disabled")
        self.log_status(f"Downloading {len(ids)} product(s) to {target}")
        def worker():
            try:
                import asf_search as asf
                results = asf.search(dataset="NISAR", granule_list=ids)
                results.download(path=str(target))
                self.events.put(("log", "Download completed."))
                self.events.put(("refresh_datasets", folder_name))
            except Exception as exc:
                self.events.put(("error", f"Download failed. Configure NASA Earthdata Login for ASF. Details: {exc}"))
            finally:
                self.events.put(("busy", False))
        threading.Thread(target=worker, daemon=True).start()

    def on_dataset_selected(self, selected):
        if not selected or selected == "No Datasets Found":
            self.outputs_dir = self.outputs_root
            return
        slug = "".join(ch if ch.isalnum() else "_" for ch in selected).strip("_")
        self.outputs_dir = os.path.join(self.outputs_root, "countries", slug)

    # =========================================================================
    # UTILITY FUNCTIONS & PIPELINE EXECUTORS
    # =========================================================================
    def get_available_datasets(self):
        folders = [
            f
            for f in os.listdir(self.datasets_dir)
            if os.path.isdir(os.path.join(self.datasets_dir, f))
        ]
        return folders if folders else ["No Datasets Found"]

    def upload_dataset_folder(self):
        folder_selected = filedialog.askdirectory(
            title="Select Dataset Folder Containing .h5 Files"
        )
        if folder_selected:
            folder_name = os.path.basename(folder_selected)
            target_path = os.path.join(self.datasets_dir, folder_name)
            os.makedirs(target_path, exist_ok=True)

            h5_count = 0
            for root, _, files in os.walk(folder_selected):
                for file in files:
                    if file.lower().endswith((".h5", ".hdf5")):
                        source_path = os.path.join(root, file)
                        destination = os.path.join(target_path, file)
                        if os.path.abspath(source_path) != os.path.abspath(destination):
                            shutil.copy2(source_path, destination)
                        h5_count += 1

            if h5_count > 0:
                messagebox.showinfo(
                    "Upload Success",
                    f"Successfully uploaded {h5_count} .h5 telemetry files to:\n{target_path}",
                )
                self.dataset_menu.configure(values=self.get_available_datasets())
                self.dataset_menu.set(folder_name)
                self.log_status(
                    f"Uploaded dataset '{folder_name}' ({h5_count} .h5 files)."
                )
            else:
                messagebox.showwarning(
                    "No HDF5 Files", "Selected folder contains no .h5 radar files."
                )

    def run_pipeline(self):
        selected = self.dataset_menu.get()
        if selected == "No Datasets Found":
            messagebox.showerror(
                "No Dataset", "Please upload a folder containing .h5 files first."
            )
            return

        dataset_path = os.path.join(self.datasets_dir, selected)
        files = sorted(Path(dataset_path).rglob("*.h5")) + sorted(Path(dataset_path).rglob("*.hdf5"))
        if not files:
            messagebox.showerror("No HDF5 data", f"No .h5 files found in {dataset_path}")
            return
        if len(files) < 2 and not messagebox.askyesno("One observation", "The pipeline expects multiple dates. Run with one file anyway?"):
            return
        self.on_dataset_selected(selected)
        os.makedirs(self.outputs_dir, exist_ok=True)
        self.busy = True
        self.btn_run.configure(state="disabled")
        self.log_status(f"Starting pipeline for {selected} with {len(files)} HDF5 file(s)…")
        output_path = self.outputs_dir
        def worker():
            try:
                from config import CONFIG
                old_inputs, old_output = CONFIG["input_files"], CONFIG["output_root"]
                try:
                    CONFIG["input_files"] = [str(path.resolve()) for path in files]
                    CONFIG["output_root"] = output_path
                    from main import orchestrate_pipeline
                    orchestrate_pipeline()
                finally:
                    CONFIG["input_files"], CONFIG["output_root"] = old_inputs, old_output
                self._refresh_worldwide_outputs()
                self.events.put(("log", f"Pipeline completed for {selected}; output folder: {output_path}"))
                self.events.put(("pipeline_done", None))
            except Exception as exc:
                self.events.put(("error", f"Pipeline failed for {selected}: {exc}"))
            finally:
                self.events.put(("busy", False))
        threading.Thread(target=worker, daemon=True).start()

    def _refresh_worldwide_outputs(self):
        root = Path(self.outputs_root) / "countries"
        root.mkdir(parents=True, exist_ok=True)
        summary, regions, country_stats = [], [], {}
        for csv_path in sorted(root.glob("*/06_candidate_regions.csv")):
            country = csv_path.parent.name.replace("_", " ")
            with csv_path.open("r", encoding="utf-8-sig", newline="") as source:
                rows = list(csv.DictReader(source))
            summary.append({"country": country, "candidate_regions": len(rows), "results_csv": str(csv_path.relative_to(self.outputs_root))})
            country_stats[csv_path.parent.name] = {
                "candidate_regions": len(rows),
                "results_csv": str(csv_path.relative_to(self.outputs_root)),
            }
            for row in rows:
                try:
                    lat, lon = float(row["centroid_lat"]), float(row["centroid_lon"])
                    regions.append({"lat": lat, "lon": lon, "title": f"{country} — region {row.get('region_id', '')}",
                        "area": row.get("area_km2", ""), "change": row.get("mean_change_db", ""),
                        "direction": row.get("change_direction", ""), "optical": row.get("cross_validation_status", "not run")})
                except (KeyError, TypeError, ValueError):
                    continue
        with open(os.path.join(self.outputs_root, "country_run_index.csv"), "w", encoding="utf-8", newline="") as target:
            writer = csv.DictWriter(target, fieldnames=["country", "candidate_regions", "results_csv"])
            writer.writeheader()
            writer.writerows(summary)
        # Draw every country polygon, even when no NISAR result has been run there.
        # Country boundaries are geographic context; colors indicate which folders
        # have completed analysis and how many candidate regions they contain.
        geojson_path = Path(self.datasets_dir) / "world_countries.geojson"
        world_data = load_world_geojson(geojson_path)
        for feature in world_data.get("features", []):
            props = feature.setdefault("properties", {})
            name = props.get("ADMIN") or props.get("name") or props.get("NAME") or "Unknown"
            stats = country_stats.get(country_folder_slug(name))
            props["showcase_country"] = name
            props["analysis_status"] = "Completed" if stats is not None else "Not analyzed"
            props["candidate_regions"] = stats["candidate_regions"] if stats is not None else 0
            props["results_csv"] = stats["results_csv"] if stats is not None else ""

        places = []
        for place, (country, west, south, east, north) in LOCATION_AOIS.items():
            places.append({"place": place, "country": country, "lat": (south+north)/2,
                "lon": (west+east)/2, "bbox": f"{west:.3f}, {south:.3f}, {east:.3f}, {north:.3f}"})
        # The global layer uses ASFProduct GeoJSON, so plotted swaths come from
        # the official NISAR catalog rather than synthetic city/country points.
        catalog_features = []
        for product in self.catalog_results:
            try:
                feature = product.geojson()
                geometry = feature.get("geometry") or getattr(product, "geometry", None)
                if not geometry:
                    continue
                source_props = feature.get("properties") or self._product_props(product)
                props = {
                    "product": source_props.get("fileID") or source_props.get("granuleName") or source_props.get("sceneName") or source_props.get("productName") or "NISAR product",
                    "acquired": source_props.get("startTime") or source_props.get("sceneDate") or "",
                    "level": source_props.get("processingLevel") or self.level_var.get(),
                    "maturity": source_props.get("dataMaturity") or source_props.get("maturity") or "",
                }
                catalog_features.append({"type": "Feature", "geometry": geometry, "properties": props})
                coords = []
                def collect_pairs(value):
                    if isinstance(value, (list, tuple)):
                        if len(value) >= 2 and isinstance(value[0], (int, float)) and isinstance(value[1], (int, float)):
                            coords.append((float(value[0]), float(value[1])))
                        else:
                            for child in value:
                                collect_pairs(child)
                collect_pairs(geometry.get("coordinates", []))
                if coords:
                    center_props = dict(props)
                    center_props["catalog_center"] = True
                    catalog_features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [(min(x for x, _ in coords)+max(x for x, _ in coords))/2, (min(y for _, y in coords)+max(y for _, y in coords))/2]}, "properties": center_props})
            except Exception:
                continue
        catalog = {"type": "FeatureCollection", "features": catalog_features}
        output_path = os.path.join(self.outputs_root, "worldwide_showcase.html")
        write_keyless_map(output_path, world_data, places, regions, catalog, "NISAR Worldwide Country Showcase")

    def open_worldwide_map(self):
        path = os.path.join(self.outputs_root, "worldwide_showcase.html")
        try:
            # Build the world boundary map on demand, including before any country
            # has analysis results. Results are layered in when available.
            self._refresh_worldwide_outputs()
            self._open_map_file(path)
        except Exception as exc:
            messagebox.showerror(
                "Could not build worldwide map",
                "The world country boundary file could not be loaded. Connect to the internet "
                "for its first download, or check datasets\\world_countries.geojson.\n\n"
                f"Details: {exc}",
            )

    def log_status(self, text):
        self.status_box.insert(tk.END, text + "\n")
        self.status_box.see(tk.END)


if __name__ == "__main__":
    app = NISARDesktopApp()
    app.mainloop()
