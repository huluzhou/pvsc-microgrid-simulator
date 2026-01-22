/**
 * 数据分析页面 - 浅色主题
 */
import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { BarChart3, Download } from "lucide-react";
import ResultCharts from "../components/analytics/ResultCharts";

interface AnalysisResult {
  analysis_type: string;
  summary: Record<string, any>;
  details: Record<string, any>;
  charts: Array<{ title: string; chart_type: string; data: any }>;
}

export default function Analytics() {
  const [analysisType, setAnalysisType] = useState("performance");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [startTime, setStartTime] = useState<string>("");
  const [endTime] = useState<string>("");
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
      alert("报告生成失败：" + error);
    }
  };

  return (
    <div className="p-4 bg-gray-50 h-full overflow-y-auto">
      <h1 className="text-lg font-bold mb-4 text-gray-800">数据分析</h1>
      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4">
        <div className="grid grid-cols-2 gap-3 mb-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">分析类型</label>
            <select value={analysisType} onChange={(e) => setAnalysisType(e.target.value)} className="bg-white border border-gray-300 rounded px-2 py-1.5 text-sm text-gray-700 w-full">
              <option value="performance">性能分析</option>
              <option value="fault">故障分析</option>
              <option value="regulation">调节性能</option>
              <option value="utilization">利用率分析</option>
              <option value="revenue">收益分析</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">开始时间</label>
            <input type="datetime-local" value={startTime} onChange={(e) => setStartTime(e.target.value)} className="bg-white border border-gray-300 rounded px-2 py-1.5 text-sm text-gray-700 w-full" />
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={handleAnalyze} disabled={isAnalyzing} className="px-4 py-2 bg-blue-500 hover:bg-blue-600 rounded text-white text-sm flex items-center gap-2 transition-colors disabled:opacity-50">
            <BarChart3 className="w-4 h-4" />{isAnalyzing ? "分析中..." : "开始分析"}
          </button>
          {result && (
            <button onClick={handleGenerateReport} className="px-4 py-2 bg-green-500 hover:bg-green-600 rounded text-white text-sm flex items-center gap-2 transition-colors">
              <Download className="w-4 h-4" />生成报告
            </button>
          )}
        </div>
      </div>
      {result && (
        <div className="space-y-4">
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">分析摘要</h2>
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(result.summary).map(([deviceId, summary]) => (
                <div key={deviceId} className="bg-gray-50 rounded border border-gray-200 p-3">
                  <h3 className="text-xs font-medium text-gray-600 mb-2">{deviceId}</h3>
                  <pre className="text-xs text-gray-700 overflow-auto">{JSON.stringify(summary, null, 2)}</pre>
                </div>
              ))}
            </div>
          </div>
          {result.charts && result.charts.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <h2 className="text-sm font-semibold text-gray-700 mb-3">分析图表</h2>
              <ResultCharts charts={result.charts} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
