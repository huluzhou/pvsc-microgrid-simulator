/**
 * 数据看板 - 支持本地 DB / CSV 数据源，多数据项并行查看，集成数据分析
 */
import { useState, useCallback, useMemo } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { open as openDialog, save as saveDialog } from '@tauri-apps/plugin-dialog';
import {
  AlertTriangle,
  LayoutDashboard,
  Database,
  FileSpreadsheet,
  ChevronDown,
  ChevronRight,
  BarChart3,
  Download,
  Loader2,
} from 'lucide-react';
import MultiSeriesChart, { type SeriesItem } from '../components/monitoring/MultiSeriesChart';
import ResultCharts from '../components/analytics/ResultCharts';

// ====== 类型定义 ======

type DataSourceType = 'local_file' | 'csv';

/** 宽表 CSV 列元信息（与 Rust 端 ColumnMeta 对应） */
interface ColumnMeta {
  key: string;
  device_sn: string;
  data_item: string;
  short_label: string;
}

/** 时间序列数据点（与 Rust 端 TimeSeriesPoint 对应） */
interface TimeSeriesPoint {
  timestamp: number;
  value: number;
}

/** 宽表 CSV 解析结果 */
interface WideTableData {
  columns: ColumnMeta[];
  series: Record<string, TimeSeriesPoint[]>;
}

/** 本地 DB 列元信息（与 Rust 端 DbColumnMeta 对应） */
interface DbColumnMeta {
  key: string;
  device_id: string;
  field_name: string;
  short_label: string;
}

/** 分析结果 */
interface AnalysisResult {
  analysis_type: string;
  summary: Record<string, unknown>;
  details: Record<string, unknown>;
  charts: Array<{ title: string; chart_type: string; data: unknown }>;
}

// ====== 常量 ======

const MAX_SELECTED_COLUMNS = 8;

const ANALYSIS_TYPES = [
  { value: 'performance', label: '性能分析' },
  { value: 'fault', label: '故障分析' },
  { value: 'regulation', label: '调节性能' },
  { value: 'utilization', label: '利用率分析' },
  { value: 'revenue', label: '收益分析' },
];

// ====== 主组件 ======

