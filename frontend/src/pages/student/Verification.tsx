import { useState } from "react"
import { useNavigate, useParams, Link } from "react-router-dom"
import { AppShell } from "@/components/layout/AppShell"
import { Card, CardContent } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Badge } from "@/components/ui/Badge"
import { ErrorState } from "@/components/ui/States"
import { CheckCircle2 } from "lucide-react"
import { currentStudent, studentCourses, getCourse, getAssignment } from "@/data/mockData"

const steps = [
  {
    key: "explain",
    label: "Explain",
    prompt: "In your own words, why does subtracting the gradient move theta toward the minimum, rather than away from it?",
  },
  {
    key: "modify",
    label: "Modify",
    prompt: "Suppose the learning rate alpha were 10x larger. What would you expect to happen to your solution, and why?",
  },
  {
    key: "transfer",
    label: "Transfer",
    prompt: "If you had two features instead of one, what would need to change in your implementation?",
  },
]

export default function Verification() {
  const { courseId = "", assignmentId = "" } = useParams()
  const navigate = useNavigate()
  const course = getCourse(courseId, "student")
  const assignment = getAssignment(assignmentId)

  const [stepIndex, setStepIndex] = useState(0)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [done, setDone] = useState(false)

  if (!course || !assignment) {
    return (
      <AppShell role="student" userName={currentStudent.name} userEmail={currentStudent.email} courses={studentCourses} crumbs={[{ label: "Courses", to: "/student/courses" }, { label: "Not found" }]}>
        <ErrorState title="Assignment not found" description="This assignment may have been removed or the link is incorrect." />
      </AppShell>
    )
  }

  const step = steps[stepIndex]

  function handleNext() {
    if (stepIndex < steps.length - 1) {
      setStepIndex((i) => i + 1)
    } else {
      setDone(true)
    }
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
        { label: "Verification" },
      ]}
    >
      <Card className="mx-auto max-w-2xl">
        <CardContent>
          {!done ? (
            <>
              <p className="text-xs font-medium uppercase tracking-wide text-[var(--color-teal-dark)]">
                Show what you understand
              </p>
              <h1 className="mt-1 text-lg font-semibold text-[var(--color-ink)]">{assignment.title}</h1>
              <p className="mt-1 text-sm text-[var(--color-ink-soft)]">
                A short conversation about the solution you submitted — this isn't a re-test, it's a chance to
                show the reasoning behind your work.
              </p>

              <div className="mt-5 flex gap-2">
                {steps.map((s, i) => (
                  <span
                    key={s.key}
                    className={`h-1.5 flex-1 rounded-full ${i <= stepIndex ? "bg-[var(--color-teal)]" : "bg-[var(--color-border)]"}`}
                  />
                ))}
              </div>

              <div className="mt-5 rounded-[var(--radius-md)] bg-[var(--color-surface-muted)] p-4">
                <Badge tone="teal">{step.label}</Badge>
                <p className="mt-2 text-[var(--color-ink)]">{step.prompt}</p>
              </div>

              <textarea
                value={answers[step.key] ?? ""}
                onChange={(e) => setAnswers((a) => ({ ...a, [step.key]: e.target.value }))}
                rows={5}
                placeholder="Write your response…"
                className="mt-4 w-full rounded-[var(--radius-md)] border border-[var(--color-border-strong)] p-3 text-sm placeholder:text-[var(--color-ink-faint)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-teal-dark)]"
              />

              <div className="mt-4 flex justify-between">
                <Button variant="outline" onClick={() => navigate(-1)}>
                  Go back
                </Button>
                <Button onClick={handleNext} disabled={!answers[step.key]?.trim()}>
                  {stepIndex < steps.length - 1 ? "Continue" : "Finish verification"}
                </Button>
              </div>
            </>
          ) : (
            <div className="flex flex-col items-center py-8 text-center">
              <CheckCircle2 className="h-10 w-10 text-[var(--color-teal-dark)]" />
              <h2 className="mt-3 text-lg font-semibold text-[var(--color-ink)]">Verification complete</h2>
              <p className="mt-1 max-w-sm text-sm text-[var(--color-ink-soft)]">
                Your reasoning has been added to this assignment's learning evidence. Your instructor will see it
                alongside your submission.
              </p>
              <Link to={`/student/courses/${course.id}/assignments/${assignment.id}`}>
                <Button className="mt-5">Back to assignment</Button>
              </Link>
            </div>
          )}
        </CardContent>
      </Card>
    </AppShell>
  )
}
