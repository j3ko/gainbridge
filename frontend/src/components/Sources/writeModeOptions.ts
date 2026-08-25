import type { write_mode } from "@/client"

export const writeModeOptions: {
  value: write_mode
  label: string
  description: string
}[] = [
  {
    value: "fix",
    label: "Fix mismatched tags",
    description:
      "Write tags that are missing, or replace ones that don't match the freshly computed gain. Leaves already-correct tags untouched.",
  },
  {
    value: "overwrite",
    label: "Overwrite all tags",
    description:
      "Rewrite ReplayGain tags on every track, even ones that already match.",
  },
  {
    value: "skip",
    label: "Skip existing tags",
    description:
      "Never touch a track that already has ReplayGain tags, even if they're wrong.",
  },
]
