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
import jwt  # pip install pyjwt

st.set_page_config(page_title="Sustav zahtjeva", layout="wide")

# Supabase konekcija – ANON KEY + custom JWT
SUPABASE_URL = "https://vwekjvazuexwoglxqrtg.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ3ZWtqdmF6dWV4d29nbHhxcnRnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzIwMzMyOTcsImV4cCI6MjA4NzYwOTI5N30.59dWvEsXOE-IochSguKYSw_mDwFvEXHmHbCW7Gy_tto"

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# JWT Secret – uzmi iz Supabase → Settings → API → JWT Settings → JWT Secret
# ČUVAJ TAJNO! Ne commitaj u git!
JWT_SECRET = "tvoj_jwt_secret_iz_supabase_dashboarda_ovdje"  # ← PROMIJENI OVO OBAVEZNO!

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
if "auth_token" not in st.session_state:
    st.session_state.auth_token = None

# Callback za search
def on_korisnici_search_change():
    st.session_state.korisnici_search = st.session_state.korisnici_search_input

# JWT generiranje
def generate_supabase_jwt(user):
    payload = {
        "sub": str(user["id"]),
        "korisničko_ime": user["korisničko_ime"],
        "aud": "authenticated",
        "role": "authenticated",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600 * 24 * 7,  # 7 dana
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

# Funkcija za autentifikaciju + JWT postavljanje
def authenticate_user(username, password):
    try:
        response = supabase.table("korisnici")\
            .select("*")\
            .eq("korisničko_ime", username.strip())\
            .execute()

        users = response.data or []

        if not users:
            st.error("Korisnik nije pronađen")
            return None

        user = users[0]

        stored = user.get('lozinka', '').strip()

        # Provjera bcrypt hash-a
        try:
            if bcrypt.checkpw(password.strip().encode('utf-8'), stored.encode('utf-8')):
                token = generate_supabase_jwt(user)
                st.session_state.auth_token = token
                supabase.postgrest.auth(token)  # postavi token za buduće upite
                return user
        except ValueError:
            pass

        # Fallback za plain lozinku
        if stored == password.strip():
            token = generate_supabase_jwt(user)
            st.session_state.auth_token = token
            supabase.postgrest.auth(token)
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
dozvoljene_za_korisnike = ["administrator", "ured"]
if tip_korisnika in dozvoljene_za_korisnike:
    stranice.append("Korisnici")

st.sidebar.title(f"Dobro došli, {st.session_state.user.get('ime_prezime', 'Nepoznato') if st.session_state.user else 'Neprijavljen'}")
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
# GODIŠNJI ODMOR (ispravljeno bez .single())
# ────────────────────────────────────────────────
if st.session_state.stranica == "godisnji":
    st.title("🏖️ Godišnji odmor i slobodni dani")

    holidays_dict = {
        2026: [date(2026, 1, 1), date(2026, 1, 6), date(2026, 4, 5), date(2026, 4, 6), date(2026, 5, 1), date(2026, 5, 30), date(2026, 6, 22), date(2026, 8, 15), date(2026, 11, 1), date(2026, 11, 18), date(2026, 12, 25), date(2026, 12, 26)],
        # Dodaj ostale godine po potrebi
    }

    # Dohvat svih korisnika za admina
    try:
        korisnici_response = supabase.table("korisnici").select("id,ime_prezime,godisnji_dani,slobodni_dani,odobreni_dani_po_godini").eq("aktivan", True).execute()
        korisnici = korisnici_response.data or []
        korisnik_options = {k["ime_prezime"]: k for k in korisnici}
    except Exception as e:
        st.error(f"Greška pri dohvaćanju korisnika: {str(e)}")
        korisnik_options = {}

    # Dohvat trenutnog korisnika – bez .single()
    try:
        user_response = supabase.table("korisnici")\
            .select("id,ime_prezime,godisnji_dani,slobodni_dani,odobreni_dani_po_godini")\
            .eq("korisničko_ime", st.session_state.user.get("korisničko_ime"))\
            .execute()
        
        if user_response.data:
            user_data = user_response.data[0]
        else:
            user_data = None
            st.warning("Nije pronađen tvoj profil u tablici korisnici. Neki podaci neće biti prikazani.")
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
    if user_data:
        preostalo_godisnje = user_data.get("godisnji_dani", 0)
        preostalo_slobodnih = user_data.get("slobodni_dani", 0)
    else:
        preostalo_godisnje = 0
        preostalo_slobodnih = 0

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

    # ... (ostatak tvog koda za potvrdu preklapanja, tablicu unosa, kalendar itd. ostaje isti – samo sam popravio dohvat profila)

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
            # ... (ostatak koda za spremanje izmjena, brisanje, PDF itd. ostaje isti)
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
# KORISNICI – SAMO ZA ADMINA (ispravljeno)
# ────────────────────────────────────────────────
elif st.session_state.stranica == "korisnici":
    st.title("Administracija - Korisnici")

    tip_korisnika = st.session_state.user.get("tip_korisnika", "nema uloge")
    trenutni_id = st.session_state.user.get("id")

    # Dohvat svih korisnika
    try:
        response = supabase.table("korisnici").select("*").execute()
        korisnici_data = response.data or []
    except Exception as e:
        st.error(f"Greška pri dohvaćanju korisnika: {str(e)}")
        korisnici_data = []

    # Search i prikaz tablice
    if korisnici_data:
        df = pd.DataFrame(korisnici_data)
        df["lozinka"] = "******"

        search_term = st.text_input(
            "Pretraži po svim stupcima",
            value=st.session_state.get("korisnici_search", ""),
            key="korisnici_search_input",
            placeholder="upiši korisničko ime, ime i prezime, tip...",
            on_change=on_korisnici_search_change
        )

        df_display = df.copy()
        if search_term:
            search_term = str(search_term).strip().lower()
            mask = df_display.astype(str).apply(lambda x: x.str.lower().str.contains(search_term), axis=1).any(axis=1)
            df_display = df_display[mask]

        if df_display.empty and search_term:
            st.info("Ništa nije pronađeno.")
        elif df_display.empty:
            st.info("Još nema korisnika u bazi.")
        else:
            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "id": None,
                    "created_at": st.column_config.DateTimeColumn("Kreiran", format="DD.MM.YYYY HH:mm"),
                    "updated_at": st.column_config.DateTimeColumn("Ažurirano", format="DD.MM.YYYY HH:mm"),
                    "korisničko_ime": st.column_config.TextColumn("Korisničko ime"),
                    "ime_prezime": st.column_config.TextColumn("Ime i prezime"),
                    "tip_korisnika": st.column_config.TextColumn("Tip korisnika"),
                    "lozinka": st.column_config.TextColumn("Lozinka", disabled=True),
                    "aktivan": st.column_config.CheckboxColumn("Aktivan"),
                    "godisnji_dani": st.column_config.NumberColumn("Godišnji dani"),
                    "slobodni_dani": st.column_config.NumberColumn("Slobodni dani"),
                }
            )
    else:
        st.info("Nema korisnika u bazi.")

    # Gumb za novog korisnika – SAMO ADMIN
    if tip_korisnika == "administrator":
        if st.button("➕ Novi korisnik", type="primary"):
            st.session_state.novi_korisnik_form_shown = True
            st.rerun()

    # Forma za novog korisnika (samo admin)
    if st.session_state.get("novi_korisnik_form_shown", False) and tip_korisnika == "administrator":
        with st.form("novi_korisnik_form", clear_on_submit=False):
            st.markdown("**Novi korisnik**")
            col1, col2 = st.columns(2)
            with col1:
                ime_prezime = st.text_input("Ime i prezime", key="ime_prezime_novi")
                korisničko_ime = st.text_input("Korisničko ime", key="korisničko_ime_novi")
                lozinka = st.text_input("Lozinka", type="password", key="lozinka_novi")
                tip_korisnika_novi = st.selectbox("Tip korisnika", [
                    "administrator", "ured", "skladištar", "terenac", "gost"
                ], key="tip_korisnika_novi")
                godisnji_dani = st.number_input("Godišnji dani (po godini)", value=20, min_value=0, key="god_dani_novi")
                slobodni_dani = st.number_input("Slobodni dani", value=0, min_value=0, key="slob_dani_novi")
            with col2:
                st.markdown("**Prava**")
                prava = st.multiselect("Odaberi prava (može više)", [
                    "NARUDŽBE - ADMINISTRATOR", "PROIZVODI - ADMINISTRATOR",
                    "DOBAVLJAČI - ADMINISTRATOR", "KORISNICI - ADMINISTRATOR",
                    "SKLADIŠTE - ADMINISTRATOR", "IZVJEŠTAJ - SVE", "IZVJEŠTAJ - PRODAJA"
                ], key="prava_novi")
                st.markdown("**Skladišta**")
                skladišta = st.multiselect("Skladišta", [
                    "Osijek - Glavno skladište", "Skladište Split", "Skladište Pula",
                    "Skladište Zagreb", "Skladište Rijeka"
                ], key="skladišta_novi")
            col_submit, col_cancel = st.columns(2)
            with col_submit:
                if st.form_submit_button("Spremi", key="spremi_novi"):
                    if korisničko_ime and ime_prezime and lozinka:
                        novi = {
                            "korisničko_ime": korisničko_ime,
                            "ime_prezime": ime_prezime,
                            "lozinka": bcrypt.hashpw(lozinka.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                            "tip_korisnika": tip_korisnika_novi,
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
                if st.form_submit_button("Odustani", key="odustani_novi"):
                    st.session_state.novi_korisnik_form_shown = False
                    st.rerun()

    # Uređivanje postojećih korisnika – ograničeno po ulozi
    st.subheader("Uređivanje korisnika")

    for korisnik in korisnici_data:
        is_admin = tip_korisnika == "administrator"
        is_own = korisnik["id"] == trenutni_id

        if is_admin or is_own:
            with st.expander(f"Uređivanje korisnika: {korisnik['korisničko_ime']} ({korisnik['ime_prezime']})", expanded=is_own):
                with st.form(f"edit_form_{korisnik['id']}", clear_on_submit=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        edit_ime_prezime = st.text_input("Ime i prezime", value=korisnik["ime_prezime"], disabled=not is_admin, key=f"ime_{korisnik['id']}")
                        edit_korisničko_ime = st.text_input("Korisničko ime", value=korisnik["korisničko_ime"], disabled=not is_admin, key=f"kor_ime_{korisnik['id']}")
                        edit_lozinka = st.text_input("Nova lozinka (ostavi prazno ako ne mijenjaš)", type="password", value="", key=f"loz_{korisnik['id']}")
                        edit_tip = st.selectbox("Tip korisnika", ["administrator", "ured", "skladištar", "terenac", "gost"], index=["administrator", "ured", "skladištar", "terenac", "gost"].index(korisnik["tip_korisnika"]), disabled=not is_admin, key=f"tip_{korisnik['id']}")
                        edit_god_dani = st.number_input("Godišnji dani", value=korisnik.get("godisnji_dani", 20), min_value=0, disabled=not is_admin, key=f"god_{korisnik['id']}")
                        edit_slob_dani = st.number_input("Slobodni dani", value=korisnik.get("slobodni_dani", 0), min_value=0, disabled=not is_admin, key=f"slob_{korisnik['id']}")
                    with col2:
                        edit_aktivan = st.checkbox("Aktivan", value=korisnik["aktivan"], disabled=not is_admin, key=f"akt_{korisnik['id']}")

                        if is_admin:
                            st.markdown("**Prava**")
                            edit_prava = st.multiselect("Prava", [
                                "NARUDŽBE - ADMINISTRATOR", "PROIZVODI - ADMINISTRATOR",
                                "DOBAVLJAČI - ADMINISTRATOR", "KORISNICI - ADMINISTRATOR",
                                "SKLADIŠTE - ADMINISTRATOR", "IZVJEŠTAJ - SVE", "IZVJEŠTAJ - PRODAJA"
                            ], default=korisnik.get("prava", []), key=f"prava_{korisnik['id']}")

                            st.markdown("**Skladišta**")
                            edit_skladišta = st.multiselect("Skladišta", [
                                "Osijek - Glavno skladište", "Skladište Split", "Skladište Pula",
                                "Skladište Zagreb", "Skladište Rijeka"
                            ], default=korisnik.get("skladišta", []), key=f"sklad_{korisnik['id']}")

                    col_submit, col_cancel = st.columns(2)
                    with col_submit:
                        if st.form_submit_button("Spremi promjene", key=f"spremi_{korisnik['id']}"):
                            update_data = {}

                            if edit_lozinka:
                                update_data["lozinka"] = bcrypt.hashpw(edit_lozinka.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

                            if is_admin:
                                update_data.update({
                                    "ime_prezime": edit_ime_prezime,
                                    "korisničko_ime": edit_korisničko_ime,
                                    "tip_korisnika": edit_tip,
                                    "aktivan": edit_aktivan,
                                    "godisnji_dani": edit_god_dani,
                                    "slobodni_dani": edit_slob_dani,
                                })
                                if "edit_prava" in locals():
                                    update_data["prava"] = edit_prava
                                if "edit_skladišta" in locals():
                                    update_data["skladišta"] = edit_skladišta

                            if update_data:
                                supabase.table("korisnici").update(update_data).eq("id", korisnik["id"]).execute()
                                st.success("Promjene spremljene!")
                                st.rerun()
                            else:
                                st.info("Nema promjena za spremiti.")

                    with col_cancel:
                        if st.form_submit_button("Odustani", key=f"odust_{korisnik['id']}"):
                            st.rerun()
        else:
            pass

    # Dodatni gumbi – svi vide
    col_export, col_refresh = st.columns(2)
    with col_export:
        if st.button("Izvezi sve korisnike u Excel"):
            output = io.BytesIO()
            pd.DataFrame(korisnici_data).to_excel(output, index=False)
            output.seek(0)
            st.download_button(
                label="Preuzmi .xlsx",
                data=output,
                file_name=f"korisnici_{datetime.now(TZ).strftime('%Y-%m-%d_%H-%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    with col_refresh:
        if st.button("🔄 Osvježi"):
            st.rerun()