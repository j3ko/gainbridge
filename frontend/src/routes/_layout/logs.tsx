import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { useState } from "react"

import { JobsService } from "@/client"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

export const Route = createFileRoute("/_layout/logs")({
  component: Logs,
  head: () => ({
    meta: [
      {
        title: "Logs - FastAPI Cloud",
      },
    ],
  }),
})

const ALL_JOBS = "all"

function LogViewer() {
  const [selectedJobId, setSelectedJobId] = useState(ALL_JOBS)

  const { data: jobs } = useQuery({
    queryKey: ["jobs"],
    queryFn: () => JobsService.listJobs(),
    refetchInterval: (query) => {
      const hasActiveJob = query.state.data?.some(
        (job) => job.status === "pending" || job.status === "running",
      )
      return hasActiveJob ? 2000 : false
    },
  })

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

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-end">
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
      <pre className="max-h-[500px] overflow-y-auto rounded-md border bg-muted/20 p-4 text-xs whitespace-pre-wrap break-words">
        {isPending ? "Loading..." : jobLog?.log || "No log entries yet."}
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
