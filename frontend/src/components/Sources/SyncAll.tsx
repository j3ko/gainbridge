import { useMutation, useQueryClient } from "@tanstack/react-query"
import { RefreshCw } from "lucide-react"

import { JobsService, SourcesService } from "@/client"
import { Button } from "@/components/ui/button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

const SyncAll = () => {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: async () => {
      const sources = await SourcesService.listSources()
      const enabled = sources.filter((source) => source.enabled)
      await Promise.all(
        enabled.map((source) =>
          JobsService.createJob({
            requestBody: { source_name: source.name, dry_run: false },
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
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] })
    },
  })

  return (
    <Button
      className="my-4"
      variant="outline"
      onClick={() => mutation.mutate()}
      disabled={mutation.isPending}
    >
      <RefreshCw
        className={mutation.isPending ? "mr-2 animate-spin" : "mr-2"}
      />
      Sync All
    </Button>
  )
}

export default SyncAll
