const cron = require("node-cron");
const { spawn } = require("child_process");

// ==== EDIT THIS ====

// Path to your virtual environment python.exe
const pythonPath = "C:\\Users\\Administrator\\Desktop\\attendace_data_collector\\attendance-data-collector\\venv\\Scripts\\python.exe";

// Working directory of your project (IMPORTANT for -m to work)
const workingDirectory = "C:\\Users\\Administrator\\Desktop\\attendace_data_collector\\attendance-data-collector";

// Module name you run with -m
const moduleName = "scripts.attendance_data_collector";
// ====================

// Function to run the module
function runPythonModule() {
    console.log("Running attendance collector:", new Date());

    const process = spawn(
        pythonPath,
        ["-m", moduleName],
        {
            cwd: workingDirectory,   // critical for module execution
            stdio: "inherit"
        }
    );

    process.on("error", (err) => {
        console.error("Failed to start process:", err);
    });

    process.on("close", (code) => {
        console.log(`Process exited with code ${code}`);
    });
}

// Run every 10 minutes
cron.schedule("*/10 * * * *", () => {
    runPythonModule();
});

console.log("PM2 Python scheduler started...");