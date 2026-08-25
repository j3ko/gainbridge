import { useMutation, useQueryClient } from "@tanstack/react-query"
import { RefreshCw } from "lucide-react"
import { useState } from "react"

import { JobsService, SourcesService } from "@/client"
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
  DialogTrigger,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

const SyncAll = () => {
  const [isOpen, setIsOpen] = useState(false)
  const [overwriteExisting, setOverwriteExisting] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: async () => {
      const sources = await SourcesService.listSources()
      const enabled = sources.filter((source) => source.enabled)
      await Promise.all(
        enabled.map((source) =>
          JobsService.createJob({
            requestBody: {
              source_name: source.name,
              dry_run: false,
              overwrite_existing: overwriteExisting,
            },
          }),
        ),
      )
      return enabled.length
    },
    onSuccess: (count) => {
      showSuccessToast(
        count > 0
          ? `Sync started for ${count} source${count === 1 ? "" : "s"}`
          : "No enabled sources to sync",
      )
      setIsOpen(false)
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
      <DialogTrigger asChild>
        <Button className="my-4" variant="outline">
          <RefreshCw className="mr-2" />
          Sync All
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Sync All Sources</DialogTitle>
          <DialogDescription>
            Scan every enabled source and write ReplayGain tags to their tracks.
          </DialogDescription>
        </DialogHeader>

        <div className="flex items-center gap-3 py-4">
          <Checkbox
            id="overwrite-existing-all"
            checked={overwriteExisting}
            onCheckedChange={(checked) =>
              setOverwriteExisting(checked === true)
            }
          />
          <Label htmlFor="overwrite-existing-all" className="font-normal">
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

export default SyncAll
