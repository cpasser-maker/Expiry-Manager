import datetime
import json
import base64
import pandas as pd
import streamlit as st
from openai import OpenAI

# Seitenkonfiguration (minimalistisch)
st.set_page_config(
    page_title="Fristen-Manager", page_icon="⏱️", layout="centered"
)

# Schlichtes, klares Design ohne viel Text
st.title("⏱️ Fristen & Ablauf")

# Session State initialisieren
if "items" not in st.session_state or not isinstance(st.session_state.items, list):
  st.session_state.items = [
      {
          "name": "Sonnencreme SPF 50",
          "category": "Kosmetik",
          "target_date": datetime.date.today() + datetime.timedelta(days=120),
          "status": "🟢 Gültig",
          "note": "Nach Öffnen 12M",
      }
  ]

# API Key im Hintergrund holen (Streamlit Secrets oder Sidebar-Fallback)
openai_api_key = ""
try:
  openai_api_key = st.secrets.get("OPENAI_API_KEY", "")
except Exception:
  pass

# Hauptnavigation über zwei klare Tabs
tab_list, tab_add = st.tabs(["📋 Übersicht", "➕ Neu hinzufügen"])

# --- TAB 1: ÜBERSICHT ---
with tab_list:
  safe_items = st.session_state.get("items", [])
  
  if not safe_items:
    st.info("Noch keine Einträge vorhanden. Füge welche im Tab 'Neu hinzufügen' hinzu.")
  else:
    today = datetime.date.today()
    display_data = []

    for idx, item in enumerate(safe_items):
      if not isinstance(item, dict):
        continue
      
      t_date = item.get("target_date", today)
      delta_days = (t_date - today).days

      # Status-Ampel
      if delta_days < 0:
        status = "🔴 Abgelaufen"
      elif delta_days <= 30:
        status = "🟡 Bald fällig"
      else:
        status = "🟢 Gültig"

      display_data.append({
          "id": idx,
          "Produkt": item.get("name", ""),
          "Kategorie": item.get("category", "Sonstige"),
          "Fällig am": t_date,
          "Status": status,
          "Notiz": item.get("note", "")
      })

    df = pd.DataFrame(display_data)
    
    # Tabelle anzeigen (nur relevante Spalten)
    st.dataframe(
        df[["Produkt", "Kategorie", "Fällig am", "Status", "Notiz"]],
        use_container_width=True,
        hide_index=True
    )

    # Schlichtes Löschen direkt unter der Tabelle
    st.markdown("### 🗑️ Eintrag entfernen")
    col_del1, col_del2 = st.columns([3, 1])
    with col_del1:
      item_to_delete = st.selectbox(
          "Wähle ein Produkt zum Löschen:",
          options=df["id"],
          format_func=lambda x: df[df["id"] == x]["Produkt"].values[0],
          label_visibility="collapsed"
      )
    with col_del2:
      if st.button("Löschen", use_container_width=True):
        st.session_state.items.pop(item_to_delete)
        st.rerun()

# --- TAB 2: NEU HINZUFÜGEN ---
with tab_add:
  st.markdown("### Wähle, wie du das Produkt erfassen möchtest:")
  
  mode = st.radio("Erfassung", ["📸 Per Foto (KI)", "✍️ Manuell eingeben"], horizontal=True, label_visibility="collapsed")
  
  st.markdown("---")

  if mode == "📸 Per Foto (KI)":
    if not openai_api_key:
      openai_api_key = st.text_input("OpenAI API-Key eingeben:", type="password")
    
    uploaded_file = st.file_uploader("Foto vom Produkt/Etikett machen", type=["jpg", "jpeg", "png"])

    if uploaded_file and st.button("🤖 Automatisch auslesen", type="primary", use_container_width=True):
      if not openai_api_key:
        st.error("Bitte gib deinen API-Key ein.")
      else:
        with st.spinner("KI liest das Etikett..."):
          try:
            client = OpenAI(api_key=openai_api_key)
            base64_image = base64.b64encode(uploaded_file.getvalue()).decode("utf-8")

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Du extrahierst Produktdaten. Finde den Namen, die Kategorie ('Kosmetik', 'Lebensmittel', 'Haushalt', 'Sonstige'), "
                            "die Haltbarkeit nach dem Öffnen in Monaten (Standard z.B. 12) oder ein festes Ablaufdatum. "
                            "Berechne das genaue Zieldatum ausgehend von heute. "
                            "Antworte AUSSCHLIESSLICH im JSON-Format mit den Schlüsseln: 'name', 'category', 'target_date' (Format YYYY-MM-DD), 'note'."
                        ),
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Extrahiere die Daten als JSON."},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                        ],
                    },
                ],
                max_tokens=200,
            )

            res_text = response.choices[0].message.content
            if "```json" in res_text:
              res_text = res_text.split("```json")[1].split("```")[0].strip()
            elif "```" in res_text:
              res_text = res_text.split("```")[1].split("```")[0].strip()

            data = json.loads(res_text)
            parsed_date = datetime.date.fromisoformat(data.get("target_date", str(datetime.date.today() + datetime.timedelta(days=180))))

            st.session_state.items.append({
                "name": data.get("name", "Unbekanntes Produkt"),
                "category": data.get("category", "Sonstige"),
                "target_date": parsed_date,
                "note": data.get("note", "Per Foto erfasst")
            })
            st.success(f"Erfolgreich hinzugefügt: {data.get('name')}")
            st.rerun()

          except Exception as e:
            st.error(f"Fehler bei der Erkennung: {e}")

  else:
    # Manueller Modus (extrem reduziert)
    with st.form("manual_form"):
      name = st.text_input("Produktname")
      category = st.selectbox("Kategorie", ["Kosmetik", "Lebensmittel", "Haushalt", "Sonstige"])
      
      # Entweder Öffnungs-Monate oder festes Datum
      typ_wahl = st.radio("Art der Frist", ["Nach Öffnen (Monate)", "Fester Ablauf"])
      
      if typ_wahl == "Nach Öffnen (Monate)":
        monate = st.number_input("Haltbarkeit nach Öffnen (in Monaten)", min_value=1, max_value=120, value=12)
        target_date = datetime.date.today() + datetime.timedelta(days=int(monate * 30.5))
        note = f"Geöffnet vor kurzem ({monate}M haltbar)"
      else:
        target_date = st.date_input("Ablaufdatum", value=datetime.date.today() + datetime.timedelta(days=30))
        note = "Fester Ablauf"

      submitted = st.form_submit_button("Speichern", type="primary", use_container_width=True)

      if submitted and name:
        st.session_state.items.append({
            "name": name,
            "category": category,
            "target_date": target_date,
            "note": note
        })
        st.success(f"'{name}' gespeichert!")
        st.rerun()
