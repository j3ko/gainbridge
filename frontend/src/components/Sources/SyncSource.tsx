import { useMutation, useQueryClient } from "@tanstack/react-query"
import { RefreshCw } from "lucide-react"

import { JobsService, type SourcePublic } from "@/client"
import { DropdownMenuItem } from "@/components/ui/dropdown-menu"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface SyncSourceProps {
  source: SourcePublic
  onSuccess: () => void
}

const SyncSource = ({ source, onSuccess }: SyncSourceProps) => {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: () =>
      JobsService.createJob({
        requestBody: { source_name: source.name, dry_run: false },
      }),
    onSuccess: () => {
      showSuccessToast(`Sync started for "${source.name}"`)
      onSuccess()
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] })
    },
  })

  return (
    <DropdownMenuItem
      onSelect={(e) => e.preventDefault()}
      onClick={() => mutation.mutate()}
      disabled={mutation.isPending}
    >
      <RefreshCw />
      Sync Now
    </DropdownMenuItem>
  )
}

export default SyncSource
