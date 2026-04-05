const express = require("express");
const multer = require("multer");
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

const app = express();
const upload = multer();

app.use(express.static("public"));

// --- Spawn Whisper ---
const whisperPy = spawn("python", ["speech-server.py"]);
let pendingWhisper = null;
let whisperBuffer = "";

whisperPy.stdout.on("data", (data) => {
  whisperBuffer += data.toString();
  const lines = whisperBuffer.split("\n");
  whisperBuffer = lines.pop();
  for (const line of lines) {
    if (line.startsWith("FINAL:")) {
      const text = line.replace("FINAL:", "").trim();
      console.log("Transcribed:", text);
      if (pendingWhisper) { pendingWhisper(text); pendingWhisper = null; }
    } else if (line.trim()) {
      console.log("Whisper:", line.trim());
    }
  }
});
whisperPy.stderr.on("data", () => {});

// --- Spawn Gemini ---
const geminiPy = spawn("python", ["C:\\Users\\hama2\\OneDrive\\Documents\\GitHub\\Capstone2\\my-server\\AI_Model\\modelcode.py"]);
let pendingGemini = null;
let geminiBuffer = "";

geminiPy.stdout.on("data", (data) => {
  geminiBuffer += data.toString();
  const lines = geminiBuffer.split("\n");
  geminiBuffer = lines.pop();
  for (const line of lines) {
    if (line.startsWith("REPLY:")) {
      const text = line.replace("REPLY:", "").trim();
      console.log("Gemini:", text);
      if (pendingGemini) { pendingGemini(text); pendingGemini = null; }
    } else if (line.trim()) {
      console.log("Gemini:", line.trim());
    }
  }
});
geminiPy.stderr.on("data", () => {});

const ttsPy = spawn("python", ["C:\\Users\\hama2\\OneDrive\\Documents\\GitHub\\Capstone2\\TTS\\textToSpeech.py"]);
let pendingTTS = null;
let ttsBuffer = "";

ttsPy.stdout.on("data", (data) => {
  ttsBuffer += data.toString();
  const lines = ttsBuffer.split("\n");
  ttsBuffer = lines.pop();
  for (const line of lines) {
    if (line.trim() === "DONE") {
      if (pendingTTS) { pendingTTS(); pendingTTS = null; }
    } else if (line.trim()) {
      console.log("TTS:", line.trim());
    }
  }
});
ttsPy.stderr.on("data", () => {});

// --- Queue ---
let busy = false;
const queue = [];

function processNext() {
  if (busy || queue.length === 0) return;
  busy = true;
  const { audioBuffer, res } = queue.shift();

  // Step 1: ffmpeg
  const ffmpeg = spawn("C:\\ffmpeg\\bin\\ffmpeg.exe", [
    "-i", "pipe:0", "-ar", "16000", "-ac", "1", "-f", "s16le", "pipe:1"
  ]);
  let pcmChunks = [];
  ffmpeg.stdout.on("data", chunk => pcmChunks.push(chunk));
  ffmpeg.stderr.on("data", () => {});

  ffmpeg.stdout.on("end", () => {
    const pcm = Buffer.concat(pcmChunks);
    const lenBuf = Buffer.alloc(4);
    lenBuf.writeUInt32LE(pcm.length, 0);

    // Step 2: Whisper
    pendingWhisper = (transcribed) => {
      if (!transcribed) {
        res.status(400).send("No speech detected");
        busy = false; processNext(); return;
      }

      // Step 3: Gemini
      geminiPy.stdin.write(transcribed + "\n");

      const geminiTimeout = setTimeout(() => {
        if (pendingGemini) {
          pendingGemini = null;
          res.status(500).send("Gemini timeout");
          busy = false; processNext();
        }
      }, 15000);

      pendingGemini = (reply) => {
        clearTimeout(geminiTimeout);

        // Step 4: TTS
        ttsPy.stdin.write(reply + "\n");

        const ttsTimeout = setTimeout(() => {
          if (pendingTTS) {
            pendingTTS = null;
            res.status(500).send("TTS timeout");
            busy = false; processNext();
          }
        }, 15000);

        pendingTTS = () => {
          clearTimeout(ttsTimeout);

          // Step 5: Send wav to browser
          const ttsOut = path.resolve("tts_out.wav");
          res.setHeader("Content-Type", "audio/wav");
          res.sendFile(ttsOut, (err) => {
            if (err) console.error("Send error:", err);
            busy = false; processNext();
          });
        };
      };
    };

    whisperPy.stdin.write(lenBuf);
    whisperPy.stdin.write(pcm);
  });

  ffmpeg.stdin.write(audioBuffer);
  ffmpeg.stdin.end();
}

app.post("/audio", upload.single("audio"), (req, res) => {
  queue.push({ audioBuffer: req.file.buffer, res });
  processNext();
});

app.listen(3000, () => console.log("Running on http://localhost:3000"));