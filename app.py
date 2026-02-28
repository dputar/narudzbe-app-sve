import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
from zoneinfo import ZoneInfo

st.set_page_config(page_title="Sustav narudžbi", layout="wide")

SUPABASE_URL = "https://vwekjvazuexwoglxqrtg.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ3ZWtqdmF6dWV4d29nbHhxcnRnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzIwMzMyOTcsImV4cCI6MjA4NzYwOTI5N30.59dWvEsXOE-IochSguKYSw_mDwFvEXHmHbCW7Gy_tto"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
TZ = ZoneInfo("Europe/Zagreb")

# ────────────────────────────────────────────────
#  SESSION STATE
# ────────────────────────────────────────────────

if "narudzbe_proizvodi" not in st.session_state:
    st.session_state.narudzbe_proizvodi = []

if "stranica" not in st.session_state:
    st.session_state.stranica = "početna"

# ────────────────────────────────────────────────
#  SIDEBAR – tvoj izgled po slici
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
#  GLAVNI SADRŽAJ
# ────────────────────────────────────────────────

if st.session_state.stranica == "login":
    st.title("Prijava u sustav narudžbi")
    tab1, tab2 = st.tabs(["Prijava", "Registracija"])

    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Lozinka", type="password", key="login_password")
        if st.button("Prijavi se", key="login_prijavi"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.session_state.stranica = "početna"
                st.rerun()
            except Exception as e:
                st.error(f"Greška: {e}")

    with tab2:
        email = st.text_input("Email", key="reg_email")
        password = st.text_input("Lozinka", type="password", key="reg_password")
        if st.button("Registriraj se", key="reg_registriraj"):
            try:
                supabase.auth.sign_up({"email": email, "password": password})
                st.success("Registracija OK – prijavi se")
            except Exception as e:
                st.error(f"Greška: {e}")

else:
    if st.session_state.stranica == "početna":
        st.title("Početna")
        st.markdown("### Dobrodošli u sustav narudžbi!")
        st.info("Ovdje će biti dashboard, statistike...")

    elif st.session_state.stranica == "narudžbe":
        st.title("Pregled narudžbi")

        if st.button("🔄 Osvježi", key="pregled_osvjezi"):
            st.rerun()

        response = supabase.table("main_orders").select("*").order("datum", desc=True).execute()
        df = pd.DataFrame(response.data or [])

        if not df.empty:
            df = df.fillna("")
            df = df.loc[:, ~df.columns.duplicated()]
            if "reprezentacija" in df.columns:
                df = df.rename(columns={"reprezentacija": "Skladište"})

            prikaz_stupci = [
                "id", "datum", "korisnik", "Skladište", "odgovorna_osoba",
                "sifra_proizvoda", "naziv_proizvoda", "kolicina", "dobavljac",
                "oznaci_za_narudzbu", "broj_narudzbe", "oznaci_zaprimljeno",
                "napomena_dobavljac", "napomena_za_nas", "unio_korisnik",
                "datum_vrijeme_narudzbe", "datum_vrijeme_zaprimanja", "cijena",
                "tip_klijenta"
            ]

            postojeći = [c for c in prikaz_stupci if c in df.columns]

            st.dataframe(
                df[postojeći],
                use_container_width=True,
                height=750
            )
        else:
            st.info("Još nema narudžbi.")

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
            korisnik = st.selectbox("", ["Daniel Putar"], key="nova_korisnik", label_visibility="collapsed")
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
            odgovorna_lista = ["Nema", "Daniel Putar", "Druga osoba"]
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
    #  ADMINISTRACIJA → DOBAVLJAČI
    # ────────────────────────────────────────────────

    elif st.session_state.stranica == "admin_dobavljaci":
        st.title("Administracija - Dobavljači")

        # Dohvati sve dobavljače
        response = supabase.table("dobavljaci").select("*").execute()
        df_dobavljaci = pd.DataFrame(response.data or [])

        if not df_dobavljaci.empty:
            st.subheader("Postojeći dobavljači")
            edited_df = st.data_editor(
                df_dobavljaci,
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
                    "created_at": st.column_config.DateTimeColumn("Kreirano"),
                    "updated_at": st.column_config.DateTimeColumn("Ažurirano"),
                }
            )

            if st.button("💾 Spremi promjene", type="primary"):
                for row in edited_df.to_dict("records"):
                    supabase.table("dobavljaci").upsert(row, on_conflict="id").execute()
                st.success("Promjene spremljene!")
                st.rerun()
        else:
            st.info("Još nema dobavljača u bazi.")

        # Dodaj novog dobavljača
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

        # Upload iz Excela – s čišćenjem nan/inf
        st.subheader("Upload dobavljača iz Excela")
        uploaded_file = st.file_uploader("Odaberi .xlsx datoteku", type=["xlsx"], key="upload_dobavljaci")
        if uploaded_file:
            try:
                df_upload = pd.read_excel(uploaded_file)
                st.write("Pregled podataka iz datoteke:")
                st.dataframe(df_upload.head(10))

                if st.button("Učitaj sve u bazu", type="primary"):
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
                        # Čišćenje nan/inf vrijednosti
                        for k in novi:
                            if pd.isna(novi[k]) or novi[k] in [float('inf'), float('-inf')]:
                                novi[k] = None

                        supabase.table("dobavljaci").insert(novi).execute()
                    st.success("Dobavljači učitani iz Excela!")
                    st.rerun()
            except Exception as e:
                st.error(f"Greška pri čitanju Excela: {e}")
                st.error("Provjeri da li je datoteka ispravna .xlsx i da ima potrebne stupce.")