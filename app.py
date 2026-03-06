import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
from zoneinfo import ZoneInfo
import time
import io
import json
import calendar
import matplotlib.pyplot as plt
from datetime import timedelta
from datetime import date
import bcrypt

st.set_page_config(page_title="Sustav zahtjeva", layout="wide")

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
if "temp_odmor" not in st.session_state:
    st.session_state.temp_odmor = None
if "form_reset" not in st.session_state:
    st.session_state.form_reset = False
if "edit_korisnik_id" not in st.session_state:
    st.session_state.edit_korisnik_id = None
if "novi_korisnik_form_shown" not in st.session_state:
    st.session_state.novi_korisnik_form_shown = False
if "korisnici_search" not in st.session_state:
    st.session_state.korisnici_search = ""

# Callback funkcije za search
def on_korisnici_search_change():
    st.session_state.korisnici_search = st.session_state.korisnici_search_input

# Funkcija za autentifikaciju
def authenticate_user(username, password):
    try:
        user_response = supabase.table("korisnici")\
            .select("*")\
            .eq("korisničko_ime", username.strip())\
            .single()\
            .execute()
        
        user = user_response.data
        
        if not user:
            st.error("Korisnik nije pronađen")
            return None
        
        stored = user['lozinka'].strip()
        
        try:
            if bcrypt.checkpw(password.strip().encode('utf-8'), stored.encode('utf-8')):
                return user
        except:
            pass
        
        if stored == password.strip():
            return user
        
        st.error("Lozinka se ne podudara")
        return None
        
    except Exception as e:
        st.error(f"Greška pri autentifikaciji: {str(e)}")
        return None

# Login stranica
if st.session_state.stranica == "login":
    st.title("Prijava u sustav zahtjeva")

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
                    st.session_state.stranica = "godisnji"  # početna stranica
                    st.success("Uspješna prijava!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Korisničko ime ne postoji ili lozinka nije ispravna.")
    
    st.stop()

# Sidebar – SAMO DVIJE STRANICE
st.sidebar.title(f"Dobro došli, {st.session_state.user.get('ime_prezime', 'Nepoznato')}")

stranice = ["Godišnji odmor", "Korisnici"]
izbor = st.sidebar.selectbox("Odaberi stranicu", stranice)

if izbor == "Godišnji odmor":
    st.session_state.stranica = "godisnji"
elif izbor == "Korisnici":
    st.session_state.stranica = "korisnici"

if st.sidebar.button("Odjavi se"):
    st.session_state.user = None
    st.session_state.stranica = "login"
    st.rerun()

# ────────────────────────────────────────────────
# GLAVNI SADRŽAJ – SAMO DVIJE STRANICE
# ────────────────────────────────────────────────

