const express = require("express");
const multer = require("multer");
const { spawn } = require("child_process");

const app = express();
const upload = multer();

app.use(express.static("public"));

app.post("/audio", upload.single("audio"), (req, res) => {
  const audioBuffer = req.file.buffer;

  // Convert WebM -> raw PCM
  const ffmpeg = spawn("C:\\ffmpeg\\bin\\ffmpeg.exe", [
    "-i", "pipe:0",
    "-ar", "16000",
    "-ac", "1",
    "-f", "s16le",
    "pipe:1"
  ]);

  let pcmChunks = [];

  ffmpeg.stdout.on("data", chunk => pcmChunks.push(chunk));

  ffmpeg.stdout.on("end", () => {
    const pcm = Buffer.concat(pcmChunks);

    // Spawn a fresh Python process for each recording
    const py = spawn("python", ["speech-server.py"]);

    let result = "";

    py.stdout.on("data", (data) => {
      result += data.toString();
      console.log("PYTHON:", data.toString());
    });

    py.stderr.on("data", () => {}); // suppress vosk logs

    py.stdout.on("end", () => {
      res.send(result.trim() || "No speech detected");
    });

    py.stdin.write(pcm);
    py.stdin.end();
  });

  ffmpeg.stderr.on("data", () => {});
  ffmpeg.stdin.write(audioBuffer);
  ffmpeg.stdin.end();
});

app.listen(3000, () => console.log("Running on http://localhost:3000"));