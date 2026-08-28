import { useQuery } from "@tanstack/react-query"
import { FaGithub } from "react-icons/fa"
import { UtilsService } from "@/client"

const socialLinks = [
  {
    icon: FaGithub,
    href: "https://github.com/j3ko/gainbridge",
    label: "GitHub",
  },
]

export function Footer() {
  const currentYear = new Date().getFullYear()
  const { data: config } = useQuery({
    queryKey: ["config"],
    queryFn: () => UtilsService.getConfig(),
  })

  return (
    <footer className="border-t py-4 px-6">
      <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
        <p className="text-muted-foreground text-sm">
          Gainbridge{config && ` v${config.version}`} - {currentYear}
        </p>
        <div className="flex items-center gap-4">
          {socialLinks.map(({ icon: Icon, href, label }) => (
            <a
              key={label}
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={label}
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              <Icon className="h-5 w-5" />
            </a>
          ))}
        </div>
      </div>
    </footer>
  )
}
