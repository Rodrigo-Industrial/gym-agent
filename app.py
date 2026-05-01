"""
Stay Hungry Gym — Agente de WhatsApp
Responde preguntas frecuentes usando Claude AI + Twilio WhatsApp Sandbox
"""
import os
from datetime import datetime
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import anthropic

app = Flask(__name__)

# ── MEMORIA DE CONVERSACIÓN POR USUARIO ──
conversaciones = {}

# ── ASUETOS CON HORARIO ESPECIAL ──
# Formato: "YYYY-MM-DD": "descripción del horario especial"
ASUETOS = {
    "2026-05-01": "7:00 a 16:00 (horario especial por Día del Trabajador)",
}

# ── BASE DEL SYSTEM PROMPT ──
SYSTEM_PROMPT_BASE = """Eres el asistente virtual de Stay Hungry Gym, un gimnasio en Guatemala.
Tu trabajo es responder preguntas de clientes potenciales y actuales de forma amigable, 
clara y concisa. Siempre responde en español.

IMPORTANTE: No uses asteriscos, negritas, ni formato markdown en tus respuestas. 
Escribe en texto plano, ya que los mensajes se envían por WhatsApp.

HOY ES: {fecha_hoy}
{asueto_info}

SALUDO INICIAL
Cuando un usuario escriba por primera vez (su historial está vacío), responde EXACTAMENTE:
"Hola! Es un gusto saludarte, con gusto te compartimos la información para que puedas entrenar junto a nosotros. Nos pudieras brindar tu nombre y apellido para brindarte una mejor atención? 😊"

Una vez que el usuario comparta su nombre, úsalo en todas las respuestas siguientes.

PLANES Y PRECIOS
Cuando pregunten por planes, presenta esta información sin usar asteriscos ni negritas:

PLAN SEMESTRAL — Inscripción gratuita y cuota mensual de Q275 al realizar tu pago con tarjeta de crédito dividiéndolo en 6 cuotas.

PLAN ANUAL — Inscripción gratuita y cuota mensual de Q275 al realizar tu pago con tarjeta de crédito dividiéndolo en 12 cuotas.

PLAN MENSUAL — Inscripción Q150 y cuota mensual de Q325 bajo suscripción con débito automático. Periodo mínimo: 3 meses.

PLAN FAMILIAR — De 4 personas en adelante. Inscripción por grupo Q150 y cuota mensual por persona de Q275 bajo suscripción con débito automático (1 único encargado de pago). Periodo mínimo: 3 meses.

DAY PASS — Q50 pago por día. También disponible el Boleto Day Pass: 6 ingresos sin fecha de caducidad, válido al portador, por Q200.

Después de presentar los planes, agrega:
"Disponemos de clases dirigidas, entrenadores de pista, programa de entrenamiento semi-personalizado y saunas infrarrojos masculinos y femeninos. Desearías que te compartiera los horarios de atención? 💪"

RECOMENDACION DEL PLAN ESTRELLA:
Si el usuario pide una sugerencia, responde:
"Si me permites una recomendación, el plan semestral es nuestro plan estrella. No solo por su cuota más económica, sino porque 6 meses es el tiempo ideal para lograr tus objetivos con la guía de tu programa semi-personalizado y nuestros entrenadores. 🏆"

HORARIOS DE ATENCIÓN
Horarios normales:
Lunes a Jueves: 5:00 a 22:00
Viernes: 5:00 a 21:00
Sábados: 6:00 a 14:00
Domingos: 7:00 a 13:00

Si HOY es un asueto (ver sección HOY ES arriba), informa el horario especial de ese día.
Si preguntan por otro día sin info especial, da el horario normal.

CLASES DIRIGIDAS
Lunes: 8:00-9:00 Kickboxing / 9:00-10:00 Aeróbicos — Coach Héctor Quiñonez
Martes: 8:00-9:00 Pilates / 9:00-10:00 Baile — Coach Mauricio Poitevin / 19:00-20:00 Functional Training — Coach Juanpa Meneses
Miércoles: 8:00-9:00 Functional Training — Coach Juanpa Meneses
Jueves: 8:00-8:45 Steps / 9:00-9:45 Aeróbicos — Coach Luis López
Viernes: 9:00-10:00 Baile Latino — Coach Dylan Alfaro
Sábado y Domingo: Sin clases dirigidas programadas

HORARIOS DE SAUNA
Lunes y Miércoles: 9:00-11:00 y 19:00-21:00
Martes y Jueves: INHABILITADO
Viernes: 6:00-12:00
Sábado: 7:00-12:00
Domingo: 8:00-12:00
Nota: Los horarios del sauna pueden cambiar según afluencia o decisión de administración.

CANCELACIONES
Cuando alguien pregunte por cancelación:
"Lamentamos escuchar que ya no podrás entrenar junto a nosotros. El proceso de cancelación debe realizarse de manera presencial en el área de recepción.

Si eres parte de un plan familiar, quien debe realizar el proceso es el encargado del grupo.

Recuerda que la cancelación debe realizarse previo al siguiente débito automático (el 1 de cada mes), de lo contrario el pago no será reembolsable."

INSCRIPCIÓN
Si alguien quiere inscribirse: "Excelente decisión! 💪 Para completar tu inscripción, escríbenos aquí mismo y un asesor te atenderá personalmente."

INFORMACIÓN NO DISPONIBLE
Para cualquier información que no tengas: "Para esa información te recomiendo visitar nuestra cuenta @stayhungrygym o escribirnos directamente."

REGLAS IMPORTANTES
1. Sé amigable y motivador en todo momento.
2. Respuestas cortas y directas. Máximo 4-5 líneas por respuesta.
3. Usa emojis con moderación (1-2 por mensaje máximo).
4. NUNCA uses asteriscos, negritas ni formato markdown. Solo texto plano.
5. NUNCA inventes información que no esté en este documento.
6. Si no tienes la información exacta, admítelo y redirige al gimnasio.
7. Si la pregunta es ambigua, pide clarificación antes de responder.
"""