export default function Dashboard() {
  // 数据源状态
  const [dataSource, setDataSource] = useState<DataSourceType | null>(null);
  const [filePath, setFilePath] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // CSV 数据
  const [csvColumns, setCsvColumns] = useState<ColumnMeta[]>([]);
  const [csvSeries, setCsvSeries] = useState<Record<string, TimeSeriesPoint[]>>({});

  // DB 数据
  const [dbColumns, setDbColumns] = useState<DbColumnMeta[]>([]);
  const [dbSeries, setDbSeries] = useState<Record<string, TimeSeriesPoint[]>>({});

  // 选中的数据列
  const [selectedKeys, setSelectedKeys] = useState<string[]>([]);

  // 分组展开状态
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({});

  // 数据分析状态
  const [selectedAnalysisTypes, setSelectedAnalysisTypes] = useState<string[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResults, setAnalysisResults] = useState<AnalysisResult[]>([]);

  // ====== 数据源加载 ======

  /** 加载本地 DB 文件 */
  const loadLocalDb = useCallback(async () => {
    setError(null);
    try {
      const path = await openDialog({
        title: '选择本地数据库',
        filters: [{ name: 'SQLite', extensions: ['db', 'sqlite'] }],
      });
      if (!path || typeof path !== 'string') return;
      setIsLoading(true);
      setFilePath(path);

      const columns = await invoke<DbColumnMeta[]>('dashboard_list_db_columns', { dbPath: path });
      setDbColumns(columns || []);
      setDbSeries({});
      setCsvColumns([]);
      setCsvSeries({});
      setSelectedKeys([]);
      setDataSource('local_file');
      setAnalysisResults([]);

      // 默认展开所有分组
      const groups: Record<string, boolean> = {};
      for (const col of columns || []) {
        groups[col.device_id] = true;
      }
      setExpandedGroups(groups);
    } catch (e) {
      setError(String(e));
    } finally {
      setIsLoading(false);
    }
  }, []);

  /** 加载 CSV 文件 */
  const loadCsv = useCallback(async () => {
    setError(null);
    try {
      const path = await openDialog({
        title: '选择 CSV 文件',
        filters: [{ name: 'CSV', extensions: ['csv'] }],
      });
      if (!path || typeof path !== 'string') return;
      setIsLoading(true);
      setFilePath(path);

      const result = await invoke<WideTableData>('dashboard_parse_wide_csv', { filePath: path });
      setCsvColumns(result.columns || []);
      setCsvSeries(result.series || {});
      setDbColumns([]);
      setDbSeries({});
      setSelectedKeys([]);
      setDataSource('csv');
      setAnalysisResults([]);

      // 默认展开所有分组
      const groups: Record<string, boolean> = {};
      for (const col of result.columns || []) {
        const groupKey = col.device_sn || '未分组';
        groups[groupKey] = true;
      }
      setExpandedGroups(groups);
    } catch (e) {
      setError(String(e));
    } finally {
      setIsLoading(false);
    }
  }, []);

  // ====== 列选择 ======

  /** 切换选中数据列 */
  const toggleColumn = useCallback(async (key: string) => {
    setSelectedKeys((prev) => {
      if (prev.includes(key)) {
        return prev.filter((k) => k !== key);
      }
      if (prev.length >= MAX_SELECTED_COLUMNS) {
        return prev; // 超出限制不添加
      }
      return [...prev, key];
    });

    // 如果是 DB 数据源且该列数据尚未加载，异步加载
    if (dataSource === 'local_file' && filePath && !dbSeries[key]) {
      const col = dbColumns.find((c) => c.key === key);
      if (col) {
        try {
          const data = await invoke<TimeSeriesPoint[]>('dashboard_query_db_series', {
            dbPath: filePath,
            deviceId: col.device_id,
            fieldName: col.field_name,
            maxPoints: 5000,
          });
          setDbSeries((prev) => ({ ...prev, [key]: data || [] }));
        } catch (e) {
          setError(`加载 ${col.short_label} 失败: ${String(e)}`);
        }
      }
    }
  }, [dataSource, filePath, dbSeries, dbColumns]);

  /** 切换分组展开/折叠 */
  const toggleGroup = useCallback((groupKey: string) => {
    setExpandedGroups((prev) => ({ ...prev, [groupKey]: !prev[groupKey] }));
  }, []);

  /** 全选/取消分组内所有列 */
  const toggleGroupAll = useCallback(async (groupKeys: string[], isSelected: boolean) => {
    if (isSelected) {
      // 取消选择分组内所有列
      setSelectedKeys((prev) => prev.filter((k) => !groupKeys.includes(k)));
    } else {
      // 选中分组内所有列（不超过最大限制）
      setSelectedKeys((prev) => {
        const newKeys = groupKeys.filter((k) => !prev.includes(k));
        const available = MAX_SELECTED_COLUMNS - prev.length;
        return [...prev, ...newKeys.slice(0, available)];
      });

      // 如果是 DB 数据源，加载未加载的列数据
      if (dataSource === 'local_file' && filePath) {
        const toLoad = groupKeys.filter((k) => !dbSeries[k]);
        for (const key of toLoad) {
          const col = dbColumns.find((c) => c.key === key);
          if (col) {
            try {
              const data = await invoke<TimeSeriesPoint[]>('dashboard_query_db_series', {
                dbPath: filePath,
                deviceId: col.device_id,
                fieldName: col.field_name,
                maxPoints: 5000,
              });
              setDbSeries((prev) => ({ ...prev, [key]: data || [] }));
            } catch {
              // 静默失败
            }
          }
        }
      }
    }
  }, [dataSource, filePath, dbSeries, dbColumns]);

  // ====== 数据分析 ======

  /** 切换分析类型选中 */
  const toggleAnalysisType = useCallback((type: string) => {
    setSelectedAnalysisTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  }, []);

  /** 执行分析 */
  const runAnalysis = useCallback(async () => {
    if (selectedAnalysisTypes.length === 0) {
      setError('请先选择分析类型');
      return;
    }
    setIsAnalyzing(true);
    setError(null);
    setAnalysisResults([]);
    try {
      const results: AnalysisResult[] = [];
      for (const analysisType of selectedAnalysisTypes) {
        const result = await invoke<AnalysisResult>('analyze_performance', {
          request: {
            device_ids: [],
            start_time: Date.now() / 1000 - 3600,
            end_time: Date.now() / 1000,
            analysis_type: analysisType,
          },
        });
        results.push(result);
      }
      setAnalysisResults(results);
    } catch (e) {
      setError(`分析失败: ${String(e)}`);
    } finally {
      setIsAnalyzing(false);
    }
  }, [selectedAnalysisTypes]);

  /** 导出分析报告 */
  const exportReport = useCallback(async () => {
    try {
      const path = await saveDialog({
        title: '导出分析报告',
        defaultPath: `analysis_report_${new Date().toISOString().slice(0, 10)}.pdf`,
        filters: [{ name: 'PDF', extensions: ['pdf'] }],
      });
      if (!path || typeof path !== 'string') return;
      setIsLoading(true);

      for (const analysisType of selectedAnalysisTypes) {
        await invoke<string>('generate_report', {
          request: {
            report_type: analysisType,
            device_ids: [],
            start_time: Date.now() / 1000 - 3600,
            end_time: Date.now() / 1000,
            format: 'pdf',
          },
        });
      }
      setError(null);
    } catch (e) {
      setError(`导出报告失败: ${String(e)}`);
    } finally {
      setIsLoading(false);
    }
  }, [selectedAnalysisTypes]);

  // ====== 构建图表数据 ======

  const chartSeries: SeriesItem[] = useMemo(() => {
    if (dataSource === 'csv') {
      return selectedKeys
        .map((key) => {
          const col = csvColumns.find((c) => c.key === key);
          const data = csvSeries[key] || [];
          if (!col || data.length === 0) return null;
          return {
            key: col.key,
            label: col.short_label,
            data,
          };
        })
        .filter((s): s is SeriesItem => s !== null);
    }
    if (dataSource === 'local_file') {
      return selectedKeys
        .map((key) => {
          const col = dbColumns.find((c) => c.key === key);
          const data = dbSeries[key] || [];
          if (!col || data.length === 0) return null;
          return {
            key: col.key,
            label: col.short_label,
            data,
          };
        })
        .filter((s): s is SeriesItem => s !== null);
    }
    return [];
  }, [dataSource, selectedKeys, csvColumns, csvSeries, dbColumns, dbSeries]);

  // ====== 构建列分组 ======

  const columnGroups = useMemo(() => {
    if (dataSource === 'csv') {
      const groups: Record<string, ColumnMeta[]> = {};
      for (const col of csvColumns) {
        const groupKey = col.device_sn || '未分组';
        if (!groups[groupKey]) groups[groupKey] = [];
        groups[groupKey].push(col);
      }
      return Object.entries(groups).map(([groupKey, cols]) => ({
        groupKey,
        label: groupKey || '未分组',
        items: cols.map((c) => ({ key: c.key, label: c.short_label, dataItem: c.data_item })),
      }));
    }
    if (dataSource === 'local_file') {
      const groups: Record<string, DbColumnMeta[]> = {};
      for (const col of dbColumns) {
        if (!groups[col.device_id]) groups[col.device_id] = [];
        groups[col.device_id].push(col);
      }
      return Object.entries(groups).map(([deviceId, cols]) => ({
        groupKey: deviceId,
        label: deviceId,
        items: cols.map((c) => ({ key: c.key, label: c.short_label, dataItem: c.field_name })),
      }));
    }
    return [];
  }, [dataSource, csvColumns, dbColumns]);

  // ====== 渲染 ======

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* 顶部工具栏 */}
      <div className="px-4 py-2 bg-white border-b border-gray-200 flex items-center gap-3 flex-wrap">
        <h1 className="text-base font-semibold text-gray-800 flex items-center gap-2">
          <LayoutDashboard className="w-5 h-5" />
          数据看板
        </h1>
        <div className="flex items-center gap-2">
          <button
            onClick={loadLocalDb}
            disabled={isLoading}
            className={`px-3 py-1.5 rounded text-xs flex items-center gap-1.5 transition-colors ${
              dataSource === 'local_file'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <Database className="w-3.5 h-3.5" />
            加载本地数据库
          </button>
          <button
            onClick={loadCsv}
            disabled={isLoading}
            className={`px-3 py-1.5 rounded text-xs flex items-center gap-1.5 transition-colors ${
              dataSource === 'csv'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            加载 CSV 文件
          </button>
        </div>
        {filePath && (
          <span className="text-xs text-gray-400 truncate max-w-sm" title={filePath}>
            {filePath}
          </span>
        )}
        {isLoading && <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />}
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="px-4 py-2 bg-red-50 border-b border-red-200 flex items-center gap-2 text-red-700 text-sm">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span className="flex-1">{error}</span>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-600 text-xs">
            关闭
          </button>
        </div>
      )}

      {/* 主内容区 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 左侧边栏 - 数据列选择 + 分析控制 */}
        <div className="w-72 bg-white border-r border-gray-200 flex flex-col overflow-hidden">
          {/* 数据列选择 */}
          <div className="flex-1 overflow-y-auto">
            <div className="p-2 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-gray-700">
                数据项 ({selectedKeys.length}/{MAX_SELECTED_COLUMNS})
              </h2>
              {selectedKeys.length > 0 && (
                <button
                  onClick={() => setSelectedKeys([])}
                  className="text-xs text-blue-500 hover:text-blue-700"
                >
                  清除
                </button>
              )}
            </div>

            {columnGroups.length === 0 ? (
              <div className="p-4 text-center text-gray-400 text-sm">
                请先加载数据库或 CSV 文件
              </div>
            ) : (
              <div className="p-1">
                {columnGroups.map((group) => {
                  const isExpanded = expandedGroups[group.groupKey] !== false;
                  const groupItemKeys = group.items.map((i) => i.key);
                  const selectedInGroup = groupItemKeys.filter((k) => selectedKeys.includes(k));
                  const allGroupSelected = selectedInGroup.length === groupItemKeys.length && groupItemKeys.length > 0;

                  return (
                    <div key={group.groupKey} className="mb-1">
                      {/* 分组标题 */}
                      <div className="flex items-center gap-1 px-2 py-1.5 rounded hover:bg-gray-50 cursor-pointer select-none">
                        <button
                          onClick={() => toggleGroup(group.groupKey)}
                          className="flex items-center gap-1 flex-1 min-w-0"
                        >
                          {isExpanded ? (
                            <ChevronDown className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                          ) : (
                            <ChevronRight className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                          )}
                          <span className="text-xs font-medium text-gray-600 truncate" title={group.label}>
                            {group.label}
                          </span>
                          <span className="text-xs text-gray-400 flex-shrink-0">
                            ({selectedInGroup.length}/{group.items.length})
                          </span>
                        </button>
                        <button
                          onClick={() => toggleGroupAll(groupItemKeys, allGroupSelected)}
                          className="text-xs text-blue-500 hover:text-blue-700 flex-shrink-0 px-1"
                        >
                          {allGroupSelected ? '取消' : '全选'}
                        </button>
                      </div>

                      {/* 分组内的数据列 */}
                      {isExpanded && (
                        <div className="ml-4 space-y-0.5">
                          {group.items.map((item) => {
                            const isChecked = selectedKeys.includes(item.key);
                            const isDisabled = !isChecked && selectedKeys.length >= MAX_SELECTED_COLUMNS;
                            return (
                              <label
                                key={item.key}
                                className={`flex items-center gap-2 px-2 py-1 rounded text-xs cursor-pointer transition-colors ${
                                  isChecked ? 'bg-blue-50 text-blue-700' : 'hover:bg-gray-50 text-gray-600'
                                } ${isDisabled ? 'opacity-50 cursor-not-allowed' : ''}`}
                              >
                                <input
                                  type="checkbox"
                                  checked={isChecked}
                                  disabled={isDisabled}
                                  onChange={() => toggleColumn(item.key)}
                                  className="w-3 h-3 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                />
                                <span className="truncate" title={item.key}>
                                  {item.dataItem}
                                </span>
                              </label>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* 数据分析控制区 */}
          <div className="border-t border-gray-200 p-2 space-y-2 bg-gray-50">
            <h3 className="text-xs font-semibold text-gray-600 flex items-center gap-1">
              <BarChart3 className="w-3.5 h-3.5" />
              数据分析
            </h3>
            <div className="space-y-1">
              {ANALYSIS_TYPES.map((at) => (
                <label
                  key={at.value}
                  className={`flex items-center gap-2 px-2 py-1 rounded text-xs cursor-pointer transition-colors ${
                    selectedAnalysisTypes.includes(at.value) ? 'bg-green-50 text-green-700' : 'hover:bg-gray-100 text-gray-600'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedAnalysisTypes.includes(at.value)}
                    onChange={() => toggleAnalysisType(at.value)}
                    className="w-3 h-3 rounded border-gray-300 text-green-600 focus:ring-green-500"
                  />
                  {at.label}
                </label>
              ))}
            </div>
            <div className="flex gap-1">
              <button
                onClick={runAnalysis}
                disabled={isAnalyzing || selectedAnalysisTypes.length === 0}
                className="flex-1 px-2 py-1.5 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 text-white rounded text-xs flex items-center justify-center gap-1 transition-colors"
              >
                {isAnalyzing ? (
                  <><Loader2 className="w-3 h-3 animate-spin" /> 分析中...</>
                ) : (
                  <><BarChart3 className="w-3 h-3" /> 开始分析</>
                )}
              </button>
              {analysisResults.length > 0 && (
                <button
                  onClick={exportReport}
                  disabled={isLoading}
                  className="px-2 py-1.5 bg-green-500 hover:bg-green-600 text-white rounded text-xs flex items-center gap-1 transition-colors"
                >
                  <Download className="w-3 h-3" /> 导出
                </button>
              )}
            </div>
          </div>
        </div>

        {/* 右侧主区域 - 图表 + 分析结果 */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* 数据图表 */}
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-gray-700">数据趋势</h3>
              {chartSeries.length > 0 && (
                <span className="text-xs text-gray-400">{chartSeries.length} 条曲线</span>
              )}
            </div>
            <div className="h-80">
              <MultiSeriesChart series={chartSeries} enableDataZoom={true} />
            </div>
          </div>

          {/* 分析结果展示 */}
          {analysisResults.length > 0 && (
            <div className="space-y-4">
              {analysisResults.map((result, idx) => (
                <div key={idx} className="bg-white rounded-lg border border-gray-200 p-4">
                  <h3 className="text-sm font-semibold text-gray-700 mb-3">
                    {ANALYSIS_TYPES.find((at) => at.value === result.analysis_type)?.label || result.analysis_type} - 分析结果
                  </h3>
                  {/* 摘要 */}
                  {result.summary && Object.keys(result.summary).length > 0 && (
                    <div className="mb-4">
                      <h4 className="text-xs font-medium text-gray-500 mb-2">摘要</h4>
                      <div className="grid grid-cols-2 lg:grid-cols-3 gap-2">
                        {Object.entries(result.summary).map(([key, value]) => (
                          <div key={key} className="bg-gray-50 rounded border border-gray-200 p-2">
                            <div className="text-xs text-gray-500 truncate" title={key}>{key}</div>
                            <div className="text-sm font-medium text-gray-800 mt-0.5">
                              {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {/* 分析图表 */}
                  {result.charts && result.charts.length > 0 && (
                    <ResultCharts charts={result.charts} />
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
