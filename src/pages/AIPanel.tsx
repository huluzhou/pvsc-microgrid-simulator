import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { Brain, TrendingUp } from "lucide-react";

export default function AIPanel() {
  const [predictionHorizon, setPredictionHorizon] = useState(3600);

  const handlePredict = async () => {
    try {
      const result = await invoke("predict_device_data", {
        request: {
          device_ids: [],
          prediction_horizon: predictionHorizon,
          prediction_type: "power",
        },
      });
      console.log("Prediction result:", result);
    } catch (error) {
      console.error("Prediction failed:", error);
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6 text-white">AI 智能</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Brain className="w-5 h-5" />
            数据预测
          </h2>
          <div className="space-y-4">
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
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded text-white transition-colors"
            >
              开始预测
            </button>
          </div>
        </div>
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5" />
            运行优化
          </h2>
          <p className="text-gray-400">优化功能将在后续实现</p>
        </div>
      </div>
    </div>
  );
}
