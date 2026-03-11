const { app, BrowserWindow, ipcMain } = require("electron");
const { autoUpdater } = require("electron-updater");
const path = require("path");

let win;

app.whenReady().then(() => {
  win = new BrowserWindow({
    fullscreen: true,
    frame: false,
    icon: path.join(__dirname, "target.ico"),
    webPreferences: {
      contextIsolation: true,
      preload: path.join(__dirname, "preload.js"),
    },
  });

  win.loadFile(path.join(__dirname, "index.html"));

  win.webContents.on("before-input-event", (event, input) => {
    if (input.key === "F11") {
      win.setFullScreen(!win.isFullScreen());
    }
    if (input.key === "Escape") {
      if (win.isFullScreen()) {
        win.setFullScreen(false);
      }
    }
  });

  // Auto-updater events
  autoUpdater.on("checking-for-update", () => {
    win.webContents.send("update-status", { state: "checking" });
  });

  autoUpdater.on("update-available", (info) => {
    win.webContents.send("update-status", { state: "available", version: info.version });
  });

  autoUpdater.on("update-not-available", () => {
    win.webContents.send("update-status", { state: "up-to-date" });
  });

  autoUpdater.on("download-progress", (progress) => {
    win.webContents.send("update-status", { state: "downloading", percent: Math.round(progress.percent) });
  });

  autoUpdater.on("update-downloaded", () => {
    win.webContents.send("update-status", { state: "downloaded" });
    setTimeout(() => autoUpdater.quitAndInstall(), 3000);
  });

  autoUpdater.on("error", (err) => {
    win.webContents.send("update-status", { state: "error", message: err.message });
  });

  // Auto-check for updates on launch
  autoUpdater.checkForUpdatesAndNotify();
});

ipcMain.handle("check-for-updates", () => {
  autoUpdater.checkForUpdatesAndNotify();
});

ipcMain.handle("get-app-version", () => {
  return app.getVersion();
});

app.on("window-all-closed", () => app.quit());
