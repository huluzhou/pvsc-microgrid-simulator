import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { BarChart3, Download } from "lucide-react";
import ResultCharts from "../components/analytics/ResultCharts";

interface AnalysisResult {
  analysis_type: string;
  summary: Record<string, any>;
  details: Record<string, any>;
  charts: Array<{
    title: string;
    chart_type: string;
    data: any;
  }>;
}

export default function Analytics() {
  const [analysisType, setAnalysisType] = useState("performance");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [startTime, setStartTime] = useState<string>("");
  const [endTime, setEndTime] = useState<string>("");
  const [deviceIds] = useState<string[]>([]);

  const handleAnalyze = async () => {
    setIsAnalyzing(true);
    setResult(null);
    try {
      const result = await invoke<AnalysisResult>("analyze_performance", {
        request: {
          device_ids: deviceIds,
          start_time: startTime ? new Date(startTime).getTime() / 1000 : Date.now() / 1000 - 3600,
          end_time: endTime ? new Date(endTime).getTime() / 1000 : Date.now() / 1000,
          analysis_type: analysisType,
        },
      });
      setResult(result);
    } catch (error) {
      console.error("Analysis failed:", error);
      alert("分析失败：" + error);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleGenerateReport = async () => {
    try {
      const reportPath = await invoke<string>("generate_report", {
        request: {
          report_type: analysisType,
          device_ids: deviceIds,
          start_time: startTime ? new Date(startTime).getTime() / 1000 : Date.now() / 1000 - 3600,
          end_time: endTime ? new Date(endTime).getTime() / 1000 : Date.now() / 1000,
          format: "pdf",
        },
      });
      alert(`报告已生成：${reportPath}`);
    } catch (error) {
      console.error("Report generation failed:", error);
      alert("报告生成失败：" + error);
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6 text-white">数据分析</h1>
      
      {/* 配置面板 */}
      <div className="bg-gray-800 rounded-lg p-6 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              分析类型
            </label>
            <select
              value={analysisType}
              onChange={(e) => setAnalysisType(e.target.value)}
              className="bg-gray-700 border border-gray-600 rounded px-4 py-2 text-white w-full"
            >
              <option value="performance">性能分析</option>
              <option value="fault">故障分析</option>
              <option value="regulation">调节性能</option>
              <option value="utilization">利用率分析</option>
              <option value="revenue">收益分析</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              开始时间
            </label>
            <input
              type="datetime-local"
              value={startTime}
              onChange={(e) => setStartTime(e.target.value)}
              className="bg-gray-700 border border-gray-600 rounded px-4 py-2 text-white w-full"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              结束时间
            </label>
            <input
              type="datetime-local"
              value={endTime}
              onChange={(e) => setEndTime(e.target.value)}
              className="bg-gray-700 border border-gray-600 rounded px-4 py-2 text-white w-full"
            />
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleAnalyze}
            disabled={isAnalyzing}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded text-white flex items-center gap-2 transition-colors disabled:opacity-50"
          >
            <BarChart3 className="w-5 h-5" />
            {isAnalyzing ? "分析中..." : "开始分析"}
          </button>
          {result && (
            <button
              onClick={handleGenerateReport}
              className="px-6 py-3 bg-green-600 hover:bg-green-700 rounded text-white flex items-center gap-2 transition-colors"
            >
              <Download className="w-5 h-5" />
              生成报告
            </button>
          )}
        </div>
      </div>

      {/* 分析结果 */}
      {result && (
        <div className="space-y-6">
          {/* 摘要信息 */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-lg font-semibold text-white mb-4">分析摘要</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.entries(result.summary).map(([deviceId, summary]) => (
                <div key={deviceId} className="bg-gray-700 rounded p-4">
                  <h3 className="text-sm font-medium text-gray-300 mb-2">{deviceId}</h3>
                  <pre className="text-xs text-white overflow-auto">
                    {JSON.stringify(summary, null, 2)}
                  </pre>
                </div>
              ))}
            </div>
          </div>

          {/* 图表 */}
          {result.charts && result.charts.length > 0 && (
            <div className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-lg font-semibold text-white mb-4">分析图表</h2>
              <ResultCharts charts={result.charts} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
