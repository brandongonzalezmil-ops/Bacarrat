import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Baccarat Analytics Pro", page_icon="🃏", layout="centered"
)

st.title("🃏 Baccarat Analytics & Bankroll Pro")
st.write("Asistente inteligente de patrones, rachas y dimensionamiento de apuestas en vivo.")

# Menú lateral
menu = st.sidebar.selectbox(
    "Menú de Baccarat", 
    ["Asistente de Rachas & Apuestas", "Calculadora & House Edge", "Gestión de Bankroll y Riesgo", "Registro de Manos"]
)

# Inicializar historial en sesión si no existe
if 'historial_manos' not in st.session_state:
    st.session_state.historial_manos = []

# --- MÓDULO 1: ASISTENTE DE RACHAS Y APUESTAS INTELIGENTES ---
if menu == "Asistente de Rachas & Apuestas":
    st.header("🎯 Asistente de Mesa en Vivo")
    st.write("Registra el resultado de la mano actual. El asistente evaluará la tendencia y te dirá **a qué apostar** y **si debes subir o mantener tu stake**.")

    # Configuración de la apuesta base del usuario
    col_cfg1, col_cfg2 = st.columns(2)
    with col_cfg1:
        apuesta_base = st.number_input("Tu Apuesta Base ($)", min_value=1000, value=10000, step=1000)
    with col_cfg2:
        bankroll_disponible = st.number_input("Bankroll actual de sesión ($)", min_value=10000, value=300000, step=10000)

    st.markdown("---")
    st.write("### 📌 Registrar Resultado de la Mano Recién Jugada:")
    
    # Botones de entrada rápida
    col_b1, col_b2, col_b3, col_b4 = st.columns(4)
    with col_b1:
        if st.button("🔴 Gana Banca (B)", use_container_width=True):
            st.session_state.historial_manos.append("B")
    with col_b2:
        if st.button("🔵 Gana Jugador (P)", use_container_width=True):
            st.session_state.historial_manos.append("P")
    with col_b3:
        if st.button("🟢 Empate (T)", use_container_width=True):
            st.session_state.historial_manos.append("T")
    with col_b4:
        if st.button("🧹 Reiniciar Mesa", use_container_width=True):
            st.session_state.historial_manos = []

    st.markdown("---")
    
    manos = st.session_state.historial_manos
    total_manos = len(manos)

    if total_manos > 0:
        # Mostrar secuencia visual de la mesa
        st.subheader("📈 Historial de la Mesa")
        secuencia_visual = " ".join([("🔴 [B]" if m == "B" else "🔵 [P]" if m == "P" else "🟢 [T]") for m in manos])
        st.markdown(f"### {secuencia_visual}")
        
        # --- LÓGICA DEL ASISTENTE Y GESTIÓN DE STAKE POR RACHAS ---
        manos_sin_empates = [m for m in manos if m != "T"]
        
        st.markdown("---")
        st.subheader("🤖 Recomendación del Asistente para la Siguiente Mano")

        if len(manos_sin_empates) > 0:
            ultima = manos_sin_empates[-1]
            
            # Calcular racha actual de la última opción
            racha_actual = 1
            for i in range(len(manos_sin_empates) - 2, -1, -1):
                if manos_sin_empates[i] == ultima:
                    racha_actual += 1
                else:
                    break
            
            # Análisis de recomendación y manejo del stake
            if racha_actual >= 3:
                # Racha fuerte: Sugerir seguir la racha y subir ligeramente la apuesta (Paroli moderado)
                sugerencia = ultima
                multiplicador_stake = 1.5 if racha_actual == 3 else (2.0 if racha_actual >= 4 else 1.0)
                consejo_apuesta = f"Seguir la racha -> {'Banca (Banker)' if sugerencia == 'B' else 'Jugador (Player)'}"
                
                if racha_actual >= 4:
                    consejo_stake = f"🔥 **¡Racha caliente de {racha_actual}! Se recomienda SUBIR la apuesta.** (Multiplica tu base x2)"
                    monto_sugerido = apuesta_base * 2.0
                else:
                    consejo_stake = f"📈 **Racha en formación ({racha_actual} seguidas). Puedes subir levemente.** (Multiplica tu base x1.5)"
                    monto_sugerido = apuesta_base * 1.5
                    
            elif len(manos_sin_empates) >= 2 and manos_sin_empates[-1] != manos_sin_empates[-2]:
                # Patrón de alternancia (Ping-Pong)
                sugerencia = "P" if ultima == "B" else "B"
                consejo_apuesta = f"Alternancia (Ping-Pong) -> {'Banca (Banker)' if sugerencia == 'B' else 'Jugador (Player)'}"
                consejo_stake = "⚖️ **Mesa inestable (Alternando). Mantén tu Apuesta Base.** No arriesgues de más."
                monto_sugerido = apuesta_base
            else:
                # Sin patrón claro
                sugerencia = "B" # Por ventaja estadística pura de la casa
                consejo_apuesta = "Banca (Banker) (Por mejor probabilidad matemática base)"
                consejo_stake = "🛡️ **Sin patrón claro. Juega prudente con tu Apuesta Base fija.**"
                monto_sugerido = apuesta_base

            # Mostrar resultados visuales limpios al usuario
            nombre_sugerencia_larga = "Banca (Banker)" if sugerencia == "B" else "Jugador (Player)"
            
            st.success(f"🎯 **A qué apostar:** {nombre_sugerencia_larga}")
            st.info(f"💰 **Sugerencia de capital:** {consejo_stake}\n\n👉 **Monto recomendado para esta mano:** **${monto_sugerido:,.0f}**")
            
            if monto_sugerido > bankroll_disponible:
                st.warning("⚠️ Cuidado: El monto sugerido supera tu bankroll actual disponible para esta sesión.")
        else:
            st.warning("Solo han salido empates. Espera una mano ganadora de Banca o Jugador para activar el asistente.")

        # Estadísticas rápidas de la sesión
        bancas = manos.count("B")
        jugadores = manos.count("P")
        empates = manos.count("T")
        
        st.markdown("---")
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Total Bancas (B)", bancas)
        col_m2.metric("Total Jugadores (P)", jugadores)
        col_m3.metric("Total Empates (T)", empates)
    else:
        st.info("👋 ¡La mesa está lista! Registra los resultados de la mano conforme salgan para que el asistente empiece a guiarte con las apuestas y el incremento por rachas.")


