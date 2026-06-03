const express = require("express");
const multer = require("multer");
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

const app = express();
const upload = multer();
app.use(express.static("public"));

// ========== Persistent Python Subprocesses ==========
const whisperPy = spawn("python", [
  "C:\\Users\\hama2\\OneDrive\\Documents\\GitHub\\Capstone2\\SpeechToText\\speechToText.py"
]);
const geminiPy = spawn("python", [
  "C:\\Users\\hama2\\OneDrive\\Documents\\GitHub\\Capstone2\\KioskProject\\AI_Model\\assistant.py"
]);
const ttsPy = spawn("python", [
  "C:\\Users\\hama2\\OneDrive\\Documents\\GitHub\\Capstone2\\TextToSpeech\\textToSpeech.py"
]);

// ========== Request Tracking ==========
let nextRequestId = 1;
const pendingRequests = new Map(); // requestId -> { resolve, reject, timer, type }

// Helper to register a pending request
function registerRequest(type, timeoutMs = 30000) {
  const id = nextRequestId++;
  let timer = setTimeout(() => {
    const pending = pendingRequests.get(id);
    if (pending) {
      pending.reject(new Error(`${type} timeout`));
      pendingRequests.delete(id);
    }
  }, timeoutMs);
  const promise = new Promise((resolve, reject) => {
    pendingRequests.set(id, { resolve, reject, timer, type });
  });
  return { id, promise };
}

// Helper to resolve a pending request by ID
function resolveRequest(id, data) {
  const pending = pendingRequests.get(id);
  if (pending) {
    clearTimeout(pending.timer);
    pending.resolve(data);
    pendingRequests.delete(id);
  }
}

function rejectRequest(id, error) {
  const pending = pendingRequests.get(id);
  if (pending) {
    clearTimeout(pending.timer);
    pending.reject(error);
    pendingRequests.delete(id);
  }
}

// ========== Whisper Output Parsing ==========
let whisperBuffer = "";
whisperPy.stdout.on("data", (data) => {
  whisperBuffer += data.toString();
  const lines = whisperBuffer.split("\n");
  whisperBuffer = lines.pop();
  for (const line of lines) {
    if (line.startsWith("FINAL:")) {
      const text = line.replace("FINAL:", "").trim();
      // Extract request ID if embedded (we'll embed it in the PCM stream)
      // Since we can't easily pass ID through stdin, we'll use a different approach:
      // We'll send the ID as the first 4 bytes of the PCM data (overloading length?)
      // Simpler: Because we serialize requests (queue), the next FINAL belongs to the current pendingWhisper.
      // But we need to know which request. We'll store a currentWhisperId.
      if (currentWhisperId !== null) {
        resolveRequest(currentWhisperId, text);
        currentWhisperId = null;
      }
    } else if (line.trim()) {
      console.log("SpeechToText:", line.trim());
    }
  }
});
whisperPy.stderr.on("data", (data) => {
  console.error("SpeechToText ERROR:", data.toString());
});

// ========== Gemini Output Parsing ==========
let geminiBuffer = "";
geminiPy.stdout.on("data", (data) => {
  geminiBuffer += data.toString();
  const lines = geminiBuffer.split("\n");
  geminiBuffer = lines.pop();
  for (const line of lines) {
    if (line.startsWith("REPLY:")) {
      const text = line.replace("REPLY:", "").trim();
      if (currentGeminiId !== null) {
        resolveRequest(currentGeminiId, text);
        currentGeminiId = null;
      }
    } else if (line.trim()) {
      console.log("Assistant:", line.trim());
    }
  }
});
geminiPy.stderr.on("data", (data) => {
  console.error("Assistant ERROR:", data.toString());
});

// ========== TTS Output Parsing ==========
let ttsBuffer = "";
ttsPy.stdout.on("data", (data) => {
  ttsBuffer += data.toString();
  const lines = ttsBuffer.split("\n");
  ttsBuffer = lines.pop();
  for (const line of lines) {
    if (line.trim() === "DONE") {
      if (currentTtsId !== null) {
        // TTS done, now read the file
        const ttsOut = path.resolve("tts_out.wav");
        fs.readFile(ttsOut, (err, audioBuffer) => {
          if (err) {
            rejectRequest(currentTtsId, err);
          } else {
            resolveRequest(currentTtsId, audioBuffer);
          }
          currentTtsId = null;
        });
      }
    } else if (line.trim()) {
      console.log("TextToSpeech:", line.trim());
    }
  }
});
ttsPy.stderr.on("data", (data) => {
  console.error("TextToSpeech ERROR:", data.toString());
});

// ========== Active Request IDs ==========
let currentWhisperId = null;
let currentGeminiId = null;
let currentTtsId = null;

// ========== Queue (serialize because TTS uses fixed file) ==========
let busy = false;
const queue = [];

async function processNext() {
  if (busy || queue.length === 0) return;
  busy = true;
  const { audioBuffer, res } = queue.shift();

  try {
    // 1. Convert to PCM (ffmpeg – still per request, quick)
    const pcm = await convertToPcm(audioBuffer);

    // 2. Whisper STT
    const { id: whisperId, promise: whisperPromise } = registerRequest("Whisper", 15000);
    currentWhisperId = whisperId;
    // Send PCM data to whisperPy
    const lenBuf = Buffer.alloc(4);
    lenBuf.writeUInt32LE(pcm.length, 0);
    whisperPy.stdin.write(lenBuf);
    whisperPy.stdin.write(pcm);
    const transcribed = await whisperPromise;
    if (!transcribed) {
      res.status(400).send("No speech detected");
      busy = false; processNext();
      return;
    }

    // 3. Gemini reply
    const { id: geminiId, promise: geminiPromise } = registerRequest("Gemini", 30000);
    currentGeminiId = geminiId;
    geminiPy.stdin.write(transcribed + "\n");
    const reply = await geminiPromise;
    if (!reply) {
      res.status(500).send("Empty assistant reply");
      busy = false; processNext();
      return;
    }

    // 4. TTS audio
    const { id: ttsId, promise: ttsPromise } = registerRequest("TTS", 30000);
    currentTtsId = ttsId;
    ttsPy.stdin.write(reply + "\n");
    const audio = await ttsPromise;

    // 5. Send JSON response
    res.json({
      text: reply,
      audio: audio.toString("base64"),
      mime: "audio/wav"
    });
  } catch (err) {
    console.error(err);
    res.status(500).send(err.message || "Processing failed");
  } finally {
    busy = false;
    processNext();
  }
}

function convertToPcm(audioBuffer) {
  return new Promise((resolve, reject) => {
    const ffmpeg = spawn("C:\\ffmpeg\\bin\\ffmpeg.exe", [
      "-i", "pipe:0", "-ar", "16000", "-ac", "1", "-f", "s16le", "pipe:1"
    ]);
    let pcmChunks = [];
    ffmpeg.stdout.on("data", chunk => pcmChunks.push(chunk));
    ffmpeg.stderr.on("data", () => {});
    ffmpeg.on("close", (code) => {
      if (code !== 0) return reject(new Error("ffmpeg conversion failed"));
      resolve(Buffer.concat(pcmChunks));
    });
    ffmpeg.on("error", reject);
    ffmpeg.stdin.write(audioBuffer);
    ffmpeg.stdin.end();
  });
}

app.post("/audio", upload.single("audio"), (req, res) => {
  if (!req.file) return res.status(400).send("No audio file");
  queue.push({ audioBuffer: req.file.buffer, res });
  processNext();
});

app.listen(3000, () => console.log("Server running on http://localhost:3000"));