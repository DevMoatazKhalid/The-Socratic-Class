import { useEffect, useRef, useState } from "react"
import { useParams } from "react-router-dom"
import { AppShell } from "@/components/layout/AppShell"
import { Button } from "@/components/ui/Button"
import { ErrorState } from "@/components/ui/States"
import { currentStudent, studentCourses, getCourse, getAssignment, chatHistory } from "@/data/mockData"
import type { ChatMessage } from "@/types"
import { cn } from "@/lib/utils"
import { Send } from "lucide-react"

const thinkingStates = [
  "Reviewing your attempt…",
  "Looking at the relevant course material…",
  "Preparing a learning question…",
]

const coachReplies = [
  "That's a reasonable place to start — can you show me what that update looks like as one line of code?",
  "Before we move on: why does subtracting the gradient, rather than adding it, move theta toward the minimum?",
  "Good. Now, what would happen to your update if the learning rate alpha were much larger?",
]

export default function AiCoach() {
  const { courseId = "", assignmentId = "" } = useParams()
  const course = getCourse(courseId, "student")
  const assignment = getAssignment(assignmentId)

  const [messages, setMessages] = useState<ChatMessage[]>(chatHistory)
  const [draft, setDraft] = useState("")
  const [thinking, setThinking] = useState<string | null>(null)
  const replyIndex = useRef(0)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" })
  }, [messages, thinking])

  if (!course || !assignment) {
    return (
      <AppShell role="student" userName={currentStudent.name} userEmail={currentStudent.email} courses={studentCourses} crumbs={[{ label: "Courses", to: "/student/courses" }, { label: "Not found" }]}>
        <ErrorState title="Assignment not found" description="This assignment may have been removed or the link is incorrect." />
      </AppShell>
    )
  }

  function send() {
    const text = draft.trim()
    if (!text) return
    setMessages((m) => [...m, { id: crypto.randomUUID(), role: "student", content: text }])
    setDraft("")
    setThinking(thinkingStates[Math.floor(Math.random() * thinkingStates.length)])
    setTimeout(() => {
      setThinking(null)
      const reply = coachReplies[replyIndex.current % coachReplies.length]
      replyIndex.current += 1
      setMessages((m) => [...m, { id: crypto.randomUUID(), role: "coach", kind: "question", content: reply }])
    }, 1100)
  }

  return (
    <AppShell
      role="student"
      userName={currentStudent.name}
      userEmail={currentStudent.email}
      courses={studentCourses}
      crumbs={[
        { label: "Courses", to: "/student/courses" },
        { label: course.name, to: `/student/courses/${course.id}` },
        { label: assignment.title, to: `/student/courses/${course.id}/assignments/${assignment.id}` },
        { label: "SocratiQ AI" },
      ]}
    >
      <div className="mx-auto flex h-[calc(100vh-8.5rem)] max-w-3xl flex-col overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-white">
        <div className="border-b border-[var(--color-border)] px-5 py-3">
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--color-teal-dark)]">Learning coach</p>
          <h1 className="text-base font-semibold text-[var(--color-ink)]">{assignment.topic}</h1>
        </div>

        <div ref={scrollRef} className="thin-scroll flex-1 space-y-3 overflow-y-auto px-5 py-5">
          {messages.map((m) => (
            <Bubble key={m.id} message={m} />
          ))}
          {thinking && (
            <div className="flex justify-start">
              <div className="flex items-center gap-2 rounded-[var(--radius-lg)] bg-[var(--color-surface-muted)] px-4 py-2.5 text-sm text-[var(--color-ink-faint)]">
                <span className="flex gap-1">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--color-ink-faint)]" />
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--color-ink-faint)] [animation-delay:150ms]" />
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--color-ink-faint)] [animation-delay:300ms]" />
                </span>
                {thinking}
              </div>
            </div>
          )}
        </div>

        <form
          className="flex items-center gap-2 border-t border-[var(--color-border)] p-3"
          onSubmit={(e) => {
            e.preventDefault()
            send()
          }}
        >
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Start your chat here…"
            className="h-11 flex-1 rounded-full border border-[var(--color-border-strong)] bg-white px-4 text-sm placeholder:text-[var(--color-ink-faint)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-teal-dark)]"
            aria-label="Message SocratiQ AI"
          />
          <Button type="submit" size="md" className="h-11 w-11 rounded-full p-0" aria-label="Send message">
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </div>
    </AppShell>
  )
}

function Bubble({ message }: { message: ChatMessage }) {
  const isStudent = message.role === "student"
  return (
    <div className={cn("flex", isStudent ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[75%] rounded-[var(--radius-lg)] px-4 py-2.5 text-sm",
          isStudent ? "bg-[var(--color-teal-light)] text-[var(--color-ink)]" : "bg-[var(--color-surface-muted)] text-[var(--color-ink)]"
        )}
      >
        {message.content}
      </div>
    </div>
  )
}
