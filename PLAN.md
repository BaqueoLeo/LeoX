# LeoX — Plan Técnico del Asistente Personal IA por WhatsApp

> **Estado:** Planificación v2
> **Fecha:** 2026-03-19
> **Autor:** BaqueoLeo

---

## 1. Visión General

LeoX no es un asistente. Es un **ente digital** con personalidad propia que vive en tu Raspberry Pi y te habla por WhatsApp como un amigo cercano. Analiza tu vida de forma autónoma — conversaciones, correos, calendario — y actúa sin que tengas que pedírselo. Sus respuestas son cortas, directas y con tono de alguien que te conoce bien. Con el tiempo, construye una memoria viva de quién eres, qué te gusta y cómo piensas.

---

## 2. Objetivos Principales

- Monitoreo constante y autónomo sin intervención del usuario
- Detectar compromisos en conversaciones de WhatsApp y correos → crear eventos/recordatorios automáticamente
- Comunicación proactiva: resúmenes, alertas, check-ins — como un amigo que sabe tu agenda
- Respuestas ultra-condensadas, coloquiales, sin frases de asistente
- Construir dos capas de memoria acumulativa: **recuerdos** y **preferencias**
- Personalidad que evoluciona y se adapta con el tiempo

---

## 3. Arquitectura General

```
┌─────────────────────────────────────────────────────────────────┐
│                       RASPBERRY PI LOCAL                        │
│                                                                 │
│  ┌─────────────────┐       ┌────────────────────────────────┐  │
│  │  WhatsApp Layer │       │       Python AI Brain          │  │
│  │   (Node.js)     │◄─────►│                                │  │
│  │   Baileys       │ REST  │  - Orquestador                 │  │
│  │                 │  API  │  - AI Router (fallback)        │  │
│  │  Puerto: 3000   │       │  - Commitment Detector         │  │
│  └─────────────────┘       │  - Scheduler autónomo          │  │
│                            │  - Gestor de memoria           │  │
│                            │  Puerto: 8000                  │  │
│                            └───────────────┬────────────────┘  │
│                                            │                   │
│              ┌─────────────────────────────┴──────────────┐   │
│              │           ChromaDB (local)                  │   │
│              │                                             │   │
│              │  Colección: "memories"    → hechos vividos  │   │
│              │  Colección: "prefs"       → preferencias    │   │
│              │  Colección: "people"      → quiénes son     │   │
│              │  Colección: "context"     → conv. activa    │   │
│              └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
         │                            │
         │ WhatsApp                   │ APIs externas
         ▼                            ▼
  [Tu número personal]      [iCloud CalDAV, Gmail OAuth2,
                             Claude / Gemini / OpenAI APIs]
```

---

## 4. Stack Tecnológico

| Capa | Tecnología | Rol |
|------|-----------|-----|
| WhatsApp | **Baileys** (Node.js) | Conexión y sesión de WhatsApp |
| Bridge interno | **FastAPI** (Python) | API REST entre Baileys y el cerebro IA |
| Cerebro IA | **Python 3.11+** | Orquestación, lógica, scheduling |
| Memoria corta | **In-memory (deque)** | Ventana de conversación activa |
| Memoria larga | **ChromaDB** (local) | 4 colecciones vectoriales |
| Análisis de compromisos | **LLM + parser estructurado** | Extrae eventos/planes de texto |
| Calendario | **iCloud CalDAV** (caldav lib) | Leer, crear y modificar eventos |
| Reminders | **iCloud Reminders** (caldav) | Leer, crear y modificar recordatorios |
| Email | **Gmail API** (OAuth2) | Monitoreo de correos + detección de compromisos |
| Scheduler | **APScheduler** (Python) | Tareas autónomas programadas |
| Config | **python-dotenv** | Variables de entorno y secrets |
| Containerización | **Docker + docker-compose** | Servicios aislados en el Pi |

---

## 5. Cadena de Fallback de IA

El sistema intenta los modelos en orden. Si uno falla (timeout, error, límite), pasa al siguiente.

```
Intento 1 → Claude (Anthropic)
  ├── claude-opus-4-6
  ├── claude-sonnet-4-6
  └── claude-haiku-4-5

Intento 2 → Gemini (Google)
  ├── gemini-2.0-pro-exp
  ├── gemini-2.0-flash
  └── gemini-1.5-pro

Intento 3 → OpenAI
  ├── gpt-4o
  ├── o1-mini
  └── gpt-4o-mini
```

- Timeout por modelo: 15 segundos
- Se registra qué modelo respondió en cada interacción
- Si todos fallan: mensaje corto y honesto al usuario

---

## 6. Sistema de Memoria Dual (el corazón del proyecto)

Este es el módulo más importante. LeoX construye dos tipos de memoria que crecen con el tiempo.

