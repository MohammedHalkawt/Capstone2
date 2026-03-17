const express = require("express");
const multer = require("multer");
const { spawn } = require("child_process");

const app = express();
const upload = multer();

app.use(express.static("public"));

const py = spawn("python", ["speech-server.py"]);

py.stdout.on("data", (data) => {
  console.log("PYTHON:", data.toString());
});
py.stderr.on("data", (data) => {
  console.error("PYTHON ERR:", data.toString());
});

app.post("/audio", upload.single("audio"), (req, res) => {
  const audioBuffer = req.file.buffer;

  // Convert WebM -> raw 16kHz mono PCM using ffmpeg
  const ffmpeg = spawn("ffmpeg", [
    "-i", "pipe:0",          // input from stdin
    "-ar", "16000",          // 16kHz sample rate
    "-ac", "1",              // mono
    "-f", "s16le",           // raw PCM signed 16-bit little-endian
    "pipe:1"                 // output to stdout
  ]);

  let pcmChunks = [];

  ffmpeg.stdout.on("data", chunk => pcmChunks.push(chunk));

  ffmpeg.stdout.on("end", () => {
    const pcm = Buffer.concat(pcmChunks);
    py.stdin.write(pcm);
    py.stdin.write(Buffer.alloc(8000)); // flush with silence
  });

  ffmpeg.stderr.on("data", () => {}); // suppress ffmpeg logs

  ffmpeg.stdin.write(audioBuffer);
  ffmpeg.stdin.end();

  res.send("OK");
});

app.listen(3000, () => console.log("Running on http://localhost:3000"));