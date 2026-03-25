import { create } from 'zustand';
import { shallow } from 'zustand/shallow';
import { Character, CharacterRelation, PlotNode, PlotConnection, Novel, Inspiration } from '@/types';

// 导出 shallow 用于组件中的性能优化
export { shallow };

// 小说Store
interface NovelState {
  novels: Novel[];
  currentNovel: Novel | null;
  setNovels: (novels: Novel[]) => void;
  setCurrentNovel: (novel: Novel | null) => void;
}

export const useNovelStore = create<NovelState>((set) => ({
  novels: [],
  currentNovel: null,
  setNovels: (novels) => set({ novels }),
  setCurrentNovel: (novel) => set({ currentNovel: novel }),
}));

// 人物Store
interface CharacterState {
  characters: Character[];
  relations: CharacterRelation[];
  selectedCharacter: Character | null;
  setCharacters: (characters: Character[]) => void;
  setRelations: (relations: CharacterRelation[]) => void;
  setSelectedCharacter: (character: Character | null) => void;
  addCharacter: (character: Character) => void;
  updateCharacter: (id: string, data: Partial<Character>) => void;
  deleteCharacter: (id: string) => void;
  addRelation: (relation: CharacterRelation) => void;
  updateRelation: (id: string, data: Partial<CharacterRelation>) => void;
  deleteRelation: (id: string) => void;
}

export const useCharacterStore = create<CharacterState>((set) => ({
  characters: [],
  relations: [],
  selectedCharacter: null,
  setCharacters: (characters) => set({ characters }),
  setRelations: (relations) => set({ relations }),
  setSelectedCharacter: (character) => set({ selectedCharacter: character }),
  addCharacter: (character) => set((state) => ({ characters: [...state.characters, character] })),
  updateCharacter: (id, data) => set((state) => ({
    characters: state.characters.map((c) => (c.id === id ? { ...c, ...data } : c)),
  })),
  deleteCharacter: (id) => set((state) => ({
    characters: state.characters.filter((c) => c.id !== id),
  })),
  addRelation: (relation) => set((state) => ({ relations: [...state.relations, relation] })),
  updateRelation: (id, data) => set((state) => ({
    relations: state.relations.map((r) => (r.id === id ? { ...r, ...data } : r)),
  })),
  deleteRelation: (id) => set((state) => ({
    relations: state.relations.filter((r) => r.id !== id),
  })),
}));

// 情节Store
interface PlotState {
  plotNodes: PlotNode[];
  plotConnections: PlotConnection[];
  selectedPlotNode: PlotNode | null;
  setPlotNodes: (nodes: PlotNode[]) => void;
  setPlotConnections: (connections: PlotConnection[]) => void;
  setSelectedPlotNode: (node: PlotNode | null) => void;
  addPlotNode: (node: PlotNode) => void;
  updatePlotNode: (id: string, data: Partial<PlotNode>) => void;
  deletePlotNode: (id: string) => void;
  addPlotConnection: (connection: PlotConnection) => void;
  updatePlotConnection: (id: string, data: Partial<PlotConnection>) => void;
  deletePlotConnection: (id: string) => void;
}

export const usePlotStore = create<PlotState>((set) => ({
  plotNodes: [],
  plotConnections: [],
  selectedPlotNode: null,
  setPlotNodes: (nodes) => set({ plotNodes: nodes }),
  setPlotConnections: (connections) => set({ plotConnections: connections }),
  setSelectedPlotNode: (node) => set({ selectedPlotNode: node }),
  addPlotNode: (node) => set((state) => ({ plotNodes: [...state.plotNodes, node] })),
  updatePlotNode: (id, data) => set((state) => ({
    plotNodes: state.plotNodes.map((n) => (n.id === id ? { ...n, ...data } : n)),
  })),
  deletePlotNode: (id) => set((state) => ({
    plotNodes: state.plotNodes.filter((n) => n.id !== id),
  })),
  addPlotConnection: (connection) => set((state) => ({ plotConnections: [...state.plotConnections, connection] })),
  updatePlotConnection: (id, data) => set((state) => ({
    plotConnections: state.plotConnections.map((c) => (c.id === id ? { ...c, ...data } : c)),
  })),
  deletePlotConnection: (id) => set((state) => ({
    plotConnections: state.plotConnections.filter((c) => c.id !== id),
  })),
}));

// 灵感Store
interface InspirationState {
  inspirations: Inspiration[];
  currentInspiration: string | null;
  isLoading: boolean;
  setInspirations: (inspirations: Inspiration[]) => void;
  setCurrentInspiration: (inspiration: string | null) => void;
  setIsLoading: (loading: boolean) => void;
  addInspiration: (inspiration: Inspiration) => void;
  updateInspiration: (id: string, data: Partial<Inspiration>) => void;
  deleteInspiration: (id: string) => void;
  clearInspirations: () => void;
}

export const useInspirationStore = create<InspirationState>((set) => ({
  inspirations: [],
  currentInspiration: null,
  isLoading: false,
  setInspirations: (inspirations) => set({ inspirations }),
  setCurrentInspiration: (inspiration) => set({ currentInspiration: inspiration }),
  setIsLoading: (loading) => set({ isLoading: loading }),
  addInspiration: (inspiration) => set((state) => ({ inspirations: [...state.inspirations, inspiration] })),
  updateInspiration: (id, data) => set((state) => ({
    inspirations: state.inspirations.map((i) => (i.id === id ? { ...i, ...data } : i)),
  })),
  deleteInspiration: (id) => set((state) => ({
    inspirations: state.inspirations.filter((i) => i.id !== id),
  })),
  clearInspirations: () => set({ inspirations: [] }),
}));

// UI状态Store
interface UIState {
  activeTab: 'characters' | 'plots' | 'inspiration';
  sidebarOpen: boolean;
  setActiveTab: (tab: 'characters' | 'plots' | 'inspiration') => void;
  setSidebarOpen: (open: boolean) => void;
}

export const useUIStore = create<UIState>((set) => ({
  activeTab: 'characters',
  sidebarOpen: true,
  setActiveTab: (tab) => set({ activeTab: tab }),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
}));
