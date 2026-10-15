
import sqlite3
import uuid
from datetime import datetime

import pandas as pd
import streamlit as st

# --------------------------------------------------
# CONFIGURACION
# --------------------------------------------------

st.set_page_config(
    page_title="Baccarat Analytics Pro",
    page_icon="🃏",
    layout="wide"
)

DB = "baccarat.db"

# Valores permitidos: A, 2-10, J, Q, K
RANGOS = ["A", "2", "3", "4", "5", "6", "7",
          "8", "9", "10", "J", "Q", "K"]

VALORES = {
    "A": 1, "2": 2, "3": 3, "4": 4,
    "5": 5, "6": 6, "7": 7, "8": 8,
    "9": 9, "10": 0, "J": 0, "Q": 0, "K": 0
}

st.title("🃏 Baccarat Analytics Pro")
st.caption(
    "Registro por zapato, conteo de cartas, estadísticas "
    "y control del bankroll."
)


# --------------------------------------------------
# BASE DE DATOS SQLITE
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


def nuevo_zapato():
    shoe_id = str(uuid.uuid4())[:8]
    st.session_state.shoe_id = shoe_id
    st.session_state.mensaje = (
        f"Nuevo zapato iniciado: {shoe_id}"
    )


def cargar_ultimo_zapato():
    with conectar() as con:
        fila = con.execute("""
            SELECT shoe_id
            FROM manos
            ORDER BY id DESC
            LIMIT 1
        """).fetchone()

    return fila[0] if fila else str(uuid.uuid4())[:8]


inicializar_db()

if "shoe_id" not in st.session_state:
    st.session_state.shoe_id = cargar_ultimo_zapato()

if "mensaje" not in st.session_state:
    st.session_state.mensaje = ""


# --------------------------------------------------
# FUNCIONES DE CARTAS
# --------------------------------------------------

def analizar_cartas(texto):
    """
    Acepta ejemplos como:
    A, 7
    10, K, 3

    Devuelve las cartas normalizadas.
    """
    if not texto or not texto.strip():
        raise ValueError("Debes ingresar las cartas.")

    cartas = [
        x.strip().upper()
        for x in texto.replace(";", ",").split(",")
        if x.strip()
    ]

    if not cartas:
        raise ValueError("No se encontraron cartas.")

    for carta in cartas:
        if carta not in RANGOS:
            raise ValueError(
                f"Carta inválida: {carta}. "
                "Usa A, 2-10, J, Q o K."
            )

    if len(cartas) not in (2, 3):
        raise ValueError(
            "Cada mano debe tener 2 o 3 cartas."
        )

    return cartas


def puntos_baccarat(cartas):
    return sum(VALORES[c] for c in cartas) % 10


def contar_cartas(df):
    """
    Cuenta las cartas registradas en el zapato actual.
    Cada carta física se cuenta una sola vez.
    """
    conteo = {r: 0 for r in RANGOS}

    for _, fila in df.iterrows():
        for columna in ("cartas_jugador", "cartas_banca"):
            cartas = fila[columna].split(",")
            for carta in cartas:
                carta = carta.strip()
                if carta in conteo:
                    conteo[carta] += 1

    return conteo


