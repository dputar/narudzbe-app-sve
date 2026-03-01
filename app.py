    # ────────────────────────────────────────────────
    # ADMINISTRACIJA → KORISNICI
    # ────────────────────────────────────────────────
    elif st.session_state.stranica == "admin_korisnici":
        st.title("Administracija - Korisnici")

        # Stanje za uređivanje korisnika
        if "edit_korisnik_id" not in st.session_state:
            st.session_state.edit_korisnik_id = None

        # Dohvati sve korisnike
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
                    value=st.session_state.korisnici_search,
                    key="korisnici_search_input",
                    placeholder="upiši korisničko ime, ime i prezime, tip...",
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
            df_display["Uredi"] = False  # checkbox za uređivanje

            # Sakrij lozinku u prikazu tablice (prikazuje ******)
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
                    "Uredi": st.column_config.CheckboxColumn("Uredi"),  # klik ovdje otvara uređivanje
                }
            )

            # Detekcija označenog "Uredi" checkboxa
            for row in edited_df.to_dict("records"):
                if row["Uredi"]:
                    st.session_state.edit_korisnik_id = row["id"]
                    st.rerun()

            # Spremi promjene (brisanje označenih)
            if st.button("💾 Spremi promjene", type="primary"):
                for row in edited_df.to_dict("records"):
                    row_id = row["id"]
                    if row["Obriši"]:
                        supabase.table("korisnici").delete().eq("id", row_id).execute()
                st.success("Promjene spremljene! Označeni korisnici obrisani.")
                st.rerun()

            # Izvoz u Excel
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

            # Osvježi
            st.button("🔄 Osvježi", on_click=st.rerun)

            # Uređivanje korisnika (otvara se kada označiš "Uredi" checkbox)
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
                                    "skladišta": edit_skladišta
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

        # Jedini gumb za novog korisnika
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
                                "skladišta": skladišta
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