import { useMutation, useQueryClient } from "@tanstack/react-query"
import { RefreshCw } from "lucide-react"
import { useState } from "react"

import { JobsService, type SourcePublic, type write_mode } from "@/client"
import { Button } from "@/components/ui/button"
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
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { writeModeOptions } from "./writeModeOptions"

interface SyncSourceProps {
  source: SourcePublic
  onSuccess: () => void
}

const SyncSource = ({ source, onSuccess }: SyncSourceProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const [writeMode, setWriteMode] = useState<write_mode>("fix")
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: () =>
      JobsService.createJob({
        requestBody: {
          source_name: source.name,
          dry_run: false,
          write_mode: writeMode,
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
        if (open) setWriteMode("fix")
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

        <RadioGroup
          value={writeMode}
          onValueChange={(value) => setWriteMode(value as write_mode)}
          className="py-2"
        >
          {writeModeOptions.map((option) => (
            <div key={option.value} className="flex items-start gap-3">
              <RadioGroupItem
                value={option.value}
                id={`write-mode-${option.value}`}
                className="mt-1"
              />
              <Label
                htmlFor={`write-mode-${option.value}`}
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

export default SyncSource
