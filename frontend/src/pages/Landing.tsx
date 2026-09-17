import { Link } from "react-router-dom"
import { Button } from "@/components/ui/Button"

const pillars = [
  {
    title: "Socratic, not silent",
    body: "The coach answers with a question, guiding students to reason toward the solution themselves.",
  },
  {
    title: "Built for both sides",
    body: "One workspace: students learn inside their assignments, teachers see exactly how they got there.",
  },
  {
    title: "Skill over shortcuts",
    body: "Every interaction is designed to build understanding, not hand over an answer to paste in.",
  },
]

export default function Landing() {
  return (
    <div className="min-h-screen bg-[var(--color-canvas)]">
      <header className="flex items-center justify-between px-6 py-5 lg:px-10">
        <Link to="/" className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-[var(--color-teal)]" />
          <span className="text-lg font-semibold text-[var(--color-ink)]">SocratiQ</span>
        </Link>
        <nav className="flex items-center gap-3">
          <Link to="/login" className="text-sm font-medium text-[var(--color-ink-soft)] hover:text-[var(--color-ink)]">
            Log in
          </Link>
          <Link to="/signup">
            <Button size="sm">Sign up</Button>
          </Link>
        </nav>
      </header>

      <section className="mx-6 overflow-hidden rounded-[var(--radius-xl)] bg-gradient-to-br from-[#c9dcec] via-[#d8e8de] to-[#e9f1e5] px-6 py-16 lg:mx-10 lg:px-14 lg:py-24">
        <p className="text-xs font-semibold uppercase tracking-wide text-[#4b5b78]">Critical thinking engine</p>
        <h1 className="mt-4 max-w-2xl text-3xl font-semibold leading-tight text-[var(--color-ink)] lg:text-5xl">
          AI that teaches students to think, not just to finish the assignment.
        </h1>
        <p className="mt-4 max-w-xl text-[var(--color-ink-soft)] lg:text-lg">
          SocratiQ turns generative AI from an answer machine into a thinking partner — for students working through a problem, and for the instructors who need to see how they got there.
        </p>
        <div className="mt-7 flex flex-wrap gap-3">
          <Link to="/signup">
            <Button size="lg">Sign up now</Button>
          </Link>
          <Link to="/login">
            <Button size="lg" variant="outline">
              Log in
            </Button>
          </Link>
        </div>
      </section>

      <section className="mx-6 mt-14 grid gap-8 border-t border-[var(--color-border-strong)] pt-10 lg:mx-10 lg:grid-cols-3">
        {pillars.map((p, i) => (
          <div key={p.title} className={i > 0 ? "border-t border-[var(--color-border)] pt-6 lg:border-t-0 lg:border-l lg:pl-8 lg:pt-0" : ""}>
            <h3 className="font-semibold text-[var(--color-ink)]">{p.title}</h3>
            <p className="mt-2 text-sm text-[var(--color-ink-soft)]">{p.body}</p>
          </div>
        ))}
      </section>

      <section className="mx-6 mt-16 max-w-2xl lg:mx-10">
        <h2 className="text-xl font-semibold text-[var(--color-ink)]">About</h2>
        <p className="mt-3 text-[var(--color-ink-soft)]">
          SocratiQ redefines how AI shows up in academic work. Instead of handing over answers, it engages a
          student's own reasoning — building real skill and critical thinking capability. Along the way, it
          captures the learning process itself, so instructors can see evidence of understanding, not just a
          final submission.
        </p>
      </section>

      <footer className="mt-16 flex flex-col items-center justify-between gap-2 bg-[var(--color-plum-dark)] px-6 py-6 text-sm text-white/80 sm:flex-row lg:px-10">
        <span>SocratiQ · All rights reserved</span>
        <a href="mailto:hello@socratiq.app" className="hover:text-white">
          hello@socratiq.app
        </a>
      </footer>
    </div>
  )
}
