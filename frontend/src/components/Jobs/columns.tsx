import type { ColumnDef } from "@tanstack/react-table"

import type { JobPublic } from "@/client"
import { Badge } from "@/components/ui/badge"

const statusVariant: Record<
  string,
  "default" | "secondary" | "destructive" | "outline"
> = {
  pending: "secondary",
  running: "default",
  completed: "outline",
  failed: "destructive",
  cancelled: "secondary",
}

export const columns: ColumnDef<JobPublic>[] = [
  {
    accessorKey: "source_name",
    header: "Source",
    cell: ({ row }) => (
      <span className="font-medium">{row.original.source_name}</span>
    ),
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => {
      const status = row.original.status ?? "pending"
      return (
        <Badge variant={statusVariant[status] ?? "secondary"}>{status}</Badge>
      )
    },
  },
  {
    id: "progress",
    header: "Progress",
    cell: ({ row }) => {
      const { processed = 0, total = 0 } = row.original
      return (
        <span className="text-muted-foreground text-sm">
          {processed} / {total || "?"}
        </span>
      )
    },
  },
  {
    accessorKey: "written",
    header: "Written",
    cell: ({ row }) => row.original.written ?? 0,
  },
  {
    accessorKey: "skipped",
    header: "Skipped",
    cell: ({ row }) => row.original.skipped ?? 0,
  },
  {
    accessorKey: "errors",
    header: "Errors",
    cell: ({ row }) => row.original.errors ?? 0,
  },
  {
    accessorKey: "dry_run",
    header: "Mode",
    cell: ({ row }) => (row.original.dry_run ? "Dry run" : "Write"),
  },
  {
    accessorKey: "created_at",
    header: "Started",
    cell: ({ row }) => new Date(row.original.created_at).toLocaleString(),
  },
  {
    id: "message",
    header: "Message",
    cell: ({ row }) => (
      <span className="text-muted-foreground text-sm">
        {row.original.message || "—"}
      </span>
    ),
  },
]
