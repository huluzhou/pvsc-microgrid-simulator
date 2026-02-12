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
  Settings2,
} from 'lucide-react';
import MultiSeriesChart, { type SeriesItem } from '../components/monitoring/MultiSeriesChart';
import ResultCharts from '../components/analytics/ResultCharts';
import AnalysisSummaryView from '../components/analytics/AnalysisSummaryView';
import DataItemConfigDialog from '../components/dashboard/DataItemConfigDialog';
import PerformanceDataMappingDialog, {
  type PerformanceDataMapping,
  PERFORMANCE_INDICATORS,
} from '../components/analytics/PerformanceDataMappingDialog';
import type { DataItemDisplayConfig } from '../types/dataItemConfig';
import { transformValue } from '../types/dataItemConfig';

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

/** 电价配置（收益分析） */
interface PriceConfig {
  tou_prices: number[];
  voltage_level: string;
  tariff_type: string;
  demand_charge_per_kw_month?: number;
  capacity_charge_per_kva_month?: number;
}

/** 分析请求（与 Rust AnalysisRequest 一致） */
interface AnalysisRequestPayload {
  data_source: 'local_file' | 'csv';
  file_path: string | null;
  start_time: number;
  end_time: number;
  analysis_type: string;
  data_item_keys: string[];
  gateway_meter_active_power_key: string | null;
  price_config: PriceConfig | null;
  series_data: Record<string, TimeSeriesPoint[]> | null;
  performance_standards?: string[] | null;
  performance_data_mapping?: {
    measured_power_key: string;
    reference_power_key?: string | null;
    rated_power_kw?: number | null;
    rated_capacity_kwh?: number | null;
    alignment_method?: string;
  } | null;
}

// ====== 常量 ======

const MAX_SELECTED_COLUMNS = 8;

