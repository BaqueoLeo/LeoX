const {
  default: makeWASocket,
  useMultiFileAuthState,
  DisconnectReason,
  fetchLatestBaileysVersion,
} = require("@whiskeysockets/baileys");
const express = require("express");
const pino = require("pino");
const qrcode = require("qrcode-terminal");
const fs = require("fs");

const app = express();
app.use(express.json());

const BRAIN_URL = process.env.BRAIN_URL || "http://localhost:8000";
const PORT = process.env.PORT || 3000;
const MY_NUMBER = process.env.MY_WHATSAPP_NUMBER || "";

const logger = pino({ level: "warn" });

let sock = null;
let connectionState = "disconnected";
let connectedNumber = null;

// ─── WhatsApp Connection ────────────────────────────────────────

async function startWhatsApp() {
  const { state, saveCreds } = await useMultiFileAuthState("./session");
  const { version } = await fetchLatestBaileysVersion();

  sock = makeWASocket({
    version,
    auth: state,
    logger,
    printQRInTerminal: false,
    browser: ["LeoX", "Chrome", "1.0.0"],
  });

  sock.ev.on("creds.update", saveCreds);

  sock.ev.on("connection.update", async (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      connectionState = "waiting_qr";
      console.log("\n╔══════════════════════════════════════╗");
      console.log("║   Escanea el QR con WhatsApp         ║");
      console.log("╚══════════════════════════════════════╝\n");
      qrcode.generate(qr, { small: true });
    }

    if (connection === "close") {
      connectionState = "disconnected";
      const statusCode =
        lastDisconnect?.error?.output?.statusCode;
      const shouldReconnect = statusCode !== DisconnectReason.loggedOut;

      console.log(
        `[WhatsApp] Desconectado. Código: ${statusCode}. Reconectar: ${shouldReconnect}`
      );

      if (shouldReconnect) {
        setTimeout(startWhatsApp, 3000);
      } else {
        console.log("[WhatsApp] Sesión cerrada. Borra ./session y reinicia.");
      }
    }

    if (connection === "open") {
      connectionState = "connected";
      connectedNumber = sock.user?.id?.split(":")[0] || "desconocido";
      console.log(`[WhatsApp] Conectado como +${connectedNumber}`);
    }
  });

  // ─── Incoming Messages ──────────────────────────────────────

  sock.ev.on("messages.upsert", async ({ messages, type }) => {
    if (type !== "notify") return;

    for (const msg of messages) {
      if (msg.key.fromMe) continue;
      if (!msg.message) continue;

      const remoteJid = msg.key.remoteJid;
      const senderNumber = remoteJid.replace("@s.whatsapp.net", "");
      const text =
        msg.message.conversation ||
        msg.message.extendedTextMessage?.text ||
        "";

      if (!text) continue;

      console.log(`[MSG] ${senderNumber}: ${text}`);

      // Forward to brain
      try {
        const response = await fetch(`${BRAIN_URL}/message`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            from: senderNumber,
            text: text,
            jid: remoteJid,
            timestamp: msg.messageTimestamp,
            pushName: msg.pushName || "",
          }),
        });

        if (response.ok) {
          const data = await response.json();

          if (data.reply) {
            if (data.format === "voice" && data.audio) {
              // Send voice note
              const audioBuffer = Buffer.from(data.audio, "base64");
              await sock.sendMessage(remoteJid, {
                audio: audioBuffer,
                mimetype: "audio/ogg; codecs=opus",
                ptt: true,
              });
            } else {
              // Send text
              await sock.sendMessage(remoteJid, { text: data.reply });
            }
          }
        } else {
          console.error(`[Brain] Error ${response.status}`);
        }
      } catch (err) {
        console.error(`[Brain] No disponible: ${err.message}`);
      }
    }
  });
}

// ─── REST API (for brain to send messages proactively) ────────

app.post("/send", async (req, res) => {
  const { to, text, audio } = req.body;

  if (!sock || connectionState !== "connected") {
    return res.status(503).json({ error: "WhatsApp no conectado" });
  }

  if (!to) {
    return res.status(400).json({ error: "Falta 'to'" });
  }

  const jid = to.includes("@") ? to : `${to}@s.whatsapp.net`;

  try {
    if (audio) {
      // Send voice note
      const audioBuffer = Buffer.from(audio, "base64");
      await sock.sendMessage(jid, {
        audio: audioBuffer,
        mimetype: "audio/ogg; codecs=opus",
        ptt: true,
      });
    } else if (text) {
      await sock.sendMessage(jid, { text });
    } else {
      return res.status(400).json({ error: "Falta 'text' o 'audio'" });
    }
    res.json({ ok: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get("/status", (req, res) => {
  res.json({
    status: connectionState,
    number: connectedNumber,
    uptime: process.uptime(),
  });
});

// ─── Fetch chat history for commitment scanner ────────────────

app.get("/chats/:jid/messages", async (req, res) => {
  // This endpoint returns recent messages from a chat
  // Used by the commitment scanner to analyze conversations
  // Note: Baileys doesn't persist history by default,
  // the brain will maintain its own message buffer
  res.json({ messages: [] });
});

// ─── Start ────────────────────────────────────────────────────

app.listen(PORT, () => {
  console.log(`[API] WhatsApp service en puerto ${PORT}`);
  startWhatsApp();
});
