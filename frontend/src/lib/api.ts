import axios, { AxiosError, AxiosResponse } from 'axios';
import { toast } from 'sonner';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8002/api';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000, // 60秒超时（AI分析可能需要较长时间）
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器 - 统一错误处理
api.interceptors.response.use(
  (response: AxiosResponse) => {
    // 检查业务层面的错误
    if (response.data?.success === false) {
      const errorMsg = response.data.error || '操作失败';
      toast.error(errorMsg);
      return Promise.reject(new Error(errorMsg));
    }
    return response;
  },
  (error: AxiosError<{ error?: string; detail?: string }>) => {
    let message = '网络请求失败';

    if (error.response) {
      const status = error.response.status;
      const data = error.response.data;

      if (status === 404) {
        message = data?.detail || data?.error || '资源不存在';
      } else if (status === 400) {
        message = data?.detail || data?.error || '请求参数错误';
      } else if (status === 500) {
        message = '服务器内部错误，请稍后重试';
      } else {
        message = data?.detail || data?.error || `请求失败 (${status})`;
      }
    } else if (error.request) {
      message = '无法连接到服务器，请检查网络';
    } else if (error.code === 'ECONNABORTED') {
      message = '请求超时，请稍后重试';
    }

    toast.error(message);
    return Promise.reject(error);
  }
);

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
