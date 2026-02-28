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

# LOGIN (ostaje isto)
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
    # SIDEBAR (ostaje isto)
    with st.sidebar:
        st.title("Sustav narudžbi")
        st.button("🏠 Početna", key="menu_pocetna", on_click=lambda: st.session_state.update({"stranica": "početna"}))
        st.button("🛒 Narudžbe", key="menu_narudzbe", on_click=lambda: st.session_state.update({"stranica": "narudžbe"}))
        st.button("🔍 Pretraga narudžbi", key="menu_pretraga", on_click=lambda: st.session_state.update({"stranica": "pretraga"}))
        with st.expander("📊 Izvještaji", expanded=False):
            st.info("Izvještaji dolaze kasnije...")
        with st.expander("⚙️ Administracija", expanded=False):
            st.button("📦 Proizvodi", key="admin_proizvodi", on_click=lambda: st.session_state.update({"stranica": "admin_proizvodi"}))
            st.button("🚚 Dobavljači", key="admin_dobavljaci", on_click=lambda: st.session_state.update({"stranica": "admin_dobavljaci"}))
            st.button("👥 Korisnici", key="admin_korisnici", on_click=lambda: st.session_state.update({"stranica": "admin_korisnici"}))
            st.button("📋 Šifarnici", key="admin_sifarnici", on_click=lambda: st.session_state.update({"stranica": "admin_sifarnici"}))
        st.button("📁 Dokumenti", key="menu_dokumenti", on_click=lambda: st.session_state.update({"stranica": "dokumenti"}))
        st.button("➡️ Odjava", key="menu_odjava", on_click=lambda: (supabase.auth.sign_out(), st.session_state.update({"user": None, "stranica": "login"})))

    # POČETNA (ostaje isto)
    if st.session_state.stranica == "početna":
        st.title("Početna")
        st.markdown("### Dobrodošli u sustav narudžbi!")
        st.info("Ovdje će biti dashboard, statistike...")

    # NARUDŽBE (ostaje isto)
    elif st.session_state.stranica == "narudžbe":
        st.title("Pregled narudžbi")
        if st.button("➕ Nova narudžba", type="primary"):
            st.session_state.stranica = "nova"
            st.rerun()
        if st.button("🔄 Osvježi"):
            st.rerun()
        response = supabase.table("main_orders").select("*").order("datum", desc=True).execute()
        df = pd.DataFrame(response.data or [])
        if not df.empty:
            df = df.fillna("")
            df = df.loc[:, ~df.columns.duplicated()]
            if "reprezentacija" in df.columns:
                df = df.rename(columns={"reprezentacija": "Skladište"})
            st.dataframe(df, use_container_width=True, height=750)
        else:
            st.info("Još nema narudžbi.")

    # NOVA NARUDŽBA (ostaje isto)
    elif st.session_state.stranica == "nova":
        # ... tvoj kod za novu narudžbu ostaje nepromijenjen ...
        pass

    # DOBAVLJAČI (ostaje isto)
    elif st.session_state.stranica == "admin_dobavljaci":
        # ... tvoj kod za dobavljače ostaje nepromijenjen ...
        pass

    # PROIZVODI – s tražilicom i exportom SVIH podataka
    elif st.session_state.stranica == "admin_proizvodi":
        st.title("Administracija - Proizvodi")

        # Uvijek dohvaćamo puni set iz baze za export
        full_response = supabase.table("proizvodi").select("*").order("created_at", desc=True).execute()
        df_full = pd.DataFrame(full_response.data or [])

        # Prikazujemo kopiju za prikaz i filtriranje
        df_display = df_full.copy()

        if not df_full.empty:
            # Naslov + tražilica pored
            col1, col2 = st.columns([6, 4])
            with col1:
                st.subheader("Postojeći proizvodi")
            with col2:
                search_term = st.text_input("Pretraži po svim stupcima", "", key="proizvodi_trazilica", placeholder="upiši naziv, šifru, dobavljača...")

            # Filtriranje za prikaz
            if search_term:
                search_term = str(search_term).strip().lower()
                mask = df_display.astype(str).apply(lambda x: x.str.lower().str.contains(search_term), axis=1).any(axis=1)
                df_display = df_display[mask].copy()
                if df_display.empty:
                    st.info("Ništa nije pronađeno po traženom pojmu.")

            # Dodaj checkbox za brisanje pojedinačnih
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

            col1, col2, col3 = st.columns(3)
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
                # Export SVIH podataka (iz punog seta iz baze)
                if st.button("Izvezi SVE podatke u Excel"):
                    if not df_full.empty:
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                            df_full.to_excel(writer, index=False, sheet_name="Svi proizvodi")
                        output.seek(0)
                        st.download_button(
                            label="Preuzmi cijelu bazu (.xlsx)",
                            data=output,
                            file_name=f"svi_proizvodi_{datetime.now(TZ).strftime('%Y-%m-%d_%H-%M')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    else:
                        st.warning("Nema podataka za export.")

            with col3:
                st.button("🔄 Osvježi tablicu", on_click=st.rerun)

        else:
            st.info("Još nema proizvoda u bazi.")

        # DODAJ NOVI PROIZVOD (ostaje isto)
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

        # UPLOAD IZ EXCELA (ostaje isto)
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

                    # Dohvati postojeće nazive
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

        # GUMB ZA OBRIŠI SVE – DOLJE + POTVRDA (ostaje isto)
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