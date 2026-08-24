import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { ScrollText } from "lucide-react"

import { JobsService } from "@/client"
import { DataTable } from "@/components/Common/DataTable"
import { columns } from "@/components/Jobs/columns"

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

function JobsTable() {
  const { data: jobs, isPending } = useQuery({
    queryKey: ["jobs"],
    queryFn: () => JobsService.listJobs(),
    refetchInterval: (query) => {
      const hasActiveJob = query.state.data?.some(
        (job) => job.status === "pending" || job.status === "running",
      )
      return hasActiveJob ? 2000 : false
    },
  })

  if (isPending) {
    return (
      <div className="py-12 text-center text-muted-foreground">Loading...</div>
    )
  }

  if (!jobs || jobs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center text-center py-12">
        <div className="rounded-full bg-muted p-4 mb-4">
          <ScrollText className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold">No sync jobs yet</h3>
        <p className="text-muted-foreground">
          Run a sync from a source to see its progress here
        </p>
      </div>
    )
  }

  return <DataTable columns={columns} data={jobs} />
}

function Logs() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Logs</h1>
        <p className="text-muted-foreground">
          Track the status of your ReplayGain sync jobs
        </p>
      </div>
      <JobsTable />
    </div>
  )
}
