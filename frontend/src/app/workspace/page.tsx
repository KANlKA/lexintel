'use client'

import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import {
  analyzeEvents,
  deleteWorkspace,
  getContradictions,
  getSummary,
  getTimeline,
  getWeaknesses,
  getWorkspaceAnalysis,
  getWorkspaces,
  saveWorkspace,
  saveWorkspaceAnalysis,
  uploadCaseFiles,
  type AnalyzeResponse,
  type CaseWorkspace,
  type Contradiction,
  type Summary,
  type TimelineEvent,
  type Weakness,
  type WorkspaceAnalysis,
} from '@/lib/api'
import clsx from 'clsx'
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  Clock,
  Database,
  FileText,
  FolderOpen,
  Gavel,
  GitBranch,
  Image,
  MapPin,
  Play,
  Plus,
  RotateCcw,
  Send,
  Shield,
  Trash2,
  Upload,
  User,
  X,
  Zap,
} from 'lucide-react'

const DOC_TYPES = ['FIR', 'Witness Statement', 'Medical Report', 'Charge Sheet', 'Court Order', 'Evidence', 'Other']

type Stage = 'list' | 'detail'
type WorkspaceTab = 'dashboard' | 'timeline' | 'contradictions' | 'weaknesses' | 'simulation'
type SimulationRole = 'judge' | 'opponent' | 'lawyer'
type SimulationMode = 'judge' | 'opponent'
type SimulationSide = 'defense' | 'prosecution'

interface UploadedFile {
  file: File
  docType: string
  id: string
}

interface SimulationMessage {
  role: SimulationRole
  content: string
  timestamp: string
}

interface WorkspaceDetailState {
  workspace: CaseWorkspace
  summary: Summary | null
  timeline: TimelineEvent[]
  contradictions: Contradiction[]
  weaknesses: Weakness[]
}

const EMPTY_DETAIL: WorkspaceDetailState = {
  workspace: {
    id: '',
    name: '',
    files: [],
    createdAt: '',
    analyzed: false,
    eventCount: 0,
  },
  summary: null,
  timeline: [],
  contradictions: [],
  weaknesses: [],
}

const tabs: Array<{ id: WorkspaceTab; label: string; icon: ReactNode }> = [
  { id: 'dashboard', label: 'Dashboard', icon: <Activity size={14} /> },
  { id: 'timeline', label: 'Timeline', icon: <Clock size={14} /> },
  { id: 'contradictions', label: 'Contradictions', icon: <AlertTriangle size={14} /> },
  { id: 'weaknesses', label: 'Weaknesses', icon: <Shield size={14} /> },
  { id: 'simulation', label: 'Simulation', icon: <Gavel size={14} /> },
]

