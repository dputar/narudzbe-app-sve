import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
from zoneinfo import ZoneInfo
import time
import io
import numpy as np

st.set_page_config(page_title="Sustav narudžbi", layout="wide")

# Supabase konekcija
SUPABASE_URL = "https://vwekjvazuexwoglxqrtg.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ3ZWtqdmF6dWV4d29nbHhxcnRnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzIwMzMyOTcsImV4cCI6MjA4NzYwOTI5N30.59dWvEsXOE-IochSguKYSw_mDwFvEXHmHbCW7Gy_tto"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
TZ = ZoneInfo("Europe/Zagreb")

# ────────────────────────────────────────────────
# SESSION STATE
# ────────────────────────────────────────────────
if "narudzbe_proizvodi" not in st.session_state:
    st.session_state.narudzbe_proizvodi = []
if "stranica" not in st.session_state:
    st.session_state.stranica = "login"
if "proizvodi_search" not in st.session_state:
    st.session_state.proizvodi_search = ""
if "dobavljaci_search" not in st.session_state:
    st.session_state.dobavljaci_search = ""
if "narudzbe_search" not in st.session_state:
    st.session_state.narudzbe_search = ""
if "korisnici_search" not in st.session_state:
    st.session_state.korisnici_search = ""

# ────────────────────────────────────────────────
# CALLBACK ZA TRAŽILICE
# ────────────────────────────────────────────────
def on_proizvodi_search_change():
    st.session_state.proizvodi_search = st.session_state.proizvodi_search_input

def on_dobavljaci_search_change():
    st.session_state.dobavljaci_search = st.session_state.dobavljaci_search_input

def on_narudzbe_search_change():
    st.session_state.narudzbe_search = st.session_state.narudzbe_search_input

def on_korisnici_search_change():
    st.session_state.korisnici_search = st.session_state.korisnici_search_input

# ────────────────────────────────────────────────
# LOGIN
# ────────────────────────────────────────────────
if st.session_state.stranica == "login":
    st.title("Prijava u sustav narudžbi")
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Lozinka", type="password", key="login_password")
    if st.button("Prijavi se", key="login_prijavi"):
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            if res.user:
                st.session_state.user = res.user
                st.session_state.stranica = "početna"
                st.success("Uspješna prijava!")
                st.rerun()
            else:
                st.error("Prijava nije uspjela – provjeri email/lozinku.")
        except Exception as e:
            st.error(f"Greška pri prijavi: {str(e)}")
