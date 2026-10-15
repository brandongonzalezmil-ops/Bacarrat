import re
import sqlite3
import uuid
from datetime import datetime

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# --------------------------------------------------
# CONFIGURACION
# --------------------------------------------------

st.set_page_config(page_title="Baccarat Pro", page_icon="🃏", layout="wide")

DB = "baccarat.db"
MAZOS = 8
RANGOS = ["A", "2", "3", "4", "5", "6", "7",
          "8", "9", "10", "J", "Q", "K"]
VALORES = {"A": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7,
           "8": 8, "9": 9, "10": 0, "J": 0, "Q": 0, "K": 0}
EMOJI = {"P": "🔵", "B": "🔴", "T": "🟢"}
NOMBRE = {"P": "Jugador", "B": "Banca", "T": "Empate"}


# --------------------------------------------------
# BASE DE DATOS
# --------------------------------------------------

def conectar():
    return sqlite3.connect(DB)


def inicializar_db():
    with conectar() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS manos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shoe_id TEXT NOT NULL,
                numero INTEGER NOT NULL,
                fecha TEXT NOT NULL,
                cartas_jugador TEXT NOT NULL,
                cartas_banca TEXT NOT NULL,
                puntos_jugador INTEGER NOT NULL,
                puntos_banca INTEGER NOT NULL,
                resultado TEXT NOT NULL
            )
        """)
        # Cartas vistas fuera de una mano (carta quemada, etc.)
        con.execute("""
            CREATE TABLE IF NOT EXISTS vistas_extra (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shoe_id TEXT NOT NULL,
                carta TEXT NOT NULL
            )
        """)


def ultimo_zapato():
    with conectar() as con:
        fila = con.execute(
            "SELECT shoe_id FROM manos ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return fila[0] if fila else str(uuid.uuid4())[:8]


def cargar_manos(shoe_id=None):
    with conectar() as con:
        if shoe_id:
            return pd.read_sql_query(
                "SELECT * FROM manos WHERE shoe_id = ? ORDER BY numero",
                con, params=(shoe_id,))
        return pd.read_sql_query(
            "SELECT * FROM manos ORDER BY id DESC", con)


def cargar_extra(shoe_id):
    with conectar() as con:
        filas = con.execute(
            "SELECT carta FROM vistas_extra WHERE shoe_id = ?",
            (shoe_id,)).fetchall()
    return [f[0] for f in filas]


# --------------------------------------------------
# REGLAS Y VALIDACION
# --------------------------------------------------

def puntos(cartas):
    return sum(VALORES[c] for c in cartas) % 10


def banca_roba(pb, x):
    """x = valor de la 3ra carta del jugador (None si se plantó)."""
    if pb <= 2:
        return True
    if x is None:
        return pb <= 5
    if pb == 3:
        return x != 8
    if pb == 4:
        return 2 <= x <= 7
    if pb == 5:
        return 4 <= x <= 7
    if pb == 6:
        return 6 <= x <= 7
    return False


def validar_mano(j, b):
    """Comprueba que la cantidad de cartas cumple las reglas de tercera
    carta. Evita errores de digitación, que dañan el conteo."""
    if len(j) < 2 or len(b) < 2:
        return "Cada lado necesita al menos 2 cartas."
    pj, pb = puntos(j[:2]), puntos(b[:2])
    if pj >= 8 or pb >= 8:
        if len(j) != 2 or len(b) != 2:
            return "Hay natural (8 o 9): nadie roba tercera carta."
        return None
    if pj <= 5:
        if len(j) != 3:
            return f"Jugador con {pj} debe robar tercera carta."
        x = VALORES[j[2]]
    else:
        if len(j) != 2:
            return f"Jugador con {pj} se planta."
        x = None
    debe = banca_roba(pb, x)
    if debe and len(b) != 3:
        return f"Banca con {pb} debe robar tercera carta."
    if not debe and len(b) != 2:
        return f"Banca con {pb} se planta en este caso."
    return None


# --------------------------------------------------
# MODELO: PROBABILIDADES EXACTAS CON EL ZAPATO RESTANTE
# --------------------------------------------------

@st.cache_data(show_spinner=False)
def calcular_probabilidades(c):
    """c = tupla de 10 enteros: cartas restantes por valor (0..9).
    Enumera todas las manos posibles sin reemplazo siguiendo las reglas
    reales de tercera carta. Devuelve (P, B, T)."""
    c = list(c)
    n = sum(c)
    P = B = T = 0.0

    for a in range(10):                      # 1ª Jugador
        if not c[a]:
            continue
        p1 = c[a] / n
        c[a] -= 1
        n1 = n - 1
        for b in range(10):                  # 1ª Banca
            if not c[b]:
                continue
            p2 = p1 * c[b] / n1
            c[b] -= 1
            n2 = n1 - 1
            for d in range(10):              # 2ª Jugador
                if not c[d]:
                    continue
                p3 = p2 * c[d] / n2
                c[d] -= 1
                n3 = n2 - 1
                for e in range(10):          # 2ª Banca
                    if not c[e]:
                        continue
                    p4 = p3 * c[e] / n3
                    c[e] -= 1
                    n4 = n3 - 1
                    pj, pb = (a + d) % 10, (b + e) % 10

                    if pj >= 8 or pb >= 8:
                        if pj > pb:
                            P += p4
                        elif pb > pj:
                            B += p4
                        else:
                            T += p4
                    elif pj <= 5:            # Jugador roba
                        for x in range(10):
                            if not c[x]:
                                continue
                            p5 = p4 * c[x] / n4
                            pj3 = (pj + x) % 10
                            if banca_roba(pb, x):
                                c[x] -= 1
                                wp = wb = wt = 0
                                for y in range(10):
                                    k = c[y]
                                    if k:
                                        t = (pb + y) % 10
                                        if pj3 > t:
                                            wp += k
                                        elif t > pj3:
                                            wb += k
                                        else:
                                            wt += k
                                c[x] += 1
                                den = n4 - 1
                                P += p5 * wp / den
                                B += p5 * wb / den
                                T += p5 * wt / den
                            else:
                                if pj3 > pb:
                                    P += p5
                                elif pb > pj3:
                                    B += p5
                                else:
                                    T += p5
                    else:                    # Jugador se planta (6-7)
                        if banca_roba(pb, None):
                            wp = wb = wt = 0
                            for y in range(10):
                                k = c[y]
                                if k:
                                    t = (pb + y) % 10
                                    if pj > t:
                                        wp += k
                                    elif t > pj:
                                        wb += k
                                    else:
                                        wt += k
                            P += p4 * wp / n4
                            B += p4 * wb / n4
                            T += p4 * wt / n4
                        else:
                            if pj > pb:
                                P += p4
                            elif pb > pj:
                                B += p4
                            else:
                                T += p4
                    c[e] += 1
                c[d] += 1
            c[b] += 1
        c[a] += 1
    return P, B, T


def conteo_por_rango(df, extra):
    conteo = {r: 0 for r in RANGOS}
    for _, f in df.iterrows():
        for col in ("cartas_jugador", "cartas_banca"):
            for carta in f[col].split(","):
                carta = carta.strip()
                if carta in conteo:
                    conteo[carta] += 1
    for carta in extra:
        if carta in conteo:
            conteo[carta] += 1
    return conteo


def restantes_por_valor(conteo):
    """Cartas restantes agrupadas por valor baccarat (0..9)."""
    rest = [0] * 10
    for r in RANGOS:
        rest[VALORES[r]] += MAZOS * 4 - conteo[r]
    return rest


# --------------------------------------------------
# ESTADO
# --------------------------------------------------

inicializar_db()

if "shoe_id" not in st.session_state:
    st.session_state.shoe_id = ultimo_zapato()
if "cj" not in st.session_state:
    st.session_state.cj = []
if "cb" not in st.session_state:
    st.session_state.cb = []
if "aviso" not in st.session_state:
    st.session_state.aviso = None


def guardar_mano(j, b):
    pj, pb = puntos(j), puntos(b)
    res = "P" if pj > pb else "B" if pb > pj else "T"
    with conectar() as con:
        sig = con.execute(
            "SELECT COALESCE(MAX(numero),0)+1 FROM manos WHERE shoe_id=?",
            (st.session_state.shoe_id,)).fetchone()[0]
        con.execute("""
            INSERT INTO manos (shoe_id, numero, fecha, cartas_jugador,
                cartas_banca, puntos_jugador, puntos_banca, resultado)
            VALUES (?,?,?,?,?,?,?,?)
        """, (st.session_state.shoe_id, sig,
              datetime.now().isoformat(timespec="seconds"),
              ",".join(j), ",".join(b), pj, pb, res))
    return res, pj, pb


def deshacer_ultima():
    with conectar() as con:
        con.execute("""
            DELETE FROM manos WHERE id = (
                SELECT id FROM manos WHERE shoe_id=?
                ORDER BY numero DESC LIMIT 1)
        """, (st.session_state.shoe_id,))


# --------------------------------------------------
# BARRA LATERAL
# --------------------------------------------------

with st.sidebar:
    st.header("⚙️ Ajustes")
    bankroll = st.number_input("Bankroll de sesión ($)", min_value=1000,
                               value=300000, step=10000)
    umbral = st.slider(
        "Ventaja mínima para recomendar apostar (%)",
        0.0, 2.0, 0.3, 0.1,
        help="Margen de seguridad por si registraste mal alguna carta.")
    st.markdown("---")
    st.write("Zapato actual")
    st.code(st.session_state.shoe_id)
    if st.button("🆕 Nuevo zapato (se barajó)", use_container_width=True):
        st.session_state.shoe_id = str(uuid.uuid4())[:8]
        st.session_state.cj, st.session_state.cb = [], []
        st.rerun()

    st.markdown("---")
    with st.expander("Carta vista fuera de mano (quemada)"):
        carta_x = st.selectbox("Carta", RANGOS, key="carta_x")
        if st.button("Agregar al conteo"):
            with conectar() as con:
                con.execute(
                    "INSERT INTO vistas_extra (shoe_id, carta) VALUES (?,?)",
                    (st.session_state.shoe_id, carta_x))
            st.rerun()

df = cargar_manos(st.session_state.shoe_id)
extra = cargar_extra(st.session_state.shoe_id)
conteo = conteo_por_rango(df, extra)
rest_valor = restantes_por_valor(conteo)
total_rest = sum(rest_valor)
total_vistas = sum(conteo.values())

# --------------------------------------------------
# 1) RECOMENDACION (SIEMPRE ARRIBA)
# --------------------------------------------------

st.title("🃏 Baccarat Pro")

if min(rest_valor) < 0 or any(conteo[r] > MAZOS * 4 for r in RANGOS):
    st.error("Hay un rango con más cartas registradas de las que existen "
             "en 8 mazos. Revisa errores (usa ↩️ Deshacer última mano).")
elif total_rest < 20:
    st.warning("Quedan menos de 20 cartas: el zapato está por terminar. "
               "No hay recomendación.")
else:
    pP, pB, pT = calcular_probabilidades(tuple(rest_valor))
    ev_b = 0.95 * pB - pP        # el empate devuelve la apuesta
    ev_p = pP - pB
    mejor = "Banca" if ev_b >= ev_p else "Jugador"
    ev_mejor = max(ev_b, ev_p) * 100

    if ev_mejor >= umbral:
        kelly = max(ev_mejor / 100, 0)
        apuesta = bankroll * min(kelly * 0.5, 0.02)
        color = "#166534"
        titulo = f"✅ APUESTA A {mejor.upper()}"
        detalle = (f"Ventaja estimada: +{ev_mejor:.2f}% · "
                   f"Apuesta máx. sugerida: ${apuesta:,.0f}")
    else:
        color = "#7f1d1d"
        titulo = "⛔ NO APUESTES ESTA MANO"
        detalle = (f"Mejor opción sería {mejor} pero con EV "
                   f"{ev_mejor:+.2f}% (la casa sigue ganando)")

    st.markdown(
        f"""<div style="background:{color};padding:18px;border-radius:12px;
        text-align:center;color:white">
        <div style="font-size:2rem;font-weight:700">{titulo}</div>
        <div style="font-size:1.1rem">{detalle}</div></div>""",
        unsafe_allow_html=True)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("P(Banca)", f"{pB*100:.2f}%")
    m2.metric("P(Jugador)", f"{pP*100:.2f}%")
    m3.metric("P(Empate)", f"{pT*100:.2f}%")
    m4.metric("EV Banca", f"{ev_b*100:+.2f}%")
    m5.metric("EV Jugador", f"{ev_p*100:+.2f}%")
    st.caption("Referencia con zapato completo: EV Banca ≈ −1.06%, "
               "Jugador ≈ −1.24%. Solo se vuelve positivo con una "
               "composición del zapato favorable y bien registrada.")

# --------------------------------------------------
# 2) REGISTRO RAPIDO POR TECLADO
# --------------------------------------------------

ALIAS = {"T": "10", "0": "10", "1": "A"}


def parsear_cartas(texto, lado):
    """'453' -> ['4','5','3']. Una letra/numero por carta.
    10 = T o 0 (o escribir 10). Acepta espacios o comas."""
    t = texto.upper().replace("10", "T")
    t = re.sub(r"[\s/,\-\.]+", "", t)
    cartas = []
    for ch in t:
        ch = ALIAS.get(ch, ch)
        if ch not in RANGOS:
            raise ValueError(f"{lado}: carta inválida '{ch}'")
        cartas.append(ch)
    if len(cartas) not in (2, 3):
        raise ValueError(f"{lado}: debe tener 2 o 3 cartas.")
    return cartas


st.markdown("---")
st.subheader("⚡ Registro rápido (teclado)")
st.caption("Jugador → **Tab** → Banca → **Enter**. Ej.: `72` y `453` · "
           "10 = `T` o `0` · J, Q, K, A normal · escribe `u` en "
           "Jugador para deshacer la última mano")

with st.form("rapido", clear_on_submit=True):
    fc1, fc2 = st.columns(2)
    entrada_j = fc1.text_input("🔵 Jugador", placeholder="72")
    entrada_b = fc2.text_input("🔴 Banca", placeholder="453")
    enviar = st.form_submit_button("Guardar (Enter)")

if enviar:
    if entrada_j.strip().lower() in ("u", "z"):
        deshacer_ultima()
        st.session_state.aviso = "↩️ Última mano deshecha."
        st.rerun()
    elif entrada_j.strip() or entrada_b.strip():
        try:
            j = parsear_cartas(entrada_j, "Jugador")
            b = parsear_cartas(entrada_b, "Banca")
            error = validar_mano(j, b)
            if error:
                raise ValueError(error)
            res, pj, pb = guardar_mano(j, b)
            st.session_state.aviso = (
                f"{EMOJI[res]} Ganó {NOMBRE[res]} ({pj} vs {pb}) · "
                f"J: {' '.join(j)} | B: {' '.join(b)}")
            st.rerun()
        except ValueError as e:
            st.error(str(e))

if st.session_state.aviso:
    st.info(st.session_state.aviso)
    st.session_state.aviso = None

# Devuelve el cursor a la caja después de cada mano (mejor esfuerzo)
components.html(
    """<script>
    const f = () => {
      const i = window.parent.document.querySelector('input[aria-label^="🔵"]');
      if (i) i.focus();
    };
    setTimeout(f, 150); setTimeout(f, 600);
    </script>""",
    height=0,
)

# --------------------------------------------------
# 3) CONTEO + PATRONES
# --------------------------------------------------

st.markdown("---")
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("🧮 Conteo del zapato (8 mazos)")
    k1, k2 = st.columns(2)
    k1.metric("Cartas vistas", total_vistas)
    k2.metric("Restantes", total_rest)

    tabla = pd.DataFrame([{
        "Carta": r,
        "Vistas": conteo[r],
        "Restantes": MAZOS * 4 - conteo[r],
    } for r in RANGOS])
    st.dataframe(tabla.set_index("Carta").T, use_container_width=True)

    por_valor = pd.DataFrame({
        "Valor": [str(i) for i in range(10)],
        "Restantes": rest_valor,
    })
    st.bar_chart(por_valor.set_index("Valor"))
    st.caption("Valor 0 = 10, J, Q, K. Más 0s y 4-6 sobrantes tiende a "
               "favorecer a Banca/Jugador de forma muy leve; el modelo "
               "ya lo calcula exacto, no hace falta interpretarlo a ojo.")

with col_b:
    st.subheader("📊 Patrones (solo descriptivo)")
    if df.empty:
        st.info("Registra manos para ver el camino de resultados.")
    else:
        res = df["resultado"].tolist()
        total = len(res)
        st.write("**Últimas 40 manos** (la más reciente al final):")
        st.write(" ".join(EMOJI[x] for x in res[-40:]))

        racha = 1
        for i in range(len(res) - 1, 0, -1):
            if res[i] == res[i - 1]:
                racha += 1
            else:
                break

        cambios = sum(1 for i in range(1, total) if res[i] != res[i - 1])

        c1, c2, c3 = st.columns(3)
        c1.metric("Manos", total)
        c2.metric("Racha actual",
                  f"{racha} × {NOMBRE[res[-1]]}")
        c3.metric("Alternancias",
                  f"{cambios}/{max(total - 1, 1)}")

        freq = pd.DataFrame({
            "Resultado": ["Banca", "Jugador", "Empate"],
            "Manos": [res.count("B"), res.count("P"), res.count("T")],
        })
        freq["%"] = (freq["Manos"] / total * 100).round(1)
        st.dataframe(freq, use_container_width=True, hide_index=True)

        st.caption(
            "Rachas y 'chops' no predicen la siguiente mano: cada mano "
            "sale de las cartas que quedan, no de lo que pasó antes. "
            "Por eso la recomendación de arriba NO usa estos patrones.")

# --------------------------------------------------
# 4) HISTORIAL
# --------------------------------------------------

with st.expander("🗂️ Historial completo"):
    todos = cargar_manos()
    if todos.empty:
        st.info("Aún no hay manos guardadas.")
    else:
        st.write(f"Manos guardadas en total: {len(todos)}")
        st.dataframe(todos, use_container_width=True)
        st.download_button(
            "📥 Descargar CSV",
            data=todos.to_csv(index=False).encode("utf-8"),
            file_name="historial_baccarat.csv", mime="text/csv")