# --- MÓDULO 2: CALCULADORA Y HOUSE EDGE ---
elif menu == "Calculadora & House Edge":
    st.header("📊 Probabilidades Matemáticas del Baccarat")
    col1, col2, col3 = st.columns(3)
    col1.metric("Banca (Banker)", "45.86%", "Comisión 5%")
    col2.metric("Jugador (Player)", "44.62%", "Sin comisión")
    col3.metric("Empate (Tie)", "9.52%", "Paga 8:1")

    st.markdown("---")
    apuesta = st.selectbox("¿A qué le vas a apostar?", ["Banca (Banker)", "Jugador (Player)", "Empate (Tie)"])
    monto_apuesta = st.number_input("Monto de tu apuesta ($)", min_value=1000, value=10000, step=1000)
    
    if apuesta == "Banca (Banker)":
        prob = 0.4586
        pago_neto = monto_apuesta * 0.95
        house_edge = "1.06%"
    elif apuesta == "Jugador (Player)":
        prob = 0.4462
        pago_neto = monto_apuesta * 1.0
        house_edge = "1.24%"
    else:
        prob = 0.0952
        pago_neto = monto_apuesta * 8.0
        house_edge = "14.36%"

    ev = (prob * pago_neto) - ((1 - prob) * monto_apuesta)
    st.info(f"**Ventaja de la Casa:** {house_edge}")
    st.metric("Expectativa Matemática (EV) por mano", f"${ev:,.2f}")


# --- MÓDULO 3: GESTIÓN DE BANKROLL Y RIESGO ---
elif menu == "Gestión de Bankroll y Riesgo":
    st.header("💰 Control de Capital")
    bankroll_total = st.number_input("Tu Bankroll Total ($)", min_value=50000, value=500000, step=50000)
    porcentaje = st.slider("Porcentaje de apuesta por mano (%)", min_value=1, max_value=10, value=2)
    monto_sugerido = bankroll_total * (porcentaje / 100)
    st.success(f"🎯 **Apuesta sugerida por mano:** ${monto_sugerido:,.2f}")


# --- MÓDULO 4: REGISTRO DE MANOS ---
elif menu == "Registro de Manos":
    st.header("📝 Historial Completo")
    if st.button("Borrar todo el historial"):
        st.session_state.historial_manos = []
    st.write(f"Manos registradas hasta ahora: {len(st.session_state.historial_manos)}")
    st.write(st.session_state.historial_manos)
