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
import { toBlob } from 'html-to-image'
import { ImageDownIcon, ListIcon, NetworkIcon, XIcon } from 'lucide-react'
import { useSearchParams } from 'react-router'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { useAuth } from '@/features/auth/useAuth'
import { formatDate } from '@/features/employees/format'
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

/** 1x1 transparent PNG, stood in for any avatar the exporter cannot inline. */
const TRANSPARENT_PIXEL =
  'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='

/**
 * Describe a failed export, including the failures that are not Errors.
 *
 * html-to-image rejects with a DOM Event when the image it builds will not
 * load, which carries no message at all - so the generic fallback used to be
 * the only thing this could ever say, however the export failed.
 */
function exportFailureMessage(error: unknown): string {
  if (typeof Event !== 'undefined' && error instanceof Event) {
    return 'The browser could not rasterise the chart. Try collapsing some branches, or use the print view.'
  }
  if (error instanceof Error && error.message) return error.message
  return getErrorMessage(error, 'Try again in a moment.')
}

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
  const canEdit = canEditRole && isToday
  const { getIntersectingNodes, setCenter, getZoom } = useReactFlow<EmployeeFlowNode>()

  const [viewMode, setViewMode] = useState<'chart' | 'list'>('chart')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [focusDepth, setFocusDepth] = useState(DEFAULT_FOCUS_DEPTH)
  const [paletteEmployeeId, setPaletteEmployeeId] = useState<string | null>(null)
  const [pendingMove, setPendingMove] = useState<PendingMove | null>(null)
  const [draggingId, setDraggingId] = useState<string | null>(null)
  const [pendingCenterId, setPendingCenterId] = useState<string | null>(null)
  const [isExportingPng, setIsExportingPng] = useState(false)
  const [focusing, setFocusing] = useState<{ id: string; name: string } | null>(null)

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
          isExpanding: false,
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
    // A selection that no longer resolves - the employee was just deleted -
    // would otherwise dim every remaining node against a focus of one ghost.
    if (!selectedId || !orgData.employeesById.has(selectedId)) return null
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
          isExpanding: orgData.expandingIds.has(node.id),
        } satisfies EmployeeNodeData,
      })),
    [nodes, selectedId, draggedInvalidIds, focusSet, orgData.expandingIds]
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

  const centeredAtRef = useRef<string | null>(null)
  useEffect(() => {
    if (!pendingCenterId) return
    const node = nodes.find((n) => n.id === pendingCenterId)
    if (!node) return
    const position = `${pendingCenterId}@${node.position.x},${node.position.y}`
    // The layout settles over several renders as the pinned ancestors and
    // their branches arrive, so follow the node until it stops moving.
    if (centeredAtRef.current === position) {
      setPendingCenterId(null)
      return
    }
    centeredAtRef.current = position
    centerOnNode(pendingCenterId)
    // The viewport is on its way, so the search is over as far as anyone
    // watching is concerned.
    setFocusing((current) => (current?.id === pendingCenterId ? null : current))
  }, [pendingCenterId, nodes, centerOnNode])

  // A node that never arrives - unreachable, or deleted mid-search - must not
  // leave the pill spinning for good.
  useEffect(() => {
    if (!focusing) return
    const timer = setTimeout(() => setFocusing(null), 8000)
    return () => clearTimeout(timer)
  }, [focusing])

  const selectEmployee = useCallback(
    async (employee: ChartEmployee) => {
      const name = `${employee.first_name} ${employee.last_name}`
      setFocusing({ id: employee.id, name })
      setViewMode('chart')
      try {
        // Their reporting line has to be fetched before the branch can be
        // opened, which is the part worth waiting on.
        await orgData.focusPathTo(employee)
      } catch (error) {
        setFocusing(null)
        toast.error(`Could not open ${name} in the chart`, {
          description: getErrorMessage(error, 'Check your connection and try again.'),
        })
        return
      }
      setSelectedId(employee.id)
      // Deferred rather than centred here: pinning the employee re-runs the
      // layout, so centring now would aim at where the node used to be.
      setPendingCenterId(employee.id)
    },
    [orgData]
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
    setPendingCenterId(null)
  }, [])

  const handleNodeDragStart: OnNodeDrag<EmployeeFlowNode> = useCallback((_event, node) => {
    setDraggingId(node.id)
    setPendingCenterId(null)
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

      if (employee.manager_id === targetId) {
        setNodes(structuralNodes)
        toast.info(
          `${employee.first_name} ${employee.last_name} already reports to ${target.first_name} ${target.last_name}`
        )
        return
      }

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
          toast.success('Reporting line updated', {
            description: `${pendingMove.employeeName} now reports to ${pendingMove.newManagerName}.${cancelledNote}`,
          })
        } else {
          toast.success('Move scheduled', {
            description: `${pendingMove.employeeName} will report to ${pendingMove.newManagerName} from ${effectiveFrom}.${cancelledNote}`,
          })
        }
      } catch (error) {
        toast.error('Could not reassign this employee', {
          description: getErrorMessage(error, 'The reporting line is unchanged. Try again in a moment.'),
        })
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
    setIsExportingPng(true)

    const bounds = getNodesBounds(nodes)
    const imageWidth = Math.max(1024, Math.round(bounds.width + 200))
    const imageHeight = Math.max(768, Math.round(bounds.height + 200))
    const viewport = getViewportForBounds(bounds, imageWidth, imageHeight, 0.1, 2, 0.1)

    try {
      // toBlob, not toPng: toPng hands back a data: URL, and turning that into
      // a Blob meant fetch()ing it - which connect-src forbids, since a data:
      // URL is an origin of its own. toBlob goes through canvas.toBlob and
      // never touches the network.
      const blob = await toBlob(viewportEl, {
        backgroundColor: '#ffffff',
        width: imageWidth,
        height: imageHeight,
        // An avatar the exporter cannot inline is left blank rather than
        // failing the whole export. Gravatar is reachable (see the API's
        // connect-src), but avatar_override_url accepts any host, and one
        // unreachable picture should not cost the chart.
        imagePlaceholder: TRANSPARENT_PIXEL,
        style: {
          width: `${imageWidth}px`,
          height: `${imageHeight}px`,
          transform: `translate(${viewport.x}px, ${viewport.y}px) scale(${viewport.zoom})`,
        },
      })
      if (!blob) throw new Error('The browser produced an empty image.')
      triggerDownload('org-chart.png', blob)
      toast.success('Chart exported', {
        description: 'org-chart.png has been downloaded.',
      })
    } catch (error) {
      toast.error('Could not export the chart', {
        description: exportFailureMessage(error),
      })
    } finally {
      setIsExportingPng(false)
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
          <Button
            variant="outline"
            size="sm"
            disabled={isExportingPng}
            onClick={() => void exportPng()}
          >
            {isExportingPng ? <Spinner className="size-4" /> : <ImageDownIcon className="size-4" />}
            {isExportingPng ? 'Exporting...' : 'Export PNG'}
          </Button>
          {selectedEmployee && (
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

      <ScheduledChangesPanel state={asOfState} canEdit={canEdit} />
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
        <div className="relative h-[70vh] w-full overflow-hidden rounded-md border border-border">
          {focusing && !orgData.isLoading && (
            <div
              role="status"
              className="absolute top-2 left-2 z-10 inline-flex items-center gap-2 rounded-md border border-border bg-card px-3 py-2 text-xs text-foreground shadow-sm"
            >
              <Spinner className="size-4 text-brand-steel" /> Finding {focusing.name} in the
              chart...
            </div>
          )}

          {orgData.isLoading && (
            <div
              role="status"
              className="absolute inset-0 z-10 grid place-items-center bg-card/80"
            >
              <span className="flex items-center gap-2 text-sm text-muted-foreground">
                <Spinner /> Loading the chart as at {formatDate(asOf)}...
              </span>
            </div>
          )}

          {!orgData.isLoading && orgData.isError && (
            <div role="alert" className="absolute inset-0 z-10 grid place-items-center bg-card/80">
              <span className="flex max-w-md flex-col items-center gap-1 px-6 text-center">
                <span className="text-sm font-semibold text-status-critical">
                  Could not load the chart
                </span>
                <span className="text-xs text-muted-foreground">
                  The organisation as at {formatDate(asOf)} could not be read. Check your
                  connection and try again.
                </span>
              </span>
            </div>
          )}

          {!orgData.isLoading && !orgData.isError && renderNodes.length === 0 && (
            <div role="status" className="absolute inset-0 z-10 grid place-items-center bg-card/80">
              <span className="flex max-w-md flex-col items-center gap-1 px-6 text-center">
                <span className="text-sm font-semibold text-foreground">
                  Nobody to show as at {formatDate(asOf)}
                </span>
                <span className="text-xs text-muted-foreground">
                  No reporting lines were in force on that date. Try a later date, or return to
                  today.
                </span>
              </span>
            </div>
          )}

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
