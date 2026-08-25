import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import type { PaginationState } from "@tanstack/react-table"
import { ScrollText } from "lucide-react"
import { useState } from "react"

import { JobsService } from "@/client"
import { DataTable } from "@/components/Common/DataTable"
import { columns } from "@/components/Jobs/columns"

export const Route = createFileRoute("/_layout/jobs")({
  component: Jobs,
  head: () => ({
    meta: [
      {
        title: "Jobs - FastAPI Cloud",
      },
    ],
  }),
})

function JobsTable() {
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 25,
  })

  const { data, isPending } = useQuery({
    queryKey: ["jobs", pagination.pageIndex, pagination.pageSize],
    queryFn: () =>
      JobsService.listJobs({
        skip: pagination.pageIndex * pagination.pageSize,
        limit: pagination.pageSize,
      }),
    placeholderData: keepPreviousData,
    refetchInterval: (query) => {
      const hasActiveJob = query.state.data?.data.some(
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

  if (!data || data.data.length === 0) {
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

  return (
    <DataTable
      columns={columns}
      data={data.data}
      pagination={pagination}
      onPaginationChange={setPagination}
      rowCount={data.count}
    />
  )
}

function Jobs() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Jobs</h1>
        <p className="text-muted-foreground">
          Track the status of your ReplayGain sync jobs
        </p>
      </div>
      <JobsTable />
    </div>
  )
}
