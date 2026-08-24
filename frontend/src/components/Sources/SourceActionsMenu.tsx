import { EllipsisVertical } from "lucide-react"
import { useState } from "react"

import type { SourcePublic } from "@/client"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import DeleteSource from "../Sources/DeleteSource"
import EditSource from "../Sources/EditSource"
import ScheduleSource from "../Sources/ScheduleSource"
import SyncSource from "../Sources/SyncSource"

interface SourceActionsMenuProps {
  source: SourcePublic
}

export const SourceActionsMenu = ({ source }: SourceActionsMenuProps) => {
  const [open, setOpen] = useState(false)

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon">
          <EllipsisVertical />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <SyncSource source={source} onSuccess={() => setOpen(false)} />
        <ScheduleSource source={source} onSuccess={() => setOpen(false)} />
        <EditSource source={source} onSuccess={() => setOpen(false)} />
        <DeleteSource name={source.name} onSuccess={() => setOpen(false)} />
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
