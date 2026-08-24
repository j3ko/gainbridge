import type { ColumnDef } from "@tanstack/react-table"

import type { SourcePublic } from "@/client"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { SourceActionsMenu } from "./SourceActionsMenu"

export const columns: ColumnDef<SourcePublic>[] = [
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) => <span className="font-medium">{row.original.name}</span>,
  },
  {
    accessorKey: "type",
    header: "Type",
    cell: ({ row }) => {
      const type = row.original.type
      return (
        <span
          className={cn(
            "max-w-xs truncate block text-muted-foreground",
            !type && "italic",
          )}
        >
          {type || "No type"}
        </span>
      )
    },
  },
  {
    accessorKey: "schedule_cron",
    header: "Schedule",
    cell: ({ row }) => {
      const { schedule_enabled, schedule_cron, next_run_at } = row.original
      if (!schedule_enabled || !schedule_cron) {
        return <Badge variant="outline">Off</Badge>
      }
      return (
        <div className="flex flex-col gap-0.5">
          <Badge variant="secondary" className="font-mono">
            {schedule_cron}
          </Badge>
          {next_run_at && (
            <span className="text-xs text-muted-foreground">
              Next: {new Date(next_run_at).toLocaleString()}
            </span>
          )}
        </div>
      )
    },
  },
  {
    id: "actions",
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) => (
      <div className="flex justify-end">
        <SourceActionsMenu source={row.original} />
      </div>
    ),
  },
]
