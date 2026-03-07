import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
import time
import io
import json
import calendar
import matplotlib.pyplot as plt
import bcrypt
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.colors import black
from pypdf import PdfReader, PdfWriter

st.set_page_config(page_title="Sustav zahtjeva", layout="wide")

# Supabase konekcija – PRIVREMENO koristimo service_role key (bypass RLS)
SUPABASE_URL = "https://vwekjvazuexwoglxqrtg.supabase.co"

# OVDJE zalijepi TOČAN service_role ključ iz Supabase dashboarda
# Settings → API → Project API keys → service_role (cijeli eyJhbGciOi... string)
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ3ZWtqdmF6dWV4d29nbHhxcnRnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjAzMzI5NywiZXhwIjoyMDg3NjA5Mjk3fQ.Gz683u3oZE5x_NoFeeRJA_VaSb0uf3G1aLUX1uE2CfA"

# Provjera da ključ nije prazan (debug)
if not SUPABASE_SERVICE_KEY or len(SUPABASE_SERVICE_KEY) < 50:
    st.error("SUPABASE_SERVICE_KEY je prazan ili prekratak – provjeri da si zalijepio cijeli ključ!")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

TZ = ZoneInfo("Europe/Zagreb")

# Ostatak tvog koda ostaje isti...
# (session state, authenticate_user funkcija, login stranica, sidebar, funkcije itd.)

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
        # Dohvati BEZ .single() – dozvoli 0 ili 1 redak
        response = supabase.table("korisnici")\
            .select("*")\
            .eq("korisničko_ime", username.strip())\
            .execute()
        
        users = response.data or []
        
        if not users:
            st.error("Korisnik nije pronađen")
            return None
        
        # Uzmi prvog (trebao bi biti samo jedan)
        user = users[0]
        
        stored = user.get('lozinka', '').strip()
        
        # Provjeri bcrypt hash (ako postoji)
        try:
            if bcrypt.checkpw(password.strip().encode('utf-8'), stored.encode('utf-8')):
                return user
        except ValueError:
            # Ako nije bcrypt – provjeri plain tekst (stari način)
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
                    st.session_state.stranica = "godisnji"
                    st.success("Uspješna prijava!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Korisničko ime ne postoji ili lozinka nije ispravna.")
    
    st.stop()

# ────────────────────────────────────────────────
# SIDEBAR – PRAVA PRISTUPA
# ────────────────────────────────────────────────
tip_korisnika = st.session_state.user.get("tip_korisnika", "korisnik") if st.session_state.user else None

stranice = ["Godišnji odmor"]
# Popis uloga koje smiju vidjeti stranicu Korisnici
dozvoljene_za_korisnike = ["administrator", "ured"]

if tip_korisnika in dozvoljene_za_korisnike:
    stranice.append("Korisnici")

st.sidebar.title(f"Dobro došli, {st.session_state.user.get('ime_prezime', 'Nepoznato') if st.session_state.user else 'Neprijavljen'}")
izbor = st.sidebar.selectbox("Odaberi stranicu", stranice)

if izbor == "Godišnji odmor":
    st.session_state.stranica = "godisnji"
elif izbor == "Korisnici" 
    st.session_state.stranica = "korisnici"

if st.sidebar.button("Odjavi se"):
    st.session_state.user = None
    st.session_state.stranica = "login"
    st.rerun()

# ────────────────────────────────────────────────
# FUNKCIJE
# ────────────────────────────────────────────────
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

def find_next_working_day(end_date_str, holidays):
    end = datetime.fromisoformat(end_date_str).date()
    current = end + timedelta(days=1)
    while current.weekday() >= 5 or current in holidays:
        current += timedelta(days=1)
    return current.strftime("%d.%m.%Y.")

def get_current_saldo(korisnik_id):
    try:
        response = supabase.table("korisnici")\
            .select("godisnji_dani,slobodni_dani")\
            .eq("id", korisnik_id)\
            .single()\
            .execute()
        data = response.data
        return data.get("godisnji_dani", 0), data.get("slobodni_dani", 0)
    except:
        return 0, 0

