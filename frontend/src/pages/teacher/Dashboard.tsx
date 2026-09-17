import { useState } from "react"
import { AppShell } from "@/components/layout/AppShell"
import { MetricCard } from "@/components/socratiq/MetricCard"
import { MasteryBadge } from "@/components/socratiq/MasteryBadge"
import { currentTeacher, teacherCourses, studentRows } from "@/data/mockData"
import { cn } from "@/lib/utils"

export default function TeacherDashboard() {
  const [activeCourse, setActiveCourse] = useState(teacherCourses[0].id)
  const course = teacherCourses.find((c) => c.id === activeCourse) ?? teacherCourses[0]

  return (
    <AppShell
      role="teacher"
      userName={currentTeacher.name}
      userEmail={currentTeacher.email}
      courses={teacherCourses}
      crumbs={[{ label: "Dashboard" }, { label: course.name }]}
    >
      <div className="mb-5 flex flex-wrap gap-2">
        {teacherCourses.map((c) => (
          <button
            key={c.id}
            onClick={() => setActiveCourse(c.id)}
            className={cn(
              "rounded-full border px-3.5 py-1.5 text-sm font-medium transition-colors",
              c.id === activeCourse
                ? "border-[var(--color-plum)] bg-[var(--color-plum)] text-white"
                : "border-[var(--color-border-strong)] bg-white text-[var(--color-ink-soft)] hover:bg-[var(--color-surface-muted)]"
            )}
          >
            {c.name}
          </button>
        ))}
      </div>

      <h1 className="text-xl font-semibold text-[var(--color-ink)]">{course.name} overview</h1>

      <div className="mt-5 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <MetricCard value="83%" label="Assignment completion" />
        <MetricCard value="80%" label="Average grade" />
        <MetricCard value="62%" label="Socratic AI usage" />
        <MetricCard value="33%" label="External AI usage" />
      </div>

      <h2 className="mb-3 mt-8 text-sm font-semibold uppercase tracking-wide text-[var(--color-ink-faint)]">
        Students
      </h2>
      <div className="overflow-x-auto rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-white">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead>
            <tr className="bg-[var(--color-slate)] text-white">
              <Th>Student name</Th>
              <Th>Task submission</Th>
              <Th>Socratic AI usage</Th>
              <Th>External AI usage</Th>
              <Th>Mastery</Th>
            </tr>
          </thead>
          <tbody>
            {studentRows.map((s, i) => (
              <tr key={s.id} className={i % 2 ? "bg-[var(--color-surface-muted)]/50" : ""}>
                <Td className="font-medium text-[var(--color-ink)]">{s.name}</Td>
                <Td>{s.taskSubmission}%</Td>
                <Td>{s.socraticAiUsage}%</Td>
                <Td>{s.externalAiUsage}%</Td>
                <Td>
                  <MasteryBadge level={s.mastery} />
                </Td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </AppShell>
  )
}

function Th({ children }: { children: React.ReactNode }) {
  return <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide">{children}</th>
}
function Td({ children, className }: { children: React.ReactNode; className?: string }) {
  return <td className={cn("border-t border-[var(--color-border)] px-4 py-3", className)}>{children}</td>
}
