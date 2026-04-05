const express = require("express");
const multer = require("multer");
const { spawn } = require("child_process");
const fs = require("fs");

const app = express();
const upload = multer();

app.use(express.static("public"));

// ----------------------------
// Spawn Python ONCE at startup
// ----------------------------

const py = spawn("python", ["speech-server.py"]);

let pendingResolve = null;
let outputBuffer = "";

py.stdout.on("data", (data) => {
  outputBuffer += data.toString();
  const lines = outputBuffer.split("\n");
  outputBuffer = lines.pop(); // keep incomplete line

  for (const line of lines) {
    if (line.startsWith("FINAL:")) {
      const text = line.replace("FINAL:", "").trim();
      console.log("PYTHON:", text);
      fs.writeFileSync(
        "C:/Users/hama2/OneDrive/Documents/GitHub/Capstone2/TTS/input.txt",
        text
      );
      if (pendingResolve) {
        pendingResolve(text);
        pendingResolve = null;
      }
    } else if (line.trim()) {
      console.log("PYTHON:", line.trim()); // model ready, etc — only logged once
    }
  }
});

py.stderr.on("data", () => {}); // suppress whisper/cuda logs

py.on("exit", (code) => {
  console.error("Python process exited with code", code);
});

// ----------------------------
// Per-request: ffmpeg -> py stdin
// ----------------------------

// We need a queue so concurrent requests don't overlap
let busy = false;
const queue = [];

function processNext() {
  if (busy || queue.length === 0) return;
  busy = true;

  const { audioBuffer, res } = queue.shift();

  const ffmpeg = spawn("C:\\ffmpeg\\bin\\ffmpeg.exe", [
    "-i", "pipe:0",
    "-ar", "16000",
    "-ac", "1",
    "-f", "s16le",
    "pipe:1"
  ]);

  let pcmChunks = [];
  ffmpeg.stdout.on("data", chunk => pcmChunks.push(chunk));
  ffmpeg.stderr.on("data", () => {});

  ffmpeg.stdout.on("end", () => {
    const pcm = Buffer.concat(pcmChunks);

    // Write a 4-byte little-endian length header so Python knows when the chunk ends
    const lenBuf = Buffer.alloc(4);
    lenBuf.writeUInt32LE(pcm.length, 0);

    pendingResolve = (text) => {
      res.send(text || "No speech detected");
      busy = false;
      processNext();
    };

    // Timeout safety — if Python never replies
    const timeout = setTimeout(() => {
      if (pendingResolve) {
        pendingResolve = null;
        res.send("No speech detected");
        busy = false;
        processNext();
      }
    }, 30000);

    // Wrap the real resolve to also clear the timeout
    const originalResolve = pendingResolve;
    pendingResolve = (text) => {
      clearTimeout(timeout);
      originalResolve(text);
    };

    py.stdin.write(lenBuf);
    py.stdin.write(pcm);
  });

  ffmpeg.stdin.write(audioBuffer);
  ffmpeg.stdin.end();
}

app.post("/audio", upload.single("audio"), (req, res) => {
  queue.push({ audioBuffer: req.file.buffer, res });
  processNext();
});

app.listen(3000, () => console.log("Running on http://localhost:3000"));