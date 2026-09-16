import dagre from 'dagre'
import { Position, type Edge, type Node } from '@xyflow/react'

export const NODE_WIDTH = 260
export const NODE_HEIGHT = 92

/** The chart's Dagre layout pass - spacing values from the brand style
 * guide (§ "Rendering the hierarchy"): a left-to-right layered tree with
 * 24px between siblings and 40px between ranks (generations). */
export function layoutWithDagre<TNode extends Node>(nodes: TNode[], edges: Edge[]): TNode[] {
  const graph = new dagre.graphlib.Graph()
  graph.setDefaultEdgeLabel(() => ({}))
  graph.setGraph({ rankdir: 'LR', nodesep: 24, ranksep: 40 })

  for (const node of nodes) {
    graph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT })
  }
  for (const edge of edges) {
    graph.setEdge(edge.source, edge.target)
  }

  dagre.layout(graph)

  return nodes.map((node) => {
    const position = graph.node(node.id)
    return {
      ...node,
      position: { x: position.x - NODE_WIDTH / 2, y: position.y - NODE_HEIGHT / 2 },
      targetPosition: Position.Left,
      sourcePosition: Position.Right,
    } as TNode
  })
}
