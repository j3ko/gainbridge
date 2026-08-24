import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Pencil, Plus, Trash2 } from "lucide-react"
import { useState } from "react"
import { useFieldArray, useForm } from "react-hook-form"
import { z } from "zod"

import { type SourceCreate, type SourcePublic, SourcesService } from "@/client"
import PlexSignIn from "@/components/Sources/PlexSignIn"
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
  FormDescription,
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

const pathMappingSchema = z.object({
  remote_path: z.string().min(1, { message: "Required" }),
  local_path: z.string().min(1, { message: "Required" }),
})

const formSchema = z.object({
  type: z.enum(["plex", "jellyfin"]),
  base_url: z.string().min(1, { message: "Server URL is required" }),
  token: z.string().min(1, { message: "Token is required" }),
  user_id: z.string().optional(),
  enabled: z.boolean(),
  path_mappings: z.array(pathMappingSchema),
})

type FormData = z.infer<typeof formSchema>

interface EditSourceProps {
  source: SourcePublic
  onSuccess: () => void
}

const EditSource = ({ source, onSuccess }: EditSourceProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const [plexSummary, setPlexSummary] = useState<string | null>(
    source.type === "plex" ? source.base_url : null,
  )
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      type: source.type as "plex" | "jellyfin",
      base_url: source.base_url,
      token: source.token,
      user_id: source.user_id ?? "",
      enabled: source.enabled,
      path_mappings: (source.path_mappings ?? []).map((m) => ({
        remote_path: m.remote_path,
        local_path: m.local_path,
      })),
    },
  })

  const sourceType = form.watch("type")
  const pathMappings = useFieldArray({
    control: form.control,
    name: "path_mappings",
  })

  const mutation = useMutation({
    mutationFn: (data: SourceCreate) =>
      SourcesService.addSource({ requestBody: data }),
    onSuccess: () => {
      showSuccessToast("Source updated successfully")
      setIsOpen(false)
      onSuccess()
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["sources"] })
    },
  })

  const onSubmit = (data: FormData) => {
    mutation.mutate({
      ...data,
      name: source.name,
      user_id: data.user_id ? data.user_id : null,
    })
  }

  const testMutation = useMutation({
    mutationFn: () =>
      SourcesService.testConnection({
        requestBody: {
          type: form.getValues("type"),
          base_url: form.getValues("base_url"),
          token: form.getValues("token"),
          user_id: form.getValues("user_id") || null,
        },
      }),
    onSuccess: (result: Record<string, unknown>) => {
      const serverName = result.server_name as string | undefined
      const version = result.version as string | undefined
      const label = [serverName, version].filter(Boolean).join(" · ")
      showSuccessToast(
        label ? `Connected to ${label}` : "Connection successful",
      )
    },
    onError: handleError.bind(showErrorToast),
  })

  const handleTestConnection = async () => {
    const valid = await form.trigger(["type", "base_url", "token", "user_id"])
    if (!valid) return
    testMutation.mutate()
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DropdownMenuItem
        onSelect={(e) => e.preventDefault()}
        onClick={() => setIsOpen(true)}
      >
        <Pencil />
        Edit Source
      </DropdownMenuItem>
      <DialogContent className="sm:max-w-md">
        <Form {...form}>
          <form className="min-w-0" onSubmit={form.handleSubmit(onSubmit)}>
            <DialogHeader>
              <DialogTitle>Edit Source</DialogTitle>
              <DialogDescription>
                Update the connection details for "{source.name}".
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <FormField
                control={form.control}
                name="type"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>
                      Type <span className="text-destructive">*</span>
                    </FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder="Select a type" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="plex">Plex</SelectItem>
                        <SelectItem value="jellyfin">Jellyfin</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {sourceType === "plex" ? (
                <FormItem className="min-w-0">
                  <FormLabel>
                    Plex Server <span className="text-destructive">*</span>
                  </FormLabel>
                  <PlexSignIn
                    connectedSummary={plexSummary}
                    onConnected={({ base_url, token, serverName }) => {
                      form.setValue("base_url", base_url, {
                        shouldValidate: true,
                      })
                      form.setValue("token", token, { shouldValidate: true })
                      setPlexSummary(`${serverName} — ${base_url}`)
                    }}
                  />
                  <FormMessage>
                    {form.formState.errors.base_url?.message ||
                      form.formState.errors.token?.message}
                  </FormMessage>
                </FormItem>
              ) : (
                <>
                  <FormField
                    control={form.control}
                    name="base_url"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          Server URL <span className="text-destructive">*</span>
                        </FormLabel>
                        <FormControl>
                          <Input
                            placeholder="http://192.168.1.10:8096"
                            type="text"
                            {...field}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="token"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          API Key <span className="text-destructive">*</span>
                        </FormLabel>
                        <FormControl>
                          <Input
                            placeholder="Token"
                            type="password"
                            {...field}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </>
              )}

              <LoadingButton
                type="button"
                variant="outline"
                size="sm"
                loading={testMutation.isPending}
                onClick={handleTestConnection}
              >
                Test Connection
              </LoadingButton>

              {sourceType === "jellyfin" && (
                <FormField
                  control={form.control}
                  name="user_id"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>User ID</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Jellyfin user ID"
                          type="text"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              )}

              <div className="flex flex-col gap-2">
                <div>
                  <FormLabel>Path Mappings</FormLabel>
                  <FormDescription>
                    If this library spans multiple folders, or this machine
                    mounts it at a different path than your Plex/Jellyfin server
                    does, add a mapping for each folder.
                  </FormDescription>
                </div>

                {pathMappings.fields.map((field, index) => (
                  <div
                    key={field.id}
                    className="flex flex-col gap-3 rounded-md border p-3"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">
                        Mapping {index + 1}
                      </span>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="size-6"
                        onClick={() => pathMappings.remove(index)}
                      >
                        <Trash2 className="size-3.5" />
                        <span className="sr-only">Remove mapping</span>
                      </Button>
                    </div>
                    <FormField
                      control={form.control}
                      name={`path_mappings.${index}.remote_path`}
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="font-normal">
                            Remote Path
                          </FormLabel>
                          <FormControl>
                            <Input
                              placeholder="/data/music"
                              type="text"
                              {...field}
                            />
                          </FormControl>
                          <FormDescription>
                            Path as your Plex/Jellyfin server sees this folder.
                          </FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name={`path_mappings.${index}.local_path`}
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="font-normal">
                            Local Path
                          </FormLabel>
                          <FormControl>
                            <Input
                              placeholder="/mnt/music"
                              type="text"
                              {...field}
                            />
                          </FormControl>
                          <FormDescription>
                            Matching path on this machine.
                          </FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                ))}

                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    pathMappings.append({ remote_path: "", local_path: "" })
                  }
                >
                  <Plus className="size-3.5" />
                  Add Mapping
                </Button>
              </div>

              <FormField
                control={form.control}
                name="enabled"
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

export default EditSource
