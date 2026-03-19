# LeoX — Plan Técnico del Asistente Personal IA por WhatsApp

> **Estado:** Planificación
> **Fecha:** 2026-03-19
> **Autor:** BaqueoLeo

---

## 1. Visión General

LeoX es un asistente personal con IA que funciona **exclusivamente por WhatsApp**, capaz de monitorear proactivamente el calendario, recordatorios, correos y mensajes del usuario, enviando resúmenes y alertas sin necesidad de que el usuario inicie la conversación. Está diseñado para vivir en un **Raspberry Pi local** y comunicarse a través de un número de WhatsApp personal dedicado.

---

## 2. Objetivos Principales

- Monitoreo constante y autónomo de agenda, recordatorios, Gmail y WhatsApp
- Comunicación proactiva: resumen matutino, alertas de eventos, conflictos de calendario
- Respuestas naturales y contextuales via WhatsApp
- Memoria a largo plazo vectorizada (recuerda conversaciones, preferencias, patrones)
- Alta disponibilidad con fallback automático entre modelos de IA

---

## 3. Arquitectura General

```
┌─────────────────────────────────────────────────────────────┐
│                     RASPBERRY PI LOCAL                      │
│                                                             │
│  ┌─────────────────┐      ┌──────────────────────────────┐ │
│  │  WhatsApp Layer │      │       Python AI Brain        │ │
│  │   (Node.js)     │◄────►│                              │ │
│  │   Baileys       │ REST │  - Orquestador principal     │ │
│  │                 │  API │  - Fallback de modelos IA    │ │
│  │  Puerto: 3000   │      │  - Scheduler de tareas       │ │
│  └─────────────────┘      │  - Integraciones externas    │ │
│                           │  - Memoria vectorial         │ │
│                           │                              │ │
│                           │  Puerto: 8000                │ │
│                           └──────────────────────────────┘ │
│                                        │                    │
│                           ┌────────────▼──────────────────┐ │
│                           │      ChromaDB / Qdrant        │ │
│                           │      (Memoria vectorial)      │ │
│                           └───────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
         │                           │
         │ WhatsApp                  │ APIs externas
         ▼                           ▼
  [Tu número personal]     [iCloud CalDAV, Gmail OAuth2,
                            Claude API, Gemini API, OpenAI API]
```

---

## 4. Stack Tecnológico

| Capa | Tecnología | Rol |
|------|-----------|-----|
| WhatsApp | **Baileys** (Node.js) | Conexión y sesión de WhatsApp |
| Bridge interno | **FastAPI** (Python) | API REST entre Baileys y el cerebro IA |
| Cerebro IA | **Python 3.11+** | Orquestación, lógica, scheduling |
| Memoria corta | **In-memory (dict + deque)** | Contexto de conversación activa |
| Memoria larga | **ChromaDB** (local) | Embeddings de conversaciones y preferencias |
| Calendario | **iCloud CalDAV** (caldav lib) | Eventos y recordatorios de Apple |
| Reminders | **iCloud Reminders** (caldav) | Apple Reminders via CalDAV |
| Email | **Gmail API** (OAuth2) | Monitoreo de correos importantes |
| Scheduler | **APScheduler** (Python) | Tareas programadas y monitoreo periódico |
| Config | **python-dotenv** | Variables de entorno y secrets |
| Containerización | **Docker + docker-compose** | Servicios aislados en el Pi |

---

## 5. Cadena de Fallback de IA

El sistema intenta los modelos en este orden. Si un modelo falla (timeout, error de API, límite de tokens), pasa automáticamente al siguiente.

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

**Lógica de fallback:**
- Timeout por modelo: 15 segundos
- Se registra en logs qué modelo respondió
- Si todos fallan: se envía mensaje de error amigable al usuario

---

## 6. Módulos del Sistema (Python)

