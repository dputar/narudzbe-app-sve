import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
from zoneinfo import ZoneInfo
import time
import io
import numpy as np
import calendar
import matplotlib.pyplot as plt
from datetime import timedelta
from datetime import date
import bcrypt  # za provjeru hashed lozinke

st.set_page_config(page_title="Sustav narudžbi", layout="wide")

# Supabase konekcija
SUPABASE_URL = "https://vwekjvazuexwoglxqrtg.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ3ZWtqdmF6dWV4d29nbHhxcnRnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzIwMzMyOTcsImV4cCI6MjA4NzYwOTI5N30.59dWvEsXOE-IochSguKYSw_mDwFvEXHmHbCW7Gy_tto"
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

TZ = ZoneInfo("Europe/Zagreb")

# Session state inicijalizacija
if "user" not in st.session_state:
    st.session_state.user = None
if "stranica" not in st.session_state:
    st.session_state.stranica = "login"
if "search_input" not in st.session_state:
    st.session_state.search_input = ""
if "temp_order" not in st.session_state:
    st.session_state.temp_order = None
if "temp_odmor" not in st.session_state:
    st.session_state.temp_odmor = None
if "form_reset" not in st.session_state:
    st.session_state.form_reset = False
if "last_refresh_time" not in st.session_state:
    st.session_state.last_refresh_time = time.time()

# Funkcija za autentifikaciju
def authenticate_user(username, password):
    try:
        user_response = supabase.table("korisnici").select("*").eq("korisničko_ime", username.strip()).single().execute()
        user = user_response.data
        if user:
            stored_hash = user['lozinka'].strip()
            try:
                if bcrypt.checkpw(password.strip().encode('utf-8'), stored_hash.encode('utf-8')):
                    return user
                else:
                    st.error("Lozinka se ne podudara")
                    return None
            except Exception as enc_err:
                st.error(f"Encoding greška: {str(enc_err)}")
                if stored_hash == password.strip():
                    st.warning("Lozinka je plain text – hashirajte je u bazi!")
                    return user
                else:
                    return None
        else:
            st.error("Korisnik nije pronađen")
            return None
    except Exception as e:
        st.error(f"Greška pri autentifikaciji: {str(e)}")
        return None

# Login stranica
if st.session_state.stranica == "login":
    st.title("Prijava u sustav narudžbi")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        username = st.text_input("Korisničko ime").strip()
        password = st.text_input("Lozinka", type="password").strip()

        if st.button("Prijavi se"):
            if not username or not password:
                st.error("Unesite korisničko ime i lozinku!")
            else:
                user = authenticate_user(username, password)
                if user:
                    st.session_state.user = user
                    st.session_state.stranica = "narudzbe"  # početna stranica nakon logina
                    st.success("Uspješna prijava!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Korisničko ime ne postoji ili lozinka nije ispravna.")

    st.stop()

# Sidebar navigacija (bez dijakritika u ključevima)
st.sidebar.title(f"Dobro došli, {st.session_state.user.get('ime_prezime', 'Nepoznato')}")

stranice = ["Narudzbe", "Proizvodi", "Dobavljaci", "Korisnici", "Dokumenti"]
izbor = st.sidebar.selectbox("Odaberi stranicu", stranice)

if izbor == "Narudzbe":
    st.session_state.stranica = "narudzbe"
elif izbor == "Proizvodi":
    st.session_state.stranica = "proizvodi"
elif izbor == "Dobavljaci":
    st.session_state.stranica = "dobavljaci"
elif izbor == "Korisnici":
    st.session_state.stranica = "korisnici"
elif izbor == "Dokumenti":
    st.session_state.stranica = "dokumenti"

if st.sidebar.button("Odjavi se"):
    st.session_state.user = None
    st.session_state.stranica = "login"
    st.rerun()

# ────────────────────────────────────────────────
# GLAVNI SADRŽAJ – STRANICE
# ────────────────────────────────────────────────
if st.session_state.stranica == "narudzbe":
    st.title("Pregled narudžbi")
    col1, col2 = st.columns([6, 4])
    with col1:
        st.subheader("Postojeće narudžbe")
    with col2:
        st.text_input(
            "Pretraži po svim stupcima",
            value=st.session_state.get("narudzbe_search", ""),
            key="narudzbe_search_input",
            placeholder="upiši broj narudžbe, datum, klijenta, proizvod...",
        )
    if st.button("🔄 Osvježi"):
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
        search_term = str(st.session_state.get("narudzbe_search", "")).strip().lower()
        if search_term:
            mask = df_display.astype(str).apply(lambda x: x.str.lower().str.contains(search_term), axis=1).any(axis=1)
            df_display = df_display[mask]
        if df_display.empty and search_term:
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
                        for i in range(0, len(df_upload), batch_size):
                            batch = df_upload.iloc[i:i + batch_size]
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
                        st.success(f"Učitano **{broj_dodanih}** novih narudžbi.")
                        st.rerun()
                except Exception as e:
                    st.error(f"Greška pri čitanju Excela: {e}")

        

