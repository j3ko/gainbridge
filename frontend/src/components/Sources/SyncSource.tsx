import { useMutation, useQueryClient } from "@tanstack/react-query"
import { RefreshCw } from "lucide-react"
import { useState } from "react"

import { JobsService, type SourcePublic } from "@/client"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { DropdownMenuItem } from "@/components/ui/dropdown-menu"
import { Label } from "@/components/ui/label"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface SyncSourceProps {
  source: SourcePublic
  onSuccess: () => void
}

const SyncSource = ({ source, onSuccess }: SyncSourceProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const [overwriteExisting, setOverwriteExisting] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: () =>
      JobsService.createJob({
        requestBody: {
          source_name: source.name,
          dry_run: false,
          overwrite_existing: overwriteExisting,
        },
      }),
    onSuccess: () => {
      showSuccessToast(`Sync started for "${source.name}"`)
      setIsOpen(false)
      onSuccess()
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] })
    },
  })

  return (
    <Dialog
      open={isOpen}
      onOpenChange={(open) => {
        setIsOpen(open)
        if (open) setOverwriteExisting(false)
      }}
    >
      <DropdownMenuItem
        onSelect={(e) => e.preventDefault()}
        onClick={() => setIsOpen(true)}
      >
        <RefreshCw />
        Sync Now
      </DropdownMenuItem>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Sync "{source.name}"</DialogTitle>
          <DialogDescription>
            Scan this source and write ReplayGain tags to its tracks.
          </DialogDescription>
        </DialogHeader>

        <div className="flex items-center gap-3 py-4">
          <Checkbox
            id="overwrite-existing"
            checked={overwriteExisting}
            onCheckedChange={(checked) =>
              setOverwriteExisting(checked === true)
            }
          />
          <Label htmlFor="overwrite-existing" className="font-normal">
            Overwrite existing ReplayGain tags
          </Label>
        </div>

        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline" disabled={mutation.isPending}>
              Cancel
            </Button>
          </DialogClose>
          <LoadingButton
            loading={mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            Sync
          </LoadingButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default SyncSource