### 6.1 `brain/` — Orquestador principal
- `orchestrator.py` — Recibe mensajes de Baileys, decide si responder o actuar
- `ai_router.py` — Implementa el fallback entre Claude → Gemini → OpenAI
- `system_prompt.py` — Prompt del sistema personalizable por el usuario

### 6.2 `integrations/` — Conectores externos
- `icloud_calendar.py` — Lee eventos via CalDAV
- `icloud_reminders.py` — Lee y crea recordatorios via CalDAV
- `gmail_monitor.py` — Lee correos importantes via Gmail API

### 6.3 `memory/` — Memoria del asistente
- `short_term.py` — Buffer de conversación activa (últimos N mensajes)
- `long_term.py` — ChromaDB: almacena y recupera contexto relevante por embeddings
- `embedder.py` — Genera embeddings (puede usar OpenAI o un modelo local)

### 6.4 `scheduler/` — Tareas autónomas
- `morning_brief.py` — Resumen matutino diario (hora configurable)
- `event_reminder.py` — Alertas X minutos antes de cada evento
- `conflict_detector.py` — Detecta solapamientos en el calendario
- `silence_checker.py` — Check-in si no hay actividad en N horas
- `email_monitor.py` — Polling de Gmail cada N minutos

### 6.5 `whatsapp/` — Bridge con Baileys (Node.js)
- `client.py` — HTTP client que habla con el servicio Node.js
- `message_parser.py` — Normaliza mensajes entrantes de WhatsApp

---

## 7. Servicio WhatsApp (Node.js / Baileys)

```
whatsapp-service/
├── index.js          # Servidor Express + Baileys
├── session/          # Sesión persistente de WhatsApp (QR code una vez)
└── package.json
```

**Flujo:**
1. Baileys se conecta con QR code (solo la primera vez)
2. Escucha mensajes entrantes → los envía a Python via HTTP POST
3. Expone endpoint `POST /send` para que Python le ordene enviar mensajes
4. La sesión se persiste en disco para no escanear QR cada reinicio

---

## 8. Comportamientos Autónomos y Proactivos

| Comportamiento | Trigger | Frecuencia |
|---------------|---------|------------|
| Resumen matutino | Hora fija (ej: 8:00 AM) | Diario |
| Recordatorio de evento | X min antes del evento | Por evento |
| Alerta de conflicto | Al detectar solapamiento | Tiempo real |
| Check-in por silencio | Si no hay actividad en N horas | Configurable |
| Revisión de correos | Gmail polling | Cada 15 min |
| Sincronización de calendario | iCloud CalDAV poll | Cada 10 min |

---

## 9. Flujo de Mensaje Entrante

```
Usuario escribe por WhatsApp
        │
        ▼
Baileys (Node.js) recibe mensaje
        │
        ▼
HTTP POST → FastAPI Python (brain)
        │
        ▼
Orchestrator analiza:
  - ¿Es una pregunta? → Responder con IA
  - ¿Es un comando? → Ejecutar acción
  - ¿Es confirmación de algo? → Procesar
        │
        ▼
Consulta memoria corta (contexto) + memoria larga (ChromaDB)
        │
        ▼
AI Router intenta Claude → Gemini → OpenAI
        │
        ▼
Respuesta formateada (breve, amigable, WhatsApp-friendly)
        │
        ▼
HTTP POST → Baileys `POST /send`
        │
        ▼
Mensaje llega al usuario
```

---

## 10. Estructura del Repositorio

```
LeoX/
├── README.md
├── PLAN.md
├── docker-compose.yml
├── .env.example
│
├── whatsapp-service/          # Servicio Node.js (Baileys)
│   ├── package.json
│   ├── index.js
│   └── session/               # Sesión persistente WhatsApp
│
├── brain/                     # Python - Core IA
│   ├── main.py                # FastAPI app + endpoints
│   ├── orchestrator.py        # Lógica principal
│   ├── ai_router.py           # Fallback Claude→Gemini→OpenAI
│   └── system_prompt.py       # System prompt personalizable
│
├── integrations/              # Python - Conectores
│   ├── icloud_calendar.py
│   ├── icloud_reminders.py
│   └── gmail_monitor.py
│
├── memory/                    # Python - Memoria
│   ├── short_term.py
│   ├── long_term.py           # ChromaDB
│   └── embedder.py
│
├── scheduler/                 # Python - Tareas autónomas
│   ├── jobs.py                # Registro de todos los jobs
│   ├── morning_brief.py
│   ├── event_reminder.py
│   ├── conflict_detector.py
│   └── silence_checker.py
│
├── requirements.txt
└── .env.example
```