def guardar_mano(jugador, banca):
    with conectar() as con:
        siguiente = con.execute("""
            SELECT COALESCE(MAX(numero), 0) + 1
            FROM manos
            WHERE shoe_id = ?
        """, (st.session_state.shoe_id,)).fetchone()[0]

        puntos_j = puntos_baccarat(jugador)
        puntos_b = puntos_baccarat(banca)

        if puntos_j > puntos_b:
            resultado = "P"
        elif puntos_b > puntos_j:
            resultado = "B"
        else:
            resultado = "T"

        con.execute("""
            INSERT INTO manos (
                shoe_id, numero, fecha,
                cartas_jugador, cartas_banca,
                puntos_jugador, puntos_banca, resultado
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            st.session_state.shoe_id,
            siguiente,
            datetime.now().isoformat(timespec="seconds"),
            ",".join(jugador),
            ",".join(banca),
            puntos_j,
            puntos_b,
            resultado
        ))

    return resultado, puntos_j, puntos_b


def cargar_manos(shoe_id=None):
    with conectar() as con:
        if shoe_id:
            df = pd.read_sql_query("""
                SELECT * FROM manos
                WHERE shoe_id = ?
                ORDER BY numero
            """, con, params=(shoe_id,))
        else:
            df = pd.read_sql_query("""
                SELECT * FROM manos
                ORDER BY id DESC
            """, con)

    return df


# --------------------------------------------------
# MENU
# --------------------------------------------------

menu = st.sidebar.radio(
    "Módulos",
    [
        "Registro en vivo",
        "Conteo de cartas",
        "Estadísticas y patrones",
        "Bankroll y EV",
        "Historial completo"
    ]
)

st.sidebar.markdown("---")
st.sidebar.write("Zapato actual")
st.sidebar.code(st.session_state.shoe_id)

if st.sidebar.button("🆕 Iniciar nuevo zapato"):
    nuevo_zapato()
    st.rerun()

if st.session_state.mensaje:
    st.sidebar.success(st.session_state.mensaje)


# --------------------------------------------------
# DATOS DEL ZAPATO ACTUAL
# --------------------------------------------------

df = cargar_manos(st.session_state.shoe_id)


# --------------------------------------------------
# MODULO 1: REGISTRO
# --------------------------------------------------

if menu == "Registro en vivo":
    st.header("📋 Registrar una mano")

    st.info(
        "Ingresa todas las cartas repartidas, incluidas "
        "las terceras cartas si las hubo. Separa los valores "
        "con comas. Ejemplo: 7, 2 o 7, 2, K."
    )

    with st.form("form_mano"):
        col1, col2 = st.columns(2)

        with col1:
            entrada_j = st.text_input(
                "🔵 Cartas de Jugador",
                placeholder="Ej.: 7, 2"
            )

        with col2:
            entrada_b = st.text_input(
                "🔴 Cartas de Banca",
                placeholder="Ej.: 4, 5, 3"
            )

        guardar = st.form_submit_button(
            "Guardar mano",
            use_container_width=True
        )

    if guardar:
        try:
            cartas_j = analizar_cartas(entrada_j)
            cartas_b = analizar_cartas(entrada_b)

            # Validación básica de cantidad total.
            if len(cartas_j) + len(cartas_b) > 6:
                raise ValueError(
                    "La cantidad total de cartas no es válida."
                )

            resultado, pj, pb = guardar_mano(
                cartas_j, cartas_b
            )

            nombres = {
                "B": "🔴 Gana Banca",
                "P": "🔵 Gana Jugador",
                "T": "🟢 Empate"
            }

            st.success(
                f"{nombres[resultado]} | "
                f"Jugador: {pj} puntos | Banca: {pb} puntos"
            )
            st.rerun()

        except ValueError as e:
            st.error(str(e))

    st.markdown("---")
    st.subheader("Últimas manos del zapato")

    if not df.empty:
        vista = df.tail(15)[[
            "numero", "cartas_jugador", "puntos_jugador",
            "cartas_banca", "puntos_banca", "resultado"
        ]].sort_values("numero", ascending=False)

        st.dataframe(vista, use_container_width=True)
    else:
        st.info("Todavía no has registrado manos en este zapato.")


# --------------------------------------------------
# MODULO 2: CONTEO DE CARTAS
# --------------------------------------------------

elif menu == "Conteo de cartas":
    st.header("🧮 Composición estimada del zapato")

    barajas = st.selectbox(
        "Número de barajas del zapato",
        [6, 8],
        index=1
    )

    conteo = contar_cartas(df)

    # En una baraja existen cuatro cartas de cada rango.
    # El conteo es por rango, no por valor baccarat.
    iniciales = {r: 4 * barajas for r in RANGOS}

    datos = []
    for rango in RANGOS:
        vistas = conteo[rango]
        restantes = iniciales[rango] - vistas

        datos.append({
            "Carta": rango,
            "Registradas": vistas,
            "Iniciales": iniciales[rango],
            "Restantes estimadas": restantes,
            "% restante del rango": (
                max(0, restantes) / iniciales[rango] * 100
            )
        })

    tabla = pd.DataFrame(datos)

    total_vistas = sum(conteo.values())
    total_iniciales = 52 * barajas
    total_restantes = total_iniciales - total_vistas

    c1, c2, c3 = st.columns(3)
    c1.metric("Cartas registradas", total_vistas)
    c2.metric("Cartas iniciales", total_iniciales)
    c3.metric("Restantes estimadas", total_restantes)

    st.dataframe(tabla, use_container_width=True)

    st.bar_chart(
        tabla.set_index("Carta")[["Registradas"]]
    )

    st.warning(
        "El conteo solo refleja las cartas que registraste. "
        "No confirma que el zapato físico tenga esa composición: "
        "si omitiste cartas o el casino barajó de nuevo, "
        "las estimaciones dejan de ser fiables. "
        "Las cartas restantes negativas indican registros "
        "inconsistentes con el número de barajas elegido."
    )

    # Conteo de valores baccarat
    st.subheader("Distribución por puntos baccarat")

    puntos = {str(i): 0 for i in range(10)}

    for rango in RANGOS:
        puntos[str(VALORES[rango])] += conteo[rango]

    st.dataframe(
        pd.DataFrame([
            {
                "Valor baccarat": valor,
                "Cartas vistas": cantidad
            }
            for valor, cantidad in puntos.items()
        ]),
        use_container_width=True
    )


# --------------------------------------------------
# MODULO 3: ESTADISTICAS Y PATRONES
# --------------------------------------------------

elif menu == "Estadísticas y patrones":
    st.header("📊 Estadísticas del zapato actual")

    if df.empty:
        st.info("Registra algunas manos para iniciar el análisis.")
    else:
        total = len(df)
        bancas = int((df["resultado"] == "B").sum())
        jugadores = int((df["resultado"] == "P").sum())
        empates = int((df["resultado"] == "T").sum())

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Manos", total)
        c2.metric("Banca", bancas)
        c3.metric("Jugador", jugadores)
        c4.metric("Empates", empates)

        st.subheader("Frecuencia observada")

        frecuencia = pd.DataFrame({
            "Resultado": ["Banca", "Jugador", "Empate"],
            "Manos": [bancas, jugadores, empates],
            "Porcentaje": [
                bancas / total * 100,
                jugadores / total * 100,
                empates / total * 100
            ]
        })

        st.dataframe(frecuencia, use_container_width=True)

        st.bar_chart(
            frecuencia.set_index("Resultado")[["Manos"]]
        )

        # Racha actual de resultados, incluyendo empates.
        resultados = df["resultado"].tolist()
        ultimo = resultados[-1]
        racha = 0

        for resultado in reversed(resultados):
            if resultado == ultimo:
                racha += 1
            else:
                break

        nombres = {"B": "Banca", "P": "Jugador", "T": "Empate"}

        st.info(
            f"Último resultado: {nombres[ultimo]}. "
            f"Racha consecutiva actual: {racha}."
        )

        # Qué sucede inmediatamente después de empates consecutivos.
        st.subheader("¿Qué sucede después de los empates?")

        secuencias = resultados
        filas = []

        for longitud in (1, 2, 3):
            oportunidades = 0
            siguiente_b = 0
            siguiente_p = 0
            siguiente_t = 0

            for i in range(len(secuencias) - longitud):
                bloque = secuencias[i:i + longitud]

                if all(x == "T" for x in bloque):
                    siguiente = secuencias[i + longitud]
                    oportunidades += 1

                    if siguiente == "B":
                        siguiente_b += 1
                    elif siguiente == "P":
                        siguiente_p += 1
                    else:
                        siguiente_t += 1

            filas.append({
                "Empates consecutivos previos": longitud,
                "Casos observados": oportunidades,
                "Siguiente Banca (%)": (
                    round(siguiente_b / oportunidades * 100, 2)
                    if oportunidades else None
                ),
                "Siguiente Jugador (%)": (
                    round(siguiente_p / oportunidades * 100, 2)
                    if oportunidades else None
                ),
                "Siguiente Empate (%)": (
                    round(siguiente_t / oportunidades * 100, 2)
                    if oportunidades else None
                )
            })

        st.dataframe(
            pd.DataFrame(filas),
            use_container_width=True
        )

        st.caption(
            "Estos porcentajes son descriptivos, no predicciones. "
            "Las muestras pueden ser pequeñas y las secuencias "
            "se pueden superponer. No apuestes basándote solo "
            "en estas frecuencias."
        )


# --------------------------------------------------
# MODULO 4: BANKROLL Y EXPECTATIVA MATEMATICA
# --------------------------------------------------

elif menu == "Bankroll y EV":
    st.header("💰 Bankroll y expectativa matemática")

    bankroll = st.number_input(
        "Bankroll de sesión ($)",
        min_value=1000,
        value=300000,
        step=10000
    )

    porcentaje = st.slider(
        "Límite de referencia por mano (%)",
        min_value=1,
        max_value=5,
        value=1
    )

    limite = bankroll * porcentaje / 100

    st.metric(
        "Límite de referencia por mano",
        f"${limite:,.0f}"
    )

    st.caption(
        "Es un límite de control, no una apuesta recomendada. "
        "Una apuesta menor no garantiza beneficios."
    )

    st.markdown("---")
    st.subheader("Calculadora EV aproximada")

    tipo = st.selectbox(
        "Tipo de apuesta",
        ["Banca (5% comisión)", "Jugador", "Empate (8:1)"]
    )

    monto = st.number_input(
        "Monto apostado ($)",
        min_value=1000,
        value=10000,
        step=1000
    )

    # Probabilidades aproximadas de baccarat de 8 barajas.
    p_b = 0.4586
    p_p = 0.4462
    p_t = 0.0952

    if tipo == "Banca (5% comisión)":
        ev = monto * (0.95 * p_b - p_p)
        ventaja = -ev / monto * 100

    elif tipo == "Jugador":
        ev = monto * (p_p - p_b)
        ventaja = -ev / monto * 100

    else:
        ev = monto * (8 * p_t - (1 - p_t))
        ventaja = -ev / monto * 100

    st.metric("EV aproximado por mano", f"${ev:,.2f}")
    st.metric("Ventaja aproximada de la casa", f"{ventaja:.2f}%")

    st.caption(
        "Estimación con probabilidades redondeadas y reglas "
        "habituales. Verifica las reglas y pagos de tu mesa."
    )


# --------------------------------------------------
# MODULO 5: HISTORIAL COMPLETO
# --------------------------------------------------

elif menu == "Historial completo":
    st.header("🗂️ Historial guardado")

    todos = cargar_manos()

    if todos.empty:
        st.info("La base de datos todavía no contiene manos.")
    else:
        st.write(f"Manos guardadas en total: {len(todos)}")

        st.dataframe(
            todos.sort_values("id", ascending=False),
            use_container_width=True
        )

        st.download_button(
            "📥 Descargar historial CSV",
            data=todos.to_csv(index=False).encode("utf-8"),
            file_name="historial_baccarat.csv",
            mime="text/csv"
        )

st.markdown("---")
st.caption(
    "Baccarat Analytics Pro · Herramienta de registro y análisis. "
    "No garantiza predicciones ni beneficios."
)