if st.session_state.stranica == "godisnji":
    st.title("🏖️ Godišnji odmor i slobodni dani")

    # ────────────────────────────────────────────────
    # TVOJ ORIGINALNI BLOK ZA GODIŠNJI ODMOR – VRATILI SMO GA U CIJELOSTI
    # ────────────────────────────────────────────────
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

    # Funkcija za pronalazak prvog radnog dana nakon završetka
    def find_next_working_day(end_date_str, holidays):
        end = datetime.fromisoformat(end_date_str).date()
        current = end + timedelta(days=1)
        while current.weekday() >= 5 or current in holidays:
            current += timedelta(days=1)
        return current.strftime("%d.%m.%Y.")

    # Računa stvarni broj iskorištenih dana za korisnika
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

    # Inicijalizacija session_state varijabli
    if "temp_odmor" not in st.session_state:
        st.session_state.temp_odmor = None
    if "form_reset" not in st.session_state:
        st.session_state.form_reset = False

    # Ručno definirani praznici (možeš proširiti)
    holidays_dict = {
        2026: [date(2026, 1, 1), date(2026, 1, 6), date(2026, 4, 5), date(2026, 4, 6), date(2026, 5, 1), date(2026, 5, 30), date(2026, 6, 22), date(2026, 8, 15), date(2026, 11, 1), date(2026, 11, 18), date(2026, 12, 25), date(2026, 12, 26)],
        # Dodaj ostale godine po potrebi
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

    # Odabir korisnika (samo admin)
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

    # Forma za dodavanje
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
            if tip_odmora == "Godišnji odmor" and broj_dana > preostalo_godisnje:
                st.error(f"Premašuješ preostale godišnje dane! Preostalo: {preostalo_godisnje}, tražiš: {broj_dana}")
                st.stop()
            elif tip_odmora == "Slobodni dan" and broj_dana > preostalo_slobodnih:
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

    if st.session_state.form_reset:
        st.session_state.form_reset = False
        st.rerun()

    # Administrativne radnje – SAMO ZA ADMINA
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

    # Prikaz unosa + uređivanje + PDF
    st.subheader("Svi unosi godišnjeg / slobodnih dana (uređivanje, brisanje i PDF)")
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

elif st.session_state.stranica == "korisnici":
    st.title("Administracija - Korisnici")
    if "edit_korisnik_id" not in st.session_state:
        st.session_state.edit_korisnik_id = None
    try:
        response = supabase.table("korisnici").select("*").execute()
        df_korisnici = pd.DataFrame(response.data or [])
    except Exception as e:
        st.error(f"Greška pri dohvaćanju korisnika: {str(e)}")
        st.stop()
    if not df_korisnici.empty:
        col1, col2 = st.columns([6, 4])
        with col1:
            st.subheader("Postojeći korisnici")
        with col2:
            st.text_input(
                "Pretraži po svim stupcima",
                value=st.session_state.get("korisnici_search", ""),
                key="korisnici_search_input",
                placeholder="upiši korisničko ime, ime i prezime, tip...",
                on_change=on_korisnici_search_change
            )
        df_display = df_korisnici.copy()
        if st.session_state.get("korisnici_search", ""):
            search_term = str(st.session_state.korisnici_search).strip().lower()
            mask = df_display.astype(str).apply(lambda x: x.str.lower().str.contains(search_term), axis=1).any(axis=1)
            df_display = df_display[mask]
        if df_display.empty and st.session_state.get("korisnici_search", ""):
            st.info("Ništa nije pronađeno.")
        elif df_display.empty:
            st.info("Još nema korisnika u bazi.")
        df_display["Obriši"] = False
        df_display["Uredi"] = False
        df_display["lozinka"] = df_display["lozinka"].apply(lambda x: "******" if x else "")
        edited_df = st.data_editor(
            df_display,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key="korisnici_editor",
            column_config={
                "korisničko_ime": st.column_config.TextColumn("Korisničko ime"),
                "ime_prezime": st.column_config.TextColumn("Ime i prezime"),
                "tip_korisnika": st.column_config.TextColumn("Tip korisnika"),
                "lozinka": st.column_config.TextColumn("Lozinka", disabled=True),
                "aktivan": st.column_config.CheckboxColumn("Aktivan"),
                "Obriši": st.column_config.CheckboxColumn("Obriši"),
                "Uredi": st.column_config.CheckboxColumn("Uredi"),
            }
        )
        for row in edited_df.to_dict("records"):
            if row["Uredi"]:
                st.session_state.edit_korisnik_id = row["id"]
                st.rerun()
        if st.button("💾 Spremi promjene", type="primary"):
            for row in edited_df.to_dict("records"):
                row_id = row["id"]
                if row["Obriši"]:
                    supabase.table("korisnici").delete().eq("id", row_id).execute()
            st.success("Promjene spremljene! Označeni korisnici obrisani.")
            st.rerun()
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
        st.button("🔄 Osvježi", on_click=st.rerun)
        if st.session_state.edit_korisnik_id:
            edit_row = df_korisnici[df_korisnici["id"] == st.session_state.edit_korisnik_id].iloc[0]
            with st.expander(f"Uređivanje korisnika: {edit_row['korisničko_ime']} ({edit_row['ime_prezime']})", expanded=True):
                with st.form("edit_korisnik_form", clear_on_submit=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        edit_ime_prezime = st.text_input("Ime i prezime", value=edit_row["ime_prezime"])
                        edit_korisničko_ime = st.text_input("Korisničko ime", value=edit_row["korisničko_ime"])
                        edit_lozinka = st.text_input("Nova lozinka (ostavi prazno ako ne mijenjaš)", type="password", value="")
                        edit_tip_korisnika = st.selectbox("Tip korisnika", [
                            "administrator", "ured", "skladištar", "terenac", "gost"
                        ], index=["administrator", "ured", "skladištar", "terenac", "gost"].index(edit_row["tip_korisnika"]))
                        edit_godisnji_dani = st.number_input("Godišnji dani (po godini)", value=edit_row.get("godisnji_dani", 20), min_value=0)
                        edit_slobodni_dani = st.number_input("Slobodni dani", value=edit_row.get("slobodni_dani", 0), min_value=0)
                    with col2:
                        st.markdown("**Prava**")
                        edit_prava = st.multiselect(
                            "Odaberi prava (može više)",
                            [
                                "NARUDŽBE - ADMINISTRATOR",
                                "PROIZVODI - ADMINISTRATOR",
                                "DOBAVLJAČI - ADMINISTRATOR",
                                "KORISNICI - ADMINISTRATOR",
                                "SKLADIŠTE - ADMINISTRATOR",
                                "IZVJEŠTAJ - SVE",
                                "IZVJEŠTAJ - PRODAJA"
                            ],
                            default=edit_row["prava"] if isinstance(edit_row["prava"], list) else []
                        )
                        st.markdown("**Odaberi koje skladište može vidjeti:**")
                        edit_skladišta = st.multiselect(
                            "Skladišta",
                            [
                                "Osijek - Glavno skladište",
                                "Skladište Split",
                                "Skladište Pula",
                                "Skladište Zagreb",
                                "Skladište Rijeka"
                            ],
                            default=edit_row["skladišta"] if isinstance(edit_row["skladišta"], list) else []
                        )
                        edit_aktivan = st.checkbox("Aktivan", value=edit_row["aktivan"])
                    col_submit, col_cancel = st.columns(2)
                    with col_submit:
                        if st.form_submit_button("Spremi promjene"):
                            update_data = {
                                "ime_prezime": edit_ime_prezime,
                                "korisničko_ime": edit_korisničko_ime,
                                "tip_korisnika": edit_tip_korisnika,
                                "aktivan": edit_aktivan,
                                "prava": edit_prava,
                                "skladišta": edit_skladišta,
                                "godisnji_dani": edit_godisnji_dani,
                                "slobodni_dani": edit_slobodni_dani
                            }
                            if edit_lozinka:
                                update_data["lozinka"] = edit_lozinka
                            supabase.table("korisnici").update(update_data).eq("id", st.session_state.edit_korisnik_id).execute()
                            st.success("Korisnik ažuriran!")
                            st.session_state.edit_korisnik_id = None
                            st.rerun()
                    with col_cancel:
                        if st.form_submit_button("Odustani"):
                            st.session_state.edit_korisnik_id = None
                            st.rerun()
    else:
        st.info("Još nema korisnika u bazi.")
    if st.button("➕ Novi korisnik", type="primary", key="novi_korisnik_gumb"):
        st.session_state.novi_korisnik_form_shown = True
        st.rerun()
    if "novi_korisnik_form_shown" not in st.session_state:
        st.session_state.novi_korisnik_form_shown = False
    if st.session_state.novi_korisnik_form_shown:
        with st.form("novi_korisnik_form", clear_on_submit=False):
            st.markdown("**Novi korisnik**")
            col1, col2 = st.columns(2)
            with col1:
                ime_prezime = st.text_input("Ime i prezime", key="ime_prezime_input")
                korisničko_ime = st.text_input("Korisničko ime", key="korisničko_ime_input")
                lozinka = st.text_input("Lozinka", type="password", key="lozinka_input")
                tip_korisnika = st.selectbox("Tip korisnika", [
                    "administrator", "ured", "skladištar", "terenac", "gost"
                ], key="tip_korisnika_input")
                godisnji_dani = st.number_input("Godišnji dani (po godini)", value=20, min_value=0, key="godisnji_dani_input")
                slobodni_dani = st.number_input("Slobodni dani", value=0, min_value=0, key="slobodni_dani_input")
            with col2:
                st.markdown("**Prava**")
                prava = st.multiselect(
                    "Odaberi prava (može više)",
                    [
                        "NARUDŽBE - ADMINISTRATOR",
                        "PROIZVODI - ADMINISTRATOR",
                        "DOBAVLJAČI - ADMINISTRATOR",
                        "KORISNICI - ADMINISTRATOR",
                        "SKLADIŠTE - ADMINISTRATOR",
                        "IZVJEŠTAJ - SVE",
                        "IZVJEŠTAJ - PRODAJA"
                    ],
                    key="prava_input"
                )
                st.markdown("**Odaberi koje skladište može vidjeti:**")
                skladišta = st.multiselect(
                    "Skladišta",
                    [
                        "Osijek - Glavno skladište",
                        "Skladište Split",
                        "Skladište Pula",
                        "Skladište Zagreb",
                        "Skladište Rijeka"
                    ],
                    key="skladišta_input"
                )
            col_submit, col_cancel = st.columns(2)
            with col_submit:
                if st.form_submit_button("Spremi", key="spremi_form"):
                    if korisničko_ime and ime_prezime and lozinka:
                        novi = {
                            "korisničko_ime": korisničko_ime,
                            "ime_prezime": ime_prezime,
                            "lozinka": lozinka,
                            "tip_korisnika": tip_korisnika,
                            "aktivan": True,
                            "prava": prava,
                            "skladišta": skladišta,
                            "godisnji_dani": godisnji_dani,
                            "slobodni_dani": slobodni_dani
                        }
                        try:
                            response = supabase.table("korisnici").insert(novi).execute()
                            st.success(f"Korisnik dodan! ID: {response.data[0]['id'] if response.data else 'Nepoznato'}")
                            st.session_state.novi_korisnik_form_shown = False
                            st.rerun()
                        except Exception as e:
                            st.error(f"Greška pri dodavanju: {str(e)}")
                    else:
                        st.error("Korisničko ime, ime i prezime te lozinka su obavezni!")
            with col_cancel:
                if st.form_submit_button("Odustani", key="odustani_form"):
                    st.session_state.novi_korisnik_form_shown = False
                    st.rerun()