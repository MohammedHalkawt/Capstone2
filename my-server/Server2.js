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

    const axios = require("axios");

py.stdout.on("data", async (data) => {
  const text = data.toString().replace("FINAL:", "").trim();
  console.log("USER:", text);

  try {
    // Call local AI model
    const response = await axios.post("http://localhost:11434/api/generate", {
      model: "mistral",
      prompt: `You are a university assistant robot. Answer briefly:\n${text}`,
      stream: false
    });

    const aiReply = response.data.response.trim();
    console.log("AI:", aiReply);

    // Send AI response to TTS
    require("fs").writeFileSync(
      "C:/Users/hama2/OneDrive/Documents/GitHub/Capstone2/TTS/input.txt",
      aiReply
    );

  } catch (err) {
    console.error("AI ERROR:", err.message);

    // fallback
    require("fs").writeFileSync(
      "C:/Users/hama2/OneDrive/Documents/GitHub/Capstone2/TTS/input.txt",
      "Sorry, I could not process that."
    );
  }
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
