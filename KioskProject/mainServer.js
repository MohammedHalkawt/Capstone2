const express = require("express");
const multer = require("multer");
const { spawn } = require("child_process");
const path = require("path");

const app = express();
const upload = multer();

app.use(express.static("public"));


const whisperPy = spawn("python", ["C:\\Users\\hama2\\OneDrive\\Documents\\GitHub\\Capstone2\\SpeechToText\\speechToText.py"]);
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
      console.log("SpeechToText:", line.trim());
    }
  }
});
whisperPy.stderr.on("data", (data) => {
  console.error("SpeechToText ERROR:", data.toString());
});

const geminiPy = spawn("python", ["C:\\Users\\hama2\\OneDrive\\Documents\\GitHub\\Capstone2\\KioskProject\\AI_Model\\assistant.py"]);
let pendingGemini = null;
let geminiBuffer = "";

geminiPy.stdout.on("data", (data) => {
  geminiBuffer += data.toString();
  const lines = geminiBuffer.split("\n");
  geminiBuffer = lines.pop();
  for (const line of lines) {
    if (line.startsWith("REPLY:")) {
      const text = line.replace("REPLY:", "").trim();
      console.log("Assistant:", text);
      if (pendingGemini) { pendingGemini(text); pendingGemini = null; }
    } else if (line.trim()) {
      console.log("Assistant:", line.trim());
    }
  }
});
geminiPy.stderr.on("data", (data) => {
  console.error("Assistant ERROR:", data.toString());
});

const ttsPy = spawn("python", ["C:\\Users\\hama2\\OneDrive\\Documents\\GitHub\\Capstone2\\TextToSpeech\\textToSpeech.py"]);
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
      console.log("TextToSpeech:", line.trim());
    }
  }
});
ttsPy.stderr.on("data", (data) => {
  console.error("TextToSpeech ERROR:", data.toString());
});

let busy = false;
const queue = [];

function processNext() {
  if (busy || queue.length === 0) return;
  busy = true;
  const { audioBuffer, res } = queue.shift();

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

    pendingWhisper = (transcribed) => {
      if (!transcribed) {
        res.status(400).send("No speech detected");
        busy = false; processNext(); return;
      }

      geminiPy.stdin.write(transcribed + "\n");

      const geminiTimeout = setTimeout(() => {
        if (pendingGemini) {
          pendingGemini = null;
          res.status(500).send("Assistant timeout");
          busy = false; processNext();
        }
      }, 15000);

      pendingGemini = (reply) => {
        clearTimeout(geminiTimeout);

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