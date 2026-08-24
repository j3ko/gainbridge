import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Clock } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { type SourcePublic, SourcesService } from "@/client"
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
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

const formSchema = z
  .object({
    schedule_enabled: z.boolean(),
    schedule_cron: z.string().optional(),
  })
  .refine((data) => !data.schedule_enabled || !!data.schedule_cron?.trim(), {
    message: "Cron expression is required when scheduling is enabled",
    path: ["schedule_cron"],
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
      schedule_enabled: source.schedule_enabled ?? false,
      schedule_cron: source.schedule_cron ?? "",
    },
  })

  const mutation = useMutation({
    mutationFn: (data: FormData) =>
      data.schedule_enabled
        ? SourcesService.setSchedule({
            name: source.name,
            requestBody: {
              schedule_cron: data.schedule_cron!.trim(),
              schedule_enabled: true,
            },
          })
        : SourcesService.clearSchedule({ name: source.name }),
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
              <FormField
                control={form.control}
                name="schedule_enabled"
                render={({ field }) => (
                  <FormItem className="flex items-center gap-3 space-y-0">
                    <FormControl>
                      <Checkbox
                        checked={field.value}
                        onCheckedChange={field.onChange}
                      />
                    </FormControl>
                    <FormLabel className="font-normal">Enabled</FormLabel>
                  </FormItem>
                )}
              />

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
                      e.g. <code>0 */6 * * *</code> = every 6 hours
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
