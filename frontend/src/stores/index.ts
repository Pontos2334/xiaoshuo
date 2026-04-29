import { create } from 'zustand';
import { shallow } from 'zustand/shallow';
import { Character, CharacterRelation, PlotNode, PlotConnection, Novel, Inspiration, Chapter, WorldEntity, EntityRelation, Foreshadow, CharacterArcPoint, TensionPoint, OutlineNode } from '@/types';

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
export type TabId = 'characters' | 'plots' | 'inspiration' | 'search' | 'knowledge' | 'chat' | 'assistant' | 'worldbuilding' | 'foreshadow' | 'arcs' | 'tension' | 'outline';

interface UIState {
  activeTab: TabId;
  sidebarOpen: boolean;
  quickSearchOpen: boolean;
  setActiveTab: (tab: TabId) => void;
  setSidebarOpen: (open: boolean) => void;
  setQuickSearchOpen: (open: boolean) => void;
  toggleQuickSearch: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  activeTab: 'characters',
  sidebarOpen: true,
  quickSearchOpen: false,
  setActiveTab: (tab) => set({ activeTab: tab }),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  setQuickSearchOpen: (open) => set({ quickSearchOpen: open }),
  toggleQuickSearch: () => set((state) => ({ quickSearchOpen: !state.quickSearchOpen })),
}));

// 章节 Store
interface ChapterState {
  chapters: Chapter[];
  selectedChapterId: string | null;
  setChapters: (chapters: Chapter[]) => void;
  setSelectedChapterId: (id: string | null) => void;
}

export const useChapterStore = create<ChapterState>((set) => ({
  chapters: [],
  selectedChapterId: null,
  setChapters: (chapters) => set({ chapters }),
  setSelectedChapterId: (id) => set({ selectedChapterId: id }),
}));

// 世界观 Store
interface WorldBuildingState {
  entities: WorldEntity[];
  entityRelations: EntityRelation[];
  selectedEntityId: string | null;
  setEntities: (entities: WorldEntity[]) => void;
  setEntityRelations: (relations: EntityRelation[]) => void;
  setSelectedEntityId: (id: string | null) => void;
  addEntity: (entity: WorldEntity) => void;
  updateEntity: (id: string, data: Partial<WorldEntity>) => void;
  deleteEntity: (id: string) => void;
}

export const useWorldBuildingStore = create<WorldBuildingState>((set) => ({
  entities: [],
  entityRelations: [],
  selectedEntityId: null,
  setEntities: (entities) => set({ entities }),
  setEntityRelations: (relations) => set({ entityRelations: relations }),
  setSelectedEntityId: (id) => set({ selectedEntityId: id }),
  addEntity: (entity) => set((state) => ({ entities: [...state.entities, entity] })),
  updateEntity: (id, data) => set((state) => ({
    entities: state.entities.map((e) => (e.id === id ? { ...e, ...data } : e)),
  })),
  deleteEntity: (id) => set((state) => ({
    entities: state.entities.filter((e) => e.id !== id),
  })),
}));

// 伏笔追踪 Store
interface ForeshadowState {
  foreshadows: Foreshadow[];
  selectedForeshadowId: string | null;
  setForeshadows: (foreshadows: Foreshadow[]) => void;
  setSelectedForeshadowId: (id: string | null) => void;
  addForeshadow: (f: Foreshadow) => void;
  updateForeshadow: (id: string, data: Partial<Foreshadow>) => void;
  deleteForeshadow: (id: string) => void;
}

export const useForeshadowStore = create<ForeshadowState>((set) => ({
  foreshadows: [],
  selectedForeshadowId: null,
  setForeshadows: (foreshadows) => set({ foreshadows }),
  setSelectedForeshadowId: (id) => set({ selectedForeshadowId: id }),
  addForeshadow: (f) => set((state) => ({ foreshadows: [...state.foreshadows, f] })),
  updateForeshadow: (id, data) => set((state) => ({
    foreshadows: state.foreshadows.map((f) => (f.id === id ? { ...f, ...data } : f)),
  })),
  deleteForeshadow: (id) => set((state) => ({
    foreshadows: state.foreshadows.filter((f) => f.id !== id),
  })),
}));

// 角色弧线 Store
interface CharacterArcState {
  arcPoints: CharacterArcPoint[];
  selectedCharacterId: string | null;
  setArcPoints: (points: CharacterArcPoint[]) => void;
  setSelectedCharacterId: (id: string | null) => void;
  addArcPoint: (point: CharacterArcPoint) => void;
  updateArcPoint: (id: string, data: Partial<CharacterArcPoint>) => void;
  deleteArcPoint: (id: string) => void;
}

export const useCharacterArcStore = create<CharacterArcState>((set) => ({
  arcPoints: [],
  selectedCharacterId: null,
  setArcPoints: (points) => set({ arcPoints: points }),
  setSelectedCharacterId: (id) => set({ selectedCharacterId: id }),
  addArcPoint: (point) => set((state) => ({ arcPoints: [...state.arcPoints, point] })),
  updateArcPoint: (id, data) => set((state) => ({
    arcPoints: state.arcPoints.map((p) => (p.id === id ? { ...p, ...data } : p)),
  })),
  deleteArcPoint: (id) => set((state) => ({
    arcPoints: state.arcPoints.filter((p) => p.id !== id),
  })),
}));

// 节奏张力 Store
interface TensionState {
  tensionPoints: TensionPoint[];
  setTensionPoints: (points: TensionPoint[]) => void;
  addTensionPoint: (point: TensionPoint) => void;
  updateTensionPoint: (id: string, data: Partial<TensionPoint>) => void;
  deleteTensionPoint: (id: string) => void;
}

export const useTensionStore = create<TensionState>((set) => ({
  tensionPoints: [],
  setTensionPoints: (points) => set({ tensionPoints: points }),
  addTensionPoint: (point) => set((state) => ({ tensionPoints: [...state.tensionPoints, point] })),
  updateTensionPoint: (id, data) => set((state) => ({
    tensionPoints: state.tensionPoints.map((p) => (p.id === id ? { ...p, ...data } : p)),
  })),
  deleteTensionPoint: (id) => set((state) => ({
    tensionPoints: state.tensionPoints.filter((p) => p.id !== id),
  })),
}));

// 大纲 Store
interface OutlineState {
  outlineNodes: OutlineNode[];
  selectedNodeId: string | null;
  setOutlineNodes: (nodes: OutlineNode[]) => void;
  setSelectedNodeId: (id: string | null) => void;
  addOutlineNode: (node: OutlineNode) => void;
  updateOutlineNode: (id: string, data: Partial<OutlineNode>) => void;
  deleteOutlineNode: (id: string) => void;
}

export const useOutlineStore = create<OutlineState>((set) => ({
  outlineNodes: [],
  selectedNodeId: null,
  setOutlineNodes: (nodes) => set({ outlineNodes: nodes }),
  setSelectedNodeId: (id) => set({ selectedNodeId: id }),
  addOutlineNode: (node) => set((state) => ({ outlineNodes: [...state.outlineNodes, node] })),
  updateOutlineNode: (id, data) => set((state) => ({
    outlineNodes: state.outlineNodes.map((n) => (n.id === id ? { ...n, ...data } : n)),
  })),
  deleteOutlineNode: (id) => set((state) => ({
    outlineNodes: state.outlineNodes.filter((n) => n.id !== id),
  })),
}));
