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

# SESSION STATE
if "narudzbe_proizvodi" not in st.session_state:
    st.session_state.narudzbe_proizvodi = []

if "stranica" not in st.session_state:
    st.session_state.stranica = "login"

if "proizvodi_search" not in st.session_state:
    st.session_state.proizvodi_search = ""

if "dobavljaci_search" not in st.session_state:
    st.session_state.dobavljaci_search = ""

# CALLBACK ZA TRAŽILICU PROIZVODA
def on_proizvodi_search_change():
    st.session_state.proizvodi_search = st.session_state.proizvodi_search_input

# CALLBACK ZA TRAŽILICU DOBAVLJAČA
def on_dobavljaci_search_change():
    st.session_state.dobavljaci_search = st.session_state.dobavljaci_search_input

# LOGIN
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
    # SIDEBAR
    with st.sidebar:
        st.title("Sustav narudžbi")

        if st.button("🏠 Početna", key="menu_pocetna"):
            st.session_state.stranica = "početna"
            st.rerun()

        if st.button("🛒 Narudžbe", key="menu_narudzbe"):
            st.session_state.stranica = "narudžbe"
            st.rerun()

        if st.button("➕ Nova narudžba", key="menu_nova_narudzba"):
            st.session_state.stranica = "nova"
            st.rerun()

        if st.button("➡️ Odjava", key="menu_odjava"):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.session_state.stranica = "login"
            st.rerun()

    # POČETNA
    if st.session_state.stranica == "početna":
        st.title("Početna")
        st.markdown("### Dobrodošli u sustav narudžbi!")
        st.info("Ovdje će biti dashboard, statistike...")

    # PREGLED NARUDŽBI
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

    # NOVA NARUDŽBA
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

    # ADMINISTRACIJA → DOBAVLJAČI (sada sa svim što treba)
    elif st.session_state.stranica == "admin_dobavljaci":
        st.title("Administracija - Dobavljači")

        # Dohvati sve dobavljače
        response = supabase.table("dobavljaci").select("*").execute()
        df_dobavljaci = pd.DataFrame(response.data or [])

        if not df_dobavljaci.empty:
            # Naslov + tražilica
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

            # DODAJ NOVOG DOBAVLJAČA
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

            # UPLOAD DOBAVLJAČA IZ EXCELA
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
    #  ADMINISTRACIJA → PROIZVODI (ostaje kao prije)
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

        # UPLOAD IZ EXCELA ZA PROIZVODE
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
                    broj_preskocenih = 0
                    broj_duplikata = 0

                    response = supabase.table("proizvodi").select("naziv").execute()
                    postojeći_nazivi = {r["naziv"].strip().lower() for r in response.data if r["naziv"]}

                    for i in range(0, len(df_upload), batch_size):
                        batch = df_upload.iloc[i:i + batch_size]
                        st.write(f"Učitavam batch {i//batch_size + 1} / {(len(df_upload) + batch_size - 1) // batch_size}...")

                        for _, row in batch.iterrows():
                            naziv = str(row.get("NAZIV", "")).strip()
                            if not naziv:
                                continue

                            if naziv.lower() in postojeći_nazivi:
                                broj_duplikata += 1
                                continue

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
                            postojeći_nazivi.add(naziv.lower())

                        time.sleep(0.3)

                    st.success(f"Učitano **{broj_dodanih}** novih proizvoda. Preskočeno **{broj_duplikata}** duplikata po nazivu.")
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