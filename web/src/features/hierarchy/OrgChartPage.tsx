import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Background,
  Controls,
  getNodesBounds,
  getViewportForBounds,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
  type Edge,
  type NodeMouseHandler,
  type OnNodeDrag,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { toPng } from 'html-to-image'
import { ImageDownIcon, ListIcon, NetworkIcon, XIcon } from 'lucide-react'
import { useSearchParams } from 'react-router'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/features/auth/useAuth'
import { apiClient } from '@/lib/apiClient'
import { getErrorMessage } from '@/lib/apiError'
import { triggerDownload } from '@/lib/download'
import { cn } from '@/lib/utils'
import { AsOfBanner } from './AsOfBanner'
import { AsOfControl } from './AsOfControl'
import { ChartSearch } from './ChartSearch'
import { EmployeeDetailDrawer } from './EmployeeDetailDrawer'
import { EmployeeNode, type EmployeeFlowNode, type EmployeeNodeData } from './EmployeeNode'
import { layoutWithDagre, NODE_HEIGHT, NODE_WIDTH } from './layout'
import { MovePreviewDialog, type PendingMove } from './MovePreviewDialog'
import { OrgChartNestedList } from './OrgChartNestedList'
import { ReassignManagerPalette } from './ReassignManagerPalette'
import { ReportingLineBreadcrumb } from './ReportingLineBreadcrumb'
import { ScheduledChangesPanel } from './ScheduledChangesPanel'
import type { ChartEmployee } from './types'
import { useAsOf } from './useAsOf'
import { useOrgChartData } from './useOrgChartData'

const nodeTypes = { employee: EmployeeNode }
const DEFAULT_FOCUS_DEPTH = 2

function buildEdges(visibleIds: Set<string>, childrenByManager: Map<string, Set<string>>): Edge[] {
  const edges: Edge[] = []
  for (const managerId of visibleIds) {
    for (const childId of childrenByManager.get(managerId) ?? []) {
      if (!visibleIds.has(childId)) continue
      edges.push({
        id: `${managerId}->${childId}`,
        source: managerId,
        target: childId,
        type: 'smoothstep',
      })
    }
  }
  return edges
}

