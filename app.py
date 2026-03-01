import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
from zoneinfo import ZoneInfo
import time
import io

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
    st.session_state.stranica = "login"

if "proizvodi_search" not in st.session_state:
    st.session_state.proizvodi_search = ""

if "dobavljaci_search" not in st.session_state:
    st.session_state.dobavljaci_search = ""

# ────────────────────────────────────────────────
#  CALLBACK ZA TRAŽILICU PROIZVODA
# ────────────────────────────────────────────────

def on_proizvodi_search_change():
    st.session_state.proizvodi_search = st.session_state.proizvodi_search_input

# ────────────────────────────────────────────────
#  CALLBACK ZA TRAŽILICU DOBAVLJAČA
# ────────────────────────────────────────────────

def on_dobavljaci_search_change():
    st.session_state.dobavljaci_search = st.session_state.dobavljaci_search_input

# ────────────────────────────────────────────────
#  LOGIN
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
    #  SIDEBAR
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
    #  POČETNA
    # ────────────────────────────────────────────────

    if st.session_state.stranica == "početna":
        st.title("Početna")
        st.markdown("### Dobrodošli u sustav narudžbi!")
        st.info("Ovdje će biti dashboard, statistike...")

    # ────────────────────────────────────────────────
    #  NARUDŽBE
    # ────────────────────────────────────────────────

    elif st.session_state.stranica == "narudžbe":
        st.title("Pregled narudžbi")

        if st.button("➕ Nova narudžba", type="primary", key="nova_narudzba_gumb"):
            st.session_state.stranica = "nova"
            st.rerun()

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

    # ────────────────────────────────────────────────
    #  NOVA NARUDŽBA
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
    #  ADMINISTRACIJA → DOBAVLJAČI (s checkboxom, tražilicom i exportom)
    # ────────────────────────────────────────────────

    elif st.session_state.stranica == "admin_dobavljaci":
        st.title("Administracija - Dobavljači")

        # Dohvati sve dobavljače
        response = supabase.table("dobavljaci").select("*").execute()
        df_dobavljaci = pd.DataFrame(response.data or [])

        if not df_dobavljaci.empty:
            # Naslov + tražilica pored
            col1, col2 = st.columns([6, 4])
            with col1:
                st.subheader("Postojeći dobavljači")
            with col2:
                st.text_input(
                    "Pretraži po svim stupcima",
                    value=st.session_state.dobavljaci_search,
                    key="dobavljaci_search_input",
                    placeholder="upiši naziv, email, rok...",
                    on_change=lambda: st.session_state.update({"dobavljaci_search": st.session_state.dobavljaci_search_input})
                )

            # Filtriranje
            df_display = df_dobavljaci.copy()
            if st.session_state.dobavljaci_search:
                search_term = str(st.session_state.dobavljaci_search).strip().lower()
                mask = df_display.astype(str).apply(lambda x: x.str.lower().str.contains(search_term), axis=1).any(axis=1)
                df_display = df_display[mask]

            if df_display.empty and st.session_state.dobavljaci_search:
                st.info("Ništa nije pronađeno.")
            elif df_display.empty:
                st.info("Još nema dobavljača u bazi.")

            # Dodaj checkbox za brisanje
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
                    if not df_full.empty:
                        output = io.BytesIO()
                        df_full.to_excel(output, index=False, sheet_name="Svi dobavljači")
                        output.seek(0)
                        st.download_button(
                            label="Preuzmi cijelu listu (.xlsx)",
                            data=output,
                            file_name=f"svi_dobavljaci_{datetime.now(TZ).strftime('%Y-%m-%d_%H-%M')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    else:
                        st.warning("Nema podataka za export.")

            with col3:
                st.button("🔄 Osvježi", on_click=st.rerun)

        else:
            st.info("Još nema dobavljača u bazi.")

    # ────────────────────────────────────────────────
    #  ADMINISTRACIJA → PROIZVODI (ostaje isto kao zadnji put)
    # ────────────────────────────────────────────────

    elif st.session_state.stranica == "admin_proizvodi":
        # ... tvoj kod za proizvode ostaje nepromijenjen – možeš ga kopirati iz prethodnog odgovora ...
        pass

    # ────────────────────────────────────────────────
    #  DODAJ NOVI PROIZVOD / UPLOAD (ostaje isto)
    # ────────────────────────────────────────────────

    # ... ostatak koda za dodavanje i upload proizvoda ostaje isti ...