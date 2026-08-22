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
        <EditSource source={source} onSuccess={() => setOpen(false)} />
        <DeleteSource id={source.id} onSuccess={() => setOpen(false)} />
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
