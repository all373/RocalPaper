const {contextBridge, ipcRenderer} = require('electron');
contextBridge.exposeInMainWorld('desktop', {
  draft: d => ipcRenderer.invoke('draft', d),
  saved: d => ipcRenderer.invoke('saved', d),
  recovery: () => ipcRenderer.invoke('recovery'),
  logs: () => ipcRenderer.invoke('logs'),
  version: () => ipcRenderer.invoke('version')
});
