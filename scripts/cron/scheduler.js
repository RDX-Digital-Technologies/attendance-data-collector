const cron = require("node-cron");
const { spawn } = require("child_process");

// ==== CONFIG ====

// Use pythonw.exe to avoid popup window
const pythonPath = "C:\\Users\\Administrator\\Desktop\\attendace_data_collector\\attendance-data-collector\\venv\\Scripts\\pythonw.exe";

// Working directory
const workingDirectory = "C:\\Users\\Administrator\\Desktop\\attendace_data_collector\\attendance-data-collector";

// Module name
const moduleName = "scripts.attendance_data_collector";

// Max time a single run is allowed (ms). Should be less than the cron interval.
const RUN_TIMEOUT_MS = 9 * 60 * 1000; // 9 minutes

// =================

// Prevent overlapping runs
let isRunning = false;

function runPythonModule() {
    if (isRunning) {
        console.log("⏳ Previous job still running, skipping this tick...");
        return;
    }

    isRunning = true;
    console.log("🚀 Running attendance collector:", new Date().toISOString());

    const child = spawn(
        pythonPath,
        ["-u", "-m", moduleName], // -u = unbuffered output (logs stream live)
        {
            cwd: workingDirectory,
            windowsHide: true,                // hide any window
            stdio: ["ignore", "pipe", "pipe"], // capture output for PM2 logs
            env: { ...process.env, PYTHONUNBUFFERED: "1" }
        }
    );

    // Safety timeout — kill if it hangs
    const killTimer = setTimeout(() => {
        console.error("⏰ Run exceeded timeout, killing process...");
        child.kill("SIGTERM");
        // Force kill if it doesn't exit in 10s
        setTimeout(() => {
            if (!child.killed) child.kill("SIGKILL");
        }, 10_000);
    }, RUN_TIMEOUT_MS);

    child.stdout.on("data", (data) => {
        process.stdout.write(`[PY] ${data}`);
    });

    child.stderr.on("data", (data) => {
        process.stderr.write(`[PY ERR] ${data}`);
    });

    child.on("error", (err) => {
        clearTimeout(killTimer);
        console.error("❌ Failed to start process:", err);
        isRunning = false;
    });

    child.on("close", (code, signal) => {
        clearTimeout(killTimer);
        if (signal) {
            console.log(`✅ Process terminated by signal ${signal}`);
        } else {
            console.log(`✅ Process exited with code ${code}`);
        }
        isRunning = false;
    });
}

// Run every 10 minutes (at :00, :10, :20, ...)
cron.schedule("*/10 * * * *", runPythonModule);

console.log("🟢 PM2 Python scheduler started. Next run at the next :00/:10/:20/:30/:40/:50 mark.");