### 6.1 Recuerdos (`memories`)
Hechos concretos que le pasaron al usuario o que LeoX observó.

```
"El 15 de marzo Leo tuvo reunión con su equipo y llegó tarde por el tráfico"
"El domingo Leo fue al cine con Ana a ver una película de terror"
"Leo mencionó que tiene un proyecto importante el viernes"
```

**Trigger de escritura:** Después de cada conversación significativa, el LLM extrae hechos relevantes y los guarda como embeddings.

### 6.2 Preferencias (`prefs`)
Lo que LeoX aprende sobre cómo es el usuario: gustos, hábitos, carácter.

```
"Leo prefiere mensajes cortos"
"A Leo no le gusta que lo molesten antes de las 9am"
"Leo toma café por las mañanas"
"Leo suele quedar con Carlos los viernes"
"Leo es directo y no le gustan las formalidades"
```

**Trigger de escritura:** LLM extrae inferencias de comportamiento periódicamente.

### 6.3 Personas (`people`)
Mapa de las personas en la vida del usuario.

```
"Carlos: amigo cercano de Leo, suelen salir los viernes, trabaja en finanzas"
"Ana: pareja/amiga de Leo, van al cine juntos"
"Mamá: le escribe seguido, cumpleaños en julio"
```

### 6.4 Recuperación contextual
Antes de cada respuesta, ChromaDB hace búsqueda semántica para traer los recuerdos y preferencias más relevantes al contexto actual. Esto hace que LeoX "recuerde" sin que el usuario tenga que repetirle nada.

---

## 7. Detector de Compromisos (Commitment Detector)

Módulo clave para la autonomía. Analiza mensajes de WhatsApp y correos buscando planes implícitos o explícitos.

### 7.1 Cómo funciona

```
Cada hora:
  ├── Leer conversaciones de WhatsApp de las últimas 2 horas
  ├── Leer correos de Gmail de las últimas 2 horas
  └── Para cada thread → LLM analiza con este objetivo:
        "¿Hay algún plan, cita, reunión o tarea acordada?
         Si sí: extrae fecha, hora, persona, descripción.
         Si no: descarta."
```

### 7.2 Estructura del compromiso detectado

```json
{
  "tipo": "evento | recordatorio | tarea",
  "descripcion": "Cena con Carlos",
  "fecha": "2026-03-21",
  "hora": "20:00",
  "persona": "Carlos",
  "fuente": "whatsapp | gmail",
  "confianza": 0.9,
  "texto_original": "dale, nos vemos el sábado a las 8"
}
```

### 7.3 Flujo de confirmación

```
LeoX detecta compromiso con confianza > 0.7
        │
        ▼
Envía mensaje corto al usuario:
"Oye, vi que quedaste con Carlos el sáb a las 8 🍽️ ¿lo agendo?"
        │
  ┌─────┴─────┐
  │ Sí / Ok   │ No / Error
  ▼           ▼
Crea evento  Descarta y
en iCloud    aprende
```

Si confianza > 0.95 (muy obvio): crea directamente y avisa en lugar de preguntar.

---

## 8. Módulos del Sistema (Python)

### 8.1 `brain/`
- `orchestrator.py` — Enrutador central: clasifica cada mensaje entrante y decide acción
- `ai_router.py` — Fallback Claude → Gemini → OpenAI con timeout y logging
- `personality.py` — System prompt base + inyección dinámica de memoria
- `response_formatter.py` — Asegura que la respuesta sea corta y coloquial

### 8.2 `integrations/`
- `icloud_calendar.py` — CRUD de eventos via CalDAV
- `icloud_reminders.py` — CRUD de recordatorios via CalDAV
- `gmail_monitor.py` — Leer correos + marcar como procesados

### 8.3 `memory/`
- `short_term.py` — Buffer de conversación activa (últimos 20 mensajes)
- `long_term.py` — ChromaDB: 4 colecciones, búsqueda semántica
- `memory_writer.py` — Extrae y escribe recuerdos/preferencias post-conversación
- `embedder.py` — Genera embeddings (OpenAI text-embedding-3-small o local)

### 8.4 `commitment/`
- `detector.py` — Analiza textos buscando compromisos
- `parser.py` — Estructura el compromiso en JSON
- `calendar_writer.py` — Crea/modifica eventos e iCloud reminders
- `confirmation.py` — Maneja el flujo de confirmación con el usuario

### 8.5 `scheduler/`
- `jobs.py` — Registro y configuración de todos los jobs
- `morning_brief.py` — Resumen matutino: agenda del día + pendientes
- `event_reminder.py` — Alerta N minutos antes de cada evento
- `conflict_detector.py` — Detecta solapamientos en el calendario
- `silence_checker.py` — Check-in si llevas horas sin actividad
- `commitment_scan.py` — Job horario de análisis de WhatsApp y Gmail
- `memory_consolidator.py` — Job nocturno: consolida recuerdos del día