const ANALYSIS_TYPES = [
  { value: 'performance', label: '性能分析' },
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
  // 收益分析：关口电表 key（为空则用当前选中的第一项）
  const [gatewayKeyForRevenue, setGatewayKeyForRevenue] = useState<string | null>(null);
  // 性能分析：指标多选（默认全选），每个指标旁标注来源标准
  const [performanceIndicators, setPerformanceIndicators] = useState<string[]>(
    () => PERFORMANCE_INDICATORS.map((i) => i.id)
  );
  // 性能分析：数据项映射（弹窗确认后保存，可随时修改）
  const [performanceDataMapping, setPerformanceDataMapping] = useState<PerformanceDataMapping | null>(null);
  const [showMappingDialog, setShowMappingDialog] = useState(false);
  const [mappingDialogReason, setMappingDialogReason] = useState<'analyze' | 'modify'>('analyze');
  // 数据项单位与方向配置（key -> config）
  const [dataItemConfig, setDataItemConfig] = useState<Record<string, DataItemDisplayConfig>>({});
  const [configDialogKey, setConfigDialogKey] = useState<string | null>(null);
  // 收益分析：电价配置
  const [priceConfig, setPriceConfig] = useState<PriceConfig>({
    tou_prices: Array.from({ length: 24 }, (_, i) => (i >= 8 && i < 12 ? 0.9 : i >= 18 && i < 22 ? 0.9 : 0.4)),
    voltage_level: '1_10kv',
    tariff_type: 'single',
  });

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
      setDataItemConfig({});
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
      setDataItemConfig({});
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

  /** 从已加载数据推断时间范围；keysOverride 用于分析时使用映射配置的 key，不依赖左侧边栏勾选 */
  const getTimeRange = useCallback(
    (keysOverride?: string[]) => {
      let start = 0;
      let end = Date.now() / 1000;
      let keysToUse = keysOverride && keysOverride.length > 0 ? keysOverride : selectedKeys;
      if (keysToUse.length === 0 && dataSource === 'csv') {
        keysToUse = Object.keys(csvSeries);
      }
      if (keysToUse.length === 0 && dataSource === 'local_file') {
        keysToUse = Object.keys(dbSeries);
      }
      if (dataSource === 'csv') {
        for (const key of keysToUse) {
          const pts = csvSeries[key] || [];
          for (const p of pts) {
            if (p.timestamp > 0) {
              start = start === 0 ? p.timestamp : Math.min(start, p.timestamp);
              end = Math.max(end, p.timestamp);
            }
          }
        }
      } else if (dataSource === 'local_file') {
        for (const key of keysToUse) {
          const pts = dbSeries[key] || [];
          for (const p of pts) {
            if (p.timestamp > 0) {
              start = start === 0 ? p.timestamp : Math.min(start, p.timestamp);
              end = Math.max(end, p.timestamp);
            }
          }
        }
      }
      if (start === 0) {
        start = end - 3600;
        if (keysOverride && keysOverride.length > 0) {
          start = 0;
          end = 2e9;
        }
      }
      return { start, end };
    },
    [dataSource, selectedKeys, csvSeries, dbSeries]
  );

  /** 构建分析请求的 series_data（仅 CSV 时传入） */
  const buildSeriesData = useCallback(
    (keys: string[]): Record<string, TimeSeriesPoint[]> | null => {
      if (dataSource !== 'csv' || keys.length === 0) return null;
      const out: Record<string, TimeSeriesPoint[]> = {};
      const { start, end } = getTimeRange(keys);
      for (const key of keys) {
        const pts = (csvSeries[key] || []).filter((p) => p.timestamp >= start && p.timestamp <= end);
        out[key] = pts;
      }
      return out;
    },
    [dataSource, csvSeries, getTimeRange]
  );

  /** 执行分析；mappingOverride 为弹窗确认时传入的映射 */
  const runAnalysis = useCallback(
    async (mappingOverride?: PerformanceDataMapping | null) => {
      if (selectedAnalysisTypes.length === 0) {
        setError('请先选择分析类型');
        return;
      }
      if (!dataSource || !filePath) {
        setError('请先加载本地数据库或 CSV 文件');
        return;
      }
      const hasPerformance = selectedAnalysisTypes.includes('performance');
      const mapping = mappingOverride ?? performanceDataMapping;

      if (hasPerformance && performanceIndicators.length === 0) {
        setError('请至少选择一个性能分析指标');
        return;
      }
      if (hasPerformance && !mapping) {
        setMappingDialogReason('analyze');
        setShowMappingDialog(true);
        return;
      }

      const keysForTimeRange: string[] = [];
      for (const t of selectedAnalysisTypes) {
        if (t === 'revenue') {
          const gk = gatewayKeyForRevenue || selectedKeys[0];
          if (gk) keysForTimeRange.push(gk);
        } else if (t === 'performance' && mapping) {
          keysForTimeRange.push(mapping.measured_power_key);
          if (mapping.reference_power_key) keysForTimeRange.push(mapping.reference_power_key);
        } else {
          keysForTimeRange.push(...selectedKeys);
        }
      }
      const { start, end } = getTimeRange([...new Set(keysForTimeRange)]);
      setIsAnalyzing(true);
      setError(null);
      setAnalysisResults([]);
      try {
        const results: AnalysisResult[] = [];
        for (const analysisType of selectedAnalysisTypes) {
          const isRevenue = analysisType === 'revenue';
          const gatewayKey = isRevenue ? (gatewayKeyForRevenue || selectedKeys[0] || null) : null;
          if (isRevenue && !gatewayKey) {
            setError('收益分析请至少选择一个关口电表有功功率数据项');
            continue;
          }
          let dataItemKeys: string[];
          let keysForRequest: string[];
          if (isRevenue) {
            dataItemKeys = [];
            keysForRequest = [gatewayKey!];
          } else {
            if (mapping) {
              dataItemKeys = [
                mapping.measured_power_key,
                ...(mapping.reference_power_key ? [mapping.reference_power_key] : []),
              ];
              keysForRequest = dataItemKeys;
            } else {
              dataItemKeys = selectedKeys;
              keysForRequest = selectedKeys;
            }
          }
          if (keysForRequest.length === 0) {
            setError('请至少选择一个数据项');
            continue;
          }
          const request: AnalysisRequestPayload = {
            data_source: dataSource,
            file_path: filePath,
            start_time: start,
            end_time: end,
            analysis_type: analysisType,
            data_item_keys: dataItemKeys,
            gateway_meter_active_power_key: gatewayKey,
            price_config: isRevenue ? priceConfig : null,
            series_data: dataSource === 'csv' ? buildSeriesData(keysForRequest) : null,
            performance_standards: hasPerformance ? performanceIndicators : null,
            performance_data_mapping: hasPerformance && mapping
              ? {
                  measured_power_key: mapping.measured_power_key,
                  reference_power_key: mapping.reference_power_key,
                  rated_power_kw: mapping.rated_power_kw,
                  rated_capacity_kwh: mapping.rated_capacity_kwh,
                  alignment_method: mapping.alignment_method,
                }
              : null,
          };
          const result = await invoke<AnalysisResult>('analyze_performance', { request });
          results.push(result);
        }
        setAnalysisResults(results);
      } catch (e) {
        setError(`分析失败: ${String(e)}`);
      } finally {
        setIsAnalyzing(false);
      }
    },
    [
      selectedAnalysisTypes,
      dataSource,
      filePath,
      selectedKeys,
      gatewayKeyForRevenue,
      priceConfig,
      performanceDataMapping,
      performanceIndicators,
      getTimeRange,
      buildSeriesData,
    ]
  );

  /** 数据映射弹窗确认：保存映射，若从「开始分析」打开则继续执行分析 */
  const handleMappingConfirm = useCallback(
    (mapping: PerformanceDataMapping) => {
      setPerformanceDataMapping(mapping);
      setShowMappingDialog(false);
      if (mappingDialogReason === 'analyze') {
        runAnalysis(mapping);
      }
    },
    [runAnalysis, mappingDialogReason]
  );

  /** 打开数据映射弹窗以修改配置 */
  const openMappingDialogToModify = useCallback(() => {
    setMappingDialogReason('modify');
    setShowMappingDialog(true);
  }, []);

  /** 导出分析报告 */
  const exportReport = useCallback(async () => {
    if (!dataSource || !filePath) {
      setError('请先加载数据后再导出报告');
      return;
    }
    const keysForTimeRange: string[] = [];
    for (const t of selectedAnalysisTypes) {
      if (t === 'revenue') {
        const gk = gatewayKeyForRevenue || selectedKeys[0];
        if (gk) keysForTimeRange.push(gk);
      } else if (t === 'performance' && performanceDataMapping) {
        keysForTimeRange.push(performanceDataMapping.measured_power_key);
        if (performanceDataMapping.reference_power_key) keysForTimeRange.push(performanceDataMapping.reference_power_key);
      } else {
        keysForTimeRange.push(...selectedKeys);
      }
    }
    const { start, end } = getTimeRange([...new Set(keysForTimeRange)]);
    try {
      const savePath = await saveDialog({
        title: '导出分析报告',
        defaultPath: `analysis_report_${new Date().toISOString().slice(0, 10)}.json`,
        filters: [{ name: 'JSON', extensions: ['json'] }],
      });
      if (!savePath || typeof savePath !== 'string') return;
      const base = savePath.replace(/\.json$/i, '');
      setIsLoading(true);

      for (let i = 0; i < selectedAnalysisTypes.length; i++) {
        const analysisType = selectedAnalysisTypes[i];
        const isRevenue = analysisType === 'revenue';
        const isPerf = analysisType === 'performance';
        const gatewayKey = isRevenue ? (gatewayKeyForRevenue || selectedKeys[0] || null) : null;
        let dataItemKeys: string[];
        let keysForRequest: string[];
        if (isRevenue) {
          dataItemKeys = [];
          keysForRequest = gatewayKey ? [gatewayKey] : [];
        } else if (isPerf && performanceDataMapping) {
          dataItemKeys = [
            performanceDataMapping.measured_power_key,
            ...(performanceDataMapping.reference_power_key ? [performanceDataMapping.reference_power_key] : []),
          ];
          keysForRequest = dataItemKeys;
        } else {
          dataItemKeys = selectedKeys;
          keysForRequest = selectedKeys;
        }
        const reportPath =
          selectedAnalysisTypes.length === 1 ? savePath : `${base}_${analysisType}.json`;
        const hasPerf = analysisType === 'performance';
        const reportRequest = {
          report_type: analysisType,
          data_source: dataSource,
          file_path: filePath,
          start_time: start,
          end_time: end,
          data_item_keys: dataItemKeys,
          gateway_meter_active_power_key: gatewayKey,
          price_config: isRevenue ? priceConfig : null,
          series_data: dataSource === 'csv' ? buildSeriesData(keysForRequest) : null,
          format: 'json',
          report_path: reportPath,
          performance_standards: hasPerf ? performanceIndicators : null,
          performance_data_mapping: hasPerf && performanceDataMapping
            ? {
                measured_power_key: performanceDataMapping.measured_power_key,
                reference_power_key: performanceDataMapping.reference_power_key,
                rated_power_kw: performanceDataMapping.rated_power_kw,
                rated_capacity_kwh: performanceDataMapping.rated_capacity_kwh,
                alignment_method: performanceDataMapping.alignment_method,
              }
            : null,
        };
        await invoke<string>('generate_report', { request: reportRequest });
        setError(null);
      }
    } catch (e) {
      setError(`导出报告失败: ${String(e)}`);
    } finally {
      setIsLoading(false);
    }
  }, [
    selectedAnalysisTypes,
    dataSource,
    filePath,
    selectedKeys,
    gatewayKeyForRevenue,
    priceConfig,
    performanceDataMapping,
    performanceIndicators,
    getTimeRange,
    buildSeriesData,
  ]);

  // ====== 构建图表数据 ======

  const chartSeries: SeriesItem[] = useMemo(() => {
    const cfg = (key: string) => dataItemConfig[key];
    if (dataSource === 'csv') {
      return selectedKeys
        .map((key) => {
          const col = csvColumns.find((c) => c.key === key);
          const rawData = csvSeries[key] || [];
          if (!col || rawData.length === 0) return null;
          const data = rawData.map((p) => ({
            timestamp: p.timestamp,
            value: transformValue(p.value, cfg(key)),
          }));
          return {
            key: col.key,
            label: col.key,
            data,
          };
        })
        .filter((s): s is SeriesItem => s !== null);
    }
    if (dataSource === 'local_file') {
      return selectedKeys
        .map((key) => {
          const col = dbColumns.find((c) => c.key === key);
          const rawData = dbSeries[key] || [];
          if (!col || rawData.length === 0) return null;
          const data = rawData.map((p) => ({
            timestamp: p.timestamp,
            value: transformValue(p.value, cfg(key)),
          }));
          return {
            key: col.key,
            label: col.key,
            data,
          };
        })
        .filter((s): s is SeriesItem => s !== null);
    }
    return [];
  }, [dataSource, selectedKeys, csvColumns, csvSeries, dbColumns, dbSeries, dataItemConfig]);

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
        items: cols.map((c) => ({ key: c.key, label: c.key, dataItem: c.data_item })),
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
        items: cols.map((c) => ({ key: c.key, label: c.key, dataItem: c.field_name })),
      }));
    }
    return [];
  }, [dataSource, csvColumns, dbColumns]);

  /** 所有可选列（用于数据映射弹窗） */
  const availableColumns = useMemo(() => {
    return columnGroups.flatMap((g) => g.items.map((i) => ({ key: i.key, label: i.label || i.dataItem })));
  }, [columnGroups]);

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
                              <div
                                key={item.key}
                                className={`flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors ${
                                  isChecked ? 'bg-blue-50 text-blue-700' : 'hover:bg-gray-50 text-gray-600'
                                } ${isDisabled ? 'opacity-50' : ''}`}
                              >
                                <label className="flex items-center gap-2 flex-1 min-w-0 cursor-pointer">
                                  <input
                                    type="checkbox"
                                    checked={isChecked}
                                    disabled={isDisabled}
                                    onChange={() => toggleColumn(item.key)}
                                    className="w-3 h-3 rounded border-gray-300 text-blue-600 focus:ring-blue-500 flex-shrink-0"
                                  />
                                  <span className="break-words line-clamp-2 truncate" title={item.key}>
                                    {item.label}
                                  </span>
                                </label>
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setConfigDialogKey(item.key);
                                  }}
                                  className="p-0.5 rounded hover:bg-gray-200 text-gray-400 hover:text-gray-600 flex-shrink-0"
                                  title="配置单位与方向"
                                >
                                  <Settings2 className="w-3 h-3" />
                                </button>
                              </div>
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
            {selectedAnalysisTypes.includes('performance') && (
              <div className="space-y-1 border-t border-gray-200 pt-2 mt-2">
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs text-gray-500">分析指标（默认全选）</label>
                  <button
                    onClick={() =>
                      setPerformanceIndicators((prev) =>
                        prev.length === PERFORMANCE_INDICATORS.length
                          ? []
                          : PERFORMANCE_INDICATORS.map((i) => i.id)
                      )
                    }
                    className="text-xs text-blue-500 hover:text-blue-700"
                  >
                    {performanceIndicators.length === PERFORMANCE_INDICATORS.length ? '全不选' : '全选'}
                  </button>
                </div>
                <div className="space-y-0.5 max-h-32 overflow-y-auto">
                  {PERFORMANCE_INDICATORS.map((ind) => (
                    <label
                      key={ind.id}
                      className="flex items-center gap-2 px-2 py-0.5 rounded text-xs cursor-pointer hover:bg-gray-100"
                    >
                      <input
                        type="checkbox"
                        checked={performanceIndicators.includes(ind.id)}
                        onChange={() => {
                          setPerformanceIndicators((prev) =>
                            prev.includes(ind.id) ? prev.filter((x) => x !== ind.id) : [...prev, ind.id]
                          );
                        }}
                        className="w-3 h-3 rounded border-gray-300 text-green-600"
                      />
                      <span className="truncate flex-1" title={ind.label}>{ind.label}</span>
                      <span className="text-gray-400 flex-shrink-0" title={ind.standard}>{ind.standard}</span>
                    </label>
                  ))}
                </div>
                {performanceDataMapping && (
                  <button
                    onClick={openMappingDialogToModify}
                    className="mt-2 w-full text-xs text-blue-600 hover:text-blue-700 border border-blue-200 rounded py-1 hover:bg-blue-50"
                  >
                    修改数据项
                  </button>
                )}
              </div>
            )}
            {selectedAnalysisTypes.includes('revenue') && (
              <div className="space-y-1.5 border-t border-gray-200 pt-2 mt-2">
                <div>
                  <label className="text-xs text-gray-500 block mb-0.5">关口电表有功</label>
                  <select
                    value={gatewayKeyForRevenue || selectedKeys[0] || ''}
                    onChange={(e) => setGatewayKeyForRevenue(e.target.value || null)}
                    className="w-full text-xs border border-gray-300 rounded px-1.5 py-1 bg-white"
                  >
                    {selectedKeys.length === 0 ? (
                      <option value="">请先选择数据项</option>
                    ) : (
                      selectedKeys.map((k) => {
                      const col = csvColumns.find((c) => c.key === k) || dbColumns.find((c) => c.key === k);
                      return (
                        <option key={k} value={k}>
                          {col?.key ?? k}
                        </option>
                      );
                    })
                    )}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-gray-500 block mb-0.5">电压等级</label>
                  <select
                    value={priceConfig.voltage_level}
                    onChange={(e) => setPriceConfig((c) => ({ ...c, voltage_level: e.target.value }))}
                    className="w-full text-xs border border-gray-300 rounded px-1.5 py-1 bg-white"
                  >
                    <option value="under_1kv">不满 1kV</option>
                    <option value="1_10kv">1–10(20)kV</option>
                    <option value="35kv">35kV</option>
                    <option value="110kv">110kV</option>
                    <option value="220kv">220kV 及以上</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-gray-500 block mb-0.5">计费方式</label>
                  <select
                    value={priceConfig.tariff_type}
                    onChange={(e) => setPriceConfig((c) => ({ ...c, tariff_type: e.target.value }))}
                    className="w-full text-xs border border-gray-300 rounded px-1.5 py-1 bg-white"
                  >
                    <option value="single">单一制</option>
                    <option value="two_part">两部制</option>
                  </select>
                </div>
                <div className="grid grid-cols-3 gap-0.5">
                  <label className="text-xs text-gray-500 col-span-3">分时电价(元/kWh, 0–23时)</label>
                  {priceConfig.tou_prices.slice(0, 24).map((v, i) => (
                    <input
                      key={i}
                      type="number"
                      step="0.01"
                      min="0"
                      value={v}
                      onChange={(e) => {
                        const next = [...priceConfig.tou_prices];
                        next[i] = Number(e.target.value) || 0;
                        setPriceConfig((c) => ({ ...c, tou_prices: next }));
                      }}
                      className="w-full text-xs border border-gray-300 rounded px-0.5 py-0.5"
                      title={`${i}时`}
                    />
                  ))}
                </div>
              </div>
            )}
            <div className="flex gap-1">
              <button
                onClick={() => runAnalysis()}
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
                <div key={idx} className="bg-white rounded-lg border border-gray-200 p-4 overflow-hidden">
                  <h3 className="text-sm font-semibold text-gray-700 mb-3">
                    {ANALYSIS_TYPES.find((at) => at.value === result.analysis_type)?.label || result.analysis_type} - 分析结果
                  </h3>
                  {/* 摘要 */}
                  {result.summary && Object.keys(result.summary).length > 0 && (
                    <div className="mb-4 max-w-full overflow-x-auto">
                      <h4 className="text-xs font-medium text-gray-500 mb-2">摘要</h4>
                      <div className="bg-gray-50 rounded-lg border border-gray-200 p-3 overflow-x-auto min-w-0">
                        <AnalysisSummaryView data={result.summary} />
                      </div>
                    </div>
                  )}
                  {/* 详情（若有） */}
                  {result.details && typeof result.details === 'object' && !Array.isArray(result.details) && Object.keys(result.details).length > 0 && (
                    <div className="mb-4 max-w-full overflow-x-auto">
                      <h4 className="text-xs font-medium text-gray-500 mb-2">详情</h4>
                      <div className="bg-gray-50 rounded-lg border border-gray-200 p-3 overflow-x-auto min-w-0">
                        <AnalysisSummaryView data={result.details} />
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

      {/* 性能分析数据项映射弹窗 */}
      <PerformanceDataMappingDialog
        open={showMappingDialog}
        onClose={() => setShowMappingDialog(false)}
        onConfirm={handleMappingConfirm}
        availableColumns={availableColumns}
        selectedIndicatorIds={performanceIndicators}
        initialMapping={performanceDataMapping}
      />
      <DataItemConfigDialog
        open={configDialogKey != null}
        onClose={() => setConfigDialogKey(null)}
        onSave={(config) => {
          if (configDialogKey) {
            setDataItemConfig((prev) => ({ ...prev, [configDialogKey]: config }));
            setConfigDialogKey(null);
          }
        }}
        dataItemKey={configDialogKey ?? ''}
        dataItemName={
          configDialogKey
            ? (columnGroups.flatMap((g) => g.items).find((i) => i.key === configDialogKey)?.dataItem ?? undefined)
            : undefined
        }
        initialConfig={configDialogKey ? dataItemConfig[configDialogKey] : undefined}
      />
    </div>
  );
}
