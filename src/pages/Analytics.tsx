import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { BarChart3, Download } from "lucide-react";

export default function Analytics() {
  const [analysisType, setAnalysisType] = useState("performance");
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const handleAnalyze = async () => {
    setIsAnalyzing(true);
    try {
      const result = await invoke("analyze_performance", {
        request: {
          device_ids: [],
          start_time: Date.now() / 1000 - 3600,
          end_time: Date.now() / 1000,
          analysis_type: analysisType,
        },
      });
      console.log("Analysis result:", result);
    } catch (error) {
      console.error("Analysis failed:", error);
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6 text-white">数据分析</h1>
      <div className="bg-gray-800 rounded-lg p-6">
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            分析类型
          </label>
          <select
            value={analysisType}
            onChange={(e) => setAnalysisType(e.target.value)}
            className="bg-gray-700 border border-gray-600 rounded px-4 py-2 text-white"
          >
            <option value="performance">性能分析</option>
            <option value="fault">故障分析</option>
            <option value="regulation">调节性能</option>
            <option value="utilization">利用率分析</option>
            <option value="revenue">收益分析</option>
          </select>
        </div>
        <button
          onClick={handleAnalyze}
          disabled={isAnalyzing}
          className="px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded text-white flex items-center gap-2 transition-colors disabled:opacity-50"
        >
          <BarChart3 className="w-5 h-5" />
          {isAnalyzing ? "分析中..." : "开始分析"}
        </button>
      </div>
    </div>
  );
}
