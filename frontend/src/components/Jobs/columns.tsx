import type { ColumnDef } from "@tanstack/react-table"

import type { JobPublic } from "@/client"
import CancelJob from "@/components/Jobs/CancelJob"
import { writeModeOptions } from "@/components/Sources/writeModeOptions"
import { Badge } from "@/components/ui/badge"

const writeModeShortLabels = Object.fromEntries(
  writeModeOptions.map((option) => [option.value, option.shortLabel]),
)

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
      const {
        processed = 0,
        total = 0,
        written = 0,
        skipped = 0,
        errors = 0,
      } = row.original
      return (
        <div
          className="text-sm whitespace-nowrap"
          title={`${written} written, ${skipped} skipped, ${errors} errors`}
        >
          <div className="text-muted-foreground">
            {processed} / {total || "?"}
          </div>
          <div className="flex gap-1.5 text-xs">
            <span>{written}w</span>
            <span className="text-muted-foreground">{skipped}s</span>
            {errors > 0 && <span className="text-destructive">{errors}e</span>}
          </div>
        </div>
      )
    },
  },
  {
    id: "mode",
    header: "Mode",
    cell: ({ row }) => {
      const mode = row.original.write_mode ?? "fix"
      return (
        <div className="flex flex-col text-sm whitespace-nowrap">
          <span>{row.original.dry_run ? "Dry run" : "Write"}</span>
          <span className="text-muted-foreground text-xs">
            {writeModeShortLabels[mode] ?? mode}
          </span>
        </div>
      )
    },
  },
  {
    accessorKey: "created_at",
    header: "Started",
    cell: ({ row }) => (
      <span className="whitespace-nowrap">
        {new Date(row.original.created_at).toLocaleString(undefined, {
          dateStyle: "short",
          timeStyle: "short",
        })}
      </span>
    ),
  },
  {
    id: "message",
    header: "Message",
    cell: ({ row }) => {
      const message = row.original.message || "—"
      return (
        <span
          title={message}
          className="text-muted-foreground text-sm block max-w-[160px] truncate"
        >
          {message}
        </span>
      )
    },
  },
  {
    id: "actions",
    header: "",
    cell: ({ row }) => <CancelJob job={row.original} />,
  },
]
