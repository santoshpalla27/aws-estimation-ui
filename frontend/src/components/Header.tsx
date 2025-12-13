import { Link } from 'react-router-dom'
import { Cloud, Github } from 'lucide-react'

export function Header() {
    return (
        <header className="border-b border-border bg-card">
            <div className="flex h-16 items-center px-6">
                <Link to="/" className="flex items-center gap-2 font-semibold">
                    <Cloud className="h-6 w-6 text-primary" />
                    <span className="text-lg">AWS Cost Estimation</span>
                </Link>

                <div className="ml-auto flex items-center gap-4">
                    <a
                        href="https://github.com"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-muted-foreground hover:text-foreground"
                    >
                        <Github className="h-5 w-5" />
                    </a>
                </div>
            </div>
        </header>
    )
}
