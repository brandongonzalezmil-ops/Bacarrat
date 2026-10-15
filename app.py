import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Baccarat Analytics Pro", page_icon="🃏", layout="centered"
)

st.title("🃏 Baccarat Analytics & Bankroll Pro")
st.write("Herramienta cuantitativa para análisis de probabilidades, control de riesgo y seguimiento de rachas en Baccarat.")

# Menú lateral
menu = st.sidebar.selectbox(
    "Menú de Baccarat", 
    ["Calculadora & House Edge", "Gestión de Bankroll y Riesgo", "Registro y Patrones (Roadmap)"]
)

# --- MÓDULO 1: CALCULADORA DE PROBABILIDADES Y CASA ---
if menu == "Calculadora & House Edge":
    st.header("📊 Probabilidades Matemáticas del Baccarat")
    st.write("Valores estándar calculados para un zapato de 8 mazos (las probabilidades reales del juego).")

    # Métricas principales de Baccarat (Zapato de 8 mazos)
    col1, col2, col3 = st.columns(3)
    col1.metric("Banca (Banker)", "45.86%", "Comisión 5%")
    col2.metric("Jugador (Player)", "44.62%", "Sin comisión")
    col3.metric("Empate (Tie)", "9.52%", "Paga 8:1 / 9:1")

    st.markdown("---")
    st.subheader("💡 Análisis de Valor y Expectativa por Mano")
    
    apuesta = st.selectbox("¿A qué le vas a apostar en esta mano?", ["Banca (Banker)", "Jugador (Player)", "Empate (Tie)"])
    monto_apuesta = st.number_input("Monto de tu apuesta ($)", min_value=1000, value=10000, step=1000)
    
    if apuesta == "Banca (Banker)":
        prob = 0.4586
        pago_neto = monto_apuesta * 0.95 # Descontando el 5% de comisión estándar
        house_edge = "1.06%"
    elif apuesta == "Jugador (Player)":
        prob = 0.4462
        pago_neto = monto_apuesta * 1.0 # Paga 1 a 1
        house_edge = "1.24%"
    else:
        prob = 0.0952
        pago_neto = monto_apuesta * 8.0 # Asumiendo pago 8:1
        house_edge = "14.36% (Alto Riesgo)"

    ev = (prob * pago_neto) - ((1 - prob) * monto_apuesta)
    
    st.info(f"**Ventaja de la Casa (House Edge):** {house_edge}")
    st.metric("Expectativa Matemática (EV) por mano", f"${ev:,.2f}")

    if apuesta == "Empate (Tie)":
        st.warning("⚠️ **Advertencia:** El empate tiene una ventaja de la casa muy alta. Matemáticamente es la apuesta menos recomendada a largo plazo.")
    elif apuesta == "Banca (Banker)":
        st.success("✅ **Apuesta Óptima:** Matemáticamente, la Banca ofrece la probabilidad de éxito más alta a largo plazo a pesar de su comisión.")


# --- MÓDULO 2: GESTIÓN DE BANKROLL Y RIESGO ---
elif menu == "Gestión de Bankroll y Riesgo":
    st.header("💰 Gestión de Capital y Control de Riesgo")
    st.write("Protege tu presupuesto definiendo límites estrictos para las sesiones de casino.")

    bankroll_total = st.number_input("Tu Bankroll Total para la Sesión ($)", min_value=50000, value=500000, step=50000)
    estrategia = st.selectbox("Estrategia de Apuestas", ["Stake Fijo (% del Bankroll)", "Martingala (Progresiva al perder)", "Paroli (Progresiva al ganar)"])

    if estrategia == "Stake Fijo (% del Bankroll)":
        porcentaje = st.slider("Porcentaje de apuesta por mano (%)", min_value=1, max_value=10, value=2)
        monto_sugerido = bankroll_total * (porcentaje / 100)
        st.success(f"🎯 **Apuesta sugerida por mano:** ${monto_sugerido:,.2f}")
        st.write(f"Con este ritmo, resistirías una mala racha de aproximadamente **{int(100/porcentaje)} manos** consecutivas.")

    elif estrategia == "Martingala (Progresiva al perder)":
        base = st.number_input("Valor de la apuesta inicial ($)", min_value=1000, value=5000, step=1000)
        st.warning("⚠️ **Precaución con Martingala:** Duplicas la apuesta tras cada pérdida. Requiere un bankroll profundo para evitar el límite de la mesa.")
        
        # Tabla de progresión rápida
        progresion = [base * (2**i) for i in range(5)]
        df_martingala = pd.DataFrame({
            "Paso / Derrotas seguidas": [f"Pérdida {i+1}" for i in range(5)],
            "Apuesta requerida ($)": progresion,
            "Acumulado arriesgado ($)": np.cumsum(progresion)
        })
        st.table(df_martingala)

    else:
        base = st.number_input("Apuesta base inicial ($)", min_value=1000, value=5000, step=1000)
        st.info("📈 **Estrategia Paroli:** Duplicas tu apuesta cuando ganas para aprovechar las rachas positivas, volviendo a la base cuando pierdes.")


# --- MÓDULO 3: REGISTRO Y PATRONES (ROADMAP) ---
elif menu == "Registro y Patrones (Roadmap)":
    st.header("📝 Registro de Manos en Vivo")
    st.write("Registra los resultados de la mesa para llevar el conteo de la sesión.")

    # Inicializar historial en sesión si no existe
    if 'historial_manos' not in st.session_state:
        st.session_state.historial_manos = []

    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
    
    with col_btn1:
        if st.button("🔴 Gana Banca (B)", use_container_width=True):
            st.session_state.historial_manos.append("B")
    with col_btn2:
        if st.button("🔵 Gana Jugador (P)", use_container_width=True):
            st.session_state.historial_manos.append("P")
    with col_btn3:
        if st.button("🟢 Empate (T)", use_container_width=True):
            st.session_state.historial_manos.append("T")
    with col_btn4:
        if st.button("🧹 Limpiar Historial", use_container_width=True):
            st.session_state.historial_manos = []

    st.markdown("---")
    st.subheader("📈 Resumen de la Sesión Actual")
    
    manos = st.session_state.historial_manos
    total_manos = len(manos)
    
    if total_manos > 0:
        bancas = manos.count("B")
        jugadores = manos.count("P")
        empates = manos.count("T")
        
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("Total Manos", total_manos)
        col_m2.metric("Banca (B)", f"{bancas} ({bancas/total_manos*100:.1f}%)")
        col_m3.metric("Jugador (P)", f"{jugadores} ({jugadores/total_manos*100:.1f}%)")
        col_m4.metric("Empates (T)", f"{empates} ({empates/total_manos*100:.1f}%)")
        
        st.write("**Secuencia de resultados:**")
        # Mostrar los resultados de forma visual en línea
        secuencia_visual = " ".join([("🔴" if m == "B" else "🔵" if m == "P" else "🟢") for m in manos])
        st.markdown(f"### {secuencia_visual}")
    else:
        st.info("Aún no hay manos registradas. Haz clic en los botones superiores a medida que avance la mesa.")
