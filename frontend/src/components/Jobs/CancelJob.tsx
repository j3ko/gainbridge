import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Ban, Loader2 } from "lucide-react"

import { type JobPublic, JobsService } from "@/client"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface CancelJobProps {
  job: JobPublic
}

const CancelJob = ({ job }: CancelJobProps) => {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: () => JobsService.cancelJob({ jobId: job.id }),
    onSuccess: () => {
      showSuccessToast(`Sync for "${job.source_name}" cancelled`)
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] })
    },
  })

  if (job.status !== "pending" && job.status !== "running") {
    return null
  }

  return (
    <LoadingButton
      variant="ghost"
      size="icon"
      title="Cancel sync"
      disabled={mutation.isPending}
      onClick={() => mutation.mutate()}
    >
      {mutation.isPending ? <Loader2 className="animate-spin" /> : <Ban />}
      <span className="sr-only">Cancel sync</span>
    </LoadingButton>
  )
}

export default CancelJob
