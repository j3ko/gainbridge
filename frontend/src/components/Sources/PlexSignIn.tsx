import { CheckCircle2 } from "lucide-react"
import { useEffect, useRef, useState } from "react"

import { type ApiError, type PlexServerOption, SourcesService } from "@/client"
import { Button } from "@/components/ui/button"
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

const POLL_INTERVAL_MS = 1500
const POLL_TIMEOUT_MS = 2 * 60 * 1000

interface PlexSignInProps {
  connectedSummary?: string | null
  onConnected: (args: {
    base_url: string
    token: string
    serverName: string
  }) => void
}

const PlexSignIn = ({ connectedSummary, onConnected }: PlexSignInProps) => {
  const { showErrorToast } = useCustomToast()
  const [connecting, setConnecting] = useState(false)
  const [servers, setServers] = useState<PlexServerOption[] | null>(null)
  const [summary, setSummary] = useState<string | null>(
    connectedSummary ?? null,
  )
  const tokenRef = useRef<string>("")
  const popupRef = useRef<Window | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }

  const closePopup = () => {
    try {
      popupRef.current?.close()
    } catch {
      // popup may be cross-origin (COOP) by this point; ignore
    }
  }

  const fetchServers = async (token: string) => {
    try {
      const result = await SourcesService.listPlexServers({ token })
      if (result.length === 0) {
        showErrorToast("No Plex servers found for this account.")
        return
      }
      tokenRef.current = token
      setServers(result)
    } catch (err) {
      handleError.call(showErrorToast, err as ApiError)
    } finally {
      setConnecting(false)
    }
  }

  const startSignIn = async () => {
    setServers(null)
    setSummary(null)
    setConnecting(true)

    // Open the popup synchronously (before any await) so browsers don't
    // treat it as an unsolicited popup and block it.
    const popup = window.open(
      "",
      "plex-oauth",
      "width=600,height=700,noopener=false,noreferrer=false",
    )
    popupRef.current = popup

    let pin: { id: string; oauth_url: string }
    try {
      pin = await SourcesService.createPlexPin()
    } catch (err) {
      closePopup()
      setConnecting(false)
      handleError.call(showErrorToast, err as ApiError)
      return
    }

    if (popup) {
      popup.location.href = pin.oauth_url
    } else {
      setConnecting(false)
      showErrorToast(
        "Your browser blocked the Plex sign-in popup. Please allow popups and try again.",
      )
      return
    }

    const deadline = Date.now() + POLL_TIMEOUT_MS
    pollRef.current = setInterval(async () => {
      let popupClosed = false
      try {
        popupClosed = !!popupRef.current?.closed
      } catch {
        popupClosed = false
      }
      if (popupClosed) {
        stopPolling()
        setConnecting(false)
        return
      }
      if (Date.now() > deadline) {
        stopPolling()
        setConnecting(false)
        closePopup()
        showErrorToast("Plex sign-in timed out. Please try again.")
        return
      }
      try {
        const status = await SourcesService.checkPlexPin({ pinId: pin.id })
        if (status.authenticated && status.token) {
          stopPolling()
          closePopup()
          await fetchServers(status.token)
        }
      } catch (err) {
        stopPolling()
        setConnecting(false)
        handleError.call(showErrorToast, err as ApiError)
      }
    }, POLL_INTERVAL_MS)
  }

  const handleSelectServer = (uri: string) => {
    const server = servers?.find((s) =>
      s.connections.some((c) => c.uri === uri),
    )
    if (!server) return
    setSummary(`${server.name} — ${uri}`)
    setServers(null)
    onConnected({
      base_url: uri,
      token: tokenRef.current,
      serverName: server.name,
    })
  }

  if (servers) {
    return (
      <div className="flex flex-col gap-2">
        <Select onValueChange={handleSelectServer}>
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Select your Plex server" />
          </SelectTrigger>
          <SelectContent>
            {servers.flatMap((server) =>
              server.connections.map((conn) => (
                <SelectItem key={conn.uri} value={conn.uri}>
                  {server.name} — {conn.uri}
                  {conn.local ? " (local)" : ""}
                </SelectItem>
              )),
            )}
          </SelectContent>
        </Select>
      </div>
    )
  }

  if (summary) {
    return (
      <div className="flex min-w-0 items-center justify-between gap-2 rounded-md border p-3 text-sm">
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <CheckCircle2 className="size-4 shrink-0 text-green-600" />
          <span className="min-w-0 truncate">Connected: {summary}</span>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="shrink-0"
          onClick={startSignIn}
        >
          Change
        </Button>
      </div>
    )
  }

  return (
    <LoadingButton type="button" loading={connecting} onClick={startSignIn}>
      Sign in with Plex
    </LoadingButton>
  )
}

export default PlexSignIn
