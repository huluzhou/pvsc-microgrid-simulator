/**
 * 历史记录管理器 - 用于实现撤销/恢复功能
 */
export interface HistoryState {
  nodes: any[];
  edges: any[];
  counter: number;
}

export class HistoryManager {
  private past: HistoryState[] = [];
  private future: HistoryState[] = [];
  private maxHistorySize: number = 50;

  /**
   * 保存当前状态到历史记录
   */
  snapshot(state: HistoryState): void {
    // 深拷贝状态
    const stateCopy = JSON.parse(JSON.stringify(state));
    
    // 添加到历史记录
    this.past.push(stateCopy);
    
    // 限制历史记录大小
    if (this.past.length > this.maxHistorySize) {
      this.past.shift();
    }
    
    // 清除未来记录（新操作后无法恢复）
    this.future = [];
  }

  /**
   * 撤销操作
   */
  undo(): HistoryState | null {
    if (this.past.length <= 1) {
      // 至少保留一个状态（当前状态）
      return this.past[0] || null;
    }
    
    const current = this.past.pop()!;
    this.future.push(current);
    
    return this.past[this.past.length - 1] || null;
  }

  /**
   * 恢复操作
   */
  redo(): HistoryState | null {
    if (this.future.length === 0) {
      return this.past[this.past.length - 1] || null;
    }
    
    const state = this.future.pop()!;
    this.past.push(state);
    
    return state;
  }

  /**
   * 检查是否可以撤销
   */
  canUndo(): boolean {
    return this.past.length > 1;
  }

  /**
   * 检查是否可以恢复
   */
  canRedo(): boolean {
    return this.future.length > 0;
  }

  /**
   * 清除所有历史记录
   */
  clear(): void {
    this.past = [];
    this.future = [];
  }

  /**
   * 初始化历史记录（设置初始状态）
   */
  initialize(initialState: HistoryState): void {
    this.past = [JSON.parse(JSON.stringify(initialState))];
    this.future = [];
  }
}
