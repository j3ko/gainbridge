import { SourcePublic } from "@/client"
import { DataTable } from "@/components/Common/DataTable"
import AddSource from "@/components/Sources/AddSource"
import { columns } from "@/components/Sources/columns"
import SyncAll from "@/components/Sources/SyncAll"
import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Search } from "lucide-react"

const MOCK_SOURCES: SourcePublic[] = [
  {
    id: 1,
    name: "Source 1",
    type: "plex",
    base_url: "http://192.168.1.10:32400",
    token: "secret",
    enabled: true,
    created_at: new Date().toISOString(),
    // add any other required SourcePublic fields from types.gen.ts
  },
]

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

function SourcesTableContent() {
  const { data: sources } = useSuspenseQuery({
    queryKey: ["sources"],
    queryFn: async (): Promise<SourcePublic[]> => MOCK_SOURCES,
  })

  if (sources.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center text-center py-12">
        <div className="rounded-full bg-muted p-4 mb-4">
          <Search className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold">You don't have any sources yet</h3>
        <p className="text-muted-foreground">Add a new source to get started</p>
      </div>
    )
  }

  return <DataTable columns={columns} data={sources} />
}

function SourcesTable() {
  return (
    // <Suspense fallback={<PendingItems />}>
    //   <SourcesTableContent />
    // </Suspense>
    <SourcesTableContent />
  )
}

function Dashboard() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Sources</h1>
          <p className="text-muted-foreground">Create and manage your sources</p>
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
