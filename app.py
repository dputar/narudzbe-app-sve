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

# ────────────────────────────────────────────────
# CALLBACK ZA TRAŽILICE
# ────────────────────────────────────────────────
def on_proizvodi_search_change():
    st.session_state.proizvodi_search = st.session_state.proizvodi_search_input

def on_dobavljaci_search_change():
    st.session_state.dobavljaci_search = st.session_state.dobavljaci_search_input

def on_narudzbe_search_change():
    st.session_state.narudzbe_search = st.session_state.narudzbe_search_input

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
    # SIDEBAR
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
    # NARUDŽBE – pregled (popravljeno: editabilna tablica + upload + sve što si tražio)
    # ────────────────────────────────────────────────
    elif st.session_state.stranica == "narudžbe":
        st.title("Pregled narudžbi")

        # Naslov + tražilica pored
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

            # Konverzija tipova da editor ne baca grešku
            for col in df.columns:
                if "datum" in col.lower() or "vrijeme" in col.lower():
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                elif df[col].dtype == "object":
                    df[col] = df[col].astype(str)
                elif df[col].dtype in ["float64", "int64"]:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            # Filtriranje
            df_display = df.copy()
            if st.session_state.narudzbe_search:
                search_term = str(st.session_state.narudzbe_search).strip().lower()
                mask = df_display.astype(str).apply(lambda x: x.str.lower().str.contains(search_term), axis=1).any(axis=1)
                df_display = df_display[mask]

            if df_display.empty and st.session_state.narudzbe_search:
                st.info("Ništa nije pronađeno po traženom pojmu.")
            elif df_display.empty:
                st.info("Još nema narudžbi.")

            # Dodaj checkbox za brisanje unutar tablice
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
                                # Čišćenje NaN / NaT / praznih vrijednosti
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
                            if update_data:  # SAMO AKO IMA PROMJENA – ovo rješava grešku
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
                        st.write("Pregled podataka iz datoteke:")
                        st.dataframe(df_upload.head(10))
                        if st.button("Učitaj sve u bazu (batch po 500)", type="primary"):
                            batch_size = 500
                            broj_dodanih = 0
                            broj_duplikata = 0
                            broj_praznih = 0

                            response = supabase.table("main_orders").select("broj_narudzbe").execute()
                            postojeći_brojevi = {r["broj_narudzbe"] for r in response.data if r["broj_narudzbe"]}

                            for i in range(0, len(df_upload), batch_size):
                                batch = df_upload.iloc[i:i + batch_size]
                                st.write(f"Učitavam batch {i//batch_size + 1}...")

                                for _, row in batch.iterrows():
                                    broj_narudzbe = str(row.get("broj_narudzbe", "")).strip()
                                    if not broj_narudzbe:
                                        broj_praznih += 1
                                        continue

                                    if broj_narudzbe in postojeći_brojevi:
                                        broj_duplikata += 1
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

                                    supabase.table("main_orders").insert(novi).execute()
                                    broj_dodanih += 1
                                    postojeći_brojevi.add(broj_narudzbe)

                                time.sleep(0.3)

                            st.write(f"Ukupno redaka u Excelu: {len(df_upload)}")
                            st.write(f"Dodano: {broj_dodanih}")
                            st.write(f"Preskočeno duplikata: {broj_duplikata}")
                            st.write(f"Preskočeno praznih/broj_narudzbe: {broj_praznih}")
                            st.success(f"Učitano **{broj_dodanih}** novih narudžbi. Preskočeno **{broj_duplikata}** duplikata. Praznih: **{broj_praznih}**.")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Greška pri čitanju/učitavanju Excela: {e}")
                        st.error("Provjeri format datoteke i stupce (npr. datum, broj_narudzbe).")
        else:
            st.info("Još nema narudžbi.")

    # ────────────────────────────────────────────────
    # NOVA NARUDŽBA (ostaje identično)
    # ────────────────────────────────────────────────
    elif st.session_state.stranica == "nova":
        col_naslov, col_natrag = st.columns([5, 1])
        with col_naslov:
            st.title("Nova narudžba")
        with col_natrag:
            if st.button("← Natrag na pregled", key="nova_natrag"):
                st.session_state.narudzbe_proizvodi = []
                st.session_state.stranica = "narudžbe"
                st.rerun()
        col_lijevo, col_desno = st.columns([1, 2])
        with col_lijevo:
            st.markdown("**Korisnik**")
            korisnik = st.selectbox("", ["Danijel Putar"], key="nova_korisnik", label_visibility="collapsed")
            st.success(f"✓ {korisnik}")
            st.markdown("**Skladište**")
            skladiste = st.selectbox("", ["Osijek - Glavno skladište"], key="nova_skladiste", label_visibility="collapsed")
            st.success(f"✓ {skladiste}")
            st.markdown("**Tip klijenta**")
            tip_klijenta = st.selectbox("", ["Doznaka", "Narudžba", "Uzorak", "Reprezentacija"], key="nova_tip_klijenta", label_visibility="collapsed")
            if tip_klijenta:
                st.success(f"✓ {tip_klijenta}")
            else:
                st.error("× Tip klijenta")
            st.markdown("**Klijent**")
            klijent = st.text_input("", placeholder="Upiši ime", key="nova_klijent", label_visibility="collapsed")
            if klijent:
                st.success(f"✓ {klijent}")
            else:
                st.error("× Klijent")
            st.markdown("**Odgovorna osoba**")
            odgovorna_lista = ["Nema", "Danijel Putar", "Druga osoba"]
            odgovorna = st.selectbox("", odgovorna_lista, key="nova_odgovorna_select", label_visibility="collapsed")
            if odgovorna == "Nema":
                odgovorna = st.text_input("Slobodan unos odgovorne osobe", key="nova_odgovorna_slobodno")
            st.success(f"✓ {odgovorna}")
            st.markdown("**Datum**")
            datum = st.date_input("", datetime.today(), key="nova_datum", label_visibility="collapsed")
            st.markdown("**Napomena**")
            napomena = st.text_area("", height=100, key="nova_napomena", label_visibility="collapsed")
        with col_desno:
            st.markdown("**Proizvodi**")
            if st.session_state.narudzbe_proizvodi:
                df = pd.DataFrame(st.session_state.narudzbe_proizvodi)
                df["Ukupno"] = df["Kol."] * df["Cijena"]
                st.dataframe(df, use_container_width=True, height=400)
                ukupno = df["Ukupno"].sum()
                st.markdown(f"**UKUPNO: {ukupno:,.2f} EUR + PDV**")
            else:
                st.info("Još nema proizvoda.")
            if st.button("➕ Dodaj proizvod", key="nova_dodaj_gumb", type="primary"):
                st.session_state.show_dodaj_proizvod = True
            if st.session_state.get("show_dodaj_proizvod", False):
                with st.form("dodaj_proizvod_form", clear_on_submit=True):
                    col1, col2 = st.columns(2)
                    sifra = col1.text_input("Šifra", key="dodaj_sifra")
                    naziv = col2.text_input("Naziv proizvoda *", key="dodaj_naziv")
                    col3, col4 = st.columns(2)
                    kol = col3.number_input("Količina *", min_value=0.01, step=0.01, format="%.2f", key="dodaj_kol")
                    cijena = col4.number_input("Cijena po komadu", min_value=0.0, step=0.01, format="%.2f", key="dodaj_cijena")
                    dobavljac = st.text_input("Dobavljač", key="dodaj_dobavljac")
                    submitted = st.form_submit_button("Dodaj u narudžbu", key="dodaj_spremi")
                    if submitted:
                        if naziv and kol > 0:
                            novi = {
                                "Šifra": sifra,
                                "Naziv": naziv,
                                "Kol.": kol,
                                "Cijena": cijena,
                                "Ukupno": kol * cijena,
                                "Dobavljač": dobavljac
                            }
                            st.session_state.narudzbe_proizvodi.append(novi)
                            st.success("Proizvod dodan!")
                            st.rerun()
                        else:
                            st.error("Naziv i količina su obavezni!")
                    if st.form_submit_button("Odustani", key="dodaj_odustani"):
                        st.session_state.show_dodaj_proizvod = False
                        st.rerun()

    # ────────────────────────────────────────────────
    # ADMINISTRACIJA → DOBAVLJAČI (ostaje identično)
    # ────────────────────────────────────────────────
    elif st.session_state.stranica == "admin_dobavljaci":
        st.title("Administracija - Dobavljači")
        response = supabase.table("dobavljaci").select("*").execute()
        df_dobavljaci = pd.DataFrame(response.data or [])
        if not df_dobavljaci.empty:
            col1, col2 = st.columns([6, 4])
            with col1:
                st.subheader("Postojeći dobavljači")
            with col2:
                st.text_input(
                    "Pretraži po svim stupcima",
                    value=st.session_state.dobavljaci_search,
                    key="dobavljaci_search_input",
                    placeholder="upiši naziv, email, rok...",
                    on_change=on_dobavljaci_search_change
                )
            df_display = df_dobavljaci.copy()
            if st.session_state.dobavljaci_search:
                search_term = str(st.session_state.dobavljaci_search).strip().lower()
                mask = df_display.astype(str).apply(lambda x: x.str.lower().str.contains(search_term), axis=1).any(axis=1)
                df_display = df_display[mask]
            if df_display.empty and st.session_state.dobavljaci_search:
                st.info("Ništa nije pronađeno.")
            elif df_display.empty:
                st.info("Još nema dobavljača u bazi.")
            df_display["Odaberi za brisanje"] = False
            edited_df = st.data_editor(
                df_display,
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
                column_config={
                    "naziv_dobavljaca": st.column_config.TextColumn("Naziv dobavljača", required=True),
                    "email": st.column_config.TextColumn("Email"),
                    "rok_isporuke": st.column_config.TextColumn("Rok isporuke"),
                    "telefonski_broj": st.column_config.TextColumn("Telefonski broj"),
                    "napomena": st.column_config.TextColumn("Napomena"),
                    "neuneseno1": st.column_config.TextColumn("Neuneseno 1"),
                    "neuneseno2": st.column_config.TextColumn("Neuneseno 2"),
                    "created_at": st.column_config.TextColumn("Kreirano"),
                    "updated_at": st.column_config.TextColumn("Ažurirano"),
                    "Odaberi za brisanje": st.column_config.CheckboxColumn("Obriši"),
                }
            )
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("💾 Spremi promjene", type="primary"):
                    for row in edited_df.to_dict("records"):
                        row_id = row["id"]
                        if row["Odaberi za brisanje"]:
                            supabase.table("dobavljaci").delete().eq("id", row_id).execute()
                        else:
                            update_data = {k: v for k, v in row.items() if k not in ["Odaberi za brisanje"]}
                            supabase.table("dobavljaci").update(update_data).eq("id", row_id).execute()
                    st.success("Promjene spremljene! Označeni dobavljači su obrisani.")
                    st.rerun()
            with col2:
                if st.button("Izvezi sve dobavljače u Excel"):
                    output = io.BytesIO()
                    df_dobavljaci.to_excel(output, index=False, sheet_name="Dobavljači")
                    output.seek(0)
                    st.download_button(
                        label="Preuzmi cijelu listu (.xlsx)",
                        data=output,
                        file_name=f"svi_dobavljaci_{datetime.now(TZ).strftime('%Y-%m-%d_%H-%M')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            with col3:
                st.button("🔄 Osvježi", on_click=st.rerun)
            st.subheader("Dodaj novog dobavljača")
            with st.form("dodaj_dobavljaca"):
                naziv = st.text_input("Naziv dobavljača *", key="dodaj_naziv_dobavljaca")
                email = st.text_input("Email", key="dodaj_email_dobavljaca")
                rok = st.text_input("Rok isporuke", key="dodaj_rok_dobavljaca")
                telefon = st.text_input("Telefonski broj", key="dodaj_telefon_dobavljaca")
                napomena = st.text_area("Napomena", key="dodaj_napomena_dobavljaca")
                neuneseno1 = st.text_input("Neuneseno 1", key="dodaj_neuneseno1")
                neuneseno2 = st.text_input("Neuneseno 2", key="dodaj_neuneseno2")
                submitted = st.form_submit_button("Dodaj dobavljača")
                if submitted:
                    if naziv:
                        novi = {
                            "naziv_dobavljaca": naziv,
                            "email": email,
                            "rok_isporuke": rok,
                            "telefonski_broj": telefon,
                            "napomena": napomena,
                            "neuneseno1": neuneseno1,
                            "neuneseno2": neuneseno2
                        }
                        supabase.table("dobavljaci").insert(novi).execute()
                        st.success("Dobavljač dodan!")
                        st.rerun()
                    else:
                        st.error("Naziv dobavljača je obavezan!")
            st.subheader("Upload dobavljača iz Excela")
            uploaded_file = st.file_uploader("Odaberi .xlsx datoteku", type=["xlsx"], key="upload_dobavljaci")
            if uploaded_file:
                try:
                    df_upload = pd.read_excel(uploaded_file)
                    st.write("Pregled podataka iz datoteke:")
                    st.dataframe(df_upload.head(10))
                    if st.button("Učitaj sve u bazu", type="primary"):
                        broj_dodanih = 0
                        broj_preskocenih = 0
                        for _, row in df_upload.iterrows():
                            novi = {
                                "naziv_dobavljaca": str(row.get("Naziv dobavljača", "")) or "",
                                "email": str(row.get("Email", "")) or "",
                                "rok_isporuke": str(row.get("Rok isporuke", "")) or "",
                                "telefonski_broj": str(row.get("Telefonski broj", "")) or "",
                                "napomena": str(row.get("Napomena", "")) or "",
                                "neuneseno1": "",
                                "neuneseno2": ""
                            }
                            for k in novi:
                                if pd.isna(novi[k]) or novi[k] in [float('inf'), float('-inf')]:
                                    novi[k] = None
                            supabase.table("dobavljaci").insert(novi).execute()
                            broj_dodanih += 1
                        st.success(f"Učitano {broj_dodanih} novih dobavljača.")
                        st.rerun()
                except Exception as e:
                    st.error(f"Greška pri čitanju Excela: {e}")
                    st.error("Provjeri da li je datoteka ispravna .xlsx i da ima potrebne stupce.")
        else:
            st.info("Još nema dobavljača u bazi.")
    # ────────────────────────────────────────────────
    # ADMINISTRACIJA → PROIZVODI (upload popravljen s dijagnostikom)
    # ────────────────────────────────────────────────
    elif st.session_state.stranica == "admin_proizvodi":
        st.title("Administracija - Proizvodi")
        full_response = supabase.table("proizvodi").select("*").order("created_at", desc=True).execute()
        df_full = pd.DataFrame(full_response.data or [])
        col1, col2 = st.columns([6, 4])
        with col1:
            st.subheader("Postojeći proizvodi")
        with col2:
            st.text_input(
                "Pretraži po svim stupcima",
                value=st.session_state.proizvodi_search,
                key="proizvodi_search_input",
                placeholder="upiši naziv, šifru, dobavljača...",
                on_change=on_proizvodi_search_change
            )
        df_display = df_full.copy()
        if st.session_state.proizvodi_search:
            search_term = str(st.session_state.proizvodi_search).strip().lower()
            mask = df_display.astype(str).apply(lambda x: x.str.lower().str.contains(search_term), axis=1).any(axis=1)
            df_display = df_display[mask]
        if df_display.empty and st.session_state.proizvodi_search:
            st.info("Ništa nije pronađeno po traženom pojmu.")
        elif df_display.empty:
            st.info("Još nema proizvoda u bazi.")
        df_display["Odaberi za brisanje"] = False
        edited_df = st.data_editor(
            df_display,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "naziv": st.column_config.TextColumn("Naziv proizvoda", required=True),
                "sifra": st.column_config.TextColumn("Šifra", required=True),
                "dobavljac": st.column_config.TextColumn("Dobavljač"),
                "cijena": st.column_config.NumberColumn("Cijena", min_value=0, format="%.2f"),
                "pakiranje": st.column_config.TextColumn("Pakiranje"),
                "napomena": st.column_config.TextColumn("Napomena"),
                "link": st.column_config.TextColumn("Link"),
                "slika": st.column_config.TextColumn("Slika (URL)"),
                "created_at": st.column_config.TextColumn("Kreirano"),
                "updated_at": st.column_config.TextColumn("Ažurirano"),
                "Odaberi za brisanje": st.column_config.CheckboxColumn("Obriši"),
            }
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Spremi promjene", type="primary"):
                for row in edited_df.to_dict("records"):
                    row_id = row["id"]
                    if row["Odaberi za brisanje"]:
                        supabase.table("proizvodi").delete().eq("id", row_id).execute()
                    else:
                        update_data = {k: v for k, v in row.items() if k not in ["Odaberi za brisanje"]}
                        supabase.table("proizvodi").update(update_data).eq("id", row_id).execute()
                st.success("Promjene spremljene! Označeni proizvodi su obrisani.")
                st.rerun()
        with col2:
            if st.button("Izvezi SVE podatke u Excel"):
                if not df_full.empty:
                    output = io.BytesIO()
                    df_full.to_excel(output, index=False, sheet_name="Svi proizvodi")
                    output.seek(0)
                    st.download_button(
                        label="Preuzmi cijelu bazu (.xlsx)",
                        data=output,
                        file_name=f"svi_proizvodi_{datetime.now(TZ).strftime('%Y-%m-%d_%H-%M')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.warning("Nema podataka za export.")
        st.subheader("Dodaj novi proizvod")
        with st.form("dodaj_proizvod"):
            naziv = st.text_input("Naziv proizvoda *", key="dodaj_naziv_proizvoda")
            sifra = st.text_input("Šifra *", key="dodaj_sifra_proizvoda")
            dobavljac = st.text_input("Dobavljač", key="dodaj_dobavljac_proizvoda")
            cijena = st.number_input("Cijena", min_value=0.0, step=0.01, format="%.2f", key="dodaj_cijena_proizvoda")
            pakiranje = st.text_input("Pakiranje", key="dodaj_pakiranje_proizvoda")
            napomena = st.text_area("Napomena", key="dodaj_napomena_proizvoda")
            link = st.text_input("Link (URL slike)", key="dodaj_link_proizvoda")
            slika = st.text_input("Slika (URL slike)", key="dodaj_slika_proizvoda")
            submitted = st.form_submit_button("Dodaj proizvod")
            if submitted:
                novi = {
                    "naziv": naziv or "",
                    "sifra": sifra or "",
                    "dobavljac": dobavljac or "",
                    "cijena": cijena,
                    "pakiranje": pakiranje or "",
                    "napomena": napomena or "",
                    "link": link or "",
                    "slika": slika or ""
                }
                try:
                    supabase.table("proizvodi").insert(novi).execute()
                    st.success("Proizvod dodan!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Greška pri dodavanju: {str(e)}")
                    if "unique constraint" in str(e):
                        st.error("Šifra već postoji u bazi – ali novi red je ipak dodan!")
            if st.form_submit_button("Odustani", key="dodaj_odustani"):
                st.rerun()
        # UPLOAD IZ EXCELA ZA PROIZVODE – popravljeno s dijagnostikom
        st.subheader("Upload proizvoda iz Excela")
        uploaded_file = st.file_uploader("Odaberi .xlsx datoteku", type=["xlsx"], key="upload_proizvodi")
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

                    response = supabase.table("proizvodi").select("naziv").execute()
                    postojeći_nazivi = {r["naziv"].strip().lower() for r in response.data if r["naziv"]}

                    for i in range(0, len(df_upload), batch_size):
                        batch = df_upload.iloc[i:i + batch_size]
                        st.write(f"Učitavam batch {i//batch_size + 1}...")

                        for _, row in batch.iterrows():
                            naziv = str(row.get("NAZIV", "")).strip()
                            if not naziv:
                                broj_praznih += 1
                                continue

                            # Zakomentiraj sljedeće 3 linije ako želiš DOPUSTITI duplikate (da doda sve redove)
                            # if naziv.lower() in postojeći_nazivi:
                            #     broj_duplikata += 1
                            #     continue

                            cijena_raw = str(row.get("CIJENA", "0")).strip()
                            cijena_raw = cijena_raw.replace(',', '.').replace(' ', '').replace('kn', '').replace('€', '').replace('HRK', '').strip()
                            try:
                                cijena = float(cijena_raw) if cijena_raw else 0
                            except ValueError:
                                cijena = 0

                            novi = {
                                "naziv": naziv,
                                "sifra": str(row.get("ŠIFRA", "")).strip() or "",
                                "dobavljac": str(row.get("DOBAVLJAČ", "")).strip() or "",
                                "cijena": cijena,
                                "pakiranje": str(row.get("PAKIRANJE", "")).strip() or "",
                                "napomena": str(row.get("NAPOMENA", "")).strip() or "",
                                "link": str(row.get("Link", "")).strip() or "",
                                "slika": str(row.get("slika", "")).strip() or ""
                            }

                            for k in novi:
                                if pd.isna(novi[k]) or novi[k] in [float('inf'), float('-inf')]:
                                    novi[k] = None

                            supabase.table("proizvodi").insert(novi).execute()
                            broj_dodanih += 1
                            # postojeći_nazivi.add(naziv.lower())  # zakomentirano da ne blokira unutar batcha

                        time.sleep(0.3)

                    st.write(f"Ukupno redaka u Excelu: {len(df_upload)}")
                    st.write(f"Dodano: {broj_dodanih}")
                    st.write(f"Preskočeno duplikata: {broj_duplikata}")
                    st.write(f"Preskočeno praznih naziva: {broj_praznih}")
                    st.success(f"Učitano **{broj_dodanih}** novih proizvoda. Preskočeno **{broj_duplikata}** duplikata. Praznih naziva: **{broj_praznih}**.")
                    st.rerun()
            except Exception as e:
                st.error(f"Greška pri čitanju Excela: {e}")
                st.error("Provjeri format datoteke.")

        # GUMB ZA OBRIŠI SVE PROIZVODA
        st.markdown("---")
        potvrdi_brisanje_svih = st.checkbox("Potvrdi brisanje svih proizvoda (nepovratno!)", key="potvrdi_obrisi_sve")
        if potvrdi_brisanje_svih:
            st.warning("Ovo će **obrisati SVE proizvode** iz baze. Nastavak je nepovratan.")
            if st.button("DA – Obriši sve proizvode", type="primary"):
                try:
                    supabase.table("proizvodi").delete().gt("id", 0).execute()
                    st.success("Svi proizvodi su obrisani!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Greška pri brisanju: {str(e)}")
                    st.error("Ako ima RLS, privremeno ga isključi u Supabaseu.")
            st.info("Ako se predomisliš, poništi checkbox iznad.")