# ────────────────────────────────────────────────
# GODIŠNJI ODMOR
# ────────────────────────────────────────────────
if st.session_state.stranica == "godisnji":
    st.title("🏖️ Godišnji odmor i slobodni dani")

    holidays_dict = {
        2026: [date(2026, 1, 1), date(2026, 1, 6), date(2026, 4, 5), date(2026, 4, 6), date(2026, 5, 1), date(2026, 5, 30), date(2026, 6, 22), date(2026, 8, 15), date(2026, 11, 1), date(2026, 11, 18), date(2026, 12, 25), date(2026, 12, 26)],
        # Dodaj ostale godine po potrebi
    }

    try:
        korisnici_response = supabase.table("korisnici").select("id,ime_prezime,godisnji_dani,slobodni_dani,odobreni_dani_po_godini").eq("aktivan", True).execute()
        korisnici = korisnici_response.data or []
        korisnik_options = {k["ime_prezime"]: k for k in korisnici}
    except Exception as e:
        st.error(f"Greška pri dohvaćanju korisnika: {str(e)}")
        korisnik_options = {}

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

    tekuca_godina = datetime.now().year

    # Odabir korisnika – SAMO ADMIN vidi padajući izbornik
    if tip_korisnika == "administrator":
        korisnik_ime = st.selectbox("Odaberi korisnika za unos", list(korisnik_options.keys()),
                                    index=list(korisnik_options.keys()).index(prijavljeni_korisnik_ime) if prijavljeni_korisnik_ime in korisnik_options else 0,
                                    key="odmor_selected_korisnik")
        selected_korisnik = korisnik_options.get(korisnik_ime, {})
        korisnik_id = selected_korisnik.get("id", prijavljeni_korisnik_id)
    else:
        korisnik_id = prijavljeni_korisnik_id
        korisnik_ime = prijavljeni_korisnik_ime
        st.text_input("Korisnik", value=korisnik_ime, disabled=True)

    # Dohvati saldo
    preostalo_godisnje, preostalo_slobodnih = get_current_saldo(korisnik_id)

    st.markdown(f"**Preostalo godišnjih dana za {tekuca_godina} ({korisnik_ime}): {preostalo_godisnje}**")
    st.markdown(f"**Preostalo slobodnih dana ({korisnik_ime}): {preostalo_slobodnih}**")

    # Forma za dodavanje – svi vide
    with st.form("dodaj_odmor_form", clear_on_submit=True):
        st.subheader("Dodaj novi unos godišnjeg / slobodnog dana")
        col1, col2 = st.columns(2)
        datum_od_input = col1.date_input("Datum od *", value=None, key="odmor_datum_od")
        datum_do_input = col2.date_input("Datum do *", value=None, key="odmor_datum_do")
        tip_odmora = st.selectbox("Tip odsustva *", [""] + ["Godišnji odmor", "Slobodni dan", "Bolovanje", "Ostalo"], index=0, key="odmor_tip")
        napomena = st.text_area("Napomena (opcionalno)", key="odmor_napomena")
        submitted = st.form_submit_button("Dodaj unos", type="primary")

    if submitted:
        if not korisnik_id or not datum_od_input or not datum_do_input or datum_do_input < datum_od_input or tip_odmora == "":
            st.error("Molimo popunite sva obavezna polja ispravno!")
        else:
            datum_od = datum_od_input
            datum_do = datum_do_input
            broj_dana = calculate_working_days(datum_od.isoformat(), datum_do.isoformat(), holidays_dict.get(tekuca_godina, []))
            preostalo_godisnje, preostalo_slobodnih = get_current_saldo(korisnik_id)
            if tip_odmora == "Godišnji odmor" and broj_dana > preostalo_godisnje:
                st.error(f"Premašuješ preostale godišnje dane! Preostalo: {preostalo_godisnje}")
            elif tip_odmora == "Slobodni dan" and broj_dana > preostalo_slobodnih:
                st.error(f"Premašuješ preostale slobodne dane! Preostalo: {preostalo_slobodnih}")
            else:
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
                        st.error("Ista osoba već ima upis na preklapajuće datume!")
                    elif preklapanja > 0:
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
                        preostalo_godisnje, preostalo_slobodnih = get_current_saldo(korisnik_id)
                        if tip_odmora == "Godišnji odmor":
                            novi_saldo = preostalo_godisnje - broj_dana
                            supabase.table("korisnici").update({"godisnji_dani": max(0, int(novi_saldo))}).eq("id", korisnik_id).execute()
                        elif tip_odmora == "Slobodni dan":
                            novi_slobodni = preostalo_slobodnih - broj_dana
                            supabase.table("korisnici").update({"slobodni_dani": max(0, int(novi_slobodni))}).eq("id", korisnik_id).execute()
                        st.success("Unos dodan!")
                        st.session_state.form_reset = True
                        st.rerun()
                except Exception as e:
                    st.error(f"Greška: {str(e)}")

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
                st.error("Ista osoba već ima upis na preklapajuće datume!")
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
                preostalo_godisnje, preostalo_slobodnih = get_current_saldo(korisnik_id)
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
            st.error(f"Greška: {str(e)}")

    if st.session_state.form_reset:
        st.session_state.form_reset = False
        st.rerun()

    # TABLICA UNOSA – FILTRIRANA ZA NE-ADMINA
    st.subheader("Svi unosi godišnjeg / slobodnih dana (uređivanje, brisanje i PDF)")
    try:
        query = supabase.table("odmori").select("*, korisnici!inner(ime_prezime)").order("datum_od", desc=True)
        if tip_korisnika != "administrator":
            query = query.eq("korisnik_id", prijavljeni_korisnik_id)
        odmori_response = query.execute()
        df_odmori = pd.DataFrame(odmori_response.data or [])
        if not df_odmori.empty:
            df_odmori["korisnik_ime"] = df_odmori["korisnici"].apply(lambda x: x["ime_prezime"] if isinstance(x, dict) else "Nepoznato")
            df_odmori = df_odmori.drop(columns=["korisnici"])
            df_odmori["Obriši"] = False
            df_odmori["Izvezi PDF"] = False
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
                            broj_dana = calculate_working_days(original_row["datum_od"], original_row["datum_do"], holidays_dict.get(tekuca_godina, []))
                            preostalo_godisnje, preostalo_slobodnih = get_current_saldo(original_row["korisnik_id"])
                            if original_row["tip"] == "Godišnji odmor":
                                supabase.table("korisnici").update({"godisnji_dani": preostalo_godisnje + broj_dana}).eq("id", original_row["korisnik_id"]).execute()
                            elif original_row["tip"] == "Slobodni dan":
                                supabase.table("korisnici").update({"slobodni_dani": preostalo_slobodnih + broj_dana}).eq("id", original_row["korisnik_id"]).execute()
                            continue
                        changed_fields = {}
                        for field in ["datum_od", "datum_do", "tip", "napomena"]:
                            if row[field] != original_row[field]:
                                changed_fields[field] = row[field]
                        if changed_fields:
                            supabase.table("odmori").update(changed_fields).eq("id", row["id"]).execute()
                            log = {
                                "action": "update",
                                "unio_korisnik": st.session_state.user.get("korisničko_ime", "Nepoznato"),
                                "old_data": original_row[["datum_od", "datum_do", "tip", "napomena"]].to_json(),
                                "new_data": row[["datum_od", "datum_do", "tip", "napomena"]].to_json(),
                                "created_at": datetime.now(TZ).isoformat()
                            }
                            supabase.table("log_odmori").insert(log).execute()
                            if "datum_od" in changed_fields or "datum_do" in changed_fields or "tip" in changed_fields:
                                stari_broj = calculate_working_days(original_row["datum_od"], original_row["datum_do"], holidays_dict.get(tekuca_godina, []))
                                novi_broj = calculate_working_days(row["datum_od"], row["datum_do"], holidays_dict.get(tekuca_godina, []))
                                preostalo_godisnje, preostalo_slobodnih = get_current_saldo(original_row["korisnik_id"])
                                if original_row["tip"] == row["tip"]:
                                    if original_row["tip"] == "Godišnji odmor":
                                        razlika = stari_broj - novi_broj
                                        supabase.table("korisnici").update({"godisnji_dani": preostalo_godisnje + razlika}).eq("id", original_row["korisnik_id"]).execute()
                                    elif original_row["tip"] == "Slobodni dan":
                                        razlika = stari_broj - novi_broj
                                        supabase.table("korisnici").update({"slobodni_dani": preostalo_slobodnih + razlika}).eq("id", original_row["korisnik_id"]).execute()
                                else:
                                    if original_row["tip"] == "Godišnji odmor":
                                        supabase.table("korisnici").update({"godisnji_dani": preostalo_godisnje + stari_broj}).eq("id", original_row["korisnik_id"]).execute()
                                    elif original_row["tip"] == "Slobodni dan":
                                        supabase.table("korisnici").update({"slobodni_dani": preostalo_slobodnih + stari_broj}).eq("id", original_row["korisnik_id"]).execute()
                                    if row["tip"] == "Godišnji odmor":
                                        supabase.table("korisnici").update({"godisnji_dani": preostalo_godisnje - novi_broj}).eq("id", original_row["korisnik_id"]).execute()
                                    elif row["tip"] == "Slobodni dan":
                                        supabase.table("korisnici").update({"slobodni_dani": preostalo_slobodnih - novi_broj}).eq("id", original_row["korisnik_id"]).execute()
                    if to_delete:
                        for rec_id in to_delete:
                            supabase.table("odmori").delete().eq("id", rec_id).execute()
                    st.success("Izmjene spremljene! Saldo ažuriran.")
                    st.rerun()
            with col2:
                if st.button("Izvezi označene u PDF"):
                    for idx, row in edited_df.iterrows():
                        if row["Izvezi PDF"]:
                            original_row = df_odmori.loc[idx]
                            template_file = "go1.pdf" if original_row["tip"] == "Godišnji odmor" else "sd.pdf" if original_row["tip"] == "Slobodni dan" else None
                            if not template_file:
                                st.warning(f"Nevažeći tip: {original_row['tip']}")
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
                            datum_podnosenja = datetime.now(TZ).strftime("%d.%m.%Y.")
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
        st.error(f"Greška pri dohvaćanju unosa: {str(e)}")

    # Pregled po korisniku – filtriran za ne-admina
    st.subheader("Pregled po korisniku")
    try:
        query = supabase.table("odmori").select("*, korisnici!inner(ime_prezime)")
        if tip_korisnika != "administrator":
            query = query.eq("korisnik_id", prijavljeni_korisnik_id)
        df_odmori = pd.DataFrame(query.execute().data or [])
        if not df_odmori.empty:
            df_odmori["korisnik_ime"] = df_odmori["korisnici"].apply(lambda x: x["ime_prezime"] if isinstance(x, dict) else "Nepoznato")
            df_odmori = df_odmori.drop(columns=["korisnici"])
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

    # Kalendar – SVI VIDE SVE UNOSE
    st.subheader("Kalendar preklapanja")
    try:
        # Bez filtriranja – svi vide sve unose
        odmori_response = supabase.table("odmori")\
            .select("*, korisnici!inner(ime_prezime)")\
            .execute()
        df_odmori = pd.DataFrame(odmori_response.data or [])
        if not df_odmori.empty:
            df_odmori["korisnik_ime"] = df_odmori["korisnici"].apply(lambda x: x["ime_prezime"] if isinstance(x, dict) else "Nepoznato")
            df_odmori = df_odmori.drop(columns=["korisnici"])
            unique_users = df_odmori["korisnik_ime"].unique()
            color_map = {user: plt.cm.tab10(i / len(unique_users)) for i, user in enumerate(unique_users)}
            col_year, col_month = st.columns(2)
            year = col_year.selectbox("Godina", range(2025, 2041), index=datetime.now().year - 2025, key="kal_god")
            month = col_month.selectbox("Mjesec", range(1, 13), index=datetime.now().month - 1,
                                        format_func=lambda m: calendar.month_name[m], key="kal_mj")
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
            st.image(buf, caption="Kalendar odsustava (svi unosi vidljivi svima)")
        else:
            st.info("Nema unosa za prikaz kalendara.")
    except Exception as e:
        st.error(f"Greška pri prikazu kalendara: {str(e)}")

# ────────────────────────────────────────────────
# KORISNICI – SAMO ZA ADMINA
# ────────────────────────────────────────────────
elif st.session_state.stranica == "korisnici" and tip_korisnika == "administrator":
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
