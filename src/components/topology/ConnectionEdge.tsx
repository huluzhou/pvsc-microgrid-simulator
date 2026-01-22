/**
 * 连接边组件 - 直线连接
 */
import { memo } from 'react';
import { EdgeProps, getStraightPath } from 'reactflow';

function ConnectionEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  selected,
}: EdgeProps) {
  const [edgePath] = getStraightPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
  });

  return (
    <g className="react-flow__edge">
      {/* 主线条 */}
      <path
        id={id}
        className="react-flow__edge-path"
        d={edgePath}
        style={{
          stroke: selected ? '#3b82f6' : '#666',
          strokeWidth: selected ? 3 : 2,
          fill: 'none',
        }}
      />
      {/* 选中时的高亮效果 */}
      {selected && (
        <path
          d={edgePath}
          style={{
            stroke: '#3b82f6',
            strokeWidth: 6,
            strokeOpacity: 0.2,
            fill: 'none',
          }}
        />
      )}
    </g>
  );
}

export default memo(ConnectionEdge);
