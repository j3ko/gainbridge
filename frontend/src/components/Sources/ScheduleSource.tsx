import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Clock } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { type SourcePublic, SourcesService } from "@/client"
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
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

const CRON_PRESETS = [
  { label: "Every hour", value: "0 * * * *" },
  { label: "Every 6 hours", value: "0 */6 * * *" },
  { label: "Every 12 hours", value: "0 */12 * * *" },
  { label: "Daily at midnight", value: "0 0 * * *" },
  { label: "Daily at 2 AM", value: "0 2 * * *" },
  { label: "Weekly (Sunday midnight)", value: "0 0 * * 0" },
]

const formSchema = z.object({
  schedule_cron: z.string().optional(),
})

type FormData = z.infer<typeof formSchema>

interface ScheduleSourceProps {
  source: SourcePublic
  onSuccess: () => void
}

const ScheduleSource = ({ source, onSuccess }: ScheduleSourceProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      schedule_cron: source.schedule_cron ?? "",
    },
  })

  const mutation = useMutation({
    mutationFn: (data: FormData) => {
      const cron = data.schedule_cron?.trim()
      return cron
        ? SourcesService.setSchedule({
            name: source.name,
            requestBody: { schedule_cron: cron },
          })
        : SourcesService.clearSchedule({ name: source.name })
    },
    onSuccess: () => {
      showSuccessToast("Schedule updated")
      setIsOpen(false)
      onSuccess()
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["sources"] })
    },
  })

  const onSubmit = (data: FormData) => {
    mutation.mutate(data)
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DropdownMenuItem
        onSelect={(e) => e.preventDefault()}
        onClick={() => setIsOpen(true)}
      >
        <Clock />
        Schedule
      </DropdownMenuItem>
      <DialogContent className="sm:max-w-md">
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)}>
            <DialogHeader>
              <DialogTitle>Schedule Sync</DialogTitle>
              <DialogDescription>
                Automatically run a sync for "{source.name}" on a recurring
                schedule.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <FormItem>
                <FormLabel>Common Schedules</FormLabel>
                <Select
                  onValueChange={(value) =>
                    form.setValue("schedule_cron", value, {
                      shouldValidate: true,
                      shouldDirty: true,
                    })
                  }
                >
                  <FormControl>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Quick fill…" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {CRON_PRESETS.map((preset) => (
                      <SelectItem key={preset.value} value={preset.value}>
                        {preset.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormItem>

              <FormField
                control={form.control}
                name="schedule_cron"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Cron Expression</FormLabel>
                    <FormControl>
                      <Input placeholder="0 */6 * * *" type="text" {...field} />
                    </FormControl>
                    <p className="text-sm text-muted-foreground">
                      e.g. <code>0 */6 * * *</code> = every 6 hours. Leave blank
                      to turn off the schedule.
                    </p>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <DialogFooter>
              <DialogClose asChild>
                <Button variant="outline" disabled={mutation.isPending}>
                  Cancel
                </Button>
              </DialogClose>
              <LoadingButton type="submit" loading={mutation.isPending}>
                Save
              </LoadingButton>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}

export default ScheduleSource