function OrgChartCanvas() {
  const asOfState = useAsOf()
  const { asOf, isToday } = asOfState
  const orgData = useOrgChartData(asOf)
  const { canEdit: canEditRole } = useAuth()
  // Editing what looks like the present while reading the past is the failure
  // mode this whole view invites, so writes are off unless as_of is today.
  const canEdit = canEditRole && isToday
  const { getIntersectingNodes, setCenter, getZoom } = useReactFlow<EmployeeFlowNode>()

  const [viewMode, setViewMode] = useState<'chart' | 'list'>('chart')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [focusDepth, setFocusDepth] = useState(DEFAULT_FOCUS_DEPTH)
  const [paletteEmployeeId, setPaletteEmployeeId] = useState<string | null>(null)
  const [pendingMove, setPendingMove] = useState<PendingMove | null>(null)
  const [draggingId, setDraggingId] = useState<string | null>(null)
  const [pendingCenterId, setPendingCenterId] = useState<string | null>(null)

  const structuralNodes = useMemo<EmployeeFlowNode[]>(() => {
    const loadedVisibleIds = new Set(
      [...orgData.visibleIds].filter((id) => orgData.employeesById.has(id))
    )
    const raw: EmployeeFlowNode[] = [...loadedVisibleIds].map((id) => {
      const employee = orgData.employeesById.get(id)!
      const depth = orgData.depthById.get(id) ?? 0
      const childIds = [...(orgData.childrenByManager.get(id) ?? [])]
      const hasChildren = orgData.hasChildren(id)
      return {
        id,
        type: 'employee',
        position: { x: 0, y: 0 },
        data: {
          employee,
          depth,
          isRoot: depth === 0,
          hasChildren,
          expanded: hasChildren === true && !orgData.collapsedIds.has(id),
          dropValidity: null,
          isDimmed: false,
          childNodeIds: childIds,
          onToggleExpand: orgData.toggleExpanded,
        },
      }
    })
    const edges = buildEdges(loadedVisibleIds, orgData.childrenByManager)
    return layoutWithDagre(raw, edges)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    orgData.visibleIds,
    orgData.employeesById,
    orgData.depthById,
    orgData.childrenByManager,
    orgData.collapsedIds,
  ])

  const structuralEdges = useMemo(
    () => buildEdges(new Set(structuralNodes.map((n) => n.id)), orgData.childrenByManager),
    [structuralNodes, orgData.childrenByManager]
  )

  const [nodes, setNodes, onNodesChange] = useNodesState<EmployeeFlowNode>(structuralNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>(structuralEdges)

  useEffect(() => setNodes(structuralNodes), [structuralNodes, setNodes])
  useEffect(() => setEdges(structuralEdges), [structuralEdges, setEdges])

  const focusSet = useMemo(() => {
    if (!selectedId) return null
    const set = new Set<string>([selectedId])
    for (const id of orgData.getDescendantIds(selectedId, focusDepth)) set.add(id)
    let cursor = orgData.employeesById.get(selectedId)?.manager_id ?? null
    while (cursor) {
      set.add(cursor)
      cursor = orgData.employeesById.get(cursor)?.manager_id ?? null
    }
    return set
  }, [selectedId, focusDepth, orgData])

  const draggedInvalidIds = useMemo(() => {
    if (!draggingId) return null
    return new Set([draggingId, ...orgData.getDescendantIds(draggingId)])
  }, [draggingId, orgData])

  const renderNodes = useMemo(
    () =>
      nodes.map((node) => ({
        ...node,
        selected: node.id === selectedId,
        data: {
          ...node.data,
          dropValidity: draggedInvalidIds
            ? draggedInvalidIds.has(node.id)
              ? ('invalid' as const)
              : ('valid' as const)
            : null,
          isDimmed: focusSet ? !focusSet.has(node.id) : false,
        } satisfies EmployeeNodeData,
      })),
    [nodes, selectedId, draggedInvalidIds, focusSet]
  )

  const centerOnNode = useCallback(
    (id: string) => {
      const node = nodes.find((n) => n.id === id)
      if (!node) {
        setPendingCenterId(id)
        return
      }
      setCenter(node.position.x + NODE_WIDTH / 2, node.position.y + NODE_HEIGHT / 2, {
        zoom: Math.max(getZoom(), 0.75),
        duration: 300,
      })
    },
    [nodes, setCenter, getZoom]
  )

  useEffect(() => {
    if (!pendingCenterId) return
    if (nodes.some((n) => n.id === pendingCenterId)) {
      centerOnNode(pendingCenterId)
      setPendingCenterId(null)
    }
  }, [pendingCenterId, nodes, centerOnNode])

  const selectEmployee = useCallback(
    async (employee: ChartEmployee) => {
      await orgData.focusPathTo(employee)
      setSelectedId(employee.id)
      setViewMode('chart')
      centerOnNode(employee.id)
    },
    [orgData, centerOnNode]
  )

  const [searchParams] = useSearchParams()
  const consumedFocusParam = useRef(false)
  useEffect(() => {
    const focusId = searchParams.get('focus')
    if (!focusId || consumedFocusParam.current) return
    consumedFocusParam.current = true
    void (async () => {
      const { data, error } = await apiClient.GET('/api/v1/employees/{employee_id}', {
        params: { path: { employee_id: focusId } },
      })
      if (error) {
        toast.error('Could not find that employee')
        return
      }
      await selectEmployee(data)
    })()
  }, [searchParams, selectEmployee])

  const handleNodeClick: NodeMouseHandler<EmployeeFlowNode> = useCallback((_event, node) => {
    setSelectedId(node.id)
  }, [])

  const handleNodeDragStart: OnNodeDrag<EmployeeFlowNode> = useCallback((_event, node) => {
    setDraggingId(node.id)
  }, [])

  const handleNodeDragStop: OnNodeDrag<EmployeeFlowNode> = useCallback(
    async (_event, node) => {
      setDraggingId(null)
      const intersecting = getIntersectingNodes(node).filter((n) => n.id !== node.id)
      const targetId = intersecting[0]?.id
      const invalidIds = new Set([node.id, ...orgData.getDescendantIds(node.id)])

      if (!targetId || invalidIds.has(targetId)) {
        setNodes(structuralNodes)
        if (targetId && invalidIds.has(targetId)) {
          toast.error("Can't drop an employee onto their own branch")
        }
        return
      }

      const employee = orgData.employeesById.get(node.id)
      const target = orgData.employeesById.get(targetId)
      if (!employee || !target) {
        setNodes(structuralNodes)
        return
      }

      // Snap the node back and let the preview carry the decision; nothing is
      // written until the move is confirmed in the modal.
      setNodes(structuralNodes)
      setPendingMove({
        employeeId: node.id,
        employeeName: `${employee.first_name} ${employee.last_name}`,
        newManagerId: targetId,
        newManagerName: `${target.first_name} ${target.last_name}`,
      })
    },
    [getIntersectingNodes, orgData, setNodes, structuralNodes]
  )

  const confirmMove = useCallback(
    async ({ effectiveFrom, reason }: { effectiveFrom: string; reason: string }) => {
      if (!pendingMove) return
      try {
        const result = await orgData.reassign({
          employeeId: pendingMove.employeeId,
          newManagerId: pendingMove.newManagerId,
          effectiveFrom,
          reason: reason || undefined,
        })
        setPendingMove(null)
        const cancelled = result?.cancelled.length ?? 0
        const cancelledNote =
          cancelled > 0
            ? ` ${cancelled} scheduled change${cancelled === 1 ? ' was' : 's were'} cancelled.`
            : ''
        if (result?.in_force_now) {
          toast.success(
            `${pendingMove.employeeName} now reports to ${pendingMove.newManagerName}.${cancelledNote}`
          )
        } else {
          toast.success(
            `${pendingMove.employeeName} will report to ${pendingMove.newManagerName} from ${effectiveFrom}.${cancelledNote}`
          )
        }
      } catch (error) {
        toast.error(getErrorMessage(error, 'Failed to reassign manager'))
      }
    },
    [orgData, pendingMove]
  )

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key.toLowerCase() !== 'm' || !selectedId || !canEdit) return
      const target = event.target as HTMLElement | null
      if (target && ['INPUT', 'TEXTAREA'].includes(target.tagName)) return
      event.preventDefault()
      setPaletteEmployeeId(selectedId)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [selectedId, canEdit])

  const paletteEmployee = paletteEmployeeId
    ? (orgData.employeesById.get(paletteEmployeeId) ?? null)
    : null
  const paletteExcludedIds = useMemo(() => {
    if (!paletteEmployeeId) return new Set<string>()
    return new Set([paletteEmployeeId, ...orgData.getDescendantIds(paletteEmployeeId)])
  }, [paletteEmployeeId, orgData])

  const handlePaletteSelect = useCallback(
    (managerId: string | null, managerLabel: string) => {
      if (!paletteEmployeeId) return
      const employee = orgData.employeesById.get(paletteEmployeeId)
      setPaletteEmployeeId(null)
      if (!employee) return
      setPendingMove({
        employeeId: paletteEmployeeId,
        employeeName: `${employee.first_name} ${employee.last_name}`,
        newManagerId: managerId,
        newManagerName: managerLabel,
      })
    },
    [paletteEmployeeId, orgData]
  )

  const selectedEmployee = selectedId ? (orgData.employeesById.get(selectedId) ?? null) : null
  const selectedManager =
    selectedEmployee?.manager_id != null
      ? (orgData.employeesById.get(selectedEmployee.manager_id) ?? null)
      : null
  const selectedManagerName = selectedManager
    ? `${selectedManager.first_name} ${selectedManager.last_name}`
    : null
  const selectedDirectReportCount = selectedId
    ? (orgData.childrenByManager.get(selectedId)?.size ?? 0)
    : 0

  const exitFocus = useCallback(() => setSelectedId(null), [])

  const exportPng = useCallback(async () => {
    if (viewMode !== 'chart') {
      toast.error('Switch to the chart view to export a PNG')
      return
    }
    const viewportEl = document.querySelector<HTMLElement>('.react-flow__viewport')
    if (!viewportEl || nodes.length === 0) return

    const bounds = getNodesBounds(nodes)
    const imageWidth = Math.max(1024, Math.round(bounds.width + 200))
    const imageHeight = Math.max(768, Math.round(bounds.height + 200))
    const viewport = getViewportForBounds(bounds, imageWidth, imageHeight, 0.1, 2, 0.1)

    try {
      const dataUrl = await toPng(viewportEl, {
        backgroundColor: '#ffffff',
        width: imageWidth,
        height: imageHeight,
        style: {
          width: `${imageWidth}px`,
          height: `${imageHeight}px`,
          transform: `translate(${viewport.x}px, ${viewport.y}px) scale(${viewport.zoom})`,
        },
      })
      const blob = await (await fetch(dataUrl)).blob()
      triggerDownload('org-chart.png', blob)
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to export the chart as an image'))
    }
  }, [nodes, viewMode])

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2 print:hidden">
        <div>
          <h1 className="font-display text-2xl font-bold">Org chart</h1>
          <p className="text-muted-foreground">Browse and manage the reporting hierarchy.</p>
        </div>
        <div className="flex items-center gap-2">
          <ChartSearch onSelect={selectEmployee} />
          <Button variant="outline" size="sm" onClick={() => void exportPng()}>
            <ImageDownIcon className="size-4" /> Export PNG
          </Button>
          {selectedId && (
            <Button variant="outline" size="sm" onClick={exitFocus}>
              <XIcon className="size-4" /> Exit focus
            </Button>
          )}
          <div className="flex items-center rounded-md border border-border p-0.5">
            <Button
              variant={viewMode === 'chart' ? 'default' : 'ghost'}
              size="sm"
              aria-pressed={viewMode === 'chart'}
              onClick={() => setViewMode('chart')}
            >
              <NetworkIcon className="size-4" /> Chart
            </Button>
            <Button
              variant={viewMode === 'list' ? 'default' : 'ghost'}
              size="sm"
              aria-pressed={viewMode === 'list'}
              onClick={() => setViewMode('list')}
            >
              <ListIcon className="size-4" /> List
            </Button>
          </div>
        </div>
      </div>

      <AsOfControl state={asOfState} />
      <AsOfBanner state={asOfState} />

      {selectedEmployee && (
        <div className="flex items-center justify-between gap-4 print:hidden">
          <ReportingLineBreadcrumb
            employeeId={selectedEmployee.id}
            employeeName={`${selectedEmployee.first_name} ${selectedEmployee.last_name}`}
            asOf={asOf}
            onSelect={(id) => {
              const ancestor = orgData.employeesById.get(id)
              if (ancestor) void selectEmployee(ancestor)
            }}
          />
          <label className="flex items-center gap-2 text-xs text-muted-foreground">
            Levels below
            <input
              type="number"
              min={0}
              max={6}
              value={focusDepth}
              onChange={(event) => setFocusDepth(Number(event.target.value) || 0)}
              className="w-14 rounded-sm border border-input-border px-1.5 py-0.5"
            />
          </label>
        </div>
      )}

      <div className={cn(viewMode === 'chart' ? 'block' : 'hidden', 'print:hidden')}>
        <div className="h-[70vh] w-full overflow-hidden rounded-md border border-border">
          <ReactFlow
            nodes={renderNodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={handleNodeClick}
            onNodeDragStart={handleNodeDragStart}
            onNodeDragStop={handleNodeDragStop}
            nodesDraggable={canEdit}
            fitView
            minZoom={0.1}
            proOptions={{ hideAttribution: true }}
          >
            <Background />
            <Controls />
            <div aria-hidden="true">
              <MiniMap pannable zoomable />
            </div>
          </ReactFlow>
        </div>
      </div>

      <div className={cn(viewMode === 'list' ? 'block' : 'hidden', 'print:block')}>
        <OrgChartNestedList onSelect={selectEmployee} asOf={asOf} />
      </div>

      <ScheduledChangesPanel state={asOfState} canEdit={canEdit} />

      <EmployeeDetailDrawer
        employee={selectedEmployee}
        managerName={selectedManagerName}
        directReportCount={selectedDirectReportCount}
        asOf={asOf}
        open={Boolean(selectedEmployee)}
        onOpenChange={(open) => !open && setSelectedId(null)}
        onSelectAncestor={(id) => {
          const ancestor = orgData.employeesById.get(id)
          if (ancestor) void selectEmployee(ancestor)
        }}
        canEdit={canEdit}
      />

      <ReassignManagerPalette
        open={Boolean(paletteEmployeeId)}
        onOpenChange={(open) => !open && setPaletteEmployeeId(null)}
        employee={paletteEmployee}
        excludedIds={paletteExcludedIds}
        onSelect={handlePaletteSelect}
      />

      <MovePreviewDialog
        move={pendingMove}
        onOpenChange={(open) => !open && setPendingMove(null)}
        onConfirm={(args) => void confirmMove(args)}
        isSubmitting={orgData.isReassigning}
      />
    </div>
  )
}

export function OrgChartPage() {
  return (
    <ReactFlowProvider>
      <OrgChartCanvas />
    </ReactFlowProvider>
  )
}
