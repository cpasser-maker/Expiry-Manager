import datetime
import pandas as pd
import streamlit as st

# Seitenkonfiguration
st.set_page_config(
    page_title="Ablauf- & Fristen-Manager", page_icon="⏳", layout="wide"
)

# Titel und Einleitung
st.title("⏳ Fristen- & Ablauf-Manager")
st.markdown(
    "Behalte den Überblick über geöffnete Kosmetik, Lebensmittel und"
    " wiederkehrende Haushaltsaufgaben."
)

# Initialisierung des Session-Speichers mit Absicherung
if "items" not in st.session_state or not isinstance(st.session_state.items, list):
  st.session_state.items = [
      {
          "name": "Sonnencreme SPF 50",
          "category": "Kosmetik",
          "typ": "Nach Öffnen (Monate)",
          "start_date": datetime.date(2025, 6, 1),
          "duration": 12,
          "note": "Letzten Sommer geöffnet",
      },
      {
          "name": "Wasserfilter Kaffeemaschine",
          "category": "Haushalt",
          "typ": "Wiederkehrend (Monate)",
          "start_date": datetime.date(2026, 1, 15),
          "duration": 2,
          "note": "Regelmäßig tauschen",
      },
  ]

# --- SEITENLEISTE: NEUEN EINTRAG HINZUFÜGEN ---
st.sidebar.header("➕ Neu hinzufügen")

with st.sidebar.form("add_form"):
  name = st.text_input("Name / Produkt")
  category = st.selectbox(
      "Kategorie", ["Kosmetik", "Lebensmittel", "Haushalt", "Sonstige"]
  )
  typ = st.selectbox(
      "Art des Limits",
      ["Nach Öffnen (Monate)", "Wiederkehrend (Monate)", "Ablaufdatum fix"],
  )

  if typ == "Ablaufdatum fix":
    start_date = st.date_input(
        "Ablaufdatum", value=datetime.date.today() + datetime.timedelta(days=30)
    )
    duration = 0
  else:
    start_date = st.date_input(
        "Startdatum (Öffnungsdatum / Letzte Erledigung)"
    )
    duration = st.number_input(
        "Gültigkeit bzw. Intervall (in Monaten)", min_value=1, max_value=120, value=6
    )

  note = st.text_input("Notiz (optional)")
  submitted = st.form_submit_button("Hinzufügen")

  if submitted and name:
    st.session_state.items.append({
        "name": name,
        "category": category,
        "typ": typ,
        "start_date": start_date,
        "duration": duration,
        "note": note,
    })
    st.sidebar.success(f"'{name}' erfolgreich hinzugefügt!")
    st.rerun()

# --- HAUPTBEREICH: FILTER & ÜBERSICHT ---
col1, col2 = st.columns([2, 1])
with col1:
  search_query = st.text_input(
      "🔍 Schnellsuche (Name oder Notiz)", ""
  ).lower()

with col2:
  # Kategorien sicher ermitteln
  safe_items = st.session_state.get("items", [])
  categories_set = set()
  if isinstance(safe_items, list):
    for item in safe_items:
      if isinstance(item, dict):
        categories_set.add(item.get("category", "Sonstige"))
  categories = ["Alle"] + sorted(list(categories_set))
  selected_cat = st.selectbox("Kategorie filtern", categories)

# Berechnungen für die Tabelle durchführen
processed_data = []
today = datetime.date.today()

safe_items = st.session_state.get("items", [])
if isinstance(safe_items, list):
  for idx, item in enumerate(safe_items):
    if not isinstance(item, dict):
      continue
    
    item_type = item.get("typ", "Ablaufdatum fix")
    item_start = item.get("start_date", today)
    item_dur = item.get("duration", 0)
    
    if item_type == "Ablaufdatum fix":
      target_date = item_start
    else:
      target_date = item_start + datetime.timedelta(
          days=int(item_dur * 30.5)
      )

    delta_days = (target_date - today).days

    if delta_days < 0:
      status = "🔴 Abgelaufen"
    elif delta_days <= 30:
      status = "🟡 Bald fällig"
    else:
      status = "🟢 Gültig"

    item_name = item.get("name", "")
    item_note = item.get("note", "")
    item_cat = item.get("category", "Sonstige")

    if search_query and search_query not in item_name.lower() and search_query not in item_note.lower():
      continue
    if selected_cat != "Alle" and item_cat != selected_cat:
      continue

    processed_data.append({
        "id": idx,
        "Name": item_name,
        "Kategorie": item_cat,
        "Typ": item_type,
        "Datum (Start/Fix)": item_start,
        "Fällig / Ablauf": target_date,
        "Verbleibende Tage": delta_days,
        "Status": status,
        "Notiz": item_note,
    })

if processed_data:
  df = pd.DataFrame(processed_data)
  display_df = df.drop(columns=["id"])
  st.dataframe(display_df, use_container_width=True, hide_index=True)

  st.markdown("---")
  st.subheader("🗑️ Einträge verwalten")
  item_to_delete = st.selectbox(
      "Eintrag zum Löschen auswählen",
      options=df["id"],
      format_func=lambda x: f"{df[df['id'] == x]['Name'].values[0]} ({df[df['id'] == x]['Status'].values[0]})",
  )
  if st.button("Ausählten Eintrag löschen"):
    st.session_state.items.pop(item_to_delete)
    st.success("Eintrag gelöscht!")
    st.rerun()
else:
  st.info("Keine Einträge gefunden, die den Filtern entsprechen.")
