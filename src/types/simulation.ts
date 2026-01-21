// 仿真类型定义
// 将在后续阶段完善

export interface SimulationState {
  isRunning: boolean;
  startTime?: Date;
  elapsedTime: number;
  calculationCount: number;
  averageDelay: number;
}
