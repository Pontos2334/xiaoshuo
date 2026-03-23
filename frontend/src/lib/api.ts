import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8002/api';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 文件相关API
export const fileApi = {
  getNovels: () => api.get('/files/novels'),
  getNovelContent: (id: string) => api.get(`/files/novels/${id}`),
  scanFolder: (path: string) => api.post('/files/scan', { path }),
};

// 人物相关API
export const characterApi = {
  getCharacters: (novelId: string) => api.get(`/characters?novelId=${novelId}`),
  getCharacter: (id: string) => api.get(`/characters/${id}`),
  analyzeCharacters: (novelId: string) => api.post('/characters/analyze', { novelId }),
  updateCharacter: (id: string, data: Record<string, unknown>) => api.put(`/characters/${id}`, data),
  deleteCharacter: (id: string) => api.delete(`/characters/${id}`),
  getRelations: (novelId: string) => api.get(`/characters/relations?novelId=${novelId}`),
  analyzeRelations: (novelId: string) => api.post('/relations/analyze', { novelId }),
  updateRelation: (id: string, data: Record<string, unknown>) => api.put(`/relations/${id}`, data),
};

// 情节相关API
export const plotApi = {
  getPlotNodes: (novelId: string) => api.get(`/plots?novelId=${novelId}`),
  getPlotNode: (id: string) => api.get(`/plots/${id}`),
  analyzePlots: (novelId: string) => api.post('/plots/analyze', { novelId }),
  updatePlotNode: (id: string, data: Record<string, unknown>) => api.put(`/plots/${id}`, data),
  deletePlotNode: (id: string) => api.delete(`/plots/${id}`),
  getConnections: (novelId: string) => api.get(`/plots/connections?novelId=${novelId}`),
  analyzeConnections: (novelId: string) => api.post('/connections/analyze', { novelId }),
  updateConnection: (id: string, data: Record<string, unknown>) => api.put(`/connections/${id}`, data),
};

// 灵感相关API
export const inspirationApi = {
  getPlotInspiration: (plotId: string) => api.post('/inspiration/plot', { plotId }),
  getContinueInspiration: (novelId: string) => api.post('/inspiration/continue', { novelId }),
  getCharacterInspiration: (characterId: string) => api.post('/inspiration/character', { characterId }),
  getEmotionInspiration: (plotId: string, emotion: string) => api.post('/inspiration/emotion', { plotId, emotion }),
};
