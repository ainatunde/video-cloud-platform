'use strict';

const { app, BrowserWindow, Menu, dialog, ipcMain } = require('electron');
const path = require('path');

// Enable hardware acceleration (default in Electron, but explicit for clarity)
app.commandLine.appendSwitch('enable-gpu-rasterization');
app.commandLine.appendSwitch('enable-zero-copy');

let mainWindow = null;
let currentStreamUrl = 'http://localhost:8080/live/stream1.m3u8';

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 800,
    minHeight: 500,
    backgroundColor: '#0f172a',
    title: 'Video Cloud Desktop',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
      // Allow loading local and remote media
      webSecurity: false,
      allowRunningInsecureContent: true,
    },
    show: false,
  });

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  buildMenu();
}

function buildMenu() {
  const template = [
    {
      label: 'File',
      submenu: [
        {
          label: 'Open Stream URL…',
          accelerator: 'CmdOrCtrl+O',
          click: () => openStreamDialog(),
        },
        {
          label: 'Open Local File…',
          accelerator: 'CmdOrCtrl+Shift+O',
          click: () => openLocalFile(),
        },
        { type: 'separator' },
        {
          label: 'Quit',
          accelerator: process.platform === 'darwin' ? 'Cmd+Q' : 'Alt+F4',
          click: () => app.quit(),
        },
      ],
    },
    {
      label: 'View',
      submenu: [
        {
          label: 'Toggle Full Screen',
          accelerator: 'F11',
          click: () => {
            if (mainWindow) {
              mainWindow.setFullScreen(!mainWindow.isFullScreen());
            }
          },
        },
        {
          label: 'Toggle Developer Tools',
          accelerator: 'CmdOrCtrl+Shift+I',
          click: () => {
            if (mainWindow) {
              mainWindow.webContents.toggleDevTools();
            }
          },
        },
        { type: 'separator' },
        { role: 'reload' },
        { role: 'forceReload' },
      ],
    },
    {
      label: 'Stream',
      submenu: [
        {
          label: 'Connect to Platform…',
          click: () => openStreamDialog(),
        },
        {
          label: 'Switch to 1080p',
          click: () => mainWindow?.webContents.send('set-quality', '1080p'),
        },
        {
          label: 'Switch to 720p',
          click: () => mainWindow?.webContents.send('set-quality', '720p'),
        },
        {
          label: 'Switch to Auto',
          click: () => mainWindow?.webContents.send('set-quality', 'auto'),
        },
      ],
    },
    {
      label: 'Help',
      submenu: [
        {
          label: 'About Video Cloud Desktop',
          click: () => {
            dialog.showMessageBox(mainWindow, {
              type: 'info',
              title: 'Video Cloud Desktop',
              message: 'Video Cloud Platform Desktop Player',
              detail: `Version: 1.0.0\nElectron: ${process.versions.electron}\nChromium: ${process.versions.chrome}`,
            });
          },
        },
      ],
    },
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

function openStreamDialog() {
  dialog.showInputBox
    ? dialog.showInputBox(mainWindow, {
        title: 'Open Stream URL',
        message: 'Enter HLS stream URL:',
        value: currentStreamUrl,
      }).then(({ response, value }) => {
        if (response === 0 && value) {
          currentStreamUrl = value;
          mainWindow?.webContents.send('load-stream', value);
        }
      }).catch(() => {})
    : (() => {
        // Fallback for Electron versions without showInputBox
        const win = new BrowserWindow({
          width: 500,
          height: 200,
          parent: mainWindow,
          modal: true,
          webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
          },
        });
        win.loadURL(`data:text/html,
          <html><body style="background:#1e293b;color:#e2e8f0;font-family:sans-serif;padding:20px">
          <label>Stream URL:</label><br>
          <input id="url" type="text" value="${currentStreamUrl}"
            style="width:100%;margin:8px 0;background:#0f172a;color:#e2e8f0;border:1px solid #475569;padding:6px;border-radius:4px">
          <button onclick="require('electron').ipcRenderer.send('stream-url', document.getElementById('url').value)"
            style="background:#2563eb;color:#fff;border:none;padding:8px 16px;border-radius:4px;cursor:pointer">
            Load
          </button>
          </body></html>`);
      })();
}

function openLocalFile() {
  dialog.showOpenDialog(mainWindow, {
    title: 'Open Video File',
    filters: [
      { name: 'Video Files', extensions: ['mp4', 'mkv', 'mov', 'avi', 'ts', 'm3u8'] },
      { name: 'All Files', extensions: ['*'] },
    ],
    properties: ['openFile'],
  }).then(result => {
    if (!result.canceled && result.filePaths.length > 0) {
      const filePath = result.filePaths[0];
      mainWindow?.webContents.send('load-stream', `file://${filePath}`);
    }
  }).catch(() => {});
}

ipcMain.on('stream-url', (event, url) => {
  currentStreamUrl = url;
  mainWindow?.webContents.send('load-stream', url);
  BrowserWindow.fromWebContents(event.sender)?.close();
});

app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