---

## 11. Variables de Entorno Necesarias

```bash
# IA - APIs
ANTHROPIC_API_KEY=
GOOGLE_AI_API_KEY=
OPENAI_API_KEY=

# WhatsApp (número del asistente)
WHATSAPP_SERVICE_URL=http://localhost:3000
MY_WHATSAPP_NUMBER=+1234567890   # Tu número personal

# iCloud
ICLOUD_USERNAME=tu@icloud.com
ICLOUD_PASSWORD=app_specific_password  # Contraseña específica de app

# Gmail
GMAIL_CREDENTIALS_PATH=./credentials.json
GMAIL_TOKEN_PATH=./token.json

# ChromaDB
CHROMA_PERSIST_DIR=./chroma_data

# Scheduler
MORNING_BRIEF_TIME=08:00          # Hora del resumen matutino
EVENT_REMINDER_MINUTES=15         # Minutos antes del evento
SILENCE_CHECK_HOURS=6             # Horas sin actividad para check-in
EMAIL_POLL_INTERVAL_MINUTES=15    # Frecuencia de chequeo de Gmail

# AI Timeouts
AI_TIMEOUT_SECONDS=15
```

---

## 12. Fases de Desarrollo

### Fase 1 — Infraestructura base (MVP)
- [ ] Docker-compose con Node.js (Baileys) + Python (FastAPI)
- [ ] Baileys conectado y enviando/recibiendo mensajes
- [ ] AI Router con fallback Claude → Gemini → OpenAI funcionando
- [ ] Enviar y recibir mensajes básicos desde el Pi

### Fase 2 — Integraciones
- [ ] iCloud CalDAV (calendario + reminders)
- [ ] Gmail OAuth2 monitoring
- [ ] Memoria corta (contexto de conversación)

### Fase 3 — Autonomía
- [ ] APScheduler con todos los jobs proactivos
- [ ] Resumen matutino funcionando
- [ ] Alertas de eventos
- [ ] Detección de conflictos

### Fase 4 — Memoria larga
- [ ] ChromaDB integrado
- [ ] Embeddings de conversaciones
- [ ] Recuperación de contexto relevante por consulta

### Fase 5 — Personalización
- [ ] System prompt configurable
- [ ] Ajustes de horarios y preferencias via WhatsApp
- [ ] Panel de logs (opcional)

---

## 13. Consideraciones de Seguridad

- **iCloud:** Usar "Contraseña específica de app" (no la contraseña principal)
- **Gmail:** OAuth2 con scope mínimo (readonly en correos)
- **Baileys:** Sesión encriptada localmente, no se comparte
- **APIs de IA:** Keys solo en `.env`, nunca en el código
- **Red:** El Pi no expone puertos al exterior; todo es local
- **WhatsApp:** Número dedicado, no mezclar con uso personal de Baileys

---

## 14. Preguntas Pendientes para Fases Futuras

- ¿Quieres que LeoX pueda crear/modificar eventos en el calendario, o solo leer?
- ¿Quieres que responda o gestione algunos WhatsApps entrantes en tu nombre?
- ¿Qué franja horaria de "silencio nocturno" no debe molestarte?
- ¿Quieres notificaciones de correos de dominios específicos solamente?
- ¿Deseas un comando de WhatsApp para pausar el asistente temporalmente?

---

*Documento generado en fase de planificación. Sujeto a cambios según evolución del proyecto.*
