import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { Brain, TrendingUp, Lightbulb } from "lucide-react";

interface PredictionResult {
  device_id: string;
  predictions: Array<{ timestamp: number; value: number }>;
  confidence: number;
}

interface OptimizationResult {
  strategy: any;
  expected_benefit: number;
  confidence: number;
}

export default function AIPanel() {
  const [predictionHorizon, setPredictionHorizon] = useState(3600);
  const [predictionType, setPredictionType] = useState("power");
  const [predictionResult, setPredictionResult] = useState<PredictionResult[] | null>(null);
  const [optimizationObjective, setOptimizationObjective] = useState("minimize_cost");
  const [optimizationResult, setOptimizationResult] = useState<OptimizationResult | null>(null);
  const [recommendations, setRecommendations] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const handlePredict = async () => {
    setIsLoading(true);
    setPredictionResult(null);
    try {
      const result = await invoke<PredictionResult[]>("predict_device_data", {
        request: {
          device_ids: [],
          prediction_horizon: predictionHorizon,
          prediction_type: predictionType,
        },
      });
      setPredictionResult(result);
    } catch (error) {
      console.error("Prediction failed:", error);
      alert("预测失败：" + error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleOptimize = async () => {
    setIsLoading(true);
    setOptimizationResult(null);
    try {
      const result = await invoke<OptimizationResult>("optimize_operation", {
        request: {
          objective: optimizationObjective,
          constraints: ["voltage_limits", "power_balance"],
          time_horizon: 3600,
        },
      });
      setOptimizationResult(result);
    } catch (error) {
      console.error("Optimization failed:", error);
      alert("优化失败：" + error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGetRecommendations = async () => {
    setIsLoading(true);
    setRecommendations([]);
    try {
      const result = await invoke<string[]>("get_ai_recommendations", {
        device_ids: [],
      });
      setRecommendations(result);
    } catch (error) {
      console.error("Failed to get recommendations:", error);
      alert("获取推荐失败：" + error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6 text-white">AI 智能</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* 数据预测 */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Brain className="w-5 h-5" />
            数据预测
          </h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                预测类型
              </label>
              <select
                value={predictionType}
                onChange={(e) => setPredictionType(e.target.value)}
                className="bg-gray-700 border border-gray-600 rounded px-4 py-2 text-white w-full"
              >
                <option value="voltage">电压</option>
                <option value="current">电流</option>
                <option value="power">功率</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                预测时间范围（秒）
              </label>
              <input
                type="number"
                value={predictionHorizon}
                onChange={(e) => setPredictionHorizon(parseInt(e.target.value))}
                className="bg-gray-700 border border-gray-600 rounded px-4 py-2 text-white w-full"
              />
            </div>
            <button
              onClick={handlePredict}
              disabled={isLoading}
              className="w-full px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded text-white transition-colors disabled:opacity-50"
            >
              {isLoading ? "预测中..." : "开始预测"}
            </button>
            {predictionResult && (
              <div className="mt-4 p-4 bg-gray-700 rounded">
                <h3 className="text-sm font-medium text-white mb-2">预测结果</h3>
                <pre className="text-xs text-gray-300 overflow-auto">
                  {JSON.stringify(predictionResult, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>

        {/* 运行优化 */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5" />
            运行优化
          </h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                优化目标
              </label>
              <select
                value={optimizationObjective}
                onChange={(e) => setOptimizationObjective(e.target.value)}
                className="bg-gray-700 border border-gray-600 rounded px-4 py-2 text-white w-full"
              >
                <option value="minimize_cost">最小化成本</option>
                <option value="maximize_efficiency">最大化效率</option>
                <option value="minimize_loss">最小化损耗</option>
              </select>
            </div>
            <button
              onClick={handleOptimize}
              disabled={isLoading}
              className="w-full px-6 py-3 bg-green-600 hover:bg-green-700 rounded text-white transition-colors disabled:opacity-50"
            >
              {isLoading ? "优化中..." : "开始优化"}
            </button>
            {optimizationResult && (
              <div className="mt-4 p-4 bg-gray-700 rounded">
                <h3 className="text-sm font-medium text-white mb-2">优化结果</h3>
                <div className="text-sm text-gray-300">
                  <p>预期收益: {optimizationResult.expected_benefit.toFixed(2)}</p>
                  <p>置信度: {(optimizationResult.confidence * 100).toFixed(1)}%</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* AI 推荐 */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Lightbulb className="w-5 h-5" />
          AI 推荐
        </h2>
        <button
          onClick={handleGetRecommendations}
          disabled={isLoading}
          className="mb-4 px-6 py-3 bg-purple-600 hover:bg-purple-700 rounded text-white transition-colors disabled:opacity-50"
        >
          {isLoading ? "获取中..." : "获取推荐"}
        </button>
        {recommendations.length > 0 && (
          <div className="space-y-2">
            {recommendations.map((rec, index) => (
              <div
                key={index}
                className="p-4 bg-gray-700 rounded text-sm text-white"
              >
                {rec}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
