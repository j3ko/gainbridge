import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { ArrowDownToLine } from "lucide-react"
import { useEffect, useMemo, useRef, useState } from "react"

import { JobsService } from "@/client"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"

// How close to the bottom (in px) still counts as "at the bottom" -- lets
// auto-scroll re-engage without requiring pixel-perfect scrolling.
const AUTO_SCROLL_THRESHOLD_PX = 24

export const Route = createFileRoute("/_layout/logs")({
  component: Logs,
  head: () => ({
    meta: [
      {
        title: "Logs - Gainbridge",
      },
    ],
  }),
})

const ALL_JOBS = "all"

// Matches the "<date> <time> LEVEL logger.name: message" format from
// logging_config.py, e.g. "2026-08-26 03:17:15,150 WARNING app.services.jobs: ...".
const LOG_LEVEL_PATTERN = /^\S+ \S+ (\w+) /
const WARN_OR_ABOVE = new Set(["WARNING", "ERROR", "CRITICAL"])

const ALL_LEVELS = "all"
const WARNINGS_AND_ERRORS = "warnings"

// A continuation line (e.g. a traceback) has no level prefix of its own --
// it inherits whatever level the line above it carried.
function filterToWarningsAndErrors(log: string): string {
  let currentLevelMatches = true
  return log
    .split("\n")
    .filter((line) => {
      const match = line.match(LOG_LEVEL_PATTERN)
      if (match) {
        currentLevelMatches = WARN_OR_ABOVE.has(match[1])
      }
      return currentLevelMatches
    })
    .join("\n")
}

function LogViewer() {
  const [selectedJobId, setSelectedJobId] = useState(ALL_JOBS)
  const [levelFilter, setLevelFilter] = useState(ALL_LEVELS)
  const [autoScroll, setAutoScroll] = useState(true)
  const [displayedLog, setDisplayedLog] = useState("")
  const scrollRef = useRef<HTMLPreElement>(null)

  // Bounded to the most recent jobs -- this is a dropdown, not a paginated
  // list, so we just cap how many show up rather than fetching every job
  // that's ever run.
  const { data: jobsPage } = useQuery({
    queryKey: ["jobs", "recent"],
    queryFn: () => JobsService.listJobs({ limit: 100 }),
    refetchInterval: (query) => {
      const hasActiveJob = query.state.data?.data.some(
        (job) => job.status === "pending" || job.status === "running",
      )
      return hasActiveJob ? 2000 : false
    },
  })
  const jobs = jobsPage?.data

  const { data: jobLog, isPending } = useQuery({
    queryKey: ["jobs", "log", selectedJobId],
    queryFn: () =>
      JobsService.getJobsLog({
        jobId: selectedJobId === ALL_JOBS ? undefined : selectedJobId,
      }),
    refetchInterval: (query) => {
      const hasActiveJob = jobs?.some(
        (job) => job.status === "pending" || job.status === "running",
      )
      return hasActiveJob && !query.state.error ? 2000 : false
    },
  })

  // biome-ignore lint/correctness/useExhaustiveDependencies: selectedJobId triggers a reset on switching logs, though it isn't read in the body
  useEffect(() => {
    setAutoScroll(true)
    setDisplayedLog("")
  }, [selectedJobId])

  // The "All jobs" log is capped server-side to the last MAX_LOG_LINES, so
  // once that cap is hit, older lines get evicted from the top on every
  // poll. Adopting that directly while paused would shift the content
  // under the user's fixed scroll position even though scrollTop never
  // moves. So while paused, only accept updates that are a pure append
  // (new content starts with what's already shown) and otherwise freeze
  // the view -- new lines resume appearing once auto-scroll re-engages.
  useEffect(() => {
    const newLog = jobLog?.log
    if (newLog === undefined) return
    if (autoScroll || newLog.startsWith(displayedLog)) {
      setDisplayedLog(newLog)
    }
  }, [jobLog?.log, autoScroll, displayedLog])

  const visibleLog = useMemo(
    () =>
      levelFilter === WARNINGS_AND_ERRORS
        ? filterToWarningsAndErrors(displayedLog)
        : displayedLog,
    [displayedLog, levelFilter],
  )

  // biome-ignore lint/correctness/useExhaustiveDependencies: visibleLog triggers a re-scroll on new content, though it isn't read in the body
  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [visibleLog, autoScroll])

  const handleScroll = () => {
    const el = scrollRef.current
    if (!el) return
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight
    setAutoScroll(distanceFromBottom <= AUTO_SCROLL_THRESHOLD_PX)
  }

  const handleAutoScrollChange = (checked: boolean) => {
    if (checked) {
      // Re-enabling should immediately catch up, not wait for the next log line.
      const el = scrollRef.current
      if (el) el.scrollTop = el.scrollHeight
    }
    setAutoScroll(checked)
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-end gap-2">
        <div className="flex items-center gap-2">
          <Switch
            id="auto-scroll"
            checked={autoScroll}
            onCheckedChange={handleAutoScrollChange}
          />
          <Label
            htmlFor="auto-scroll"
            className="flex items-center gap-1.5 font-normal"
          >
            <ArrowDownToLine className="size-4 text-muted-foreground" />
            Auto-scroll
          </Label>
        </div>
        <Select value={levelFilter} onValueChange={setLevelFilter}>
          <SelectTrigger className="w-[200px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL_LEVELS}>All levels</SelectItem>
            <SelectItem value={WARNINGS_AND_ERRORS}>
              Warnings & errors only
            </SelectItem>
          </SelectContent>
        </Select>
        <Select value={selectedJobId} onValueChange={setSelectedJobId}>
          <SelectTrigger className="w-[280px]">
            <SelectValue placeholder="All jobs" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL_JOBS}>All jobs</SelectItem>
            {jobs?.map((job) => (
              <SelectItem key={job.id} value={job.id}>
                {job.source_name} — {new Date(job.created_at).toLocaleString()}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <pre
        ref={scrollRef}
        onScroll={handleScroll}
        className="max-h-[500px] overflow-y-auto rounded-md border bg-muted/20 p-4 text-xs whitespace-pre-wrap break-words"
      >
        {isPending
          ? "Loading..."
          : visibleLog ||
            (displayedLog
              ? "No log entries match this filter."
              : "No log entries yet.")}
      </pre>
    </div>
  )
}

function Logs() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Logs</h1>
        <p className="text-muted-foreground">
          Raw log output from your ReplayGain sync jobs
        </p>
      </div>
      <LogViewer />
    </div>
  )
}
