import { BaseEdge, EdgeProps, getBezierPath } from "reactflow";

export default function ConnectionEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  markerEnd,
}: EdgeProps) {
  const [edgePath] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  return (
    <>
      <BaseEdge
        path={edgePath}
        id={id}
        style={{
          ...style,
          stroke: "#60a5fa",
          strokeWidth: 2,
        }}
        markerEnd={markerEnd}
      />
    </>
  );
}