export default function WorkspacePage() {
  const [stage, setStage] = useState<Stage>('list')
  const [workspaces, setWorkspaces] = useState<CaseWorkspace[]>([])
  const [detail, setDetail] = useState<WorkspaceDetailState>(EMPTY_DETAIL)
  const [files, setFiles] = useState<UploadedFile[]>([])
  const [dragging, setDragging] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [progress, setProgress] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [currentTab, setCurrentTab] = useState<WorkspaceTab>('dashboard')
  const [mode, setMode] = useState<SimulationMode>('opponent')
  const [side, setSide] = useState<SimulationSide>('defense')
  const [messages, setMessages] = useState<SimulationMessage[]>([])
  const [input, setInput] = useState('')
  const [simulationLoading, setSimulationLoading] = useState(false)
  const [simulationStarted, setSimulationStarted] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setWorkspaces(getWorkspaces())
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const currentWorkspace = detail.workspace.id ? detail.workspace : null
  const hasAnalysis = Boolean(detail.summary)

  const timelineStats = useMemo(() => {
    const timed = detail.timeline.filter((event) => !event.time_uncertain).length
    const uncertain = detail.timeline.filter((event) => event.time_uncertain).length
    return { timed, uncertain }
  }, [detail.timeline])

  const contradictionStats = useMemo(() => ({
    critical: detail.contradictions.filter((item) => item.severity === 'critical').length,
    moderate: detail.contradictions.filter((item) => item.severity === 'moderate').length,
    minor: detail.contradictions.filter((item) => item.severity === 'minor').length,
  }), [detail.contradictions])

  const weaknessStats = useMemo(() => ({
    high: detail.weaknesses.filter((item) => item.severity === 'high').length,
    medium: detail.weaknesses.filter((item) => item.severity === 'medium').length,
    low: detail.weaknesses.filter((item) => item.severity === 'low').length,
  }), [detail.weaknesses])

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragging(true)
  }, [])

  const onDragLeave = useCallback(() => setDragging(false), [])

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    addFiles(Array.from(e.dataTransfer.files))
  }, [])

  function guessDocType(name: string): string {
    const normalized = name.toLowerCase()
    if (normalized.includes('fir')) return 'FIR'
    if (normalized.includes('witness')) return 'Witness Statement'
    if (normalized.includes('medical')) return 'Medical Report'
    if (normalized.includes('charge')) return 'Charge Sheet'
    if (normalized.includes('order') || normalized.includes('court')) return 'Court Order'
    if (normalized.includes('evidence')) return 'Evidence'
    return 'Other'
  }

  function addFiles(incoming: File[]) {
    const allowed = incoming.filter((file) =>
      ['.pdf', '.png', '.jpg', '.jpeg', '.txt'].some((ext) => file.name.toLowerCase().endsWith(ext)),
    )
    const mapped: UploadedFile[] = allowed.map((file) => ({
      file,
      docType: guessDocType(file.name),
      id: crypto.randomUUID(),
    }))
    setFiles((prev) => [...prev, ...mapped])
  }

  function removeFile(id: string) {
    setFiles((prev) => prev.filter((item) => item.id !== id))
  }

  function updateDocType(id: string, docType: string) {
    setFiles((prev) => prev.map((item) => (item.id === id ? { ...item, docType } : item)))
  }

  function refreshWorkspaceList() {
    setWorkspaces(getWorkspaces())
  }

  function createWorkspace() {
    setError(null)
    setNotice(null)
    setFiles([])
    setMessages([])
    setSimulationStarted(false)
    setProgress([])
    setCurrentTab('dashboard')
    setDetail({
      workspace: {
        id: crypto.randomUUID(),
        name: '',
        files: [],
        createdAt: new Date().toISOString(),
        analyzed: false,
        eventCount: 0,
      },
      summary: null,
      timeline: [],
      contradictions: [],
      weaknesses: [],
    })
    setStage('detail')
  }

  function openWorkspace(workspace: CaseWorkspace) {
    const storedAnalysis = getWorkspaceAnalysis(workspace.id)
    setError(null)
    setNotice(null)
    setFiles([])
    setProgress([])
    setMessages([])
    setSimulationStarted(false)
    setCurrentTab('dashboard')
    setDetail({
      workspace,
      summary: storedAnalysis?.summary ?? null,
      timeline: storedAnalysis?.timeline ?? [],
      contradictions: storedAnalysis?.contradictions ?? [],
      weaknesses: storedAnalysis?.weaknesses ?? [],
    })
    setStage('detail')
  }

  function persistWorkspace(nextWorkspace: CaseWorkspace) {
    saveWorkspace(nextWorkspace)
    setDetail((prev) => ({ ...prev, workspace: nextWorkspace }))
    refreshWorkspaceList()
  }

  function saveCurrentWorkspace() {
    if (!currentWorkspace) return

    const trimmedName = detail.workspace.name.trim()
    if (!trimmedName) {
      setError('Please give this workspace a case name before saving.')
      return
    }

    const pendingFiles = files.map((item) => `${item.docType}: ${item.file.name}`)
    const mergedFiles = Array.from(new Set([
      ...detail.workspace.files,
      ...pendingFiles,
    ]))

    const nextWorkspace: CaseWorkspace = {
      ...detail.workspace,
      name: trimmedName,
      files: mergedFiles,
      analyzed: detail.workspace.analyzed,
      eventCount: detail.workspace.eventCount,
      lastAnalyzedAt: detail.workspace.lastAnalyzedAt,
    }
    persistWorkspace(nextWorkspace)
    setError(null)
    setNotice(
      pendingFiles.length > 0
        ? 'Workspace saved. Document names were saved with it.'
        : 'Workspace saved.',
    )
  }

  async function fetchAnalysisSnapshot(): Promise<WorkspaceAnalysis> {
    const [summary, timeline, contradictions, weaknesses] = await Promise.all([
      getSummary(),
      getTimeline(),
      getContradictions(),
      getWeaknesses(),
    ])

    return {
      summary,
      timeline,
      contradictions,
      weaknesses,
      updatedAt: new Date().toISOString(),
    }
  }

  async function runAnalysis() {
    if (!currentWorkspace) return

    const trimmedName = detail.workspace.name.trim()
    if (!trimmedName) {
      setError('Please enter a workspace name before analyzing.')
      return
    }
    if (files.length === 0) {
      setError('Upload at least one document to analyze this workspace.')
      return
    }

    setError(null)
    setNotice(null)
    setAnalyzing(true)
    setProgress([])

    const log = (line: string) => setProgress((prev) => [...prev, line])

    try {
      log(`Workspace ready: ${trimmedName}`)
      log(`Queued ${files.length} document(s) for case analysis`)
      log('Uploading documents to the pipeline...')
      const extracted = await uploadCaseFiles(files.map((item) => item.file))
      log(`Extracted ${extracted.events_extracted} event(s) from uploaded documents`)

      if (extracted.events_extracted === 0) {
        throw new Error('No events could be extracted from the uploaded documents.')
      }

      log('Running reasoning on extracted events...')
      const analysis: AnalyzeResponse = await analyzeEvents(extracted.events)
      log(`Built graph with ${analysis.graph.nodes} nodes and ${analysis.graph.edges} edges`)
      log(`Detected ${analysis.contradictions_found} contradiction(s)`)
      log(`Scored ${analysis.weaknesses_scored} weakness record(s)`)

      log('Loading workspace views...')
      const snapshot = await fetchAnalysisSnapshot()

      const mergedFiles = Array.from(new Set([
        ...detail.workspace.files,
        ...files.map((item) => `${item.docType}: ${item.file.name}`),
      ]))

      const nextWorkspace: CaseWorkspace = {
        ...detail.workspace,
        name: trimmedName,
        files: mergedFiles,
        analyzed: true,
        eventCount: snapshot.summary.events_total,
        lastAnalyzedAt: snapshot.updatedAt,
      }

      saveWorkspace(nextWorkspace)
      saveWorkspaceAnalysis(nextWorkspace.id, snapshot)

      setDetail({
        workspace: nextWorkspace,
        summary: snapshot.summary,
        timeline: snapshot.timeline,
        contradictions: snapshot.contradictions,
        weaknesses: snapshot.weaknesses,
      })
      setFiles([])
      setCurrentTab('dashboard')
      setMessages([])
      setSimulationStarted(false)
      refreshWorkspaceList()
      setNotice('Workspace analysis is complete and saved.')
      log('Workspace analysis is ready below.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed.')
    } finally {
      setAnalyzing(false)
    }
  }

  function removeWorkspace(id: string) {
    deleteWorkspace(id)
    refreshWorkspaceList()
    if (currentWorkspace?.id === id) {
      setDetail(EMPTY_DETAIL)
      setStage('list')
    }
  }

  async function startSimulation() {
    setSimulationStarted(true)
    setMessages([])
    setSimulationLoading(true)

    try {
      const res = await fetch('/api/simulation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode,
          side,
          weaknesses: detail.weaknesses,
          contradictions: detail.contradictions,
          messages: [{ role: 'lawyer', content: 'Begin the hearing. Ask your first question.' }],
        }),
      })
      if (!res.ok) {
        throw new Error('Simulation request failed')
      }
      const data = (await res.json()) as { text: string }
      setMessages([{
        role: mode,
        content: data.text,
        timestamp: new Date().toLocaleTimeString(),
      }])
    } catch {
      setMessages([{
        role: mode,
        content: 'Simulation service is unavailable.',
        timestamp: new Date().toLocaleTimeString(),
      }])
    } finally {
      setSimulationLoading(false)
    }
  }

  async function sendSimulationMessage() {
    if (!input.trim() || simulationLoading) return

    const userMessage: SimulationMessage = {
      role: 'lawyer',
      content: input,
      timestamp: new Date().toLocaleTimeString(),
    }
    const nextMessages = [...messages, userMessage]
    setMessages(nextMessages)
    setInput('')
    setSimulationLoading(true)

    try {
      const res = await fetch('/api/simulation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode,
          side,
          weaknesses: detail.weaknesses,
          contradictions: detail.contradictions,
          messages: nextMessages.map(({ role, content }) => ({ role, content })),
        }),
      })
      if (!res.ok) {
        throw new Error('Simulation request failed')
      }
      const data = (await res.json()) as { text: string }
      setMessages((prev) => [...prev, {
        role: mode,
        content: data.text,
        timestamp: new Date().toLocaleTimeString(),
      }])
    } catch {
      setMessages((prev) => [...prev, {
        role: mode,
        content: 'Simulation service is unavailable.',
        timestamp: new Date().toLocaleTimeString(),
      }])
    } finally {
      setSimulationLoading(false)
    }
  }

  function resetSimulation() {
    setSimulationStarted(false)
    setMessages([])
    setInput('')
  }

  return (
    <div className="min-h-screen p-8" style={{ background: '#0A0A0F' }}>
      <div className="mb-8 fade-up">
        <div className="text-xs tracking-widest uppercase mb-2" style={{ color: '#C9A84C', fontFamily: 'var(--font-mono)' }}>
          Workspace Hub
        </div>
        <h1 className="text-4xl font-semibold mb-2" style={{ fontFamily: 'var(--font-display)', color: '#E8E8F0' }}>
          Case Workspace
        </h1>
        <p style={{ color: '#6B6B80' }}>
          Create a workspace, upload multiple case documents, and review the full analysis without leaving this page.
        </p>
      </div>

      {stage === 'list' && (
        <div className="space-y-8 fade-up">
          <div className="flex items-center justify-between gap-4 rounded-lg p-6" style={{ background: '#111118', border: '1px solid #1E1E2A' }}>
            <div>
              <div className="text-lg font-medium mb-1" style={{ color: '#E8E8F0' }}>Everything starts here</div>
              <p className="text-sm" style={{ color: '#6B6B80' }}>
                Spin up a workspace, name the matter, upload documents, and review dashboard, timeline, contradictions, weaknesses, and simulation in one flow.
              </p>
            </div>
            <button
              onClick={createWorkspace}
              className="flex items-center gap-2 px-5 py-2.5 rounded text-sm transition-all"
              style={{
                background: 'rgba(201,168,76,0.1)',
                border: '1px solid rgba(201,168,76,0.35)',
                color: '#C9A84C',
              }}
            >
              <Plus size={14} />
              Create Workspace
            </button>
          </div>

          {workspaces.length === 0 ? (
            <div className="py-20 text-center rounded-lg" style={{ border: '1px dashed #2A2A38', background: '#111118' }}>
              <FolderOpen size={34} className="mx-auto mb-4" style={{ color: '#3A3A4A' }} />
              <div className="text-lg mb-1" style={{ color: '#E8E8F0' }}>No workspaces yet</div>
              <p style={{ color: '#6B6B80' }}>Create your first workspace to begin organizing and analyzing case documents.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
              {workspaces.map((workspace, index) => (
                <div
                  key={workspace.id}
                  className="rounded-lg p-5 fade-up"
                  style={{
                    animationDelay: `${index * 0.04}s`,
                    background: '#111118',
                    border: '1px solid #1E1E2A',
                  }}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <FolderOpen size={15} style={{ color: '#C9A84C' }} />
                        <div className="font-medium truncate" style={{ color: '#E8E8F0' }}>{workspace.name || 'Untitled workspace'}</div>
                        {workspace.analyzed && (
                          <span className="text-xs px-2 py-0.5 rounded" style={{ background: 'rgba(76,175,124,0.15)', color: '#4CAF7C' }}>
                            analyzed
                          </span>
                        )}
                      </div>
                      <div className="text-xs mb-3" style={{ color: '#6B6B80' }}>
                        {workspace.eventCount} events · {workspace.files.length} document(s)
                        {workspace.lastAnalyzedAt ? ` · Updated ${new Date(workspace.lastAnalyzedAt).toLocaleString()}` : ''}
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {workspace.files.slice(0, 4).map((file) => (
                          <span
                            key={file}
                            className="text-xs px-2 py-1 rounded"
                            style={{ background: '#1A1A25', color: '#A8A8B8' }}
                          >
                            {file}
                          </span>
                        ))}
                        {workspace.files.length > 4 && (
                          <span className="text-xs px-2 py-1 rounded" style={{ background: '#1A1A25', color: '#6B6B80' }}>
                            +{workspace.files.length - 4} more
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => openWorkspace(workspace)}
                        className="flex items-center gap-1 text-xs px-3 py-1.5 rounded transition-all"
                        style={{
                          background: 'rgba(201,168,76,0.08)',
                          border: '1px solid rgba(201,168,76,0.2)',
                          color: '#C9A84C',
                        }}
                      >
                        Open <ChevronRight size={12} />
                      </button>
                      <button
                        onClick={() => removeWorkspace(workspace.id)}
                        className="p-1.5 rounded transition-all"
                        style={{
                          background: 'transparent',
                          border: '1px solid #2A2A38',
                          color: '#6B6B80',
                        }}
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {stage === 'detail' && currentWorkspace && (
        <div className="space-y-6 fade-up">
          <div className="flex items-center justify-between gap-4">
            <button
              onClick={() => {
                refreshWorkspaceList()
                setStage('list')
              }}
              className="text-xs transition-all"
              style={{ color: '#6B6B80' }}
            >
              ← Back to workspace list
            </button>
            <div className="flex items-center gap-2">
              <button
                onClick={saveCurrentWorkspace}
                className="px-4 py-2 rounded text-xs uppercase tracking-widest"
                style={{
                  background: 'transparent',
                  border: '1px solid #2A2A38',
                  color: '#A8A8B8',
                  fontFamily: 'var(--font-mono)',
                }}
              >
                Save Workspace
              </button>
              <button
                onClick={createWorkspace}
                className="px-4 py-2 rounded text-xs uppercase tracking-widest"
                style={{
                  background: 'rgba(201,168,76,0.1)',
                  border: '1px solid rgba(201,168,76,0.35)',
                  color: '#C9A84C',
                  fontFamily: 'var(--font-mono)',
                }}
              >
                New Workspace
              </button>
            </div>
          </div>

          <div className="grid gap-6 xl:grid-cols-[420px_minmax(0,1fr)]">
            <section className="space-y-6">
              <div className="rounded-lg p-6" style={{ background: '#111118', border: '1px solid #1E1E2A' }}>
                <div className="text-xs tracking-widest uppercase mb-2" style={{ color: '#6B6B80', fontFamily: 'var(--font-mono)' }}>
                  Workspace Setup
                </div>
                <label className="text-xs uppercase tracking-widest block mb-2" style={{ color: '#6B6B80', fontFamily: 'var(--font-mono)' }}>
                  Workspace Name
                </label>
                <input
                  value={detail.workspace.name}
                  onChange={(e) => setDetail((prev) => ({
                    ...prev,
                    workspace: { ...prev.workspace, name: e.target.value },
                  }))}
                  placeholder="e.g. State v. Johnson — Burglary 2024"
                  className="w-full px-4 py-3 rounded text-sm outline-none mb-4"
                  style={{
                    background: '#0D0D14',
                    border: '1px solid #2A2A38',
                    color: '#E8E8F0',
                  }}
                />
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <WorkspaceMeta label="Created" value={new Date(detail.workspace.createdAt).toLocaleDateString()} />
                  <WorkspaceMeta label="Documents" value={String(detail.workspace.files.length + files.length)} />
                  <WorkspaceMeta label="Events" value={String(detail.workspace.eventCount)} />
                  <WorkspaceMeta label="Status" value={detail.workspace.analyzed ? 'Analyzed' : 'Draft'} />
                </div>
              </div>

              <div className="rounded-lg p-6" style={{ background: '#111118', border: '1px solid #1E1E2A' }}>
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <div className="text-xs tracking-widest uppercase mb-1" style={{ color: '#6B6B80', fontFamily: 'var(--font-mono)' }}>
                      Document Intake
                    </div>
                    <p className="text-sm" style={{ color: '#A8A8B8' }}>
                      Upload multiple files. PDFs, images, and text files will be analyzed together as one case.
                    </p>
                  </div>
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="px-3 py-2 rounded text-xs uppercase tracking-widest"
                    style={{
                      background: 'transparent',
                      border: '1px solid #2A2A38',
                      color: '#A8A8B8',
                      fontFamily: 'var(--font-mono)',
                    }}
                  >
                    Browse
                  </button>
                </div>

                <div
                  onDragOver={onDragOver}
                  onDragLeave={onDragLeave}
                  onDrop={onDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className="rounded-lg p-10 text-center mb-4 cursor-pointer transition-all"
                  style={{
                    border: `2px dashed ${dragging ? '#C9A84C' : '#2A2A38'}`,
                    background: dragging ? 'rgba(201,168,76,0.04)' : '#0D0D14',
                  }}
                >
                  <Upload size={28} className="mx-auto mb-3" style={{ color: dragging ? '#C9A84C' : '#3A3A4A' }} />
                  <p className="text-sm mb-1" style={{ color: dragging ? '#C9A84C' : '#6B6B80' }}>
                    {dragging ? 'Drop files here' : 'Drag and drop case documents'}
                  </p>
                  <p className="text-xs" style={{ color: '#3A3A4A' }}>
                    PDF · PNG · JPG · TXT · multi-upload supported
                  </p>
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    accept=".pdf,.png,.jpg,.jpeg,.txt"
                    className="hidden"
                    onChange={(e) => addFiles(Array.from(e.target.files || []))}
                  />
                </div>

                {detail.workspace.files.length > 0 && (
                  <div className="mb-4">
                    <div className="text-xs uppercase tracking-widest mb-2" style={{ color: '#6B6B80', fontFamily: 'var(--font-mono)' }}>
                      Saved Documents
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {detail.workspace.files.map((file) => (
                        <span key={file} className="text-xs px-2 py-1 rounded" style={{ background: '#1A1A25', color: '#A8A8B8' }}>
                          {file}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {files.length > 0 && (
                  <div className="space-y-2 mb-4">
                    <div className="text-xs uppercase tracking-widest mb-2" style={{ color: '#6B6B80', fontFamily: 'var(--font-mono)' }}>
                      Ready To Analyze
                    </div>
                    {files.map((item) => (
                      <div
                        key={item.id}
                        className="flex items-center gap-3 p-3 rounded-lg"
                        style={{ background: '#0D0D14', border: '1px solid #1E1E2A' }}
                      >
                        <div style={{ color: '#C9A84C', flexShrink: 0 }}>
                          {item.file.name.match(/\.(png|jpg|jpeg)$/i) ? <Image size={14} /> : <FileText size={14} />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm truncate" style={{ color: '#E8E8F0' }}>{item.file.name}</div>
                          <div className="text-xs" style={{ color: '#6B6B80' }}>
                            {(item.file.size / 1024).toFixed(1)} KB
                          </div>
                        </div>
                        <select
                          value={item.docType}
                          onChange={(e) => updateDocType(item.id, e.target.value)}
                          className="text-xs px-2 py-1 rounded outline-none"
                          style={{
                            background: '#1E1E2A',
                            border: '1px solid #2A2A38',
                            color: '#A8A8B8',
                          }}
                        >
                          {DOC_TYPES.map((type) => (
                            <option key={type} value={type}>{type}</option>
                          ))}
                        </select>
                        <button
                          onClick={() => removeFile(item.id)}
                          style={{ background: 'none', border: 'none', color: '#6B6B80' }}
                        >
                          <X size={14} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                {error && (
                  <div className="flex items-center gap-2 p-3 rounded mb-4" style={{ background: 'rgba(224,82,82,0.08)', border: '1px solid rgba(224,82,82,0.2)' }}>
                    <AlertCircle size={14} style={{ color: '#E05252' }} />
                    <span className="text-sm" style={{ color: '#E05252' }}>{error}</span>
                  </div>
                )}

                {notice && (
                  <div className="flex items-center gap-2 p-3 rounded mb-4" style={{ background: 'rgba(76,175,124,0.08)', border: '1px solid rgba(76,175,124,0.2)' }}>
                    <FolderOpen size={14} style={{ color: '#4CAF7C' }} />
                    <span className="text-sm" style={{ color: '#4CAF7C' }}>{notice}</span>
                  </div>
                )}

                <button
                  onClick={runAnalysis}
                  disabled={analyzing || files.length === 0}
                  className="w-full py-3 rounded font-medium text-sm transition-all flex items-center justify-center gap-2"
                  style={{
                    background: files.length === 0 ? 'transparent' : 'rgba(201,168,76,0.12)',
                    border: `1px solid ${files.length === 0 ? '#2A2A38' : 'rgba(201,168,76,0.4)'}`,
                    color: files.length === 0 ? '#6B6B80' : '#C9A84C',
                  }}
                >
                  {analyzing ? <RotateCcw size={14} className="animate-spin" /> : <Play size={14} />}
                  {analyzing ? 'Analyzing Workspace...' : 'Analyze Documents'}
                </button>

                {progress.length > 0 && (
                  <div className="mt-4 rounded-lg p-4" style={{ background: '#0D0D14', border: '1px solid #1E1E2A' }}>
                    <div className="text-xs uppercase tracking-widest mb-3" style={{ color: '#6B6B80', fontFamily: 'var(--font-mono)' }}>
                      Analysis Log
                    </div>
                    <div className="space-y-1.5">
                      {progress.map((line, index) => (
                        <div
                          key={`${line}-${index}`}
                          className="text-xs"
                          style={{
                            color: line.includes('ready') ? '#4CAF7C' : line.includes('Uploading') || line.includes('Running') ? '#C9A84C' : '#A8A8B8',
                            fontFamily: 'var(--font-mono)',
                          }}
                        >
                          {line}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </section>

            <section className="space-y-6">
              {hasAnalysis ? (
                <>
                  <div className="rounded-lg p-3" style={{ background: '#111118', border: '1px solid #1E1E2A' }}>
                    <div className="flex flex-wrap gap-2">
                      {tabs.map((tab) => (
                        <button
                          key={tab.id}
                          onClick={() => setCurrentTab(tab.id)}
                          className={clsx('flex items-center gap-2 px-4 py-2 rounded text-xs uppercase tracking-widest transition-all')}
                          style={{
                            fontFamily: 'var(--font-mono)',
                            background: currentTab === tab.id ? 'rgba(201,168,76,0.12)' : 'transparent',
                            border: `1px solid ${currentTab === tab.id ? 'rgba(201,168,76,0.4)' : '#2A2A38'}`,
                            color: currentTab === tab.id ? '#C9A84C' : '#6B6B80',
                          }}
                        >
                          {tab.icon}
                          {tab.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {currentTab === 'dashboard' && detail.summary && (
                    <div className="space-y-6">
                      <div className="rounded-lg p-6" style={{ background: '#111118', border: '1px solid #1E1E2A' }}>
                        <div className="text-xs tracking-widest uppercase mb-2" style={{ color: '#C9A84C', fontFamily: 'var(--font-mono)' }}>
                          Workspace Dashboard
                        </div>
                        <h2 className="text-3xl font-semibold mb-2" style={{ fontFamily: 'var(--font-display)', color: '#E8E8F0' }}>
                          {detail.workspace.name || 'Untitled workspace'}
                        </h2>
                        <p style={{ color: '#6B6B80' }}>
                          Review the current analysis across the same workspace you used for document upload.
                        </p>
                      </div>

                      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 2xl:grid-cols-3">
                        <StatCard icon={<Database size={18} />} label="Total Events" value={detail.summary.events_total} sub={`${detail.summary.timed_events} timed · ${detail.summary.uncertain_events} uncertain`} accent="#C9A84C" />
                        <StatCard icon={<AlertTriangle size={18} />} label="Contradictions" value={detail.summary.contradictions_total} sub={`${detail.summary.critical_contradictions} critical`} accent="#E05252" />
                        <StatCard icon={<Shield size={18} />} label="High Risk Events" value={detail.summary.high_weakness_events} sub={`${detail.summary.medium_weakness_events} medium · ${detail.summary.low_weakness_events} low`} accent="#D4882A" />
                        <StatCard icon={<GitBranch size={18} />} label="Event Graph" value={detail.summary.graph?.nodes ?? 0} sub={`${detail.summary.graph?.edges ?? 0} relationships`} accent="#4CAF7C" />
                        <StatCard icon={<Clock size={18} />} label="Timeline Coverage" value={timelineStats.timed} sub={`${timelineStats.uncertain} uncertain events`} accent="#6B8FD4" />
                        <StatCard icon={<Zap size={18} />} label="Coverage" value={`${detail.summary.events_total > 0 ? Math.round((detail.summary.timed_events / detail.summary.events_total) * 100) : 0}%`} sub="events with known time" accent="#A084D4" />
                      </div>

                      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                        <QuickPanel title="Timeline" desc={`${detail.timeline.length} ordered events ready to inspect`} color="#6B8FD4" />
                        <QuickPanel title="Contradictions" desc={`${contradictionStats.critical} critical conflicts need attention`} color="#E05252" />
                        <QuickPanel title="Weaknesses" desc={`${weaknessStats.high} high-risk events are driving simulation pressure`} color="#D4882A" />
                        <QuickPanel title="Simulation" desc="Use the loaded weaknesses and contradictions to rehearse your argument" color="#C9A84C" />
                      </div>
                    </div>
                  )}

                  {currentTab === 'timeline' && (
                    <div className="space-y-6">
                      <div className="rounded-lg p-6" style={{ background: '#111118', border: '1px solid #1E1E2A' }}>
                        <div className="text-xs tracking-widest uppercase mb-2" style={{ color: '#6B8FD4', fontFamily: 'var(--font-mono)' }}>
                          Timeline
                        </div>
                        <h2 className="text-3xl font-semibold mb-2" style={{ fontFamily: 'var(--font-display)', color: '#E8E8F0' }}>
                          Event Sequence
                        </h2>
                        <p style={{ color: '#6B6B80' }}>
                          Chronological reconstruction of all extracted events in this workspace.
                        </p>
                      </div>
                      <div className="relative">
                        <div className="absolute left-[19px] top-0 bottom-0 w-px" style={{ background: 'linear-gradient(to bottom, #C9A84C, #2A2A38 80%)' }} />
                        <div className="space-y-1">
                          {detail.timeline.map((event, index) => (
                            <TimelineNode key={event.event_id} event={event} index={index} />
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  {currentTab === 'contradictions' && (
                    <div className="space-y-6">
                      <div className="flex gap-4 mb-2">
                        <SeverityBadge count={contradictionStats.critical} label="Critical" color="#E05252" bg="rgba(224,82,82,0.1)" />
                        <SeverityBadge count={contradictionStats.moderate} label="Moderate" color="#D4882A" bg="rgba(212,136,42,0.1)" />
                        <SeverityBadge count={contradictionStats.minor} label="Minor" color="#4CAF7C" bg="rgba(76,175,124,0.1)" />
                      </div>
                      <div className="space-y-3">
                        {detail.contradictions.map((item, index) => (
                          <ContradictionCard key={`${item.event1_id}-${item.event2_id}-${index}`} contradiction={item} index={index} />
                        ))}
                      </div>
                    </div>
                  )}

                  {currentTab === 'weaknesses' && (
                    <div className="space-y-2">
                      {detail.weaknesses.map((item, index) => (
                        <WeaknessRow key={`${item.event_id}-${index}`} weakness={item} index={index} />
                      ))}
                    </div>
                  )}

                  {currentTab === 'simulation' && (
                    <div className="rounded-lg p-6" style={{ background: '#111118', border: '1px solid #1E1E2A' }}>
                      {!simulationStarted ? (
                        <div className="max-w-2xl">
                          <div className="mb-5">
                            <div className="text-xs tracking-widest uppercase mb-2" style={{ color: '#C9A84C', fontFamily: 'var(--font-mono)' }}>
                              Hearing Simulation
                            </div>
                            <p style={{ color: '#6B6B80' }}>
                              Run the simulation inside this workspace using the contradictions and weaknesses already loaded from the analysis.
                            </p>
                          </div>

                          <div className="grid gap-4 md:grid-cols-2 mb-6">
                            <ModeCard title="Simulation Mode">
                              {(['judge', 'opponent'] as const).map((value) => (
                                <button
                                  key={value}
                                  onClick={() => setMode(value)}
                                  className="flex-1 py-2 rounded text-sm transition-all capitalize"
                                  style={{
                                    background: mode === value ? 'rgba(201,168,76,0.12)' : 'transparent',
                                    border: `1px solid ${mode === value ? 'rgba(201,168,76,0.4)' : '#2A2A38'}`,
                                    color: mode === value ? '#C9A84C' : '#6B6B80',
                                  }}
                                >
                                  {value === 'judge' ? 'Judge' : 'Opposing Counsel'}
                                </button>
                              ))}
                            </ModeCard>

                            <ModeCard title="Your Role">
                              {(['defense', 'prosecution'] as const).map((value) => (
                                <button
                                  key={value}
                                  onClick={() => setSide(value)}
                                  className="flex-1 py-2 rounded text-sm transition-all capitalize"
                                  style={{
                                    background: side === value ? 'rgba(201,168,76,0.12)' : 'transparent',
                                    border: `1px solid ${side === value ? 'rgba(201,168,76,0.4)' : '#2A2A38'}`,
                                    color: side === value ? '#C9A84C' : '#6B6B80',
                                  }}
                                >
                                  {value}
                                </button>
                              ))}
                            </ModeCard>
                          </div>

                          <div className="p-4 rounded-lg mb-6 text-xs space-y-1" style={{ background: '#0D0D14', border: '1px solid #1E1E2A', color: '#6B6B80' }}>
                            <div>{detail.weaknesses.length} weakness record(s) loaded</div>
                            <div>{detail.contradictions.length} contradiction(s) loaded</div>
                            <div>The simulation will use this workspace context automatically.</div>
                          </div>

                          <button
                            onClick={startSimulation}
                            className="w-full py-3 rounded font-medium transition-all"
                            style={{
                              background: 'rgba(201,168,76,0.12)',
                              border: '1px solid rgba(201,168,76,0.4)',
                              color: '#C9A84C',
                            }}
                          >
                            <Gavel size={14} className="inline mr-2" />
                            Begin Hearing
                          </button>
                        </div>
                      ) : (
                        <div className="flex flex-col" style={{ minHeight: '640px' }}>
                          <div className="flex items-center justify-between mb-4">
                            <div>
                              <div className="text-xs tracking-widest uppercase mb-1" style={{ color: '#C9A84C', fontFamily: 'var(--font-mono)' }}>
                                Simulation Live
                              </div>
                              <div style={{ color: '#6B6B80' }}>
                                {mode === 'judge' ? 'Judge' : 'Opposing counsel'} mode · You are representing the {side}.
                              </div>
                            </div>
                            <button
                              onClick={resetSimulation}
                              className="flex items-center gap-2 px-3 py-2 rounded text-xs uppercase tracking-widest"
                              style={{
                                background: 'transparent',
                                border: '1px solid #2A2A38',
                                color: '#A8A8B8',
                                fontFamily: 'var(--font-mono)',
                              }}
                            >
                              <RotateCcw size={12} />
                              Reset
                            </button>
                          </div>

                          <div className="flex-1 overflow-y-auto space-y-3 mb-4 pr-2" style={{ minHeight: 0 }}>
                            {messages.map((message, index) => (
                              <div key={`${message.timestamp}-${index}`} className={`flex ${message.role === 'lawyer' ? 'justify-end' : 'justify-start'}`}>
                                <div
                                  className="max-w-[75%] p-4 rounded-lg"
                                  style={
                                    message.role === 'lawyer'
                                      ? { background: 'rgba(201,168,76,0.08)', border: '1px solid rgba(201,168,76,0.2)' }
                                      : { background: '#0D0D14', border: '1px solid #1E1E2A' }
                                  }
                                >
                                  <div className="text-xs mb-1 flex items-center gap-2" style={{ color: '#6B6B80' }}>
                                    <span style={{ color: message.role === 'lawyer' ? '#C9A84C' : '#E05252' }}>
                                      {message.role === 'lawyer' ? 'You' : mode === 'judge' ? 'Judge' : 'Opposing Counsel'}
                                    </span>
                                    <span>{message.timestamp}</span>
                                  </div>
                                  <p className="text-sm leading-relaxed" style={{ color: '#E8E8F0', whiteSpace: 'pre-wrap' }}>
                                    {message.content}
                                  </p>
                                </div>
                              </div>
                            ))}

                            {simulationLoading && (
                              <div className="flex justify-start">
                                <div className="p-4 rounded-lg" style={{ background: '#0D0D14', border: '1px solid #1E1E2A' }}>
                                  <div className="flex gap-1">
                                    {[0, 1, 2].map((dot) => (
                                      <div
                                        key={dot}
                                        className="w-1.5 h-1.5 rounded-full"
                                        style={{ background: '#C9A84C', animation: `pulseDot 1.2s ease-in-out ${dot * 0.2}s infinite` }}
                                      />
                                    ))}
                                  </div>
                                </div>
                              </div>
                            )}
                            <div ref={bottomRef} />
                          </div>

                          <div className="flex gap-3">
                            <textarea
                              value={input}
                              onChange={(e) => setInput(e.target.value)}
                              placeholder="Type your answer as counsel..."
                              className="flex-1 rounded-lg px-4 py-3 text-sm outline-none resize-none"
                              style={{
                                background: '#0D0D14',
                                border: '1px solid #2A2A38',
                                color: '#E8E8F0',
                                minHeight: '88px',
                              }}
                            />
                            <button
                              onClick={sendSimulationMessage}
                              disabled={!input.trim() || simulationLoading}
                              className="self-end flex items-center gap-2 px-4 py-3 rounded text-sm"
                              style={{
                                background: !input.trim() || simulationLoading ? 'transparent' : 'rgba(201,168,76,0.12)',
                                border: `1px solid ${!input.trim() || simulationLoading ? '#2A2A38' : 'rgba(201,168,76,0.4)'}`,
                                color: !input.trim() || simulationLoading ? '#6B6B80' : '#C9A84C',
                              }}
                            >
                              <Send size={14} />
                              Send
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </>
              ) : (
                <div className="rounded-lg p-10 text-center" style={{ background: '#111118', border: '1px dashed #2A2A38' }}>
                  <FolderOpen size={36} className="mx-auto mb-4" style={{ color: '#3A3A4A' }} />
                  <div className="text-2xl mb-2" style={{ fontFamily: 'var(--font-display)', color: '#E8E8F0' }}>
                    Analyze this workspace to unlock the review views
                  </div>
                  <p className="max-w-2xl mx-auto" style={{ color: '#6B6B80' }}>
                    Once you upload documents and run the analysis, this panel will switch into workspace dashboard, timeline, contradictions, weaknesses, and hearing simulation.
                  </p>
                </div>
              )}
            </section>
          </div>
        </div>
      )}
    </div>
  )
}

function WorkspaceMeta({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded p-3" style={{ background: '#0D0D14', border: '1px solid #1E1E2A' }}>
      <div className="text-[10px] uppercase tracking-widest mb-1" style={{ color: '#6B6B80', fontFamily: 'var(--font-mono)' }}>
        {label}
      </div>
      <div className="text-sm" style={{ color: '#E8E8F0' }}>{value}</div>
    </div>
  )
}

function StatCard({
  icon,
  label,
  value,
  sub,
  accent,
}: {
  icon: ReactNode
  label: string
  value: number | string
  sub: string
  accent: string
}) {
  return (
    <div className="p-5 rounded-lg" style={{ background: '#111118', border: '1px solid #1E1E2A' }}>
      <div className="flex items-center gap-2 mb-3" style={{ color: accent }}>
        {icon}
        <span className="text-xs uppercase tracking-widest" style={{ fontFamily: 'var(--font-mono)', color: '#6B6B80' }}>
          {label}
        </span>
      </div>
      <div className="text-3xl font-semibold mb-1" style={{ fontFamily: 'var(--font-display)', color: '#E8E8F0' }}>
        {value}
      </div>
      <div className="text-xs" style={{ color: '#6B6B80' }}>{sub}</div>
    </div>
  )
}

function QuickPanel({ title, desc, color }: { title: string; desc: string; color: string }) {
  return (
    <div className="p-5 rounded-lg" style={{ background: '#111118', border: '1px solid #1E1E2A' }}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium" style={{ color: '#E8E8F0' }}>{title}</span>
        <span style={{ color }}>→</span>
      </div>
      <p className="text-xs" style={{ color: '#6B6B80' }}>{desc}</p>
    </div>
  )
}

function TimelineNode({ event, index }: { event: TimelineEvent; index: number }) {
  const [open, setOpen] = useState(false)
  const confidenceColor = event.confidence >= 0.8 ? '#4CAF7C' : event.confidence >= 0.7 ? '#D4882A' : '#E05252'

  return (
    <div className="relative pl-10 fade-up" style={{ animationDelay: `${index * 0.03}s` }}>
      <div
        className="absolute left-[13px] top-4 w-3 h-3 rounded-full border-2 z-10"
        style={{
          background: event.time_uncertain ? '#1E1E2A' : '#C9A84C',
          borderColor: event.time_uncertain ? '#3A3A4A' : '#C9A84C',
          boxShadow: event.time_uncertain ? 'none' : '0 0 8px rgba(201,168,76,0.4)',
        }}
      />

      <div
        className="mb-1 rounded-lg overflow-hidden transition-all duration-200 cursor-pointer"
        style={{ background: '#111118', border: '1px solid #1E1E2A' }}
        onClick={() => setOpen(!open)}
      >
        <div className="px-4 py-3 flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <span className="text-xs px-2 py-0.5 rounded" style={{ background: 'rgba(107,143,212,0.15)', color: '#6B8FD4', fontFamily: 'var(--font-mono)' }}>
                #{event.timeline_position}
              </span>
              {event.time_uncertain && (
                <span className="text-xs px-2 py-0.5 rounded" style={{ background: 'rgba(107,107,128,0.15)', color: '#6B6B80' }}>
                  time uncertain
                </span>
              )}
              <span className="text-xs" style={{ color: confidenceColor, fontFamily: 'var(--font-mono)' }}>
                {Math.round(event.confidence * 100)}% conf
              </span>
            </div>
            <div className="text-sm font-medium" style={{ color: '#E8E8F0' }}>
              <span style={{ color: '#C9A84C' }}>{event.actor}</span>
              <span style={{ color: '#6B6B80' }}> → </span>
              {event.action}
            </div>
          </div>
          <div className="text-xs text-right flex-shrink-0" style={{ color: '#6B6B80' }}>
            {event.time || '—'}
          </div>
        </div>

        {open && (
          <div className="px-4 pb-3 pt-0 border-t" style={{ borderColor: '#1E1E2A' }}>
            <div className="grid grid-cols-2 gap-3 mt-3">
              {event.location && <DetailRow icon={<MapPin size={12} />} label="Location" value={event.location} />}
              <DetailRow icon={<FileText size={12} />} label="Source" value={event.source_document} />
              {event.time && <DetailRow icon={<Clock size={12} />} label="Time" value={event.time} />}
              <DetailRow icon={<User size={12} />} label="Actor" value={event.actor} />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function DetailRow({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-start gap-2">
      <span className="mt-0.5" style={{ color: '#6B6B80' }}>{icon}</span>
      <div>
        <div className="text-xs uppercase tracking-wider mb-0.5" style={{ color: '#3A3A4A', fontFamily: 'var(--font-mono)' }}>
          {label}
        </div>
        <div className="text-xs" style={{ color: '#A8A8B8' }}>{value}</div>
      </div>
    </div>
  )
}

function ContradictionCard({ contradiction, index }: { contradiction: Contradiction; index: number }) {
  const [open, setOpen] = useState(false)

  const styles: Record<string, { color: string; bg: string; border: string }> = {
    critical: { color: '#E05252', bg: 'rgba(224,82,82,0.06)', border: 'rgba(224,82,82,0.25)' },
    moderate: { color: '#D4882A', bg: 'rgba(212,136,42,0.06)', border: 'rgba(212,136,42,0.25)' },
    minor: { color: '#4CAF7C', bg: 'rgba(76,175,124,0.06)', border: 'rgba(76,175,124,0.25)' },
  }

  const tone = styles[contradiction.severity] ?? styles.minor

  return (
    <div className="rounded-lg overflow-hidden fade-up" style={{ animationDelay: `${index * 0.04}s`, background: tone.bg, border: `1px solid ${tone.border}` }}>
      <div className="px-5 py-4 flex items-start justify-between cursor-pointer" onClick={() => setOpen(!open)}>
        <div className="flex items-start gap-3 flex-1">
          <AlertTriangle size={15} className="mt-0.5 flex-shrink-0" style={{ color: tone.color }} />
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <span className="text-xs px-2 py-0.5 rounded uppercase tracking-wider" style={{ background: tone.bg, color: tone.color, border: `1px solid ${tone.border}`, fontFamily: 'var(--font-mono)' }}>
                {contradiction.severity}
              </span>
              <span className="text-xs" style={{ color: '#6B6B80', fontFamily: 'var(--font-mono)' }}>
                {contradiction.type.replace(/_/g, ' ')}
              </span>
            </div>
            <p className="text-sm" style={{ color: '#A8A8B8' }}>{contradiction.description}</p>
          </div>
        </div>
        <div style={{ color: '#6B6B80' }}>
          {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </div>
      </div>

      {open && (
        <div className="px-5 pb-4 pt-0 border-t" style={{ borderColor: 'rgba(255,255,255,0.05)' }}>
          <div className="grid grid-cols-2 gap-3 mt-3">
            <div className="p-3 rounded" style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid #1E1E2A' }}>
              <div className="text-xs uppercase tracking-widest mb-1" style={{ color: '#6B6B80', fontFamily: 'var(--font-mono)' }}>Event 1</div>
              <p className="text-xs" style={{ color: '#A8A8B8' }}>{contradiction.event1_summary}</p>
            </div>
            <div className="p-3 rounded" style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid #1E1E2A' }}>
              <div className="text-xs uppercase tracking-widest mb-1" style={{ color: '#6B6B80', fontFamily: 'var(--font-mono)' }}>Event 2</div>
              <p className="text-xs" style={{ color: '#A8A8B8' }}>{contradiction.event2_summary}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function SeverityBadge({ count, label, color, bg }: { count: number; label: string; color: string; bg: string }) {
  return (
    <div className="px-4 py-2 rounded-lg flex items-center gap-2" style={{ background: bg, border: `1px solid ${color}30` }}>
      <span className="text-lg font-semibold" style={{ fontFamily: 'var(--font-display)', color }}>{count}</span>
      <span className="text-xs" style={{ color }}>{label}</span>
    </div>
  )
}

function WeaknessRow({ weakness, index }: { weakness: Weakness; index: number }) {
  const [open, setOpen] = useState(false)

  const palette = {
    high: { color: '#E05252', bg: 'rgba(224,82,82,0.06)', bar: '#E05252' },
    medium: { color: '#D4882A', bg: 'rgba(212,136,42,0.06)', bar: '#D4882A' },
    low: { color: '#4CAF7C', bg: 'rgba(76,175,124,0.06)', bar: '#4CAF7C' },
  }
  const tone = palette[weakness.severity]
  const pct = Math.round(weakness.weakness_score * 100)

  return (
    <div className="rounded-lg overflow-hidden fade-up" style={{ animationDelay: `${index * 0.025}s`, background: '#111118', border: '1px solid #1E1E2A' }}>
      <div className="px-4 py-3 flex items-center gap-4 cursor-pointer" onClick={() => setOpen(!open)}>
        <div className="flex-shrink-0 w-12 text-center">
          <div className="text-lg font-semibold leading-none" style={{ fontFamily: 'var(--font-display)', color: tone.color }}>
            {pct}
          </div>
          <div className="text-xs" style={{ color: '#3A3A4A', fontFamily: 'var(--font-mono)' }}>/ 100</div>
        </div>

        <div className="flex-shrink-0 w-24 h-1.5 rounded-full overflow-hidden" style={{ background: '#1E1E2A' }}>
          <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: tone.bar }} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-xs px-2 py-0.5 rounded uppercase tracking-wider flex-shrink-0" style={{ background: tone.bg, color: tone.color, fontFamily: 'var(--font-mono)' }}>
              {weakness.severity}
            </span>
            <span className="text-xs truncate" style={{ color: '#C9A84C' }}>{weakness.actor}</span>
          </div>
          <p className="text-sm truncate" style={{ color: '#A8A8B8' }}>{weakness.action}</p>
        </div>

        <div style={{ color: '#6B6B80', flexShrink: 0 }}>
          {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </div>
      </div>

      {open && (
        <div className="px-4 pb-3 pt-0 border-t" style={{ borderColor: '#1E1E2A' }}>
          <div className="mt-3">
            <div className="text-xs uppercase tracking-widest mb-2" style={{ color: '#6B6B80', fontFamily: 'var(--font-mono)' }}>
              Risk Factors
            </div>
            <div className="space-y-1">
              {weakness.reasons.map((reason, index) => (
                <div key={`${reason}-${index}`} className="flex items-center gap-2 text-xs" style={{ color: '#A8A8B8' }}>
                  <span style={{ color: tone.color }}>·</span>
                  {reason}
                </div>
              ))}
            </div>
            <div className="mt-3 text-xs" style={{ color: '#6B6B80' }}>
              Source: <span style={{ color: '#A8A8B8', fontFamily: 'var(--font-mono)' }}>{weakness.source_document}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function ModeCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="p-4 rounded-lg" style={{ background: '#0D0D14', border: '1px solid #1E1E2A' }}>
      <label className="text-xs uppercase tracking-widest block mb-3" style={{ color: '#6B6B80', fontFamily: 'var(--font-mono)' }}>
        {title}
      </label>
      <div className="flex gap-2">{children}</div>
    </div>
  )
}