else:
    # ────────────────────────────────────────────────
    # SIDEBAR – dodan Korisnici
    # ────────────────────────────────────────────────
    with st.sidebar:
        st.title("Sustav narudžbi")
        if st.button("🏠 Početna", key="menu_pocetna"):
            st.session_state.stranica = "početna"
            st.rerun()
        if st.button("🛒 Narudžbe", key="menu_narudzbe"):
            st.session_state.stranica = "narudžbe"
            st.rerun()
        if st.button("🔍 Pretraga narudžbi", key="menu_pretraga"):
            st.session_state.stranica = "pretraga"
            st.rerun()
        with st.expander("📊 Izvještaji", expanded=False):
            st.info("Izvještaji dolaze kasnije...")
        with st.expander("⚙️ Administracija", expanded=False):
            if st.button("📦 Proizvodi", key="admin_proizvodi"):
                st.session_state.stranica = "admin_proizvodi"
                st.rerun()
            if st.button("🚚 Dobavljači", key="admin_dobavljaci"):
                st.session_state.stranica = "admin_dobavljaci"
                st.rerun()
            if st.button("👥 Korisnici", key="admin_korisnici"):
                st.session_state.stranica = "admin_korisnici"
                st.rerun()
            if st.button("📋 Šifarnici", key="admin_sifarnici"):
                st.session_state.stranica = "admin_sifarnici"
                st.rerun()
        if st.button("📁 Dokumenti", key="menu_dokumenti"):
            st.session_state.stranica = "dokumenti"
            st.rerun()
        if st.button("➡️ Odjava", key="menu_odjava"):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.session_state.stranica = "login"
            st.rerun()

    # ────────────────────────────────────────────────
    # POČETNA
    # ────────────────────────────────────────────────
    if st.session_state.stranica == "početna":
        st.title("Početna")
        st.markdown("### Dobrodošli u sustav narudžbi!")
        st.info("Ovdje će biti dashboard, statistike...")

    # ────────────────────────────────────────────────
    # NARUDŽBE – pregled (ostaje isto kao prije)
    # ────────────────────────────────────────────────
    elif st.session_state.stranica == "narudžbe":
        st.title("Pregled narudžbi")

        col1, col2 = st.columns([6, 4])
        with col1:
            st.subheader("Postojeće narudžbe")
        with col2:
            st.text_input(
                "Pretraži po svim stupcima",
                value=st.session_state.narudzbe_search,
                key="narudzbe_search_input",
                placeholder="upiši broj narudžbe, datum, klijenta, proizvod...",
                on_change=on_narudzbe_search_change
            )

        if st.button("🔄 Osvježi", key="pregled_osvjezi"):
            st.rerun()

        response = supabase.table("main_orders").select("*").order("datum", desc=True).execute()
        df = pd.DataFrame(response.data or [])

        if not df.empty:
            df = df.fillna("")
            df = df.loc[:, ~df.columns.duplicated()]
            if "reprezentacija" in df.columns:
                df = df.rename(columns={"reprezentacija": "Skladište"})

            for col in df.columns:
                if "datum" in col.lower() or "vrijeme" in col.lower():
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                elif df[col].dtype == "object":
                    df[col] = df[col].astype(str)
                elif df[col].dtype in ["float64", "int64"]:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            df_display = df.copy()
            if st.session_state.narudzbe_search:
                search_term = str(st.session_state.narudzbe_search).strip().lower()
                mask = df_display.astype(str).apply(lambda x: x.str.lower().str.contains(search_term), axis=1).any(axis=1)
                df_display = df_display[mask]

            if df_display.empty and st.session_state.narudzbe_search:
                st.info("Ništa nije pronađeno po traženom pojmu.")
            elif df_display.empty:
                st.info("Još nema narudžbi.")

            df_display["Obriši"] = False

            edited_df = st.data_editor(
                df_display,
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
                column_config={
                    "id": st.column_config.NumberColumn("ID", disabled=True),
                    "datum": st.column_config.DateColumn("Datum"),
                    "korisnik": st.column_config.TextColumn("Korisnik"),
                    "Skladište": st.column_config.TextColumn("Skladište"),
                    "odgovorna_osoba": st.column_config.TextColumn("Odgovorna osoba"),
                    "sifra_proizvoda": st.column_config.TextColumn("Šifra proizvoda"),
                    "naziv_proizvoda": st.column_config.TextColumn("Naziv proizvoda"),
                    "kolicina": st.column_config.NumberColumn("Količina"),
                    "dobavljac": st.column_config.TextColumn("Dobavljač"),
                    "oznaci_za_narudzbu": st.column_config.CheckboxColumn("Označi za narudžbu"),
                    "broj_narudzbe": st.column_config.TextColumn("Broj narudžbe"),
                    "oznaci_zaprimljeno": st.column_config.CheckboxColumn("Zaprimljeno"),
                    "napomena_dobavljac": st.column_config.TextColumn("Napomena dobavljaču"),
                    "napomena_za_nas": st.column_config.TextColumn("Napomena za nas"),
                    "unio_korisnik": st.column_config.TextColumn("Unio korisnik"),
                    "datum_vrijeme_narudzbe": st.column_config.DateColumn("Datum narudžbe"),
                    "datum_vrijeme_zaprimanja": st.column_config.DateColumn("Datum zaprimanja"),
                    "cijena": st.column_config.NumberColumn("Cijena", format="%.2f"),
                    "tip_klijenta": st.column_config.TextColumn("Tip klijenta"),
                    "Obriši": st.column_config.CheckboxColumn("Obriši"),
                }
            )

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                if st.button("💾 Spremi promjene", type="primary"):
                    obrisano = 0
                    spremljeno = 0
                    for row in edited_df.to_dict("records"):
                        row_id = row["id"]
                        if row["Obriši"]:
                            supabase.table("main_orders").delete().eq("id", row_id).execute()
                            obrisano += 1
                        else:
                            update_data = {}
                            for k, v in row.items():
                                if k in ["Obriši", "id"]:
                                    continue
                                if pd.isna(v) or (isinstance(v, float) and np.isnan(v)):
                                    update_data[k] = None
                                elif isinstance(v, pd.Timestamp):
                                    update_data[k] = v.isoformat()
                                elif isinstance(v, datetime):
                                    update_data[k] = v.isoformat()
                                elif isinstance(v, str) and v.strip() == "":
                                    update_data[k] = None
                                else:
                                    update_data[k] = v
                            if update_data:
                                supabase.table("main_orders").update(update_data).eq("id", row_id).execute()
                                spremljeno += 1
                    if obrisano > 0 or spremljeno > 0:
                        st.success(f"Obrisano {obrisano} narudžbi. Spremljeno {spremljeno} promjena.")
                    else:
                        st.info("Nema označenih za brisanje niti promjena za spremanje.")
                    st.rerun()

            with col2:
                if st.button("Izvezi pregled u Excel"):
                    output = io.BytesIO()
                    edited_df.drop(columns=["Obriši"]).to_excel(output, index=False, sheet_name="Narudžbe")
                    output.seek(0)
                    st.download_button(
                        label="Preuzmi .xlsx",
                        data=output,
                        file_name=f"narudzbe_pregled_{datetime.now(TZ).strftime('%Y-%m-%d_%H-%M')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

            with col3:
                st.button("➕ Nova narudžba", type="primary", on_click=lambda: st.session_state.update({"stranica": "nova"}))

            with col4:
                st.subheader("Upload narudžbi iz Excela")
                uploaded_file = st.file_uploader("Odaberi .xlsx datoteku", type=["xlsx"], key="upload_narudzbe")
                if uploaded_file:
                    try:
                        df_upload = pd.read_excel(uploaded_file)
                        st.write("Pregled podataka iz datoteke (prvih 10 redaka):")
                        st.dataframe(df_upload.head(10))

                        if st.button("Učitaj sve u bazu (batch po 500)", type="primary"):
                            batch_size = 500
                            broj_dodanih = 0
                            broj_duplikata = 0
                            broj_praznih = 0

                            response = supabase.table("main_orders").select("broj_narudzbe").execute()
                            postojeći_brojevi = {str(r["broj_narudzbe"]).strip() for r in response.data if r["broj_narudzbe"] and str(r["broj_narudzbe"]).strip()}

                            st.write(f"Broj postojećih narudžbi u bazi prije upload-a: {len(postojeći_brojevi)}")

                            for i in range(0, len(df_upload), batch_size):
                                batch = df_upload.iloc[i:i + batch_size]
                                st.write(f"Učitavam batch {i//batch_size + 1} (redovi {i+1} do {min(i+batch_size, len(df_upload))})...")

                                for idx, row in batch.iterrows():
                                    broj_candidates = ["broj_narudzbe", "Broj narudžbe", "Broj Narudžbe", "broj narudzbe"]
                                    broj_narudzbe = None
                                    for cand in broj_candidates:
                                        if cand in row and pd.notna(row[cand]):
                                            broj_narudzbe = str(row[cand]).strip()
                                            break

                                    if not broj_narudzbe:
                                        broj_praznih += 1
                                        broj_narudzbe = None
                                        st.write(f"Red {idx+1}: broj_narudzbe je prazan → postavljen na None")

                                    st.write(f"Red {idx+1}: broj_narudzbe = {broj_narudzbe if broj_narudzbe else 'None'}")

                                    if broj_narudzbe and broj_narudzbe in postojeći_brojevi:
                                        broj_duplikata += 1
                                        st.write(f"Red {idx+1}: PRESKOČEN DUPLIKAT '{broj_narudzbe}'")
                                        continue

                                    novi = {
                                        "datum": row.get("datum", None),
                                        "korisnik": str(row.get("korisnik", "")).strip() or "",
                                        "Skladište": str(row.get("Skladište", "")).strip() or "",
                                        "odgovorna_osoba": str(row.get("odgovorna_osoba", "")).strip() or "",
                                        "sifra_proizvoda": str(row.get("sifra_proizvoda", "")).strip() or "",
                                        "naziv_proizvoda": str(row.get("naziv_proizvoda", "")).strip() or "",
                                        "kolicina": float(row.get("kolicina", 0)) or 0,
                                        "dobavljac": str(row.get("dobavljac", "")).strip() or "",
                                        "oznaci_za_narudzbu": bool(row.get("oznaci_za_narudzbu", False)),
                                        "broj_narudzbe": broj_narudzbe,
                                        "oznaci_zaprimljeno": bool(row.get("oznaci_zaprimljeno", False)),
                                        "napomena_dobavljac": str(row.get("napomena_dobavljac", "")).strip() or "",
                                        "napomena_za_nas": str(row.get("napomena_za_nas", "")).strip() or "",
                                        "unio_korisnik": str(row.get("unio_korisnik", "")).strip() or "",
                                        "datum_vrijeme_narudzbe": row.get("datum_vrijeme_narudzbe", None),
                                        "datum_vrijeme_zaprimanja": row.get("datum_vrijeme_zaprimanja", None),
                                        "cijena": float(row.get("cijena", 0)) or 0,
                                        "tip_klijenta": str(row.get("tip_klijenta", "")).strip() or ""
                                    }

                                    for k in novi:
                                        if pd.isna(novi[k]):
                                            novi[k] = None

                                    try:
                                        supabase.table("main_orders").insert(novi).execute()
                                        broj_dodanih += 1
                                        if broj_narudzbe:
                                            postojeći_brojevi.add(broj_narudzbe)
                                        st.write(f"Red {idx+1}: USPJEŠNO DODAN → broj_narudzbe = {broj_narudzbe if broj_narudzbe else 'None'}")
                                    except Exception as insert_e:
                                        st.error(f"Red {idx+1}: GREŠKA pri insertu: {insert_e}")

                                time.sleep(0.3)

                            st.markdown("---")
                            st.write(f"Ukupno redaka u Excelu: {len(df_upload)}")
                            st.write(f"Dodano: {broj_dodanih}")
                            st.write(f"Preskočeno duplikata: {broj_duplikata}")
                            st.write(f"Preskočeno praznih broj_narudzbe: {broj_praznih}")
                            st.success(f"Učitano **{broj_dodanih}** novih narudžbi.")
                            # st.rerun()  ← zakomentirano za testiranje
                    except Exception as e:
                        st.error(f"Greška pri čitanju Excela: {e}")
                        st.error("Provjeri format datoteke – stupac 'broj_narudzbe' može biti prazan (dodaje se kao None).")

        else:
            st.info("Još nema narudžbi.")

    # ────────────────────────────────────────────────
    # ADMIN KORISNICI – NOVO
    # ────────────────────────────────────────────────
    elif st.session_state.stranica == "admin_korisnici":
        st.title("Administracija - Korisnici")

        # Dohvati sve korisnike
        response = supabase.table("users").select("*").execute()
        df_korisnici = pd.DataFrame(response.data or [])

        if not df_korisnici.empty:
            col1, col2 = st.columns([6, 4])
            with col1:
                st.subheader("Postojeći korisnici")
            with col2:
                st.text_input(
                    "Pretraži po svim stupcima",
                    value=st.session_state.korisnici_search,
                    key="korisnici_search_input",
                    placeholder="upiši email, ime, ulogu...",
                    on_change=on_korisnici_search_change
                )

            df_display = df_korisnici.copy()
            if st.session_state.korisnici_search:
                search_term = str(st.session_state.korisnici_search).strip().lower()
                mask = df_display.astype(str).apply(lambda x: x.str.lower().str.contains(search_term), axis=1).any(axis=1)
                df_display = df_display[mask]

            if df_display.empty and st.session_state.korisnici_search:
                st.info("Ništa nije pronađeno.")
            elif df_display.empty:
                st.info("Još nema korisnika u bazi.")

            df_display["Obriši"] = False

            edited_df = st.data_editor(
                df_display,
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
                column_config={
                    "id": st.column_config.TextColumn("ID", disabled=True),
                    "email": st.column_config.TextColumn("Email", required=True),
                    "ime": st.column_config.TextColumn("Ime"),
                    "prezime": st.column_config.TextColumn("Prezime"),
                    "uloga": st.column_config.SelectboxColumn("Uloga", options=["admin", "korisnik", "dobavljač"]),
                    "aktivan": st.column_config.CheckboxColumn("Aktivan"),
                    "telefon": st.column_config.TextColumn("Telefon"),
                    "napomena": st.column_config.TextColumn("Napomena"),
                    "created_at": st.column_config.TextColumn("Kreirano", disabled=True),
                    "Obriši": st.column_config.CheckboxColumn("Obriši"),
                }
            )

            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("💾 Spremi promjene", type="primary"):
                    for row in edited_df.to_dict("records"):
                        row_id = row["id"]
                        if row["Obriši"]:
                            supabase.table("users").delete().eq("id", row_id).execute()
                        else:
                            update_data = {k: v for k, v in row.items() if k not in ["Obriši", "id", "created_at"]}
                            supabase.table("users").update(update_data).eq("id", row_id).execute()
                    st.success("Promjene spremljene! Označeni korisnici obrisani.")
                    st.rerun()

            with col2:
                if st.button("Izvezi sve korisnike u Excel"):
                    output = io.BytesIO()
                    df_korisnici.to_excel(output, index=False, sheet_name="Korisnici")
                    output.seek(0)
                    st.download_button(
                        label="Preuzmi .xlsx",
                        data=output,
                        file_name=f"korisnici_{datetime.now(TZ).strftime('%Y-%m-%d_%H-%M')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

            with col3:
                st.button("🔄 Osvježi", on_click=st.rerun)

        else:
            st.info("Još nema korisnika u bazi.")

        # ────────────────────────────────────────────────
        # DODAJ NOVOG KORISNIKA
        # ────────────────────────────────────────────────
        st.subheader("Dodaj novog korisnika")
        with st.form("dodaj_korisnika"):
            email = st.text_input("Email *", key="dodaj_email_korisnika")
            ime = st.text_input("Ime", key="dodaj_ime_korisnika")
            prezime = st.text_input("Prezime", key="dodaj_prezime_korisnika")
            uloga = st.selectbox("Uloga", ["admin", "korisnik", "dobavljač"], key="dodaj_uloga_korisnika")
            telefon = st.text_input("Telefon", key="dodaj_telefon_korisnika")
            napomena = st.text_area("Napomena", key="dodaj_napomena_korisnika")
            aktivan = st.checkbox("Aktivan", value=True, key="dodaj_aktivan_korisnika")

            submitted = st.form_submit_button("Dodaj korisnika")
            if submitted:
                if email:
                    novi = {
                        "email": email,
                        "ime": ime or None,
                        "prezime": prezime or None,
                        "uloga": uloga,
                        "telefon": telefon or None,
                        "napomena": napomena or None,
                        "aktivan": aktivan
                    }
                    try:
                        supabase.table("users").insert(novi).execute()
                        st.success("Korisnik dodan!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Greška pri dodavanju: {e}")
                        if "unique constraint" in str(e):
                            st.error("Email već postoji u bazi!")
                else:
                    st.error("Email je obavezan!")

        # ────────────────────────────────────────────────
        # UPLOAD KORISNIKA IZ EXCELA
        # ────────────────────────────────────────────────
        st.subheader("Upload korisnika iz Excela")
        uploaded_file = st.file_uploader("Odaberi .xlsx datoteku", type=["xlsx"], key="upload_korisnici")
        if uploaded_file:
            try:
                df_upload = pd.read_excel(uploaded_file)
                st.write("Pregled podataka iz datoteke:")
                st.dataframe(df_upload.head(10))

                if st.button("Učitaj sve u bazu (batch po 500)", type="primary"):
                    batch_size = 500
                    broj_dodanih = 0
                    broj_duplikata = 0
                    broj_praznih = 0

                    # Dohvati postojeće emailove
                    response = supabase.table("users").select("email").execute()
                    postojeći_emailovi = {r["email"].strip().lower() for r in response.data if r["email"]}

                    for i in range(0, len(df_upload), batch_size):
                        batch = df_upload.iloc[i:i + batch_size]
                        st.write(f"Učitavam batch {i//batch_size + 1}...")

                        for _, row in batch.iterrows():
                            email = str(row.get("email", "")).strip()
                            if not email:
                                broj_praznih += 1
                                continue

                            if email.lower() in postojeći_emailovi:
                                broj_duplikata += 1
                                continue

                            novi = {
                                "email": email,
                                "ime": str(row.get("ime", "")).strip() or None,
                                "prezime": str(row.get("prezime", "")).strip() or None,
                                "uloga": str(row.get("uloga", "korisnik")).strip() or "korisnik",
                                "telefon": str(row.get("telefon", "")).strip() or None,
                                "napomena": str(row.get("napomena", "")).strip() or None,
                                "aktivan": bool(row.get("aktivan", True))
                            }

                            for k in novi:
                                if pd.isna(novi[k]):
                                    novi[k] = None

                            supabase.table("users").insert(novi).execute()
                            broj_dodanih += 1
                            postojeći_emailovi.add(email.lower())

                        time.sleep(0.3)

                    st.success(f"Učitano **{broj_dodanih}** novih korisnika. Preskočeno **{broj_duplikata}** duplikata po emailu. Praznih emailova: **{broj_praznih}**.")
                    st.rerun()
            except Exception as e:
                st.error(f"Greška pri čitanju/učitavanju Excela: {e}")
                st.error("Provjeri format datoteke i stupce (obavezno 'email').")

    # ────────────────────────────────────────────────
    # OSTALE SEKCIJE (ostaju identične)
    # ────────────────────────────────────────────────
    # ... (npr. admin_proizvodi, admin_dobavljaci, nova narudžba – ostaju kao što su bili)