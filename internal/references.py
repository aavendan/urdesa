import streamlit as st

def referencias():

    st.header("Referencias")

    body = "* Urdesa (Sector) (Guayaquil)(N.d.). Retrieved from https://wikimapia.org/3524525/es/Urdesa-Sector\n"
    body += "* Urdesa. (2026). Retrieved from https://es.wikipedia.org/wiki/Urdesa\n"
    body += "* Mimg-Ge. (2025). Urdesa renovará su esencia con Plan Urbanístico que prioriza movilidad, comunidad e identidad – Alcaldía de Guayaquil. Retrieved from https://guayaquil.gob.ec/urdesa-renovara-esencia-plan-urbanistico-prioriza-movilidad-comunidad-identidad/\n"
    body += "* Pino, C. I. (2025). Urdesa, 70 años después: entre el florecimiento urbano y el reto de la seguridad. Retrieved from https://www.expreso.ec/guayaquil/urdesa-cumple-70-anos-retos-inseguridad-paso-242085.html"
    st.markdown( body , text_alignment="justify")