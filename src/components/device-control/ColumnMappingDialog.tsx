/**
 * 列映射配置对话框 - 浅色主题
 */
import { useState, useCallback } from 'react';
import { X } from 'lucide-react';
import { LoadCalculation, ColumnSource, PowerUnit } from '../../types/dataSource';

interface ColumnMappingDialogProps {
  columns: string[];
  initialValue?: LoadCalculation;
  onSave: (config: LoadCalculation) => void;
  onClose: () => void;
}

interface ColumnInputProps {
  label: string;
  description: string;
  color: string;
  columns: string[];
  value?: ColumnSource;
  onChange: (source: ColumnSource | undefined) => void;
  required?: boolean;
}

function ColumnInput({ label, description, color, columns, value, onChange, required = false }: ColumnInputProps) {
  return (
    <div className="p-2 bg-gray-50 rounded border border-gray-200">
      <div className="flex items-center justify-between mb-1">
        <label className="text-xs font-medium text-gray-700 flex items-center gap-1">
          <div className={`w-2 h-2 rounded-full ${color}`} />
          {label}{required && <span className="text-red-500">*</span>}
        </label>
      </div>
      <div className="text-xs text-gray-500 mb-1">{description}</div>
      <div className="flex gap-2">
        <select value={value?.columnName ?? ''} onChange={(e) => { if (e.target.value) onChange({ columnName: e.target.value, unit: value?.unit ?? 'kW' }); else onChange(undefined); }} className="flex-1 px-2 py-1 bg-white border border-gray-300 rounded text-xs">
          <option value="">-- 不使用 --</option>
          {columns.map((col) => <option key={col} value={col}>{col}</option>)}
        </select>
        <select value={value?.unit ?? 'kW'} onChange={(e) => { if (value?.columnName) onChange({ columnName: value.columnName, unit: e.target.value as PowerUnit }); }} disabled={!value?.columnName} className="w-14 px-1 py-1 bg-white border border-gray-300 rounded text-xs disabled:opacity-50">
          <option value="W">W</option>
          <option value="kW">kW</option>
          <option value="MW">MW</option>
        </select>
      </div>
    </div>
  );
}

export default function ColumnMappingDialog({ columns, initialValue, onSave, onClose }: ColumnMappingDialogProps) {
  const [gridMeter, setGridMeter] = useState<ColumnSource | undefined>(initialValue?.gridMeter);
  const [pvGeneration, setPvGeneration] = useState<ColumnSource | undefined>(initialValue?.pvGeneration);
  const [storagePower, setStoragePower] = useState<ColumnSource | undefined>(initialValue?.storagePower);
  const [chargerPower, setChargerPower] = useState<ColumnSource | undefined>(initialValue?.chargerPower);

  const handleSave = useCallback(() => {
    if (!gridMeter) return;
    onSave({ gridMeter, pvGeneration, storagePower, chargerPower });
  }, [gridMeter, pvGeneration, storagePower, chargerPower, onSave]);

  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4">
        <div className="flex items-center justify-between p-3 border-b border-gray-200">
          <h3 className="text-sm font-semibold text-gray-800">负载计算列映射</h3>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded transition-colors">
            <X className="w-4 h-4 text-gray-500" />
          </button>
        </div>
        <div className="p-3 space-y-3 max-h-[60vh] overflow-y-auto">
          <div className="p-2 bg-blue-50 border border-blue-200 rounded text-xs">
            <div className="text-blue-700 font-medium mb-1">负载计算公式</div>
            <div className="font-mono text-blue-900">负载 = 关口电表(下网) + 光伏发电 - 储能充电 - 充电桩充电</div>
          </div>
          <div className="space-y-2">
            <ColumnInput label="关口电表功率" description="正值=下网" color="bg-blue-500" columns={columns} value={gridMeter} onChange={setGridMeter} required />
            <ColumnInput label="光伏发电功率" description="正值=发电" color="bg-orange-500" columns={columns} value={pvGeneration} onChange={setPvGeneration} />
            <ColumnInput label="储能功率" description="正值=充电" color="bg-green-500" columns={columns} value={storagePower} onChange={setStoragePower} />
            <ColumnInput label="充电桩功率" description="正值=充电" color="bg-cyan-500" columns={columns} value={chargerPower} onChange={setChargerPower} />
          </div>
        </div>
        <div className="flex gap-2 p-3 border-t border-gray-200">
          <button onClick={handleSave} disabled={!gridMeter} className="flex-1 px-3 py-1.5 bg-blue-500 hover:bg-blue-600 rounded text-white text-sm transition-colors disabled:opacity-50">确认配置</button>
          <button onClick={onClose} className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded text-gray-700 text-sm transition-colors">取消</button>
        </div>
      </div>
    </div>
  );
}