# ────────────────────────────────────────────────
# DOKUMENTI – OVDJE JE CIJELI TVOJ KOD (bez promjena osim stabilnosti)
# ────────────────────────────────────────────────
elif st.session_state.stranica == "dokumenti":
    st.title("Godišnji odmor i slobodni dani")

    from datetime import datetime, timedelta
    import io
    import json

    # Funkcija za izračun radnih dana
    def calculate_working_days(start_str, end_str, holidays):
        start = datetime.fromisoformat(start_str).date()
        end = datetime.fromisoformat(end_str).date()
        count = 0
        current = start
        while current <= end:
            if current.weekday() < 5 and current not in holidays:
                count += 1
            current += timedelta(days=1)
        return count

    # Prvi radni dan nakon završetka
    def find_next_working_day(end_date_str, holidays):
        end = datetime.fromisoformat(end_date_str).date()
        current = end + timedelta(days=1)
        while current.weekday() >= 5 or current in holidays:
            current += timedelta(days=1)
        return current.strftime("%d.%m.%Y.")

    # Stvarni broj iskorištenih dana za korisnika
    def get_used_days_for_user(korisnik_id, exclude_id=None):
        query = supabase.table("odmori").select("datum_od, datum_do").eq("korisnik_id", korisnik_id)
        if exclude_id:
            query = query.neq("id", exclude_id)
        response = query.execute()
        df = pd.DataFrame(response.data or [])
        if df.empty:
            return 0
        df["datum_od"] = pd.to_datetime(df["datum_od"]).dt.date
        df["datum_do"] = pd.to_datetime(df["datum_do"]).dt.date
        holidays = holidays_dict.get(tekuca_godina, [])
        total = 0
        for _, row in df.iterrows():
            total += calculate_working_days(row["datum_od"].isoformat(), row["datum_do"].isoformat(), holidays)
        return total

    # Inicijalizacija session_state
    if "temp_odmor" not in st.session_state:
        st.session_state.temp_odmor = None
    if "form_reset" not in st.session_state:
        st.session_state.form_reset = False

    # Praznici 2026–2040 (možeš dodati i ranije godine ako treba)
    holidays_dict = {
        2026: [date(2026, 1, 1), date(2026, 1, 6), date(2026, 4, 5), date(2026, 4, 6), date(2026, 5, 1), date(2026, 5, 30), date(2026, 6, 22), date(2026, 8, 15), date(2026, 11, 1), date(2026, 11, 18), date(2026, 12, 25), date(2026, 12, 26)],
        2027: [date(2027, 1, 1), date(2027, 1, 6), date(2027, 3, 28), date(2027, 3, 29), date(2027, 5, 1), date(2027, 5, 27), date(2027, 6, 22), date(2027, 8, 15), date(2027, 11, 1), date(2027, 11, 18), date(2027, 12, 25), date(2027, 12, 26)],
        2028: [date(2028, 1, 1), date(2028, 1, 6), date(2028, 4, 16), date(2028, 4, 17), date(2028, 5, 1), date(2028, 5, 30), date(2028, 6, 22), date(2028, 8, 15), date(2028, 11, 1), date(2028, 11, 18), date(2028, 12, 25), date(2028, 12, 26)],
        2029: [date(2029, 1, 1), date(2029, 1, 6), date(2029, 4, 1), date(2029, 4, 2), date(2029, 5, 1), date(2029, 5, 30), date(2029, 6, 22), date(2029, 8, 15), date(2029, 11, 1), date(2029, 11, 18), date(2029, 12, 25), date(2029, 12, 26)],
        2030: [date(2030, 1, 1), date(2030, 1, 6), date(2030, 4, 21), date(2030, 4, 22), date(2030, 5, 1), date(2030, 5, 30), date(2030, 6, 22), date(2030, 8, 15), date(2030, 11, 1), date(2030, 11, 18), date(2030, 12, 25), date(2030, 12, 26)],
        2031: [date(2031, 1, 1), date(2031, 1, 6), date(2031, 4, 13), date(2031, 4, 14), date(2031, 5, 1), date(2031, 5, 30), date(2031, 6, 22), date(2031, 8, 15), date(2031, 11, 1), date(2031, 11, 18), date(2031, 12, 25), date(2031, 12, 26)],
        2032: [date(2032, 1, 1), date(2032, 1, 6), date(2032, 3, 28), date(2032, 3, 29), date(2032, 5, 1), date(2032, 5, 30), date(2032, 6, 22), date(2032, 8, 15), date(2032, 11, 1), date(2032, 11, 18), date(2032, 12, 25), date(2032, 12, 26)],
        2033: [date(2033, 1, 1), date(2033, 1, 6), date(2033, 4, 17), date(2033, 4, 18), date(2033, 5, 1), date(2033, 5, 30), date(2033, 6, 22), date(2033, 8, 15), date(2033, 11, 1), date(2033, 11, 18), date(2033, 12, 25), date(2033, 12, 26)],
        2034: [date(2034, 1, 1), date(2034, 1, 6), date(2034, 4, 9), date(2034, 4, 10), date(2034, 5, 1), date(2034, 5, 30), date(2034, 6, 22), date(2034, 8, 15), date(2034, 11, 1), date(2034, 11, 18), date(2034, 12, 25), date(2034, 12, 26)],
        2035: [date(2035, 1, 1), date(2035, 1, 6), date(2035, 3, 25), date(2035, 3, 26), date(2035, 5, 1), date(2035, 5, 30), date(2035, 6, 22), date(2035, 8, 15), date(2035, 11, 1), date(2035, 11, 18), date(2035, 12, 25), date(2035, 12, 26)],
        2036: [date(2036, 1, 1), date(2036, 1, 6), date(2036, 4, 13), date(2036, 4, 14), date(2036, 5, 1), date(2036, 5, 30), date(2036, 6, 22), date(2036, 8, 15), date(2036, 11, 1), date(2036, 11, 18), date(2036, 12, 25), date(2036, 12, 26)],
        2037: [date(2037, 1, 1), date(2037, 1, 6), date(2037, 4, 5), date(2037, 4, 6), date(2037, 5, 1), date(2037, 5, 30), date(2037, 6, 22), date(2037, 8, 15), date(2037, 11, 1), date(2037, 11, 18), date(2037, 12, 25), date(2037, 12, 26)],
        2038: [date(2038, 1, 1), date(2038, 1, 6), date(2038, 4, 25), date(2038, 4, 26), date(2038, 5, 1), date(2038, 5, 30), date(2038, 6, 22), date(2038, 8, 15), date(2038, 11, 1), date(2038, 11, 18), date(2038, 12, 25), date(2038, 12, 26)],
        2039: [date(2039, 1, 1), date(2039, 1, 6), date(2039, 4, 10), date(2039, 4, 11), date(2039, 5, 1), date(2039, 5, 30), date(2039, 6, 22), date(2039, 8, 15), date(2039, 11, 1), date(2039, 11, 18), date(2039, 12, 25), date(2039, 12, 26)],
        2040: [date(2040, 1, 1), date(2040, 1, 6), date(2040, 4, 1), date(2040, 4, 2), date(2040, 5, 1), date(2040, 5, 30), date(2040, 6, 22), date(2040, 8, 15), date(2040, 11, 1), date(2040, 11, 18), date(2040, 12, 25), date(2040, 12, 26)],
    }

    # Dohvati korisnike za padajući izbornik
    try:
        korisnici_response = supabase.table("korisnici").select("id,ime_prezime,godisnji_dani,slobodni_dani,odobreni_dani_po_godini").eq("aktivan", True).execute()
        korisnici = korisnici_response.data or []
        korisnik_options = {k["ime_prezime"]: k for k in korisnici}
    except Exception as e:
        st.error(f"Greška pri dohvaćanju korisnika: {str(e)}")
        korisnik_options = {}

    # Dohvati svježe podatke prijavljenog korisnika
    try:
        user_response = supabase.table("korisnici")\
            .select("id,ime_prezime,godisnji_dani,slobodni_dani,odobreni_dani_po_godini")\
            .eq("id", st.session_state.user.get("id"))\
            .single()\
            .execute()
        user_data = user_response.data
    except Exception as e:
        user_data = None
        st.error(f"Greška pri dohvaćanju podataka korisnika: {str(e)}")

    prijavljeni_korisnik_ime = user_data["ime_prezime"] if user_data else "Nepoznato"
    prijavljeni_korisnik_id = user_data["id"] if user_data else None
    tip_korisnika = st.session_state.user.get("tip_korisnika", "korisnik")

    tekuca_godina = datetime.now().year

    # Odabir korisnika (samo za admina)
    if tip_korisnika == "administrator":
        korisnik_ime = st.selectbox("Odaberi korisnika za unos", list(korisnik_options.keys()),
                                    index=list(korisnik_options.keys()).index(prijavljeni_korisnik_ime) if prijavljeni_korisnik_ime in korisnik_options else 0,
                                    key="odmor_selected_korisnik")
        selected_korisnik = korisnik_options.get(korisnik_ime, {})
        korisnik_id = selected_korisnik.get("id", prijavljeni_korisnik_id)
    else:
        korisnik_id = prijavljeni_korisnik_id
        korisnik_ime = prijavljeni_korisnik_ime
        st.text_input("Korisnik *", value=korisnik_ime, disabled=True, key="odmor_korisnik_disabled")

    # Dohvati kumulativni saldo
    try:
        korisnik_response = supabase.table("korisnici")\
            .select("godisnji_dani,slobodni_dani")\
            .eq("id", korisnik_id)\
            .single()\
            .execute()
        korisnik_podaci = korisnik_response.data
        preostalo_godisnje = korisnik_podaci.get("godisnji_dani") or 0
        preostalo_slobodnih = korisnik_podaci.get("slobodni_dani") or 0
    except Exception as e:
        preostalo_godisnje = 0
        preostalo_slobodnih = 0
        st.error(f"Greška pri dohvaćanju salda korisnika: {str(e)}")

    st.markdown(f"**Preostalo godišnjih dana za {tekuca_godina} ({korisnik_ime}): {preostalo_godisnje}**")
    st.markdown(f"**Preostalo slobodnih dana ({korisnik_ime}): {preostalo_slobodnih}**")

    # Forma za dodavanje odmora
    with st.form("dodaj_odmor_form", clear_on_submit=True):
        st.subheader("Dodaj novi unos godišnjeg / slobodnog dana")

        col1, col2 = st.columns(2)
        datum_od_input = col1.date_input("Datum od *", value=None, key="odmor_datum_od")
        datum_do_input = col2.date_input("Datum do *", value=None, key="odmor_datum_do")

        tip_odmora = st.selectbox("Tip odsustva *", [""] + ["Godišnji odmor", "Slobodni dan", "Bolovanje", "Ostalo"], index=0, key="odmor_tip")
        napomena = st.text_area("Napomena (opcionalno)", key="odmor_napomena")

        submitted = st.form_submit_button("Dodaj unos", type="primary")

    if submitted:
        if not korisnik_id:
            st.error("Korisnik je obavezan!")
        elif not datum_od_input or not datum_do_input:
            st.error("Datum od i Datum do su obavezni!")
        elif datum_do_input < datum_od_input:
            st.error("Datum 'do' ne može biti prije 'od'!")
        elif tip_odmora == "":
            st.error("Tip odsustva je obavezan!")
        else:
            datum_od = datum_od_input
            datum_do = datum_do_input

            broj_dana = calculate_working_days(datum_od.isoformat(), datum_do.isoformat(), holidays_dict.get(tekuca_godina, []))

            # Provjera ograničenja
            if tip_odmora == "Godišnji odmor":
                if broj_dana > preostalo_godisnje:
                    st.error(f"Premašuješ preostale godišnje dane! Preostalo: {preostalo_godisnje}, tražiš: {broj_dana}")
                    st.stop()
            elif tip_odmora == "Slobodni dan":
                if broj_dana > preostalo_slobodnih:
                    st.error(f"Premašuješ preostale slobodne dane! Preostalo: {preostalo_slobodnih}, tražiš: {broj_dana}")
                    st.stop()

            try:
                odmori_response = supabase.table("odmori").select("*").execute()
                df_odmori = pd.DataFrame(odmori_response.data or [])

                preklapanja = 0
                preklapanja_ista_osoba = 0
                for _, row in df_odmori.iterrows():
                    start_db = datetime.fromisoformat(row["datum_od"]).date()
                    end_db = datetime.fromisoformat(row["datum_do"]).date()
                    start = max(datum_od, start_db)
                    end = min(datum_do, end_db)
                    if start <= end:
                        preklapanja += (end - start).days + 1
                        if row["korisnik_id"] == korisnik_id:
                            preklapanja_ista_osoba += (end - start).days + 1

                if preklapanja_ista_osoba > 0:
                    st.error("Ista osoba već ima upis na preklapajuće datume! Ne može se dodati dupli unos.")
                    st.stop()

                if preklapanja > 0:
                    st.session_state.temp_odmor = {
                        "korisnik_id": korisnik_id,
                        "datum_od": datum_od,
                        "datum_do": datum_do,
                        "tip": tip_odmora,
                        "napomena": napomena.strip() or None,
                        "unio_korisnik": st.session_state.user.get("korisničko_ime", "Nepoznato"),
                        "broj_dana": broj_dana
                    }
                    st.rerun()
                else:
                    novi = {
                        "korisnik_id": korisnik_id,
                        "datum_od": datum_od.isoformat(),
                        "datum_do": datum_do.isoformat(),
                        "tip": tip_odmora,
                        "napomena": napomena.strip() or None,
                        "unio_korisnik": st.session_state.user.get("korisničko_ime", "Nepoznato"),
                        "created_at": datetime.now(TZ).isoformat()
                    }
                    supabase.table("odmori").insert(novi).execute()

                    # Oduzmi dane iz salda
                    if tip_odmora == "Godišnji odmor":
                        novi_saldo = preostalo_godisnje - broj_dana
                        supabase.table("korisnici").update({"godisnji_dani": max(0, int(novi_saldo))}).eq("id", korisnik_id).execute()
                    elif tip_odmora == "Slobodni dan":
                        novi_slobodni = preostalo_slobodnih - broj_dana
                        supabase.table("korisnici").update({"slobodni_dani": max(0, int(novi_slobodni))}).eq("id", korisnik_id).execute()

                    st.success("Unos dodan bez preklapanja!")
                    st.session_state.form_reset = True
                    st.rerun()
            except Exception as e:
                st.error(f"Greška pri provjeri/spremanju: {str(e)}")

    # Potvrda preklapanja
    if st.session_state.temp_odmor:
        try:
            odmori_response = supabase.table("odmori").select("*").execute()
            df_odmori = pd.DataFrame(odmori_response.data or [])
            preklapanja = 0
            preklapanja_ista_osoba = 0
            for _, row in df_odmori.iterrows():
                start_db = datetime.fromisoformat(row["datum_od"]).date()
                end_db = datetime.fromisoformat(row["datum_do"]).date()
                start = max(st.session_state.temp_odmor["datum_od"], start_db)
                end = min(st.session_state.temp_odmor["datum_do"], end_db)
                if start <= end:
                    preklapanja += (end - start).days + 1
                    if row["korisnik_id"] == st.session_state.temp_odmor["korisnik_id"]:
                        preklapanja_ista_osoba += (end - start).days + 1

            if preklapanja_ista_osoba > 0:
                st.error("Ista osoba već ima upis na preklapajuće datume! Ne može se dodati.")
                st.session_state.temp_odmor = None
                st.rerun()
                return

            st.warning(f"Preklapanje u {preklapanja} dana sa drugim korisnicima.")
            col1, col2 = st.columns(2)
            if col1.button("Potvrdi dodavanje sa preklapanjem"):
                novi = {
                    "korisnik_id": st.session_state.temp_odmor["korisnik_id"],
                    "datum_od": st.session_state.temp_odmor["datum_od"].isoformat(),
                    "datum_do": st.session_state.temp_odmor["datum_do"].isoformat(),
                    "tip": st.session_state.temp_odmor["tip"],
                    "napomena": st.session_state.temp_odmor["napomena"],
                    "unio_korisnik": st.session_state.temp_odmor["unio_korisnik"],
                    "created_at": datetime.now(TZ).isoformat()
                }
                supabase.table("odmori").insert(novi).execute()

                broj_dana = st.session_state.temp_odmor["broj_dana"]
                if st.session_state.temp_odmor["tip"] == "Godišnji odmor":
                    novi_saldo = preostalo_godisnje - broj_dana
                    supabase.table("korisnici").update({"godisnji_dani": max(0, int(novi_saldo))}).eq("id", korisnik_id).execute()
                elif st.session_state.temp_odmor["tip"] == "Slobodni dan":
                    novi_slobodni = preostalo_slobodnih - broj_dana
                    supabase.table("korisnici").update({"slobodni_dani": max(0, int(novi_slobodni))}).eq("id", korisnik_id).execute()

                st.success("Unos dodan sa preklapanjem!")
                st.session_state.temp_odmor = None
                st.session_state.form_reset = True
                st.rerun()
            if col2.button("Odustani"):
                st.session_state.temp_odmor = None
                st.session_state.form_reset = True
                st.rerun()
        except Exception as e:
            st.error(f"Greška pri ponovnom dohvaćanju: {str(e)}")

    # Reset forme
    if st.session_state.form_reset:
        st.session_state.form_reset = False
        st.rerun()

    # Kalendar – ispod forme
    st.subheader("Kalendar preklapanja")
    try:
        col_year, col_month = st.columns(2)
        year = col_year.selectbox("Godina", range(2025, 2041), index=datetime.now().year - 2025, key="kal_god")
        month = col_month.selectbox("Mjesec", range(1, 13), index=datetime.now().month - 1,
                                    format_func=lambda m: calendar.month_name[m], key="kal_mj")

        odmori_response = supabase.table("odmori")\
            .select("*, korisnici!inner(ime_prezime)")\
            .execute()

        df_odmori = pd.DataFrame(odmori_response.data or [])

        if not df_odmori.empty:
            df_odmori["korisnik_ime"] = df_odmori["korisnici"].apply(lambda x: x["ime_prezime"] if isinstance(x, dict) and "ime_prezime" in x else "Nepoznato")
            df_odmori = df_odmori.drop(columns=["korisnici"])

            unique_users = df_odmori["korisnik_ime"].unique()
            color_map = {user: plt.cm.tab10(i / len(unique_users)) for i, user in enumerate(unique_users)}

            cal = calendar.monthcalendar(year, month)

            fig, ax = plt.subplots(figsize=(12, 8))
            ax.set_title(f"{calendar.month_name[month]} {year}", fontsize=18, pad=35)
            ax.axis('off')

            days = ['Pon', 'Uto', 'Sri', 'Čet', 'Pet', 'Sub', 'Ned']
            for i, day in enumerate(days):
                ax.text(i + 0.5, 0.3, day, ha='center', va='bottom', fontsize=14, fontweight='bold', color='black')

            for week_num, week in enumerate(cal):
                for day_num, day in enumerate(week):
                    if day == 0:
                        continue
                    x = day_num
                    y = -week_num - 0.8
                    rect = plt.Rectangle((x, y), 1, -1, fill=False, edgecolor='black', linewidth=1)
                    ax.add_patch(rect)
                    ax.text(x + 0.5, y - 0.5, day, ha='center', va='center', fontsize=12)

                    current_date = datetime(year, month, day).date()
                    overlapping_users = []
                    for _, unos in df_odmori.iterrows():
                        start = datetime.fromisoformat(unos["datum_od"]).date()
                        end = datetime.fromisoformat(unos["datum_do"]).date()
                        if start <= current_date <= end:
                            overlapping_users.append(unos["korisnik_ime"])

                    is_weekend = current_date.weekday() >= 5
                    is_holiday = current_date in holidays_dict.get(year, [])
                    if is_weekend or is_holiday:
                        continue

                    if len(overlapping_users) > 1:
                        ax.add_patch(plt.Rectangle((x, y), 1, -1, color='red', alpha=0.5))
                        text = "\n".join(overlapping_users)
                        ax.text(x + 0.5, y - 0.8, text, ha='center', va='center', fontsize=8, color='white')
                    elif len(overlapping_users) == 1:
                        user = overlapping_users[0]
                        user_color = color_map.get(user, 'gray')
                        ax.add_patch(plt.Rectangle((x, y), 1, -1, color=user_color, alpha=0.5))
                        ax.text(x + 0.5, y - 0.8, user, ha='center', va='center', fontsize=8, color='white')

            ax.set_xlim(0, 7)
            ax.set_ylim(-7.0, 0.8)
            ax.set_aspect('equal')

            fig.tight_layout(pad=4.5)

            buf = io.BytesIO()
            fig.savefig(buf, format="png", bbox_inches='tight', dpi=120)
            buf.seek(0)
            st.image(buf, caption="Kalendar odsustava (crveno za preklapanja, boje po korisniku, imena ispod datuma)")
        else:
            st.info("Nema unosa za prikaz kalendara.")
    except Exception as e:
        st.error(f"Greška pri prikazu kalendara: {str(e)}")

    # Administrativne radnje – SAMO ZA ADMINISTRATORA
    if tip_korisnika == "administrator":
        st.subheader("Administrativne radnje")

        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"Dodijeli nove godišnje dane za {tekuca_godina} svima"):
                try:
                    korisnici_response = supabase.table("korisnici").select("id,ime_prezime,godisnji_dani,odobreni_dani_po_godini").execute()
                    for kor in korisnici_response.data or []:
                        kor_id = kor["id"]
                        dodjeljeni = kor.get("odobreni_dani_po_godini") or 20
                        trenutni = kor.get("godisnji_dani") or 0
                        novi_saldo = trenutni + dodjeljeni

                        supabase.table("korisnici").update({"godisnji_dani": novi_saldo}).eq("id", kor_id).execute()

                        supabase.table("godisnji_balans").upsert({
                            "korisnik_id": kor_id,
                            "godina": tekuca_godina,
                            "iskoristeno_dana": 0,
                            "neiskoristeno_dana": dodjeljeni
                        }).execute()

                    st.success(f"Novi godišnji dani dodijeljeni svima za {tekuca_godina}. godinu!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Greška pri dodjeljivanju: {str(e)}")

        with col2:
            if st.button("Izvrši konverziju 30.06. (neiskorišteni → slobodni dani)"):
                try:
                    korisnici_response = supabase.table("korisnici").select("id,ime_prezime,godisnji_dani,odobreni_dani_po_godini,slobodni_dani").execute()
                    korisnici_df = pd.DataFrame(korisnici_response.data or [])

                    for _, kor in korisnici_df.iterrows():
                        kor_id = kor["id"]
                        trenutni_saldo = kor.get("godisnji_dani") or 0
                        odobreni = kor.get("odobreni_dani_po_godini") or 20
                        slobodni = kor.get("slobodni_dani") or 0

                        if trenutni_saldo > odobreni:
                            razlika = trenutni_saldo - odobreni
                            novi_slobodni = slobodni + razlika
                            supabase.table("korisnici").update({
                                "godisnji_dani": odobreni,
                                "slobodni_dani": novi_slobodni
                            }).eq("id", kor_id).execute()

                            st.write(f"{kor['ime_prezime']}: prebačeno {razlika} dana u slobodne (novi saldo: {novi_slobodni})")

                    st.success("Konverzija 30.06. izvršena za sve korisnike!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Greška pri konverziji: {str(e)}")

    # Prikaz i uređivanje/brisanje unosa + PDF
    st.subheader("Svi unosi (uređivanje, brisanje i PDF)")
    try:
        odmori_response = supabase.table("odmori")\
            .select("*, korisnici!inner(ime_prezime)")\
            .order("datum_od", desc=True)\
            .execute()

        df_odmori = pd.DataFrame(odmori_response.data or [])

        if not df_odmori.empty:
            df_odmori["korisnik_ime"] = df_odmori["korisnici"].apply(lambda x: x["ime_prezime"] if isinstance(x, dict) and "ime_prezime" in x else "Nepoznato")
            df_odmori = df_odmori.drop(columns=["korisnici"])

            df_odmori["Obriši"] = False
            df_odmori["Izvezi PDF"] = False

            if tip_korisnika != "administrator":
                df_odmori = df_odmori[df_odmori["korisnik_id"] == prijavljeni_korisnik_id]

            edited_df = st.data_editor(
                df_odmori[["id", "korisnik_ime", "datum_od", "datum_do", "tip", "napomena", "unio_korisnik", "created_at", "Obriši", "Izvezi PDF"]],
                column_config={
                    "id": st.column_config.NumberColumn("ID", disabled=True),
                    "korisnik_ime": st.column_config.TextColumn("Korisnik", disabled=True),
                    "created_at": st.column_config.TextColumn("Kreirano", disabled=True),
                    "unio_korisnik": st.column_config.TextColumn("Unio", disabled=True),
                    "Obriši": st.column_config.CheckboxColumn("Obriši", default=False),
                    "Izvezi PDF": st.column_config.CheckboxColumn("Izvezi PDF", default=False)
                },
                hide_index=True,
                use_container_width=True,
                num_rows="fixed",
                key="odmori_editor"
            )

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Spremi izmjene i obriši označene"):
                    to_delete = []
                    for idx, row in edited_df.iterrows():
                        original_row = df_odmori.loc[idx]

                        if row["Obriši"]:
                            to_delete.append(row["id"])
                            log = {
                                "action": "delete",
                                "unio_korisnik": st.session_state.user.get("korisničko_ime", "Nepoznato"),
                                "old_data": original_row[["datum_od", "datum_do", "tip", "napomena"]].to_json(),
                                "created_at": datetime.now(TZ).isoformat()
                            }
                            supabase.table("log_odmori").insert(log).execute()

                            used_before = get_used_days_for_user(original_row["korisnik_id"])
                            supabase.table("odmori").delete().eq("id", row["id"]).execute()
                            used_after = get_used_days_for_user(original_row["korisnik_id"])
                            razlika = used_before - used_after

                            if original_row["tip"] == "Godišnji odmor":
                                novi_saldo = preostalo_godisnje + razlika
                                supabase.table("korisnici").update({"godisnji_dani": max(0, int(novi_saldo))}).eq("id", original_row["korisnik_id"]).execute()
                            elif original_row["tip"] == "Slobodni dan":
                                novi_slobodni = preostalo_slobodnih + razlika
                                supabase.table("korisnici").update({"slobodni_dani": max(0, int(novi_slobodni))}).eq("id", original_row["korisnik_id"]).execute()

                            continue

                        changed_fields = {}
                        for field in ["datum_od", "datum_do", "tip", "napomena"]:
                            if row[field] != original_row[field]:
                                changed_fields[field] = {
                                    "old": original_row[field],
                                    "new": row[field]
                                }

                        if changed_fields:
                            update_data = {k: row[k] for k in changed_fields}
                            supabase.table("odmori").update(update_data).eq("id", row["id"]).execute()
                            log = {
                                "action": "update",
                                "unio_korisnik": st.session_state.user.get("korisničko_ime", "Nepoznato"),
                                "old_data": {k: v["old"] for k, v in changed_fields.items()},
                                "new_data": {k: v["new"] for k, v in changed_fields.items()},
                                "created_at": datetime.now(TZ).isoformat()
                            }
                            supabase.table("log_odmori").insert(log).execute()

                            if "tip" in changed_fields or "datum_od" in changed_fields or "datum_do" in changed_fields:
                                used_before = get_used_days_for_user(original_row["korisnik_id"], exclude_id=row["id"])
                                used_after = get_used_days_for_user(original_row["korisnik_id"])
                                razlika = used_before - used_after

                                if original_row["tip"] == row["tip"]:
                                    if original_row["tip"] == "Godišnji odmor":
                                        novi_saldo = preostalo_godisnje + razlika
                                        supabase.table("korisnici").update({"godisnji_dani": max(0, int(novi_saldo))}).eq("id", original_row["korisnik_id"]).execute()
                                    elif original_row["tip"] == "Slobodni dan":
                                        novi_slobodni = preostalo_slobodnih + razlika
                                        supabase.table("korisnici").update({"slobodni_dani": max(0, int(novi_slobodni))}).eq("id", original_row["korisnik_id"]).execute()
                                else:
                                    if original_row["tip"] == "Godišnji odmor":
                                        supabase.table("korisnici").update({"godisnji_dani": preostalo_godisnje + used_before}).eq("id", original_row["korisnik_id"]).execute()
                                    elif original_row["tip"] == "Slobodni dan":
                                        supabase.table("korisnici").update({"slobodni_dani": preostalo_slobodnih + used_before}).eq("id", original_row["korisnik_id"]).execute()

                                    if row["tip"] == "Godišnji odmor":
                                        novi_saldo = preostalo_godisnje - used_after
                                        supabase.table("korisnici").update({"godisnji_dani": max(0, int(novi_saldo))}).eq("id", original_row["korisnik_id"]).execute()
                                    elif row["tip"] == "Slobodni dan":
                                        novi_slobodni = preostalo_slobodnih - used_after
                                        supabase.table("korisnici").update({"slobodni_dani": max(0, int(novi_slobodni))}).eq("id", original_row["korisnik_id"]).execute()

                    if to_delete:
                        for rec_id in to_delete:
                            supabase.table("odmori").delete().eq("id", rec_id).execute()

                    st.success("Izmjene i brisanja spremljeni! Saldo ažuriran.")
                    st.rerun()

            with col2:
                if st.button("Izvezi označene u PDF"):
                    from reportlab.lib.pagesizes import A4
                    from reportlab.pdfgen import canvas
                    from reportlab.lib.units import mm
                    from reportlab.lib.colors import black
                    from pypdf import PdfReader, PdfWriter
                    for idx, row in edited_df.iterrows():
                        if row["Izvezi PDF"]:
                            original_row = df_odmori.loc[idx]
                            if original_row["tip"] == "Godišnji odmor":
                                template_file = "go1.pdf"
                            elif original_row["tip"] == "Slobodni dan":
                                template_file = "sd.pdf"
                            else:
                                st.warning(f"Nevažeći tip za PDF: {original_row['tip']}")
                                continue
                            overlay_buffer = io.BytesIO()
                            c = canvas.Canvas(overlay_buffer, pagesize=A4)
                            width, height = A4
                            c.setFont('Helvetica', 12)
                            ime_prezime = original_row["korisnik_ime"]
                            broj_dana = str(calculate_working_days(original_row["datum_od"], original_row["datum_do"], holidays_dict.get(tekuca_godina, [])))
                            datum_od = datetime.fromisoformat(original_row["datum_od"]).strftime("%d.%m.%Y.")
                            datum_do = datetime.fromisoformat(original_row["datum_do"]).strftime("%d.%m.%Y.")
                            prvi_radni_dan = find_next_working_day(original_row["datum_do"], holidays_dict.get(tekuca_godina, []))
                            datum_podnosenja = datetime.fromisoformat(original_row["created_at"]).strftime("%d.%m.%Y.")
                            c.drawCentredString(width / 2 - 45*mm, height - 129*mm, ime_prezime)
                            c.drawCentredString(width / 2 - 5*mm, height - 144*mm, broj_dana)
                            c.drawCentredString(width / 2 - 4*mm, height - 164*mm, datum_od)
                            c.drawCentredString(width / 2 - 60*mm, height - 184*mm, datum_do)
                            c.drawCentredString(width / 2 + 44*mm, height - 184*mm, prvi_radni_dan)
                            c.drawCentredString(width / 2 - 60*mm, height - 211*mm, datum_podnosenja)
                            c.save()
                            overlay_buffer.seek(0)
                            template_reader = PdfReader(template_file)
                            overlay_reader = PdfReader(overlay_buffer)
                            writer = PdfWriter()
                            template_page = template_reader.pages[0]
                            overlay_page = overlay_reader.pages[0]
                            template_page.merge_page(overlay_page)
                            writer.add_page(template_page)
                            output_buffer = io.BytesIO()
                            writer.write(output_buffer)
                            output_buffer.seek(0)
                            st.download_button(
                                label=f"Preuzmi PDF za unos ID {row['id']} ({original_row['tip']})",
                                data=output_buffer,
                                file_name=f"{original_row['tip']}_{row['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                                mime="application/pdf",
                                key=f"pdf_download_{row['id']}"
                            )
        else:
            st.info("Još nema unosa.")
    except Exception as e:
        st.error(f"Greška pri dohvaćanju/uređivanju unosa: {str(e)}")

    # Pregled po korisniku
    st.subheader("Pregled po korisniku")
    try:
        if 'df_odmori' in locals() and not df_odmori.empty:
            if tip_korisnika != "administrator":
                df_odmori = df_odmori[df_odmori["korisnik_id"] == prijavljeni_korisnik_id]

            praznici_response = supabase.table("praznici").select("datum").execute()
            holidays = {datetime.fromisoformat(p["datum"]).date() for p in praznici_response.data or []}

            df_odmori["broj_dana"] = df_odmori.apply(lambda row: calculate_working_days(row["datum_od"], row["datum_do"], holidays), axis=1)

            summary = df_odmori.groupby("korisnik_ime").agg(
                ukupno_dana=("broj_dana", "sum"),
                broj_unosa=("id", "count")
            ).reset_index()

            st.dataframe(summary, use_container_width=True, hide_index=True)
            st.info("Napomena: Broj dana isključuje vikende i praznike/blagdane.")
        else:
            st.info("Nema podataka za pregled.")
    except Exception as e:
        st.error(f"Greška pri sumiranju: {str(e)}")

    # Log izmjena i brisanja
    st.subheader("Log izmjena i brisanja")
    try:
        log_response = supabase.table("log_odmori")\
            .select("*")\
            .order("created_at", desc=True)\
            .execute()

        df_log = pd.DataFrame(log_response.data or [])

        if not df_log.empty:
            if 'old_data' in df_log.columns:
                df_log['old_data'] = df_log['old_data'].apply(
                    lambda x: json.dumps(x, ensure_ascii=False, indent=2) if isinstance(x, (dict, list)) else str(x)
                )
            if 'new_data' in df_log.columns:
                df_log['new_data'] = df_log['new_data'].apply(
                    lambda x: json.dumps(x, ensure_ascii=False, indent=2) if isinstance(x, (dict, list)) else str(x)
                )

            st.dataframe(
                df_log[["action", "unio_korisnik", "old_data", "new_data", "created_at"]],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Još nema log zapisa.")
    except Exception as e:
        st.error(f"Greška pri dohvaćanju loga: {str(e)}")