### 8.6 `whatsapp/`
- `client.py` — HTTP client para hablar con Baileys (Node.js)
- `message_parser.py` — Normaliza mensajes entrantes
- `history_fetcher.py` — Obtiene historial de chats para el detector de compromisos

---

## 9. Personalidad de LeoX

LeoX no es un asistente. Tiene voz propia.

### Reglas de respuesta
- **Máximo 3 líneas** salvo que el usuario pida más detalle
- Sin saludos formales, sin "¡Claro!", sin "Por supuesto"
- Sin emojis excesivos, máximo 1 por mensaje si viene al caso
- Usa el nombre del usuario naturalmente, no en cada mensaje
- Puede usar jerga, contracciones, lenguaje casual
- Si no sabe algo, lo dice directo: "no sé" o "no tengo eso claro"
- Puede hacer preguntas breves de seguimiento como haría un amigo

### Ejemplos de tono

| ❌ Asistente | ✅ LeoX |
|-------------|---------|
| "¡Hola! ¿En qué puedo ayudarte hoy?" | (no saluda innecesariamente) |
| "Por supuesto, con gusto te ayudo con eso." | "Va, ya lo agendo." |
| "Tienes una reunión importante mañana a las 10am con tu equipo." | "Mañana 10am reunión de equipo. ¿ya tienes el material listo?" |
| "He detectado que podrías tener un compromiso." | "Oye, ¿eso con Carlos el viernes va?" |

### Evolución de personalidad
Con el tiempo LeoX adapta su tono según lo que aprende:
- Si el usuario es escueto → LeoX se vuelve más escueto
- Si el usuario bromea → LeoX empieza a bromear
- Si hay temas recurrentes → LeoX los trae sin que se los pidan

---

## 10. Comportamientos Autónomos

| Comportamiento | Trigger | Frecuencia |
|---------------|---------|------------|
| Resumen matutino | Hora fija configurable | Diario |
| Recordatorio de evento | N min antes del evento | Por evento |
| Alerta de conflicto de horario | Al detectar solapamiento | Tiempo real |
| Check-in por silencio | Sin actividad N horas | Configurable |
| Scan de compromisos en WhatsApp | Job periódico | Cada hora |
| Scan de compromisos en Gmail | Job periódico | Cada hora |
| Consolidación de memoria | Resumen del día | Diario (noche) |
| Sync de calendario | iCloud CalDAV poll | Cada 10 min |

---

## 11. Flujos Principales

### 11.1 Mensaje entrante (usuario escribe)
```
Usuario escribe → Baileys → HTTP POST → Orchestrator
  │
  ├── Recuperar contexto corto (últimos 20 msgs)
  ├── Buscar memoria relevante en ChromaDB
  ├── Construir prompt: system + memoria + contexto + mensaje
  ├── AI Router (Claude → Gemini → OpenAI)
  ├── Formatear respuesta (corta, coloquial)
  ├── Enviar via Baileys
  └── Post-proceso: ¿guardar recuerdo nuevo?
```

### 11.2 Scan horario de compromisos
```
APScheduler dispara cada hora
  │
  ├── Fetch chats de WhatsApp (últimas 2h)
  ├── Fetch correos de Gmail (últimas 2h)
  ├── Para cada conversación → Commitment Detector
  ├── Filtrar duplicados (ya agendados)
  ├── Para compromisos con alta confianza:
  │     └── Crear evento/recordatorio en iCloud silenciosamente
  │         + notificar al usuario brevemente
  └── Para compromisos con media confianza:
        └── Preguntar al usuario antes de crear
```

### 11.3 Consolidación nocturna de memoria
```
APScheduler dispara a medianoche
  │
  ├── Revisar todas las conversaciones del día
  ├── LLM extrae hechos relevantes → guardar en "memories"
  ├── LLM extrae inferencias de comportamiento → guardar en "prefs"
  └── Actualizar/enriquecer perfiles de personas en "people"
```

---

## 12. Estructura del Repositorio

