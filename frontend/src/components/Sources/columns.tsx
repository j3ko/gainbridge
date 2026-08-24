import type { ColumnDef } from "@tanstack/react-table"
import { Check, Copy } from "lucide-react"

import type { SourcePublic } from "@/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { useCopyToClipboard } from "@/hooks/useCopyToClipboard"
import { cn } from "@/lib/utils"
import { SourceActionsMenu } from "./SourceActionsMenu"

function _CopyId({ id }: { id: string }) {
  const [copiedText, copy] = useCopyToClipboard()
  const isCopied = copiedText === id

  return (
    <div className="flex items-center gap-1.5 group">
      <span className="font-mono text-xs text-muted-foreground">{id}</span>
      <Button
        variant="ghost"
        size="icon"
        className="size-6 opacity-0 group-hover:opacity-100 transition-opacity"
        onClick={() => copy(id)}
      >
        {isCopied ? (
          <Check className="size-3 text-green-500" />
        ) : (
          <Copy className="size-3" />
        )}
        <span className="sr-only">Copy ID</span>
      </Button>
    </div>
  )
}

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