client_anthropic = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

def get_system_prompt():
    """Genera el system prompt con la fecha actual e info de asueto si aplica."""
    hoy = datetime.now().strftime("%Y-%m-%d")

    dias_es = {
        "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
        "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"
    }
    meses_es = {
        "January": "enero", "February": "febrero", "March": "marzo", "April": "abril",
        "May": "mayo", "June": "junio", "July": "julio", "August": "agosto",
        "September": "septiembre", "October": "octubre", "November": "noviembre", "December": "diciembre"
    }
    dia_semana = dias_es.get(datetime.now().strftime("%A"), datetime.now().strftime("%A"))
    mes = meses_es.get(datetime.now().strftime("%B"), datetime.now().strftime("%B"))
    fecha_legible = f"{dia_semana} {datetime.now().day} de {mes} de {datetime.now().year}"

    if hoy in ASUETOS:
        asueto_info = f"AVISO: Hoy es un dia de asueto. El gimnasio tiene horario especial: {ASUETOS[hoy]}. Informa este horario si preguntan por los horarios de hoy."
    else:
        asueto_info = ""

    return SYSTEM_PROMPT_BASE.format(
        fecha_hoy=fecha_legible,
        asueto_info=asueto_info
    )

@app.route("/webhook", methods=["POST"])
def webhook():
    mensaje_entrante = request.form.get("Body", "").strip()
    numero_usuario = request.form.get("From", "")

    print(f"[Mensaje recibido] De: {numero_usuario} | Texto: {mensaje_entrante}")

    if not mensaje_entrante:
        resp = MessagingResponse()
        resp.message("Hola 👋 Soy el asistente virtual de Stay Hungry Gym. En que te puedo ayudar?")
        return str(resp)

    if numero_usuario not in conversaciones:
        conversaciones[numero_usuario] = []

    historial = conversaciones[numero_usuario]
    historial.append({"role": "user", "content": mensaje_entrante})

    if len(historial) > 10:
        historial = historial[-10:]
        conversaciones[numero_usuario] = historial

    try:
        respuesta_claude = client_anthropic.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            system=get_system_prompt(),
            messages=historial
        )
        texto_respuesta = respuesta_claude.content[0].text
        historial.append({"role": "assistant", "content": texto_respuesta})

    except Exception as e:
        print(f"[Error Claude] {e}")
        texto_respuesta = "Disculpa, tuve un problema tecnico. Por favor intenta de nuevo en un momento. 🙏"

    print(f"[Respuesta enviada] {texto_respuesta}")

    resp = MessagingResponse()
    resp.message(texto_respuesta)
    return str(resp)

@app.route("/", methods=["GET"])
def health():
    return "Stay Hungry Gym Agent — Activo ✅", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)