```
LeoX/
├── README.md
├── PLAN.md
├── docker-compose.yml
├── .env.example
│
├── whatsapp-service/              # Node.js (Baileys)
│   ├── package.json
│   ├── index.js                   # Express + Baileys + endpoints
│   └── session/                   # Sesión persistente WhatsApp
│
├── brain/                         # Python - Núcleo
│   ├── main.py                    # FastAPI app
│   ├── orchestrator.py
│   ├── ai_router.py
│   ├── personality.py
│   └── response_formatter.py
│
├── integrations/
│   ├── icloud_calendar.py         # CRUD eventos CalDAV
│   ├── icloud_reminders.py        # CRUD recordatorios CalDAV
│   └── gmail_monitor.py           # Gmail OAuth2
│
├── memory/
│   ├── short_term.py
│   ├── long_term.py               # ChromaDB wrapper
│   ├── memory_writer.py           # Extractor de recuerdos/preferencias
│   └── embedder.py
│
├── commitment/
│   ├── detector.py                # Análisis de texto por compromisos
│   ├── parser.py                  # Estructura el compromiso en JSON
│   ├── calendar_writer.py         # Crea eventos/reminders en iCloud
│   └── confirmation.py            # Flujo de confirmación con usuario
│
├── scheduler/
│   ├── jobs.py                    # Registro de todos los jobs
│   ├── morning_brief.py
│   ├── event_reminder.py
│   ├── conflict_detector.py
│   ├── silence_checker.py
│   ├── commitment_scan.py         # Job horario (WhatsApp + Gmail)
│   └── memory_consolidator.py    # Job nocturno
│
├── whatsapp/
│   ├── client.py
│   ├── message_parser.py
│   └── history_fetcher.py
│
├── requirements.txt
└── .env.example
```

---

## 13. Variables de Entorno

```bash
# IA - APIs
ANTHROPIC_API_KEY=
GOOGLE_AI_API_KEY=
OPENAI_API_KEY=

# WhatsApp
WHATSAPP_SERVICE_URL=http://localhost:3000
MY_WHATSAPP_NUMBER=+1234567890        # Tu número personal

# iCloud
ICLOUD_USERNAME=tu@icloud.com
ICLOUD_PASSWORD=app_specific_password  # Contraseña específica de app (no la principal)

# Gmail
GMAIL_CREDENTIALS_PATH=./credentials.json
GMAIL_TOKEN_PATH=./token.json

# ChromaDB
CHROMA_PERSIST_DIR=./chroma_data

# Scheduler
MORNING_BRIEF_TIME=08:00
EVENT_REMINDER_MINUTES=15
SILENCE_CHECK_HOURS=6
COMMITMENT_SCAN_INTERVAL_HOURS=1
MEMORY_CONSOLIDATION_TIME=23:30

# Personalidad
LEOX_NAME=Leo                          # Cómo LeoX llama al usuario
COMMITMENT_AUTO_CREATE_THRESHOLD=0.95  # Confianza para crear sin confirmar
COMMITMENT_ASK_THRESHOLD=0.70          # Confianza para preguntar antes de crear

# AI
AI_TIMEOUT_SECONDS=15
EMBEDDING_MODEL=text-embedding-3-small
```

---

## 14. Fases de Desarrollo

### Fase 1 — Infraestructura base (MVP)
- [ ] Docker-compose: Baileys (Node.js) + FastAPI (Python)
- [ ] Baileys conectado y enviando/recibiendo mensajes al Pi
- [ ] AI Router funcionando con fallback Claude → Gemini → OpenAI
- [ ] Respuestas básicas llegando al usuario por WhatsApp

### Fase 2 — Personalidad y memoria corta
- [ ] System prompt de personalidad base
- [ ] Buffer de conversación activa (short-term memory)
- [ ] Response formatter (respuestas cortas y coloquiales)

### Fase 3 — Integraciones de datos
- [ ] iCloud CalDAV: leer y crear/modificar eventos
- [ ] iCloud Reminders: leer y crear/modificar recordatorios
- [ ] Gmail OAuth2: leer correos importantes

### Fase 4 — Autonomía proactiva
- [ ] APScheduler con todos los jobs
- [ ] Resumen matutino
- [ ] Alertas de eventos y conflictos
- [ ] Scan de WhatsApp y Gmail cada hora

### Fase 5 — Commitment Detector
- [ ] Detector de compromisos en conversaciones de WhatsApp
- [ ] Detector de compromisos en correos de Gmail
- [ ] Flujo de confirmación con el usuario
- [ ] Auto-creación de eventos/recordatorios en iCloud

### Fase 6 — Memoria larga y evolución
- [ ] ChromaDB con 4 colecciones
- [ ] Memory writer: extracción de recuerdos y preferencias
- [ ] Consolidación nocturna
- [ ] Inyección dinámica de memoria en el contexto
- [ ] Evolución de personalidad basada en preferencias aprendidas

---

## 15. Consideraciones de Seguridad

- **iCloud:** Solo contraseña específica de app, nunca la contraseña principal
- **Gmail:** OAuth2 con scope de solo lectura
- **Baileys:** Sesión cifrada localmente, número dedicado solo para LeoX
- **APIs de IA:** Keys exclusivamente en `.env`, nunca en código ni logs
- **Red:** El Pi no expone puertos al exterior; todo el tráfico es local
- **ChromaDB:** Base de datos local, nunca se sincroniza a la nube
- **Datos personales:** WhatsApp y correos procesados en memoria, no se guardan en raw

---

*Documento actualizado con autonomía creativa, memory dual y commitment detection.*
