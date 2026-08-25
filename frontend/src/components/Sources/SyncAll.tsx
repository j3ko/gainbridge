import { useMutation, useQueryClient } from "@tanstack/react-query"
import { RefreshCw } from "lucide-react"
import { useState } from "react"

import { JobsService, SourcesService, type write_mode } from "@/client"
import { Button } from "@/components/ui/button"
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
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { writeModeOptions } from "./writeModeOptions"

const SyncAll = () => {
  const [isOpen, setIsOpen] = useState(false)
  const [writeMode, setWriteMode] = useState<write_mode>("fix")
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
              write_mode: writeMode,
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
        if (open) setWriteMode("fix")
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

        <RadioGroup
          value={writeMode}
          onValueChange={(value) => setWriteMode(value as write_mode)}
          className="py-2"
        >
          {writeModeOptions.map((option) => (
            <div key={option.value} className="flex items-start gap-3">
              <RadioGroupItem
                value={option.value}
                id={`write-mode-all-${option.value}`}
                className="mt-1"
              />
              <Label
                htmlFor={`write-mode-all-${option.value}`}
                className="flex flex-col items-start gap-1 font-normal"
              >
                {option.label}
                <span className="text-sm text-muted-foreground">
                  {option.description}
                </span>
              </Label>
            </div>
          ))}
        </RadioGroup>

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
