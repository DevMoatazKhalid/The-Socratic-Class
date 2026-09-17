import { useRef, useState } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"
import { AppShell } from "@/components/layout/AppShell"
import { Card, CardContent } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Badge } from "@/components/ui/Badge"
import { LearningJourney, type JourneyStep } from "@/components/socratiq/LearningJourney"
import { ErrorState } from "@/components/ui/States"
import { Paperclip, MessageCircle } from "lucide-react"
import { currentStudent, studentCourses, getCourse, getAssignment } from "@/data/mockData"
import type { AssignmentStatus } from "@/types"

function journeyFor(status: AssignmentStatus): JourneyStep[] {
  const order: AssignmentStatus[] = ["not_started", "in_progress", "submitted", "verified"]
  const idx = order.indexOf(status)
  const labels = ["Initial attempt", "AI coaching", "Final submission", "Learning verification"]
  return labels.map((label, i) => ({
    label,
    state: i < idx ? "done" : i === idx ? "current" : "upcoming",
  }))
}

export default function StudentAssignmentDetail() {
  const { courseId = "", assignmentId = "" } = useParams()
  const navigate = useNavigate()
  const course = getCourse(courseId, "student")
  const assignment = getAssignment(assignmentId)
  const fileInput = useRef<HTMLInputElement>(null)

  const [status, setStatus] = useState<AssignmentStatus>(assignment?.status ?? "not_started")
  const [fileName, setFileName] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (!course || !assignment) {
    return (
      <AppShell role="student" userName={currentStudent.name} userEmail={currentStudent.email} courses={studentCourses} crumbs={[{ label: "Courses", to: "/student/courses" }, { label: "Not found" }]}>
        <ErrorState title="Assignment not found" description="This assignment may have been removed or the link is incorrect." />
      </AppShell>
    )
  }

  function handleSubmit() {
    setSubmitting(true)
    setTimeout(() => {
      setSubmitting(false)
      setStatus("submitted")
    }, 700)
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
        { label: assignment.title },
      ]}
    >
      <div className="grid gap-6 lg:grid-cols-[1fr,280px]">
        <Card>
          <CardContent>
            <div className="flex items-start justify-between gap-3">
              <div>
                <h1 className="text-lg font-semibold text-[var(--color-ink)]">{assignment.title}</h1>
                <p className="mt-1 text-sm text-[var(--color-ink-faint)]">
                  {course.name} · {assignment.topic}
                </p>
              </div>
              <Badge tone={status === "verified" ? "success" : status === "submitted" ? "teal" : "warning"}>
                {status === "verified" ? "Verified" : status === "submitted" ? "Submitted" : status === "in_progress" ? "In progress" : "Not started"}
              </Badge>
            </div>

            <p className="mt-4 text-[var(--color-ink-soft)]">{assignment.prompt}</p>

            {fileName && (
              <p className="mt-4 flex items-center gap-2 text-sm text-[var(--color-ink-soft)]">
                <Paperclip className="h-4 w-4" /> {fileName}
              </p>
            )}

            <div className="mt-6 flex flex-wrap gap-2">
              <Button variant="outline" onClick={() => navigate(-1)}>
                Go back
              </Button>
              <input ref={fileInput} type="file" className="hidden" onChange={(e) => setFileName(e.target.files?.[0]?.name ?? null)} />
              <Button variant="secondary" onClick={() => fileInput.current?.click()}>
                Upload
              </Button>
              <Button
                onClick={handleSubmit}
                disabled={!fileName || submitting || status === "submitted" || status === "verified"}
              >
                {submitting ? "Submitting…" : status === "submitted" || status === "verified" ? "Submitted" : "Submit"}
              </Button>
              <Link to={`/student/courses/${course.id}/assignments/${assignment.id}/coach`}>
                <Button variant="primary" className="gap-1.5">
                  <MessageCircle className="h-4 w-4" /> Ask SocratiQ AI
                </Button>
              </Link>
            </div>

            {status === "submitted" && (
              <div className="mt-6 rounded-[var(--radius-md)] border border-[var(--color-teal-light)] bg-[var(--color-teal-light)]/50 p-4">
                <p className="text-sm font-medium text-[var(--color-ink)]">Ready for learning verification</p>
                <p className="mt-1 text-sm text-[var(--color-ink-soft)]">
                  Show what you understand about your solution before it's graded — a short, conversational check tied to what you actually submitted.
                </p>
                <Link to={`/student/courses/${course.id}/assignments/${assignment.id}/verify`}>
                  <Button size="sm" className="mt-3">
                    Start verification
                  </Button>
                </Link>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <h2 className="mb-4 text-sm font-semibold text-[var(--color-ink)]">Your learning journey</h2>
            <LearningJourney steps={journeyFor(status)} />
          </CardContent>
        </Card>
      </div>
    </AppShell>
  )
}
