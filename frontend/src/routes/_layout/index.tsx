import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Search } from "lucide-react"
import { SourcesService } from "@/client"
import { DataTable } from "@/components/Common/DataTable"
import AddSource from "@/components/Sources/AddSource"
import { columns } from "@/components/Sources/columns"
import SyncAll from "@/components/Sources/SyncAll"

export const Route = createFileRoute("/_layout/")({
  component: Dashboard,
  head: () => ({
    meta: [
      {
        title: "Dashboard - FastAPI Cloud",
      },
    ],
  }),
})

function SourcesTable() {
  const { data: sources, isPending } = useQuery({
    queryKey: ["sources"],
    queryFn: () => SourcesService.listSources(),
  })

  if (isPending) {
    return (
      <div className="py-12 text-center text-muted-foreground">Loading...</div>
    )
  }

  if (!sources || sources.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center text-center py-12">
        <div className="rounded-full bg-muted p-4 mb-4">
          <Search className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold">
          You don't have any sources yet
        </h3>
        <p className="text-muted-foreground">Add a new source to get started</p>
      </div>
    )
  }

  return <DataTable columns={columns} data={sources} />
}

function Dashboard() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Sources</h1>
          <p className="text-muted-foreground">
            Create and manage your sources
          </p>
        </div>
        <div className="flex items-center gap-2">
          <SyncAll />
          <AddSource />
        </div>
      </div>
      <SourcesTable />
    </div>
  )
}
